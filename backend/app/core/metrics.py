from prometheus_client import Counter, Histogram, Gauge

# Prometheus Metric Instruments
PIPELINE_RUNS_TOTAL = Counter(
    "pipeline_runs_total",
    "Total count of pipeline runs partitioned by pipeline ID and terminal status",
    ["pipeline_id", "status"]
)

PIPELINE_EXECUTION_DURATION_SECONDS = Histogram(
    "pipeline_execution_duration_seconds",
    "Duration of pipeline runs in seconds",
    ["pipeline_id"],
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

INCIDENTS_DETECTED_TOTAL = Counter(
    "incidents_detected_total",
    "Total failure incidents detected by category and severity",
    ["dataset_name", "failure_category", "severity"]
)

RECOVERY_ATTEMPTS_TOTAL = Counter(
    "recovery_attempts_total",
    "Total recovery attempts executed by strategy and outcome",
    ["strategy", "outcome"]
)

QUALITY_CHECKS_FAILED_TOTAL = Counter(
    "quality_checks_failed_total",
    "Total data quality rule violations",
    ["dataset_name", "rule_id"]
)

INGESTION_ROWS_TOTAL = Counter(
    "ingestion_rows_total",
    "Total rows ingested into raw tables",
    ["dataset_name"]
)

ACTIVE_OPEN_INCIDENTS = Gauge(
    "active_open_incidents",
    "Current number of unresolved incidents awaiting action or approval",
    ["dataset_name"]
)

