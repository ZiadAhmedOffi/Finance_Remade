import React, { useState, useEffect } from "react";
import { fundsApi } from "../api/api";

interface DealsTabProps {
  fundId: string;
  canEdit: boolean;
}

interface Deal {
  id: string;
  name: string;
  description: string;
  amount_invested: string;
  date_of_investment: string;
  status: string;
}

const DealsTab: React.FC<DealsTabProps> = ({ fundId, canEdit }) => {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [newDeal, setNewDeal] = useState({
    name: "",
    description: "",
    amount_invested: "",
    date_of_investment: new Date().toISOString().split('T')[0],
    status: "PENDING"
  });

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

  const handleAddDeal = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fundsApi.createDeal(fundId, newDeal);
      setIsAdding(false);
      setNewDeal({
        name: "",
        description: "",
        amount_invested: "",
        date_of_investment: new Date().toISOString().split('T')[0],
        status: "PENDING"
      });
      fetchDeals();
    } catch (err) {
      setError("Failed to add deal.");
    }
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

  if (loading) return <div>Loading deals...</div>;

  return (
    <div className="deals-tab">
      <div className="deals-header">
        <h3>Investment Deals</h3>
        {canEdit && !isAdding && (
          <button className="btn btn-primary" onClick={() => setIsAdding(true)}>+ Add New Deal</button>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {isAdding && (
        <div className="add-deal-overlay">
          <form onSubmit={handleAddDeal} className="add-deal-form">
            <h4>Add New Investment Deal</h4>
            <div className="form-group">
              <label>Deal Name</label>
              <input type="text" value={newDeal.name} onChange={e => setNewDeal({...newDeal, name: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Amount Invested [USD]</label>
              <input type="number" value={newDeal.amount_invested} onChange={e => setNewDeal({...newDeal, amount_invested: e.target.value})} required step="any" />
            </div>
            <div className="form-group">
              <label>Date of Investment</label>
              <input type="date" value={newDeal.date_of_investment} onChange={e => setNewDeal({...newDeal, date_of_investment: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Status</label>
              <select value={newDeal.status} onChange={e => setNewDeal({...newDeal, status: e.target.value})}>
                <option value="PENDING">Pending</option>
                <option value="ACTIVE">Active</option>
                <option value="EXITED">Exited</option>
              </select>
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea value={newDeal.description} onChange={e => setNewDeal({...newDeal, description: e.target.value})} rows={3} />
            </div>
            <div className="form-actions">
              <button type="button" className="btn" onClick={() => setIsAdding(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary">Create Deal</button>
            </div>
          </form>
        </div>
      )}

      {deals.length > 0 ? (
        <table className="logs-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Deal Name</th>
              <th>Amount</th>
              <th>Status</th>
              {canEdit && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {deals.map(deal => (
              <tr key={deal.id}>
                <td>{new Date(deal.date_of_investment).toLocaleDateString()}</td>
                <td>
                  <strong>{deal.name}</strong>
                  <div style={{fontSize: '0.8rem', color: '#666'}}>{deal.description}</div>
                </td>
                <td>${parseFloat(deal.amount_invested).toLocaleString()}</td>
                <td>
                  <span className={`status-badge status-${deal.status.toLowerCase()}`}>
                    {deal.status}
                  </span>
                </td>
                {canEdit && (
                  <td>
                    <button className="btn-delete" onClick={() => handleDeleteDeal(deal.id)}>Delete</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="empty-state">No investment deals found.</div>
      )}

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
        .add-deal-form h4 {
          margin-top: 0;
          margin-bottom: 1.5rem;
        }
        .status-badge {
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-size: 0.75rem;
          font-weight: 700;
        }
        .status-active { background: #d1ecf1; color: #0c5460; }
        .status-pending { background: #fff3cd; color: #856404; }
        .status-exited { background: #d4edda; color: #155724; }
        .btn-delete {
          background: none;
          border: none;
          color: #dc3545;
          cursor: pointer;
          font-weight: 600;
        }
        .btn-delete:hover { text-decoration: underline; }
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

export default DealsTab;
