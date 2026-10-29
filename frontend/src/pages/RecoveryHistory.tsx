import React, { useState } from 'react';
import type { RecoveryAttempt, QuarantinedRecord } from '../types';
import { CheckCircle2, XCircle, Search } from 'lucide-react';

interface RecoveryHistoryProps {
  recoveryAttempts: RecoveryAttempt[];
  quarantinedRecords: QuarantinedRecord[];
}

export const RecoveryHistory: React.FC<RecoveryHistoryProps> = ({
  recoveryAttempts,
  quarantinedRecords,
}) => {
  const [activeView, setActiveView] = useState<'attempts' | 'quarantine'>('attempts');
  const [searchFilter, setSearchFilter] = useState('');

  const filteredQuarantine = quarantinedRecords.filter((q) =>
    q.dataset_name.toLowerCase().includes(searchFilter.toLowerCase()) ||
    q.rejection_reason.toLowerCase().includes(searchFilter.toLowerCase()) ||
    (q.source_identifier && q.source_identifier.toLowerCase().includes(searchFilter.toLowerCase()))
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Sub-header navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
            Recovery Audit Trail & Quarantine Ledger
          </h2>
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
            Immutable records of automated healings, zero-defect verifications, and quarantined dirty rows
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', backgroundColor: '#1e293b', padding: '0.25rem', borderRadius: '0.375rem' }}>
          <button
            onClick={() => setActiveView('attempts')}
            style={{
              backgroundColor: activeView === 'attempts' ? '#38bdf8' : 'transparent',
              color: activeView === 'attempts' ? '#0f172a' : '#cbd5e1',
              border: 'none',
              padding: '0.4rem 0.85rem',
              borderRadius: '0.25rem',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Recovery Attempts ({recoveryAttempts.length})
          </button>
          <button
            onClick={() => setActiveView('quarantine')}
            style={{
              backgroundColor: activeView === 'quarantine' ? '#38bdf8' : 'transparent',
              color: activeView === 'quarantine' ? '#0f172a' : '#cbd5e1',
              border: 'none',
              padding: '0.4rem 0.85rem',
              borderRadius: '0.25rem',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Quarantine Vault ({quarantinedRecords.length})
          </button>
        </div>
      </div>

      {activeView === 'attempts' ? (
        /* Recovery Attempts Table */
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '0.5rem',
          padding: '1.25rem'
        }}>
          {recoveryAttempts.length === 0 ? (
            <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.85rem' }}>
              No recovery attempts recorded yet.
            </p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', fontSize: '0.75rem' }}>
                    <th style={{ padding: '0.75rem' }}>ATTEMPT ID</th>
                    <th style={{ padding: '0.75rem' }}>STRATEGY APPLIED</th>
                    <th style={{ padding: '0.75rem' }}>STATUS</th>
                    <th style={{ padding: '0.75rem' }}>POST-VERIFICATION</th>
                    <th style={{ padding: '0.75rem' }}>DURATION</th>
                    <th style={{ padding: '0.75rem' }}>OPERATOR / POLICY</th>
                    <th style={{ padding: '0.75rem' }}>EXECUTION LOG</th>
                    <th style={{ padding: '0.75rem' }}>EXECUTED AT</th>
                  </tr>
                </thead>
                <tbody>
                  {recoveryAttempts.map((att) => {
                    const isSuccess = att.status === 'SUCCESS';
                    return (
                      <tr key={att.attempt_id} style={{ borderBottom: '1px solid #1f293d' }}>
                        <td style={{ padding: '0.75rem', fontFamily: 'monospace', color: '#94a3b8' }}>
                          {att.attempt_id.slice(0, 8)}...
                        </td>
                        <td style={{ padding: '0.75rem', fontWeight: 600, color: '#38bdf8' }}>
                          {att.strategy_applied}
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <span style={{
                            padding: '0.15rem 0.4rem',
                            borderRadius: '0.2rem',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            backgroundColor: isSuccess ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                            color: isSuccess ? '#34d399' : '#f87171'
                          }}>
                            {att.status}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                            {att.post_verification_passed ? (
                              <CheckCircle2 size={16} color="#10b981" />
                            ) : (
                              <XCircle size={16} color="#ef4444" />
                            )}
                            <span style={{
                              fontWeight: 600,
                              color: att.post_verification_passed ? '#34d399' : '#f87171'
                            }}>
                              {att.post_verification_passed ? 'PASSED' : 'FAILED'}
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: '0.75rem', color: '#94a3b8' }}>
                          {att.duration_ms ? `${att.duration_ms}ms` : '--'}
                        </td>
                        <td style={{ padding: '0.75rem', color: '#cbd5e1' }}>
                          {att.approved_by || att.policy_id || 'AUTOPILOT'}
                        </td>
                        <td style={{ padding: '0.75rem', color: '#94a3b8', fontSize: '0.75rem', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {att.execution_log || '--'}
                        </td>
                        <td style={{ padding: '0.75rem', color: '#64748b' }}>
                          {new Date(att.executed_at).toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Quarantined Records Table */
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '0.5rem',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <p style={{ margin: 0, fontSize: '0.85rem', color: '#94a3b8' }}>
              Isolated records preserved for forensic review and downstream replay without polluting analytics.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', backgroundColor: '#0f172a', padding: '0.25rem 0.5rem', borderRadius: '0.375rem', border: '1px solid #334155' }}>
              <Search size={14} color="#94a3b8" />
              <input
                type="text"
                placeholder="Search quarantine..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                style={{
                  backgroundColor: 'transparent',
                  border: 'none',
                  color: '#f8fafc',
                  outline: 'none',
                  fontSize: '0.8rem',
                  marginLeft: '0.5rem'
                }}
              />
            </div>
          </div>

          {filteredQuarantine.length === 0 ? (
            <p style={{ margin: '1rem 0', color: '#94a3b8', fontSize: '0.85rem' }}>
              No quarantined records matching filter.
            </p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', fontSize: '0.75rem' }}>
                    <th style={{ padding: '0.75rem' }}>QUARANTINE ID</th>
                    <th style={{ padding: '0.75rem' }}>DATASET</th>
                    <th style={{ padding: '0.75rem' }}>IDENTIFIER</th>
                    <th style={{ padding: '0.75rem' }}>REJECTION REASON</th>
                    <th style={{ padding: '0.75rem' }}>RECORD PAYLOAD</th>
                    <th style={{ padding: '0.75rem' }}>ISOLATED AT</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredQuarantine.map((q) => (
                    <tr key={q.quarantine_id} style={{ borderBottom: '1px solid #1f293d' }}>
                      <td style={{ padding: '0.75rem', fontFamily: 'monospace', color: '#94a3b8' }}>
                        {q.quarantine_id.slice(0, 8)}...
                      </td>
                      <td style={{ padding: '0.75rem', fontWeight: 600, color: '#f1f5f9' }}>
                        {q.dataset_name}
                      </td>
                      <td style={{ padding: '0.75rem', color: '#38bdf8' }}>
                        {q.source_identifier || 'N/A'}
                      </td>
                      <td style={{ padding: '0.75rem', color: '#f87171', fontWeight: 500 }}>
                        {q.rejection_reason}
                      </td>
                      <td style={{ padding: '0.75rem', fontFamily: 'monospace', fontSize: '0.75rem', color: '#94a3b8' }}>
                        {JSON.stringify(q.record_content)}
                      </td>
                      <td style={{ padding: '0.75rem', color: '#64748b' }}>
                        {new Date(q.quarantined_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
