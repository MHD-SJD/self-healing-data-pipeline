import pytest
import uuid
import sys
from pathlib import Path
from unittest.mock import MagicMock
from types import SimpleNamespace

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.classification.classifier import FailureClassifier
from app.classification.taxonomy import FailureCategory, IncidentSeverity


@pytest.fixture
def mock_db():
    session = MagicMock()
    return session


@pytest.fixture
def classifier(mock_db):
    return FailureClassifier(db=mock_db)


def test_classify_missing_data(classifier):
    run_id = uuid.uuid4()
    mock_batch = SimpleNamespace(batch_id=uuid.uuid4())
    mock_val = SimpleNamespace(
        rule_id="req_customer_id",
        severity="CRITICAL",
        failure_details={"error": "Required column missing"}
    )
    incidents = classifier.classify_and_record(
        run_id=run_id,
        batch=mock_batch,
        dataset_name="customers",
        failed_results=[mock_val],
        anomalies=[]
    )
    assert len(incidents) == 1
    assert incidents[0].failure_category == FailureCategory.MISSING_DATA.value
    assert incidents[0].recommended_action == "quarantine_missing_records"
    assert incidents[0].requires_human_approval is False


def test_classify_duplicate_data(classifier):
    run_id = uuid.uuid4()
    mock_val = SimpleNamespace(
        rule_id="unique_order_id",
        severity="ERROR",
        failure_details={"duplicate_count": 5}
    )
    incidents = classifier.classify_and_record(
        run_id=run_id,
        batch=None,
        dataset_name="orders",
        failed_results=[mock_val],
        anomalies=[]
    )
    assert len(incidents) == 1
    assert incidents[0].failure_category == FailureCategory.DUPLICATE_DATA.value
    assert incidents[0].recommended_action == "deduplicate_retaining_latest"
    assert incidents[0].requires_human_approval is False


def test_classify_schema_drift_breaking(classifier):
    run_id = uuid.uuid4()
    mock_val = SimpleNamespace(
        rule_id="schema_contract",
        severity="CRITICAL",
        failure_details={"is_breaking": True, "missing_required_columns": ["email"]}
    )
    incidents = classifier.classify_and_record(
        run_id=run_id,
        batch=None,
        dataset_name="customers",
        failed_results=[mock_val],
        anomalies=[]
    )
    assert len(incidents) == 1
    assert incidents[0].failure_category == FailureCategory.SCHEMA_DRIFT.value
    assert incidents[0].requires_human_approval is True
    assert incidents[0].recommended_action == "quarantine_batch_require_approval"


def test_classify_schema_drift_additive(classifier):
    run_id = uuid.uuid4()
    mock_val = SimpleNamespace(
        rule_id="schema_contract",
        severity="INFO",
        failure_details={"is_breaking": False, "unexpected_columns": ["loyalty_tier"]}
    )
    incidents = classifier.classify_and_record(
        run_id=run_id,
        batch=None,
        dataset_name="customers",
        failed_results=[mock_val],
        anomalies=[]
    )
    assert len(incidents) == 1
    assert incidents[0].failure_category == FailureCategory.SCHEMA_DRIFT.value
    assert incidents[0].requires_human_approval is False
    assert incidents[0].recommended_action == "adopt_additive_columns"


def test_classify_invalid_records(classifier):
    run_id = uuid.uuid4()
    mock_val = SimpleNamespace(
        rule_id="valid_amount",
        severity="ERROR",
        failure_details={"invalid_count": 3}
    )
    incidents = classifier.classify_and_record(
        run_id=run_id,
        batch=None,
        dataset_name="orders",
        failed_results=[mock_val],
        anomalies=[]
    )
    assert len(incidents) == 1
    assert incidents[0].failure_category == FailureCategory.INVALID_RECORDS.value
    assert incidents[0].recommended_action == "quarantine_invalid_rows"


def test_classify_distribution_anomaly(classifier):
    run_id = uuid.uuid4()
    mock_anomaly = SimpleNamespace(
        metric_name="amount_mean",
        observed_metric=650.0,
        baseline_mean=120.0,
        baseline_stddev=15.0,
        z_score=35.3,
        anomaly_type="OUTLIER_MEAN",
        severity="WARNING"
    )
    incidents = classifier.classify_and_record(
        run_id=run_id,
        batch=None,
        dataset_name="orders",
        failed_results=[],
        anomalies=[mock_anomaly]
    )
    assert len(incidents) == 1
    assert incidents[0].failure_category == FailureCategory.DISTRIBUTION_ANOMALY.value
    assert incidents[0].requires_human_approval is True
    assert incidents[0].recommended_action == "pause_downstream_and_request_approval"


def test_classify_timeout_exception(classifier):
    run_id = uuid.uuid4()
    exc = TimeoutError("Database connection timeout after 30s")
    incidents = classifier.classify_and_record(
        run_id=run_id,
        batch=None,
        dataset_name="orders",
        failed_results=[],
        anomalies=[],
        runtime_exception=exc
    )
    assert len(incidents) == 1
    assert incidents[0].failure_category == FailureCategory.INFRASTRUCTURE_OR_TIMEOUT_FAILURE.value
    assert incidents[0].recommended_action == "retry_with_backoff"
    assert incidents[0].requires_human_approval is False


def test_classify_ingestion_exception(classifier):
    run_id = uuid.uuid4()
    exc = FileNotFoundError("CSV source file data/samples/customers.csv not found")
    incidents = classifier.classify_and_record(
        run_id=run_id,
        batch=None,
        dataset_name="customers",
        failed_results=[],
        anomalies=[],
        runtime_exception=exc
    )
    assert len(incidents) == 1
    assert incidents[0].failure_category == FailureCategory.INGESTION_FAILURE.value
    assert incidents[0].recommended_action == "retry_ingestion_or_check_source"


def test_classify_dbt_exception(classifier):
    run_id = uuid.uuid4()
    exc = RuntimeError("dbt run failed: compilation error in stg_orders.sql")
    incidents = classifier.classify_and_record(
        run_id=run_id,
        batch=None,
        dataset_name="orders",
        failed_results=[],
        anomalies=[],
        runtime_exception=exc
    )
    assert len(incidents) == 1
    assert incidents[0].failure_category == FailureCategory.TRANSFORMATION_FAILURE.value
    assert incidents[0].requires_human_approval is True


def test_classify_unknown_exception(classifier):
    run_id = uuid.uuid4()
    exc = ValueError("Unexpected token in input stream")
    incidents = classifier.classify_and_record(
        run_id=run_id,
        batch=None,
        dataset_name="orders",
        failed_results=[],
        anomalies=[],
        runtime_exception=exc
    )
    assert len(incidents) == 1
    assert incidents[0].failure_category == FailureCategory.UNKNOWN_FAILURE.value
    assert incidents[0].requires_human_approval is True

