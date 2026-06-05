"""
apps/admin/pages/schema_prompts.py
------------------------------------
Schema Prompt Management page.

Features:
- List all extraction prompts from schema_registry, grouped by document_type.
- st.expander per document_type shows version history.
- Active version highlighted with green "ACTIVE" badge.
- Edit prompt text → INSERT new version (is_active=false) → trigger test harness job.
- Promote button (after test harness passes) → activate new version.
- Model selector (dbrx-instruct, claude-sonnet, gemini-flash).
- Latest MLflow eval accuracy + link to experiment.
"""
from __future__ import annotations

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st

from lib.sql_warehouse import wh_query
from lib.lakebase import lb_exec, lb_exec_returning, lb_query
from lib.databricks_api import trigger_pipeline, get_job_run_status

_AVAILABLE_MODELS = [
    "dbrx-instruct",
    "claude-sonnet",
    "gemini-flash",
]

_PROMPTS_QUERY = """
    SELECT
        document_type,
        vertical,
        version,
        is_active,
        preferred_model,
        prompt_text,
        updated_at,
        prompt_id,
        mlflow_experiment_id,
        mlflow_run_id,
        test_accuracy
    FROM docubricks_prod.schema_registry.extraction_prompts
    ORDER BY vertical, document_type, version DESC
"""

_MLFLOW_BASE = "https://{host}/#mlflow/experiments/{exp_id}/runs/{run_id}"


def _active_badge() -> str:
    return (
        '<span style="background:#dcfce7;color:#16a34a;border-radius:4px;'
        'font-size:11px;font-weight:700;padding:2px 8px;">ACTIVE</span>'
    )


def _version_badge(version: int) -> str:
    return (
        f'<span style="background:#f3f4f6;color:#374151;border-radius:4px;'
        f'font-size:11px;font-weight:600;padding:2px 7px;">v{version}</span>'
    )


def _pending_badge() -> str:
    return (
        '<span style="background:#fef9c3;color:#854d0e;border-radius:4px;'
        'font-size:11px;font-weight:700;padding:2px 8px;">PENDING TEST</span>'
    )


def _group_prompts(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["document_type"], []).append(row)
    return grouped


def _trigger_test_harness(document_type: str, version: int) -> str:
    """Trigger the schema test harness job and return the run_id."""
    run_id = trigger_pipeline(
        document_id=f"test_harness_{document_type}_v{version}",
        tenant_id="__test__",
    )
    return run_id


def _poll_test_harness(run_id: str) -> dict:
    return get_job_run_status(run_id)


