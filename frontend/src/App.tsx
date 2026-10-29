import React, { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { Overview } from './pages/Overview';
import { Pipelines } from './pages/Pipelines';
import { DataQuality } from './pages/DataQuality';
import { Incidents } from './pages/Incidents';
import { RecoveryHistory } from './pages/RecoveryHistory';
import { api } from './services/api';
import type {
  Pipeline, PipelineRun, FailureIncident, ValidationResult,
  DetectedAnomaly, RecoveryAttempt, QuarantinedRecord, QualityScore
} from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [systemStatus, setSystemStatus] = useState<string>('UP');
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isTriggering, setIsTriggering] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState<string | null>(null);

  // Platform Telemetry State
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [incidents, setIncidents] = useState<FailureIncident[]>([]);
  const [validationResults, setValidationResults] = useState<ValidationResult[]>([]);
  const [anomalies, setAnomalies] = useState<DetectedAnomaly[]>([]);
  const [recoveryAttempts, setRecoveryAttempts] = useState<RecoveryAttempt[]>([]);
  const [quarantinedRecords, setQuarantinedRecords] = useState<QuarantinedRecord[]>([]);
  const [qualityScore, setQualityScore] = useState<QualityScore | null>(null);

  const fetchAllData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const [
        healthRes, pipelinesRes, runsRes, incidentsRes,
        qualityRes, anomaliesRes, scoreRes, attemptsRes, quarantineRes
      ] = await Promise.allSettled([
        api.getHealth(),
        api.getPipelines(),
        api.getRuns(),
        api.getIncidents(),
        api.getQualityResults(),
        api.getAnomalies(),
        api.getQualityScore(),
        api.getRecoveryAttempts(),
        api.getQuarantinedRecords(),
      ]);

      if (healthRes.status === 'fulfilled') setSystemStatus(healthRes.value.status);
      if (pipelinesRes.status === 'fulfilled') setPipelines(pipelinesRes.value);
      if (runsRes.status === 'fulfilled') setRuns(runsRes.value);
      if (incidentsRes.status === 'fulfilled') setIncidents(incidentsRes.value);
      if (qualityRes.status === 'fulfilled') setValidationResults(qualityRes.value);
      if (anomaliesRes.status === 'fulfilled') setAnomalies(anomaliesRes.value);
      if (scoreRes.status === 'fulfilled') setQualityScore(scoreRes.value);
      if (attemptsRes.status === 'fulfilled') setRecoveryAttempts(attemptsRes.value);
      if (quarantineRes.status === 'fulfilled') setQuarantinedRecords(quarantineRes.value);
    } catch (e) {
      console.error('Failed fetching telemetry:', e);
      setSystemStatus('DEGRADED');
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 15000); // Poll every 15s
    return () => clearInterval(interval);
  }, [fetchAllData]);

  const handleTriggerPipeline = async (pipelineId: string) => {
    setIsTriggering(pipelineId);
    try {
      await api.triggerPipeline(pipelineId, true);
      await fetchAllData();
    } catch (e: any) {
      alert(`Pipeline execution error: ${e.message}`);
    } finally {
      setIsTriggering(null);
    }
  };

  const handleRetryIncident = async (incidentId: string) => {
    setIsProcessing(incidentId);
    try {
      await api.retryIncident(incidentId);
      await fetchAllData();
    } catch (e: any) {
      alert(`Healing retry failed: ${e.message}`);
    } finally {
      setIsProcessing(null);
    }
  };

  const handleDryRunRecovery = async (incidentId: string) => {
    return await api.dryRunRecovery(incidentId);
  };

  const handleApproveRecovery = async (incidentId: string) => {
    setIsProcessing(incidentId);
    try {
      await api.approveRecovery(incidentId, 'LEAD_DATA_ENGINEER');
      await fetchAllData();
    } catch (e: any) {
      alert(`Approval error: ${e.message}`);
    } finally {
      setIsProcessing(null);
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#0b0f19', color: '#f8fafc' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
        onRefresh={fetchAllData}
        isRefreshing={isRefreshing}
      />

      <main style={{ maxWidth: '1400px', margin: '0 auto', padding: '1.5rem' }}>
        {activeTab === 'overview' && (
          <Overview
            pipelines={pipelines}
            runs={runs}
            incidents={incidents}
            recoveryAttempts={recoveryAttempts}
            qualityScore={qualityScore}
            onNavigateToTab={setActiveTab}
          />
        )}

        {activeTab === 'pipelines' && (
          <Pipelines
            pipelines={pipelines}
            runs={runs}
            onTriggerPipeline={handleTriggerPipeline}
            isTriggering={isTriggering}
          />
        )}

        {activeTab === 'quality' && (
          <DataQuality
            validationResults={validationResults}
            anomalies={anomalies}
            qualityScore={qualityScore}
          />
        )}

        {activeTab === 'incidents' && (
          <Incidents
            incidents={incidents}
            onRetryIncident={handleRetryIncident}
            onDryRunRecovery={handleDryRunRecovery}
            onApproveRecovery={handleApproveRecovery}
            isProcessing={isProcessing}
          />
        )}

        {activeTab === 'recovery' && (
          <RecoveryHistory
            recoveryAttempts={recoveryAttempts}
            quarantinedRecords={quarantinedRecords}
          />
        )}
      </main>
    </div>
  );
};

export default App;
