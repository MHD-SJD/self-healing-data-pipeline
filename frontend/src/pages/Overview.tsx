import React from 'react';
import type { Pipeline, PipelineRun, FailureIncident, RecoveryAttempt, QualityScore } from '../types';
import { CheckCircle2, AlertOctagon, HeartHandshake, Gauge, ArrowUpRight } from 'lucide-react';

interface OverviewProps {
  pipelines: Pipeline[];
  runs: PipelineRun[];
  incidents: FailureIncident[];
  recoveryAttempts: RecoveryAttempt[];
  qualityScore: QualityScore | null;
  onNavigateToTab: (tab: string) => void;
}

export const Overview: React.FC<OverviewProps> = ({
  pipelines,
  runs,
  incidents,
  recoveryAttempts,
  qualityScore,
  onNavigateToTab,
}) => {
  const totalRuns = runs.length;
  const successfulRuns = runs.filter((r) => r.status === 'COMPLETED' || r.status === 'HEALED').length;
  const openIncidents = incidents.filter((i) => i.status === 'OPEN' || i.status === 'PENDING_APPROVAL');
  
  const completedRecoveries = recoveryAttempts.filter((r) => r.status === 'SUCCESS').length;
  const totalRecoveries = recoveryAttempts.length;
  const recoveryRate = totalRecoveries > 0 ? Math.round((completedRecoveries / totalRecoveries) * 100) : 100;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* KPI Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        {/* Quality Score */}
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '0.5rem',
          padding: '1.25rem',
          position: 'relative'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.875rem', color: '#94a3b8', fontWeight: 500 }}>Data Quality Score</span>
            <Gauge size={20} color="#38bdf8" />
          </div>
          <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '2rem', fontWeight: 700, color: '#f8fafc' }}>
              {qualityScore ? `${qualityScore.overall_score}%` : '100%'}
            </span>
            <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>Active Gate</span>
          </div>
          <p style={{ margin: '0.5rem 0 0', fontSize: '0.75rem', color: '#64748b' }}>
            Calculated as (Passed Rules / Total Evaluated Checks)
          </p>
        </div>

        {/* Total Pipelines */}
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '0.5rem',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.875rem', color: '#94a3b8', fontWeight: 500 }}>Active Pipelines</span>
            <ArrowUpRight size={20} color="#818cf8" />
          </div>
          <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '2rem', fontWeight: 700, color: '#f8fafc' }}>{pipelines.length}</span>
            <span style={{ fontSize: '0.75rem', color: '#818cf8', fontWeight: 600 }}>Orchestrated</span>
          </div>
          <p style={{ margin: '0.5rem 0 0', fontSize: '0.75rem', color: '#64748b' }}>
            Orders, Customers & Inventory
          </p>
        </div>

        {/* Pipeline Runs */}
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '0.5rem',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.875rem', color: '#94a3b8', fontWeight: 500 }}>Execution Runs</span>
            <CheckCircle2 size={20} color="#10b981" />
          </div>
          <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '2rem', fontWeight: 700, color: '#f8fafc' }}>{totalRuns}</span>
            <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>
              {totalRuns > 0 ? `${Math.round((successfulRuns / totalRuns) * 100)}% Success` : '100%'}
            </span>
          </div>
          <p style={{ margin: '0.5rem 0 0', fontSize: '0.75rem', color: '#64748b' }}>
            {successfulRuns} succeeded / healed
          </p>
        </div>

        {/* Open Incidents */}
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '0.5rem',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.875rem', color: '#94a3b8', fontWeight: 500 }}>Open Incidents</span>
            <AlertOctagon size={20} color={openIncidents.length > 0 ? '#f59e0b' : '#10b981'} />
          </div>
          <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '2rem', fontWeight: 700, color: openIncidents.length > 0 ? '#f59e0b' : '#f8fafc' }}>
              {openIncidents.length}
            </span>
            <span style={{ fontSize: '0.75rem', color: openIncidents.length > 0 ? '#f59e0b' : '#10b981', fontWeight: 600 }}>
              {openIncidents.length > 0 ? 'Requires Action' : 'All Clear'}
            </span>
          </div>
          <p style={{ margin: '0.5rem 0 0', fontSize: '0.75rem', color: '#64748b' }}>
            {incidents.filter((i) => i.status === 'RESOLVED').length} healed autonomously
          </p>
        </div>

        {/* Self-Healing Success */}
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '0.5rem',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.875rem', color: '#94a3b8', fontWeight: 500 }}>Recovery Success Rate</span>
            <HeartHandshake size={20} color="#38bdf8" />
          </div>
          <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '2rem', fontWeight: 700, color: '#f8fafc' }}>{recoveryRate}%</span>
            <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 600 }}>Zero-Defect</span>
          </div>
          <p style={{ margin: '0.5rem 0 0', fontSize: '0.75rem', color: '#64748b' }}>
            {completedRecoveries} of {totalRecoveries} verified
          </p>
        </div>
      </div>

      {/* Main Grid: Architecture Highlights & Recent Activity */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem' }}>
        {/* Recent Pipeline Activity Stream */}
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '0.5rem',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>
              Recent Pipeline Execution Activity
            </h3>
            <button
              onClick={() => onNavigateToTab('pipelines')}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                color: '#38bdf8',
                fontSize: '0.8rem',
                cursor: 'pointer',
                fontWeight: 500
              }}
            >
              View All Runs &rarr;
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {runs.slice(0, 6).map((run) => {
              const isSuccess = run.status === 'COMPLETED' || run.status === 'HEALED';
              const isHealed = run.status === 'HEALED';

              return (
                <div
                  key={run.run_id}
                  style={{
                    backgroundColor: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '0.375rem',
                    padding: '0.75rem 1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      backgroundColor: isHealed ? '#06b6d4' : isSuccess ? '#10b981' : '#ef4444'
                    }} />
                    <div>
                      <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#f1f5f9' }}>
                        {run.pipeline_id}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'flex', gap: '0.75rem' }}>
                        <span>Trigger: {run.trigger_type}</span>
                        <span>•</span>
                        <span>{new Date(run.started_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{
                      padding: '0.2rem 0.5rem',
                      borderRadius: '0.25rem',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      backgroundColor: isHealed ? 'rgba(6, 182, 212, 0.15)' : isSuccess ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                      color: isHealed ? '#22d3ee' : isSuccess ? '#34d399' : '#f87171'
                    }}>
                      {run.status}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      {run.duration_ms ? `${run.duration_ms}ms` : '--'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Platform Self-Healing Policies & State Guard */}
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '0.5rem',
          padding: '1.25rem'
        }}>
          <h3 style={{ margin: '0 0 1rem', fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>
            Autonomous Healing Architecture
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ padding: '0.75rem', backgroundColor: '#0f172a', borderRadius: '0.375rem', border: '1px solid #334155' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#38bdf8', fontWeight: 600, fontSize: '0.85rem' }}>
                <CheckCircle2 size={16} />
                <span>Deterministic Deduplication</span>
              </div>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
                Identifies duplicate primary business keys. Retains latest state, isolates excluded tuples into auditable quarantine with zero data loss.
              </p>
            </div>

            <div style={{ padding: '0.75rem', backgroundColor: '#0f172a', borderRadius: '0.375rem', border: '1px solid #334155' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#38bdf8', fontWeight: 600, fontSize: '0.85rem' }}>
                <CheckCircle2 size={16} />
                <span>Schema Drift Adoption</span>
              </div>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
                Non-breaking additive columns automatically register in schema registry and alter raw storage. Breaking changes trigger quarantine & approval.
              </p>
            </div>

            <div style={{ padding: '0.75rem', backgroundColor: '#0f172a', borderRadius: '0.375rem', border: '1px solid #334155' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#38bdf8', fontWeight: 600, fontSize: '0.85rem' }}>
                <CheckCircle2 size={16} />
                <span>Distribution Drift & Anomaly Gate</span>
              </div>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
                Continuous Z-score monitoring halts downstream dbt transformation on metric spikes, preventing corrupted analytical reports.
              </p>
            </div>

            <div style={{ padding: '0.75rem', backgroundColor: '#0f172a', borderRadius: '0.375rem', border: '1px solid #334155' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#38bdf8', fontWeight: 600, fontSize: '0.85rem' }}>
                <CheckCircle2 size={16} />
                <span>Post-Recovery Verification</span>
              </div>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
                Re-evaluates validation suite on repaired dataset before confirming resolution status.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
