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

interface DealPrognosisTabProps {
  fundId: string;
  canEdit: boolean;
}

/**
 * Interface representing an individual investment deal.
 */
interface Deal {
  id: string;
  company_name: string;
  company_type: string;
  industry: string;
  entry_year: number;
  exit_year: number;
  amount_invested: string;
  entry_valuation: string;
  base_factor: string;
  downside_factor: string;
  upside_factor: string;
  selected_scenario: "BASE" | "DOWNSIDE" | "UPSIDE";
  holding_period: number;
  post_money_ownership: number;
  exit_valuation: number;
  exit_value: number;
}

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8", "#82ca9d"];

/**
 * DealPrognosisTab Component
 * 
 * Manages the "Deal Prognosis" section of a fund.
 * Features:
 * - CRUD operations for investment deals.
 * - Real-time scenario switching (Base, Upside, Downside).
 * - Portfolio analytics (Company type distribution, Capital allocation, Holding periods).
 * 
 * @param {string} fundId - The unique identifier of the fund.
 * @param {boolean} canEdit - Flag indicating if the current user has write permissions.
 */
const DealPrognosisTab: React.FC<DealPrognosisTabProps> = ({ fundId, canEdit }) => {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [editingDeal, setEditingDeal] = useState<Deal | null>(null);

  const emptyDeal = {
    company_name: "",
    company_type: "",
    industry: "",
    entry_year: new Date().getFullYear(),
    exit_year: new Date().getFullYear() + 5,
    amount_invested: "1000000",
    entry_valuation: "10000000",
    base_factor: "2.00",
    downside_factor: "1.00",
    upside_factor: "3.50",
    selected_scenario: "BASE" as const
  };

  const [formData, setFormData] = useState(emptyDeal);

  /**
   * Fetches the current list of deals for the fund.
   */
  const fetchDeals = async () => {
    try {
      const response = await fundsApi.getDeals(fundId);
      setDeals(response.data);
    } catch (err) {
      setError("Failed to fetch deals.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeals();
  }, [fundId]);

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
    try {
      if (editingDeal) {
        await fundsApi.updateDeal(fundId, editingDeal.id, formData);
      } else {
        await fundsApi.createDeal(fundId, formData);
      }
      setIsAdding(false);
      setEditingDeal(null);
      setFormData(emptyDeal);
      fetchDeals();
    } catch (err) {
      setError(`Failed to ${editingDeal ? "update" : "add"} deal.`);
    }
  };

  /**
   * Pre-populates form for editing an existing deal.
   */
  const handleEdit = (deal: Deal) => {
    setEditingDeal(deal);
    setFormData({
      company_name: deal.company_name,
      company_type: deal.company_type,
      industry: deal.industry,
      entry_year: deal.entry_year,
      exit_year: deal.exit_year,
      amount_invested: deal.amount_invested,
      entry_valuation: deal.entry_valuation,
      base_factor: deal.base_factor,
      downside_factor: deal.downside_factor,
      upside_factor: deal.upside_factor,
      selected_scenario: deal.selected_scenario
    });
    setIsAdding(true);
  };

  /**
   * Permanently deletes a deal.
   */
  const handleDeleteDeal = async (dealId: string) => {
    if (!window.confirm("Are you sure you want to delete this deal?")) return;
    try {
      await fundsApi.deleteDeal(fundId, dealId);
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

  if (loading) return <div>Loading deals...</div>;

  return (
    <div className="deals-tab">
      {error && <div className="alert alert-error">{error}</div>}

      {/* Add/Edit Deal Overlay */}
      {isAdding && (
        <div className="add-deal-overlay content-card" style={{marginBottom: '3rem'}}>
          <form onSubmit={handleSubmit} className="add-deal-form">
            <h4>{editingDeal ? "Edit Investment Deal" : "Add New Investment Deal"}</h4>
            
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
                <input type="number" value={formData.entry_year} onChange={e => setFormData({...formData, entry_year: parseInt(e.target.value)})} required />
              </div>
              <div className="form-group">
                <label>Exit Year</label>
                <input type="number" value={formData.exit_year} onChange={e => setFormData({...formData, exit_year: parseInt(e.target.value)})} required />
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
                <label>Base Factor</label>
                <input type="number" value={formData.base_factor} onChange={e => setFormData({...formData, base_factor: e.target.value})} required step="0.01" />
              </div>
              <div className="form-group">
                <label>Downside Factor</label>
                <input type="number" value={formData.downside_factor} onChange={e => setFormData({...formData, downside_factor: e.target.value})} required step="0.01" />
              </div>
              <div className="form-group">
                <label>Upside Factor</label>
                <input type="number" value={formData.upside_factor} onChange={e => setFormData({...formData, upside_factor: e.target.value})} required step="0.01" />
              </div>
              <div className="form-group">
                <label>Selected Scenario</label>
                <select value={formData.selected_scenario} onChange={e => setFormData({...formData, selected_scenario: e.target.value as "BASE" | "DOWNSIDE" | "UPSIDE"})}>
                  <option value="BASE">Base</option>
                  <option value="DOWNSIDE">Downside</option>
                  <option value="UPSIDE">Upside</option>
                </select>
              </div>
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
          <h3 style={{margin: 0, border: 'none'}}>Investment Deals</h3>
          {canEdit && !isAdding && (
            <button className="btn btn-primary" onClick={() => { setIsAdding(true); setEditingDeal(null); setFormData(emptyDeal); }}>+ Add New Deal</button>
          )}
        </div>
        <div className="table-responsive">
          {deals.length > 0 ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Company Name</th>
                  <th>Type</th>
                  <th>Industry</th>
                  <th>Entry Year</th>
                  <th>Amt Invested</th>
                  <th>Entry Val</th>
                  <th>Exit Year</th>
                  <th>Scenario</th>
                  <th>Holding Period</th>
                  <th>Ownership %</th>
                  <th>Exit Val</th>
                  <th>Exit Value</th>
                  {canEdit && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {deals.map(deal => (
                  <tr key={deal.id}>
                    <td><strong>{deal.company_name}</strong></td>
                    <td>{deal.company_type}</td>
                    <td>{deal.industry}</td>
                    <td>{deal.entry_year}</td>
                    <td>{formatCurrency(deal.amount_invested)}</td>
                    <td>{formatCurrency(deal.entry_valuation)}</td>
                    <td>{deal.exit_year}</td>
                    <td>
                      <span className={`status-badge scenario-${deal.selected_scenario.toLowerCase()}`}>
                        {deal.selected_scenario}
                      </span>
                    </td>
                    <td>{deal.holding_period} yrs</td>
                    <td>{formatPercentage(deal.post_money_ownership)}</td>
                    <td>{formatCurrency(deal.exit_valuation)}</td>
                    <td>{formatCurrency(deal.exit_value)}</td>
                    {canEdit && (
                      <td>
                        <div style={{display: 'flex', gap: '0.5rem'}}>
                          <button onClick={() => handleEdit(deal)} style={{background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', fontWeight: '600'}}>Edit</button>
                          <button onClick={() => handleDeleteDeal(deal.id)} style={{background: 'none', border: 'none', color: '#dc3545', cursor: 'pointer', fontWeight: '600'}}>Delete</button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div style={{textAlign: 'center', padding: '3rem', color: '#64748b'}}>No investment deals found.</div>
          )}
        </div>
      </div>

      {/* Analytics Visualizations */}
      {deals.length > 0 && (
        <div className="charts-grid" style={{marginTop: '3rem'}}>
          <div className="chart-container">
            <h4>Deals by Company Type</h4>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={chartDataDealsByType}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
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
            <h4>Capital Invested by Company Type</h4>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={chartDataCapitalByType}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  fill="#82ca9d"
                  dataKey="value"
                  label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                >
                  {chartDataCapitalByType.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
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

export default DealPrognosisTab;
