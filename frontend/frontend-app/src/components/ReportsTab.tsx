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

const DEFAULT_DYNAMIC_SECTIONS = [
  { id: "perf_overview", title: "Performance Overview" },
  { id: "portfolio_comp", title: "Portfolio Composition" },
  { id: "value_appreciation", title: "Value Appreciation" },
  { id: "risk_assessment", title: "Risk Assessment" },
  { id: "deal_prognosis", title: "Deal Prognosis" }
];

const DEFAULT_CAPITAL_CALL_SECTIONS = [
  { id: "cc_overview", title: "Capital Call Overview" },
  { id: "investment_case", title: "Investment Case" },
  { id: "why_invest", title: "Why Invest" },
  { id: "liquidity_analysis", title: "Liquidity Analysis" }
];

const ReportsTab: React.FC<ReportsTabProps> = ({ fundId, isAdmin }) => {
  const [dynamicReports, setDynamicReports] = useState<Report[]>([]);
  const [capitalCallReports, setCapitalCallReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [viewMode, setViewMode] = useState<"LISTING" | "PLANNING">("LISTING");
  const [reportConfig, setReportConfig] = useState<any>({
    dynamic: { sections: DEFAULT_DYNAMIC_SECTIONS.map(s => ({ ...s, enabled: true, type: 'DEFAULT' })) },
    capital_call: { sections: DEFAULT_CAPITAL_CALL_SECTIONS.map(s => ({ ...s, enabled: true, type: 'DEFAULT' })) }
  });

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

  const [isAddingCustom, setIsAddingCustom] = useState<"DYNAMIC" | "CAPITAL_CALL" | null>(null);
  const [customTitle, setCustomTitle] = useState("");
  const [customText, setCustomText] = useState("");

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [dynamicRes, capitalCallRes, fundRes] = await Promise.all([
        fundsApi.getReports(),
        fundsApi.getCapitalCallReports(),
        fundsApi.getFund(fundId)
      ]);
      
      setDynamicReports(dynamicRes.data.filter((r: Report) => r.fund === fundId));
      setCapitalCallReports(capitalCallRes.data.filter((r: Report) => r.fund === fundId));
      
      if (fundRes.data.report_config && Object.keys(fundRes.data.report_config).length > 0) {
        let config = fundRes.data.report_config;
        
        // Migration logic for old format
        const migrate = (type: 'dynamic' | 'capital_call', defaults: any[]) => {
          if (config[type] && (config[type].enabled_sections || config[type].custom_sections)) {
            const enabled = config[type].enabled_sections || [];
            const custom = config[type].custom_sections || [];
            config[type].sections = [
              ...defaults.map(s => ({ ...s, enabled: enabled.includes(s.id), type: 'DEFAULT' })),
              ...custom.map((s: any) => ({ ...s, enabled: true, type: 'CUSTOM' }))
            ];
            delete config[type].enabled_sections;
            delete config[type].custom_sections;
          }
        };

        migrate('dynamic', DEFAULT_DYNAMIC_SECTIONS);
        migrate('capital_call', DEFAULT_CAPITAL_CALL_SECTIONS);
        
        setReportConfig(config);
      }
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

  const [draggedItem, setDraggedItem] = useState<{ type: 'dynamic' | 'capital_call', index: number } | null>(null);

  const handleSavePlanning = async () => {
    try {
      await fundsApi.updateFund(fundId, { report_config: reportConfig });
      alert("Report structure updated successfully!");
      setViewMode("LISTING");
    } catch (err) {
      alert("Failed to save report planning.");
    }
  };

  const moveSection = (type: 'dynamic' | 'capital_call', index: number, direction: 'UP' | 'DOWN') => {
    const newConfig = { ...reportConfig };
    const sections = [...newConfig[type].sections];
    const newIndex = direction === 'UP' ? index - 1 : index + 1;
    
    if (newIndex >= 0 && newIndex < sections.length) {
      const temp = sections[index];
      sections[index] = sections[newIndex];
      sections[newIndex] = temp;
      newConfig[type].sections = sections;
      setReportConfig(newConfig);
    }
  };

  const reorderSection = (type: 'dynamic' | 'capital_call', oldIndex: number, newIndex: number) => {
    if (oldIndex === newIndex) return;
    const newConfig = { ...reportConfig };
    const sections = [...newConfig[type].sections];
    const [movedItem] = sections.splice(oldIndex, 1);
    sections.splice(newIndex, 0, movedItem);
    newConfig[type].sections = sections;
    setReportConfig(newConfig);
  };

  const toggleSection = (type: 'dynamic' | 'capital_call', sectionId: string) => {
    const newConfig = { ...reportConfig };
    newConfig[type].sections = newConfig[type].sections.map((s: any) => 
      s.id === sectionId ? { ...s, enabled: !s.enabled } : s
    );
    setReportConfig(newConfig);
  };

  const handleAddCustomSection = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customTitle || !customText || !isAddingCustom) return;

    const type = isAddingCustom === "DYNAMIC" ? "dynamic" : "capital_call";
    const newConfig = { ...reportConfig };
    newConfig[type].sections = [
      ...(newConfig[type].sections || []),
      { id: `custom_${Date.now()}`, title: customTitle, text: customText, enabled: true, type: 'CUSTOM' }
    ];
    setReportConfig(newConfig);
    setCustomTitle("");
    setCustomText("");
    setIsAddingCustom(null);
  };

  const handleRemoveCustomSection = (type: 'dynamic' | 'capital_call', sectionId: string) => {
    const newConfig = { ...reportConfig };
    newConfig[type].sections = newConfig[type].sections.filter((s: any) => s.id !== sectionId);
    setReportConfig(newConfig);
  };

  const handleCreateDynamicReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newReportName.trim()) return;

    try {
      await fundsApi.createReport({
        name: newReportName,
        fund: fundId,
        config_json: {
          layout: "grid",
          report_config: reportConfig.dynamic, // Store snapshot of current planning
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
          capital_raised: parseFloat(capitalRaised),
          report_config: reportConfig.capital_call // Store snapshot
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

  const renderPlanningMode = () => {
    const renderSectionList = (type: 'dynamic' | 'capital_call', title: string) => {
      const sections = reportConfig[type].sections || [];

      // Touch Reordering State
      const handleTouchStart = (idx: number) => {
        setDraggedItem({ type, index: idx });
      };

      const handleTouchMove = (e: React.TouchEvent, idx: number) => {
        if (!draggedItem || draggedItem.type !== type) return;
        
        // Find the element under the finger
        const touch = e.touches[0];
        const element = document.elementFromPoint(touch.clientX, touch.clientY);
        const container = element?.closest('.planning-section-item');
        
        if (container) {
          const overIdx = parseInt(container.getAttribute('data-index') || '-1');
          if (overIdx !== -1 && overIdx !== draggedItem.index) {
            reorderSection(type, draggedItem.index, overIdx);
            setDraggedItem({ type, index: overIdx });
          }
        }
      };

      const handleTouchEnd = () => {
        setDraggedItem(null);
      };

      return (
        <div className="content-card" style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h4 style={{ margin: 0 }}>{title} Structure</h4>
            <button className="btn btn-secondary btn-sm" onClick={() => setIsAddingCustom(type === 'dynamic' ? "DYNAMIC" : "CAPITAL_CALL")}>+ Add Custom Section</button>
          </div>
          
          <div className="planning-sections-list" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {sections.map((s: any, idx: number) => (
              <div 
                key={s.id} 
                className="planning-section-item"
                data-index={idx}
                draggable
                onDragStart={() => setDraggedItem({ type, index: idx })}
                onDragOver={(e) => {
                  e.preventDefault();
                  if (draggedItem && draggedItem.type === type && draggedItem.index !== idx) {
                    reorderSection(type, draggedItem.index, idx);
                    setDraggedItem({ type, index: idx });
                  }
                }}
                onDragEnd={() => setDraggedItem(null)}
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '1rem', 
                  padding: '1rem', 
                  background: s.enabled ? '#fff' : '#f8fafc', 
                  borderRadius: '12px', 
                  border: '1px solid #e2e8f0',
                  boxShadow: s.enabled ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                  opacity: s.enabled ? 1 : 0.7,
                  cursor: 'grab',
                  transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                  transform: draggedItem?.index === idx && draggedItem.type === type ? 'scale(1.02)' : 'none',
                  zIndex: draggedItem?.index === idx && draggedItem.type === type ? 10 : 1
                }}
              >
                {/* Drag Handle & Reorder Controls */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <div 
                    className="drag-handle"
                    onTouchStart={() => handleTouchStart(idx)}
                    onTouchMove={(e) => handleTouchMove(e, idx)}
                    onTouchEnd={handleTouchEnd}
                    style={{ 
                      fontSize: '1.2rem', 
                      color: '#94a3b8', 
                      cursor: 'grab',
                      padding: '0.5rem 0.25rem',
                      userSelect: 'none',
                      touchAction: 'none' // Important for touch move
                    }}
                  >
                    ⠿
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.1rem' }}>
                    <button 
                      className="btn-icon" 
                      onClick={() => moveSection(type, idx, 'UP')}
                      disabled={idx === 0}
                      style={{ fontSize: '0.7rem', padding: '1px', opacity: idx === 0 ? 0.2 : 0.6 }}
                      title="Move Up"
                    >
                      ▲
                    </button>
                    <button 
                      className="btn-icon" 
                      onClick={() => moveSection(type, idx, 'DOWN')}
                      disabled={idx === sections.length - 1}
                      style={{ fontSize: '0.7rem', padding: '1px', opacity: idx === sections.length - 1 ? 0.2 : 0.6 }}
                      title="Move Down"
                    >
                      ▼
                    </button>
                  </div>
                </div>

                {/* Enabled Toggle */}
                <input 
                  type="checkbox" 
                  checked={s.enabled}
                  onChange={() => toggleSection(type, s.id)}
                  style={{ width: '20px', height: '20px', cursor: 'pointer' }}
                />

                {/* Content Info */}
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '1rem' }}>{s.title}</span>
                    <span style={{ 
                      fontSize: '0.65rem', 
                      padding: '2px 6px', 
                      borderRadius: '4px', 
                      background: s.type === 'DEFAULT' ? '#eff6ff' : '#fdf2f8',
                      color: s.type === 'DEFAULT' ? '#2563eb' : '#db2777',
                      fontWeight: 700,
                      textTransform: 'uppercase'
                    }}>
                      {s.type}
                    </span>
                  </div>
                  {s.type === 'CUSTOM' && (
                    <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.25rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '500px' }}>
                      {s.text}
                    </div>
                  )}
                </div>

                {/* Actions */}
                {s.type === 'CUSTOM' && (
                  <button 
                    className="btn-icon delete" 
                    onClick={() => handleRemoveCustomSection(type, s.id)}
                    title="Remove custom section"
                  >
                    🗑️
                  </button>
                )}
              </div>
            ))}
            {sections.length === 0 && (
              <p style={{ textAlign: 'center', color: '#94a3b8', padding: '2rem', border: '2px dashed #e2e8f0', borderRadius: '12px' }}>No sections defined.</p>
            )}
          </div>
        </div>
      );
    };

    return (
      <div className="planning-mode animate-fade-in">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
           <div>
             <h3 style={{ border: 'none', margin: 0 }}>Report Structure Planning</h3>
             <p className="text-secondary" style={{ marginTop: '0.5rem' }}>Arrange sections, toggle visibility, and add custom commentary for future reports.</p>
           </div>
           <div style={{ display: 'flex', gap: '1rem' }}>
             <button className="btn-secondary" onClick={() => setViewMode('LISTING')}>Cancel</button>
             <button className="btn-primary" onClick={handleSavePlanning}>Save All Changes</button>
           </div>
        </div>

        <div className="planning-container" style={{ maxWidth: '1000px', margin: '0 auto' }}>
          {renderSectionList('dynamic', 'Dynamic Fund Report')}
          {renderSectionList('capital_call', 'Capital Call Report')}
        </div>
      </div>
    );
  };

  if (loading) return <div className="loading-state" style={{ textAlign: 'center', padding: '4rem' }}>Loading reports...</div>;

  return (
    <div className="reports-tab">
      {error && <div className="alert-mini error" style={{ marginBottom: '1.5rem' }}>{error}</div>}

      <div className="tab-mode-toggle" style={{ marginBottom: '2rem', display: 'flex', gap: '1rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '1rem' }}>
        <button 
          className={`btn ${viewMode === 'LISTING' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setViewMode('LISTING')}
        >
          Listing Mode
        </button>
        <button 
          className={`btn ${viewMode === 'PLANNING' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setViewMode('PLANNING')}
        >
          Planning Mode
        </button>
      </div>

      {viewMode === "PLANNING" ? (
        renderPlanningMode()
      ) : (
        <>
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
        </>
      )}

      {/* Modal for Adding Custom Section */}
      {isAddingCustom && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '600px' }}>
            <h3 style={{ border: 'none', marginBottom: '1.5rem' }}>Add Custom Section to {isAddingCustom === "DYNAMIC" ? "Dynamic" : "Capital Call"} Report</h3>
            <form onSubmit={handleAddCustomSection}>
              <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Section Title</label>
                <input 
                  type="text" 
                  value={customTitle} 
                  onChange={(e) => setCustomTitle(e.target.value)}
                  placeholder="e.g. Market Outlook or General Commentary"
                  className="form-input"
                  required
                />
              </div>
              <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Content (Max 5000 characters)</label>
                <textarea 
                  value={customText} 
                  onChange={(e) => setCustomText(e.target.value)}
                  placeholder="Enter the justified text content here..."
                  className="form-input"
                  rows={8}
                  maxLength={5000}
                  required
                />
                <p className="text-secondary" style={{ fontSize: '0.75rem', marginTop: '0.5rem' }}>{customText.length}/5000 characters used.</p>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setIsAddingCustom(null)}>Cancel</button>
                <button type="submit" className="btn-primary">Add Section</button>
              </div>
            </form>
          </div>
        </div>
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
