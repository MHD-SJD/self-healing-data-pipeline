import React, { useState } from 'react';
import type { Pipeline, PipelineRun } from '../types';
import { Play } from 'lucide-react';

interface PipelinesProps {
  pipelines: Pipeline[];
  runs: PipelineRun[];
  onTriggerPipeline: (pipelineId: string) => Promise<void>;
  isTriggering: string | null;
}

export const Pipelines: React.FC<PipelinesProps> = ({
  pipelines,
  runs,
  onTriggerPipeline,
  isTriggering,
}) => {
  const [selectedPipeline, setSelectedPipeline] = useState<string | null>(null);

  const filteredRuns = selectedPipeline
    ? runs.filter((r) => r.pipeline_id === selectedPipeline)
    : runs;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Registered Pipelines Cards */}
      <div>
        <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0 0 1rem', color: '#f8fafc' }}>
          Registered Orchestration Pipelines
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          {pipelines.map((p) => {
            const pipelineRuns = runs.filter((r) => r.pipeline_id === p.pipeline_id);
            const latestRun = pipelineRuns[0];
            const isRunning = isTriggering === p.pipeline_id;

            return (
              <div
                key={p.pipeline_id}
                onClick={() => setSelectedPipeline(selectedPipeline === p.pipeline_id ? null : p.pipeline_id)}
                style={{
                  backgroundColor: '#1e293b',
                  border: selectedPipeline === p.pipeline_id ? '2px solid #38bdf8' : '1px solid #334155',
                  borderRadius: '0.5rem',
                  padding: '1.25rem',
                  cursor: 'pointer',
                  transition: 'border-color 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>
                      {p.name}
                    </h3>
                    <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
                      {p.description}
                    </p>
                  </div>
                  <span style={{
                    padding: '0.2rem 0.5rem',
                    borderRadius: '0.25rem',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    backgroundColor: p.is_active ? 'rgba(16, 185, 129, 0.15)' : 'rgba(100, 116, 139, 0.2)',
                    color: p.is_active ? '#34d399' : '#94a3b8'
                  }}>
                    {p.is_active ? 'ACTIVE' : 'PAUSED'}
                  </span>
                </div>

                <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', gap: '0.5rem' }}>
                    <span>Schedule: <strong style={{ color: '#cbd5e1' }}>{p.schedule_interval}</strong></span>
                    <span>•</span>
                    <span>Runs: <strong style={{ color: '#cbd5e1' }}>{pipelineRuns.length}</strong></span>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onTriggerPipeline(p.pipeline_id);
                    }}
                    disabled={isRunning}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      backgroundColor: '#38bdf8',
                      color: '#0f172a',
                      fontWeight: 600,
                      fontSize: '0.8rem',
                      padding: '0.4rem 0.75rem',
                      borderRadius: '0.375rem',
                      border: 'none',
                      cursor: isRunning ? 'not-allowed' : 'pointer',
                      opacity: isRunning ? 0.6 : 1
                    }}
                  >
                    <Play size={14} fill="#0f172a" />
                    {isRunning ? 'Running...' : 'Run Pipeline'}
                  </button>
                </div>

                {latestRun && (
                  <div style={{
                    marginTop: '0.75rem',
                    paddingTop: '0.75rem',
                    borderTop: '1px solid #334155',
                    fontSize: '0.75rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    color: '#94a3b8'
                  }}>
                    <span>Last Run: {new Date(latestRun.started_at).toLocaleTimeString()}</span>
                    <span style={{
                      fontWeight: 600,
                      color: latestRun.status === 'COMPLETED' || latestRun.status === 'HEALED' ? '#34d399' : '#f87171'
                    }}>
                      {latestRun.status} ({latestRun.duration_ms}ms)
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Execution Run History Table */}
      <div style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '0.5rem',
        padding: '1.25rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600, color: '#f8fafc' }}>
              Execution Run History {selectedPipeline && `(${selectedPipeline})`}
            </h3>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
              Comprehensive execution metrics, input/output row tracking, and downstream dbt status
            </p>
          </div>
          {selectedPipeline && (
            <button
              onClick={() => setSelectedPipeline(null)}
              style={{
                backgroundColor: '#334155',
                color: '#cbd5e1',
                border: 'none',
                padding: '0.3rem 0.6rem',
                borderRadius: '0.25rem',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              Clear Filter
            </button>
          )}
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', fontSize: '0.75rem' }}>
                <th style={{ padding: '0.75rem' }}>RUN ID</th>
                <th style={{ padding: '0.75rem' }}>PIPELINE</th>
                <th style={{ padding: '0.75rem' }}>STATUS</th>
                <th style={{ padding: '0.75rem' }}>INPUT / OUTPUT ROWS</th>
                <th style={{ padding: '0.75rem' }}>DURATION</th>
                <th style={{ padding: '0.75rem' }}>DBT STATUS</th>
                <th style={{ padding: '0.75rem' }}>TRIGGER</th>
                <th style={{ padding: '0.75rem' }}>TIMESTAMP</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.map((run) => {
                const meta = run.metadata_payload || {};
                const inputRows = meta.input_rows ?? '--';
                const outputRows = meta.output_rows ?? '--';
                const dbtStatus = meta.dbt_result?.status ?? 'SKIPPED';

                const statusColor =
                  run.status === 'HEALED'
                    ? '#22d3ee'
                    : run.status === 'COMPLETED'
                    ? '#34d399'
                    : run.status === 'PENDING_APPROVAL'
                    ? '#fbbf24'
                    : '#f87171';

                return (
                  <tr key={run.run_id} style={{ borderBottom: '1px solid #1f293d' }}>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace', color: '#94a3b8' }}>
                      {run.run_id.slice(0, 8)}...
                    </td>
                    <td style={{ padding: '0.75rem', fontWeight: 600, color: '#f1f5f9' }}>
                      {run.pipeline_id}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.2rem 0.5rem',
                        borderRadius: '0.25rem',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        backgroundColor: `${statusColor}22`,
                        color: statusColor
                      }}>
                        {run.status}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', color: '#cbd5e1' }}>
                      {inputRows} &rarr; <strong style={{ color: '#38bdf8' }}>{outputRows}</strong>
                    </td>
                    <td style={{ padding: '0.75rem', color: '#94a3b8' }}>
                      {run.duration_ms ? `${run.duration_ms}ms` : '--'}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.15rem 0.4rem',
                        borderRadius: '0.2rem',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        backgroundColor: dbtStatus === 'SUCCESS' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(100, 116, 139, 0.2)',
                        color: dbtStatus === 'SUCCESS' ? '#34d399' : '#94a3b8'
                      }}>
                        {dbtStatus}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', color: '#94a3b8' }}>{run.trigger_type}</td>
                    <td style={{ padding: '0.75rem', color: '#64748b' }}>
                      {new Date(run.started_at).toLocaleString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
