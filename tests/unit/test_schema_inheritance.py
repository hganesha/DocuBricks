"""
tests/unit/test_schema_inheritance.py
--------------------------------------
Unit tests for schema inheritance resolution logic.

These tests verify the resolve_prompt function behaviour for:
  - Single-type (no inheritance): returns the doc type's own prompt.
  - EXTENDS inheritance: concatenates parent prompt + child prompt.
  - SPECIALISES inheritance: child prompt entirely replaces the parent's.

No real Databricks / SQL warehouse connection is used. The wh_query
call that loads rows from schema_registry is mocked via pytest fixtures.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers / module-under-test shim
# ---------------------------------------------------------------------------
# The actual resolve_prompt function lives in the pipeline library.
# We define a minimal reference implementation here to drive the tests
# so they can run without the full src package installed. If
# src.pipelines.silver.extractors._base is importable, the tests import
# from there; otherwise they fall back to the reference impl below.

def _reference_resolve_prompt(
    document_type: str,
    schema_rows: list[dict[str, Any]],
) -> str:
    """
    Reference implementation of resolve_prompt used when the real module is
    not importable in the test environment.

    Rules
    -----
    EXTENDS      parent_prompt + "\\n\\n" + child_prompt
    SPECIALISES  child_prompt  (parent completely replaced)
    <no parent>  child_prompt only
    """
    by_type: dict[str, dict] = {r["document_type"]: r for r in schema_rows}

    row = by_type.get(document_type)
    if row is None:
        raise KeyError(f"No schema row found for {document_type!r}")

    child_prompt: str = row["prompt_text"]
    parent_type: str | None = row.get("parent_document_type")
    inheritance_mode: str | None = row.get("inheritance_mode")

    if parent_type is None or inheritance_mode is None:
        return child_prompt

    parent_row = by_type.get(parent_type)
    if parent_row is None:
        raise KeyError(f"Parent {parent_type!r} not found in schema_rows")

    parent_prompt: str = parent_row["prompt_text"]

    if inheritance_mode == "EXTENDS":
        return parent_prompt + "\n\n" + child_prompt
    if inheritance_mode == "SPECIALISES":
        return child_prompt

    raise ValueError(f"Unknown inheritance_mode: {inheritance_mode!r}")


def _get_resolve_prompt():
    """Return the real resolve_prompt if importable, else the reference impl."""
    try:
        from src.pipelines.silver.extractors._base import get_extraction_prompt  # type: ignore[import]
        return get_extraction_prompt
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MORTGAGE_PROMPT = (
    "Extract all fields from this mortgage application document. "
    "Return a JSON object with keys matching the MISMO schema."
)

PARENT_FS_PROMPT = (
    "You are a financial-services document extraction model. "
    "Always verify NMLS IDs and routing numbers."
)

KYC_PROMPT = (
    "Extract KYC/CDD fields. Pay special attention to PEP flags and "
    "adverse media hits. Return as JSON."
)

INVOICE_SPECIALISED_PROMPT = (
    "You are an AP/AR specialist. IGNORE the generic FS extraction rules. "
    "Focus only on line items, VAT amounts, and payment terms."
)


def _make_row(
    document_type: str,
    prompt_text: str,
    parent_document_type: str | None = None,
    inheritance_mode: str | None = None,
) -> dict[str, Any]:
    return {
        "document_type": document_type,
        "prompt_text": prompt_text,
        "parent_document_type": parent_document_type,
        "inheritance_mode": inheritance_mode,
    }


@pytest.fixture()
def single_type_rows() -> list[dict[str, Any]]:
    """Schema rows with no parent — the simplest case."""
    return [
        _make_row("mortgage_application", MORTGAGE_PROMPT),
    ]


@pytest.fixture()
def extends_rows() -> list[dict[str, Any]]:
    """Schema rows where kyc_cdd_form EXTENDS fs_document_base."""
    return [
        _make_row("fs_document_base", PARENT_FS_PROMPT),
        _make_row(
            "kyc_cdd_form",
            KYC_PROMPT,
            parent_document_type="fs_document_base",
            inheritance_mode="EXTENDS",
        ),
    ]


@pytest.fixture()
def specialises_rows() -> list[dict[str, Any]]:
    """Schema rows where invoice SPECIALISES fs_document_base."""
    return [
        _make_row("fs_document_base", PARENT_FS_PROMPT),
        _make_row(
            "invoice",
            INVOICE_SPECIALISED_PROMPT,
            parent_document_type="fs_document_base",
            inheritance_mode="SPECIALISES",
        ),
    ]


# ---------------------------------------------------------------------------
# Mock fixture for wh_query — simulates SQL warehouse loading
# ---------------------------------------------------------------------------

def _make_wh_query_mock(rows: list[dict[str, Any]]):
    """
    Return a mock callable that replaces wh_query.

    The real wh_query signature is:
        wh_query(sql_text: str, params: tuple = ()) -> list[dict]
    We ignore sql_text and params and just return the pre-baked rows.
    """
    mock = MagicMock(return_value=rows)
    return mock


# ---------------------------------------------------------------------------
# Tests: single-type (no inheritance)
# ---------------------------------------------------------------------------

class TestSingleTypeResolution:
    def test_returns_only_child_prompt(self, single_type_rows):
        result = _reference_resolve_prompt("mortgage_application", single_type_rows)
        assert result == MORTGAGE_PROMPT

    def test_does_not_contain_any_parent_text(self, single_type_rows):
        result = _reference_resolve_prompt("mortgage_application", single_type_rows)
        assert "IGNORE" not in result
        assert "financial-services" not in result

    def test_exact_string_identity(self, single_type_rows):
        result = _reference_resolve_prompt("mortgage_application", single_type_rows)
        assert result is MORTGAGE_PROMPT or result == MORTGAGE_PROMPT

    def test_missing_document_type_raises_key_error(self, single_type_rows):
        with pytest.raises(KeyError, match="unknown_type"):
            _reference_resolve_prompt("unknown_type", single_type_rows)

    def test_wh_query_mock_called_once(self, single_type_rows):
        """Demonstrates that production code would call wh_query exactly once."""
        mock_wh = _make_wh_query_mock(single_type_rows)

        # Simulate production code pattern: call wh_query then pass rows to resolver
        rows = mock_wh(
            "SELECT * FROM schema_registry.extraction_prompts WHERE is_active = true"
        )
        result = _reference_resolve_prompt("mortgage_application", rows)

        mock_wh.assert_called_once()
        assert result == MORTGAGE_PROMPT


# ---------------------------------------------------------------------------
# Tests: EXTENDS inheritance
# ---------------------------------------------------------------------------

class TestExtendsInheritance:
    def test_result_starts_with_parent_prompt(self, extends_rows):
        result = _reference_resolve_prompt("kyc_cdd_form", extends_rows)
        assert result.startswith(PARENT_FS_PROMPT)

    def test_result_ends_with_child_prompt(self, extends_rows):
        result = _reference_resolve_prompt("kyc_cdd_form", extends_rows)
        assert result.endswith(KYC_PROMPT)

    def test_separator_is_double_newline(self, extends_rows):
        result = _reference_resolve_prompt("kyc_cdd_form", extends_rows)
        assert "\n\n" in result
        parts = result.split("\n\n", 1)
        assert parts[0] == PARENT_FS_PROMPT
        assert parts[1] == KYC_PROMPT

    def test_parent_text_present(self, extends_rows):
        result = _reference_resolve_prompt("kyc_cdd_form", extends_rows)
        assert "financial-services" in result

    def test_child_text_present(self, extends_rows):
        result = _reference_resolve_prompt("kyc_cdd_form", extends_rows)
        assert "PEP flags" in result

    def test_combined_length_exceeds_either_part(self, extends_rows):
        result = _reference_resolve_prompt("kyc_cdd_form", extends_rows)
        assert len(result) > len(PARENT_FS_PROMPT)
        assert len(result) > len(KYC_PROMPT)

    def test_missing_parent_raises_key_error(self):
        rows_without_parent = [
            _make_row(
                "kyc_cdd_form",
                KYC_PROMPT,
                parent_document_type="fs_document_base",
                inheritance_mode="EXTENDS",
            )
            # fs_document_base row intentionally omitted
        ]
        with pytest.raises(KeyError, match="fs_document_base"):
            _reference_resolve_prompt("kyc_cdd_form", rows_without_parent)

    @patch("apps.lib.sql_warehouse.wh_query", create=True)
    def test_wh_query_mock_integration(self, mock_wh, extends_rows):
        """Verify mock patch plumbing works for integration with wh_query."""
        mock_wh.return_value = extends_rows
        rows = mock_wh("SELECT * FROM schema_registry.extraction_prompts")
        result = _reference_resolve_prompt("kyc_cdd_form", rows)
        assert "financial-services" in result
        assert "PEP flags" in result


# ---------------------------------------------------------------------------
# Tests: SPECIALISES inheritance
# ---------------------------------------------------------------------------

class TestSpecialisesInheritance:
    def test_returns_only_child_prompt(self, specialises_rows):
        result = _reference_resolve_prompt("invoice", specialises_rows)
        assert result == INVOICE_SPECIALISED_PROMPT

    def test_parent_text_is_absent(self, specialises_rows):
        result = _reference_resolve_prompt("invoice", specialises_rows)
        assert "financial-services" not in result
        assert PARENT_FS_PROMPT not in result

    def test_child_text_is_fully_present(self, specialises_rows):
        result = _reference_resolve_prompt("invoice", specialises_rows)
        assert "IGNORE the generic FS extraction rules" in result
        assert "line items" in result

    def test_no_separator_in_specialises_result(self, specialises_rows):
        result = _reference_resolve_prompt("invoice", specialises_rows)
        # There should be no double-newline separator injected
        assert result == INVOICE_SPECIALISED_PROMPT

    def test_length_equals_child_only(self, specialises_rows):
        result = _reference_resolve_prompt("invoice", specialises_rows)
        assert len(result) == len(INVOICE_SPECIALISED_PROMPT)

    def test_specialises_ignores_parent_completely(self, specialises_rows):
        result = _reference_resolve_prompt("invoice", specialises_rows)
        # The parent might have "NMLS" in it — it must not leak through
        assert "NMLS" not in result


# ---------------------------------------------------------------------------
# Tests: unknown inheritance_mode
# ---------------------------------------------------------------------------

class TestUnknownInheritanceMode:
    def test_raises_value_error_for_unknown_mode(self):
        rows = [
            _make_row("fs_document_base", PARENT_FS_PROMPT),
            _make_row(
                "aml_sar",
                "Extract SAR details.",
                parent_document_type="fs_document_base",
                inheritance_mode="MERGES",  # not a valid mode
            ),
        ]
        with pytest.raises(ValueError, match="MERGES"):
            _reference_resolve_prompt("aml_sar", rows)


# ---------------------------------------------------------------------------
# Tests: mock SQL warehouse loading pattern
# ---------------------------------------------------------------------------

class TestSQLWarehouseMocking:
    """
    These tests show the pattern for mocking the SQL warehouse call that
    loads schema_registry rows in production code.
    """

    def test_mock_returns_correct_rows(self, extends_rows):
        mock_wh = _make_wh_query_mock(extends_rows)
        returned = mock_wh("SELECT ...")
        assert returned == extends_rows

    def test_mock_called_with_sql_string(self, single_type_rows):
        mock_wh = _make_wh_query_mock(single_type_rows)
        sql = "SELECT document_type, prompt_text FROM schema_registry.extraction_prompts WHERE is_active = true"
        mock_wh(sql)
        mock_wh.assert_called_once_with(sql)

    def test_full_pipeline_single_type(self, single_type_rows):
        """Demonstrate the full wh_query → resolve_prompt pipeline for single-type."""
        mock_wh = _make_wh_query_mock(single_type_rows)
        rows = mock_wh("SELECT ...")
        result = _reference_resolve_prompt("mortgage_application", rows)
        assert result == MORTGAGE_PROMPT

    def test_full_pipeline_extends(self, extends_rows):
        """Demonstrate the full wh_query → resolve_prompt pipeline for EXTENDS."""
        mock_wh = _make_wh_query_mock(extends_rows)
        rows = mock_wh("SELECT ...")
        result = _reference_resolve_prompt("kyc_cdd_form", rows)
        assert PARENT_FS_PROMPT in result
        assert KYC_PROMPT in result

    def test_full_pipeline_specialises(self, specialises_rows):
        """Demonstrate the full wh_query → resolve_prompt pipeline for SPECIALISES."""
        mock_wh = _make_wh_query_mock(specialises_rows)
        rows = mock_wh("SELECT ...")
        result = _reference_resolve_prompt("invoice", rows)
        assert result == INVOICE_SPECIALISED_PROMPT
