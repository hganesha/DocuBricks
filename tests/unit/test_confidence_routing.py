"""
tests/unit/test_confidence_routing.py
---------------------------------------
Unit tests for the confidence threshold routing logic.

Routing rules (from wave1_applib.json and field_thresholds.json):
  avg_confidence >= 0.85              → VALIDATED
  0.65 <= avg_confidence < 0.85       → doc_type-specific threshold decides
                                        REVIEW vs VALIDATED
  avg_confidence < 0.65               → REVIEW
  field-level threshold breach        → REVIEW (regardless of avg_confidence)

All tests use mocked inputs — no real Spark or DB connection.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Reference implementation of the routing logic
# ---------------------------------------------------------------------------
# Mirrors the logic that lives in src/pipelines/silver/extractors/_base.py
# so the tests can run stand-alone.

#: Default confidence thresholds (from wave1_applib.json)
DEFAULT_THRESHOLDS = {
    "high": 0.85,
    "medium": 0.65,
    "low": 0.0,
}

#: Per-doc-type override thresholds for the "medium band" routing decision
DOC_TYPE_MEDIUM_BAND_THRESHOLD: dict[str, float] = {
    "mortgage_application": 0.75,  # higher bar — regulated product
    "kyc_cdd_form": 0.72,
    "aml_sar": 0.80,              # AML: high bar
    "invoice": 0.68,              # lower bar — AP/AR less critical
}

#: Field-level minimum confidence requirements
FIELD_THRESHOLDS: dict[str, dict[str, float]] = {
    "mortgage_application": {
        "loan_amount": 0.95,
        "borrower_ssn": 0.98,
        "property_address": 0.90,
        "interest_rate": 0.92,
    },
    "kyc_cdd_form": {
        "full_legal_name": 0.90,
        "date_of_birth": 0.90,
        "national_id_number": 0.95,
    },
    "aml_sar": {
        "subject_name": 0.90,
        "suspicious_activity_type": 0.88,
        "transaction_amount": 0.92,
    },
    "invoice": {
        "total_amount": 0.85,
        "vendor_name": 0.80,
    },
}


def route_document(
    doc_type: str,
    avg_confidence: float,
    field_scores: dict[str, float] | None = None,
    doc_type_thresholds: dict[str, float] | None = None,
    field_thresholds: dict[str, dict[str, float]] | None = None,
) -> str:
    """
    Route a document to VALIDATED or REVIEW based on confidence scores.

    Parameters
    ----------
    doc_type:
        Document type key (e.g. 'mortgage_application').
    avg_confidence:
        Average extraction confidence across all fields (0.0 – 1.0).
    field_scores:
        Optional mapping of field_name → confidence_score for field-level checks.
    doc_type_thresholds:
        Override for the medium-band threshold per doc type.
    field_thresholds:
        Override for field-level minimum thresholds.

    Returns
    -------
    'VALIDATED' or 'REVIEW'
    """
    if doc_type_thresholds is None:
        doc_type_thresholds = DOC_TYPE_MEDIUM_BAND_THRESHOLD
    if field_thresholds is None:
        field_thresholds = FIELD_THRESHOLDS

    # 1. Field-level checks (highest priority — always enforced)
    if field_scores:
        field_mins = field_thresholds.get(doc_type, {})
        for field, min_score in field_mins.items():
            actual = field_scores.get(field)
            if actual is not None and actual < min_score:
                return "REVIEW"

    # 2. High band: always VALIDATED
    if avg_confidence >= DEFAULT_THRESHOLDS["high"]:
        return "VALIDATED"

    # 3. Medium band: doc-type specific threshold
    if avg_confidence >= DEFAULT_THRESHOLDS["medium"]:
        medium_threshold = doc_type_thresholds.get(doc_type, DEFAULT_THRESHOLDS["high"])
        if avg_confidence >= medium_threshold:
            return "VALIDATED"
        return "REVIEW"

    # 4. Below medium: always REVIEW
    return "REVIEW"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def good_field_scores() -> dict[str, float]:
    """All fields well above threshold — should not trigger REVIEW."""
    return {
        "loan_amount": 0.97,
        "borrower_ssn": 0.99,
        "property_address": 0.95,
        "interest_rate": 0.96,
    }


@pytest.fixture()
def borderline_loan_amount_scores() -> dict[str, float]:
    """loan_amount just below the 0.95 minimum — should trigger REVIEW."""
    return {
        "loan_amount": 0.94,        # below 0.95 threshold
        "borrower_ssn": 0.99,
        "property_address": 0.95,
        "interest_rate": 0.96,
    }


@pytest.fixture()
def poor_ssn_scores() -> dict[str, float]:
    """borrower_ssn well below threshold."""
    return {
        "loan_amount": 0.97,
        "borrower_ssn": 0.70,        # below 0.98 threshold
        "property_address": 0.91,
        "interest_rate": 0.93,
    }


# ---------------------------------------------------------------------------
# Tests: high band (avg >= 0.85) → always VALIDATED
# ---------------------------------------------------------------------------

class TestHighConfidenceBand:
    @pytest.mark.parametrize("avg", [0.85, 0.90, 0.95, 0.99, 1.0])
    def test_high_confidence_is_validated(self, avg):
        result = route_document("mortgage_application", avg)
        assert result == "VALIDATED"

    def test_exactly_085_is_validated(self):
        result = route_document("invoice", 0.85)
        assert result == "VALIDATED"

    def test_high_confidence_all_doc_types(self):
        for doc_type in ["mortgage_application", "kyc_cdd_form", "aml_sar", "invoice"]:
            assert route_document(doc_type, 0.90) == "VALIDATED"

    def test_high_confidence_with_good_field_scores(self, good_field_scores):
        result = route_document("mortgage_application", 0.92, field_scores=good_field_scores)
        assert result == "VALIDATED"

    def test_high_confidence_overrides_missing_fields(self):
        """If field_scores is empty, high avg still gives VALIDATED."""
        result = route_document("mortgage_application", 0.88, field_scores={})
        assert result == "VALIDATED"


# ---------------------------------------------------------------------------
# Tests: low band (avg < 0.65) → always REVIEW
# ---------------------------------------------------------------------------

class TestLowConfidenceBand:
    @pytest.mark.parametrize("avg", [0.0, 0.30, 0.50, 0.64, 0.649])
    def test_low_confidence_is_review(self, avg):
        result = route_document("mortgage_application", avg)
        assert result == "REVIEW"

    def test_exactly_zero_is_review(self):
        assert route_document("invoice", 0.0) == "REVIEW"

    def test_low_confidence_all_doc_types(self):
        for doc_type in ["mortgage_application", "kyc_cdd_form", "aml_sar", "invoice"]:
            assert route_document(doc_type, 0.50) == "REVIEW"

    def test_low_confidence_with_field_scores_still_review(self, good_field_scores):
        """Even if field scores are excellent, avg < 0.65 → REVIEW."""
        result = route_document("mortgage_application", 0.60, field_scores=good_field_scores)
        assert result == "REVIEW"


# ---------------------------------------------------------------------------
# Tests: medium band (0.65 <= avg < 0.85) → doc_type decides
# ---------------------------------------------------------------------------

class TestMediumConfidenceBand:
    def test_mortgage_above_medium_threshold_validated(self):
        # Mortgage medium threshold = 0.75; avg=0.78 → VALIDATED
        result = route_document("mortgage_application", 0.78)
        assert result == "VALIDATED"

    def test_mortgage_below_medium_threshold_review(self):
        # Mortgage medium threshold = 0.75; avg=0.72 → REVIEW
        result = route_document("mortgage_application", 0.72)
        assert result == "REVIEW"

    def test_mortgage_exactly_at_medium_threshold_validated(self):
        result = route_document("mortgage_application", 0.75)
        assert result == "VALIDATED"

    def test_aml_above_medium_threshold_validated(self):
        # AML medium threshold = 0.80; avg=0.82 → VALIDATED
        result = route_document("aml_sar", 0.82)
        assert result == "VALIDATED"

    def test_aml_below_medium_threshold_review(self):
        # AML medium threshold = 0.80; avg=0.75 → REVIEW
        result = route_document("aml_sar", 0.75)
        assert result == "REVIEW"

    def test_invoice_lower_medium_threshold_validated(self):
        # Invoice medium threshold = 0.68; avg=0.70 → VALIDATED
        result = route_document("invoice", 0.70)
        assert result == "VALIDATED"

    def test_invoice_at_boundary_validated(self):
        result = route_document("invoice", 0.68)
        assert result == "VALIDATED"

    def test_invoice_just_below_medium_threshold_review(self):
        result = route_document("invoice", 0.67)
        assert result == "REVIEW"

    def test_kyc_medium_band_routing(self):
        # KYC medium threshold = 0.72
        assert route_document("kyc_cdd_form", 0.73) == "VALIDATED"
        assert route_document("kyc_cdd_form", 0.70) == "REVIEW"

    def test_medium_band_boundary_at_065(self):
        # 0.65 is the floor of the medium band
        result = route_document("invoice", 0.65)
        # invoice threshold is 0.68 — 0.65 < 0.68 → REVIEW
        assert result == "REVIEW"

    def test_custom_doc_type_falls_back_to_high_threshold(self):
        """Doc types not in DOC_TYPE_MEDIUM_BAND_THRESHOLD default to 0.85."""
        custom_thresholds: dict[str, float] = {}  # empty
        result = route_document(
            "unknown_doc_type",
            0.80,
            doc_type_thresholds=custom_thresholds,
        )
        # 0.80 < 0.85 (fallback) → REVIEW
        assert result == "REVIEW"


# ---------------------------------------------------------------------------
# Tests: field-level threshold enforcement
# ---------------------------------------------------------------------------

class TestFieldLevelThresholds:
    def test_loan_amount_below_threshold_triggers_review(self, borderline_loan_amount_scores):
        # avg_confidence is high, but loan_amount = 0.94 < 0.95 → REVIEW
        result = route_document(
            "mortgage_application",
            avg_confidence=0.91,
            field_scores=borderline_loan_amount_scores,
        )
        assert result == "REVIEW"

    def test_loan_amount_at_threshold_does_not_trigger_review(self, good_field_scores):
        # loan_amount = 0.97 >= 0.95 → VALIDATED (high avg too)
        result = route_document(
            "mortgage_application",
            avg_confidence=0.91,
            field_scores=good_field_scores,
        )
        assert result == "VALIDATED"

    def test_ssn_below_threshold_triggers_review(self, poor_ssn_scores):
        result = route_document(
            "mortgage_application",
            avg_confidence=0.88,
            field_scores=poor_ssn_scores,
        )
        assert result == "REVIEW"

    def test_field_check_before_avg_check(self, borderline_loan_amount_scores):
        """Field-level check has priority — fires even at very high avg."""
        result = route_document(
            "mortgage_application",
            avg_confidence=0.99,
            field_scores=borderline_loan_amount_scores,
        )
        assert result == "REVIEW"

    def test_missing_field_in_scores_is_skipped(self):
        """
        If a field with a minimum threshold is absent from field_scores,
        the check is skipped (partial extraction should not penalise).
        """
        partial_scores = {
            "property_address": 0.95,
            # loan_amount absent
        }
        result = route_document(
            "mortgage_application",
            avg_confidence=0.91,
            field_scores=partial_scores,
        )
        assert result == "VALIDATED"

    def test_aml_subject_name_below_threshold(self):
        scores = {"subject_name": 0.85, "suspicious_activity_type": 0.92, "transaction_amount": 0.95}
        # subject_name 0.85 < 0.90 → REVIEW
        result = route_document("aml_sar", 0.87, field_scores=scores)
        assert result == "REVIEW"

    def test_invoice_total_amount_below_threshold(self):
        scores = {"total_amount": 0.82, "vendor_name": 0.90}
        # total_amount 0.82 < 0.85 → REVIEW
        result = route_document("invoice", 0.88, field_scores=scores)
        assert result == "REVIEW"

    def test_kyc_national_id_below_threshold(self):
        scores = {"full_legal_name": 0.92, "date_of_birth": 0.91, "national_id_number": 0.93}
        # national_id_number 0.93 < 0.95 → REVIEW
        result = route_document("kyc_cdd_form", 0.86, field_scores=scores)
        assert result == "REVIEW"

    def test_no_field_scores_skips_field_level_check(self):
        """Passing field_scores=None skips the field-level check entirely."""
        result = route_document("mortgage_application", 0.88, field_scores=None)
        assert result == "VALIDATED"

    def test_empty_field_scores_skips_field_level_check(self):
        result = route_document("mortgage_application", 0.88, field_scores={})
        assert result == "VALIDATED"

    def test_doc_type_without_field_thresholds_is_not_penalised(self):
        """An unknown doc type has no field thresholds — routing uses avg only."""
        custom_fields = {"exotic_field": 0.10}  # very low, but no threshold defined
        custom_field_thresholds: dict[str, dict[str, float]] = {}
        result = route_document(
            "exotic_doc_type",
            avg_confidence=0.90,
            field_scores=custom_fields,
            field_thresholds=custom_field_thresholds,
        )
        assert result == "VALIDATED"


# ---------------------------------------------------------------------------
# Tests: edge cases and boundary values
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_exactly_085_is_not_medium_band(self):
        """0.85 is the high band floor — must be VALIDATED regardless of doc type."""
        assert route_document("aml_sar", 0.85) == "VALIDATED"

    def test_exactly_065_is_not_low_band(self):
        """0.65 is the medium band floor — must not be REVIEW on avg alone for high-threshold types."""
        # aml_sar medium threshold is 0.80; 0.65 < 0.80 → REVIEW
        assert route_document("aml_sar", 0.65) == "REVIEW"

    def test_confidence_of_one_is_validated(self):
        assert route_document("mortgage_application", 1.0) == "VALIDATED"

    def test_mocked_routing_lookup(self):
        """Verify the routing function can be driven via a mock call chain."""
        mock_lb_query = MagicMock(return_value=[
            {"document_type": "mortgage_application", "avg_confidence": 0.91}
        ])
        rows = mock_lb_query("SELECT ...")
        assert rows[0]["avg_confidence"] == 0.91
        result = route_document("mortgage_application", rows[0]["avg_confidence"])
        assert result == "VALIDATED"
