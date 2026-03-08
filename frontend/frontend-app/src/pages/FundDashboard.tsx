import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api/api";
import "./FundDashboard.css";
import ModelInputsTab from "../components/ModelInputsTab";
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
  
  const [activeTab, setActiveTab] = useState<"model-inputs" | "deals" | "dashboard" | "aggregated-exits" | "admin-fee" | "basic-info" | "logs">("model-inputs");
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

  return (
    <div className="fund-dashboard-container">
      <header className="fund-header">
        <div className="header-left">
          <button className="back-btn" onClick={() => navigate("/dashboard")}>&larr; Funds</button>
          <div className="fund-title-block">
            <h1>{fund.name}</h1>
            <span className="badge">{fund.is_active ? "Active" : "Inactive"}</span>
          </div>
        </div>
        <div className="header-right">
          <button className="btn-logout" onClick={handleLogout}>Logout</button>
        </div>
      </header>
      
      <div className="alert-container">
        {message && <div className="alert alert-success">{message}</div>}
        {error && <div className="alert alert-error">{error}</div>}
      </div>

      <div className="tabs-container">
        <div className="tabs">
          <button 
            className={activeTab === "model-inputs" ? "tab-btn active" : "tab-btn"}
            onClick={() => setActiveTab("model-inputs")}
          >
            Model Inputs
          </button>
          <button 
            className={activeTab === "deals" ? "tab-btn active" : "tab-btn"}
            onClick={() => setActiveTab("deals")}
          >
            Deal Prognosis
          </button>
          <button 
            className={activeTab === "dashboard" ? "tab-btn active" : "tab-btn"}
            onClick={() => setActiveTab("dashboard")}
          >
            Dashboard
          </button>
          <button 
            className={activeTab === "aggregated-exits" ? "tab-btn active" : "tab-btn"}
            onClick={() => setActiveTab("aggregated-exits")}
          >
            Aggregated Exits
          </button>
          <button 
            className={activeTab === "admin-fee" ? "tab-btn active" : "tab-btn"}
            onClick={() => setActiveTab("admin-fee")}
          >
            Admin Fee
          </button>
          <button 
            className={activeTab === "basic-info" ? "tab-btn active" : "tab-btn"}
            onClick={() => setActiveTab("basic-info")}
          >
            Basic Info
          </button>
          {canEdit && (
            <button 
              className={activeTab === "logs" ? "tab-btn active" : "tab-btn"}
              onClick={() => setActiveTab("logs")}
            >
              Logs
            </button>
          )}
        </div>
      </div>

      <div className="tab-content">
        {activeTab === "model-inputs" && fundId && (
          <ModelInputsTab fundId={fundId} canEdit={canEdit} />
        )}

        {activeTab === "deals" && fundId && (
          <DealPrognosisTab fundId={fundId} canEdit={canEdit} />
        )}

        {activeTab === "dashboard" && fundId && (
          <FundPerformanceTab fundId={fundId} />
        )}

        {activeTab === "aggregated-exits" && fundId && (
          <AggregatedExitsTab fundId={fundId} />
        )}

        {activeTab === "admin-fee" && fundId && (
          <AdminFeeTab fundId={fundId} />
        )}

        {activeTab === "basic-info" && (
          <section className="basic-info-section">
            <div className="card-container">
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
                   <div className="info-row">
                     <label>Fund Name</label>
                     <p>{fund.name}</p>
                   </div>
                   <div className="info-row">
                     <label>Description</label>
                     <p>{fund.description || "No description provided."}</p>
                   </div>
                </div>
              )}
              
              <div className="sc-display" style={{marginTop: "2rem"}}>
                <h3>Steering Committee</h3>
                {fund.steering_committee.length > 0 ? (
                  <ul className="sc-list">
                    {fund.steering_committee.map((email, idx) => (
                      <li key={idx}>{email}</li>
                    ))}
                  </ul>
                ) : <p>No SC members assigned.</p>}
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
    </div>
  );
};

export default FundDashboard;
