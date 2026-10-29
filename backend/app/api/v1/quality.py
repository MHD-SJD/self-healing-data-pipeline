import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.metadata import ValidationResult, DetectedAnomaly
from app.schemas.quality import QualityResultResponse, AnomalyResponse

router = APIRouter(tags=["Data Quality & Anomalies"])


@router.get("/quality/results", response_model=List[QualityResultResponse])
def list_quality_results(
    batch_id: Optional[uuid.UUID] = None,
    rule_id: Optional[str] = None,
    passed: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieves data quality validation results."""
    query = db.query(ValidationResult)
    if batch_id:
        query = query.filter(ValidationResult.batch_id == batch_id)
    if rule_id:
        query = query.filter(ValidationResult.rule_id == rule_id)
    if passed is not None:
        query = query.filter(ValidationResult.passed == passed)

    return query.order_by(ValidationResult.evaluated_at.desc()).offset(offset).limit(limit).all()


@router.get("/anomalies", response_model=List[AnomalyResponse])
def list_anomalies(
    dataset: Optional[str] = None,
    anomaly_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieves detected statistical distribution anomalies."""
    query = db.query(DetectedAnomaly)
    if dataset:
        query = query.filter(DetectedAnomaly.dataset_name == dataset)
    if anomaly_type:
        query = query.filter(DetectedAnomaly.anomaly_type == anomaly_type)

    return query.order_by(DetectedAnomaly.detected_at.desc()).offset(offset).limit(limit).all()


@router.get("/quality/score")
def get_quality_score(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Computes system-wide and dataset-level Data Quality Scores.
    Score Calculation: (Total Passed Checks / Total Evaluated Checks) * 100
    """
    total_checks = db.query(func.count(ValidationResult.result_id)).scalar() or 0
    passed_checks = db.query(func.count(ValidationResult.result_id)).filter(
        ValidationResult.passed == True
    ).scalar() or 0

    overall_score = round((passed_checks / total_checks * 100.0), 1) if total_checks > 0 else 100.0

    return {
        "overall_score": overall_score,
        "total_checks_evaluated": total_checks,
        "total_passed": passed_checks,
        "total_failed": total_checks - passed_checks,
        "calculation_formula": "Round((Passed_Checks / Total_Checks) * 100, 1)"
    }

