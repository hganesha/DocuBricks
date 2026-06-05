"""
apps/lib/components/field_editor.py
-------------------------------------
Editable field grid for the Review & Correction UI.

Shows extracted fields alongside their confidence scores.
Low-confidence fields are highlighted so reviewers know where to focus.
"""
from __future__ import annotations

import streamlit as st
from .confidence_badge import confidence_badge

_LOW_CONF = 0.65
_MED_CONF = 0.85


def field_editor(
    fields: dict[str, any],
    confidence_scores: dict[str, float] | None = None,
    editable: bool = True,
    skip_fields: set[str] | None = None,
) -> dict[str, str]:
    """
    Render an editable grid of extracted fields.

    Parameters
    ----------
    fields:
        {field_name: value} — the extracted values to display.
    confidence_scores:
        Optional {field_name: 0.0-1.0} — shown as badges next to each field.
    editable:
        If False, renders as read-only text (for review history display).
    skip_fields:
        Field names to exclude from rendering (e.g. internal IDs).

    Returns
    -------
    dict[str, str]
        The (possibly corrected) field values.  Keys match input `fields`.
    """
    skip = skip_fields or {"document_id", "tenant_id", "extracted_at",
                           "avg_confidence_score", "field_confidences",
                           "extraction_result", "extracted_json"}
    corrected: dict[str, str] = {}

    for field, value in fields.items():
        if field.startswith("_") or field in skip:
            corrected[field] = str(value) if value is not None else ""
            continue

        conf = confidence_scores.get(field) if confidence_scores else None
        is_low = conf is not None and conf < _LOW_CONF

        # Amber highlight for low-confidence fields
        if is_low:
            st.markdown(
                f'<div style="background:#fef3c7;border-left:3px solid #f59e0b;'
                f'padding:4px 8px;border-radius:0 4px 4px 0;margin-bottom:2px;">'
                f'<span style="font-size:11px;color:#92400e;font-weight:500">'
                f'⚠ Low confidence — review carefully</span></div>',
                unsafe_allow_html=True,
            )

        col_label, col_input = st.columns([1, 2])
        with col_label:
            st.markdown(
                f'<p style="font-size:12px;font-weight:500;color:#374151;'
                f'padding-top:8px;margin:0">{field.replace("_", " ").title()}</p>',
                unsafe_allow_html=True,
            )
            if conf is not None:
                confidence_badge(conf)

        with col_input:
            str_value = str(value) if value is not None else ""
            if editable:
                corrected[field] = st.text_input(
                    label=field,
                    value=str_value,
                    key=f"field_{field}",
                    label_visibility="collapsed",
                )
            else:
                st.markdown(
                    f'<p style="font-size:13px;color:#111827;padding-top:6px;margin:0">'
                    f'{str_value or "<em style=\'color:#9ca3af\'>—</em>"}</p>',
                    unsafe_allow_html=True,
                )
                corrected[field] = str_value

    return corrected


def field_diff_view(original: dict, corrected: dict) -> None:
    """
    Side-by-side diff of original extracted values vs human corrections.
    Only renders fields that actually changed.
    """
    changed = {
        k: (original.get(k), corrected.get(k))
        for k in corrected
        if str(original.get(k, "")) != str(corrected.get(k, ""))
    }

    if not changed:
        st.info("No fields were changed.")
        return

    st.markdown(
        f"**{len(changed)} field{'s' if len(changed) != 1 else ''} corrected:**"
    )
    col_field, col_before, col_after = st.columns([1, 1.5, 1.5])
    col_field.markdown("**Field**")
    col_before.markdown("**Before**")
    col_after.markdown("**After**")
    st.divider()

    for field, (before, after) in changed.items():
        col_f, col_b, col_a = st.columns([1, 1.5, 1.5])
        col_f.markdown(
            f'<span style="font-size:12px;font-weight:500">'
            f'{field.replace("_"," ").title()}</span>',
            unsafe_allow_html=True,
        )
        col_b.markdown(
            f'<span style="font-size:12px;color:#dc2626;'
            f'text-decoration:line-through">{before or "—"}</span>',
            unsafe_allow_html=True,
        )
        col_a.markdown(
            f'<span style="font-size:12px;color:#16a34a">{after or "—"}</span>',
            unsafe_allow_html=True,
        )
