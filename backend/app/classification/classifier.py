import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.metadata import (
    FailureIncident, ValidationResult, DetectedAnomaly, IngestionBatch
)
from app.classification.taxonomy import FailureCategory, IncidentSeverity, IncidentStatus


class FailureClassifier:
    """
    Deterministic rule-based classification engine that maps validation failures,
    anomalies, and runtime errors to concrete failure categories and recovery actions.
    """

    def __init__(self, db: Session):
        self.db = db

    def classify_and_record(
        self,
        run_id: uuid.UUID,
        batch: Optional[IngestionBatch],
        dataset_name: str,
        failed_results: List[ValidationResult],
        anomalies: List[DetectedAnomaly],
        runtime_exception: Optional[Exception] = None
    ) -> List[FailureIncident]:
        """
        Analyzes all failure signals for a batch/run and creates structured FailureIncident records.
        """
        incidents: List[FailureIncident] = []
        batch_id = batch.batch_id if batch else None

        # 1. Check for Runtime / Ingestion / Timeout Exception
        if runtime_exception:
            exc_str = str(runtime_exception).lower()
            if "timeout" in exc_str or "connection" in exc_str or "network" in exc_str:
                category = FailureCategory.INFRASTRUCTURE_OR_TIMEOUT_FAILURE
                action = "retry_with_backoff"
                requires_human = False
            elif "file" in exc_str or "csv" in exc_str or "ingest" in exc_str:
                category = FailureCategory.INGESTION_FAILURE
                action = "retry_ingestion_or_check_source"
                requires_human = False
            elif "dbt" in exc_str or "transform" in exc_str:
                category = FailureCategory.TRANSFORMATION_FAILURE
                action = "halt_and_preserve_logs"
                requires_human = True
            else:
                category = FailureCategory.UNKNOWN_FAILURE
                action = "escalate_for_human_investigation"
                requires_human = True

            incident = FailureIncident(
                run_id=run_id,
                batch_id=batch_id,
                dataset_name=dataset_name,
                failure_category=category.value,
                severity=IncidentSeverity.CRITICAL.value,
                explanation=f"Runtime exception occurred: {str(runtime_exception)}",
                evidence={"exception_type": type(runtime_exception).__name__, "message": str(runtime_exception)},
                recommended_action=action,
                status=IncidentStatus.OPEN.value,
                requires_human_approval=requires_human
            )
            self.db.add(incident)
            incidents.append(incident)

        # 2. Check for Statistical Anomalies
        for anomaly in anomalies:
            incident = FailureIncident(
                run_id=run_id,
                batch_id=batch_id,
                dataset_name=dataset_name,
                failure_category=FailureCategory.DISTRIBUTION_ANOMALY.value,
                severity=anomaly.severity or IncidentSeverity.WARNING.value,
                explanation=(
                    f"Statistical anomaly detected in '{anomaly.metric_name}': "
                    f"Observed {anomaly.observed_metric} deviates from baseline mean {anomaly.baseline_mean} "
                    f"(z-score: {anomaly.z_score})"
                ),
                evidence={
                    "metric_name": anomaly.metric_name,
                    "observed": float(anomaly.observed_metric),
                    "baseline_mean": float(anomaly.baseline_mean) if anomaly.baseline_mean else None,
                    "z_score": float(anomaly.z_score) if anomaly.z_score else None,
                    "type": anomaly.anomaly_type
                },
                recommended_action="pause_downstream_and_request_approval",
                status=IncidentStatus.OPEN.value,
                requires_human_approval=True
            )
            self.db.add(incident)
            incidents.append(incident)

        # 3. Classify Data Quality Validation Failures
        category_groups: Dict[FailureCategory, List[ValidationResult]] = {}
        for r in failed_results:
            details = r.failure_details or {}
            rule_id = r.rule_id

            if "req_" in rule_id or "completeness" in rule_id:
                cat = FailureCategory.MISSING_DATA
            elif "unique_" in rule_id or "uniqueness" in rule_id:
                cat = FailureCategory.DUPLICATE_DATA
            elif "schema" in rule_id:
                cat = FailureCategory.SCHEMA_DRIFT
            else:
                cat = FailureCategory.INVALID_RECORDS

            category_groups.setdefault(cat, []).append(r)

        for cat, results in category_groups.items():
            # Determine highest severity
            severities = [r.severity for r in results]
            overall_severity = IncidentSeverity.CRITICAL.value if "CRITICAL" in severities else IncidentSeverity.ERROR.value

            evidence = {"rules_failed": [r.rule_id for r in results], "details": [r.failure_details for r in results]}

            if cat == FailureCategory.MISSING_DATA:
                explanation = f"Dataset '{dataset_name}' contains unacceptable null rates or missing mandatory identifiers."
                recommended_action = "quarantine_missing_records"
                requires_human = False

            elif cat == FailureCategory.DUPLICATE_DATA:
                explanation = f"Dataset '{dataset_name}' contains duplicate records violating primary key uniqueness constraints."
                recommended_action = "deduplicate_retaining_latest"
                requires_human = False

            elif cat == FailureCategory.SCHEMA_DRIFT:
                # Check if additive only or breaking
                is_breaking = any(r.failure_details.get("is_breaking", False) for r in results if r.failure_details)
                if is_breaking:
                    explanation = f"Breaking schema drift detected in '{dataset_name}' (missing required column or non-additive type change)."
                    recommended_action = "quarantine_batch_require_approval"
                    requires_human = True
                    overall_severity = IncidentSeverity.CRITICAL.value
                else:
                    explanation = f"Additive schema drift detected in '{dataset_name}' (new compatible nullable column)."
                    recommended_action = "adopt_additive_columns"
                    requires_human = False
                    overall_severity = IncidentSeverity.INFO.value

            elif cat == FailureCategory.INVALID_RECORDS:
                explanation = f"Dataset '{dataset_name}' contains records violating business validation rules (e.g. negative amount, invalid email)."
                recommended_action = "quarantine_invalid_rows"
                requires_human = False

            else:
                explanation = f"Unclassified quality failures in '{dataset_name}'."
                recommended_action = "investigate"
                requires_human = True

            incident = FailureIncident(
                run_id=run_id,
                batch_id=batch_id,
                dataset_name=dataset_name,
                failure_category=cat.value,
                severity=overall_severity,
                explanation=explanation,
                evidence=evidence,
                recommended_action=recommended_action,
                status=IncidentStatus.OPEN.value,
                requires_human_approval=requires_human
            )
            self.db.add(incident)
            incidents.append(incident)

        self.db.commit()
        for inc in incidents:
            logger.info(
                f"Incident opened: ID={inc.incident_id}, Category={inc.failure_category}, "
                f"Severity={inc.severity}, Action={inc.recommended_action}"
            )
        return incidents

