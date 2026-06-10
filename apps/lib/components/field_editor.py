"""
apps/lib/components/field_editor.py
-------------------------------------
Human-in-the-loop field review and correction UI.

Two public entry-points:

  field_editor(fields, confidence_scores, editable, skip_fields, schema_meta)
    → renders fields organised into tabs by section (or flat if no schema_meta)
    → returns {field: corrected_value} dict

  field_diff_view(original, corrected)
    → side-by-side diff of AI extraction vs human corrections (history page)
"""
from __future__ import annotations

import json
import datetime
from typing import Any

import streamlit as st
import pandas as pd

from .confidence_badge import confidence_badge

# ── Confidence thresholds ──────────────────────────────────────────────────────
_LOW_CONF  = 0.65   # below this → red, shown in Needs Review tab
_MED_CONF  = 0.85   # below this → amber highlight in section tabs

# ── Internal skip set ─────────────────────────────────────────────────────────
_DEFAULT_SKIP: frozenset[str] = frozenset({
    "document_id", "tenant_id", "extracted_at",
    "avg_confidence_score", "field_confidences",
    "extraction_result", "extracted_json",
})


# ── Date helpers ───────────────────────────────────────────────────────────────

def _parse_date(value: Any) -> datetime.date | None:
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str) and value.strip():
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


# ── Per-field widget renderers ─────────────────────────────────────────────────

def _render_field(
    field: str,
    value: Any,
    meta: dict,
    conf: float | None,
    editable: bool,
    form_key_prefix: str = "",
) -> Any:
    """
    Render one field row (label + confidence badge + widget).
    Returns the (possibly corrected) value in its native Python type.
    String coercion for the corrected-dict happens at the call-site.
    """
    display_type = meta.get("display_type", "text")
    is_low  = conf is not None and conf < _LOW_CONF
    is_med  = conf is not None and _LOW_CONF <= conf < _MED_CONF

    # ── Confidence highlight banner ────────────────────────────────────────────
    if is_low:
        st.markdown(
            '<div style="background:#FCE8E6;border-left:3px solid #A32D2D;'
            'padding:3px 8px;border-radius:0 4px 4px 0;margin-bottom:2px;">'
            '<span style="font-size:11px;color:#A32D2D;font-weight:600">'
            '⚠ Low confidence — verify carefully</span></div>',
            unsafe_allow_html=True,
        )
    elif is_med:
        st.markdown(
            '<div style="background:#FEF7E0;border-left:3px solid #B06000;'
            'padding:3px 8px;border-radius:0 4px 4px 0;margin-bottom:2px;">'
            '<span style="font-size:11px;color:#B06000;font-weight:600">'
            '~ Review recommended</span></div>',
            unsafe_allow_html=True,
        )

    col_label, col_input = st.columns([1, 2])

    # ── Label + badge ──────────────────────────────────────────────────────────
    with col_label:
        # Build display label with type hint prefix/suffix
        label_txt = field.replace("_", " ").title()
        if display_type == "currency":
            label_txt = f"$ {label_txt}"
        elif display_type == "percent":
            label_txt = f"% {label_txt}"

        st.markdown(
            f'<p style="font-size:12px;font-weight:500;color:#374151;'
            f'padding-top:8px;margin:0">{label_txt}</p>',
            unsafe_allow_html=True,
        )
        if conf is not None:
            confidence_badge(conf)

    # ── Input widget ───────────────────────────────────────────────────────────
    with col_input:
        widget_key = f"{form_key_prefix}_{field}"

        if not editable:
            # Read-only rendering
            str_val = str(value) if value is not None else ""
            st.markdown(
                f'<p style="font-size:13px;color:#111827;padding-top:6px;margin:0">'
                f'{str_val or "<em style=\'color:#9ca3af\'>—</em>"}</p>',
                unsafe_allow_html=True,
            )
            return str_val

        # ── date ──────────────────────────────────────────────────────────────
        if display_type == "date":
            parsed = _parse_date(value)
            result = st.date_input(
                label=field,
                value=parsed,
                key=widget_key,
                label_visibility="collapsed",
            )
            return result.isoformat() if result else ""

        # ── boolean ───────────────────────────────────────────────────────────
        if display_type == "boolean":
            if isinstance(value, bool):
                bool_val = value
            else:
                bool_val = str(value).lower() in ("true", "yes", "1")
            result = st.checkbox(
                label=field,
                value=bool_val,
                key=widget_key,
                label_visibility="collapsed",
            )
            return str(result)

        # ── currency / percent / decimal ──────────────────────────────────────
        if display_type in ("currency", "percent", "decimal"):
            try:
                num_val = float(value) if value not in (None, "", "None") else 0.0
            except (ValueError, TypeError):
                num_val = 0.0
            result = st.number_input(
                label=field,
                value=num_val,
                format="%.2f",
                step=0.01,
                key=widget_key,
                label_visibility="collapsed",
            )
            return str(result)

        # ── integer ───────────────────────────────────────────────────────────
        if display_type == "integer":
            try:
                int_val = int(float(value)) if value not in (None, "", "None") else 0
            except (ValueError, TypeError):
                int_val = 0
            result = st.number_input(
                label=field,
                value=int_val,
                step=1,
                key=widget_key,
                label_visibility="collapsed",
            )
            return str(int(result))

        # ── table (array of dicts) ────────────────────────────────────────────
        if display_type == "table":
            return _render_table_field(field, value, meta, widget_key, editable)

        # ── textarea ──────────────────────────────────────────────────────────
        if display_type == "textarea":
            str_val = str(value) if value is not None else ""
            result = st.text_area(
                label=field,
                value=str_val,
                key=widget_key,
                label_visibility="collapsed",
                height=80,
            )
            return result

        # ── text (default) ────────────────────────────────────────────────────
        str_val = str(value) if value is not None else ""
        result = st.text_input(
            label=field,
            value=str_val,
            key=widget_key,
            label_visibility="collapsed",
        )
        return result


