# Databricks notebook source
# DocuBricks — Gold FS Portfolio Views
# Layer 4: Silver extracted tables → Gold materialized views for Financial Services
#
# DLT channel: PREVIEW  |  Compute: Serverless
# Target schema: docubricks_prod.gold
# Pipeline config key: catalog_name
#
# Materialized views in this notebook
# ------------------------------------
# 1. fs_mortgage_portfolio       — tenant + week aggregations, loan stats, DTI
# 2. fs_kyc_compliance_summary   — tenant + date, KYC profile counts by risk rating
# 3. fs_aml_alerts_summary       — tenant + week, AML SAR counts by risk tier
#
# All views read from fully-qualified Silver tables so the Gold pipeline is
# independent of the Silver pipeline and can be refreshed on its own cadence.

# COMMAND ----------
import dlt
from pyspark.sql.functions import (
    col, count, count_if, sum as spark_sum, avg, date_trunc,
    percentile_approx, lit, coalesce, current_timestamp, to_date,
    when, expr
)

# ---------------------------------------------------------------------------
# Runtime configuration
# ---------------------------------------------------------------------------
CATALOG_NAME = spark.conf.get("catalog_name", "docubricks_prod")

# Fully-qualified Silver table references
# These are batch reads (not streaming) because Gold is a materialized view
# layer refreshed after each Silver pipeline run.
SILVER_MORTGAGE   = f"{CATALOG_NAME}.silver.silver_extracted_mortgage_application"
SILVER_KYC        = f"{CATALOG_NAME}.silver.silver_extracted_kyc_cdd_form"
SILVER_AML        = f"{CATALOG_NAME}.silver.silver_extracted_aml_sar"
SILVER_CLASSIFIED = f"{CATALOG_NAME}.silver.silver_classified"

# ---------------------------------------------------------------------------
# 1. fs_mortgage_portfolio
#
# Aggregated per tenant + calendar week.
# Designed for Genie queries like:
#   "Show DTI trends by tenant this quarter"
#   "Which tenants have the highest proportion of high-DTI applications?"
#
# Source table: silver_extracted_mortgage_application
# Populated by Wave 2 MortgageExtractorAgent.
# ---------------------------------------------------------------------------

@dlt.table(
    name="fs_mortgage_portfolio",
    comment=(
        "FS vertical: mortgage application portfolio summary by tenant and week. "
        "Refreshed after each Silver pipeline run. Trusted by Genie FS workspace."
    ),
    cluster_by=["tenant_id", "week"],
    table_properties={
        "delta.enableChangeDataFeed":       "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact":   "true",
        "delta.enableDeletionVectors":      "true",
        "quality":                          "gold",
        "docubricks.layer":                 "gold",
        "docubricks.vertical":              "fs",
        "docubricks.subject":               "mortgage_portfolio",
    },
)
@dlt.expect_or_fail("tenant_id_present",    "tenant_id IS NOT NULL")
@dlt.expect_or_fail("week_present",         "week IS NOT NULL")
@dlt.expect("application_count_positive",   "application_count > 0")
def fs_mortgage_portfolio():
    """
    Tenant + week aggregation of mortgage application extraction results.

    Columns
    -------
    tenant_id               : tenant identifier (UC RLS key)
    week                    : Monday of the ISO week (date_trunc('week', extracted_at))
    application_count       : total applications extracted
    total_loan_amount       : sum of loan_amount across all applications
    avg_loan_amount         : mean loan_amount
    median_loan_amount      : approximate median loan_amount (percentile p50)
    avg_dti                 : mean debt_to_income_ratio
    p75_dti                 : 75th-percentile DTI (risk indicator)
    high_dti_count          : count where debt_to_income_ratio > 0.43 (GSE threshold)
    low_confidence_count    : count where avg_confidence_score < 0.80
    review_required_count   : count where avg_confidence_score < 0.65
    avg_confidence          : mean extraction confidence for the period
    total_pages_processed   : sum of page_count (compute cost proxy)
    refreshed_at            : timestamp of last Gold refresh
    """
    return (
        spark.table(SILVER_MORTGAGE)
        .withColumn("week", date_trunc("week", col("extracted_at")))
        .groupBy("tenant_id", "week")
        .agg(
            count("*").alias("application_count"),
            coalesce(spark_sum("loan_amount"), lit(0)).alias("total_loan_amount"),
            avg("loan_amount").alias("avg_loan_amount"),
            percentile_approx("loan_amount", 0.5).alias("median_loan_amount"),
            avg("debt_to_income_ratio").alias("avg_dti"),
            percentile_approx("debt_to_income_ratio", 0.75).alias("p75_dti"),
            count_if(col("debt_to_income_ratio") > 0.43).alias("high_dti_count"),
            count_if(col("avg_confidence_score") < 0.80).alias("low_confidence_count"),
            count_if(col("avg_confidence_score") < 0.65).alias("review_required_count"),
            avg("avg_confidence_score").alias("avg_confidence"),
            coalesce(spark_sum("page_count"), lit(0)).alias("total_pages_processed"),
        )
        .withColumn("refreshed_at", current_timestamp())
        .select(
            "tenant_id",
            "week",
            "application_count",
            "total_loan_amount",
            "avg_loan_amount",
            "median_loan_amount",
            "avg_dti",
            "p75_dti",
            "high_dti_count",
            "low_confidence_count",
            "review_required_count",
            "avg_confidence",
            "total_pages_processed",
            "refreshed_at",
        )
    )


