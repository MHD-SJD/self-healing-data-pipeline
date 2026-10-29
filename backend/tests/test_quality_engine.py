import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.quality.rules import QualityRuleEvaluator


def test_completeness_pass():
    df = pd.DataFrame({
        "order_id": ["ORD-1", "ORD-2", "ORD-3"],
        "amount": [10.0, 25.5, 30.0]
    })
    passed, observed_pct, threshold, details = QualityRuleEvaluator.evaluate_completeness(
        df, "order_id", {"max_null_pct": 0.0}
    )
    assert passed is True
    assert observed_pct == 0.0
    assert details["null_count"] == 0


def test_completeness_fail_null_threshold():
    df = pd.DataFrame({
        "customer_id": ["C1", None, "C3", "C4", ""]
    })
    # 2 nulls out of 5 rows = 40%
    passed, observed_pct, threshold, details = QualityRuleEvaluator.evaluate_completeness(
        df, "customer_id", {"max_null_pct": 10.0}
    )
    assert passed is False
    assert observed_pct == 40.0
    assert details["null_count"] == 2


def test_completeness_missing_column():
    df = pd.DataFrame({"col_a": [1, 2, 3]})
    passed, observed_pct, threshold, details = QualityRuleEvaluator.evaluate_completeness(
        df, "missing_col", {"max_null_pct": 5.0}
    )
    assert passed is False
    assert observed_pct == 100.0
    assert "error" in details


def test_uniqueness_pass():
    df = pd.DataFrame({
        "sku": ["SKU-001", "SKU-002", "SKU-003"]
    })
    passed, dup_count, _, details = QualityRuleEvaluator.evaluate_uniqueness(
        df, "sku", {}
    )
    assert passed is True
    assert dup_count == 0.0
    assert details["duplicate_count"] == 0


def test_uniqueness_fail_duplicates():
    df = pd.DataFrame({
        "order_id": ["ORD-1", "ORD-2", "ORD-1", "ORD-3"]
    })
    passed, dup_count, _, details = QualityRuleEvaluator.evaluate_uniqueness(
        df, "order_id", {}
    )
    assert passed is False
    assert dup_count == 2.0
    assert "ORD-1" in details["sample_duplicate_keys"]


def test_uniqueness_missing_column():
    df = pd.DataFrame({"a": [1, 2]})
    passed, dup_count, _, details = QualityRuleEvaluator.evaluate_uniqueness(
        df, "non_existent", {}
    )
    assert passed is False
    assert "error" in details


def test_validity_regex_pass():
    df = pd.DataFrame({
        "email": ["user.one@example.com", "test.dev@sub.org"]
    })
    passed, invalid_count, _, details = QualityRuleEvaluator.evaluate_validity(
        df, "email", {"regex": r"^[\w\.-]+@[\w\.-]+\.\w+$"}
    )
    assert passed is True
    assert invalid_count == 0.0


def test_validity_regex_fail():
    df = pd.DataFrame({
        "email": ["valid@test.com", "not-an-email", "missing-at-domain.com"]
    })
    passed, invalid_count, _, details = QualityRuleEvaluator.evaluate_validity(
        df, "email", {"regex": r"^[\w\.-]+@[\w\.-]+\.\w+$"}
    )
    assert passed is False
    assert invalid_count == 2.0


def test_validity_min_value_pass():
    df = pd.DataFrame({"amount": [10.5, 20.0, 100.0]})
    passed, invalid_count, _, _ = QualityRuleEvaluator.evaluate_validity(
        df, "amount", {"min_value": 0.01}
    )
    assert passed is True
    assert invalid_count == 0.0


def test_validity_min_value_fail():
    df = pd.DataFrame({"amount": [50.0, -10.0, -0.5, 12.0]})
    passed, invalid_count, _, details = QualityRuleEvaluator.evaluate_validity(
        df, "amount", {"min_value": 0.0}
    )
    assert passed is False
    assert invalid_count == 2.0


def test_validity_allowed_values():
    df = pd.DataFrame({"status": ["COMPLETED", "PROCESSING", "UNKNOWN_STATUS", "SHIPPED"]})
    passed, invalid_count, _, details = QualityRuleEvaluator.evaluate_validity(
        df, "status", {"allowed_values": ["COMPLETED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]}
    )
    assert passed is False
    assert invalid_count == 1.0
    assert "UNKNOWN_STATUS" in details["sample_invalid_values"]


def test_schema_validation_pass():
    df = pd.DataFrame({
        "customer_id": ["C1"],
        "email": ["e@x.com"],
        "signup_date": ["2024-01-01"]
    })
    schema_def = {
        "columns": {
            "customer_id": {"type": "string", "nullable": False},
            "email": {"type": "string", "nullable": False},
            "signup_date": {"type": "timestamp", "nullable": True}
        },
        "allow_additive_columns": True
    }
    passed, observed, _, details = QualityRuleEvaluator.evaluate_schema(df, schema_def, {})
    assert passed is True
    assert observed == 0.0
    assert details["is_breaking"] is False


def test_schema_missing_required_column():
    df = pd.DataFrame({
        "customer_id": ["C1"]
        # 'email' missing
    })
    schema_def = {
        "columns": {
            "customer_id": {"type": "string", "nullable": False},
            "email": {"type": "string", "nullable": False}
        }
    }
    passed, observed, _, details = QualityRuleEvaluator.evaluate_schema(df, schema_def, {})
    assert passed is False
    assert "email" in details["missing_required_columns"]
    assert details["is_breaking"] is True


def test_schema_additive_columns_allowed():
    df = pd.DataFrame({
        "customer_id": ["C1"],
        "email": ["e@x.com"],
        "loyalty_tier": ["GOLD"]  # new additive column
    })
    schema_def = {
        "columns": {
            "customer_id": {"type": "string", "nullable": False},
            "email": {"type": "string", "nullable": False}
        },
        "allow_additive_columns": True
    }
    passed, observed, _, details = QualityRuleEvaluator.evaluate_schema(
        df, schema_def, {"allow_additive": True}
    )
    # Passed is False because schema drift is detected, but is_breaking is False (triggers auto-adoption)
    assert details["is_breaking"] is False
    assert details["is_additive_only"] is True
    assert "loyalty_tier" in details["unexpected_columns"]


def test_schema_additive_columns_disallowed():
    df = pd.DataFrame({
        "customer_id": ["C1"],
        "unexpected_data": ["surprise"]
    })
    schema_def = {
        "columns": {
            "customer_id": {"type": "string", "nullable": False}
        },
        "allow_additive_columns": False
    }
    passed, observed, _, details = QualityRuleEvaluator.evaluate_schema(
        df, schema_def, {"allow_additive": False}
    )
    assert passed is False
    assert details["is_breaking"] is True