def _render_table_field(
    field: str,
    value: Any,
    meta: dict,
    widget_key: str,
    editable: bool,
) -> str:
    """
    Render an array-of-dicts field as st.data_editor.
    Returns a JSON string of the (possibly edited) list.
    """
    columns = meta.get("table_columns", [])
    col_names = [c["name"] for c in columns]

    # Parse existing value
    rows: list[dict] = []
    if isinstance(value, list):
        rows = value
    elif isinstance(value, str) and value.strip().startswith("["):
        try:
            rows = json.loads(value)
        except json.JSONDecodeError:
            rows = []

    # Build seed DataFrame with correct columns
    if rows:
        df = pd.DataFrame(rows)
        # Ensure all defined columns exist
        for col in col_names:
            if col not in df.columns:
                df[col] = None
        df = df[col_names]   # reorder to schema order
    else:
        df = pd.DataFrame(columns=col_names)

    # Build column config for st.data_editor
    col_config: dict = {}
    for c in columns:
        if c["type"] == "currency":
            col_config[c["name"]] = st.column_config.NumberColumn(
                c["name"].replace("_", " ").title(),
                format="$%.2f",
                step=0.01,
            )
        elif c["type"] in ("decimal",):
            col_config[c["name"]] = st.column_config.NumberColumn(
                c["name"].replace("_", " ").title(),
                format="%.4f",
                step=0.0001,
            )
        elif c["type"] == "integer":
            col_config[c["name"]] = st.column_config.NumberColumn(
                c["name"].replace("_", " ").title(),
                step=1,
                format="%d",
            )
        else:
            col_config[c["name"]] = st.column_config.TextColumn(
                c["name"].replace("_", " ").title()
            )

    if not col_names:
        # No column spec — show generic editor
        col_config = None

    edited_df = st.data_editor(
        df,
        key=widget_key,
        use_container_width=True,
        num_rows="dynamic" if editable else "fixed",
        disabled=not editable,
        column_config=col_config or {},
        hide_index=True,
    )

    return edited_df.to_json(orient="records")


# ── Section-tab renderer ───────────────────────────────────────────────────────

def _section_tab_label(section: dict, fields: dict, conf_scores: dict) -> str:
    """Build a tab label with field count and optional ⚠ warning count."""
    present = [f for f in section["fields"] if f in fields and not f.startswith("_")]
    low_count = sum(
        1 for f in present
        if conf_scores.get(f) is not None and conf_scores[f] < _LOW_CONF
    )
    label = f"{section['label']} ({len(present)})"
    if low_count:
        label += f" ⚠{low_count}"
    return label


def _render_section(
    section_fields: list[str],
    fields: dict,
    field_meta: dict,
    conf_scores: dict,
    editable: bool,
    form_key_prefix: str,
    corrected: dict,
    skip: frozenset[str],
) -> None:
    """Render all fields belonging to one section into `corrected`."""
    any_rendered = False
    for field in section_fields:
        if field.startswith("_") or field in skip or field not in fields:
            if field in fields:
                corrected[field] = str(fields[field]) if fields[field] is not None else ""
            continue
        conf = conf_scores.get(field)
        corrected[field] = _render_field(
            field, fields[field], field_meta.get(field, {}),
            conf, editable, form_key_prefix,
        )
        any_rendered = True

    if not any_rendered:
        st.caption("No extracted fields in this section.")


# ── Public: field_editor ───────────────────────────────────────────────────────

