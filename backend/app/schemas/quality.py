from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, UUID4, ConfigDict


class QualityResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    result_id: UUID4
    batch_id: UUID4
    run_id: UUID4
    rule_id: str
    passed: bool
    observed_value: Optional[float] = None
    expected_threshold: Optional[float] = None
    severity: str
    failure_details: Optional[Dict[str, Any]] = None
    evaluated_at: datetime


class AnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    anomaly_id: UUID4
    batch_id: UUID4
    dataset_name: str
    metric_name: str
    observed_metric: float
    baseline_mean: Optional[float] = None
    baseline_stddev: Optional[float] = None
    z_score: Optional[float] = None
    anomaly_type: str
    severity: str
    detected_at: datetime