def render(session: dict) -> None:
    st.title("Schema & Prompt Manager")
    st.caption(
        "Manage extraction prompt versions per document type. "
        "New versions must pass the test harness before being promoted to active."
    )

    host = os.environ.get("DATABRICKS_HOST", "")

    with st.spinner("Loading prompts from schema registry…"):
        try:
            rows = wh_query(_PROMPTS_QUERY)
        except Exception as exc:
            st.error(f"Failed to load prompts: {exc}")
            return

    if not rows:
        st.info("No prompts found in schema_registry.extraction_prompts.")
        return

    grouped = _group_prompts(rows)

    for doc_type, versions in grouped.items():
        active_ver = next((v for v in versions if v["is_active"]), None)
        active_label = f" — v{active_ver['version']} active" if active_ver else " — no active version"

        with st.expander(
            f"**{doc_type.replace('_', ' ').title()}**{active_label}",
            expanded=False,
        ):
            # ── Version history table header ───────────────────────────────────
            hcols = st.columns([1, 2, 2, 2, 3])
            hcols[0].markdown("**Ver**")
            hcols[1].markdown("**Model**")
            hcols[2].markdown("**Updated**")
            hcols[3].markdown("**Accuracy**")
            hcols[4].markdown("**Status / Actions**")
            st.markdown('<hr style="margin:4px 0;">', unsafe_allow_html=True)

            for v in versions:
                version      = v["version"]
                is_active    = v["is_active"]
                model        = v["preferred_model"] or "—"
                updated_at   = v["updated_at"]
                accuracy     = v["test_accuracy"]
                prompt_id    = v["prompt_id"]
                exp_id       = v.get("mlflow_experiment_id")
                run_id_ml    = v.get("mlflow_run_id")
                prompt_text  = v.get("prompt_text", "")

                updated_str = (
                    updated_at.strftime("%Y-%m-%d") if hasattr(updated_at, "strftime") else str(updated_at)
                )
                acc_str = f"{accuracy:.1%}" if accuracy is not None else "—"

                vcols = st.columns([1, 2, 2, 2, 3])
                vcols[0].markdown(_version_badge(version), unsafe_allow_html=True)
                vcols[1].markdown(f'<span style="font-size:12px">{model}</span>', unsafe_allow_html=True)
                vcols[2].markdown(f'<span style="font-size:12px">{updated_str}</span>', unsafe_allow_html=True)

                # Accuracy + MLflow link
                if exp_id and run_id_ml:
                    mlflow_url = _MLFLOW_BASE.format(host=host, exp_id=exp_id, run_id=run_id_ml)
                    vcols[3].markdown(
                        f'<a href="{mlflow_url}" target="_blank" style="font-size:12px">'
                        f'{acc_str} ↗</a>',
                        unsafe_allow_html=True,
                    )
                else:
                    vcols[3].markdown(f'<span style="font-size:12px">{acc_str}</span>', unsafe_allow_html=True)

                with vcols[4]:
                    if is_active:
                        st.markdown(_active_badge(), unsafe_allow_html=True)
                    else:
                        # Check session state for pending test run for this prompt
                        state_key_run  = f"test_run_{prompt_id}"
                        state_key_done = f"test_done_{prompt_id}"

                        if st.session_state.get(state_key_done):
                            st.markdown(_pending_badge(), unsafe_allow_html=True)
                            if st.button("⬆ Promote", key=f"promote_{prompt_id}"):
                                try:
                                    lb_exec(
                                        "UPDATE docubricks_prod.schema_registry.extraction_prompts "
                                        "SET is_active = FALSE "
                                        "WHERE document_type = %s AND is_active = TRUE",
                                        (doc_type,),
                                    )
                                    lb_exec(
                                        "UPDATE docubricks_prod.schema_registry.extraction_prompts "
                                        "SET is_active = TRUE "
                                        "WHERE prompt_id = %s",
                                        (prompt_id,),
                                    )
                                    del st.session_state[state_key_done]
                                    st.success(f"v{version} promoted to active.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Promotion failed: {exc}")
                        elif st.session_state.get(state_key_run):
                            # Poll for completion
                            run_id_job = st.session_state[state_key_run]
                            status_info = _poll_test_harness(run_id_job)
                            state = status_info.get("state", "UNKNOWN")
                            result = status_info.get("result_state", "")
                            if state == "TERMINATED" and result == "SUCCESS":
                                st.session_state[state_key_done] = True
                                del st.session_state[state_key_run]
                                st.rerun()
                            elif state == "TERMINATED":
                                st.error(f"Test harness failed: {status_info.get('state_message','')}")
                                del st.session_state[state_key_run]
                            else:
                                st.markdown(
                                    f'<span style="font-size:11px;color:#6b7280">Testing… ({state})</span>',
                                    unsafe_allow_html=True,
                                )

                st.markdown('<hr style="margin:2px 0;border-color:#f3f4f6;">', unsafe_allow_html=True)

            # ── Edit section ───────────────────────────────────────────────────
            st.markdown("#### Create New Version")
            current_prompt = versions[0].get("prompt_text", "") if versions else ""
            current_model  = versions[0].get("preferred_model", _AVAILABLE_MODELS[0]) if versions else _AVAILABLE_MODELS[0]

            new_model = st.selectbox(
                "Preferred model",
                options=_AVAILABLE_MODELS,
                index=_AVAILABLE_MODELS.index(current_model) if current_model in _AVAILABLE_MODELS else 0,
                key=f"model_sel_{doc_type}",
            )

            new_prompt = st.text_area(
                "Prompt text",
                value=current_prompt,
                height=300,
                key=f"prompt_text_{doc_type}",
                help="Edit the extraction prompt. Saving creates a new version (inactive until test passes).",
            )

            save_col, _ = st.columns([1, 3])
            with save_col:
                if st.button("💾 Save new version", key=f"save_{doc_type}"):
                    next_version = (versions[0]["version"] + 1) if versions else 1
                    try:
                        result = lb_exec_returning(
                            """
                            INSERT INTO docubricks_prod.schema_registry.extraction_prompts
                                (document_type, vertical, version, is_active, preferred_model,
                                 prompt_text, updated_at)
                            VALUES (%s, %s, %s, FALSE, %s, %s, NOW())
                            RETURNING prompt_id
                            """,
                            (
                                doc_type,
                                versions[0].get("vertical", ""),
                                next_version,
                                new_model,
                                new_prompt,
                            ),
                        )
                        new_prompt_id = result["prompt_id"] if result else None

                        if new_prompt_id:
                            # Trigger test harness
                            run_id_job = _trigger_test_harness(doc_type, next_version)
                            st.session_state[f"test_run_{new_prompt_id}"] = run_id_job
                            st.success(
                                f"v{next_version} created (inactive). "
                                f"Test harness running — refresh to check status."
                            )
                            st.rerun()
                        else:
                            st.warning("Version inserted but prompt_id not returned.")
                    except Exception as exc:
                        st.error(f"Failed to save new version: {exc}")
