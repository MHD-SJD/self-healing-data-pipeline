import React, { useState } from 'react';
import type { FailureIncident } from '../types';
import { AlertOctagon, CheckCircle, Eye, ThumbsUp, Wrench } from 'lucide-react';

interface IncidentsProps {
  incidents: FailureIncident[];
  onRetryIncident: (incidentId: string) => Promise<void>;
  onDryRunRecovery: (incidentId: string) => Promise<any>;
  onApproveRecovery: (incidentId: string) => Promise<void>;
  isProcessing: string | null;
}

export const Incidents: React.FC<IncidentsProps> = ({
  incidents,
  onRetryIncident,
  onDryRunRecovery,
  onApproveRecovery,
  isProcessing,
}) => {
  const [dryRunModal, setDryRunModal] = useState<any | null>(null);

  const handleSimulateDryRun = async (incident: FailureIncident) => {
    try {
      const result = await onDryRunRecovery(incident.incident_id);
      setDryRunModal(result);
    } catch (e: any) {
      alert(`Dry run failed: ${e.message}`);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
            Failure Incident Queue & Governance
          </h2>
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
            Deterministic taxonomy classification with safe human approval gates for high-risk mutations
          </p>
        </div>
      </div>

      {incidents.length === 0 ? (
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '0.5rem',
          padding: '3rem',
          textAlign: 'center'
        }}>
          <CheckCircle size={48} color="#10b981" style={{ margin: '0 auto 1rem' }} />
          <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1.2rem' }}>Zero Active Incidents</h3>
          <p style={{ margin: '0.5rem 0 0', color: '#94a3b8', fontSize: '0.85rem' }}>
            All ingested data batches have been validated and healed successfully.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {incidents.map((inc) => {
            const isResolved = inc.status === 'RESOLVED';
            const isPendingApproval = inc.status === 'PENDING_APPROVAL';
            const isEscalated = inc.status === 'ESCALATED_HUMAN_REQUIRED';
            const isBusy = isProcessing === inc.incident_id;

            return (
              <div
                key={inc.incident_id}
                style={{
                  backgroundColor: '#1e293b',
                  border: isPendingApproval ? '2px solid #f59e0b' : '1px solid #334155',
                  borderRadius: '0.5rem',
                  padding: '1.25rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{
                      backgroundColor: isResolved ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                      padding: '0.5rem',
                      borderRadius: '0.375rem',
                      color: isResolved ? '#10b981' : '#ef4444'
                    }}>
                      <AlertOctagon size={22} />
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                          {inc.failure_category}
                        </span>
                        <span style={{
                          padding: '0.15rem 0.4rem',
                          borderRadius: '0.2rem',
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          backgroundColor: inc.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                          color: inc.severity === 'CRITICAL' ? '#f87171' : '#fbbf24'
                        }}>
                          {inc.severity}
                        </span>
                        <span style={{
                          padding: '0.15rem 0.4rem',
                          borderRadius: '0.2rem',
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          backgroundColor: isResolved ? 'rgba(16, 185, 129, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                          color: isResolved ? '#34d399' : '#38bdf8'
                        }}>
                          {inc.status}
                        </span>
                      </div>
                      <p style={{ margin: '0.35rem 0 0', fontSize: '0.85rem', color: '#cbd5e1' }}>
                        {inc.explanation}
                      </p>
                    </div>
                  </div>

                  {/* Incident Action Buttons */}
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      onClick={() => handleSimulateDryRun(inc)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        backgroundColor: '#334155',
                        color: '#cbd5e1',
                        border: 'none',
                        padding: '0.4rem 0.75rem',
                        borderRadius: '0.375rem',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                    >
                      <Eye size={14} />
                      Simulate Dry-Run
                    </button>

                    {(isPendingApproval || isEscalated) && (
                      <button
                        onClick={() => onApproveRecovery(inc.incident_id)}
                        disabled={isBusy}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          backgroundColor: '#10b981',
                          color: '#0f172a',
                          border: 'none',
                          padding: '0.4rem 0.75rem',
                          borderRadius: '0.375rem',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          cursor: isBusy ? 'not-allowed' : 'pointer'
                        }}
                      >
                        <ThumbsUp size={14} />
                        {isBusy ? 'Authorizing...' : 'Authorize Recovery'}
                      </button>
                    )}

                    {!isResolved && !isPendingApproval && (
                      <button
                        onClick={() => onRetryIncident(inc.incident_id)}
                        disabled={isBusy}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          backgroundColor: '#38bdf8',
                          color: '#0f172a',
                          border: 'none',
                          padding: '0.4rem 0.75rem',
                          borderRadius: '0.375rem',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          cursor: isBusy ? 'not-allowed' : 'pointer'
                        }}
                      >
                        <Wrench size={14} />
                        {isBusy ? 'Healing...' : 'Heal Incident'}
                      </button>
                    )}
                  </div>
                </div>

                {/* Evidence & Metrics Drawer */}
                <div style={{
                  marginTop: '1rem',
                  padding: '0.75rem',
                  backgroundColor: '#0f172a',
                  borderRadius: '0.375rem',
                  border: '1px solid #334155',
                  fontSize: '0.75rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '0.5rem'
                }}>
                  <div style={{ display: 'flex', gap: '1rem', color: '#94a3b8' }}>
                    <span>Dataset: <strong style={{ color: '#cbd5e1' }}>{inc.dataset_name}</strong></span>
                    <span>Recommended: <strong style={{ color: '#38bdf8' }}>{inc.recommended_action}</strong></span>
                    <span>Human Approval Required: <strong style={{ color: inc.requires_human_approval ? '#fbbf24' : '#34d399' }}>
                      {inc.requires_human_approval ? 'YES' : 'NO'}
                    </strong></span>
                  </div>
                  <span style={{ color: '#64748b' }}>
                    Created: {new Date(inc.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Dry Run Simulation Modal */}
      {dryRunModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 50,
          padding: '1rem'
        }}>
          <div style={{
            backgroundColor: '#1e293b',
            border: '1px solid #38bdf8',
            borderRadius: '0.5rem',
            maxWidth: '600px',
            width: '100%',
            padding: '1.5rem',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)'
          }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '1.15rem', color: '#38bdf8', fontWeight: 700 }}>
              Dry-Run Recovery Preview (Non-Mutating)
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
              <div><strong>Proposed Strategy:</strong> {dryRunModal.strategy}</div>
              <div><strong>Action:</strong> {dryRunModal.proposed_action}</div>
              <div><strong>Impacted Rows to Quarantine:</strong> {dryRunModal.impacted_rows}</div>
              <div><strong>Requires Human Authorization:</strong> {dryRunModal.will_require_approval ? 'YES' : 'NO'}</div>
              <div style={{
                marginTop: '0.5rem',
                padding: '0.75rem',
                backgroundColor: '#0f172a',
                borderRadius: '0.375rem',
                maxHeight: '180px',
                overflowY: 'auto',
                fontFamily: 'monospace',
                fontSize: '0.75rem'
              }}>
                {JSON.stringify(dryRunModal.summary, null, 2)}
              </div>
            </div>

            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                onClick={() => setDryRunModal(null)}
                style={{
                  backgroundColor: '#334155',
                  color: '#cbd5e1',
                  border: 'none',
                  padding: '0.5rem 1rem',
                  borderRadius: '0.375rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
