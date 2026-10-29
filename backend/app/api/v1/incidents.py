import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.metadata import FailureIncident
from app.schemas.incident import IncidentResponse, IncidentRetryRequest
from app.recovery.engine import RecoveryEngine
from app.ingestion.base import BaseIngester
import pandas as pd

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=List[IncidentResponse])
def list_incidents(
    status: Optional[str] = None,
    dataset: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Lists failure incidents with filtering and pagination."""
    query = db.query(FailureIncident)
    if status:
        query = query.filter(FailureIncident.status == status)
    if dataset:
        query = query.filter(FailureIncident.dataset_name == dataset)
    if severity:
        query = query.filter(FailureIncident.severity == severity)

    return query.order_by(FailureIncident.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retrieves single incident details."""
    incident = db.query(FailureIncident).filter(FailureIncident.incident_id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/{incident_id}/retry")
def retry_incident_recovery(
    incident_id: uuid.UUID,
    payload: IncidentRetryRequest = IncidentRetryRequest(),
    db: Session = Depends(get_db)
):
    """Retries automated healing on an open or failed incident."""
    incident = db.query(FailureIncident).filter(FailureIncident.incident_id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    recovery_engine = RecoveryEngine(db)
    
    # Load batch raw data if available
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
        "incident_id": str(incident.incident_id),
        "status": incident.status,
        "recovery_summary": summary
    }

