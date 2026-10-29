import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.metadata import PipelineRun
from app.schemas.pipeline import PipelineRunResponse

router = APIRouter(prefix="/runs", tags=["Pipeline Runs"])


@router.get("", response_model=List[PipelineRunResponse])
def list_runs(
    pipeline_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieves paginated pipeline execution runs with optional filters."""
    query = db.query(PipelineRun)
    if pipeline_id:
        query = query.filter(PipelineRun.pipeline_id == pipeline_id)
    if status:
        query = query.filter(PipelineRun.status == status)

    return query.order_by(PipelineRun.started_at.desc()).offset(offset).limit(limit).all()


@router.get("/{run_id}", response_model=PipelineRunResponse)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retrieves specific pipeline run details."""
    run = db.query(PipelineRun).filter(PipelineRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

