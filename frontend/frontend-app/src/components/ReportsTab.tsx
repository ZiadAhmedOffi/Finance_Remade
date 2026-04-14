import React, { useState, useEffect, useCallback } from "react";
import { fundsApi } from "../api/api";
import "../pages/FundDashboard.css";

interface Report {
  id: string;
  slug: string;
  name: string;
  report_type: "DYNAMIC" | "CAPITAL_CALL";
  fund: string;
  fund_name: string;
  status: "ACTIVE" | "INACTIVE" | "GENERATING" | "FAILED";
  static_url: string;
  config_json: any;
  created_by_email: string;
  created_at: string;
}

interface ReportsTabProps {
  fundId: string;
  isAdmin: boolean;
}

const ReportsTab: React.FC<ReportsTabProps> = ({ fundId, isAdmin }) => {
  const [dynamicReports, setDynamicReports] = useState<Report[]>([]);
  const [capitalCallReports, setCapitalCallReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [isCreatingDynamic, setIsCreatingDynamic] = useState(false);
  const [isCreatingCapitalCall, setIsCreatingCapitalCall] = useState(false);
  
  const [newReportName, setNewReportName] = useState("");
  const [targetCapital, setTargetCapital] = useState("");
  const [capitalRaised, setCapitalRaised] = useState("");

  // Toggles and Pagination
  const [isDynamicOpen, setIsDynamicOpen] = useState(true);
  const [isCapitalCallOpen, setIsCapitalCallOpen] = useState(false);
  const [dynamicPage, setDynamicPage] = useState(1);
  const [capitalCallPage, setCapitalCallPage] = useState(1);
  const reportsPerPage = 10;

  // Editing state
  const [editingReportId, setEditingReportId] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<any>({});

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [dynamicRes, capitalCallRes] = await Promise.all([
        fundsApi.getReports(),
        fundsApi.getCapitalCallReports()
      ]);
      
      setDynamicReports(dynamicRes.data.filter((r: Report) => r.fund === fundId));
      setCapitalCallReports(capitalCallRes.data.filter((r: Report) => r.fund === fundId));
      setError(null);
    } catch (err) {
      setError("Failed to fetch reports.");
    } finally {
      setLoading(false);
    }
  }, [fundId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateDynamicReport = async (e: React.FormEvent) => {
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
      setIsCreatingDynamic(false);
      fetchData();
    } catch (err) {
      alert("Failed to create report.");
    }
  };

  const handleCreateCapitalCallReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newReportName.trim()) return;

    try {
      await fundsApi.createCapitalCallReport({
        name: newReportName,
        fund: fundId,
        config_json: {
          target_capital: parseFloat(targetCapital),
          capital_raised: parseFloat(capitalRaised)
        }
      });
      setNewReportName("");
      setTargetCapital("");
      setCapitalRaised("");
      setIsCreatingCapitalCall(false);
      fetchData();
    } catch (err) {
      alert("Failed to create capital call report.");
    }
  };

  const handleToggleStatus = async (report: Report) => {
    const newStatus = report.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
    try {
      if (report.report_type === "CAPITAL_CALL") {
        await fundsApi.updateCapitalCallReport(report.id, { status: newStatus });
      } else {
        await fundsApi.updateReport(report.id, { status: newStatus });
      }
      fetchData();
    } catch (err) {
      alert("Failed to update report status.");
    }
  };

  const handleDeleteReport = async (report: Report) => {
    if (!window.confirm("Are you sure you want to delete this report?")) return;
    try {
      if (report.report_type === "CAPITAL_CALL") {
        await fundsApi.deleteCapitalCallReport(report.id);
      } else {
        await fundsApi.deleteReport(report.id);
      }
      fetchData();
    } catch (err) {
      alert("Failed to delete report.");
    }
  };

  const handleRegenerate = async (id: string) => {
    try {
      await fundsApi.regenerateReport(id);
      fetchData();
    } catch (err) {
      alert("Failed to regenerate report.");
    }
  };

  const startEditing = (report: Report) => {
    setEditingReportId(report.id);
    setEditValues({
      name: report.name,
      target_capital: report.config_json?.target_capital || "",
      capital_raised: report.config_json?.capital_raised || ""
    });
  };

  const handleSaveEdit = async (report: Report) => {
    try {
      if (report.report_type === "CAPITAL_CALL") {
        await fundsApi.updateCapitalCallReport(report.id, {
          name: editValues.name,
          config_json: {
            ...report.config_json,
            target_capital: parseFloat(editValues.target_capital),
            capital_raised: parseFloat(editValues.capital_raised)
          }
        });
      } else {
        await fundsApi.updateReport(report.id, { name: editValues.name });
      }
      setEditingReportId(null);
      fetchData();
    } catch (err) {
      alert("Failed to update report.");
    }
  };

  const renderReportTable = (
    reports: Report[], 
    title: string, 
    isOpen: boolean, 
    setIsOpen: (v: boolean) => void,
    currentPage: number,
    setCurrentPage: (p: number) => void,
    onCreate: () => void, 
    description: string
  ) => {
    const totalPages = Math.ceil(reports.length / reportsPerPage);
    const paginatedReports = reports.slice((currentPage - 1) * reportsPerPage, currentPage * reportsPerPage);

    return (
      <div className="content-card" style={{ marginBottom: '2.5rem' }}>
        <div 
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
          onClick={() => setIsOpen(!isOpen)}
        >
          <div>
            <h3 style={{ border: 'none', margin: 0, padding: 0 }}>
              {isOpen ? "▼" : "▶"} {title}
            </h3>
            <p className="text-secondary" style={{ marginTop: '0.5rem' }}>{description}</p>
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }} onClick={(e) => e.stopPropagation()}>
            {isAdmin && (
              <button className="btn-primary" onClick={onCreate}>
                + Create New
              </button>
            )}
          </div>
        </div>

        <div className={`collapsible-section ${isOpen ? 'open' : ''}`}>
          <div style={{ marginTop: '2rem' }}>
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Report Name</th>
                    <th>Status</th>
                    <th>Created By</th>
                    <th>Created At</th>
                    {title.includes("Capital Call") && (
                      <>
                        <th>Target</th>
                        <th>Raised</th>
                      </>
                    )}
                    <th>Public Link</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedReports.length > 0 ? (
                    paginatedReports.map((report) => (
                      <tr key={report.id}>
                        <td style={{ fontWeight: 600 }}>
                          {editingReportId === report.id ? (
                            <input 
                              type="text" 
                              className="form-input-sm"
                              value={editValues.name}
                              onChange={(e) => setEditValues({...editValues, name: e.target.value})}
                            />
                          ) : report.name}
                        </td>
                        <td>
                          <span className={`status-badge ${report.status.toLowerCase()}`}>
                            {report.status}
                          </span>
                        </td>
                        <td>{report.created_by_email}</td>
                        <td>{new Date(report.created_at).toLocaleDateString()}</td>
                        {title.includes("Capital Call") && (
                          <>
                            <td>
                              {editingReportId === report.id ? (
                                <input 
                                  type="number" 
                                  className="form-input-sm"
                                  style={{ width: '100px' }}
                                  value={editValues.target_capital}
                                  onChange={(e) => setEditValues({...editValues, target_capital: e.target.value})}
                                />
                              ) : `$${(report.config_json?.target_capital || 0).toLocaleString()}`}
                            </td>
                            <td>
                              {editingReportId === report.id ? (
                                <input 
                                  type="number" 
                                  className="form-input-sm"
                                  style={{ width: '100px' }}
                                  value={editValues.capital_raised}
                                  onChange={(e) => setEditValues({...editValues, capital_raised: e.target.value})}
                                />
                              ) : `$${(report.config_json?.capital_raised || 0).toLocaleString()}`}
                            </td>
                          </>
                        )}
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
                            {editingReportId === report.id ? (
                              <>
                                <button className="btn-icon" onClick={() => handleSaveEdit(report)} title="Save">💾</button>
                                <button className="btn-icon" onClick={() => setEditingReportId(null)} title="Cancel">❌</button>
                              </>
                            ) : (
                              <>
                                <button className="btn-icon" onClick={() => startEditing(report)} title="Edit">✏️</button>
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
                                  onClick={() => handleDeleteReport(report)}
                                  title="Delete"
                                >
                                  🗑️
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={title.includes("Capital Call") ? 8 : 6} style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                        No reports generated yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            
            {totalPages > 1 && (
              <div className="pagination-controls" style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'center', gap: '0.5rem' }}>
                {Array.from({ length: totalPages }, (_, i) => (
                  <button
                    key={i}
                    onClick={() => setCurrentPage(i + 1)}
                    className={`btn ${currentPage === i + 1 ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ minWidth: '2.5rem', padding: '0.25rem' }}
                  >
                    {i + 1}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  if (loading) return <div className="loading-state" style={{ textAlign: 'center', padding: '4rem' }}>Loading reports...</div>;

  return (
    <div className="reports-tab">
      {error && <div className="alert-mini error" style={{ marginBottom: '1.5rem' }}>{error}</div>}

      {renderReportTable(
        dynamicReports, 
        "Dynamic Fund Reports", 
        isDynamicOpen,
        setIsDynamicOpen,
        dynamicPage,
        setDynamicPage,
        () => setIsCreatingDynamic(true),
        "Interactive static reports showing current fund performance and metrics."
      )}

      {renderReportTable(
        capitalCallReports, 
        "Capital Call Reports", 
        isCapitalCallOpen,
        setIsCapitalCallOpen,
        capitalCallPage,
        setCapitalCallPage,
        () => setIsCreatingCapitalCall(true),
        "Premium, shareable landing pages for fund capital calls and investor cases."
      )}

      {/* Modal for Dynamic Report */}
      {isCreatingDynamic && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3 style={{ border: 'none', marginBottom: '1.5rem' }}>Create New Dynamic Report</h3>
            <form onSubmit={handleCreateDynamicReport}>
              <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Report Name</label>
                <input 
                  type="text" 
                  value={newReportName} 
                  onChange={(e) => setNewReportName(e.target.value)}
                  placeholder="e.g. Q4 2025 Performance Update"
                  className="form-input"
                  required
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setIsCreatingDynamic(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Generate Report</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal for Capital Call Report */}
      {isCreatingCapitalCall && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3 style={{ border: 'none', marginBottom: '1.5rem' }}>Generate Capital Call Report</h3>
            <form onSubmit={handleCreateCapitalCallReport}>
              <div className="form-group" style={{ marginBottom: '1.2rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Report Name</label>
                <input 
                  type="text" 
                  value={newReportName} 
                  onChange={(e) => setNewReportName(e.target.value)}
                  placeholder="e.g. Series A Capital Call - Growth Fund"
                  className="form-input"
                  required
                />
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                <div className="form-group">
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Target Capital (USD)</label>
                  <input 
                    type="number" 
                    value={targetCapital} 
                    onChange={(e) => setTargetCapital(e.target.value)}
                    placeholder="e.g. 50000000"
                    className="form-input"
                    required
                  />
                </div>
                <div className="form-group">
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Capital Raised (USD)</label>
                  <input 
                    type="number" 
                    value={capitalRaised} 
                    onChange={(e) => setCapitalRaised(e.target.value)}
                    placeholder="e.g. 20000000"
                    className="form-input"
                    required
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setIsCreatingCapitalCall(false)}>Cancel</button>
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
