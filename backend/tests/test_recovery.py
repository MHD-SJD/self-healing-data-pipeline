import pytest
import uuid
import pandas as pd
import sys
from pathlib import Path
from unittest.mock import MagicMock
from types import SimpleNamespace

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.recovery.strategies import RecoveryStrategies


@pytest.fixture
def mock_db():
    session = MagicMock()
    return session


def test_deduplicate_removes_duplicates(mock_db):
    batch_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    df = pd.DataFrame({
        "order_id": ["ORD-1", "ORD-2", "ORD-1"],
        "order_date": ["2024-01-01 10:00:00", "2024-01-01 11:00:00", "2024-01-01 12:00:00"],
        "amount": [100.0, 50.0, 120.0]
    })
    clean_df, summary = RecoveryStrategies.deduplicate(
        db=mock_db,
        df=df,
        dataset_name="orders",
        batch_id=batch_id,
        incident_id=incident_id,
        key_column="order_id",
        time_column="order_date",
        dry_run=False
    )
    assert len(clean_df) == 2
    assert summary["quarantined_duplicates"] == 1
    assert mock_db.add.called
    assert mock_db.commit.called


def test_deduplicate_keeps_latest(mock_db):
    batch_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    df = pd.DataFrame({
        "order_id": ["ORD-1", "ORD-1"],
        "order_date": ["2024-01-01 09:00:00", "2024-01-01 18:00:00"],
        "amount": [10.0, 99.0]
    })
    clean_df, summary = RecoveryStrategies.deduplicate(
        db=mock_db,
        df=df,
        dataset_name="orders",
        batch_id=batch_id,
        incident_id=incident_id,
        key_column="order_id",
        time_column="order_date"
    )
    assert len(clean_df) == 1
    # Check that the retained row is the one with amount 99.0 (latest)
    assert clean_df.iloc[0]["amount"] == 99.0


def test_deduplicate_no_duplicates(mock_db):
    batch_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    df = pd.DataFrame({
        "order_id": ["ORD-1", "ORD-2", "ORD-3"],
        "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"]
    })
    clean_df, summary = RecoveryStrategies.deduplicate(
        db=mock_db,
        df=df,
        dataset_name="orders",
        batch_id=batch_id,
        incident_id=incident_id,
        key_column="order_id"
    )
    assert len(clean_df) == 3
    assert summary["status"] == "NO_OP"
    assert not mock_db.add.called


def test_deduplicate_dry_run(mock_db):
    batch_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    df = pd.DataFrame({
        "order_id": ["ORD-1", "ORD-1"],
        "order_date": ["2024-01-01", "2024-01-02"]
    })
    clean_df, summary = RecoveryStrategies.deduplicate(
        db=mock_db,
        df=df,
        dataset_name="orders",
        batch_id=batch_id,
        incident_id=incident_id,
        key_column="order_id",
        dry_run=True
    )
    assert len(clean_df) == 1
    assert summary["dry_run"] is True
    assert summary["quarantined_duplicates"] == 1
    assert not mock_db.add.called
    assert not mock_db.commit.called


def test_quarantine_missing_keys(mock_db):
    batch_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    df = pd.DataFrame({
        "customer_id": ["C1", None, "", "C4"],
        "email": ["c1@a.com", "c2@a.com", "c3@a.com", "c4@a.com"]
    })
    clean_df, summary = RecoveryStrategies.quarantine_missing_keys(
        db=mock_db,
        df=df,
        dataset_name="customers",
        batch_id=batch_id,
        incident_id=incident_id,
        key_column="customer_id",
        dry_run=False
    )
    assert len(clean_df) == 2
    assert summary["quarantined_rows"] == 2
    assert mock_db.add.called
    assert mock_db.commit.called


def test_quarantine_missing_keys_none_missing(mock_db):
    batch_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    df = pd.DataFrame({"customer_id": ["C1", "C2"]})
    clean_df, summary = RecoveryStrategies.quarantine_missing_keys(
        db=mock_db,
        df=df,
        dataset_name="customers",
        batch_id=batch_id,
        incident_id=incident_id,
        key_column="customer_id"
    )
    assert len(clean_df) == 2
    assert summary["quarantined_rows"] == 0
    assert not mock_db.add.called


def test_quarantine_invalid_records(mock_db):
    batch_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    df = pd.DataFrame({
        "order_id": ["O1", "O2", "O3"],
        "amount": [100.0, -50.0, 20.0]
    })
    invalid_mask = df["amount"] < 0
    clean_df, summary = RecoveryStrategies.quarantine_invalid_records(
        db=mock_db,
        df=df,
        dataset_name="orders",
        batch_id=batch_id,
        incident_id=incident_id,
        invalid_mask=invalid_mask,
        rejection_reason="Negative amount prohibited",
        dry_run=False
    )
    assert len(clean_df) == 2
    assert summary["quarantined_rows"] == 1
    assert mock_db.add.called
    assert mock_db.commit.called


def test_quarantine_invalid_dry_run(mock_db):
    batch_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    df = pd.DataFrame({"amount": [10.0, -5.0]})
    invalid_mask = df["amount"] < 0
    clean_df, summary = RecoveryStrategies.quarantine_invalid_records(
        db=mock_db,
        df=df,
        dataset_name="orders",
        batch_id=batch_id,
        incident_id=incident_id,
        invalid_mask=invalid_mask,
        rejection_reason="Negative amount",
        dry_run=True
    )
    assert len(clean_df) == 1
    assert summary["dry_run"] is True
    assert not mock_db.add.called


def test_adopt_additive_schema_dry_run(mock_db):
    batch_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    mock_schema = SimpleNamespace(
        version=1,
        schema_definition={"columns": {"id": {"type": "string"}}}
    )
    mock_db.query().filter().order_by().first.return_value = mock_schema

    summary = RecoveryStrategies.adopt_additive_schema(
        db=mock_db,
        dataset_name="customers",
        new_columns=["loyalty_tier"],
        batch_id=batch_id,
        incident_id=incident_id,
        dry_run=True
    )
    assert summary["strategy"] == "adopt_additive_schema"
    assert summary["dry_run"] is True
    assert summary["previous_version"] == 1
    assert summary["new_version"] == 2
    assert "loyalty_tier" in summary["adopted_columns"]
    assert not mock_db.add.called
    assert not mock_db.execute.called

