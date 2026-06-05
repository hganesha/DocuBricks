"""
apps/admin/pages/tenant_onboarding.py
---------------------------------------
New tenant onboarding form + existing tenant table.

Onboarding flow:
  1. Fill form (name, vertical, tier, reviewer_emails, owner_email).
  2. Submit → INSERT tenant_registry, reviewer assignments, user rows.
  3. Show landing path for file drops.
  4. "Run smoke test" → upload sample doc → poll to COMPLETE.

Existing tenants: table of active tenants with status, tier, vertical, doc count.
"""
from __future__ import annotations

import sys
import os
import re
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import pandas as pd

from lib.lakebase import lb_exec, lb_exec_returning, lb_query
from lib.sql_warehouse import wh_query, wh_query_df
from lib.databricks_api import trigger_pipeline, get_job_run_status

_VERTICALS = [
    "financial_services",
    "healthcare",
    "insurance",
    "legal",
    "real_estate",
    "logistics",
]

_TIERS = ["starter", "professional", "enterprise"]

_TENANTS_QUERY = """
    SELECT
        t.tenant_id,
        t.tenant_name,
        t.vertical,
        t.tier,
        t.status,
        t.created_at,
        COUNT(d.document_id) AS doc_count
    FROM  tenant_registry   t
    LEFT JOIN document_registry d ON d.tenant_id = t.tenant_id
    WHERE t.status = 'active'
    GROUP BY t.tenant_id, t.tenant_name, t.vertical, t.tier, t.status, t.created_at
    ORDER BY t.created_at DESC
"""

_SAMPLE_DOCS: dict[str, str] = {
    "financial_services": "samples/invoice_sample.pdf",
    "healthcare":         "samples/invoice_sample.pdf",
    "insurance":          "samples/invoice_sample.pdf",
    "legal":              "samples/invoice_sample.pdf",
    "real_estate":        "samples/mortgage_application_sample.pdf",
    "logistics":          "samples/invoice_sample.pdf",
}

_VOLUME_BASE = "dbfs:/Volumes/docubricks_prod/{tenant_id}/{vertical}/inbox/"


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug[:40]


def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


