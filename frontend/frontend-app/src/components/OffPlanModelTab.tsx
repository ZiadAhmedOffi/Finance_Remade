import React, { useState, useEffect } from "react";
import { realEstateApi } from "../api/api";
import { formatCurrency } from "../utils/formatters";

interface OffPlanProperty {
  property_id: string;
  property_name: string;
  purchase_price: string;
  construction_start: string;
  expected_completion: string;
  appreciation_rate: string;
  sale_at_completion: boolean;
  value_at_completion: number;
  details_id: string;
}

interface Milestone {
  id: string;
  milestone: string;
  date: string;
  percentage: string;
  cash_flow: number;
  cumulative_deployed: number;
}

interface ScheduleData {
  schedule: Milestone[];
  metrics: {
    xirr: number;
    total_expected_profit: number;
  };
}

const OffPlanModelTab: React.FC<{ portfolioId: string; canEdit: boolean }> = ({ portfolioId, canEdit }) => {
  const [properties, setProperties] = useState<OffPlanProperty[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>("");
  const [scheduleData, setScheduleData] = useState<ScheduleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [scheduleLoading, setScheduleLoading] = useState(false);

  // Local state for inputs to avoid immediate refreshes
  const [localPropertyInputs, setLocalPropertyInputs] = useState<Record<string, Partial<OffPlanProperty>>>({});
  const [localMilestoneInputs, setLocalMilestoneInputs] = useState<Record<string, { milestone?: string; date?: string; percentage?: string }>>({});

  // Visibility toggles
  const [showPropertiesTable, setShowPropertiesTable] = useState(true);
  const [showScheduleTable, setShowScheduleTable] = useState(true);

  useEffect(() => {
    fetchProperties();
  }, [portfolioId]);

  useEffect(() => {
    if (selectedPropertyId) {
      fetchSchedule();
    } else {
      setScheduleData(null);
    }
  }, [selectedPropertyId]);

  const fetchProperties = async () => {
    try {
      setLoading(true);
      const response = await realEstateApi.getOffPlanModel(portfolioId);
      setProperties(response.data);
      
      const initialInputs: Record<string, Partial<OffPlanProperty>> = {};
      response.data.forEach((p: OffPlanProperty) => {
        initialInputs[p.property_id] = {
          construction_start: p.construction_start,
          expected_completion: p.expected_completion,
          appreciation_rate: p.appreciation_rate,
          sale_at_completion: p.sale_at_completion
        };
      });
      setLocalPropertyInputs(initialInputs);

      if (response.data.length > 0 && !selectedPropertyId) {
        setSelectedPropertyId(response.data[0].property_id);
      }
    } catch (err) {
      console.error("Failed to fetch off-plan properties", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSchedule = async () => {
    try {
      setScheduleLoading(true);
      const response = await realEstateApi.getOffPlanSchedule(portfolioId, selectedPropertyId);
      setScheduleData(response.data);

      const initialMilestones: Record<string, any> = {};
      response.data.schedule.forEach((m: Milestone) => {
        initialMilestones[m.id] = {
          milestone: m.milestone,
          date: m.date,
          percentage: m.percentage
        };
      });
      setLocalMilestoneInputs(initialMilestones);
    } catch (err) {
      console.error("Failed to fetch schedule", err);
    } finally {
      setScheduleLoading(false);
    }
  };

  const handlePropertyDetailChange = (propertyId: string, field: string, value: any) => {
    setLocalPropertyInputs(prev => ({
      ...prev,
      [propertyId]: { ...prev[propertyId], [field]: value }
    }));
  };

  const handlePropertyDetailBlur = async (propertyId: string, field: string, value: any) => {
    try {
      const fieldMapping: Record<string, string> = {
        "construction_start": "construction_start_date",
        "expected_completion": "expected_completion_date",
        "appreciation_rate": "appreciation_rate_at_completion",
        "sale_at_completion": "sale_at_completion"
      };
      await realEstateApi.updateOffPlanDetails(portfolioId, propertyId, { [fieldMapping[field]]: value });
      fetchProperties();
      if (selectedPropertyId === propertyId) {
        fetchSchedule();
      }
    } catch (err) {
      console.error("Failed to update details", err);
    }
  };

  const handleMilestoneChange = (milestoneId: string, field: string, value: string) => {
    setLocalMilestoneInputs(prev => ({
      ...prev,
      [milestoneId]: { ...prev[milestoneId], [field]: value }
    }));
  };

  const handleMilestoneBlur = async (milestoneId: string, field: string, value: string) => {
    if (milestoneId === "completion" || milestoneId === "sale") return;

    try {
      const fieldMapping: Record<string, string> = {
        "milestone": "milestone_name",
        "date": "date",
        "percentage": "percentage_of_price"
      };
      await realEstateApi.updateOffPlanMilestone(portfolioId, milestoneId, { [fieldMapping[field]]: value });
      fetchSchedule();
    } catch (err) {
      console.error("Failed to update milestone", err);
    }
  };

  const handleAddMilestone = async () => {
    if (!selectedPropertyId) return;
    try {
      const prop = properties.find(p => p.property_id === selectedPropertyId);
      await realEstateApi.createOffPlanMilestone(portfolioId, selectedPropertyId, {
        milestone_name: "New Milestone",
        date: prop?.construction_start || new Date().toISOString().split('T')[0],
        percentage_of_price: "0.00"
      });
      fetchSchedule();
    } catch (err) {
      console.error("Failed to create milestone", err);
    }
  };

  const handleDeleteMilestone = async (milestoneId: string) => {
    if (milestoneId === "completion" || milestoneId === "sale") return;
    if (!window.confirm("Are you sure you want to delete this milestone?")) return;
    try {
      await realEstateApi.deleteOffPlanMilestone(portfolioId, milestoneId);
      fetchSchedule();
    } catch (err) {
      console.error("Failed to delete milestone", err);
    }
  };

  return (
    <div className="off-plan-model-container">
      <style>{`
        .off-plan-model-container { padding: 1rem; }
        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
          background: #f8fafc;
          padding: 0.75rem 1rem;
          border-radius: 8px;
          cursor: pointer;
        }
        .section-content {
          overflow: hidden;
          transition: max-height 0.5s ease-out, opacity 0.3s ease-in;
          max-height: 2000px;
          opacity: 1;
        }
        .section-content.collapsed {
          max-height: 0;
          opacity: 0;
          pointer-events: none;
        }
        .table-wrapper {
          overflow-x: auto;
          background: white;
          border-radius: 8px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          margin-bottom: 2rem;
        }
        .data-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.875rem;
        }
        .data-table th, .data-table td {
          padding: 0.75rem 1rem;
          text-align: left;
          border-bottom: 1px solid #e2e8f0;
          white-space: nowrap;
        }
        .data-table th { background: #f8fafc; font-weight: 600; color: #475569; }
        .data-table tr:hover { background: #f1f5f9; }
        .editable-input {
          border: 1px solid transparent;
          background: transparent;
          padding: 0.25rem;
          width: 100%;
          border-radius: 4px;
        }
        .editable-input:focus {
          border-color: #3b82f6;
          background: white;
          outline: none;
        }
        .editable-input:hover { background: rgba(0,0,0,0.05); }
        .metrics-card {
          background: #f1f5f9;
          padding: 1rem;
          border-radius: 8px;
          display: flex;
          gap: 2rem;
          margin-bottom: 1rem;
        }
        .metric-item { display: flex; flex-direction: column; }
        .metric-label { font-size: 0.75rem; color: #64748b; font-weight: 600; text-transform: uppercase; }
        .metric-value { font-size: 1.25rem; font-weight: 700; color: #1e293b; }
        .btn-delete {
          background: #fee2e2;
          color: #991b1b;
          border: 1px solid #fecaca;
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.75rem;
        }
      `}</style>

      <div className="section">
        <div className="section-header" onClick={() => setShowPropertiesTable(!showPropertiesTable)}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ transform: showPropertiesTable ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>▶</span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1e293b', margin: 0 }}>Off-Plan Properties</h2>
          </div>
        </div>

        <div className={`section-content ${showPropertiesTable ? '' : 'collapsed'}`}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>Loading properties...</div>
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Property Name</th>
                    <th>Total Purchase Price</th>
                    <th>Construction Start</th>
                    <th>Expected Delivery Date</th>
                    <th>Appreciation Rate</th>
                    <th>Sale at Completion</th>
                    <th>Value at Completion</th>
                  </tr>
                </thead>
                <tbody>
                  {properties.map((p) => (
                    <tr key={p.property_id}>
                      <td style={{ fontWeight: 600 }}>{p.property_name}</td>
                      <td>{formatCurrency(parseFloat(p.purchase_price))}</td>
                      <td>
                        <input 
                          type="date" 
                          className="editable-input" 
                          value={localPropertyInputs[p.property_id]?.construction_start || ""} 
                          onChange={(e) => handlePropertyDetailChange(p.property_id, "construction_start", e.target.value)}
                          onBlur={(e) => handlePropertyDetailBlur(p.property_id, "construction_start", e.target.value)}
                          disabled={!canEdit}
                        />
                      </td>
                      <td>
                        <input 
                          type="date" 
                          className="editable-input" 
                          value={localPropertyInputs[p.property_id]?.expected_completion || ""} 
                          onChange={(e) => handlePropertyDetailChange(p.property_id, "expected_completion", e.target.value)}
                          onBlur={(e) => handlePropertyDetailBlur(p.property_id, "expected_completion", e.target.value)}
                          disabled={!canEdit}
                        />
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <input 
                            type="number" 
                            className="editable-input" 
                            style={{ width: '60px' }}
                            value={localPropertyInputs[p.property_id]?.appreciation_rate || ""} 
                            onChange={(e) => handlePropertyDetailChange(p.property_id, "appreciation_rate", e.target.value)}
                            onBlur={(e) => handlePropertyDetailBlur(p.property_id, "appreciation_rate", e.target.value)}
                            disabled={!canEdit}
                          />
                          <span>%</span>
                        </div>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <input 
                          type="checkbox" 
                          checked={localPropertyInputs[p.property_id]?.sale_at_completion || false} 
                          onChange={(e) => {
                            const val = e.target.checked;
                            handlePropertyDetailChange(p.property_id, "sale_at_completion", val);
                            handlePropertyDetailBlur(p.property_id, "sale_at_completion", val);
                          }}
                          disabled={!canEdit}
                        />
                      </td>
                      <td style={{ fontWeight: 700, color: '#2563eb' }}>{formatCurrency(p.value_at_completion)}</td>
                    </tr>
                  ))}
                  {properties.length === 0 && (
                    <tr><td colSpan={7} style={{ textAlign: 'center', padding: '2rem' }}>No off-plan properties found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="section" style={{ marginTop: '1rem' }}>
        <div className="section-header" onClick={() => setShowScheduleTable(!showScheduleTable)}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ transform: showScheduleTable ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>▶</span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1e293b', margin: 0 }}>Payment Schedule</h2>
          </div>
          {canEdit && selectedPropertyId && (
            <button className="btn btn-primary" onClick={(e) => { e.stopPropagation(); handleAddMilestone(); }}>
              + Add Milestone
            </button>
          )}
        </div>

        <div className={`section-content ${showScheduleTable ? '' : 'collapsed'}`}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ fontWeight: 500, marginRight: '1rem' }}>Select Property:</label>
            <select 
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
              value={selectedPropertyId} 
              onChange={(e) => setSelectedPropertyId(e.target.value)}
            >
              {properties.map(p => (
                <option key={p.property_id} value={p.property_id}>{p.property_name}</option>
              ))}
            </select>
          </div>

          {scheduleLoading ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>Loading schedule...</div>
          ) : scheduleData && (
            <>
              <div className="metrics-card">
                <div className="metric-item">
                  <span className="metric-label">Projected XIRR</span>
                  <span className="metric-value" style={{ color: scheduleData.metrics.xirr >= 0 ? '#10b981' : '#ef4444' }}>
                    {scheduleData.metrics.xirr}%
                  </span>
                </div>
                <div className="metric-item">
                  <span className="metric-label">Total Expected Profit</span>
                  <span className="metric-value">{formatCurrency(scheduleData.metrics.total_expected_profit)}</span>
                </div>
              </div>

              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Milestone</th>
                      <th>Date / Expected Date</th>
                      <th>% of Price</th>
                      <th>Cash Flow</th>
                      <th>Cumulative Deployed</th>
                      {canEdit && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {scheduleData.schedule.map((m) => (
                      <tr key={m.id}>
                        <td style={{ fontWeight: 600 }}>
                          {m.id === "completion" || m.id === "sale" ? (
                            <span>{m.milestone}</span>
                          ) : (
                            <input 
                              type="text" 
                              className="editable-input" 
                              value={localMilestoneInputs[m.id]?.milestone || ""} 
                              onChange={(e) => handleMilestoneChange(m.id, "milestone", e.target.value)}
                              onBlur={(e) => handleMilestoneBlur(m.id, "milestone", e.target.value)}
                              disabled={!canEdit}
                            />
                          )}
                        </td>
                        <td>
                          {m.id === "completion" || m.id === "sale" ? (
                            <span>{m.date}</span>
                          ) : (
                            <input 
                              type="date" 
                              className="editable-input" 
                              value={localMilestoneInputs[m.id]?.date || ""} 
                              onChange={(e) => handleMilestoneChange(m.id, "date", e.target.value)}
                              onBlur={(e) => handleMilestoneBlur(m.id, "date", e.target.value)}
                              disabled={!canEdit}
                            />
                          )}
                        </td>
                        <td>
                          {m.id === "sale" ? (
                            <span>-</span>
                          ) : m.id === "completion" ? (
                            <span>{parseFloat(m.percentage.toString()).toFixed(2)}%</span>
                          ) : (
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                              <input 
                                type="number" 
                                className="editable-input" 
                                style={{ width: '60px' }}
                                value={localMilestoneInputs[m.id]?.percentage || ""} 
                                onChange={(e) => handleMilestoneChange(m.id, "percentage", e.target.value)}
                                onBlur={(e) => handleMilestoneBlur(m.id, "percentage", e.target.value)}
                                disabled={!canEdit}
                              />
                              <span>%</span>
                            </div>
                          )}
                        </td>
                        <td style={{ fontWeight: 600, color: m.cash_flow < 0 ? '#ef4444' : '#10b981' }}>
                          {formatCurrency(m.cash_flow)}
                        </td>
                        <td>{formatCurrency(m.cumulative_deployed)}</td>
                        {canEdit && (
                          <td>
                            {m.id !== "completion" && m.id !== "sale" && (
                              <button className="btn-delete" onClick={() => handleDeleteMilestone(m.id)}>Delete</button>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default OffPlanModelTab;
