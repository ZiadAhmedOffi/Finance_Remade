import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { complianceApi } from "../api/api";
import { clearAuthTokens } from "../utils/auth";
import "./CompliancePortal.css";

type ComplianceProfile = {
  id: string;
  party: {
    display_name: string;
    party_type: string;
    email?: string;
  };
  current_state: string;
  current_risk_tier: string;
  operability_blocked: boolean;
  active_restrictions?: Array<{
    id: string;
    restriction_type: string;
    reason_code: string;
    active: boolean;
  }>;
};

type ComplianceCase = {
  id: string;
  case_type: string;
  state: string;
  risk_tier: string;
  opened_at: string;
  submitted_at?: string | null;
  vendor_cases?: Array<{
    id: string;
    external_case_id: string;
    sync_status: string;
    last_error?: string;
  }>;
  review_tasks?: Array<{
    id: string;
    task_type: string;
    status: string;
    priority: string;
    reason: string;
  }>;
  evidence_documents?: Array<{
    id: string;
    document_type: string;
    storage_mode: string;
    storage_reference: string;
    vendor_reference: string;
    created_at: string;
  }>;
  decisions?: Array<{
    id: string;
    decision_type: string;
    notes: string;
    created_at: string;
  }>;
};

const initialEvidenceForm = {
  document_type: "PROOF_OF_ADDRESS",
  storage_mode: "APP_REFERENCE",
  storage_reference: "",
  vendor_reference: "",
};

