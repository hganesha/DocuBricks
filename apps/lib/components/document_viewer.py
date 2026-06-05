"""
apps/lib/components/document_viewer.py
-----------------------------------------
Inline document renderer for the Review UI.

Fetches raw bytes from UC Volume via the Databricks Files API
and renders them inline (PDF iframe, image, or download link).
"""
from __future__ import annotations

import base64
import os

import httpx
import streamlit as st

_HOST  = os.environ.get("DATABRICKS_HOST", "")
_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")

_MIME_TO_KIND = {
    "application/pdf": "pdf",
    "image/png": "image",
    "image/jpeg": "image",
    "image/tiff": "image",
    "image/webp": "image",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/html": "html",
}

_EXT_TO_MIME = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tiff": "image/tiff",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _fetch_bytes(source_path: str) -> tuple[bytes, str]:
    """Fetch file bytes from UC Volume via Files API. Returns (bytes, mime_type)."""
    url = f"{_HOST}/api/2.0/fs/files{source_path}"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {_TOKEN}"}, timeout=30)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "application/octet-stream").split(";")[0]
    if content_type == "application/octet-stream":
        ext = "." + source_path.rsplit(".", 1)[-1].lower() if "." in source_path else ""
        content_type = _EXT_TO_MIME.get(ext, "application/octet-stream")
    return resp.content, content_type


def document_viewer(source_path: str, height: int = 600) -> None:
    """
    Embed a document inline in Streamlit.

    - PDF  → <iframe> with base64 data URI
    - Image → st.image()
    - Other → download link
    """
    if not source_path:
        st.caption("No source path available.")
        return
    try:
        raw, mime = _fetch_bytes(source_path)
    except Exception as exc:
        st.error(f"Could not load document: {exc}")
        return

    kind = _MIME_TO_KIND.get(mime, "other")

    if kind == "pdf":
        b64 = base64.b64encode(raw).decode()
        st.components.v1.html(
            f'<iframe src="data:application/pdf;base64,{b64}" '
            f'width="100%" height="{height}px" style="border:none"></iframe>',
            height=height + 10,
        )
    elif kind == "image":
        st.image(raw, use_container_width=True)
    elif kind == "html":
        st.components.v1.html(raw.decode("utf-8", errors="replace"), height=height)
    else:
        filename = source_path.rsplit("/", 1)[-1]
        st.download_button(
            label=f"Download {filename}",
            data=raw,
            file_name=filename,
            mime=mime,
        )
        st.caption("Preview not available for this file type.")


def document_thumbnail(source_path: str) -> None:
    """Small thumbnail preview (max 200px tall). Falls back to filename label."""
    if not source_path:
        return
    ext = "." + source_path.rsplit(".", 1)[-1].lower() if "." in source_path else ""
    mime = _EXT_TO_MIME.get(ext, "application/octet-stream")
    kind = _MIME_TO_KIND.get(mime, "other")

    if kind == "image":
        try:
            raw, _ = _fetch_bytes(source_path)
            st.image(raw, width=200)
            return
        except Exception:
            pass

    # Fallback: styled filename chip
    filename = source_path.rsplit("/", 1)[-1]
    icon = "📄" if kind == "pdf" else "🖼" if kind == "image" else "📎"
    st.markdown(
        f'<div style="background:#f3f4f6;border:1px solid #e5e7eb;border-radius:6px;'
        f'padding:8px 12px;font-size:12px;color:#374151">{icon} {filename}</div>',
        unsafe_allow_html=True,
    )
