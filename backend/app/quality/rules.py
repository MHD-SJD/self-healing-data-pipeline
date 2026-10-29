import re
from typing import Dict, Any, Tuple, List
import pandas as pd
import numpy as np


class QualityRuleEvaluator:
    """Evaluates individual data quality rules against a pandas DataFrame."""

    @staticmethod
    def evaluate_completeness(df: pd.DataFrame, column: str, params: Dict[str, Any]) -> Tuple[bool, float, float, Dict[str, Any]]:
        """
        Validates null rate and required presence.
        Returns: (passed, observed_null_pct, max_threshold, details)
        """
        max_null_pct = float(params.get("max_null_pct", 0.0))
        if column not in df.columns:
            return False, 100.0, max_null_pct, {"error": f"Required column '{column}' missing from dataset"}

        total_rows = len(df)
        if total_rows == 0:
            return True, 0.0, max_null_pct, {"total_rows": 0}

        null_count = int(df[column].isna().sum() + (df[column] == "").sum() + (df[column].str.lower() == "nan").sum())
        null_pct = round((null_count / total_rows) * 100.0, 2)
        passed = null_pct <= max_null_pct

        details = {
            "total_rows": total_rows,
            "null_count": null_count,
            "null_percentage": null_pct,
            "threshold_max_pct": max_null_pct
        }
        return passed, null_pct, max_null_pct, details

    @staticmethod
    def evaluate_uniqueness(df: pd.DataFrame, column: str, params: Dict[str, Any]) -> Tuple[bool, float, float, Dict[str, Any]]:
        """
        Validates primary key uniqueness.
        Returns: (passed, observed_duplicate_count, expected_duplicates, details)
        """
        if column not in df.columns:
            return False, 0.0, 0.0, {"error": f"Primary key column '{column}' not found"}

        total_rows = len(df)
        if total_rows == 0:
            return True, 0.0, 0.0, {"total_rows": 0}

        # Filter out NaN/null for uniqueness check
        valid_series = df[column].dropna()
        duplicates = valid_series[valid_series.duplicated(keep=False)]
        dup_count = int(len(duplicates))
        passed = dup_count == 0

        details = {
            "total_rows": total_rows,
            "duplicate_count": dup_count,
            "sample_duplicate_keys": duplicates.unique()[:5].tolist() if dup_count > 0 else []
        }
        return passed, float(dup_count), 0.0, details

    @staticmethod
    def evaluate_validity(df: pd.DataFrame, column: str, params: Dict[str, Any]) -> Tuple[bool, float, float, Dict[str, Any]]:
        """
        Validates regex patterns, numeric ranges, and allowed enum values.
        """
        if column not in df.columns:
            return False, 0.0, 0.0, {"error": f"Column '{column}' not found"}

        total_rows = len(df)
        if total_rows == 0:
            return True, 0.0, 0.0, {"total_rows": 0}

        invalid_indices = []
        
        # 1. Regex check
        if "regex" in params:
            pattern = re.compile(params["regex"])
            for idx, val in df[column].dropna().items():
                if not pattern.match(str(val).strip()):
                    invalid_indices.append(idx)

        # 2. Min value (numeric)
        if "min_value" in params:
            min_val = float(params["min_value"])
            numeric_vals = pd.to_numeric(df[column], errors="coerce")
            below_min = numeric_vals[numeric_vals < min_val].index.tolist()
            invalid_indices.extend(below_min)

        # 3. Allowed enum values
        if "allowed_values" in params:
            allowed = set(params["allowed_values"])
            for idx, val in df[column].dropna().items():
                if str(val).strip().upper() not in allowed and str(val).strip() not in allowed:
                    invalid_indices.append(idx)

        invalid_count = len(set(invalid_indices))
        passed = invalid_count == 0

        details = {
            "total_rows": total_rows,
            "invalid_count": invalid_count,
            "sample_invalid_values": df.loc[list(set(invalid_indices))[:5], column].tolist() if invalid_count > 0 else []
        }
        return passed, float(invalid_count), 0.0, details

    @staticmethod
    def evaluate_schema(df: pd.DataFrame, schema_def: Dict[str, Any], params: Dict[str, Any]) -> Tuple[bool, float, float, Dict[str, Any]]:
        """
        Evaluates schema contract: missing required columns, new additive columns, type changes.
        """
        expected_cols = schema_def.get("columns", {})
        actual_cols = set(df.columns)
        # Exclude internal metadata columns
        actual_clean_cols = {c for c in actual_cols if not c.startswith("_")}

        missing_required = []
        for col_name, col_meta in expected_cols.items():
            if not col_meta.get("nullable", True) and col_name not in actual_clean_cols:
                missing_required.append(col_name)

        unexpected_cols = list(actual_clean_cols - set(expected_cols.keys()))
        allow_additive = params.get("allow_additive", schema_def.get("allow_additive_columns", True))

        is_breaking = len(missing_required) > 0 or (len(unexpected_cols) > 0 and not allow_additive)
        passed = (not is_breaking) and (len(unexpected_cols) == 0)

        details = {
            "missing_required_columns": missing_required,
            "unexpected_columns": unexpected_cols,
            "is_additive_only": len(missing_required) == 0 and len(unexpected_cols) > 0 and allow_additive,
            "is_breaking": is_breaking
        }
        observed = float(len(missing_required) + len(unexpected_cols))
        return passed, observed, 0.0, details

