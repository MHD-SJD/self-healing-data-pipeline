import type {
  Pipeline, PipelineRun, FailureIncident, ValidationResult,
  DetectedAnomaly, RecoveryAttempt, QuarantinedRecord, QualityScore
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error (${response.status}): ${errorText}`);
  }
  return response.json();
}

export const api = {
  // Health
  getHealth: () => fetchJson<{ status: string; database: string; service: string }>('/health'),

  // Pipelines
  getPipelines: () => fetchJson<Pipeline[]>('/pipelines'),
  getPipeline: (id: string) => fetchJson<Pipeline>(`/pipelines/${id}`),
  triggerPipeline: (id: string, autoHeal: boolean = true) =>
    fetchJson<any>(`/pipelines/${id}/run`, {
      method: 'POST',
      body: JSON.stringify({ auto_heal: autoHeal }),
    }),

  // Runs
  getRuns: (limit: number = 50) => fetchJson<PipelineRun[]>(`/runs?limit=${limit}`),
  getRun: (runId: string) => fetchJson<PipelineRun>(`/runs/${runId}`),

  // Incidents
  getIncidents: (limit: number = 50) => fetchJson<FailureIncident[]>(`/incidents?limit=${limit}`),
  retryIncident: (incidentId: string, approvedBy?: string) =>
    fetchJson<any>(`/incidents/${incidentId}/retry`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: approvedBy || 'OPERATOR' }),
    }),

  // Quality & Anomalies
  getQualityResults: (limit: number = 100) => fetchJson<ValidationResult[]>(`/quality/results?limit=${limit}`),
  getAnomalies: (limit: number = 50) => fetchJson<DetectedAnomaly[]>(`/anomalies?limit=${limit}`),
  getQualityScore: () => fetchJson<QualityScore>('/quality/score'),

  // Recovery & Quarantined records
  getRecoveryAttempts: (limit: number = 50) => fetchJson<RecoveryAttempt[]>(`/recovery/attempts?limit=${limit}`),
  dryRunRecovery: (incidentId: string) =>
    fetchJson<any>('/recovery/dry-run', {
      method: 'POST',
      body: JSON.stringify({ incident_id: incidentId }),
    }),
  approveRecovery: (attemptOrIncidentId: string, approvedBy: string = 'LEAD_DATA_ENGINEER') =>
    fetchJson<any>(`/recovery/${attemptOrIncidentId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  getQuarantinedRecords: (limit: number = 50) => fetchJson<QuarantinedRecord[]>(`/recovery/quarantine?limit=${limit}`),
};
