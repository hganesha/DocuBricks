"""
apps/portal/pages/upload.py
----------------------------
Document Upload page.

Features
~~~~~~~~
- File uploader (pdf, docx, png, jpg, tiff)
- Vertical selector populated from Lakebase
- SHA-256 duplicate detection before uploading
- Volume upload via lib.databricks_api.upload_to_volume
- Document registration in Lakebase (document_registry)
- Pipeline trigger via lib.databricks_api.trigger_pipeline
- "Try a sample" expander with 3 pre-loaded document options
- Auto-navigate to Status page on successful upload via session state
"""
from __future__ import annotations

import hashlib
import uuid
import time
from datetime import datetime, timezone

import streamlit as st

from lib.auth import get_session
from lib.lakebase import lb_query, lb_exec_returning
from lib.databricks_api import upload_to_volume, trigger_pipeline
from lib.components.vertical_selector import vertical_selector
from lib.otel import tracer, docs_uploaded

# ---------------------------------------------------------------------------
# Allowed file types
# ---------------------------------------------------------------------------
_ALLOWED_TYPES = ["pdf", "docx", "png", "jpg", "jpeg", "tiff"]

_SAMPLE_DOCUMENTS = [
    {
        "label": "Sample Mortgage Application (PDF)",
        "filename": "sample_mortgage_application.pdf",
        "vertical": "fs",
        "description": "A 12-page residential mortgage application with income statements.",
    },
    {
        "label": "Sample KYC / CDD Form (PDF)",
        "filename": "sample_kyc_cdd_form.pdf",
        "vertical": "fs",
        "description": "Know Your Customer due-diligence form with ID copies.",
    },
    {
        "label": "Sample Invoice (PDF)",
        "filename": "sample_invoice.pdf",
        "vertical": "fs",
        "description": "A standard commercial invoice with line-item breakdown.",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _check_duplicate(sha256: str, tenant_id: str) -> dict | None:
    """Return existing document_registry row if SHA-256 already exists for this tenant."""
    rows = lb_query(
        "SELECT document_id, status, created_at FROM document_registry "
        "WHERE content_hash = %s AND tenant_id = %s LIMIT 1",
        (sha256, tenant_id),
    )
    return rows[0] if rows else None


def _register_document(
    document_id: str,
    tenant_id: str,
    vertical: str,
    filename: str,
    file_ext: str,
    content_hash: str,
    volume_path: str,
) -> None:
    lb_exec_returning(
        """
        INSERT INTO document_registry
            (document_id, tenant_id, vertical, original_filename,
             file_ext, content_hash, source_path, status, created_at, updated_at)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, 'RECEIVED', %s, %s)
        RETURNING document_id
        """,
        (
            document_id,
            tenant_id,
            vertical,
            filename,
            file_ext,
            content_hash,
            volume_path,
            datetime.now(timezone.utc),
            datetime.now(timezone.utc),
        ),
    )


def _do_upload(
    file_bytes: bytes,
    filename: str,
    vertical: str,
    tenant_id: str,
) -> tuple[str, str]:
    """
    Run the full upload workflow: hash → volume → register → trigger.
    Returns (document_id, run_id).
    """
    content_hash = _sha256(file_bytes)
    file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    document_id = content_hash  # use SHA-256 as stable document ID

    with tracer.start_as_current_span("portal.upload"):
        volume_path = upload_to_volume(file_bytes, document_id, tenant_id, vertical, file_ext)
        _register_document(
            document_id=document_id,
            tenant_id=tenant_id,
            vertical=vertical,
            filename=filename,
            file_ext=file_ext,
            content_hash=content_hash,
            volume_path=volume_path,
        )
        run_id = trigger_pipeline(document_id, tenant_id)

    docs_uploaded.add(1, {"tenant_id": tenant_id, "vertical": vertical})
    return document_id, run_id


# ---------------------------------------------------------------------------
# Page render
# ---------------------------------------------------------------------------

def render(session: dict) -> None:
    tenant_id = session["tenant_id"]

    st.title("Upload Document")
    st.caption("Supported formats: PDF, DOCX, PNG, JPG, TIFF. Max 200 MB per file.")

    # ── Vertical selector ──────────────────────────────────────────────────
    vertical = vertical_selector(tenant_id)

    st.divider()

    # ── File uploader ──────────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Choose a file to upload",
        type=_ALLOWED_TYPES,
        help="Files are stored in Unity Catalog Volumes and processed by the DocuBricks pipeline.",
        key="portal_upload_file",
    )

    # ── Sample documents expander ──────────────────────────────────────────
    with st.expander("Try a sample document"):
        st.markdown(
            "Don't have a document handy? Pick one of our pre-loaded samples to "
            "explore DocuBricks extraction."
        )
        for sample in _SAMPLE_DOCUMENTS:
            col_label, col_btn = st.columns([4, 1])
            with col_label:
                st.markdown(f"**{sample['label']}**  \n{sample['description']}")
            with col_btn:
                if st.button("Use this", key=f"sample_{sample['filename']}"):
                    st.session_state["sample_selected"] = sample
                    st.rerun()

    # Handle sample selection
    sample_selected = st.session_state.pop("sample_selected", None)
    if sample_selected is not None:
        # Build a minimal fake bytes payload for demonstration
        sample_bytes = (
            f"SAMPLE DOCUMENT: {sample_selected['label']}\n"
            f"Generated at {datetime.now(timezone.utc).isoformat()}\n"
            f"Tenant: {tenant_id}\n"
        ).encode()

        _handle_submission(
            file_bytes=sample_bytes,
            filename=sample_selected["filename"],
            vertical=sample_selected.get("vertical", vertical),
            tenant_id=tenant_id,
        )
        return

    # ── Upload button ──────────────────────────────────────────────────────
    if uploaded_file is not None:
        st.markdown(
            f"**Selected:** `{uploaded_file.name}` &nbsp;·&nbsp; "
            f"{uploaded_file.size / 1024:.1f} KB"
        )

        if st.button("Upload & Process", type="primary", key="portal_upload_btn"):
            file_bytes = uploaded_file.read()
            _handle_submission(
                file_bytes=file_bytes,
                filename=uploaded_file.name,
                vertical=vertical,
                tenant_id=tenant_id,
            )


def _handle_submission(
    file_bytes: bytes,
    filename: str,
    vertical: str,
    tenant_id: str,
) -> None:
    """
    Centralised handler: duplicate-check, upload, register, trigger, navigate.
    """
    content_hash = _sha256(file_bytes)

    # Duplicate detection
    existing = _check_duplicate(content_hash, tenant_id)
    if existing:
        doc_id = existing["document_id"]
        status = existing.get("status", "UNKNOWN")
        st.warning(
            f"This document was already processed.  \n"
            f"**Document ID:** `{doc_id}`  \n"
            f"**Status:** {status}  \n\n"
            "Click **View Status** below to track it."
        )
        if st.button("View Status", key="dup_view_status"):
            st.session_state["tracking_doc"] = doc_id
            st.session_state["nav_page"] = "Status"
            st.rerun()
        return

    with st.spinner("Uploading and registering document…"):
        try:
            document_id, run_id = _do_upload(
                file_bytes=file_bytes,
                filename=filename,
                vertical=vertical,
                tenant_id=tenant_id,
            )
        except Exception as exc:
            st.error(f"Upload failed: {exc}")
            return

    st.success(
        f"Document uploaded successfully!  \n"
        f"**Document ID:** `{document_id}`  \n"
        f"**Pipeline Run:** `{run_id}`"
    )

    # Auto-navigate to status page
    st.session_state["tracking_doc"] = document_id
    st.session_state["nav_page"] = "Status"
    time.sleep(1.2)
    st.rerun()
