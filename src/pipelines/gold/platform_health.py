# Databricks notebook source
# DocuBricks — Gold Platform Health
# Layer 4: lightweight operational health metrics for Genie and dashboards
#
# DLT channel: PREVIEW  |  Compute: Serverless
# Target schema: docubricks_prod.gold
# Pipeline config key: catalog_name

# COMMAND ----------
from functools import reduce

import dlt
from pyspark.sql import DataFrame
from pyspark.sql.functions import count, current_timestamp, lit


CATALOG_NAME = spark.conf.get("catalog_name", "docubricks_prod")

HEALTH_SOURCES = {
    "silver_classified": f"{CATALOG_NAME}.silver.silver_classified",
    "fs_mortgage_portfolio": f"{CATALOG_NAME}.gold.fs_mortgage_portfolio",
    "fs_kyc_compliance_summary": f"{CATALOG_NAME}.gold.fs_kyc_compliance_summary",
    "fs_aml_alerts_summary": f"{CATALOG_NAME}.gold.fs_aml_alerts_summary",
}


def _table_exists(table_name: str) -> bool:
    try:
        return bool(spark.catalog.tableExists(table_name))
    except Exception:
        return False


def _count_metric(source_name: str, table_name: str) -> DataFrame:
    if _table_exists(table_name):
        base = spark.table(table_name).agg(count(lit(1)).cast("long").alias("metric_value"))
    else:
        base = spark.range(1).select(lit(0).cast("long").alias("metric_value"))

    return (
        base
        .select(
            lit(source_name).alias("source_name"),
            lit("row_count").alias("metric_name"),
            "metric_value",
            current_timestamp().alias("measured_at"),
        )
    )


@dlt.table(
    name="platform_health",
    comment=(
        "DocuBricks platform health metrics for Genie, dashboards, and smoke checks. "
        "Provides a stable Gold table even before all downstream sources are populated."
    ),
    table_properties={
        "delta.enableChangeDataFeed": "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true",
        "quality": "gold",
        "docubricks.layer": "gold",
        "docubricks.subject": "platform_health",
    },
)
@dlt.expect_or_fail("source_name_present", "source_name IS NOT NULL")
@dlt.expect_or_fail("metric_name_present", "metric_name IS NOT NULL")
def platform_health():
    metrics = [
        _count_metric(source_name, table_name)
        for source_name, table_name in HEALTH_SOURCES.items()
    ]
    return reduce(lambda left, right: left.unionByName(right), metrics)