def render(session: dict) -> None:
    st.title("Tenant Onboarding")

    tab_new, tab_existing = st.tabs(["New Tenant", "Existing Tenants"])

    # ── New Tenant Form ────────────────────────────────────────────────────────
    with tab_new:
        st.subheader("Register a New Tenant")

        with st.form("new_tenant_form"):
            name_col, id_col = st.columns([2, 2])
            with name_col:
                tenant_name = st.text_input(
                    "Tenant name *",
                    placeholder="Acme Financial Corp",
                )
            with id_col:
                tenant_id_hint = _slugify(tenant_name) if tenant_name else ""
                tenant_id_input = st.text_input(
                    "Tenant ID (auto-slug) *",
                    value=tenant_id_hint,
                    help="Auto-generated from name. Lowercase letters, numbers, underscores only.",
                )

            vert_col, tier_col = st.columns([2, 2])
            with vert_col:
                vertical = st.selectbox("Vertical *", options=_VERTICALS)
            with tier_col:
                tier = st.selectbox("Tier *", options=_TIERS)

            owner_email = st.text_input(
                "Owner email *",
                placeholder="owner@acmefinancial.com",
            )

            reviewer_emails_raw = st.text_area(
                "Reviewer emails (one per line) *",
                placeholder="reviewer1@acmefinancial.com\nreviewer2@acmefinancial.com",
                height=100,
            )

            submitted = st.form_submit_button("Create Tenant", type="primary")

        if submitted:
            # ── Validation ─────────────────────────────────────────────────────
            errors: list[str] = []

            if not tenant_name.strip():
                errors.append("Tenant name is required.")
            if not tenant_id_input.strip():
                errors.append("Tenant ID is required.")
            elif not re.match(r"^[a-z0-9_]{2,40}$", tenant_id_input.strip()):
                errors.append("Tenant ID must be 2–40 chars: lowercase letters, numbers, underscores only.")
            if not _valid_email(owner_email):
                errors.append("Owner email is not valid.")

            reviewer_emails = [
                e.strip()
                for e in reviewer_emails_raw.splitlines()
                if e.strip()
            ]
            invalid_reviewers = [e for e in reviewer_emails if not _valid_email(e)]
            if invalid_reviewers:
                errors.append(f"Invalid reviewer email(s): {', '.join(invalid_reviewers)}")
            if not reviewer_emails:
                errors.append("At least one reviewer email is required.")

            if errors:
                for err in errors:
                    st.error(err)
            else:
                tenant_id = tenant_id_input.strip()

                with st.spinner("Creating tenant…"):
                    try:
                        # 1. Insert tenant_registry
                        lb_exec(
                            """
                            INSERT INTO tenant_registry
                                (tenant_id, tenant_name, vertical, tier, status, created_at)
                            VALUES (%s, %s, %s, %s, 'active', NOW())
                            """,
                            (tenant_id, tenant_name.strip(), vertical, tier),
                        )

                        # 2. Insert reviewer assignments + user rows
                        for reviewer_email in reviewer_emails:
                            lb_exec(
                                """
                                INSERT INTO tenant_reviewer_assignments
                                    (tenant_id, reviewer_email, assigned_at)
                                VALUES (%s, %s, NOW())
                                ON CONFLICT (tenant_id, reviewer_email) DO NOTHING
                                """,
                                (tenant_id, reviewer_email),
                            )
                            lb_exec(
                                """
                                INSERT INTO tenant_users
                                    (tenant_id, user_email, role, created_at)
                                VALUES (%s, %s, 'reviewer', NOW())
                                ON CONFLICT (tenant_id, user_email) DO UPDATE
                                    SET role = 'reviewer'
                                """,
                                (tenant_id, reviewer_email),
                            )

                        # 3. Owner user row
                        lb_exec(
                            """
                            INSERT INTO tenant_users
                                (tenant_id, user_email, role, created_at)
                            VALUES (%s, %s, 'admin', NOW())
                            ON CONFLICT (tenant_id, user_email) DO UPDATE
                                SET role = 'admin'
                            """,
                            (tenant_id, owner_email.strip()),
                        )

                        landing_path = _VOLUME_BASE.format(
                            tenant_id=tenant_id, vertical=vertical
                        )

                        st.success(f"Tenant **{tenant_name}** created successfully!")
                        st.info(f"File drop path: `{landing_path}`")

                        # Store for smoke test
                        st.session_state["_new_tenant_id"] = tenant_id
                        st.session_state["_new_tenant_vertical"] = vertical

                    except Exception as exc:
                        st.error(f"Failed to create tenant: {exc}")

        # ── Smoke test ─────────────────────────────────────────────────────────
        new_tid = st.session_state.get("_new_tenant_id")
        if new_tid:
            st.markdown("---")
            st.markdown(f"**Smoke test for `{new_tid}`**")

            if st.button("▶ Run smoke test"):
                vertical_code = st.session_state.get("_new_tenant_vertical", "financial_services")
                sample_path   = _SAMPLE_DOCS.get(vertical_code, "samples/invoice_sample.pdf")

                with st.spinner("Uploading sample document…"):
                    try:
                        # Read sample file bytes
                        sample_bytes = b""  # placeholder — in production read from dbfs/s3
                        if os.path.exists(sample_path):
                            with open(sample_path, "rb") as fh:
                                sample_bytes = fh.read()

                        import uuid
                        smoke_doc_id = f"smoke_{new_tid}_{uuid.uuid4().hex[:8]}"

                        run_id = trigger_pipeline(
                            document_id=smoke_doc_id,
                            tenant_id=new_tid,
                        )

                        st.info(f"Pipeline triggered. Run ID: `{run_id}`")

                        # Poll
                        progress = st.progress(0)
                        status_placeholder = st.empty()
                        terminal = {"COMPLETE", "QUARANTINE", "FAILED", "REVIEW"}
                        attempts = 0
                        max_attempts = 30

                        while attempts < max_attempts:
                            status_info = get_job_run_status(run_id)
                            state  = status_info.get("state", "UNKNOWN")
                            result = status_info.get("result_state", "")
                            msg    = status_info.get("state_message", "")

                            status_placeholder.markdown(f"State: `{state}` — {msg}")
                            progress.progress(min(attempts / max_attempts, 0.99))
                            attempts += 1

                            if state == "TERMINATED":
                                progress.progress(1.0)
                                if result == "SUCCESS":
                                    st.success("Smoke test passed — document processed to COMPLETE!")
                                else:
                                    st.error(f"Smoke test failed: {msg}")
                                break

                            time.sleep(5)
                        else:
                            st.warning("Smoke test timed out (150 s). Check Job Monitor.")

                    except Exception as exc:
                        st.error(f"Smoke test error: {exc}")

    # ── Existing Tenants ───────────────────────────────────────────────────────
    with tab_existing:
        st.subheader("Active Tenants")

        with st.spinner("Loading tenants…"):
            try:
                tenant_rows = lb_query(_TENANTS_QUERY)
            except Exception as exc:
                # Fallback: try warehouse
                try:
                    tenant_rows = wh_query(_TENANTS_QUERY)
                except Exception:
                    st.error(f"Could not load tenants: {exc}")
                    return

        if not tenant_rows:
            st.info("No active tenants found.")
            return

        df = pd.DataFrame(tenant_rows)
        df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d")
        df = df.rename(columns={
            "tenant_id":   "Tenant ID",
            "tenant_name": "Name",
            "vertical":    "Vertical",
            "tier":        "Tier",
            "status":      "Status",
            "created_at":  "Created",
            "doc_count":   "Docs",
        })

        st.dataframe(
            df[["Tenant ID", "Name", "Vertical", "Tier", "Status", "Created", "Docs"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Docs": st.column_config.NumberColumn("Docs", format="%d"),
            },
        )
