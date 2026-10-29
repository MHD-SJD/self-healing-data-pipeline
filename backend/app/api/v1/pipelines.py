from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pathlib import Path

from app.core.database import get_db
from app.models.metadata import Pipeline
from app.schemas.pipeline import PipelineResponse, RunTriggerRequest
from app.services.pipeline_service import PipelineExecutionService

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


@router.get("", response_model=List[PipelineResponse])
def list_pipelines(db: Session = Depends(get_db)):
    """Retrieves all registered data pipelines."""
    return db.query(Pipeline).all()


@router.get("/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    """Retrieves metadata for a specific pipeline."""
    p = db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return p


@router.post("/{pipeline_id}/run")
def trigger_pipeline(
    pipeline_id: str,
    payload: RunTriggerRequest = RunTriggerRequest(),
    db: Session = Depends(get_db)
):
    """Triggers an end-to-end self-healing pipeline execution."""
    p = db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    custom_path = Path(payload.custom_filepath) if payload.custom_filepath else None
    service = PipelineExecutionService(db)
    result = service.trigger_pipeline_run(
        pipeline_id=pipeline_id,
        custom_filepath=custom_path,
        trigger_type="API_TRIGGER",
        auto_heal=payload.auto_heal
    )
    return result

