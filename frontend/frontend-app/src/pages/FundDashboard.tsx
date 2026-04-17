import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api/api";
import "./FundDashboard.css";
import ModelInputsTab from "../components/ModelInputsTab";
import CurrentDealsTab from "../components/CurrentDealsTab";
import DealPrognosisTab from "../components/DealPrognosisTab";
import FundPerformanceTab from "../components/FundPerformanceTab";
import AggregatedExitsTab from "../components/AggregatedExitsTab";
import AdminFeeTab from "../components/AdminFeeTab";
import RiskAssessmentTab from "../components/RiskAssessmentTab";
import InvestorLogTab from "../components/InvestorLogTab";
import ReportsTab from "../components/ReportsTab";

interface ReasonToInvest {
  title: string;
  brief_desc: string;
}

interface Fund {
  id: string;
  name: string;
  description: string;
  tag: string;
  sharia_compliant: boolean;
  region: string;
  focus: "GROWTH" | "YIELD" | null;
  overview: string;
  strategy: string;
  structure: string;
  strategy_and_fund_lifecycle: string;
  reasons_to_invest: ReasonToInvest[];
  steering_committee: string[];
  status: "ESTABLISHED" | "FUTURE" | "DEACTIVATED";
}

interface FundLog {
  id: string;
  actor_email: string;
  action: string;
  success: boolean;
  metadata: any;
  timestamp: string;
}

