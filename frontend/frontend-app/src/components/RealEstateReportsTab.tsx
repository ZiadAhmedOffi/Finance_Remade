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

const DEFAULT_DYNAMIC_SECTIONS = [
  { id: "overview", title: "Portfolio Overview" },
  { id: "allocation", title: "Strategic Allocation" },
  { id: "growth", title: "Capital Appreciation" },
  { id: "financing", title: "Debt & Financing" },
  { id: "assets", title: "Asset Performance" },
  { id: "cash_flow", title: "Cash Flow Analysis" },
  { id: "portfolio_strategy", title: "Portfolio Strategy" },
  { id: "why_invest", title: "Why Invest With Us?" }
];

const DEFAULT_ANNUAL_SECTIONS = [
  { id: "annual_summary", title: "Annual Performance Summary" },
  { id: "market_review", title: "Market Review & Outlook" },
  { id: "portfolio_strategy", title: "Portfolio Strategy" },
  { id: "asset_highlights", title: "Key Asset Highlights" },
  { id: "financial_statements", title: "Summarized Financial Statements" },
  { id: "risk_measures", title: "Risk Profile & Measures" },
  { id: "why_invest", title: "Why Invest With Us?" }
];

const RealEstateReportsTab: React.FC<RealEstateReportsTabProps> = ({ portfolioId, isAdmin }) => {
  const [dynamicReports, setDynamicReports] = useState<Report[]>([]);
  // const [annualReports, setAnnualReports] = useState<Report[]>([]);
  // const [portfolio, setPortfolio] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [viewMode, setViewMode] = useState<"LISTING" | "PLANNING">("LISTING");
  const [reportConfig, setReportConfig] = useState<any>({
    dynamic: { sections: DEFAULT_DYNAMIC_SECTIONS.map(s => ({ ...s, enabled: true, type: 'DEFAULT' })) },
    annual: { sections: DEFAULT_ANNUAL_SECTIONS.map(s => ({ ...s, enabled: true, type: 'DEFAULT' })) }
  });

  const [isCreatingDynamic, setIsCreatingDynamic] = useState(false);
  const [isCreatingAnnual, setIsCreatingAnnual] = useState(false);
  
  const [newReportName, setNewReportName] = useState("");

  const [isDynamicOpen, setIsDynamicOpen] = useState(true);
  // const [isAnnualOpen, setIsAnnualOpen] = useState(false);
  const [dynamicPage, setDynamicPage] = useState(1);
  // const [annualPage, setAnnualPage] = useState(1);
  const reportsPerPage = 10;

  const [editingReportId, setEditingReportId] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<any>({});

  // Textual Info State (Hidded/WIP)
  /*
  const [overview, setOverview] = useState("");
  const [strategy, setStrategy] = useState("");
  const [structure, setStructure] = useState("");
  const [portfolioLifecycle, setPortfolioLifecycle] = useState("");
  const [reasonsToInvest, setReasonsToInvest] = useState<{ title: string; brief_desc: string }[]>([]);
  const [isSavingTextual, setIsSavingTextual] = useState(false);
  */

  const [isAddingCustom, setIsAddingCustom] = useState<"DYNAMIC" | "ANNUAL" | null>(null);
  const [customTitle, setCustomTitle] = useState("");
  const [customText, setCustomText] = useState("");

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [reportsRes, portfolioRes] = await Promise.all([
        realEstateApi.getReports(portfolioId),
        realEstateApi.getPortfolio(portfolioId)
      ]);
      
      const allReports = reportsRes.data;
      setDynamicReports(allReports.filter((r: Report) => r.report_type === "DYNAMIC"));
      // setAnnualReports(allReports.filter((r: Report) => r.report_type === "ANNUAL"));
      // setPortfolio(portfolioRes.data);
      
      // Set Textual Info (Hidded/WIP)
      /*
      setOverview(portfolioRes.data.overview || "");
      setStrategy(portfolioRes.data.strategy || "");
      setStructure(portfolioRes.data.structure || "");
      setPortfolioLifecycle(portfolioRes.data.portfolio_lifecycle || "");
      setReasonsToInvest(portfolioRes.data.reasons_to_invest || []);
      */

      if (portfolioRes.data.report_config && Object.keys(portfolioRes.data.report_config).length > 0) {
        let config = JSON.parse(JSON.stringify(portfolioRes.data.report_config));
        
        const ensureSections = (type: 'dynamic' | 'annual', defaults: any[]) => {
          if (!config[type]) {
            config[type] = { sections: defaults.map(s => ({ ...s, enabled: true, type: 'DEFAULT' })) };
            return;
          }

          if (config[type].sections) {
            const existingIds = config[type].sections.map((s: any) => s.id);
            const missingDefaults = defaults.filter(d => !existingIds.includes(d.id));
            if (missingDefaults.length > 0) {
              config[type].sections = [
                ...config[type].sections,
                ...missingDefaults.map(s => ({ ...s, enabled: true, type: 'DEFAULT' }))
              ];
            }
          } else {
             config[type].sections = defaults.map(s => ({ ...s, enabled: true, type: 'DEFAULT' }));
          }
        };

        ensureSections('dynamic', DEFAULT_DYNAMIC_SECTIONS);
        ensureSections('annual', DEFAULT_ANNUAL_SECTIONS);
        
        setReportConfig(config);
      }
      setError(null);
    } catch (err) {
      setError("Failed to fetch reports.");
    } finally {
      setLoading(false);
    }
  }, [portfolioId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const [draggedItem, setDraggedItem] = useState<{ type: 'dynamic' | 'annual', index: number } | null>(null);

  const handleSavePlanning = async () => {
    try {
      await realEstateApi.updatePortfolio(portfolioId, { report_config: reportConfig });
      alert("Report structure updated successfully!");
      setViewMode("LISTING");
    } catch (err) {
      alert("Failed to save report planning.");
    }
  };

  const moveSection = (type: 'dynamic' | 'annual', index: number, direction: 'UP' | 'DOWN') => {
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

  const reorderSection = (type: 'dynamic' | 'annual', oldIndex: number, newIndex: number) => {
    if (oldIndex === newIndex) return;
    const newConfig = { ...reportConfig };
    const sections = [...newConfig[type].sections];
    const [movedItem] = sections.splice(oldIndex, 1);
    sections.splice(newIndex, 0, movedItem);
    newConfig[type].sections = sections;
    setReportConfig(newConfig);
  };

  const toggleSection = (type: 'dynamic' | 'annual', sectionId: string) => {
    const newConfig = { ...reportConfig };
    newConfig[type].sections = newConfig[type].sections.map((s: any) => 
      s.id === sectionId ? { ...s, enabled: !s.enabled } : s
    );
    setReportConfig(newConfig);
  };

  const handleAddCustomSection = (_e: React.FormEvent) => {
    _e.preventDefault();
    if (!customTitle || !customText || !isAddingCustom) return;

    const type = isAddingCustom === "DYNAMIC" ? "dynamic" : "annual";
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

  const handleRemoveCustomSection = (type: 'dynamic' | 'annual', sectionId: string) => {
    const newConfig = { ...reportConfig };
    newConfig[type].sections = newConfig[type].sections.filter((s: any) => s.id !== sectionId);
    setReportConfig(newConfig);
  };

  const handleCreateReport = async (type: "DYNAMIC" | "ANNUAL") => {
    if (!newReportName.trim()) return;

    try {
      const slug = `${newReportName.toLowerCase().replace(/ /g, "-")}-${Math.floor(Math.random() * 10000)}`;
      await realEstateApi.createReport({
        name: newReportName,
        slug,
        portfolio: portfolioId,
        report_type: type,
        config_json: {
          report_config: type === "DYNAMIC" ? reportConfig.dynamic : reportConfig.annual,
          layout: "grid"
        },
        status: "ACTIVE"
      });
      setNewReportName("");
      setIsCreatingDynamic(false);
      setIsCreatingAnnual(false);
      fetchData();
    } catch (err: any) {
      alert("Failed to create report: " + (err.response?.data?.error || err.message));
    }
  };

  const handleToggleStatus = async (report: Report) => {
    const newStatus = report.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
    try {
      await realEstateApi.updateReport(report.id, { status: newStatus });
      fetchData();
    } catch (err) {
      alert("Failed to update report status.");
    }
  };

  const handleDeleteReport = async (report: Report) => {
    if (!window.confirm("Are you sure you want to delete this report?")) return;
    try {
      await realEstateApi.deleteReport(report.id);
      fetchData();
    } catch (err) {
      alert("Failed to delete report.");
    }
  };

  const handleRegenerate = async (id: string) => {
    try {
      await realEstateApi.regenerateReport(id);
      fetchData();
    } catch (err) {
      alert("Failed to regenerate report.");
    }
  };

  const startEditing = (report: Report) => {
    setEditingReportId(report.id);
    setEditValues({
      name: report.name
    });
  };

  const handleSaveEdit = async (report: Report) => {
    try {
      await realEstateApi.updateReport(report.id, { name: editValues.name });
      setEditingReportId(null);
      fetchData();
    } catch (err) {
      alert("Failed to update report.");
    }
  };

  /*
  const handleUpdateTextualInfo = async () => {
    try {
      setIsSavingTextual(true);
      await realEstateApi.updatePortfolio(portfolioId, {
        overview,
        strategy,
        structure,
        portfolio_lifecycle: portfolioLifecycle,
        reasons_to_invest: reasonsToInvest
      });
      alert("Portfolio textual information updated successfully!");
    } catch (err) {
      alert("Failed to update textual information.");
    } finally {
      setIsSavingTextual(false);
    }
  };
  */

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
                          <div className="slug-hint" style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                            /real-estate/reports/public/{report.slug}
                          </div>
                        </td>
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
                              href={`/real-estate/reports/public/${report.slug}`} 
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
                      <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
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

  /*
  const renderTextualInfo = () => {
    return (
      <div className="content-card textual-info-section" style={{ marginTop: '2.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <div>
            <h3 style={{ border: 'none', margin: 0, padding: 0 }}>Portfolio Textual Information</h3>
            <p className="text-secondary" style={{ marginTop: '0.5rem' }}>Define descriptive content to be displayed in the generated reports.</p>
          </div>
          {isAdmin && (
            <button 
              className="btn-primary" 
              onClick={handleUpdateTextualInfo}
              disabled={isSavingTextual}
            >
              {isSavingTextual ? "Saving..." : "Update Information"}
            </button>
          )}
        </div>

        <div className="info-grid-edit" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
          <div className="form-group" style={{ gridColumn: 'span 2' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 700, color: '#475569' }}>Overview (In-depth)</label>
            <textarea 
              value={overview} 
              onChange={(e) => setOverview(e.target.value)} 
              rows={5}
              placeholder="Detailed portfolio overview for reports..."
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}
              readOnly={!isAdmin}
            />
          </div>

          <div className="form-group">
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 700, color: '#475569' }}>Strategy</label>
            <textarea 
              value={strategy} 
              onChange={(e) => setStrategy(e.target.value)} 
              rows={4}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}
              readOnly={!isAdmin}
            />
          </div>

          <div className="form-group">
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 700, color: '#475569' }}>Structure</label>
            <textarea 
              value={structure} 
              onChange={(e) => setStructure(e.target.value)} 
              rows={4}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}
              readOnly={!isAdmin}
            />
          </div>

          <div className="form-group" style={{ gridColumn: 'span 2' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 700, color: '#475569' }}>Portfolio Lifecycle</label>
            <textarea 
              value={portfolioLifecycle} 
              onChange={(e) => setPortfolioLifecycle(e.target.value)} 
              rows={5}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}
              readOnly={!isAdmin}
            />
          </div>
        </div>

        <div className="reasons-section" style={{ marginTop: '3rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h4 style={{ margin: 0, fontWeight: 700 }}>Reasons to Invest</h4>
            {isAdmin && (
              <button 
                type="button" 
                className="btn-secondary btn-sm"
                onClick={() => setReasonsToInvest([...reasonsToInvest, { title: "", brief_desc: "" }])}
              >
                + Add Reason
              </button>
            )}
          </div>
          
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '30%' }}>Title</th>
                  <th>Brief Description</th>
                  {isAdmin && <th style={{ width: '80px' }}>Action</th>}
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
                        style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}
                        readOnly={!isAdmin}
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
                        placeholder="Brief Description"
                        rows={2}
                        style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #e2e8f0', marginTop: '4px' }}
                        readOnly={!isAdmin}
                      />
                    </td>
                    {isAdmin && (
                      <td>
                        <button 
                          className="btn-icon delete" 
                          onClick={() => setReasonsToInvest(reasonsToInvest.filter((_, i) => i !== idx))}
                        >
                          🗑️
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
                {reasonsToInvest.length === 0 && (
                  <tr>
                    <td colSpan={isAdmin ? 3 : 2} style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                      No investment reasons added.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };
  */

  const renderPlanningMode = () => {
    const renderSectionList = (type: 'dynamic' | 'annual', title: string) => {
      const sections = reportConfig[type].sections || [];

      return (
        <div className="content-card" style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h4 style={{ margin: 0 }}>{title} Structure</h4>
            <button className="btn btn-secondary btn-sm" onClick={() => setIsAddingCustom(type === 'dynamic' ? "DYNAMIC" : "ANNUAL")}>+ Add Custom Section</button>
          </div>
          
          <div className="planning-sections-list" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {sections.map((s: any, idx: number) => (
              <div 
                key={s.id} 
                className="planning-section-item"
                draggable
                onDragStart={() => {
                   setDraggedItem({ type, index: idx });
                }}
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
                  transition: 'all 0.2s ease',
                  transform: draggedItem?.index === idx && draggedItem.type === type ? 'scale(1.02)' : 'none',
                  zIndex: draggedItem?.index === idx && draggedItem.type === type ? 10 : 1
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.1rem' }}>
                    <button 
                      className="btn-icon" 
                      onClick={() => moveSection(type, idx, 'UP')}
                      disabled={idx === 0}
                      style={{ fontSize: '0.7rem', padding: '1px', opacity: idx === 0 ? 0.2 : 0.6 }}
                    >
                      ▲
                    </button>
                    <button 
                      className="btn-icon" 
                      onClick={() => moveSection(type, idx, 'DOWN')}
                      disabled={idx === sections.length - 1}
                      style={{ fontSize: '0.7rem', padding: '1px', opacity: idx === sections.length - 1 ? 0.2 : 0.6 }}
                    >
                      ▼
                    </button>
                </div>

                <input 
                  type="checkbox" 
                  checked={s.enabled}
                  onChange={() => toggleSection(type, s.id)}
                  style={{ width: '20px', height: '20px', cursor: 'pointer' }}
                />

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

                {s.type === 'CUSTOM' && (
                  <button 
                    className="btn-icon delete" 
                    onClick={() => handleRemoveCustomSection(type, s.id)}
                  >
                    🗑️
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      );
    };

    return (
      <div className="planning-mode animate-fade-in">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
           <div>
             <h3 style={{ border: 'none', margin: 0 }}>Portfolio Report Structure Planning</h3>
             <p className="text-secondary" style={{ marginTop: '0.5rem' }}>Arrange sections, toggle visibility, and add custom commentary for your real estate reports.</p>
           </div>
           <div style={{ display: 'flex', gap: '1rem' }}>
             <button className="btn-secondary" onClick={() => setViewMode('LISTING')}>Cancel</button>
             <button className="btn-primary" onClick={handleSavePlanning}>Save All Changes</button>
           </div>
        </div>

        <div className="planning-container" style={{ maxWidth: '1000px', margin: '0 auto' }}>
          {renderSectionList('dynamic', 'Dynamic Portfolio Report')}
          {/* Annual reports hidden for now as it's a work-in-progress */}
          {/* {renderSectionList('annual', 'Annual Performance Report')} */}
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
        {isAdmin && (
          <button 
            className={`btn ${viewMode === 'PLANNING' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setViewMode('PLANNING')}
          >
            Planning Mode
          </button>
        )}
      </div>

      {viewMode === "PLANNING" ? (
        renderPlanningMode()
      ) : (
        <>
          {renderReportTable(
            dynamicReports, 
            "Dynamic Portfolio Reports", 
            isDynamicOpen,
            setIsDynamicOpen,
            dynamicPage,
            setDynamicPage,
            () => setIsCreatingDynamic(true),
            "Real-time interactive reports showing current portfolio performance and asset details."
          )}

          {/* Annual reports hidden for now as it's a work-in-progress */}
          {/* {renderReportTable(
            annualReports, 
            "Annual Performance Reports", 
            isAnnualOpen,
            setIsAnnualOpen,
            annualPage,
            setAnnualPage,
            () => setIsCreatingAnnual(true),
            "Comprehensive year-end reports for institutional investors and stakeholders."
          )} */}

          {/* Textual info section hidden for now as it's a work-in-progress */}
          {/* {renderTextualInfo()} */}
        </>
      )}

      {/* Modal for Adding Custom Section */}
      {isAddingCustom && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '600px' }}>
            <h3 style={{ border: 'none', marginBottom: '1.5rem' }}>Add Custom Section to {isAddingCustom === "DYNAMIC" ? "Dynamic" : "Annual"} Report</h3>
            <form onSubmit={handleAddCustomSection}>
              <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Section Title</label>
                <input 
                  type="text" 
                  value={customTitle} 
                  onChange={(e) => setCustomTitle(e.target.value)}
                  placeholder="e.g. Market Outlook or General Commentary"
                  className="form-input"
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}
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
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}
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
      {(isCreatingDynamic || isCreatingAnnual) && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3 style={{ border: 'none', marginBottom: '1.5rem' }}>Create New {isCreatingDynamic ? "Dynamic" : "Annual"} Report</h3>
            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Report Name</label>
              <input 
                type="text" 
                value={newReportName} 
                onChange={(e) => setNewReportName(e.target.value)}
                placeholder={isCreatingDynamic ? "e.g. Q2 2026 Performance Update" : "e.g. 2025 Annual Portfolio Report"}
                className="form-input"
                style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}
                required
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => { setIsCreatingDynamic(false); setIsCreatingAnnual(false); }}>Cancel</button>
              <button 
                className="btn-primary" 
                onClick={() => handleCreateReport(isCreatingDynamic ? "DYNAMIC" : "ANNUAL")}
              >
                Generate Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RealEstateReportsTab;
