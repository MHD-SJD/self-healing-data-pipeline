import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.metadata import (
    FailureIncident, IngestionBatch, RecoveryPolicy, RecoveryAttempt, AuditEvent
)
from app.recovery.policies import PolicyMatcher
from app.recovery.strategies import RecoveryStrategies
from app.recovery.verifier import PostRecoveryVerifier
from app.classification.taxonomy import IncidentStatus, RecoverySafetyLevel


class RecoveryEngine:
    """
    Orchestrates policy matching, recovery execution, dry-run previews,
    safety gating, and post-recovery verification.
    """

    def __init__(self, db: Session):
        self.db = db
        self.policy_matcher = PolicyMatcher(db)
        self.verifier = PostRecoveryVerifier(db)

    def recover(
        self,
        incident: FailureIncident,
        df: pd.DataFrame,
        dry_run: bool = False,
        approved_by: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Executes policy-driven recovery for a specific incident.
        Returns the (potentially modified/healed) DataFrame and an execution summary.
        """
        start_time = time.time()
        logger.info(
            f"Recovery Engine initiated for Incident {incident.incident_id} (Category: {incident.failure_category}, Dry-Run: {dry_run})"
        )

        # 1. Match Policy
        policy = self.policy_matcher.find_applicable_policy(incident)
        if not policy:
            logger.warning(f"No recovery policy found for category {incident.failure_category}")
            return df, {
                "status": "NO_POLICY",
                "message": f"No active policy for {incident.failure_category}"
            }

        # 2. Safety Gating & Preconditions
        if policy.safety_level in [RecoverySafetyLevel.REQUIRES_APPROVAL.value, RecoverySafetyLevel.MANUAL_ONLY.value]:
            if not approved_by and not dry_run:
                incident.status = IncidentStatus.PENDING_APPROVAL.value
                self.db.commit()
                return df, {
                    "status": "PENDING_APPROVAL",
                    "policy_id": policy.policy_id,
                    "message": "Action requires human approval before proceeding."
                }

        # 3. Create Recovery Attempt Record (if not dry-run)
        attempt = None
        if not dry_run:
            incident.status = IncidentStatus.HEALING_IN_PROGRESS.value
            attempt = RecoveryAttempt(
                incident_id=incident.incident_id,
                policy_id=policy.policy_id,
                strategy_applied=incident.recommended_action,
                status="IN_PROGRESS",
                approved_by=approved_by,
                executed_at=datetime.utcnow()
            )
            self.db.add(attempt)
            self.db.commit()

        # 4. Strategy Dispatch
        repaired_df = df.copy()
        strategy_summary = {}
        category = incident.failure_category
        batch_id = incident.batch_id or uuid.uuid4()

        try:
            if category == "DUPLICATE_DATA":
                key_col = "order_id" if incident.dataset_name == "orders" else ("customer_id" if incident.dataset_name == "customers" else "sku")
                time_col = "order_date" if incident.dataset_name == "orders" else ("signup_date" if incident.dataset_name == "customers" else "last_restocked_at")
                repaired_df, strategy_summary = RecoveryStrategies.deduplicate(
                    self.db, df, incident.dataset_name, batch_id, incident.incident_id,
                    key_column=key_col, time_column=time_col, dry_run=dry_run
                )

            elif category == "MISSING_DATA":
                key_col = "order_id" if incident.dataset_name == "orders" else ("customer_id" if incident.dataset_name == "customers" else "product_id")
                repaired_df, strategy_summary = RecoveryStrategies.quarantine_missing_keys(
                    self.db, df, incident.dataset_name, batch_id, incident.incident_id,
                    key_column=key_col, dry_run=dry_run
                )

            elif category == "SCHEMA_DRIFT":
                evidence = incident.evidence or {}
                rules_failed = evidence.get("rules_failed", [])
                details = evidence.get("details", [{}])[0]
                unexpected_cols = details.get("unexpected_columns", [])
                strategy_summary = RecoveryStrategies.adopt_additive_schema(
                    self.db, incident.dataset_name, unexpected_cols, batch_id, incident.incident_id, dry_run=dry_run
                )

            elif category == "INVALID_RECORDS":
                # Evaluate invalid rows (e.g. negative amount or invalid email)
                invalid_mask = pd.Series(False, index=df.index)
                reason = "Invalid record detected"
                if incident.dataset_name == "orders" and "amount" in df.columns:
                    amounts = pd.to_numeric(df["amount"], errors="coerce")
                    invalid_mask = amounts < 0
                    reason = "Violation: Negative order amount prohibited"
                elif incident.dataset_name == "customers" and "email" in df.columns:
                    invalid_mask = ~df["email"].astype(str).str.contains(r"^[\w\.-]+@[\w\.-]+\.\w+$")
                    reason = "Violation: Malformed customer email address"

                repaired_df, strategy_summary = RecoveryStrategies.quarantine_invalid_records(
                    self.db, df, incident.dataset_name, batch_id, incident.incident_id,
                    invalid_mask=invalid_mask, rejection_reason=reason, dry_run=dry_run
                )

            elif category == "DISTRIBUTION_ANOMALY":
                strategy_summary = {
                    "strategy": "pause_downstream_publication",
                    "action": "flagged_and_paused",
                    "dry_run": dry_run
                }

            # 5. Post-Recovery Verification
            failed_rule_ids = incident.evidence.get("rules_failed", []) if incident.evidence else []
            verification_result = {"all_passed": True}

            if not dry_run and failed_rule_ids:
                batch = self.db.query(IngestionBatch).filter(IngestionBatch.batch_id == batch_id).first()
                if batch:
                    verification_result = self.verifier.verify_repaired_data(
                        batch, repaired_df, failed_rule_ids
                    )

            duration_ms = int((time.time() - start_time) * 1000)

            # 6. Finalize Status
            if not dry_run and attempt:
                all_verified = verification_result.get("all_passed", True)
                attempt.status = "SUCCESS" if all_verified else "FAILED"
                attempt.duration_ms = duration_ms
                attempt.execution_log = f"Strategy: {incident.recommended_action}. Summary: {strategy_summary}"
                attempt.post_verification_passed = all_verified
                attempt.post_verification_details = verification_result

                if all_verified:
                    incident.status = IncidentStatus.RESOLVED.value
                    incident.resolved_at = datetime.utcnow()
                else:
                    incident.status = IncidentStatus.ESCALATED_HUMAN_REQUIRED.value

                # Log Audit Event
                audit = AuditEvent(
                    entity_type="INCIDENT",
                    entity_id=str(incident.incident_id),
                    event_type="HEALED" if all_verified else "HEAL_FAILED",
                    actor=approved_by or "SYSTEM_AUTOPILOT",
                    details={
                        "attempt_id": str(attempt.attempt_id),
                        "duration_ms": duration_ms,
                        "verified": all_verified,
                        "strategy": incident.recommended_action
                    }
                )
                self.db.add(audit)
                self.db.commit()

            return repaired_df, {
                "status": "SUCCESS" if verification_result.get("all_passed", True) else "FAILED",
                "dry_run": dry_run,
                "strategy_summary": strategy_summary,
                "verification": verification_result,
                "duration_ms": duration_ms
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Recovery failed with exception: {e}", exc_info=True)
            if not dry_run and attempt:
                attempt.status = "FAILED"
                attempt.execution_log = str(e)
                attempt.duration_ms = int((time.time() - start_time) * 1000)
                incident.status = IncidentStatus.ESCALATED_HUMAN_REQUIRED.value
                self.db.commit()
            return df, {"status": "ERROR", "error": str(e)}

