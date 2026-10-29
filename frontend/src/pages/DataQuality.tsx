import React, { useState } from 'react';
import type { ValidationResult, DetectedAnomaly, QualityScore } from '../types';
import { CheckCircle2, XCircle, ShieldCheck, TrendingUp } from 'lucide-react';

interface DataQualityProps {
  validationResults: ValidationResult[];
  anomalies: DetectedAnomaly[];
  qualityScore: QualityScore | null;
}

export const DataQuality: React.FC<DataQualityProps> = ({
  validationResults,
  anomalies,
  qualityScore,
}) => {
  const [filterPassed, setFilterPassed] = useState<boolean | null>(null);

  const filteredResults = filterPassed !== null
    ? validationResults.filter((r) => r.passed === filterPassed)
    : validationResults;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Quality Summary Banner */}
      <div style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '0.5rem',
        padding: '1.25rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            backgroundColor: 'rgba(56, 189, 248, 0.15)',
            color: '#38bdf8',
            padding: '0.75rem',
            borderRadius: '0.5rem'
          }}>
            <ShieldCheck size={32} />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
              Data Quality & Distribution Engine
            </h2>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
              Formula: {qualityScore?.calculation_formula || 'Round((Passed / Total) * 100, 1)'}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1.5rem', textAlign: 'right' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Overall Score</div>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#38bdf8' }}>
              {qualityScore?.overall_score ?? 100}%
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Total Checks</div>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc' }}>
              {qualityScore?.total_checks_evaluated ?? 0}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Violations Caught</div>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f87171' }}>
              {qualityScore?.total_failed ?? 0}
            </div>
          </div>
        </div>
      </div>

      {/* Statistical Distribution Anomalies Section */}
      <div style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '0.5rem',
        padding: '1.25rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <TrendingUp size={20} color="#f59e0b" />
          <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600, color: '#f8fafc' }}>
            Statistical Distribution Anomalies ({anomalies.length})
          </h3>
        </div>

        {anomalies.length === 0 ? (
          <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.85rem' }}>
            No statistical drift or metric anomalies detected. All current distributions match historical baselines.
          </p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', fontSize: '0.75rem' }}>
                  <th style={{ padding: '0.75rem' }}>DATASET</th>
                  <th style={{ padding: '0.75rem' }}>METRIC</th>
                  <th style={{ padding: '0.75rem' }}>OBSERVED VALUE</th>
                  <th style={{ padding: '0.75rem' }}>BASELINE MEAN</th>
                  <th style={{ padding: '0.75rem' }}>Z-SCORE DEVIATION</th>
                  <th style={{ padding: '0.75rem' }}>ANOMALY TYPE</th>
                  <th style={{ padding: '0.75rem' }}>SEVERITY</th>
                  <th style={{ padding: '0.75rem' }}>DETECTED AT</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((a) => (
                  <tr key={a.anomaly_id} style={{ borderBottom: '1px solid #1f293d' }}>
                    <td style={{ padding: '0.75rem', fontWeight: 600, color: '#f1f5f9' }}>{a.dataset_name}</td>
                    <td style={{ padding: '0.75rem', color: '#38bdf8' }}>{a.metric_name}</td>
                    <td style={{ padding: '0.75rem', color: '#f8fafc', fontWeight: 600 }}>{a.observed_metric}</td>
                    <td style={{ padding: '0.75rem', color: '#94a3b8' }}>{a.baseline_mean ?? '--'}</td>
                    <td style={{ padding: '0.75rem', color: '#f59e0b', fontWeight: 700 }}>
                      {a.z_score ? `σ = ${a.z_score}` : '--'}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.2rem 0.5rem',
                        borderRadius: '0.25rem',
                        fontSize: '0.75rem',
                        backgroundColor: 'rgba(245, 158, 11, 0.15)',
                        color: '#fbbf24',
                        fontWeight: 600
                      }}>
                        {a.anomaly_type}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.2rem 0.5rem',
                        borderRadius: '0.25rem',
                        fontSize: '0.75rem',
                        backgroundColor: a.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                        color: a.severity === 'CRITICAL' ? '#f87171' : '#fbbf24',
                        fontWeight: 600
                      }}>
                        {a.severity}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', color: '#64748b' }}>
                      {new Date(a.detected_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Validation Rule Results Table */}
      <div style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '0.5rem',
        padding: '1.25rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600, color: '#f8fafc' }}>
              Validation Rule Results ({filteredResults.length})
            </h3>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
              Evaluated completeness, primary key uniqueness, schema contracts, and validity constraints
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => setFilterPassed(null)}
              style={{
                backgroundColor: filterPassed === null ? '#38bdf8' : '#334155',
                color: filterPassed === null ? '#0f172a' : '#cbd5e1',
                border: 'none',
                padding: '0.35rem 0.75rem',
                borderRadius: '0.375rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              All ({validationResults.length})
            </button>
            <button
              onClick={() => setFilterPassed(false)}
              style={{
                backgroundColor: filterPassed === false ? '#ef4444' : '#334155',
                color: '#f8fafc',
                border: 'none',
                padding: '0.35rem 0.75rem',
                borderRadius: '0.375rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Violations ({validationResults.filter((r) => !r.passed).length})
            </button>
            <button
              onClick={() => setFilterPassed(true)}
              style={{
                backgroundColor: filterPassed === true ? '#10b981' : '#334155',
                color: '#f8fafc',
                border: 'none',
                padding: '0.35rem 0.75rem',
                borderRadius: '0.375rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Passed ({validationResults.filter((r) => r.passed).length})
            </button>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', fontSize: '0.75rem' }}>
                <th style={{ padding: '0.75rem' }}>RULE ID</th>
                <th style={{ padding: '0.75rem' }}>STATUS</th>
                <th style={{ padding: '0.75rem' }}>OBSERVED VALUE</th>
                <th style={{ padding: '0.75rem' }}>THRESHOLD</th>
                <th style={{ padding: '0.75rem' }}>SEVERITY</th>
                <th style={{ padding: '0.75rem' }}>DETAILS & VIOLATIONS</th>
                <th style={{ padding: '0.75rem' }}>TIMESTAMP</th>
              </tr>
            </thead>
            <tbody>
              {filteredResults.map((r) => (
                <tr key={r.result_id} style={{ borderBottom: '1px solid #1f293d' }}>
                  <td style={{ padding: '0.75rem', fontWeight: 600, color: '#f1f5f9' }}>{r.rule_id}</td>
                  <td style={{ padding: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      {r.passed ? (
                        <CheckCircle2 size={16} color="#10b981" />
                      ) : (
                        <XCircle size={16} color="#ef4444" />
                      )}
                      <span style={{
                        fontWeight: 600,
                        color: r.passed ? '#34d399' : '#f87171'
                      }}>
                        {r.passed ? 'PASSED' : 'FAILED'}
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '0.75rem', color: '#cbd5e1' }}>{r.observed_value ?? '--'}</td>
                  <td style={{ padding: '0.75rem', color: '#94a3b8' }}>{r.expected_threshold ?? '--'}</td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{
                      padding: '0.15rem 0.4rem',
                      borderRadius: '0.2rem',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      backgroundColor: r.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(100, 116, 139, 0.2)',
                      color: r.severity === 'CRITICAL' ? '#f87171' : '#cbd5e1'
                    }}>
                      {r.severity}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem', color: '#94a3b8', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                    {JSON.stringify(r.failure_details || {})}
                  </td>
                  <td style={{ padding: '0.75rem', color: '#64748b' }}>
                    {new Date(r.evaluated_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
