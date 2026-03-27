import React, { useState, useEffect } from "react";
import { fundsApi } from "../api/api";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface CurrentDealsTabProps {
  fundId: string;
  canEdit: boolean;
}

/**
 * Interface representing an individual current investment deal.
 */
interface CurrentDeal {
  id: string;
  company_name: string;
  company_type: string;
  industry: string;
  entry_year: number;
  latest_valuation_year: number;
  amount_invested: string;
  entry_valuation: string;
  latest_valuation: string;
  holding_period: number;
  post_money_ownership: number;
  moic: number;
  final_exit_amount: number;
  is_pro_rata: boolean;
  parent_deal: string | null;
}

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8", "#82ca9d"];

/**
 * CurrentDealsTab Component
 * 
 * Manages the "Current Deals" section of a fund.
 */
const CurrentDealsTab: React.FC<CurrentDealsTabProps> = ({ fundId, canEdit }) => {
  const [deals, setDeals] = useState<CurrentDeal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [editingDeal, setEditingDeal] = useState<CurrentDeal | null>(null);
  const [expandedDeals, setExpandedDeals] = useState<Record<string, boolean>>({});

  const currentYear = new Date().getFullYear();

  const emptyDeal = {
    company_name: "",
    company_type: "",
    industry: "",
    entry_year: currentYear,
    latest_valuation_year: currentYear,
    amount_invested: "1000000",
    entry_valuation: "10000000",
    latest_valuation: "12000000",
    is_pro_rata: false,
    parent_deal: null as string | null
  };

  const [formData, setFormData] = useState(emptyDeal);

  /**
   * Fetches the current list of deals for the fund.
   */
  const fetchDeals = async () => {
    try {
      const response = await fundsApi.getCurrentDeals(fundId);
      setDeals(response.data);
    } catch (err) {
      setError("Failed to fetch current deals.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeals();
  }, [fundId]);

  const toggleExpand = (dealId: string) => {
    setExpandedDeals(prev => ({
      ...prev,
      [dealId]: !prev[dealId]
    }));
  };

  // Helper to get parent options
  const getParentOptions = () => {
    return deals.filter(d => 
      !d.is_pro_rata && 
      d.company_name.toLowerCase() === formData.company_name.toLowerCase() &&
      d.id !== editingDeal?.id
    );
  };

  /* --- Data Processing for Analytics --- */

  // 1. Group deals by company type for Pie Chart
  const dealsByType = deals.reduce((acc: any, deal) => {
    const type = deal.company_type || "Unknown";
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {});
  const chartDataDealsByType = Object.keys(dealsByType).map(type => ({ name: type, value: dealsByType[type] }));

  // 2. Aggregate invested capital by company type for Pie Chart
  const capitalByType = deals.reduce((acc: any, deal) => {
    const type = deal.company_type || "Unknown";
    acc[type] = (acc[type] || 0) + parseFloat(deal.amount_invested);
    return acc;
  }, {});
  const chartDataCapitalByType = Object.keys(capitalByType).map(type => ({ name: type, value: capitalByType[type] }));

  // 3. Extract max holding periods per distinct company for Bar Chart
  const holdingPeriods = deals.reduce((acc: any, deal) => {
    if (!acc[deal.company_name] || deal.holding_period > acc[deal.company_name]) {
      acc[deal.company_name] = deal.holding_period;
    }
    return acc;
  }, {});
  const chartDataHoldingPeriod = Object.keys(holdingPeriods)
    .map(name => ({ name, holding_period: holdingPeriods[name] }))
    .sort((a, b) => b.holding_period - a.holding_period);

  /**
   * Handles creation or update of a deal.
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (formData.entry_year > currentYear) {
      setError(`Entry year cannot be in the future (max ${currentYear}).`);
      return;
    }
    if (formData.latest_valuation_year > currentYear) {
      setError(`Latest valuation year cannot be in the future (max ${currentYear}).`);
      return;
    }
    if (formData.latest_valuation_year < formData.entry_year) {
      setError("Latest valuation year cannot be before entry year.");
      return;
    }

    if (formData.is_pro_rata && !formData.parent_deal) {
      setError("A parent deal must be selected for pro rata deals.");
      return;
    }

    try {
      if (editingDeal) {
        await fundsApi.updateCurrentDeal(fundId, editingDeal.id, formData);
      } else {
        await fundsApi.createCurrentDeal(fundId, formData);
      }
      setIsAdding(false);
      setEditingDeal(null);
      setFormData(emptyDeal);
      setError(null);
      fetchDeals();
    } catch (err: any) {
      const serverMsg = err.response?.data ? JSON.stringify(err.response.data) : "";
      setError(`Failed to ${editingDeal ? "update" : "add"} deal. ${serverMsg}`);
    }
  };

  /**
   * Pre-populates form for editing an existing deal.
   */
  const handleEdit = (deal: CurrentDeal) => {
    setEditingDeal(deal);
    setFormData({
      company_name: deal.company_name,
      company_type: deal.company_type,
      industry: deal.industry,
      entry_year: deal.entry_year,
      latest_valuation_year: deal.latest_valuation_year,
      amount_invested: deal.amount_invested,
      entry_valuation: deal.entry_valuation,
      latest_valuation: deal.latest_valuation,
      is_pro_rata: deal.is_pro_rata,
      parent_deal: deal.parent_deal
    });
    setIsAdding(true);
  };

  /**
   * Permanently deletes a deal.
   */
  const handleDeleteDeal = async (dealId: string) => {
    if (!window.confirm("Are you sure you want to delete this deal?")) return;
    try {
      await fundsApi.deleteCurrentDeal(fundId, dealId);
      fetchDeals();
    } catch (err) {
      setError("Failed to delete deal.");
    }
  };

  // Formatting Utilities
  const formatCurrency = (val: string | number) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(num);
  };

  const formatPercentage = (val: number) => {
    return `${val.toFixed(2)}%`;
  };

  const formatMOIC = (val: number) => {
    return `${val.toFixed(2)}x`;
  };

  // Process deals for display: Group pro-rata deals under their parents
  const getDisplayDeals = () => {
    const parentDeals = deals.filter(d => !d.is_pro_rata);
    const proRataDeals = deals.filter(d => d.is_pro_rata);
    
    const displayList: { deal: CurrentDeal, isVisible: boolean, isProRata: boolean, hasChildren: boolean }[] = [];
    
    parentDeals.forEach(parent => {
      const associatedProRata = proRataDeals.filter(pr => pr.parent_deal === parent.id);
      displayList.push({ 
        deal: parent, 
        isVisible: true, 
        isProRata: false, 
        hasChildren: associatedProRata.length > 0 
      });
      
      associatedProRata.forEach(child => {
        displayList.push({ 
          deal: child, 
          isVisible: expandedDeals[parent.id] || false, 
          isProRata: true, 
          hasChildren: false 
        });
      });
    });

    // Also include pro-rata deals whose parents are missing (fallback)
    const orphans = proRataDeals.filter(pr => !parentDeals.find(p => p.id === pr.parent_deal));
    orphans.forEach(orphan => {
      displayList.push({ 
        deal: orphan, 
        isVisible: true, 
        isProRata: true, 
        hasChildren: false 
      });
    });

    return displayList;
  };

  if (loading) return <div>Loading current deals...</div>;

  return (
    <div className="deals-tab">
      {error && <div className="alert alert-error">{error}</div>}

      {/* Add/Edit Deal Overlay */}
      {isAdding && (
        <div className="add-deal-overlay content-card" style={{marginBottom: '3rem'}}>
          <form onSubmit={handleSubmit} className="add-deal-form">
            <h4>{editingDeal ? "Edit Current Deal" : "Add New Current Deal"}</h4>
            
            <div className="form-grid" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '1.5rem'}}>
              <div className="form-group">
                <label>Company Name</label>
                <input type="text" value={formData.company_name} onChange={e => setFormData({...formData, company_name: e.target.value})} required />
              </div>
              <div className="form-group">
                <label>Company Type</label>
                <input type="text" value={formData.company_type} onChange={e => setFormData({...formData, company_type: e.target.value})} required />
              </div>
              <div className="form-group">
                <label>Industry</label>
                <input type="text" value={formData.industry} onChange={e => setFormData({...formData, industry: e.target.value})} required />
              </div>
              <div className="form-group">
                <label>Entry Year</label>
                <input type="number" value={formData.entry_year} max={currentYear} onChange={e => setFormData({...formData, entry_year: parseInt(e.target.value)})} required />
              </div>
              <div className="form-group">
                <label>Latest Valuation Year</label>
                <input type="number" value={formData.latest_valuation_year} max={currentYear} onChange={e => setFormData({...formData, latest_valuation_year: parseInt(e.target.value)})} required />
              </div>
              <div className="form-group">
                <label>Amount Invested (USD)</label>
                <input type="number" value={formData.amount_invested} onChange={e => setFormData({...formData, amount_invested: e.target.value})} required step="any" />
              </div>
              <div className="form-group">
                <label>Entry Valuation (USD)</label>
                <input type="number" value={formData.entry_valuation} onChange={e => setFormData({...formData, entry_valuation: e.target.value})} required step="any" />
              </div>
              <div className="form-group">
                <label>Latest Valuation (USD)</label>
                <input type="number" value={formData.latest_valuation} onChange={e => setFormData({...formData, latest_valuation: e.target.value})} required step="any" />
              </div>
              <div className="form-group" style={{display: 'flex', alignItems: 'center', gap: '0.5rem', height: '100%', paddingTop: '1.5rem'}}>
                <input 
                  type="checkbox" 
                  id="is_pro_rata"
                  checked={formData.is_pro_rata} 
                  onChange={e => {
                    const isChecked = e.target.checked;
                    setFormData({
                      ...formData, 
                      is_pro_rata: isChecked,
                      parent_deal: isChecked ? formData.parent_deal : null
                    });
                  }} 
                />
                <label htmlFor="is_pro_rata" style={{margin: 0}}>Is Pro Rata Deal?</label>
              </div>
              {formData.is_pro_rata && (
                <div className="form-group">
                  <label>Parent Deal</label>
                  <select 
                    value={formData.parent_deal || ""} 
                    onChange={e => setFormData({...formData, parent_deal: e.target.value || null})}
                    required
                  >
                    <option value="">Select Parent Deal</option>
                    {getParentOptions().map(option => (
                      <option key={option.id} value={option.id}>
                        {option.company_name} ({option.entry_year}) - {formatCurrency(option.amount_invested)}
                      </option>
                    ))}
                  </select>
                  {getParentOptions().length === 0 && (
                    <small style={{color: '#dc3545', display: 'block', marginTop: '0.25rem'}}>
                      No existing deals for this company found.
                    </small>
                  )}
                </div>
              )}
            </div>

            <div className="form-actions" style={{marginTop: '1.5rem'}}>
              <button type="button" className="btn" onClick={() => { setIsAdding(false); setEditingDeal(null); }}>Cancel</button>
              <button type="submit" className="btn btn-primary">{editingDeal ? "Update Deal" : "Create Deal"}</button>
            </div>
          </form>
        </div>
      )}

      {/* Deals Listing Table */}
      <div className="content-card">
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', borderBottom: '1px solid var(--border-light)', paddingBottom: '1rem'}}>
          <h3 style={{margin: 0, border: 'none'}}>Current Deals (Made)</h3>
          {canEdit && !isAdding && (
            <button className="btn btn-primary" onClick={() => { setIsAdding(true); setEditingDeal(null); setFormData(emptyDeal); }}>+ Add New Deal</button>
          )}
        </div>
        <div className="table-responsive">
          {deals.length > 0 ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th className="sticky-left">Company Name</th>
                  <th>Type</th>
                  <th>Industry</th>
                  <th>Entry Year</th>
                  <th>Amt Invested</th>
                  <th>Entry Val</th>
                  <th>Latest Val</th>
                  <th>Val Year</th>
                  <th>MOIC</th>
                  <th>Holding Period</th>
                  <th>Ownership %</th>
                  <th>Current Value</th>
                  {canEdit && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {getDisplayDeals().map(({ deal, isVisible, isProRata, hasChildren }) => (
                  isVisible && (
                    <tr 
                      key={deal.id} 
                      className={isProRata ? "pro-rata-row" : ""}
                      style={{ 
                        borderLeft: isProRata ? '4px solid #2563eb' : 'none'
                      }}
                    >
                      <td className="sticky-left" style={{ backgroundColor: 'white' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          {isProRata && <span style={{ color: '#2563eb', fontWeight: 'bold', marginLeft: '1rem' }}>↳</span>}
                          <strong>{deal.company_name}</strong>
                          {hasChildren && (
                            <button 
                              onClick={() => toggleExpand(deal.id)}
                              style={{
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                padding: '2px 5px',
                                fontSize: '0.8rem',
                                color: '#64748b',
                                display: 'inline-flex',
                                alignItems: 'center'
                              }}
                              title={expandedDeals[deal.id] ? "Hide Pro Rata" : "Show Pro Rata"}
                            >
                              {expandedDeals[deal.id] ? '▼' : '▶'}
                            </button>
                          )}
                          {isProRata && <small style={{ color: '#2563eb', fontStyle: 'italic', marginLeft: 'auto' }}>Pro Rata</small>}
                        </div>
                      </td>
                      <td>{deal.company_type}</td>
                      <td>{deal.industry}</td>
                      <td>{deal.entry_year}</td>
                      <td>{formatCurrency(deal.amount_invested)}</td>
                      <td>{formatCurrency(deal.entry_valuation)}</td>
                      <td>{formatCurrency(deal.latest_valuation)}</td>
                      <td>{deal.latest_valuation_year}</td>
                      <td>{formatMOIC(deal.moic)}</td>
                      <td>{deal.holding_period} yrs</td>
                      <td>{formatPercentage(deal.post_money_ownership)}</td>
                      <td>{formatCurrency(deal.final_exit_amount)}</td>
                      {canEdit && (
                        <td>
                          <div style={{display: 'flex', gap: '0.5rem'}}>
                            <button onClick={() => handleEdit(deal)} style={{background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', fontWeight: '600'}}>Edit</button>
                            <button onClick={() => handleDeleteDeal(deal.id)} style={{background: 'none', border: 'none', color: '#dc3545', cursor: 'pointer', fontWeight: '600'}}>Delete</button>
                          </div>
                        </td>
                      )}
                    </tr>
                  )
                ))}
              </tbody>
            </table>
          ) : (
            <div style={{textAlign: 'center', padding: '3rem', color: '#64748b'}}>No current deals found.</div>
          )}
        </div>
      </div>

      {/* Analytics Visualizations */}
      {deals.length > 0 && (
        <div className="charts-grid" style={{marginTop: '3rem'}}>
          <div className="chart-container">
            <h4>Current Deals by Company Type</h4>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={chartDataDealsByType}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, percent }) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}
                >
                  {chartDataDealsByType.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-container">
            <h4>Capital Invested (Current Deals)</h4>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={chartDataCapitalByType}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  fill="#82ca9d"
                  dataKey="value"
                  label={({ name, percent }) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}
                >
                  {chartDataCapitalByType.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: any) => formatCurrency(Number(value))} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-container wide">
            <h4>Holding Period by Company (Years)</h4>
            <ResponsiveContainer width="100%" height={Math.max(250, chartDataHoldingPeriod.length * 40)}>
              <BarChart
                layout="vertical"
                data={chartDataHoldingPeriod}
                margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={90} />
                <Tooltip />
                <Legend />
                <Bar dataKey="holding_period" fill="#8884d8" name="Holding Period (Years)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

export default CurrentDealsTab;
