import uuid
from typing import Dict, Any, List, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.metadata import (
    IngestionBatch, DataQualityRule, ValidationResult, DetectedAnomaly, DatasetSchema
)
from app.quality.rules import QualityRuleEvaluator
from app.quality.statistical import StatisticalProfileMonitor


class QualityEngine:
    def __init__(self, db: Session):
        self.db = db

    def validate_batch(
        self,
        batch: IngestionBatch,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Runs comprehensive data quality checks on an ingested batch.
        Logs each result to the metadata store.
        """
        dataset_name = batch.dataset_name
        logger.info(f"Executing Data Quality Engine for dataset '{dataset_name}', batch {batch.batch_id}")

        rules: List[DataQualityRule] = self.db.query(DataQualityRule).filter(
            DataQualityRule.dataset_name == dataset_name,
            DataQualityRule.is_active == True
        ).all()

        validation_results = []
        all_passed = True
        has_critical_failure = False

        # Load active dataset schema definition
        active_schema = self.db.query(DatasetSchema).filter(
            DatasetSchema.dataset_name == dataset_name,
            DatasetSchema.is_active == True
        ).order_by(DatasetSchema.version.desc()).first()
        schema_def = active_schema.schema_definition if active_schema else {}

        for rule in rules:
            passed = True
            observed = 0.0
            threshold = 0.0
            details = {}

            if rule.rule_type == "completeness":
                passed, observed, threshold, details = QualityRuleEvaluator.evaluate_completeness(
                    df, rule.column_name, rule.parameters
                )
            elif rule.rule_type == "uniqueness":
                passed, observed, threshold, details = QualityRuleEvaluator.evaluate_uniqueness(
                    df, rule.column_name, rule.parameters
                )
            elif rule.rule_type == "validity":
                passed, observed, threshold, details = QualityRuleEvaluator.evaluate_validity(
                    df, rule.column_name, rule.parameters
                )
            elif rule.rule_type == "schema":
                passed, observed, threshold, details = QualityRuleEvaluator.evaluate_schema(
                    df, schema_def, rule.parameters
                )
            elif rule.rule_type == "distribution":
                # Distribution evaluated below
                continue

            result = ValidationResult(
                batch_id=batch.batch_id,
                run_id=batch.run_id,
                rule_id=rule.rule_id,
                passed=passed,
                observed_value=round(observed, 2),
                expected_threshold=round(threshold, 2),
                severity=rule.severity,
                failure_details=details
            )
            self.db.add(result)
            validation_results.append(result)

            if not passed:
                all_passed = False
                if rule.severity == "CRITICAL":
                    has_critical_failure = True
                logger.warning(
                    f"Quality rule '{rule.rule_id}' FAILED for {dataset_name}. "
                    f"Observed: {observed}, Threshold: {threshold}, Severity: {rule.severity}"
                )

        # Statistical Anomaly Monitoring
        detected_anomalies = []
        vol_anomaly = StatisticalProfileMonitor.detect_volume_anomaly(
            self.db, dataset_name, len(df)
        )
        if vol_anomaly:
            anomaly_rec = DetectedAnomaly(
                batch_id=batch.batch_id,
                dataset_name=dataset_name,
                metric_name=vol_anomaly["metric_name"],
                observed_metric=vol_anomaly["observed_metric"],
                baseline_mean=vol_anomaly["baseline_mean"],
                baseline_stddev=vol_anomaly["baseline_stddev"],
                z_score=vol_anomaly["z_score"],
                anomaly_type=vol_anomaly["anomaly_type"],
                severity=vol_anomaly["severity"]
            )
            self.db.add(anomaly_rec)
            detected_anomalies.append(anomaly_rec)

        # Check numeric metric distribution for specific datasets
        if dataset_name == "orders" and "amount" in df.columns:
            # Baseline expected order mean between $20 and $1000
            metric_anomaly = StatisticalProfileMonitor.detect_numeric_metric_anomaly(
                df, "amount", expected_mean_range=(20.0, 1000.0)
            )
            if metric_anomaly:
                anomaly_rec = DetectedAnomaly(
                    batch_id=batch.batch_id,
                    dataset_name=dataset_name,
                    metric_name=metric_anomaly["metric_name"],
                    observed_metric=metric_anomaly["observed_metric"],
                    baseline_mean=metric_anomaly["baseline_mean"],
                    baseline_stddev=metric_anomaly["baseline_stddev"],
                    z_score=metric_anomaly["z_score"],
                    anomaly_type=metric_anomaly["anomaly_type"],
                    severity=metric_anomaly["severity"]
                )
                self.db.add(anomaly_rec)
                detected_anomalies.append(anomaly_rec)

        self.db.commit()

        return {
            "all_passed": all_passed,
            "has_critical_failure": has_critical_failure,
            "total_checks": len(validation_results),
            "failed_checks": [r for r in validation_results if not r.passed],
            "anomalies": detected_anomalies
        }