# ---------------------------------------------------------------------------
# 2. fs_kyc_compliance_summary
#
# Aggregated per tenant + calendar date.
# Designed for Genie queries like:
#   "How many High-risk KYC profiles were onboarded this month?"
#   "Show PEP screening completion rate by tenant"
#
# Source table: silver_extracted_kyc_cdd_form
# Populated by Wave 2 KYCExtractorAgent.
# ---------------------------------------------------------------------------

@dlt.table(
    name="fs_kyc_compliance_summary",
    comment=(
        "FS vertical: KYC/CDD compliance summary by tenant and extraction date. "
        "Counts risk ratings, PEP flags, and confidence metrics."
    ),
    cluster_by=["tenant_id", "extraction_date"],
    table_properties={
        "delta.enableChangeDataFeed":       "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact":   "true",
        "delta.enableDeletionVectors":      "true",
        "quality":                          "gold",
        "docubricks.layer":                 "gold",
        "docubricks.vertical":              "fs",
        "docubricks.subject":               "kyc_compliance",
    },
)
@dlt.expect_or_fail("tenant_id_present_kyc", "tenant_id IS NOT NULL")
@dlt.expect_or_fail("date_present_kyc",      "extraction_date IS NOT NULL")
def fs_kyc_compliance_summary():
    """
    Tenant + date aggregation of KYC / CDD extraction results.

    Columns
    -------
    tenant_id                   : tenant identifier
    extraction_date             : calendar date of extraction
    total_profiles              : total KYC profiles extracted
    individual_count            : count where customer_type = 'Individual'
    business_count              : count where customer_type = 'Business'
    high_risk_count             : count where risk_rating = 'High'
    medium_risk_count           : count where risk_rating = 'Medium'
    low_risk_count              : count where risk_rating = 'Low'
    pep_flagged_count           : count where pep_status IS NOT NULL
    bo_incomplete_count         : count where beneficial_ownership_collected = false
    low_confidence_count        : count where avg_confidence_score < 0.80
    avg_confidence              : mean extraction confidence
    refreshed_at                : timestamp of last Gold refresh
    """
    return (
        spark.table(SILVER_KYC)
        .withColumn("extraction_date", to_date(col("extracted_at")))
        .groupBy("tenant_id", "extraction_date")
        .agg(
            count("*").alias("total_profiles"),
            count_if(col("customer_type") == "Individual").alias("individual_count"),
            count_if(col("customer_type") == "Business").alias("business_count"),
            count_if(col("risk_rating") == "High").alias("high_risk_count"),
            count_if(col("risk_rating") == "Medium").alias("medium_risk_count"),
            count_if(col("risk_rating") == "Low").alias("low_risk_count"),
            count_if(col("pep_status").isNotNull()).alias("pep_flagged_count"),
            count_if(col("beneficial_ownership_collected") == False).alias("bo_incomplete_count"),  # noqa: E712
            count_if(col("avg_confidence_score") < 0.80).alias("low_confidence_count"),
            avg("avg_confidence_score").alias("avg_confidence"),
        )
        .withColumn("refreshed_at", current_timestamp())
        .select(
            "tenant_id",
            "extraction_date",
            "total_profiles",
            "individual_count",
            "business_count",
            "high_risk_count",
            "medium_risk_count",
            "low_risk_count",
            "pep_flagged_count",
            "bo_incomplete_count",
            "low_confidence_count",
            "avg_confidence",
            "refreshed_at",
        )
    )


