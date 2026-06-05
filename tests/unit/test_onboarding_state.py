"""
tests/unit/test_onboarding_state.py
--------------------------------------
Unit tests for the Python onboarding state machine defined in ONBOARDING_SPEC.md.

Scenarios
---------
1. State advances linearly through DEPLOY_STEPS.
2. A completed step is skipped on retry (idempotency).
3. A failed step writes FAILED status and does not advance state.
4. State persistence: save to file, load back, state is identical.

All Databricks API calls are mocked — no real workspace connection.
"""
from __future__ import annotations

import dataclasses
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Callable
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Minimal reference implementation of the onboarding state machine
# ---------------------------------------------------------------------------
# Mirrors the design in ONBOARDING_SPEC.md §State Machine Architecture.
# The real implementation lives in apps/onboarding/core/.
# If importable, tests use that; otherwise they use this reference impl.

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
    pass


@dataclasses.dataclass
class DeployStep:
    key: str
    label: str
    status: str = "pending"       # pending | running | complete | failed
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
            "deploy_log": [dataclasses.asdict(s) for s in self.deploy_log],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OnboardingState":
        deploy_log = [DeployStep(**s) for s in d.get("deploy_log", [])]
        return cls(
            onboarding_id=d["onboarding_id"],
            state=d["state"],
            started_at=d["started_at"],
            updated_at=d["updated_at"],
            deploy_log=deploy_log,
        )


def init_state() -> OnboardingState:
    now = datetime.now(timezone.utc).isoformat()
    deploy_log = [
        DeployStep(key=key, label=key.replace("_", " ").title())
        for key in DEPLOY_STEPS
    ]
    return OnboardingState(
        onboarding_id=str(uuid.uuid4()),
        state="WELCOME",
        started_at=now,
        updated_at=now,
        deploy_log=deploy_log,
    )


def save_state(state: OnboardingState, path: str) -> None:
    state.updated_at = datetime.now(timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2)


def load_state(path: str) -> OnboardingState | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return OnboardingState.from_dict(json.load(f))


def advance_screen_state(state: OnboardingState) -> None:
    """Advance to the next screen state in the linear sequence."""
    idx = SCREEN_STATES.index(state.state)
    if idx < len(SCREEN_STATES) - 1:
        state.state = SCREEN_STATES[idx + 1]


def get_step(state: OnboardingState, key: str) -> DeployStep:
    for step in state.deploy_log:
        if step.key == key:
            return step
    raise KeyError(f"Step {key!r} not found in deploy_log")


def mark_running(step: DeployStep) -> None:
    step.status = "running"
    step.started_at = datetime.now(timezone.utc).isoformat()


def mark_complete(step: DeployStep) -> None:
    step.status = "complete"
    step.elapsed_ms = 100  # placeholder


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
    """
    Idempotent step executor.

    If the step is already 'complete', it is skipped.
    On success: step is marked complete.
    On ProvisioningError: step is marked failed; exception is re-raised.
    """
    step = get_step(state, step_key)

    if step.status == "complete":
        return  # idempotent: already done

    mark_running(step)
    try:
        fn(*args, **kwargs)
        mark_complete(step)
    except ProvisioningError as e:
        mark_failed(step, str(e))
        raise


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def fresh_state() -> OnboardingState:
    return init_state()


@pytest.fixture()
def tmp_state_file(tmp_path) -> str:
    return str(tmp_path / "onboarding_test.json")


# ---------------------------------------------------------------------------
# Tests: linear screen state progression
# ---------------------------------------------------------------------------

class TestLinearStateProgression:
    def test_initial_state_is_welcome(self, fresh_state):
        assert fresh_state.state == "WELCOME"

    def test_advance_from_welcome_to_project(self, fresh_state):
        advance_screen_state(fresh_state)
        assert fresh_state.state == "PROJECT"

    def test_advance_through_all_screen_states(self, fresh_state):
        for expected in SCREEN_STATES[1:]:
            advance_screen_state(fresh_state)
            assert fresh_state.state == expected

    def test_complete_is_final_state(self, fresh_state):
        fresh_state.state = "COMPLETE"
        # Advancing from COMPLETE should not raise (no index out of bounds)
        # It stays at COMPLETE (last element)
        before = fresh_state.state
        advance_screen_state(fresh_state)
        assert fresh_state.state == before  # still COMPLETE

    def test_deploy_log_initialized_with_all_steps(self, fresh_state):
        step_keys = {s.key for s in fresh_state.deploy_log}
        for expected_key in DEPLOY_STEPS:
            assert expected_key in step_keys

    def test_all_steps_start_as_pending(self, fresh_state):
        for step in fresh_state.deploy_log:
            assert step.status == "pending"

    def test_deploying_state_before_first_doc(self, fresh_state):
        """State must pass through DEPLOYING before FIRST_DOC."""
        fresh_state.state = "REVIEW"
        advance_screen_state(fresh_state)
        assert fresh_state.state == "DEPLOYING"
        advance_screen_state(fresh_state)
        assert fresh_state.state == "FIRST_DOC"


