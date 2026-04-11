import React, { useState, useEffect, useCallback } from "react";
import { fundsApi } from "../api/api";
import "../pages/FundDashboard.css";

interface Report {
  id: string;
  slug: string;
  name: string;
  fund: string;
  fund_name: string;
  status: "ACTIVE" | "INACTIVE" | "GENERATING" | "FAILED";
  static_url: string;
  created_by_email: string;
  created_at: string;
}

interface ReportsTabProps {
  fundId: string;
  isAdmin: boolean;
}

const ReportsTab: React.FC<ReportsTabProps> = ({ fundId, isAdmin }) => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [newReportName, setNewReportName] = useState("");

  const fetchReports = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fundsApi.getReports();
      // Filter for this fund if needed, or show all if backend already filtered
      const fundReports = response.data.filter((r: Report) => r.fund === fundId);
      setReports(fundReports);
      setError(null);
    } catch (err) {
      setError("Failed to fetch reports.");
    } finally {
      setLoading(false);
    }
  }, [fundId]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleCreateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newReportName.trim()) return;

    try {
      await fundsApi.createReport({
        name: newReportName,
        fund: fundId,
        config_json: {
          layout: "grid",
          modules: [
            { id: "performance_summary", type: "METRIC_CARD", title: "Performance Summary" },
            { id: "irr_trend", type: "LINE_CHART", metric: "irr", title: "IRR Trend" }
          ]
        }
      });
      setNewReportName("");
      setIsCreating(false);
      fetchReports();
    } catch (err) {
      alert("Failed to create report.");
    }
  };

  const handleToggleStatus = async (report: Report) => {
    const newStatus = report.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
    try {
      await fundsApi.updateReport(report.id, { status: newStatus });
      fetchReports();
    } catch (err) {
      alert("Failed to update report status.");
    }
  };

  const handleDeleteReport = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this report?")) return;
    try {
      await fundsApi.deleteReport(id);
      fetchReports();
    } catch (err) {
      alert("Failed to delete report.");
    }
  };

  const handleRegenerate = async (id: string) => {
    try {
      await fundsApi.regenerateReport(id);
      fetchReports();
    } catch (err) {
      alert("Failed to regenerate report.");
    }
  };

  if (loading) return <div className="loading-state" style={{ textAlign: 'center', padding: '4rem' }}>Loading reports...</div>;

  return (
    <div className="reports-tab">
      <div className="content-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <div>
            <h3 style={{ border: 'none', margin: 0, padding: 0 }}>Dynamic Fund Reports</h3>
            <p className="text-secondary" style={{ marginTop: '0.5rem' }}>Generate and manage interactive static reports for stakeholders.</p>
          </div>
          {isAdmin && (
            <button className="btn-primary" onClick={() => setIsCreating(true)}>
              + Create New Report
            </button>
          )}
        </div>

        {error && <div className="alert-mini error" style={{ marginBottom: '1.5rem' }}>{error}</div>}

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Report Name</th>
                <th>Status</th>
                <th>Created By</th>
                <th>Created At</th>
                <th>Public Link</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.length > 0 ? (
                reports.map((report) => (
                  <tr key={report.id}>
                    <td style={{ fontWeight: 600 }}>{report.name}</td>
                    <td>
                      <span className={`status-badge ${report.status.toLowerCase()}`}>
                        {report.status}
                      </span>
                    </td>
                    <td>{report.created_by_email}</td>
                    <td>{new Date(report.created_at).toLocaleDateString()}</td>
                    <td>
                      {report.status === "ACTIVE" ? (
                        <a 
                          href={`/reports/public/${report.slug}`} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="link-primary"
                        >
                          View Report ↗
                        </a>
                      ) : (
                        <span className="text-secondary">N/A (Inactive)</span>
                      )}
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button 
                          className="btn-icon" 
                          onClick={() => handleToggleStatus(report)}
                          title={report.status === "ACTIVE" ? "Deactivate" : "Activate"}
                        >
                          {report.status === "ACTIVE" ? "🚫" : "✅"}
                        </button>
                        <button 
                          className="btn-icon" 
                          onClick={() => handleRegenerate(report.id)}
                          title="Regenerate"
                        >
                          🔄
                        </button>
                        <button 
                          className="btn-icon delete" 
                          onClick={() => handleDeleteReport(report.id)}
                          title="Delete"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                    No reports generated for this fund yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isCreating && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3 style={{ border: 'none', marginBottom: '1.5rem' }}>Create New Report</h3>
            <form onSubmit={handleCreateReport}>
              <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Report Name</label>
                <input 
                  type="text" 
                  value={newReportName} 
                  onChange={(e) => setNewReportName(e.target.value)}
                  placeholder="e.g. Q4 2025 Investor Update"
                  className="form-input"
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-light)' }}
                  required
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setIsCreating(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Generate Report</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportsTab;