def field_editor(
    fields: dict[str, Any],
    confidence_scores: dict[str, float] | None = None,
    editable: bool = True,
    skip_fields: set[str] | None = None,
    schema_meta: dict | None = None,
) -> dict[str, str]:
    """
    Render fields for human review and optional correction.

    Parameters
    ----------
    fields:
        {field_name: extracted_value}
    confidence_scores:
        {field_name: 0.0–1.0}
    editable:
        False → read-only (used in history diffs)
    skip_fields:
        Additional field names to suppress.
    schema_meta:
        From schema_sections.get_schema_meta(doc_type).
        If provided: renders tabs per section + type-aware widgets.
        If None: falls back to flat text-input list (backward-compat).

    Returns
    -------
    dict[str, str]  — corrected field values (all stringified).
    """
    conf_scores: dict[str, float] = confidence_scores or {}
    skip: frozenset[str] = _DEFAULT_SKIP | frozenset(skip_fields or set())
    corrected: dict[str, str] = {}

    # ── Flat fallback (no schema_meta) ────────────────────────────────────────
    if not schema_meta or not schema_meta.get("sections"):
        for field, value in fields.items():
            if field.startswith("_") or field in skip:
                corrected[field] = str(value) if value is not None else ""
                continue
            conf = conf_scores.get(field)
            corrected[field] = _render_field(
                field, value, {}, conf, editable, "flat",
            )
        return corrected

    # ── Section-tab layout ────────────────────────────────────────────────────
    sections   = schema_meta["sections"]
    field_meta = schema_meta.get("field_meta", {})

    # Identify fields not covered by any section (render in an "Other" bucket)
    covered: set[str] = {f for s in sections for f in s["fields"]}
    uncovered = [
        f for f in fields
        if f not in covered and not f.startswith("_") and f not in skip
    ]

    # Build low-confidence bucket
    low_conf_fields = sorted(
        [
            f for f in fields
            if f not in skip
            and not f.startswith("_")
            and conf_scores.get(f, 1.0) < _LOW_CONF
        ],
        key=lambda f: conf_scores.get(f, 1.0),
    )

    # ── Build tab labels ───────────────────────────────────────────────────────
    tab_labels: list[str] = []
    if low_conf_fields:
        tab_labels.append(f"⚠ Needs Review ({len(low_conf_fields)})")

    for s in sections:
        tab_labels.append(_section_tab_label(s, fields, conf_scores))

    if uncovered:
        tab_labels.append(f"Other ({len(uncovered)})")

    tabs = st.tabs(tab_labels)
    tab_idx = 0

    # ── Needs Review tab ───────────────────────────────────────────────────────
    if low_conf_fields:
        with tabs[tab_idx]:
            st.caption("Fields with confidence below 65% — sorted lowest first.")
            for field in low_conf_fields:
                conf = conf_scores.get(field)
                corrected[field] = _render_field(
                    field, fields[field], field_meta.get(field, {}),
                    conf, editable, "nr",
                )
        tab_idx += 1

    # ── Section tabs ───────────────────────────────────────────────────────────
    for section in sections:
        with tabs[tab_idx]:
            _render_section(
                section["fields"], fields, field_meta,
                conf_scores, editable, f"s_{section['id']}",
                corrected, skip,
            )
        tab_idx += 1

    # ── Other tab ──────────────────────────────────────────────────────────────
    if uncovered:
        with tabs[tab_idx]:
            st.caption("Fields not mapped to a section.")
            for field in uncovered:
                conf = conf_scores.get(field)
                corrected[field] = _render_field(
                    field, fields[field], field_meta.get(field, {}),
                    conf, editable, "oth",
                )

    # Propagate skip-fields so corrected dict stays complete
    for field, value in fields.items():
        if field.startswith("_") or field in skip:
            corrected.setdefault(field, str(value) if value is not None else "")

    return corrected


# ── Public: field_diff_view ────────────────────────────────────────────────────

def field_diff_view(original: dict, corrected: dict) -> None:
    """Side-by-side diff showing only fields the reviewer changed."""
    changed = {
        k: (original.get(k), corrected.get(k))
        for k in corrected
        if str(original.get(k, "")) != str(corrected.get(k, ""))
    }

    if not changed:
        st.info("No fields were changed.")
        return

    st.markdown(f"**{len(changed)} field{'s' if len(changed) != 1 else ''} corrected:**")

    col_f, col_b, col_a = st.columns([1, 1.5, 1.5])
    col_f.markdown("**Field**")
    col_b.markdown("**Before (AI)**")
    col_a.markdown("**After (Human)**")
    st.divider()

    for field, (before, after) in changed.items():
        cf, cb, ca = st.columns([1, 1.5, 1.5])
        cf.markdown(
            f'<span style="font-size:12px;font-weight:500">'
            f'{field.replace("_", " ").title()}</span>',
            unsafe_allow_html=True,
        )
        cb.markdown(
            f'<span style="font-size:12px;color:#dc2626;'
            f'text-decoration:line-through">{before or "—"}</span>',
            unsafe_allow_html=True,
        )
        ca.markdown(
            f'<span style="font-size:12px;color:#16a34a">{after or "—"}</span>',
            unsafe_allow_html=True,
        )
