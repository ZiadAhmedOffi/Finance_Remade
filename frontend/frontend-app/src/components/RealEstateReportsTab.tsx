import React, { useState, useEffect, useCallback } from "react";
import { realEstateApi } from "../api/api";
import "../pages/FundDashboard.css";

interface Report {
  id: string;
  slug: string;
  name: string;
  report_type: "DYNAMIC" | "ANNUAL";
  portfolio: string;
  portfolio_name: string;
  status: "ACTIVE" | "INACTIVE" | "GENERATING" | "FAILED";
  static_url: string;
  config_json: any;
  created_by_email: string;
  created_at: string;
}

interface RealEstateReportsTabProps {
  portfolioId: string;
  isAdmin: boolean;
}

const DEFAULT_RE_SECTIONS = [
  { id: "overview", title: "Portfolio Overview", enabled: true },
  { id: "allocation", title: "Strategic Allocation", enabled: true },
  { id: "growth", title: "Capital Appreciation", enabled: true },
  { id: "financing", title: "Debt & Financing", enabled: true },
  { id: "assets", title: "Asset Performance", enabled: true },
];

const RealEstateReportsTab: React.FC<RealEstateReportsTabProps> = ({ portfolioId, isAdmin }) => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [isCreating, setIsCreating] = useState(false);
  const [newReportName, setNewReportName] = useState("");
  const [reportConfig, setReportConfig] = useState<any>({
    sections: DEFAULT_RE_SECTIONS
  });

  const fetchReports = useCallback(async () => {
    try {
      setLoading(true);
      const response = await realEstateApi.getReports(portfolioId);
      setReports(response.data);
    } catch (err: any) {
      setError("Failed to fetch reports.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [portfolioId]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleCreateReport = async () => {
    if (!newReportName) return;
    try {
      const slug = `${newReportName.toLowerCase().replace(/ /g, "-")}-${Math.floor(Math.random() * 10000)}`;
      await realEstateApi.createReport({
        name: newReportName,
        slug,
        portfolio: portfolioId,
        config_json: { report_config: reportConfig },
        status: "ACTIVE" // Auto-active for now
      });
      setNewReportName("");
      setIsCreating(false);
      fetchReports();
    } catch (err: any) {
        alert("Error creating report: " + (err.response?.data?.error || err.message));
    }
  };

  const handleDeleteReport = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this report?")) return;
    try {
      await realEstateApi.deleteReport(id);
      fetchReports();
    } catch (err) {
      alert("Error deleting report.");
    }
  };

  const handleToggleSection = (sectionId: string) => {
    setReportConfig((prev: any) => ({
      ...prev,
      sections: prev.sections.map((s: any) => 
        s.id === sectionId ? { ...s, enabled: !s.enabled } : s
      )
    }));
  };

  if (loading) return <div className="loading-spinner">Loading reports...</div>;

  return (
    <div className="reports-tab">
      <div className="tab-header">
        <h2>Portfolio Performance Reports</h2>
        {isAdmin && (
          <button className="btn-primary" onClick={() => setIsCreating(true)}>
            + Create New Report
          </button>
        )}
      </div>

      {isCreating && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Configure Institutional Report</h3>
            <div className="form-group">
              <label>Report Name</label>
              <input 
                type="text" 
                value={newReportName} 
                onChange={(e) => setNewReportName(e.target.value)} 
                placeholder="e.g. Q2 2026 Institutional Update"
              />
            </div>

            <div className="config-sections">
              <h4>Enabled Sections</h4>
              {reportConfig.sections.map((section: any) => (
                <div key={section.id} className="section-toggle">
                  <input 
                    type="checkbox" 
                    checked={section.enabled} 
                    onChange={() => handleToggleSection(section.id)}
                  />
                  <span>{section.title}</span>
                </div>
              ))}
            </div>

            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setIsCreating(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleCreateReport}>Generate Report</button>
            </div>
          </div>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      <div className="reports-grid">
        {reports.length === 0 ? (
          <div className="empty-state">No reports generated for this portfolio yet.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Report Name</th>
                <th>Status</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.id}>
                  <td>
                    <strong>{report.name}</strong>
                    <div className="slug-hint">/reports/public/{report.slug}</div>
                  </td>
                  <td>
                    <span className={`status-badge ${report.status.toLowerCase()}`}>
                      {report.status}
                    </span>
                  </td>
                  <td>{new Date(report.created_at).toLocaleDateString()}</td>
                  <td className="actions-cell">
                    <button 
                      className="btn-view"
                      onClick={() => window.open(`/real-estate/reports/public/${report.slug}`, "_blank")}
                    >
                      View Public Link
                    </button>
                    {isAdmin && (
                      <button 
                        className="btn-delete"
                        onClick={() => handleDeleteReport(report.id)}
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default RealEstateReportsTab;