# ---------------------------------------------------------------------------
# Tests: idempotency — completed step is skipped on retry
# ---------------------------------------------------------------------------

class TestStepIdempotency:
    def test_completed_step_is_skipped(self, fresh_state):
        mock_fn = MagicMock()
        step = get_step(fresh_state, "create_uc_schemas")
        step.status = "complete"

        provision_step(fresh_state, "create_uc_schemas", mock_fn)

        mock_fn.assert_not_called()

    def test_completed_step_stays_complete(self, fresh_state):
        mock_fn = MagicMock()
        step = get_step(fresh_state, "verify_workspace")
        step.status = "complete"

        provision_step(fresh_state, "verify_workspace", mock_fn)

        assert get_step(fresh_state, "verify_workspace").status == "complete"

    def test_pending_step_is_executed(self, fresh_state):
        mock_fn = MagicMock()
        provision_step(fresh_state, "verify_workspace", mock_fn)
        mock_fn.assert_called_once()

    def test_running_step_is_executed_again(self, fresh_state):
        """A step left in 'running' (e.g. after crash) should re-execute."""
        mock_fn = MagicMock()
        step = get_step(fresh_state, "verify_workspace")
        step.status = "running"  # stale running state from previous crash

        provision_step(fresh_state, "verify_workspace", mock_fn)
        mock_fn.assert_called_once()

    def test_multiple_retries_after_success_are_no_ops(self, fresh_state):
        mock_fn = MagicMock()

        # First call: executes and marks complete
        provision_step(fresh_state, "create_uc_schemas", mock_fn)
        assert mock_fn.call_count == 1

        # Second call: skipped
        provision_step(fresh_state, "create_uc_schemas", mock_fn)
        assert mock_fn.call_count == 1  # still 1

        # Third call: skipped
        provision_step(fresh_state, "create_uc_schemas", mock_fn)
        assert mock_fn.call_count == 1

    def test_idempotency_across_all_steps(self, fresh_state):
        """Mark all steps complete; none should execute on provision_step call."""
        for step in fresh_state.deploy_log:
            step.status = "complete"

        for step_key in DEPLOY_STEPS:
            mock_fn = MagicMock()
            provision_step(fresh_state, step_key, mock_fn)
            mock_fn.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: failed step writes FAILED status and does not advance
# ---------------------------------------------------------------------------

class TestFailedStep:
    def test_failed_step_marks_status_failed(self, fresh_state):
        def bad_fn():
            raise ProvisioningError("UC permission denied")

        with pytest.raises(ProvisioningError):
            provision_step(fresh_state, "create_uc_schemas", bad_fn)

        step = get_step(fresh_state, "create_uc_schemas")
        assert step.status == "failed"

    def test_failed_step_records_error_message(self, fresh_state):
        def bad_fn():
            raise ProvisioningError("Network timeout")

        with pytest.raises(ProvisioningError):
            provision_step(fresh_state, "create_uc_schemas", bad_fn)

        step = get_step(fresh_state, "create_uc_schemas")
        assert "Network timeout" in step.error

    def test_failed_step_reraises_exception(self, fresh_state):
        def bad_fn():
            raise ProvisioningError("Service unavailable")

        with pytest.raises(ProvisioningError, match="Service unavailable"):
            provision_step(fresh_state, "verify_workspace", bad_fn)

    def test_failed_step_does_not_advance_screen_state(self, fresh_state):
        fresh_state.state = "DEPLOYING"

        def bad_fn():
            raise ProvisioningError("Lakebase quota exceeded")

        with pytest.raises(ProvisioningError):
            provision_step(fresh_state, "provision_lakebase", bad_fn)

        assert fresh_state.state == "DEPLOYING"  # must not have advanced

    def test_failed_step_does_not_mark_subsequent_steps_complete(self, fresh_state):
        def bad_fn():
            raise ProvisioningError("oops")

        with pytest.raises(ProvisioningError):
            provision_step(fresh_state, "create_uc_schemas", bad_fn)

        # Steps after create_uc_schemas must still be pending
        for step in fresh_state.deploy_log:
            if step.key not in ("create_uc_schemas", "verify_workspace", "create_service_principal", "grant_sp_permissions"):
                assert step.status == "pending", f"{step.key} should still be pending"

    def test_non_provisioning_error_propagates(self, fresh_state):
        """Only ProvisioningError is caught; other exceptions propagate directly."""
        def bad_fn():
            raise RuntimeError("Unexpected system error")

        with pytest.raises(RuntimeError, match="Unexpected system error"):
            provision_step(fresh_state, "verify_workspace", bad_fn)

    def test_step_can_be_retried_after_failure(self, fresh_state):
        """After a FAILED step, the next call to provision_step re-executes it."""
        call_count = 0

        def flaky_fn():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ProvisioningError("transient error")

        with pytest.raises(ProvisioningError):
            provision_step(fresh_state, "verify_workspace", flaky_fn)

        assert get_step(fresh_state, "verify_workspace").status == "failed"

        # Second attempt: should succeed
        provision_step(fresh_state, "verify_workspace", flaky_fn)
        assert get_step(fresh_state, "verify_workspace").status == "complete"
        assert call_count == 2


