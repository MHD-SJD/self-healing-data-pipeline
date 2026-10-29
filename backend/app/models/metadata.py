import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Numeric, Text, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Pipeline(Base):
    __tablename__ = "pipelines"
    __table_args__ = {"schema": "pipeline_metadata"}

    pipeline_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    schedule_interval = Column(String(64))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    runs = relationship("PipelineRun", back_populates="pipeline", cascade="all, delete-orphan")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = {"schema": "pipeline_metadata"}

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(String(64), ForeignKey("pipeline_metadata.pipelines.pipeline_id", ondelete="CASCADE"), nullable=False)
    status = Column(String(32), default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED, HEALED, ESCALATED
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    trigger_type = Column(String(32), default="MANUAL")
    error_message = Column(Text)
    metadata_payload = Column("metadata", JSON, default=dict)

    pipeline = relationship("Pipeline", back_populates="runs")
    batches = relationship("IngestionBatch", back_populates="run", cascade="all, delete-orphan")
    incidents = relationship("FailureIncident", back_populates="run", cascade="all, delete-orphan")


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"
    __table_args__ = {"schema": "pipeline_metadata"}

    batch_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_metadata.pipeline_runs.run_id", ondelete="CASCADE"), nullable=False)
    dataset_name = Column(String(64), nullable=False)
    source_path = Column(String(512), nullable=False)
    idempotency_token = Column(String(128), unique=True)
    input_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    quarantined_rows = Column(Integer, default=0)
    checksum = Column(String(64))
    status = Column(String(32), default="PENDING")  # PENDING, INGESTED, FAILED, QUARANTINED
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))

    run = relationship("PipelineRun", back_populates="batches")
    validation_results = relationship("ValidationResult", back_populates="batch", cascade="all, delete-orphan")
    anomalies = relationship("DetectedAnomaly", back_populates="batch", cascade="all, delete-orphan")


class DatasetSchema(Base):
    __tablename__ = "dataset_schemas"
    __table_args__ = {"schema": "pipeline_metadata"}

    schema_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_name = Column(String(64), nullable=False)
    version = Column(Integer, nullable=False)
    schema_definition = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class DataQualityRule(Base):
    __tablename__ = "data_quality_rules"
    __table_args__ = {"schema": "pipeline_metadata"}

    rule_id = Column(String(64), primary_key=True)
    dataset_name = Column(String(64), nullable=False)
    rule_type = Column(String(64), nullable=False)  # completeness, uniqueness, schema, validity, distribution
    column_name = Column(String(64))
    parameters = Column(JSON, default=dict)
    severity = Column(String(32), default="ERROR")  # INFO, WARNING, ERROR, CRITICAL
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class ValidationResult(Base):
    __tablename__ = "validation_results"
    __table_args__ = {"schema": "pipeline_metadata"}

    result_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_metadata.ingestion_batches.batch_id", ondelete="CASCADE"), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_metadata.pipeline_runs.run_id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(String(64), ForeignKey("pipeline_metadata.data_quality_rules.rule_id"), nullable=False)
    passed = Column(Boolean, nullable=False)
    observed_value = Column(Numeric)
    expected_threshold = Column(Numeric)
    severity = Column(String(32), nullable=False)
    failure_details = Column(JSON, default=dict)
    evaluated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    batch = relationship("IngestionBatch", back_populates="validation_results")


class DetectedAnomaly(Base):
    __tablename__ = "detected_anomalies"
    __table_args__ = {"schema": "pipeline_metadata"}

    anomaly_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_metadata.ingestion_batches.batch_id", ondelete="CASCADE"), nullable=False)
    dataset_name = Column(String(64), nullable=False)
    metric_name = Column(String(64), nullable=False)
    observed_metric = Column(Numeric, nullable=False)
    baseline_mean = Column(Numeric)
    baseline_stddev = Column(Numeric)
    z_score = Column(Numeric)
    anomaly_type = Column(String(64), nullable=False)  # VOLUME_SPIKE, VOLUME_DROP, OUTLIER_MEAN, DRIFT
    severity = Column(String(32), default="WARNING")
    detected_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    batch = relationship("IngestionBatch", back_populates="anomalies")


class FailureIncident(Base):
    __tablename__ = "failure_incidents"
    __table_args__ = {"schema": "pipeline_metadata"}

    incident_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_metadata.pipeline_runs.run_id", ondelete="CASCADE"), nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_metadata.ingestion_batches.batch_id", ondelete="SET NULL"))
    dataset_name = Column(String(64), nullable=False)
    failure_category = Column(String(64), nullable=False)
    severity = Column(String(32), default="ERROR")
    explanation = Column(Text, nullable=False)
    evidence = Column(JSON, default=dict)
    recommended_action = Column(String(128), nullable=False)
    status = Column(String(32), default="OPEN")  # OPEN, HEALING_IN_PROGRESS, RESOLVED, PENDING_APPROVAL, ESCALATED_HUMAN_REQUIRED, CANCELLED
    requires_human_approval = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    resolved_at = Column(DateTime(timezone=True))

    run = relationship("PipelineRun", back_populates="incidents")
    recovery_attempts = relationship("RecoveryAttempt", back_populates="incident", cascade="all, delete-orphan")


class RecoveryPolicy(Base):
    __tablename__ = "recovery_policies"
    __table_args__ = {"schema": "pipeline_metadata"}

    policy_id = Column(String(64), primary_key=True)
    failure_category = Column(String(64), nullable=False)
    safety_level = Column(String(32), default="AUTOMATIC")  # AUTOMATIC, REQUIRES_APPROVAL, MANUAL_ONLY
    max_retries = Column(Integer, default=3)
    auto_apply = Column(Boolean, default=True)
    preconditions = Column(JSON, default=dict)
    action_config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"
    __table_args__ = {"schema": "pipeline_metadata"}

    attempt_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_metadata.failure_incidents.incident_id", ondelete="CASCADE"), nullable=False)
    policy_id = Column(String(64), ForeignKey("pipeline_metadata.recovery_policies.policy_id"))
    strategy_applied = Column(String(128), nullable=False)
    status = Column(String(32), default="IN_PROGRESS")  # IN_PROGRESS, SUCCESS, FAILED, ROLLED_BACK
    execution_log = Column(Text)
    duration_ms = Column(Integer)
    post_verification_passed = Column(Boolean)
    post_verification_details = Column(JSON, default=dict)
    approved_by = Column(String(64))
    executed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    incident = relationship("FailureIncident", back_populates="recovery_attempts")


class QuarantinedRecord(Base):
    __tablename__ = "quarantined_records"
    __table_args__ = {"schema": "pipeline_metadata"}

    quarantine_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_metadata.ingestion_batches.batch_id", ondelete="SET NULL"))
    incident_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_metadata.failure_incidents.incident_id", ondelete="SET NULL"))
    dataset_name = Column(String(64), nullable=False)
    source_identifier = Column(String(128))
    record_content = Column(JSON, nullable=False)
    rejection_reason = Column(Text, nullable=False)
    quarantined_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = {"schema": "pipeline_metadata"}

    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)
    event_type = Column(String(64), nullable=False)
    actor = Column(String(64), default="SYSTEM")
    details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

