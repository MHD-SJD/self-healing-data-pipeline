import json
import uuid
from typing import Dict, Any, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.logging import logger
from app.models.metadata import QuarantinedRecord, DatasetSchema, IngestionBatch


def _sanitize_record(row_dict: dict) -> dict:
    """Replaces NaN/NaT values with None and casts UUIDs/timestamps to strings for valid Postgres JSON."""
    sanitized = {}
    for k, v in row_dict.items():
        if pd.isna(v):
            sanitized[k] = None
        elif isinstance(v, uuid.UUID):
            sanitized[k] = str(v)
        elif hasattr(v, "isoformat"):
            sanitized[k] = v.isoformat()
        else:
            sanitized[k] = v
    return sanitized


class RecoveryStrategies:
    """Implements safe, policy-governed data recovery strategies."""

    @staticmethod
    def deduplicate(
        db: Session,
        df: pd.DataFrame,
        dataset_name: str,
        batch_id: uuid.UUID,
        incident_id: uuid.UUID,
        key_column: str = "order_id",
        time_column: str = "order_date",
        dry_run: bool = False
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Deduplicates records deterministically by primary key, keeping the latest timestamp record.
        Preserves discarded records in quarantined_records.
        """
        if key_column not in df.columns:
            return df, {"status": "SKIPPED", "reason": f"Key column {key_column} not found"}

        initial_count = len(df)
        duplicates_mask = df.duplicated(subset=[key_column], keep=False)
        duplicate_rows = df[duplicates_mask]
        num_duplicates = len(duplicate_rows)

        if num_duplicates == 0:
            return df, {"status": "NO_OP", "initial_count": initial_count, "retained_count": initial_count}

        # Sort by timestamp column if present, then drop duplicates keeping the last
        if time_column in df.columns:
            sorted_df = df.sort_values(by=[time_column], ascending=True)
            clean_df = sorted_df.drop_duplicates(subset=[key_column], keep="last").copy()
            discarded_df = sorted_df[sorted_df.duplicated(subset=[key_column], keep="last")]
        else:
            clean_df = df.drop_duplicates(subset=[key_column], keep="first").copy()
            discarded_df = df[df.duplicated(subset=[key_column], keep="first")]

        discarded_count = len(discarded_df)

        if not dry_run:
            # Record discarded records into quarantined_records table
            for _, row in discarded_df.iterrows():
                q_rec = QuarantinedRecord(
                    batch_id=batch_id,
                    incident_id=incident_id,
                    dataset_name=dataset_name,
                    source_identifier=str(row.get(key_column, "")),
                    record_content=_sanitize_record(row.to_dict()),
                    rejection_reason=f"Deterministic deduplication: duplicate key '{row.get(key_column)}' superseded by later record"
                )
                db.add(q_rec)
            db.commit()

        summary = {
            "strategy": "deduplicate",
            "dry_run": dry_run,
            "initial_rows": initial_count,
            "retained_rows": len(clean_df),
            "quarantined_duplicates": discarded_count,
            "key_column": key_column
        }
        return clean_df, summary

    @staticmethod
    def quarantine_missing_keys(
        db: Session,
        df: pd.DataFrame,
        dataset_name: str,
        batch_id: uuid.UUID,
        incident_id: uuid.UUID,
        key_column: str,
        dry_run: bool = False
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Isolates rows with missing mandatory identifiers into quarantined_records.
        Never invents missing business identifiers.
        """
        if key_column not in df.columns:
            return df, {"status": "SKIPPED", "reason": f"Column {key_column} not found"}

        initial_count = len(df)
        missing_mask = df[key_column].isna() | (df[key_column] == "") | (df[key_column].astype(str).str.lower() == "nan")
        missing_rows = df[missing_mask]
        clean_df = df[~missing_mask].copy()

        quarantined_count = len(missing_rows)

        if not dry_run and quarantined_count > 0:
            for _, row in missing_rows.iterrows():
                q_rec = QuarantinedRecord(
                    batch_id=batch_id,
                    incident_id=incident_id,
                    dataset_name=dataset_name,
                    source_identifier="MISSING_KEY",
                    record_content=_sanitize_record(row.to_dict()),
                    rejection_reason=f"Mandatory identifier '{key_column}' is null or empty"
                )
                db.add(q_rec)
            db.commit()

        summary = {
            "strategy": "quarantine_missing_keys",
            "dry_run": dry_run,
            "initial_rows": initial_count,
            "retained_rows": len(clean_df),
            "quarantined_rows": quarantined_count,
            "column": key_column
        }
        return clean_df, summary

    @staticmethod
    def quarantine_invalid_records(
        db: Session,
        df: pd.DataFrame,
        dataset_name: str,
        batch_id: uuid.UUID,
        incident_id: uuid.UUID,
        invalid_mask: pd.Series,
        rejection_reason: str,
        dry_run: bool = False
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Quarantines records failing validity rules (negative amounts, bad emails).
        """
        initial_count = len(df)
        invalid_rows = df[invalid_mask]
        clean_df = df[~invalid_mask].copy()

        quarantined_count = len(invalid_rows)

        if not dry_run and quarantined_count > 0:
            for _, row in invalid_rows.iterrows():
                q_rec = QuarantinedRecord(
                    batch_id=batch_id,
                    incident_id=incident_id,
                    dataset_name=dataset_name,
                    source_identifier=str(row.get("order_id", row.get("customer_id", row.get("product_id", "")))),
                    record_content=_sanitize_record(row.to_dict()),
                    rejection_reason=rejection_reason
                )
                db.add(q_rec)
            db.commit()

        summary = {
            "strategy": "quarantine_invalid_records",
            "dry_run": dry_run,
            "initial_rows": initial_count,
            "retained_rows": len(clean_df),
            "quarantined_rows": quarantined_count,
            "reason": rejection_reason
        }
        return clean_df, summary

    @staticmethod
    def adopt_additive_schema(
        db: Session,
        dataset_name: str,
        new_columns: list[str],
        batch_id: uuid.UUID,
        incident_id: uuid.UUID,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Automatically adopts new additive nullable columns by updating schema registry
        and altering raw tables.
        """
        latest_schema = db.query(DatasetSchema).filter(
            DatasetSchema.dataset_name == dataset_name,
            DatasetSchema.is_active == True
        ).order_by(DatasetSchema.version.desc()).first()

        current_version = latest_schema.version if latest_schema else 1
        new_version = current_version + 1

        new_schema_def = dict(latest_schema.schema_definition) if latest_schema else {"columns": {}}
        for col in new_columns:
            new_schema_def["columns"][col] = {"type": "string", "nullable": True, "added_in_version": new_version}

        if not dry_run:
            # Register new schema version
            updated_schema = DatasetSchema(
                dataset_name=dataset_name,
                version=new_version,
                schema_definition=new_schema_def,
                is_active=True
            )
            db.add(updated_schema)

            # Alter raw table if needed
            table_name = f"raw_{dataset_name}"
            for col in new_columns:
                try:
                    db.execute(text(f'ALTER TABLE raw_data.{table_name} ADD COLUMN IF NOT EXISTS "{col}" TEXT'))
                except Exception as e:
                    logger.warning(f"Column '{col}' already exists or alter error: {e}")
            db.commit()

        return {
            "strategy": "adopt_additive_schema",
            "dry_run": dry_run,
            "dataset_name": dataset_name,
            "previous_version": current_version,
            "new_version": new_version,
            "adopted_columns": new_columns
        }

