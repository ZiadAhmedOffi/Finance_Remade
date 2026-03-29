import React, { useState, useEffect, useCallback } from "react";
import { fundsApi } from "../api/api";

interface Investor {
  id: string;
  email: string;
}

interface Fund {
  id: string;
  name: string;
}

interface InvestorAction {
  id: string;
  investor: string;
  investor_email: string;
  fund: string;
  fund_name: string;
  type: string;
  year: number;
  amount: string;
  original_value: string;
  exit_value: string;
  created_at: string;
}

const InvestorActionsAdmin: React.FC = () => {
  const [actions, setActions] = useState<InvestorAction[]>([]);
  const [investors, setInvestors] = useState<Investor[]>([]);
  const [funds, setFunds] = useState<Fund[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // Form state
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [type, setType] = useState<"CAPITAL_INVESTMENT" | "SECONDARY_EXIT">("CAPITAL_INVESTMENT");
  const [investorId, setInvestorId] = useState("");
  const [fundId, setFundId] = useState("");
  const [year, setYear] = useState(new Date().getFullYear());
  const [amount, setAmount] = useState("");
  const [originalValue, setOriginalValue] = useState("");
  const [exitValue, setExitValue] = useState("");

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [actionsRes, investorsRes, fundsRes] = await Promise.all([
        fundsApi.getInvestorActions(),
        fundsApi.getInvestors(),
        fundsApi.getFunds()
      ]);
      setActions(actionsRes.data);
      setInvestors(investorsRes.data);
      setFunds(fundsRes.data);
    } catch (err) {
      setError("Failed to fetch data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const resetForm = () => {
    setIsEditing(false);
    setEditingId(null);
    setAmount("");
    setOriginalValue("");
    setExitValue("");
    setType("CAPITAL_INVESTMENT");
    setInvestorId("");
    setFundId("");
    setYear(new Date().getFullYear());
    setMessage(null);
    setError(null);
  };

  const handleEdit = (action: InvestorAction) => {
    setIsEditing(true);
    setEditingId(action.id);
    setType(action.type as any);
    setInvestorId(action.investor);
    setFundId(action.fund);
    setYear(action.year);
    setAmount(action.amount || "");
    setOriginalValue(action.original_value || "");
    setExitValue(action.exit_value || "");
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this action?")) return;
    try {
      await fundsApi.deleteInvestorAction(id);
      setMessage("Investor action deleted successfully.");
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to delete action.");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const data: any = {
        type,
        investor: investorId,
        fund: fundId,
        year
      };
      if (type === "CAPITAL_INVESTMENT") {
        data.amount = amount;
        data.original_value = null;
        data.exit_value = null;
      } else {
        data.amount = null;
        data.original_value = originalValue;
        data.exit_value = exitValue;
      }

      if (isEditing && editingId) {
        await fundsApi.updateInvestorAction(editingId, data);
        setMessage("Investor action updated successfully.");
      } else {
        await fundsApi.createInvestorAction(data);
        setMessage("Investor action created successfully.");
      }
      
      fetchData();
      resetForm();
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to save action.");
    }
  };

  if (loading) return <div>Loading Investor Actions...</div>;

  return (
    <div className="investor-actions-admin">
      <section className="content-card" style={{ marginBottom: '2rem' }}>
        <h3>{isEditing ? "Edit Investor Action" : "Create Investor Action"}</h3>
        {message && <div className="alert alert-success">{message}</div>}
        {error && <div className="alert alert-error">{error}</div>}
        
        <form onSubmit={handleSubmit} className="action-form">
          <div className="form-grid">
            <div className="form-group">
              <label>Action Type</label>
              <select value={type} onChange={(e) => setType(e.target.value as any)}>
                <option value="CAPITAL_INVESTMENT">Capital Investment</option>
                <option value="SECONDARY_EXIT">Secondary Exit</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Investor</label>
              <select value={investorId} onChange={(e) => setInvestorId(e.target.value)} required>
                <option value="">-- Select Investor --</option>
                {investors.map(i => <option key={i.id} value={i.id}>{i.email}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label>Fund</label>
              <select value={fundId} onChange={(e) => setFundId(e.target.value)} required>
                <option value="">-- Select Fund --</option>
                {funds.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label>Year</label>
              <input type="number" value={year} onChange={(e) => setYear(parseInt(e.target.value))} required />
            </div>

            {type === "CAPITAL_INVESTMENT" ? (
              <div className="form-group">
                <label>Amount Invested (USD)</label>
                <input type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
              </div>
            ) : (
              <>
                <div className="form-group">
                  <label>Original Value (USD)</label>
                  <input type="number" step="0.01" value={originalValue} onChange={(e) => setOriginalValue(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Exit Value (USD)</label>
                  <input type="number" step="0.01" value={exitValue} onChange={(e) => setExitValue(e.target.value)} required />
                </div>
              </>
            )}
          </div>
          <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem' }}>
            <button type="submit" className="btn btn-primary">
              {isEditing ? "Update Action" : "Create Action"}
            </button>
            {isEditing && (
              <button type="button" className="btn btn-secondary" onClick={resetForm}>
                Cancel
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="content-card">
        <h3>Existing Actions</h3>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Investor</th>
                <th>Fund</th>
                <th>Type</th>
                <th>Year</th>
                <th>Amount/Value</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {actions.map(action => (
                <tr key={action.id}>
                  <td>{action.investor_email}</td>
                  <td>{action.fund_name}</td>
                  <td>{action.type === "CAPITAL_INVESTMENT" ? "Capital Investment" : "Secondary Exit"}</td>
                  <td>{action.year}</td>
                  <td>
                    {action.type === "CAPITAL_INVESTMENT" 
                      ? `$${parseFloat(action.amount).toLocaleString()}` 
                      : `Orig: $${parseFloat(action.original_value).toLocaleString()} | Exit: $${parseFloat(action.exit_value).toLocaleString()}`}
                  </td>
                  <td className="actions">
                    <button onClick={() => handleEdit(action)} className="btn btn-primary btn-sm">Edit</button>
                    <button onClick={() => handleDelete(action.id)} className="btn btn-deactivate btn-sm">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default InvestorActionsAdmin;
