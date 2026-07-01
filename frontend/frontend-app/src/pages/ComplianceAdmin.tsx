import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { complianceApi } from "../api/api";
import { clearAuthTokens } from "../utils/auth";
import "./CompliancePortal.css";

type ComplianceCase = {
  id: string;
  case_type: string;
  state: string;
  risk_tier: string;
  profile?: {
    id: string;
    party: {
      display_name: string;
      party_type: string;
      email?: string;
    };
  };
  restrictions?: Array<{
    id: string;
    restriction_type: string;
    reason_code: string;
    active: boolean;
  }>;
  vendor_cases?: Array<{
    id: string;
    external_case_id: string;
    sync_status: string;
  }>;
  evidence_documents?: Array<{
    id: string;
    document_type: string;
    storage_reference: string;
    vendor_reference: string;
  }>;
  risk_assessments?: Array<{
    id: string;
    risk_tier: string;
    triggered_rules: string[];
  }>;
};

type ReviewTask = {
  id: string;
  task_type: string;
  status: string;
  priority: string;
  assignee_email?: string;
  reason?: string;
};

const ComplianceAdmin: React.FC = () => {
  const navigate = useNavigate();
  const [cases, setCases] = useState<ComplianceCase[]>([]);
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [selectedCase, setSelectedCase] = useState<ComplianceCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [restrictionReason, setRestrictionReason] = useState("COMPLIANCE_REVIEW_HOLD");
  const [riskTier, setRiskTier] = useState("MEDIUM");
  const [triggeredRules, setTriggeredRules] = useState("MANUAL_REVIEW");
  const [evidenceDocumentType, setEvidenceDocumentType] = useState("ANALYST_NOTE");
  const [evidenceReference, setEvidenceReference] = useState("");
  const [syncPayload, setSyncPayload] = useState('{ "sync_status": "SYNCED", "screenings": [] }');

  const loadAdminWorkspace = async () => {
    setLoading(true);
    setError(null);
    try {
      const [casesRes, tasksRes] = await Promise.all([
        complianceApi.getAdminCases(),
        complianceApi.getAdminReviewTasks(),
      ]);
      setCases(casesRes.data);
      setTasks(tasksRes.data);
      const firstCaseId = selectedCaseId || casesRes.data[0]?.id || "";
      if (firstCaseId) {
        setSelectedCaseId(firstCaseId);
        const detailRes = await complianceApi.getAdminCaseDetail(firstCaseId);
        setSelectedCase(detailRes.data);
      } else {
        setSelectedCase(null);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to load compliance admin workspace.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminWorkspace();
  }, []);

  const handleLogout = () => {
    clearAuthTokens();
    navigate("/login");
  };

  const refreshSelectedCase = async (caseId: string) => {
    const response = await complianceApi.getAdminCaseDetail(caseId);
    setSelectedCase(response.data);
    setSelectedCaseId(caseId);
  };

  const runCaseAction = async (action: () => Promise<any>, successMessage: string) => {
    if (!selectedCaseId) return;
    setWorking(true);
    setMessage(null);
    setError(null);
    try {
      await action();
      setMessage(successMessage);
      await loadAdminWorkspace();
      await refreshSelectedCase(selectedCaseId);
    } catch (err: any) {
      setError(err.response?.data?.error || "Compliance admin action failed.");
    } finally {
      setWorking(false);
    }
  };

  const handleSyncVendorCase = async (vendorCaseId: string) => {
    let payload: Record<string, any> = {};
    try {
      payload = JSON.parse(syncPayload);
    } catch {
      setError("Vendor sync payload must be valid JSON.");
      return;
    }
    await runCaseAction(
      () => complianceApi.syncAdminVendorCase(vendorCaseId, { payload }),
      "Vendor sync dispatched successfully.",
    );
  };

  if (loading) {
    return <div className="compliance-portal-shell">Loading compliance admin workspace...</div>;
  }

  return (
    <div className="compliance-portal-shell">
      <header className="compliance-portal-header">
        <div>
          <div className="compliance-kicker">Compliance Operations</div>
          <h1>Reviewer and Manager Console</h1>
          <p>Drive case decisions, restrictions, vendor sync, and risk review from one place.</p>
        </div>
        <div className="compliance-header-actions">
          <Link to="/admin" className="compliance-link-btn">Back to Admin</Link>
          <button className="compliance-danger-btn" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      {error && <div className="compliance-banner compliance-banner-error">{error}</div>}
      {message && <div className="compliance-banner compliance-banner-success">{message}</div>}

      <section className="compliance-summary-grid">
        <article className="compliance-panel">
          <div className="compliance-section-head">
            <h2>Open Review Tasks</h2>
            <span>{tasks.length}</span>
          </div>
          <div className="compliance-scroll-list">
            {tasks.length ? (
              tasks.slice(0, 8).map((task) => (
                <div key={task.id} className="compliance-list-card">
                  <strong>{task.task_type}</strong>
                  <span>{task.status} / {task.priority}</span>
                  <small>{task.assignee_email || task.reason || "Unassigned"}</small>
                </div>
              ))
            ) : (
              <p>No review tasks currently queued.</p>
            )}
          </div>
        </article>

        <article className="compliance-panel compliance-case-list">
          <div className="compliance-section-head">
            <h2>Cases</h2>
            <span>{cases.length}</span>
          </div>
          {cases.map((item) => (
            <button
              key={item.id}
              className={`compliance-case-item ${selectedCaseId === item.id ? "active" : ""}`}
              onClick={() => refreshSelectedCase(item.id)}
            >
              <strong>{item.profile?.party?.display_name || item.case_type}</strong>
              <span>{item.case_type}</span>
              <small>{item.state} / {item.risk_tier}</small>
            </button>
          ))}
        </article>
      </section>

      <section className="compliance-panel compliance-case-detail">
        {selectedCase ? (
          <>
            <div className="compliance-section-head">
              <div>
                <h2>{selectedCase.profile?.party?.display_name || selectedCase.case_type}</h2>
                <p className="compliance-meta-line">
                  {selectedCase.case_type} | {selectedCase.state} | {selectedCase.risk_tier}
                </p>
              </div>
              {selectedCase.profile?.id && (
                <button
                  className="compliance-secondary-btn"
                  disabled={working}
                  onClick={() => runCaseAction(
                    () => complianceApi.rescreenProfile(selectedCase.profile!.id, { source: "manual_admin_rescreen" }),
                    "Rescreen workflow queued successfully.",
                  )}
                >
                  Queue Rescreen
                </button>
              )}
            </div>

            <div className="compliance-detail-columns">
              <div>
                <h3>Decision Actions</h3>
                <textarea
                  className="compliance-notes"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Reviewer or manager notes"
                />
                <div className="compliance-action-grid">
                  <button className="compliance-primary-btn" disabled={working} onClick={() => runCaseAction(
                    () => complianceApi.assignAdminCaseTask(selectedCase.id, { task_type: "INITIAL_REVIEW", priority: "MEDIUM", reason: notes || "Manual review assignment" }),
                    "Review task assigned.",
                  )}>
                    Assign Task
                  </button>
                  <button className="compliance-secondary-btn" disabled={working} onClick={() => runCaseAction(
                    () => complianceApi.requestAdminCaseInformation(selectedCase.id, { notes }),
                    "Request for information sent.",
                  )}>
                    Request Info
                  </button>
                  <button className="compliance-primary-btn" disabled={working} onClick={() => runCaseAction(
                    () => complianceApi.approveAdminCase(selectedCase.id, { notes }),
                    "Case approved.",
                  )}>
                    Approve
                  </button>
                  <button className="compliance-danger-btn" disabled={working} onClick={() => runCaseAction(
                    () => complianceApi.rejectAdminCase(selectedCase.id, { notes }),
                    "Case rejected.",
                  )}>
                    Reject
                  </button>
                </div>

                <h3>Restriction</h3>
                <input
                  value={restrictionReason}
                  onChange={(event) => setRestrictionReason(event.target.value)}
                  placeholder="Restriction reason code"
                />
                <button
                  className="compliance-danger-btn"
                  disabled={working}
                  onClick={() => runCaseAction(
                    () => complianceApi.restrictAdminCase(selectedCase.id, {
                      restriction_type: "FULL_ACCOUNT_RESTRICTION",
                      reason_code: restrictionReason,
                      notes,
                    }),
                    "Case restricted.",
                  )}
                >
                  Apply Restriction
                </button>

                {selectedCase.restrictions?.filter((item) => item.active).map((restriction) => (
                  <div key={restriction.id} className="compliance-list-card">
                    <strong>{restriction.restriction_type}</strong>
                    <span>{restriction.reason_code}</span>
                    <button
                      className="compliance-link-btn inline"
                      disabled={working}
                      onClick={() => runCaseAction(
                        () => complianceApi.liftRestriction(restriction.id, { notes }),
                        "Restriction lifted.",
                      )}
                    >
                      Lift
                    </button>
                  </div>
                ))}
              </div>

              <div>
                <h3>Risk Assessment</h3>
                <select value={riskTier} onChange={(event) => setRiskTier(event.target.value)}>
                  <option value="LOW">LOW</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="HIGH">HIGH</option>
                  <option value="PROHIBITED">PROHIBITED</option>
                </select>
                <input
                  value={triggeredRules}
                  onChange={(event) => setTriggeredRules(event.target.value)}
                  placeholder="Comma-separated triggered rules"
                />
                <button
                  className="compliance-secondary-btn"
                  disabled={working}
                  onClick={() => runCaseAction(
                    () => complianceApi.addAdminCaseRiskAssessment(selectedCase.id, {
                      risk_tier: riskTier,
                      triggered_rules: triggeredRules.split(",").map((item) => item.trim()).filter(Boolean),
                      score_snapshot: { source: "ui", timestamp: new Date().toISOString() },
                    }),
                    "Risk assessment recorded.",
                  )}
                >
                  Record Risk
                </button>

                <h3>Evidence</h3>
                <input
                  value={evidenceDocumentType}
                  onChange={(event) => setEvidenceDocumentType(event.target.value)}
                  placeholder="Document type"
                />
                <input
                  value={evidenceReference}
                  onChange={(event) => setEvidenceReference(event.target.value)}
                  placeholder="Storage reference"
                />
                <button
                  className="compliance-secondary-btn"
                  disabled={working}
                  onClick={() => runCaseAction(
                    () => complianceApi.addAdminCaseEvidence(selectedCase.id, {
                      document_type: evidenceDocumentType,
                      storage_mode: "APP_REFERENCE",
                      storage_reference: evidenceReference,
                    }),
                    "Evidence reference added.",
                  )}
                >
                  Add Evidence
                </button>

                <h3>Vendor Workflow</h3>
                <button
                  className="compliance-primary-btn"
                  disabled={working}
                  onClick={() => runCaseAction(
                    () => complianceApi.submitAdminCaseToVendor(selectedCase.id),
                    "Case submitted to vendor.",
                  )}
                >
                  Submit To Vendor
                </button>
                <textarea
                  className="compliance-notes"
                  value={syncPayload}
                  onChange={(event) => setSyncPayload(event.target.value)}
                  placeholder="Vendor sync payload JSON"
                />
                {selectedCase.vendor_cases?.map((vendorCase) => (
                  <div key={vendorCase.id} className="compliance-list-card">
                    <strong>{vendorCase.external_case_id}</strong>
                    <span>{vendorCase.sync_status}</span>
                    <button
                      className="compliance-link-btn inline"
                      disabled={working}
                      onClick={() => handleSyncVendorCase(vendorCase.id)}
                    >
                      Sync
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="compliance-empty-state">Select a compliance case to manage it.</div>
        )}
      </section>
    </div>
  );
};

export default ComplianceAdmin;
