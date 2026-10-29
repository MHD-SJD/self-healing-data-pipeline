export interface Pipeline {
  pipeline_id: string;
  name: string;
  description?: string;
  schedule_interval?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PipelineRun {
  run_id: string;
  pipeline_id: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'HEALED' | 'ESCALATED' | 'FAILED' | 'PENDING_APPROVAL';
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  trigger_type: string;
  error_message?: string;
  metadata_payload?: {
    dataset?: string;
    input_rows?: number;
    output_rows?: number;
    incidents_count?: number;
    unresolved_count?: number;
    dbt_result?: {
      status?: string;
      exit_code?: number;
      stdout?: string;
    };
  };
}

export interface FailureIncident {
  incident_id: string;
  run_id: string;
  batch_id?: string;
  dataset_name: string;
  failure_category: string;
  severity: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  explanation: string;
  evidence?: Record<string, any>;
  recommended_action: string;
  status: 'OPEN' | 'HEALING_IN_PROGRESS' | 'RESOLVED' | 'PENDING_APPROVAL' | 'ESCALATED_HUMAN_REQUIRED' | 'CANCELLED';
  requires_human_approval: boolean;
  created_at: string;
  resolved_at?: string;
}

export interface ValidationResult {
  result_id: string;
  batch_id: string;
  run_id: string;
  rule_id: string;
  passed: boolean;
  observed_value?: number;
  expected_threshold?: number;
  severity: string;
  failure_details?: Record<string, any>;
  evaluated_at: string;
}

export interface DetectedAnomaly {
  anomaly_id: string;
  batch_id: string;
  dataset_name: string;
  metric_name: string;
  observed_metric: number;
  baseline_mean?: number;
  baseline_stddev?: number;
  z_score?: number;
  anomaly_type: string;
  severity: string;
  detected_at: string;
}

export interface RecoveryAttempt {
  attempt_id: string;
  incident_id: string;
  policy_id?: string;
  strategy_applied: string;
  status: 'IN_PROGRESS' | 'SUCCESS' | 'FAILED' | 'ROLLED_BACK';
  execution_log?: string;
  duration_ms?: number;
  post_verification_passed?: boolean;
  post_verification_details?: Record<string, any>;
  approved_by?: string;
  executed_at: string;
}

export interface QuarantinedRecord {
  quarantine_id: string;
  batch_id?: string;
  incident_id?: string;
  dataset_name: string;
  source_identifier?: string;
  rejection_reason: string;
  record_content: Record<string, any>;
  quarantined_at: string;
}

export interface QualityScore {
  overall_score: number;
  total_checks_evaluated: number;
  total_passed: number;
  total_failed: number;
  calculation_formula: string;
}