const FundDashboard: React.FC = () => {
  const { fundId } = useParams<{ fundId: string }>();
  const navigate = useNavigate();
  
  const [activeTab, setActiveTab] = useState<"model-inputs" | "deals" | "dashboard" | "aggregated-exits" | "risk" | "admin-fee" | "basic-info" | "logs" | "investor-log" | "reports">("dashboard");
  const [fund, setFund] = useState<Fund | null>(null);
  const [logs, setLogs] = useState<FundLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  
  // Pagination for action logs
  const [currentLogPage, setCurrentLogPage] = useState(1);
  const logsPerPage = 10;

  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newTag, setNewTag] = useState("VC");
  
  // New Fund Fields
  const [shariaCompliant, setShariaCompliant] = useState(false);
  const [region, setRegion] = useState("");
  const [focus, setFocus] = useState<"GROWTH" | "YIELD" | "">("");
  const [overview, setOverview] = useState("");
  const [strategy, setStrategy] = useState("");
  const [structure, setStructure] = useState("");
  const [strategyAndLifecycle, setStrategyAndLifecycle] = useState("");
  const [reasonsToInvest, setReasonsToInvest] = useState<ReasonToInvest[]>([]);
  
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [isSCMember, setIsSCMember] = useState(false);

  const checkPermissions = useCallback((fundData: Fund) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        const roles = payload.roles || [];
        
        const superAdmin = roles.some((r: any) => r.role === "SUPER_ADMIN");
        const scMember = roles.some((r: any) => r.role === "STEERING_COMMITTEE" && r.fund === fundData.id);
        
        setIsSuperAdmin(superAdmin);
        setIsSCMember(scMember);
      } catch (e) {
        console.error("Error decoding token", e);
      }
    }
  }, []);

  const fetchFundData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get(`/funds/${fundId}/`);
      setFund(response.data);
      setNewName(response.data.name);
      setNewDescription(response.data.description);
      setNewTag(response.data.tag);
      setShariaCompliant(response.data.sharia_compliant || false);
      setRegion(response.data.region || "");
      setFocus(response.data.focus || "");
      setOverview(response.data.overview || "");
      setStrategy(response.data.strategy || "");
      setStructure(response.data.structure || "");
      setStrategyAndLifecycle(response.data.strategy_and_fund_lifecycle || "");
      setReasonsToInvest(response.data.reasons_to_invest || []);
      checkPermissions(response.data);
      setError(null);
    } catch (err: any) {
      if (err.response?.status === 404 || err.response?.status === 403) {
        setError("404 - Fund not found or access denied.");
      } else {
        setError("Failed to fetch fund details.");
      }
    } finally {
      setLoading(false);
    }
  }, [fundId, checkPermissions]);

  const fetchLogs = useCallback(async () => {
    try {
      const response = await api.get(`/funds/${fundId}/logs/`);
      setLogs(response.data);
    } catch (err) {
      console.error("Failed to fetch logs", err);
    }
  }, [fundId]);

  useEffect(() => {
    fetchFundData();
  }, [fetchFundData]);

  useEffect(() => {
    if (activeTab === "logs") {
      fetchLogs();
    }
  }, [activeTab, fetchLogs]);

  const handleUpdateInfo = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.put(`/funds/${fundId}/`, {
        name: newName,
        description: newDescription,
        tag: newTag,
        sharia_compliant: shariaCompliant,
        region: region,
        focus: focus || null,
        overview: overview,
        strategy: strategy,
        structure: structure,
        strategy_and_fund_lifecycle: strategyAndLifecycle,
        reasons_to_invest: reasonsToInvest
      });
      setMessage("Fund information updated successfully.");
      fetchFundData();
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to update fund information.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/login");
  };

  if (loading) return <div className="fund-dashboard-container">Loading Fund Dashboard...</div>;
  if (error) return <div className="fund-dashboard-container"><div className="error-state">{error}</div></div>;
  if (!fund) return null;

  const canEdit = isSuperAdmin || isSCMember;

  const menuItems = [
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "deals", label: "Investment Deals", icon: "🤝" },
    { id: "model-inputs", label: "Model Inputs", icon: "⚙️" },
    { id: "aggregated-exits", label: "Aggregated Exits", icon: "📈" },
    { id: "risk", label: "Stability and Risk", icon: "⚖️" },
    ...(canEdit ? [{ id: "investor-log", label: "Investor Log", icon: "📋" }] : []),
    { id: "reports", label: "Reports", icon: "📄" },
    { id: "admin-fee", label: "Admin Fee", icon: "💰" },
    { id: "basic-info", label: "Basic Info", icon: "ℹ️" },
    ...(canEdit ? [{ id: "logs", label: "Action Logs", icon: "📝" }] : []),
  ];

  return (
    <div className="fund-dashboard-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand">FinanceRemade</div>
          <button className="back-link" onClick={() => navigate("/dashboard")}>
            &larr; Back to Funds
          </button>
        </div>
        
        <nav className="sidebar-nav">
          {menuItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${activeTab === item.id ? "active" : ""}`}
              onClick={() => setActiveTab(item.id as any)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <span className="user-icon">👤</span>
            <span className="user-role">{isSuperAdmin ? "Super Admin" : isSCMember ? "SC Member" : "Investor"}</span>
          </div>
          <button className="logout-button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="content-header">
          <div className="header-title">
            <h1>{fund.name}</h1>
            <span className={`status-badge ${fund.status === "DEACTIVATED" ? "inactive" : "active"}`}>
              {fund.status === "DEACTIVATED" ? "Inactive" : "Active"}
            </span>
          </div>
          <div className="header-actions">
            {message && <div className="alert-mini success">{message}</div>}
            {error && <div className="alert-mini error">{error}</div>}
          </div>
        </header>

        <div className="scrollable-content">
          {activeTab === "dashboard" && fundId && (
            <FundPerformanceTab fundId={fundId} />
          )}

          {activeTab === "deals" && fundId && (
            <div className="deals-content-wrapper">
              {canEdit && (
                <div className="content-card" style={{border: '1px dashed #007bff', background: '#f0f7ff', marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.5rem 2.5rem'}}>
                  <div>
                    <h3 style={{border: 'none', margin: 0, fontSize: '1.1rem', color: '#0056b3'}}>Bulk Upload Deals via Excel?</h3>
                    <p style={{margin: '0.25rem 0 0 0', fontSize: '0.9rem', color: '#64748b'}}>Use our Excel ingestion tool to add multiple deals at once.</p>
                  </div>
                  <button className="btn btn-primary" onClick={() => setActiveTab('model-inputs')}>
                    Go to Ingestion Tool &rarr;
                  </button>
                </div>
              )}
              
              <div style={{ marginBottom: "4rem" }}>
                <h2 style={{ marginBottom: "2rem", borderBottom: "2px solid #64748b", paddingBottom: "0.5rem", color: "#475569" }}>Current Deals (Already Made)</h2>
                <CurrentDealsTab fundId={fundId} canEdit={canEdit} />
              </div>
              
              <div style={{ marginTop: "4rem" }}>
                <h2 style={{ marginBottom: "2rem", borderBottom: "2px solid #007bff", paddingBottom: "0.5rem", color: "#0056b3" }}>Deal Prognosis (Future)</h2>
                <DealPrognosisTab fundId={fundId} canEdit={canEdit} />
              </div>
            </div>
          )}

          {activeTab === "model-inputs" && fundId && (
            <ModelInputsTab fundId={fundId} canEdit={canEdit} />
          )}

          {activeTab === "aggregated-exits" && fundId && (
            <AggregatedExitsTab fundId={fundId} />
          )}

          {activeTab === "risk" && fundId && (
            <RiskAssessmentTab fundId={fundId} canEdit={canEdit} />
          )}
          {activeTab === "investor-log" && canEdit && fundId && (
            <InvestorLogTab fundId={fundId} canEdit={canEdit} />
          )}

          {activeTab === "reports" && fundId && (
            <ReportsTab fundId={fundId} isAdmin={canEdit} />
          )}

          {activeTab === "admin-fee" && fundId && (
            <AdminFeeTab fundId={fundId} />
          )}
          {activeTab === "basic-info" && (
            <section className="basic-info-tab">
              <div className="content-card">
                {canEdit ? (
                  <form onSubmit={handleUpdateInfo} className="edit-form">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                      <h3 style={{ margin: 0, border: 'none' }}>Edit Fund Information</h3>
                      <button type="submit" className="btn btn-primary">Update Information</button>
                    </div>

                    <div className="info-grid-edit" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
                      <div className="form-group">
                        <label>Fund Name</label>
                        <input 
                          type="text" 
                          value={newName} 
                          onChange={(e) => setNewName(e.target.value)} 
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Fund Tag</label>
                        <select 
                          value={newTag} 
                          onChange={(e) => setNewTag(e.target.value)}
                          className="form-input"
                        >
                          <option value="BIC">BIC</option>
                          <option value="VC">VC</option>
                          <option value="VS">VS</option>
                          <option value="AIG">AIG</option>
                          <option value="SF">SF</option>
                          <option value="REAL_ESTATE">Real estate</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Region</label>
                        <input 
                          type="text" 
                          value={region} 
                          onChange={(e) => setRegion(e.target.value)} 
                          placeholder="e.g. Saudi Arabia"
                        />
                      </div>
                      <div className="form-group">
                        <label>Focus</label>
                        <select 
                          value={focus} 
                          onChange={(e) => setFocus(e.target.value as any)}
                          className="form-input"
                        >
                          <option value="">Select Focus</option>
                          <option value="GROWTH">Growth Focused</option>
                          <option value="YIELD">Yield Focused</option>
                        </select>
                      </div>
                      <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1.5rem' }}>
                        <input 
                          type="checkbox" 
                          id="sharia-compliant"
                          checked={shariaCompliant} 
                          onChange={(e) => setShariaCompliant(e.target.checked)} 
                        />
                        <label htmlFor="sharia-compliant" style={{ marginBottom: 0 }}>Sharia Compliant</label>
                      </div>
                    </div>

                    <div className="form-group" style={{ marginTop: '1.5rem' }}>
                      <label>Description (Short)</label>
                      <textarea 
                        value={newDescription} 
                        onChange={(e) => setNewDescription(e.target.value)} 
                        rows={3}
                      />
                    </div>

                    <div className="form-group" style={{ marginTop: '1.5rem' }}>
                      <label>Overview (In-depth)</label>
                      <textarea 
                        value={overview} 
                        onChange={(e) => setOverview(e.target.value)} 
                        rows={5}
                        placeholder="Provide a detailed overview of the fund for reports..."
                      />
                    </div>

                    <div className="info-grid-edit" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginTop: '1.5rem' }}>
                      <div className="form-group">
                        <label>Strategy</label>
                        <textarea 
                          value={strategy} 
                          onChange={(e) => setStrategy(e.target.value)} 
                          rows={3}
                        />
                      </div>
                      <div className="form-group">
                        <label>Structure</label>
                        <textarea 
                          value={structure} 
                          onChange={(e) => setStructure(e.target.value)} 
                          rows={3}
                        />
                      </div>
                    </div>

                    <div className="form-group" style={{ marginTop: '1.5rem' }}>
                      <label>Strategy & Fund Lifecycle</label>
                      <textarea 
                        value={strategyAndLifecycle} 
                        onChange={(e) => setStrategyAndLifecycle(e.target.value)} 
                        rows={5}
                        placeholder="Describe the investment strategy and lifecycle..."
                      />
                    </div>

                    <div className="reasons-section" style={{ marginTop: '2.5rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <h4 style={{ margin: 0 }}>Reasons to Invest</h4>
                        <button 
                          type="button" 
                          className="btn btn-secondary btn-sm"
                          onClick={() => setReasonsToInvest([...reasonsToInvest, { title: "", brief_desc: "" }])}
                        >
                          + Add Reason
                        </button>
                      </div>
                      
                      <div className="table-responsive">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th style={{ width: '30%' }}>Title</th>
                              <th>Brief Description</th>
                              <th style={{ width: '80px' }}>Action</th>
                            </tr>
                          </thead>
                          <tbody>
                            {reasonsToInvest.map((reason, idx) => (
                              <tr key={idx}>
                                <td>
                                  <input 
                                    type="text" 
                                    value={reason.title} 
                                    onChange={(e) => {
                                      const newReasons = [...reasonsToInvest];
                                      newReasons[idx].title = e.target.value;
                                      setReasonsToInvest(newReasons);
                                    }}
                                    placeholder="Title"
                                    className="form-input-sm"
                                  />
                                </td>
                                <td>
                                  <textarea 
                                    value={reason.brief_desc} 
                                    onChange={(e) => {
                                      const newReasons = [...reasonsToInvest];
                                      newReasons[idx].brief_desc = e.target.value;
                                      setReasonsToInvest(newReasons);
                                    }}
                                    placeholder="Brief description..."
                                    className="form-input-sm"
                                    rows={2}
                                  />
                                </td>
                                <td>
                                  <button 
                                    type="button" 
                                    className="btn-icon delete"
                                    onClick={() => setReasonsToInvest(reasonsToInvest.filter((_, i) => i !== idx))}
                                  >
                                    🗑️
                                  </button>
                                </td>
                              </tr>
                            ))}
                            {reasonsToInvest.length === 0 && (
                              <tr>
                                <td colSpan={3} style={{ textAlign: 'center', color: '#64748b', padding: '1rem' }}>
                                  No reasons added yet.
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </form>
                ) : (
                  <div className="info-display">
                     <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                        <h3 style={{ margin: 0, border: 'none' }}>Fund Information</h3>
                        {fund.sharia_compliant && <span className="status-badge" style={{ background: '#ecfdf5', color: '#059669', border: '1px solid #10b981' }}>Sharia Compliant</span>}
                     </div>
                     
                     <div className="info-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
                       <div className="info-item">
                         <label>Fund Name</label>
                         <p className="value">{fund.name}</p>
                       </div>
                       <div className="info-item">
                         <label>Tag</label>
                         <p className="value">{fund.tag === "REAL_ESTATE" ? "Real estate" : fund.tag}</p>
                       </div>
                       <div className="info-item">
                         <label>Region</label>
                         <p className="value">{fund.region || "N/A"}</p>
                       </div>
                       <div className="info-item">
                         <label>Focus</label>
                         <p className="value">{fund.focus === "GROWTH" ? "Growth Focused" : fund.focus === "YIELD" ? "Yield Focused" : "N/A"}</p>
                       </div>
                     </div>

                     <div className="info-item full-width" style={{ marginTop: '1.5rem' }}>
                         <label>Description</label>
                         <p className="value description">{fund.description || "No description provided."}</p>
                     </div>

                     {fund.overview && (
                       <div className="info-item full-width" style={{ marginTop: '1.5rem' }}>
                         <label>Overview</label>
                         <p className="value description">{fund.overview}</p>
                       </div>
                     )}

                     <div className="info-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginTop: '1.5rem' }}>
                       <div className="info-item">
                         <label>Strategy</label>
                         <p className="value">{fund.strategy || "N/A"}</p>
                       </div>
                       <div className="info-item">
                         <label>Structure</label>
                         <p className="value">{fund.structure || "N/A"}</p>
                       </div>
                     </div>

                     {fund.strategy_and_fund_lifecycle && (
                       <div className="info-item full-width" style={{ marginTop: '1.5rem' }}>
                         <label>Strategy & Lifecycle</label>
                         <p className="value description">{fund.strategy_and_fund_lifecycle}</p>
                       </div>
                     )}

                     {fund.reasons_to_invest && fund.reasons_to_invest.length > 0 && (
                       <div className="reasons-display" style={{ marginTop: '2rem' }}>
                         <label style={{ display: 'block', marginBottom: '1rem', fontWeight: 600, color: '#475569' }}>Reasons to Invest</label>
                         <div className="reasons-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1rem' }}>
                           {fund.reasons_to_invest.map((reason, idx) => (
                             <div key={idx} className="reason-card" style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                               <h5 style={{ margin: '0 0 0.5rem 0', color: '#1e293b' }}>{reason.title}</h5>
                               <p style={{ margin: 0, fontSize: '0.9rem', color: '#64748b' }}>{reason.brief_desc}</p>
                             </div>
                           ))}
                         </div>
                       </div>
                     )}
                  </div>
                )}
              </div>

              <div className="content-card">
                <div className="sc-display">
                  <h3>Steering Committee</h3>
                  {fund.steering_committee.length > 0 ? (
                    <div className="sc-grid">
                      {fund.steering_committee.map((email, idx) => (
                        <div key={idx} className="sc-member-card">
                          <div className="sc-icon">👤</div>
                          <div className="sc-email">{email}</div>
                        </div>
                      ))}
                    </div>
                  ) : <p className="empty-msg">No SC members assigned to this fund.</p>}
                </div>
              </div>
            </section>
          )}


          {activeTab === "logs" && canEdit && (
            <section className="logs-section content-card">
              <h3>Action Logs</h3>
              {logs.length > 0 ? (
                <>
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Timestamp</th>
                          <th>Actor</th>
                          <th>Action</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {logs.slice((currentLogPage - 1) * logsPerPage, currentLogPage * logsPerPage).map(log => (
                          <tr key={log.id}>
                            <td>{new Date(log.timestamp).toLocaleString()}</td>
                            <td>{log.actor_email}</td>
                            <td>{log.action}</td>
                            <td>
                              <span className={log.success ? "status-success" : "status-failed"}>
                                {log.success ? "Success" : "Failed"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {logs.length > logsPerPage && (
                    <div className="pagination-controls" style={{marginTop: '2rem', display: 'flex', justifyContent: 'center', gap: '0.5rem'}}>
                      {Array.from({ length: Math.ceil(logs.length / logsPerPage) }, (_, i) => (
                        <button
                          key={i}
                          onClick={() => setCurrentLogPage(i + 1)}
                          className={`btn ${currentLogPage === i + 1 ? 'btn-primary' : 'btn-secondary'}`}
                          style={{minWidth: '2.5rem'}}
                        >
                          {i + 1}
                        </button>
                      ))}
                    </div>
                  )}
                </>
              ) : <p>No logs available for this fund.</p>}
            </section>
          )}
        </div>
      </main>
    </div>
  );
};

export default FundDashboard;