# ---------------------------------------------------------------------------
# 3. fs_aml_alerts_summary
#
# Aggregated per tenant + calendar week.
# Designed for Genie queries like:
#   "How many SARs were filed last quarter?"
#   "Which tenants have the most critical AML alerts?"
#
# Source table: silver_extracted_aml_sar
# Populated by Wave 2 AMLExtractorAgent.
# ---------------------------------------------------------------------------

@dlt.table(
    name="fs_aml_alerts_summary",
    comment=(
        "FS vertical: AML Suspicious Activity Report summary by tenant and week. "
        "Counts by risk tier, filing status, and confidence metrics."
    ),
    cluster_by=["tenant_id", "week"],
    table_properties={
        "delta.enableChangeDataFeed":       "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact":   "true",
        "delta.enableDeletionVectors":      "true",
        "quality":                          "gold",
        "docubricks.layer":                 "gold",
        "docubricks.vertical":              "fs",
        "docubricks.subject":               "aml_alerts",
    },
)
@dlt.expect_or_fail("tenant_id_present_aml", "tenant_id IS NOT NULL")
@dlt.expect_or_fail("week_present_aml",      "week IS NOT NULL")
def fs_aml_alerts_summary():
    """
    Tenant + week aggregation of AML SAR extraction results.

    Columns
    -------
    tenant_id                   : tenant identifier
    week                        : Monday of the ISO week
    total_sar_count             : total SARs extracted
    critical_risk_count         : count where risk_tier = 'Critical'
    high_risk_count             : count where risk_tier = 'High'
    medium_risk_count           : count where risk_tier = 'Medium'
    low_risk_count              : count where risk_tier = 'Low'
    filed_count                 : count where filing_status = 'FILED'
    pending_filing_count        : count where filing_status = 'PENDING'
    total_suspicious_amount     : sum of suspicious_activity_amount
    avg_confidence              : mean extraction confidence
    low_confidence_count        : count where avg_confidence_score < 0.80
    review_required_count       : count where avg_confidence_score < 0.65
    refreshed_at                : timestamp of last Gold refresh
    """
    return (
        spark.table(SILVER_AML)
        .withColumn("week", date_trunc("week", col("extracted_at")))
        .groupBy("tenant_id", "week")
        .agg(
            count("*").alias("total_sar_count"),
            count_if(col("risk_tier") == "Critical").alias("critical_risk_count"),
            count_if(col("risk_tier") == "High").alias("high_risk_count"),
            count_if(col("risk_tier") == "Medium").alias("medium_risk_count"),
            count_if(col("risk_tier") == "Low").alias("low_risk_count"),
            count_if(col("filing_status") == "FILED").alias("filed_count"),
            count_if(col("filing_status") == "PENDING").alias("pending_filing_count"),
            coalesce(
                spark_sum("suspicious_activity_amount"), lit(0)
            ).alias("total_suspicious_amount"),
            avg("avg_confidence_score").alias("avg_confidence"),
            count_if(col("avg_confidence_score") < 0.80).alias("low_confidence_count"),
            count_if(col("avg_confidence_score") < 0.65).alias("review_required_count"),
        )
        .withColumn("refreshed_at", current_timestamp())
        .select(
            "tenant_id",
            "week",
            "total_sar_count",
            "critical_risk_count",
            "high_risk_count",
            "medium_risk_count",
            "low_risk_count",
            "filed_count",
            "pending_filing_count",
            "total_suspicious_amount",
            "avg_confidence",
            "low_confidence_count",
            "review_required_count",
            "refreshed_at",
        )
    )
