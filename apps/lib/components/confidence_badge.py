"""
apps/lib/components/confidence_badge.py
----------------------------------------
Color-coded confidence score indicators.

``confidence_badge``  — inline HTML pill with emoji
``confidence_bar``    — horizontal bar chart of per-field scores

Thresholds
~~~~~~~~~~
≥ 0.85   green   high confidence
0.65–0.85  amber  medium / borderline
< 0.65   red    low confidence — triggers review queue
None     gray   score not available
"""
from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Threshold configuration
# ---------------------------------------------------------------------------

# Each entry: (min_score, css_class, emoji, label)
_TIERS: list[tuple[float, str, str, str]] = [
    (0.85, "db-badge-green", "●", "High"),
    (0.65, "db-badge-amber", "●", "Medium"),
    (0.0,  "db-badge-red",   "●", "Low"),
]


def _tier_for(score: float) -> tuple[str, str, str]:
    """Return (css_class, emoji, tier_label) for a numeric confidence score."""
    for threshold, css, emoji, label in _TIERS:
        if score >= threshold:
            return css, emoji, label
    return "db-badge-red", "●", "Low"


# ---------------------------------------------------------------------------
# Public components
# ---------------------------------------------------------------------------

def confidence_badge(score: float | None, label: str = "Confidence") -> None:
    """
    Render a colored pill badge showing a confidence score.

    Parameters
    ----------
    score:  confidence value in [0, 1], or ``None`` if unavailable
    label:  prefix text displayed before the score (default: "Confidence")
    """
    if score is None:
        st.markdown(
            f'<span class="db-badge db-badge-gray">● {label}: —</span>',
            unsafe_allow_html=True,
        )
        return

    css, emoji, tier = _tier_for(score)
    pct = f"{score:.0%}"
    st.markdown(
        f'<span class="db-badge {css}">{emoji} {label}: {pct}</span>',
        unsafe_allow_html=True,
    )


def confidence_bar(field_scores: dict[str, float]) -> None:
    """
    Render a horizontal bar chart of per-field confidence scores.

    Bars are sorted in ascending confidence order (lowest at the top) so
    reviewers see the most problematic fields first.  Bar colors follow the
    same thresholds as :func:`confidence_badge`.

    Parameters
    ----------
    field_scores:
        Mapping of field name → confidence score in [0, 1].
    """
    if not field_scores:
        st.caption("No field confidence scores available.")
        return

    import pandas as pd

    # Sort ascending (lowest confidence first)
    sorted_items = sorted(field_scores.items(), key=lambda kv: kv[1])
    fields = [k for k, _ in sorted_items]
    scores = [v for _, v in sorted_items]

    df = pd.DataFrame({"Field": fields, "Confidence": scores})

    # Assign bar color per row using thresholds
    def _color(v: float) -> str:
        if v >= 0.85:
            return "#0F6E56"   # teal / green
        if v >= 0.65:
            return "#B06000"   # amber
        return "#A32D2D"       # red

    colors = [_color(v) for v in scores]

    # Render using Streamlit's bar_chart but we need per-bar colors,
    # so we fall back to a Matplotlib figure when multiple colors are needed.
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, max(2, len(fields) * 0.4)))
        bars = ax.barh(fields, scores, color=colors)
        ax.set_xlim(0, 1)
        ax.set_xlabel("Confidence", fontsize=9)
        ax.tick_params(axis="y", labelsize=8)
        ax.axvline(0.85, color="#0F6E56", linewidth=0.8, linestyle="--", alpha=0.6)
        ax.axvline(0.65, color="#B06000", linewidth=0.8, linestyle="--", alpha=0.6)
        ax.set_facecolor("#F0F4F9")
        fig.patch.set_facecolor("#F0F4F9")
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
    except ImportError:
        # Matplotlib not available — fall back to native bar_chart (single color)
        st.bar_chart(
            df.set_index("Field"),
            y="Confidence",
            height=max(150, len(fields) * 30),
        )
