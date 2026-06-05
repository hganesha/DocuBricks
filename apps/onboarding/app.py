"""Streamlit entrypoint for the DocuBricks onboarding Databricks App."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from apps.onboarding.core.state import (
    advance_screen_state,
    init_state,
    load_state,
    save_state,
)


STATE_PATH = Path(".docubricks_onboarding_state.json")


def _load_or_create_state():
    state = load_state(str(STATE_PATH))
    if state is None:
        state = init_state()
        save_state(state, str(STATE_PATH))
    return state


def main() -> None:
    st.set_page_config(
        page_title="DocuBricks Onboarding",
        page_icon="DB",
        layout="centered",
    )
    state = _load_or_create_state()

    st.title("DocuBricks Onboarding")
    st.caption("Self-service workspace provisioning and first-document validation.")

    screen_states = [
        "WELCOME",
        "PROJECT",
        "VERTICAL",
        "WORKSPACE",
        "RESOURCES",
        "REVIEW",
        "DEPLOYING",
        "FIRST_DOC",
        "COMPLETE",
    ]
    st.progress((screen_states.index(state.state) + 1) / len(screen_states))
    st.subheader(state.state.replace("_", " ").title())

    with st.expander("Deployment steps", expanded=True):
        for step in state.deploy_log:
            st.write(f"{step.label}: {step.status}")

    if st.button("Advance demo state", type="primary"):
        advance_screen_state(state)
        save_state(state, str(STATE_PATH))
        st.rerun()


if __name__ == "__main__":
    main()
