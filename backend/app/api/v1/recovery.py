import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.metadata import RecoveryAttempt, FailureIncident, QuarantinedRecord
from app.schemas.recovery import (
    RecoveryAttemptResponse, DryRunRequest, DryRunResponse, ApproveRequest
)
from app.recovery.engine import RecoveryEngine
import pandas as pd

router = APIRouter(prefix="/recovery", tags=["Self-Healing & Recovery"])


@router.get("/attempts", response_model=List[RecoveryAttemptResponse])
def list_recovery_attempts(
    incident_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Lists audit logs of all automated and manual recovery attempts."""
    query = db.query(RecoveryAttempt)
    if incident_id:
        query = query.filter(RecoveryAttempt.incident_id == incident_id)
    if status:
        query = query.filter(RecoveryAttempt.status == status)

    return query.order_by(RecoveryAttempt.executed_at.desc()).offset(offset).limit(limit).all()


@router.post("/dry-run", response_model=DryRunResponse)
def dry_run_recovery(payload: DryRunRequest, db: Session = Depends(get_db)):
    """
    Simulates recovery action in dry-run mode without mutating data or altering state.
    Returns impact prediction and summary.
    """
    incident = db.query(FailureIncident).filter(FailureIncident.incident_id == payload.incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    recovery_engine = RecoveryEngine(db)

    # Load raw data if available
    raw_table = f"raw_{incident.dataset_name}"
    df = pd.DataFrame()
    if incident.batch_id:
        try:
            df = pd.read_sql(
                f"SELECT * FROM raw_data.{raw_table} WHERE _batch_id = '{str(incident.batch_id)}'",
                con=db.bind
            )
        except Exception:
            pass

    _, summary = recovery_engine.recover(
        incident=incident,
        df=df,
        dry_run=True
    )

    strat_summary = summary.get("strategy_summary", {})
    impacted = strat_summary.get("quarantined_duplicates", strat_summary.get("quarantined_rows", 0))

    return DryRunResponse(
        incident_id=incident.incident_id,
        strategy=incident.recommended_action,
        proposed_action=f"Execute {incident.recommended_action} with isolation to quarantined_records",
        impacted_rows=impacted,
        will_require_approval=incident.requires_human_approval,
        summary=summary
    )


@router.post("/{attempt_id}/approve")
def approve_recovery(
    attempt_id: uuid.UUID,
    payload: ApproveRequest = ApproveRequest(),
    db: Session = Depends(get_db)
):
    """Approves a pending recovery attempt or incident requiring human authorization."""
    attempt = db.query(RecoveryAttempt).filter(RecoveryAttempt.attempt_id == attempt_id).first()
    incident = None
    if attempt:
        incident = attempt.incident
    else:
        # Fallback: check if attempt_id was passed as incident_id
        incident = db.query(FailureIncident).filter(FailureIncident.incident_id == attempt_id).first()

    if not incident:
        raise HTTPException(status_code=404, detail="Recovery attempt / Incident not found")

    recovery_engine = RecoveryEngine(db)
    raw_table = f"raw_{incident.dataset_name}"
    df = pd.DataFrame()
    if incident.batch_id:
        try:
            df = pd.read_sql(
                f"SELECT * FROM raw_data.{raw_table} WHERE _batch_id = '{str(incident.batch_id)}'",
                con=db.bind
            )
        except Exception:
            pass

    _, summary = recovery_engine.recover(
        incident=incident,
        df=df,
        dry_run=False,
        approved_by=payload.approved_by
    )

    return {
        "status": "APPROVED_AND_EXECUTED",
        "incident_id": str(incident.incident_id),
        "approved_by": payload.approved_by,
        "summary": summary
    }


@router.get("/quarantine")
def list_quarantined_records(
    dataset: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieves isolated quarantined records with rejection reasons."""
    query = db.query(QuarantinedRecord)
    if dataset:
        query = query.filter(QuarantinedRecord.dataset_name == dataset)

    records = query.order_by(QuarantinedRecord.quarantined_at.desc()).offset(offset).limit(limit).all()
    return [
        {
            "quarantine_id": str(r.quarantine_id),
            "batch_id": str(r.batch_id) if r.batch_id else None,
            "incident_id": str(r.incident_id) if r.incident_id else None,
            "dataset_name": r.dataset_name,
            "source_identifier": r.source_identifier,
            "rejection_reason": r.rejection_reason,
            "record_content": r.record_content,
            "quarantined_at": r.quarantined_at
        }
        for r in records
    ]

