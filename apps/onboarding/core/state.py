"""Persistent state helpers for the DocuBricks onboarding app."""

from __future__ import annotations

import dataclasses
import json
import os
import uuid
from collections.abc import Callable
from datetime import datetime, timezone


DEPLOY_STEPS = [
    "verify_workspace",
    "create_service_principal",
    "grant_sp_permissions",
    "create_uc_schemas",
    "upload_schema_registry",
    "create_dlt_pipeline",
    "provision_lakebase",
    "migrate_state_to_lakebase",
    "create_genie_workspace",
    "create_vector_index",
    "deploy_portal_app",
    "deploy_review_app",
    "deploy_admin_app",
    "write_secrets",
    "run_health_check",
]

SCREEN_STATES = [
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


class ProvisioningError(Exception):
    """Expected provisioning failure that should be recorded on the step."""


@dataclasses.dataclass
class DeployStep:
    key: str
    label: str
    status: str = "pending"
    started_at: str | None = None
    elapsed_ms: int | None = None
    error: str | None = None


@dataclasses.dataclass
class OnboardingState:
    onboarding_id: str
    state: str
    started_at: str
    updated_at: str
    deploy_log: list[DeployStep] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "onboarding_id": self.onboarding_id,
            "state": self.state,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "deploy_log": [dataclasses.asdict(step) for step in self.deploy_log],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "OnboardingState":
        deploy_log = [DeployStep(**step) for step in payload.get("deploy_log", [])]
        return cls(
            onboarding_id=payload["onboarding_id"],
            state=payload["state"],
            started_at=payload["started_at"],
            updated_at=payload["updated_at"],
            deploy_log=deploy_log,
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_state() -> OnboardingState:
    now = _now()
    return OnboardingState(
        onboarding_id=str(uuid.uuid4()),
        state="WELCOME",
        started_at=now,
        updated_at=now,
        deploy_log=[
            DeployStep(key=key, label=key.replace("_", " ").title())
            for key in DEPLOY_STEPS
        ],
    )


def save_state(state: OnboardingState, path: str) -> None:
    state.updated_at = _now()
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state.to_dict(), handle, indent=2)


def load_state(path: str) -> OnboardingState | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return OnboardingState.from_dict(json.load(handle))


def advance_screen_state(state: OnboardingState) -> None:
    current_index = SCREEN_STATES.index(state.state)
    if current_index < len(SCREEN_STATES) - 1:
        state.state = SCREEN_STATES[current_index + 1]
        state.updated_at = _now()


def get_step(state: OnboardingState, key: str) -> DeployStep:
    for step in state.deploy_log:
        if step.key == key:
            return step
    raise KeyError(f"Step {key!r} not found in deploy_log")


def mark_running(step: DeployStep) -> None:
    step.status = "running"
    step.started_at = _now()
    step.error = None


def mark_complete(step: DeployStep) -> None:
    step.status = "complete"
    step.elapsed_ms = 100
    step.error = None


def mark_failed(step: DeployStep, error: str) -> None:
    step.status = "failed"
    step.error = error


def provision_step(
    state: OnboardingState,
    step_key: str,
    fn: Callable,
    *args,
    **kwargs,
) -> None:
    step = get_step(state, step_key)
    if step.status == "complete":
        return

    mark_running(step)
    try:
        fn(*args, **kwargs)
        mark_complete(step)
    except ProvisioningError as exc:
        mark_failed(step, str(exc))
        raise
    finally:
        state.updated_at = _now()

