-- ==============================================================================
-- Database Initialization Script for Self-Healing Data Pipeline Platform
-- ==============================================================================

-- Create distinct schemas
CREATE SCHEMA IF NOT EXISTS pipeline_metadata;
CREATE SCHEMA IF NOT EXISTS raw_data;
CREATE SCHEMA IF NOT EXISTS staging_data;
CREATE SCHEMA IF NOT EXISTS analytics_data;

-- Set search path
SET search_path TO pipeline_metadata, public;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- 1. Operational Metadata Schema
-- ==============================================================================

-- Pipelines
CREATE TABLE IF NOT EXISTS pipeline_metadata.pipelines (
    pipeline_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    schedule_interval VARCHAR(64),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Pipeline Runs
CREATE TABLE IF NOT EXISTS pipeline_metadata.pipeline_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id VARCHAR(64) NOT NULL REFERENCES pipeline_metadata.pipelines(pipeline_id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- PENDING, RUNNING, COMPLETED, FAILED, HEALED, ESCALATED
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    trigger_type VARCHAR(32) DEFAULT 'MANUAL', -- SCHEDULED, MANUAL, RETRY, REPLAY
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Ingestion Batches
CREATE TABLE IF NOT EXISTS pipeline_metadata.ingestion_batches (
    batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_metadata.pipeline_runs(run_id) ON DELETE CASCADE,
    dataset_name VARCHAR(64) NOT NULL, -- orders, customers, inventory
    source_path VARCHAR(512) NOT NULL,
    idempotency_token VARCHAR(128) UNIQUE,
    input_rows INTEGER DEFAULT 0,
    processed_rows INTEGER DEFAULT 0,
    quarantined_rows INTEGER DEFAULT 0,
    checksum VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- PENDING, INGESTED, FAILED, QUARANTINED
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Dataset Schema Versions
CREATE TABLE IF NOT EXISTS pipeline_metadata.dataset_schemas (
    schema_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_name VARCHAR(64) NOT NULL,
    version INTEGER NOT NULL,
    schema_definition JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (dataset_name, version)
);

-- Data Quality Rules
CREATE TABLE IF NOT EXISTS pipeline_metadata.data_quality_rules (
    rule_id VARCHAR(64) PRIMARY KEY,
    dataset_name VARCHAR(64) NOT NULL,
    rule_type VARCHAR(64) NOT NULL, -- completeness, uniqueness, schema, validity, distribution
    column_name VARCHAR(64),
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    severity VARCHAR(32) NOT NULL DEFAULT 'ERROR', -- INFO, WARNING, ERROR, CRITICAL
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Validation Results
CREATE TABLE IF NOT EXISTS pipeline_metadata.validation_results (
    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES pipeline_metadata.ingestion_batches(batch_id) ON DELETE CASCADE,
    run_id UUID NOT NULL REFERENCES pipeline_metadata.pipeline_runs(run_id) ON DELETE CASCADE,
    rule_id VARCHAR(64) NOT NULL REFERENCES pipeline_metadata.data_quality_rules(rule_id),
    passed BOOLEAN NOT NULL,
    observed_value NUMERIC,
    expected_threshold NUMERIC,
    severity VARCHAR(32) NOT NULL,
    failure_details JSONB DEFAULT '{}'::jsonb,
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Detected Anomalies
CREATE TABLE IF NOT EXISTS pipeline_metadata.detected_anomalies (
    anomaly_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES pipeline_metadata.ingestion_batches(batch_id) ON DELETE CASCADE,
    dataset_name VARCHAR(64) NOT NULL,
    metric_name VARCHAR(64) NOT NULL,
    observed_metric NUMERIC NOT NULL,
    baseline_mean NUMERIC,
    baseline_stddev NUMERIC,
    z_score NUMERIC,
    anomaly_type VARCHAR(64) NOT NULL, -- VOLUME_SPIKE, VOLUME_DROP, OUTLIER_MEAN, DRIFT
    severity VARCHAR(32) DEFAULT 'WARNING',
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Failure Incidents
CREATE TABLE IF NOT EXISTS pipeline_metadata.failure_incidents (
    incident_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_metadata.pipeline_runs(run_id) ON DELETE CASCADE,
    batch_id UUID REFERENCES pipeline_metadata.ingestion_batches(batch_id) ON DELETE SET NULL,
    dataset_name VARCHAR(64) NOT NULL,
    failure_category VARCHAR(64) NOT NULL, -- MISSING_DATA, DUPLICATE_DATA, SCHEMA_DRIFT, DISTRIBUTION_ANOMALY, INVALID_RECORDS, INGESTION_FAILURE, TRANSFORMATION_FAILURE, INFRASTRUCTURE_OR_TIMEOUT_FAILURE, UNKNOWN_FAILURE
    severity VARCHAR(32) NOT NULL DEFAULT 'ERROR', -- INFO, WARNING, ERROR, CRITICAL
    explanation TEXT NOT NULL,
    evidence JSONB DEFAULT '{}'::jsonb,
    recommended_action VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN', -- OPEN, HEALING_IN_PROGRESS, RESOLVED, PENDING_APPROVAL, ESCALATED_HUMAN_REQUIRED, CANCELLED
    requires_human_approval BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Recovery Policies
CREATE TABLE IF NOT EXISTS pipeline_metadata.recovery_policies (
    policy_id VARCHAR(64) PRIMARY KEY,
    failure_category VARCHAR(64) NOT NULL,
    safety_level VARCHAR(32) NOT NULL DEFAULT 'AUTOMATIC', -- AUTOMATIC, REQUIRES_APPROVAL, MANUAL_ONLY
    max_retries INTEGER DEFAULT 3,
    auto_apply BOOLEAN DEFAULT TRUE,
    preconditions JSONB DEFAULT '{}'::jsonb,
    action_config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Recovery Attempts
CREATE TABLE IF NOT EXISTS pipeline_metadata.recovery_attempts (
    attempt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES pipeline_metadata.failure_incidents(incident_id) ON DELETE CASCADE,
    policy_id VARCHAR(64) REFERENCES pipeline_metadata.recovery_policies(policy_id),
    strategy_applied VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'IN_PROGRESS', -- IN_PROGRESS, SUCCESS, FAILED, ROLLED_BACK
    execution_log TEXT,
    duration_ms INTEGER,
    post_verification_passed BOOLEAN,
    post_verification_details JSONB DEFAULT '{}'::jsonb,
    approved_by VARCHAR(64),
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Quarantined Records
CREATE TABLE IF NOT EXISTS pipeline_metadata.quarantined_records (
    quarantine_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID REFERENCES pipeline_metadata.ingestion_batches(batch_id) ON DELETE SET NULL,
    incident_id UUID REFERENCES pipeline_metadata.failure_incidents(incident_id) ON DELETE SET NULL,
    dataset_name VARCHAR(64) NOT NULL,
    source_identifier VARCHAR(128),
    record_content JSONB NOT NULL,
    rejection_reason TEXT NOT NULL,
    quarantined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit Events
CREATE TABLE IF NOT EXISTS pipeline_metadata.audit_events (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL, -- CREATED, UPDATED, DELETED, HEALED, APPROVED, REJECTED
    actor VARCHAR(64) DEFAULT 'SYSTEM',
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 2. Raw Data Tables
-- ==============================================================================

CREATE TABLE IF NOT EXISTS raw_data.raw_customers (
    _raw_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    _batch_id UUID NOT NULL,
    _ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    customer_id VARCHAR(64),
    email VARCHAR(255),
    first_name VARCHAR(128),
    last_name VARCHAR(128),
    signup_date VARCHAR(64),
    country VARCHAR(64),
    phone VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS raw_data.raw_orders (
    _raw_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    _batch_id UUID NOT NULL,
    _ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    order_id VARCHAR(64),
    customer_id VARCHAR(64),
    product_id VARCHAR(64),
    order_date VARCHAR(64),
    amount NUMERIC,
    status VARCHAR(32),
    shipping_address TEXT
);

CREATE TABLE IF NOT EXISTS raw_data.raw_inventory (
    _raw_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    _batch_id UUID NOT NULL,
    _ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    product_id VARCHAR(64),
    sku VARCHAR(64),
    product_name VARCHAR(255),
    category VARCHAR(64),
    unit_price NUMERIC,
    stock_quantity INTEGER,
    warehouse_code VARCHAR(32),
    last_restocked_at VARCHAR(64)
);

-- Create Indexes for fast querying
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline_id ON pipeline_metadata.pipeline_runs(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_metadata.pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_batches_run_id ON pipeline_metadata.ingestion_batches(run_id);
CREATE INDEX IF NOT EXISTS idx_validation_results_batch_id ON pipeline_metadata.validation_results(batch_id);
CREATE INDEX IF NOT EXISTS idx_failure_incidents_status ON pipeline_metadata.failure_incidents(status);
CREATE INDEX IF NOT EXISTS idx_raw_customers_batch_id ON raw_data.raw_customers(_batch_id);
CREATE INDEX IF NOT EXISTS idx_raw_orders_batch_id ON raw_data.raw_orders(_batch_id);
CREATE INDEX IF NOT EXISTS idx_raw_inventory_batch_id ON raw_data.raw_inventory(_batch_id);

