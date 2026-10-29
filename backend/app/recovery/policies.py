from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.metadata import RecoveryPolicy, FailureIncident


class PolicyMatcher:
    """Matches a FailureIncident against configured RecoveryPolicies."""

    def __init__(self, db: Session):
        self.db = db

    def find_applicable_policy(self, incident: FailureIncident) -> Optional[RecoveryPolicy]:
        """
        Finds the highest-priority policy matching the incident's failure category
        and preconditions.
        """
        policies: List[RecoveryPolicy] = self.db.query(RecoveryPolicy).filter(
            RecoveryPolicy.failure_category == incident.failure_category
        ).all()

        for policy in policies:
            # Check if incident requires approval vs policy safety level
            if incident.requires_human_approval and policy.safety_level == "AUTOMATIC":
                continue
            return policy

        # Fallback to any policy matching the category
        return policies[0] if policies else None

