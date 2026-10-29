from typing import Dict, Any, List
import pandas as pd
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.metadata import IngestionBatch, DataQualityRule, ValidationResult
from app.quality.rules import QualityRuleEvaluator


class PostRecoveryVerifier:
    """
    Zero-defect post-recovery verification engine.
    Re-runs quality rules against healed data to verify complete resolution
    before allowing downstream transformation.
    """

    def __init__(self, db: Session):
        self.db = db

    def verify_repaired_data(
        self,
        batch: IngestionBatch,
        repaired_df: pd.DataFrame,
        failed_rule_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Re-tests failed rules on the healed dataset.
        Returns whether all checks passed along with detailed evidence.
        """
        logger.info(f"Running post-recovery verification for batch {batch.batch_id} on {len(repaired_df)} rows")

        rules_to_check = self.db.query(DataQualityRule).filter(
            DataQualityRule.rule_id.in_(failed_rule_ids)
        ).all()

        passed_all = True
        verification_details = []

        for rule in rules_to_check:
            passed = True
            observed = 0.0
            threshold = 0.0
            details = {}

            if rule.rule_type == "completeness":
                passed, observed, threshold, details = QualityRuleEvaluator.evaluate_completeness(
                    repaired_df, rule.column_name, rule.parameters
                )
            elif rule.rule_type == "uniqueness":
                passed, observed, threshold, details = QualityRuleEvaluator.evaluate_uniqueness(
                    repaired_df, rule.column_name, rule.parameters
                )
            elif rule.rule_type == "validity":
                passed, observed, threshold, details = QualityRuleEvaluator.evaluate_validity(
                    repaired_df, rule.column_name, rule.parameters
                )

            verification_details.append({
                "rule_id": rule.rule_id,
                "passed": passed,
                "observed_value": observed,
                "threshold": threshold,
                "details": details
            })

            if not passed:
                passed_all = False
                logger.error(
                    f"Post-recovery verification FAILED for rule '{rule.rule_id}'. "
                    f"Observed: {observed}, Threshold: {threshold}"
                )

        if passed_all:
            logger.info(f"Post-recovery verification PASSED for all {len(rules_to_check)} targeted rules!")

        return {
            "all_passed": passed_all,
            "checked_rules_count": len(rules_to_check),
            "verification_details": verification_details
        }

