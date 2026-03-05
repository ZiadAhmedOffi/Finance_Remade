import React, { useState, useEffect } from "react";
import { fundsApi } from "../api/api";

interface DealPrognosisTabProps {
  fundId: string;
  canEdit: boolean;
}

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

/**
 * DealPrognosisTab Component (Formerly Investment Deals)
 * Displays and manages investment deals for a fund.
 * Restricted to Super Admins and Fund Steering Committee members for editing.
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

  const handleDeleteDeal = async (dealId: string) => {
    if (!window.confirm("Are you sure you want to delete this deal?")) return;
    try {
      await fundsApi.deleteDeal(fundId, dealId);
      fetchDeals();
    } catch (err) {
      setError("Failed to delete deal.");
    }
  };

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
      <div className="deals-header">
        <h3>Deal Prognosis</h3>
        {canEdit && !isAdding && (
          <button className="btn btn-primary" onClick={() => { setIsAdding(true); setEditingDeal(null); setFormData(emptyDeal); }}>+ Add New Deal</button>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {isAdding && (
        <div className="add-deal-overlay">
          <form onSubmit={handleSubmit} className="add-deal-form">
            <h4>{editingDeal ? "Edit Investment Deal" : "Add New Investment Deal"}</h4>
            
            <div className="form-grid">
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

      <div className="table-responsive">
        {deals.length > 0 ? (
          <table className="logs-table deals-table">
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
                      <div className="action-buttons">
                        <button className="btn-edit" onClick={() => handleEdit(deal)}>Edit</button>
                        <button className="btn-delete" onClick={() => handleDeleteDeal(deal.id)}>Delete</button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty-state">No investment deals found.</div>
        )}
      </div>

      <style>{`
        .deals-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
        }
        .add-deal-overlay {
          background: #f8f9fa;
          padding: 2rem;
          border-radius: 8px;
          border: 1px solid #ddd;
          margin-bottom: 2rem;
        }
        .form-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 1rem;
        }
        .table-responsive {
          overflow-x: auto;
        }
        .deals-table {
          font-size: 0.85rem;
          min-width: 1200px;
        }
        .status-badge {
          padding: 0.2rem 0.4rem;
          border-radius: 4px;
          font-size: 0.7rem;
          font-weight: 700;
        }
        .scenario-base { background: #d1ecf1; color: #0c5460; }
        .scenario-downside { background: #f8d7da; color: #721c24; }
        .scenario-upside { background: #d4edda; color: #155724; }
        .action-buttons {
          display: flex;
          gap: 0.5rem;
        }
        .btn-edit {
          background: none;
          border: none;
          color: #007bff;
          cursor: pointer;
          font-weight: 600;
        }
        .btn-delete {
          background: none;
          border: none;
          color: #dc3545;
          cursor: pointer;
          font-weight: 600;
        }
        .btn-edit:hover, .btn-delete:hover { text-decoration: underline; }
        .empty-state {
          text-align: center;
          padding: 3rem;
          background: #f8f9fa;
          border-radius: 8px;
          color: #666;
        }
      `}</style>
    </div>
  );
};

export default DealPrognosisTab;