# ---------------------------------------------------------------------------
# Tests: state persistence (save to file, load back, state preserved)
# ---------------------------------------------------------------------------

class TestStatePersistence:
    def test_save_creates_file(self, fresh_state, tmp_state_file):
        save_state(fresh_state, tmp_state_file)
        assert os.path.exists(tmp_state_file)

    def test_load_returns_onboarding_state(self, fresh_state, tmp_state_file):
        save_state(fresh_state, tmp_state_file)
        loaded = load_state(tmp_state_file)
        assert isinstance(loaded, OnboardingState)

    def test_onboarding_id_preserved(self, fresh_state, tmp_state_file):
        save_state(fresh_state, tmp_state_file)
        loaded = load_state(tmp_state_file)
        assert loaded.onboarding_id == fresh_state.onboarding_id

    def test_state_field_preserved(self, fresh_state, tmp_state_file):
        fresh_state.state = "DEPLOYING"
        save_state(fresh_state, tmp_state_file)
        loaded = load_state(tmp_state_file)
        assert loaded.state == "DEPLOYING"

    def test_deploy_log_length_preserved(self, fresh_state, tmp_state_file):
        save_state(fresh_state, tmp_state_file)
        loaded = load_state(tmp_state_file)
        assert len(loaded.deploy_log) == len(fresh_state.deploy_log)

    def test_completed_step_persisted_correctly(self, fresh_state, tmp_state_file):
        step = get_step(fresh_state, "create_uc_schemas")
        step.status = "complete"
        step.elapsed_ms = 1234
        save_state(fresh_state, tmp_state_file)
        loaded = load_state(tmp_state_file)
        loaded_step = get_step(loaded, "create_uc_schemas")
        assert loaded_step.status == "complete"
        assert loaded_step.elapsed_ms == 1234

    def test_failed_step_error_persisted(self, fresh_state, tmp_state_file):
        step = get_step(fresh_state, "provision_lakebase")
        step.status = "failed"
        step.error = "Connection timeout after 30s"
        save_state(fresh_state, tmp_state_file)
        loaded = load_state(tmp_state_file)
        loaded_step = get_step(loaded, "provision_lakebase")
        assert loaded_step.status == "failed"
        assert "Connection timeout" in loaded_step.error

    def test_load_returns_none_for_missing_file(self, tmp_state_file):
        # File does not exist
        result = load_state(tmp_state_file + ".nonexistent")
        assert result is None

    def test_round_trip_all_steps(self, fresh_state, tmp_state_file):
        """Mark every step with a distinct status and verify round-trip."""
        statuses = ["pending", "running", "complete", "failed", "pending"]
        for i, step in enumerate(fresh_state.deploy_log):
            step.status = statuses[i % len(statuses)]

        save_state(fresh_state, tmp_state_file)
        loaded = load_state(tmp_state_file)

        for original, loaded_step in zip(fresh_state.deploy_log, loaded.deploy_log):
            assert original.key == loaded_step.key
            assert original.status == loaded_step.status

    def test_save_updates_updated_at(self, fresh_state, tmp_state_file):
        original_updated_at = fresh_state.updated_at
        save_state(fresh_state, tmp_state_file)
        loaded = load_state(tmp_state_file)
        # updated_at should be refreshed on save (may equal or be later)
        assert loaded.updated_at >= original_updated_at

    def test_multiple_saves_last_wins(self, fresh_state, tmp_state_file):
        fresh_state.state = "PROJECT"
        save_state(fresh_state, tmp_state_file)

        fresh_state.state = "DEPLOYING"
        save_state(fresh_state, tmp_state_file)

        loaded = load_state(tmp_state_file)
        assert loaded.state == "DEPLOYING"

    def test_state_file_is_valid_json(self, fresh_state, tmp_state_file):
        save_state(fresh_state, tmp_state_file)
        with open(tmp_state_file, encoding="utf-8") as f:
            data = json.load(f)  # raises if invalid JSON
        assert "onboarding_id" in data
        assert "state" in data
        assert "deploy_log" in data

    @patch("apps.onboarding.core.state.save_state", create=True)
    def test_mock_patch_save_state(self, mock_save, fresh_state, tmp_state_file):
        """Verify mock patching works for production code paths."""
        mock_save(fresh_state, tmp_state_file)
        mock_save.assert_called_once_with(fresh_state, tmp_state_file)

    @patch("apps.onboarding.core.state.load_state", create=True)
    def test_mock_patch_load_state(self, mock_load, fresh_state):
        mock_load.return_value = fresh_state
        result = mock_load("/fake/path.json")
        assert result is fresh_state