const CompliancePortal: React.FC = () => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<ComplianceProfile | null>(null);
  const [cases, setCases] = useState<ComplianceCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>("");
  const [selectedCase, setSelectedCase] = useState<ComplianceCase | null>(null);
  const [entityForm, setEntityForm] = useState({
    display_name: "",
    legal_name: "",
    jurisdiction: "",
    country_code: "",
  });
  const [evidenceForm, setEvidenceForm] = useState(initialEvidenceForm);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadCaseDetail = async (caseId: string) => {
    const response = await complianceApi.getMyCaseDetail(caseId);
    setSelectedCase(response.data);
  };

  const loadPortal = async () => {
    setLoading(true);
    setError(null);
    try {
      const [profileRes, casesRes] = await Promise.all([
        complianceApi.getMyProfile(),
        complianceApi.getMyCases(),
      ]);
      setProfile(profileRes.data);
      setCases(casesRes.data);
      const firstCaseId = selectedCaseId || casesRes.data[0]?.id || "";
      if (firstCaseId) {
        setSelectedCaseId(firstCaseId);
        await loadCaseDetail(firstCaseId);
      } else {
        setSelectedCase(null);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to load compliance portal.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPortal();
  }, []);

  const handleLogout = () => {
    clearAuthTokens();
    navigate("/login");
  };

  const handleCaseSelection = async (caseId: string) => {
    setSelectedCaseId(caseId);
    setMessage(null);
    setError(null);
    try {
      await loadCaseDetail(caseId);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to load case detail.");
    }
  };

  const handleSubmitCase = async () => {
    if (!selectedCaseId) return;
    setSubmitting(true);
    setMessage(null);
    setError(null);
    try {
      await complianceApi.submitMyCase(selectedCaseId);
      setMessage("Case submitted to compliance successfully.");
      await loadPortal();
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to submit case.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddEvidence = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedCaseId) return;
    setSubmitting(true);
    setMessage(null);
    setError(null);
    try {
      await complianceApi.addMyCaseEvidence(selectedCaseId, evidenceForm);
      setEvidenceForm(initialEvidenceForm);
      setMessage("Evidence reference added successfully.");
      await loadCaseDetail(selectedCaseId);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to add evidence.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateEntity = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);
    setError(null);
    try {
      await complianceApi.createEntityProfile(entityForm);
      setEntityForm({
        display_name: "",
        legal_name: "",
        jurisdiction: "",
        country_code: "",
      });
      setMessage("Entity KYB profile created successfully.");
      await loadPortal();
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to create entity compliance profile.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="compliance-portal-shell">Loading compliance workspace...</div>;
  }

  return (
    <div className="compliance-portal-shell">
      <header className="compliance-portal-header">
        <div>
          <div className="compliance-kicker">Compliance Workspace</div>
          <h1>KYC / KYB / AML Portal</h1>
          <p>Track onboarding state, submit evidence references, and follow reviewer actions.</p>
        </div>
        <div className="compliance-header-actions">
          <Link to="/dashboard" className="compliance-link-btn">Back to Dashboard</Link>
          <button className="compliance-danger-btn" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      {error && <div className="compliance-banner compliance-banner-error">{error}</div>}
      {message && <div className="compliance-banner compliance-banner-success">{message}</div>}

      <section className="compliance-summary-grid">
        <article className="compliance-panel compliance-profile-panel">
          <h2>Profile Status</h2>
          {profile ? (
            <>
              <div className="compliance-status-row">
                <span className={`compliance-badge compliance-badge-${profile.current_state.toLowerCase()}`}>
                  {profile.current_state}
                </span>
                <span className="compliance-mono">{profile.current_risk_tier}</span>
              </div>
              <div className="compliance-key-value">
                <span>Subject</span>
                <strong>{profile.party.display_name}</strong>
              </div>
              <div className="compliance-key-value">
                <span>Type</span>
                <strong>{profile.party.party_type}</strong>
              </div>
              <div className="compliance-key-value">
                <span>Operability</span>
                <strong>{profile.operability_blocked ? "Blocked" : "Active"}</strong>
              </div>
              <div className="compliance-restrictions">
                <h3>Active Restrictions</h3>
                {profile.active_restrictions?.length ? (
                  profile.active_restrictions.map((restriction) => (
                    <div key={restriction.id} className="compliance-restriction-chip">
                      {restriction.restriction_type}: {restriction.reason_code}
                    </div>
                  ))
                ) : (
                  <p>No active restrictions.</p>
                )}
              </div>
            </>
          ) : (
            <p>No compliance profile found.</p>
          )}
        </article>

        <article className="compliance-panel">
          <h2>Create Entity KYB Case</h2>
          <form className="compliance-form" onSubmit={handleCreateEntity}>
            <input
              value={entityForm.display_name}
              onChange={(event) => setEntityForm((prev) => ({ ...prev, display_name: event.target.value }))}
              placeholder="Entity display name"
              required
            />
            <input
              value={entityForm.legal_name}
              onChange={(event) => setEntityForm((prev) => ({ ...prev, legal_name: event.target.value }))}
              placeholder="Legal name"
            />
            <input
              value={entityForm.jurisdiction}
              onChange={(event) => setEntityForm((prev) => ({ ...prev, jurisdiction: event.target.value }))}
              placeholder="Jurisdiction"
            />
            <input
              value={entityForm.country_code}
              onChange={(event) => setEntityForm((prev) => ({ ...prev, country_code: event.target.value.toUpperCase() }))}
              placeholder="Country code"
              maxLength={2}
            />
            <button type="submit" className="compliance-primary-btn" disabled={submitting}>
              Create Entity Profile
            </button>
          </form>
        </article>
      </section>

      <section className="compliance-main-grid">
        <aside className="compliance-panel compliance-case-list">
          <div className="compliance-section-head">
            <h2>My Cases</h2>
            <span>{cases.length}</span>
          </div>
          {cases.length ? (
            cases.map((item) => (
              <button
                key={item.id}
                className={`compliance-case-item ${selectedCaseId === item.id ? "active" : ""}`}
                onClick={() => handleCaseSelection(item.id)}
              >
                <strong>{item.case_type}</strong>
                <span>{item.state}</span>
                <small>{item.risk_tier}</small>
              </button>
            ))
          ) : (
            <p>No compliance cases available yet.</p>
          )}
        </aside>

        <section className="compliance-panel compliance-case-detail">
          {selectedCase ? (
            <>
              <div className="compliance-section-head">
                <div>
                  <h2>{selectedCase.case_type}</h2>
                  <p className="compliance-meta-line">
                    State: {selectedCase.state} | Risk: {selectedCase.risk_tier}
                  </p>
                </div>
                <button
                  className="compliance-primary-btn"
                  onClick={handleSubmitCase}
                  disabled={submitting || !["DRAFT", "WAITING_FOR_APPLICANT"].includes(selectedCase.state)}
                >
                  Submit Case
                </button>
              </div>

              <div className="compliance-detail-columns">
                <div>
                  <h3>Evidence References</h3>
                  {selectedCase.evidence_documents?.length ? (
                    selectedCase.evidence_documents.map((document) => (
                      <div key={document.id} className="compliance-list-card">
                        <strong>{document.document_type}</strong>
                        <span>{document.storage_mode}</span>
                        <small>{document.storage_reference || document.vendor_reference || "No reference set"}</small>
                      </div>
                    ))
                  ) : (
                    <p>No evidence references recorded.</p>
                  )}

                  <form className="compliance-form" onSubmit={handleAddEvidence}>
                    <select
                      value={evidenceForm.document_type}
                      onChange={(event) => setEvidenceForm((prev) => ({ ...prev, document_type: event.target.value }))}
                    >
                      <option value="PROOF_OF_ADDRESS">Proof of Address</option>
                      <option value="PASSPORT">Passport</option>
                      <option value="NATIONAL_ID">National ID</option>
                      <option value="INCORPORATION_DOC">Incorporation Document</option>
                      <option value="OWNERSHIP_CHART">Ownership Chart</option>
                    </select>
                    <select
                      value={evidenceForm.storage_mode}
                      onChange={(event) => setEvidenceForm((prev) => ({ ...prev, storage_mode: event.target.value }))}
                    >
                      <option value="APP_REFERENCE">App Reference</option>
                      <option value="VENDOR_REFERENCE">Vendor Reference</option>
                    </select>
                    <input
                      value={evidenceForm.storage_reference}
                      onChange={(event) => setEvidenceForm((prev) => ({ ...prev, storage_reference: event.target.value }))}
                      placeholder="Storage reference"
                    />
                    <input
                      value={evidenceForm.vendor_reference}
                      onChange={(event) => setEvidenceForm((prev) => ({ ...prev, vendor_reference: event.target.value }))}
                      placeholder="Vendor reference"
                    />
                    <button type="submit" className="compliance-secondary-btn" disabled={submitting}>
                      Add Evidence Reference
                    </button>
                  </form>
                </div>

                <div>
                  <h3>Workflow Activity</h3>
                  {selectedCase.review_tasks?.length ? (
                    selectedCase.review_tasks.map((task) => (
                      <div key={task.id} className="compliance-list-card">
                        <strong>{task.task_type}</strong>
                        <span>{task.status}</span>
                        <small>{task.reason || task.priority}</small>
                      </div>
                    ))
                  ) : (
                    <p>No reviewer tasks visible yet.</p>
                  )}

                  <h3>Vendor Checks</h3>
                  {selectedCase.vendor_cases?.length ? (
                    selectedCase.vendor_cases.map((vendorCase) => (
                      <div key={vendorCase.id} className="compliance-list-card">
                        <strong>{vendorCase.external_case_id}</strong>
                        <span>{vendorCase.sync_status}</span>
                        <small>{vendorCase.last_error || "No vendor errors"}</small>
                      </div>
                    ))
                  ) : (
                    <p>No vendor checks submitted yet.</p>
                  )}

                  <h3>Decisions</h3>
                  {selectedCase.decisions?.length ? (
                    selectedCase.decisions.map((decision) => (
                      <div key={decision.id} className="compliance-list-card">
                        <strong>{decision.decision_type}</strong>
                        <small>{decision.notes || "No reviewer notes."}</small>
                      </div>
                    ))
                  ) : (
                    <p>No decisions recorded yet.</p>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="compliance-empty-state">Select a case to inspect its workflow details.</div>
          )}
        </section>
      </section>
    </div>
  );
};

export default CompliancePortal;
