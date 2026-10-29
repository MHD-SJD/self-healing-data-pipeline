import os
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.metadata import (
    Pipeline, PipelineRun, IngestionBatch, FailureIncident
)
from app.ingestion.orders_ingestion import OrdersIngester
from app.ingestion.customers_ingestion import CustomersIngester
from app.ingestion.inventory_ingestion import InventoryIngester
from app.quality.engine import QualityEngine
from app.classification.classifier import FailureClassifier
from app.recovery.engine import RecoveryEngine


class PipelineExecutionService:
    """
    Coordinates the full self-healing data pipeline lifecycle:
    Ingestion -> Quality Check -> Anomaly Detection -> Classification -> Recovery -> Verification -> dbt
    """

    def __init__(self, db: Session):
        self.db = db
        self.quality_engine = QualityEngine(db)
        self.classifier = FailureClassifier(db)
        self.recovery_engine = RecoveryEngine(db)

    def trigger_pipeline_run(
        self,
        pipeline_id: str,
        custom_filepath: Optional[Path] = None,
        trigger_type: str = "MANUAL",
        auto_heal: bool = True
    ) -> Dict[str, Any]:
        """Runs the complete self-healing pipeline end-to-end."""
        start_time = time.time()
        pipeline = self.db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
        if not pipeline:
            raise ValueError(f"Pipeline '{pipeline_id}' not found.")

        # Create Run record
        run = PipelineRun(
            pipeline_id=pipeline_id,
            status="RUNNING",
            trigger_type=trigger_type,
            started_at=datetime.utcnow()
        )
        self.db.add(run)
        self.db.commit()

        dataset_name = "orders"
        if "customer" in pipeline_id:
            dataset_name = "customers"
        elif "inventory" in pipeline_id:
            dataset_name = "inventory"

        # Determine file path
        if custom_filepath:
            filepath = custom_filepath
        else:
            filepath = settings.SAMPLES_DIR / f"{dataset_name}.csv"

        logger.info(f"Pipeline run {run.run_id} initiated for pipeline '{pipeline_id}', dataset '{dataset_name}'")

        try:
            # 1. Ingestion
            if dataset_name == "customers":
                ingester = CustomersIngester(self.db)
            elif dataset_name == "inventory":
                ingester = InventoryIngester(self.db)
            else:
                ingester = OrdersIngester(self.db)

            batch, df = ingester.ingest(filepath, run.run_id)

            # 2. Quality Validation & Anomaly Detection
            validation_summary = self.quality_engine.validate_batch(batch, df)
            all_passed = validation_summary["all_passed"]
            failed_checks = validation_summary["failed_checks"]
            anomalies = validation_summary["anomalies"]

            incidents = []
            recovery_summaries = []
            final_df = df

            # 3. If quality violations detected: Classify & Heal
            if not all_passed or len(anomalies) > 0:
                logger.warning(
                    f"Violations detected in run {run.run_id} ({len(failed_checks)} failed rules, {len(anomalies)} anomalies). Launching classifier."
                )
                incidents = self.classifier.classify_and_record(
                    run_id=run.run_id,
                    batch=batch,
                    dataset_name=dataset_name,
                    failed_results=failed_checks,
                    anomalies=anomalies
                )

                if auto_heal:
                    for incident in incidents:
                        if not incident.requires_human_approval:
                            final_df, rec_summary = self.recovery_engine.recover(
                                incident=incident,
                                df=final_df,
                                dry_run=False
                            )
                            recovery_summaries.append(rec_summary)

            # Check final resolution status
            unresolved_incidents = [inc for inc in incidents if inc.status != "RESOLVED"]

            if not incidents:
                run.status = "COMPLETED"
            elif not unresolved_incidents:
                run.status = "HEALED"
            elif any(inc.status == "PENDING_APPROVAL" for inc in unresolved_incidents):
                run.status = "PENDING_APPROVAL"
            else:
                run.status = "ESCALATED"

            # 4. Trigger dbt transformations if pipeline is COMPLETED or HEALED
            dbt_result = None
            if run.status in ["COMPLETED", "HEALED"]:
                dbt_result = self.run_dbt_transformations(select_model=f"stg_{dataset_name}")

            duration_ms = int((time.time() - start_time) * 1000)
            run.completed_at = datetime.utcnow()
            run.duration_ms = duration_ms
            run.metadata_payload = {
                "dataset": dataset_name,
                "input_rows": len(df),
                "output_rows": len(final_df),
                "incidents_count": len(incidents),
                "unresolved_count": len(unresolved_incidents),
                "dbt_result": dbt_result
            }
            self.db.commit()

            return {
                "run_id": str(run.run_id),
                "pipeline_id": pipeline_id,
                "dataset_name": dataset_name,
                "status": run.status,
                "duration_ms": duration_ms,
                "input_rows": len(df),
                "output_rows": len(final_df),
                "incidents": [
                    {
                        "incident_id": str(inc.incident_id),
                        "category": inc.failure_category,
                        "severity": inc.severity,
                        "status": inc.status,
                        "action": inc.recommended_action
                    }
                    for inc in incidents
                ],
                "recoveries": recovery_summaries,
                "dbt_status": dbt_result.get("status") if dbt_result else "SKIPPED"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Pipeline run {run.run_id} crashed: {e}", exc_info=True)
            # Record runtime failure incident
            self.classifier.classify_and_record(
                run_id=run.run_id,
                batch=None,
                dataset_name=dataset_name,
                failed_results=[],
                anomalies=[],
                runtime_exception=e
            )
            run.status = "FAILED"
            run.completed_at = datetime.utcnow()
            run.duration_ms = int((time.time() - start_time) * 1000)
            run.error_message = str(e)
            self.db.commit()
            return {
                "run_id": str(run.run_id),
                "pipeline_id": pipeline_id,
                "status": "FAILED",
                "error": str(e)
            }

    def run_dbt_transformations(self, select_model: Optional[str] = None) -> Dict[str, Any]:
        """Executes dbt core run and test for staging/analytics models."""
        dbt_dir = settings.DBT_PROJECT_DIR
        if not dbt_dir.exists():
            return {"status": "SKIPPED", "message": "dbt project directory not found"}

        try:
            cmd = ["dbt", "run", "--profiles-dir", str(dbt_dir), "--project-dir", str(dbt_dir)]
            if select_model:
                cmd.extend(["--select", select_model])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            return {
                "status": "SUCCESS" if result.returncode == 0 else "FAILED",
                "exit_code": result.returncode,
                "stdout": result.stdout[-500:] if result.stdout else "",
                "stderr": result.stderr[-500:] if result.stderr else ""
            }
        except Exception as e:
            logger.error(f"dbt execution error: {e}")
            return {"status": "ERROR", "error": str(e)}

