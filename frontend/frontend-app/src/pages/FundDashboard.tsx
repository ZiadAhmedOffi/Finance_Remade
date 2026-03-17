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

interface Fund {
  id: string;
  name: string;
  description: string;
  steering_committee: string[];
  is_active: boolean;
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
  
  const [activeTab, setActiveTab] = useState<"model-inputs" | "deals" | "dashboard" | "aggregated-exits" | "admin-fee" | "basic-info" | "logs">("dashboard");
  const [fund, setFund] = useState<Fund | null>(null);
  const [logs, setLogs] = useState<FundLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [isSCMember, setIsSCMember] = useState(false);

  const checkPermissions = useCallback((fundData: Fund) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        const roles = payload.roles || [];
        
        const superAdmin = roles.some((r: any) => r.role === "SUPER_ADMIN");
        const scMember = roles.some((r: any) => r.role === "STEERING_COMMITTEE" && r.fund === fundData.name);
        
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
        description: newDescription
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
            <span className={`status-badge ${fund.is_active ? "active" : "inactive"}`}>
              {fund.is_active ? "Active" : "Inactive"}
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

          {activeTab === "admin-fee" && fundId && (
            <AdminFeeTab fundId={fundId} />
          )}

          {activeTab === "basic-info" && (
            <section className="basic-info-tab">
              <div className="content-card">
                {canEdit ? (
                  <form onSubmit={handleUpdateInfo} className="edit-form">
                    <h3>Edit Fund Information</h3>
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
                      <label>Description</label>
                      <textarea 
                        value={newDescription} 
                        onChange={(e) => setNewDescription(e.target.value)} 
                        rows={5}
                      />
                    </div>
                    <button type="submit" className="btn btn-primary">Update Information</button>
                  </form>
                ) : (
                  <div className="info-display">
                     <h3>Fund Information</h3>
                     <div className="info-grid">
                       <div className="info-item">
                         <label>Fund Name</label>
                         <p className="value">{fund.name}</p>
                       </div>
                       <div className="info-item full-width">
                         <label>Description</label>
                         <p className="value description">{fund.description || "No description provided."}</p>
                       </div>
                     </div>
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
                      {logs.map(log => (
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
              ) : <p>No logs available for this fund.</p>}
            </section>
          )}
        </div>
      </main>
    </div>
  );
};

export default FundDashboard;
