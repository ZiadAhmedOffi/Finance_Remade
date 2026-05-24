import React, { useState, useEffect } from "react";
import { realEstateApi } from "../api/api";

interface Jurisdiction {
  id: string;
  name: string;
  currency: string;
  rules_count: number;
}

interface TaxRule {
  id: string;
  jurisdiction: string;
  name: string;
  event_type: string;
  trigger: string;
  tax_base: string;
  rate: string;
  valuation_ratio: string;
  revaluation_freq: number;
  deductibility_cap: string;
  lcf_limit: number | null;
  responsible_party: string;
  is_active: boolean;
}

interface Portfolio {
  id: string;
  name: string;
  jurisdiction?: string;
  jurisdiction_name?: string;
}

const TaxationManagementTab: React.FC<{ portfolio: Portfolio; onUpdate: () => void; canEdit: boolean }> = ({ portfolio, onUpdate, canEdit }) => {
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [selectedJurisdictionId, setSelectedJurisdictionId] = useState<string | null>(portfolio.jurisdiction || null);
  const [taxRules, setTaxRules] = useState<TaxRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showJurModal, setShowJurModal] = useState(false);
  const [showRuleModal, setShowRuleModal] = useState(false);
  
  const [newJur, setNewJur] = useState({ name: "", currency: "USD" });
  const [editingJur, setEditingJur] = useState<Jurisdiction | null>(null);

  const [newRule, setNewRule] = useState<Partial<TaxRule>>({
    name: "",
    event_type: "OWNERSHIP",
    trigger: "ANNUAL",
    tax_base: "MARKET_VALUE",
    rate: "0.01",
    valuation_ratio: "1.00",
    revaluation_freq: 1,
    responsible_party: "BOTH",
    is_active: true
  });
  const [editingRule, setEditingRule] = useState<TaxRule | null>(null);

  useEffect(() => {
    fetchJurisdictions();
  }, []);

  useEffect(() => {
    if (selectedJurisdictionId) {
      fetchTaxRules(selectedJurisdictionId);
    } else {
      setTaxRules([]);
    }
  }, [selectedJurisdictionId]);

  const fetchJurisdictions = async () => {
    try {
      setLoading(true);
      const res = await realEstateApi.getJurisdictions();
      setJurisdictions(res.data);
    } catch (err) {
      console.error("Failed to fetch jurisdictions", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTaxRules = async (jurId: string) => {
    try {
      const res = await realEstateApi.getTaxRules(jurId);
      setTaxRules(res.data);
    } catch (err) {
      console.error("Failed to fetch tax rules", err);
    }
  };

  const handleLinkJurisdiction = async (jurId: string) => {
    try {
      setSaving(true);
      await realEstateApi.updatePortfolio(portfolio.id, { jurisdiction: jurId });
      setSelectedJurisdictionId(jurId);
      onUpdate();
    } catch (err) {
      alert("Failed to link jurisdiction");
    } finally {
      setSaving(false);
    }
  };

  const handleCreateJurisdiction = async () => {
    try {
      setSaving(true);
      await realEstateApi.createJurisdiction(newJur);
      fetchJurisdictions();
      setShowJurModal(false);
      setNewJur({ name: "", currency: "USD" });
    } catch (err) {
      alert("Failed to create jurisdiction");
    } finally {
      setSaving(false);
    }
  };

  const handleCreateRule = async () => {
    if (!selectedJurisdictionId) return;
    try {
      setSaving(true);
      await realEstateApi.createTaxRule({ ...newRule, jurisdiction: selectedJurisdictionId });
      fetchTaxRules(selectedJurisdictionId);
      setShowRuleModal(false);
    } catch (err) {
      alert("Failed to create tax rule");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRule = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this rule?")) return;
    try {
      await realEstateApi.deleteTaxRule(id);
      if (selectedJurisdictionId) fetchTaxRules(selectedJurisdictionId);
    } catch (err) {
      alert("Failed to delete rule");
    }
  };

  return (
    <div className="taxation-management">
      <style>{`
        .taxation-management {
          padding: 1.5rem;
          color: #334155;
        }
        .management-card {
          background: white;
          border-radius: 12px;
          padding: 1.5rem;
          margin-bottom: 2rem;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .management-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          border-bottom: 1px solid #f1f5f9;
          padding-bottom: 1rem;
        }
        .management-header h2 {
          margin: 0;
          font-size: 1.25rem;
          font-weight: 700;
        }
        .jurisdiction-selector {
          display: flex;
          gap: 1rem;
          align-items: center;
        }
        .tax-table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 1rem;
        }
        .tax-table th, .tax-table td {
          text-align: left;
          padding: 0.75rem;
          border-bottom: 1px solid #f1f5f9;
        }
        .tax-table th {
          font-weight: 600;
          color: #64748b;
          font-size: 0.875rem;
        }
        .badge {
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-size: 0.75rem;
          font-weight: 600;
        }
        .badge-info { background: #e0f2fe; color: #0369a1; }
        .badge-success { background: #dcfce7; color: #15803d; }
        .modal-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0,0,0,0.5);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 1000;
        }
        .modal-content {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          width: 100%;
          max-width: 500px;
        }
        .form-group {
          margin-bottom: 1rem;
        }
        .form-group label {
          display: block;
          margin-bottom: 0.5rem;
          font-weight: 600;
          font-size: 0.875rem;
        }
        .form-group input, .form-group select {
          width: 100%;
          padding: 0.625rem;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
        }
      `}</style>

      {/* 1. Link Jurisdiction Section */}
      <div className="management-card">
        <div className="management-header">
          <h2>Portfolio Jurisdiction</h2>
        </div>
        <div className="jurisdiction-selector">
          <div style={{ flex: 1 }}>
            <p style={{ margin: "0 0 0.5rem 0", fontSize: "0.875rem", color: "#64748b" }}>
              Current: <strong>{portfolio.jurisdiction_name || "None Linked"}</strong>
            </p>
            <select 
              className="form-control"
              value={selectedJurisdictionId || ""}
              onChange={(e) => setSelectedJurisdictionId(e.target.value)}
              disabled={!canEdit}
            >
              <option value="">-- Select a Jurisdiction --</option>
              {jurisdictions.map(j => (
                <option key={j.id} value={j.id}>{j.name} ({j.currency})</option>
              ))}
            </select>
          </div>
          {canEdit && selectedJurisdictionId !== portfolio.jurisdiction && (
            <button 
              className="btn btn-primary" 
              onClick={() => handleLinkJurisdiction(selectedJurisdictionId!)}
              disabled={saving}
            >
              {saving ? "Linking..." : "Link to Portfolio"}
            </button>
          )}
          {canEdit && (
            <button className="btn btn-outline" onClick={() => setShowJurModal(true)}>
              + Create New Jurisdiction
            </button>
          )}
        </div>
      </div>

      {/* 2. Tax Rules Section */}
      {selectedJurisdictionId && (
        <div className="management-card">
          <div className="management-header">
            <h2>Tax Rules for {jurisdictions.find(j => j.id === selectedJurisdictionId)?.name}</h2>
            {canEdit && (
              <button className="btn btn-primary btn-sm" onClick={() => setShowRuleModal(true)}>
                + Add Rule
              </button>
            )}
          </div>
          
          {taxRules.length === 0 ? (
            <p style={{ textAlign: "center", padding: "2rem", color: "#94a3b8" }}>
              No tax rules defined for this jurisdiction.
            </p>
          ) : (
            <table className="tax-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Trigger</th>
                  <th>Base</th>
                  <th>Rate (%)</th>
                  <th>Responsible</th>
                  {canEdit && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {taxRules.map(rule => (
                  <tr key={rule.id}>
                    <td><strong>{rule.name}</strong></td>
                    <td><span className="badge badge-info">{rule.event_type}</span></td>
                    <td>{rule.trigger}</td>
                    <td>{rule.tax_base}</td>
                    <td>{(parseFloat(rule.rate) * 100).toFixed(2)}%</td>
                    <td>{rule.responsible_party}</td>
                    {canEdit && (
                      <td>
                        <button 
                          className="btn btn-sm btn-outline" 
                          style={{ color: "#ef4444", borderColor: "#ef4444" }}
                          onClick={() => handleDeleteRule(rule.id)}
                        >
                          Delete
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Jurisdiction Modal */}
      {showJurModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Create New Jurisdiction</h3>
            <div className="form-group">
              <label>Name</label>
              <input 
                type="text" 
                value={newJur.name} 
                onChange={e => setNewJur({ ...newJur, name: e.target.value })}
                placeholder="e.g. United Kingdom"
              />
            </div>
            <div className="form-group">
              <label>Currency</label>
              <input 
                type="text" 
                value={newJur.currency} 
                onChange={e => setNewJur({ ...newJur, currency: e.target.value })}
                placeholder="e.g. GBP"
              />
            </div>
            <div style={{ display: "flex", gap: "1rem", marginTop: "2rem" }}>
              <button className="btn btn-primary" onClick={handleCreateJurisdiction} disabled={saving}>
                Create
              </button>
              <button className="btn btn-outline" onClick={() => setShowJurModal(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tax Rule Modal */}
      {showRuleModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: "600px" }}>
            <h3>Add New Tax Rule</h3>
            <div className="form-group">
              <label>Rule Name</label>
              <input 
                type="text" 
                value={newRule.name} 
                onChange={e => setNewRule({ ...newRule, name: e.target.value })}
                placeholder="e.g. Annual Property Tax"
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              <div className="form-group">
                <label>Event Type</label>
                <select value={newRule.event_type} onChange={e => setNewRule({ ...newRule, event_type: e.target.value })}>
                  <option value="ACQUISITION">Acquisition</option>
                  <option value="OWNERSHIP">Ownership</option>
                  <option value="INCOME">Income</option>
                  <option value="DISPOSAL">Disposal</option>
                  <option value="FINANCING">Financing</option>
                </select>
              </div>
              <div className="form-group">
                <label>Trigger</label>
                <select value={newRule.trigger} onChange={e => setNewRule({ ...newRule, trigger: e.target.value })}>
                  <option value="ANNUAL">Annual</option>
                  <option value="CONTRACT_SIGNING">Contract Signing</option>
                  <option value="ON_PAYMENT">On Payment</option>
                  <option value="HANDOVER">Handover</option>
                  <option value="DISPOSAL">Disposal</option>
                </select>
              </div>
              <div className="form-group">
                <label>Tax Base</label>
                <select value={newRule.tax_base} onChange={e => setNewRule({ ...newRule, tax_base: e.target.value })}>
                  <option value="MARKET_VALUE">Market Value</option>
                  <option value="ASSESSED_VALUE">Assessed Value</option>
                  <option value="NET_INCOME">Net Income</option>
                  <option value="LOAN_AMOUNT">Loan Amount</option>
                  <option value="FIXED">Fixed Amount</option>
                </select>
              </div>
              <div className="form-group">
                <label>Tax Rate (Decimal, e.g. 0.05)</label>
                <input 
                  type="number" step="0.0001"
                  value={newRule.rate} 
                  onChange={e => setNewRule({ ...newRule, rate: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Responsible Party</label>
                <select value={newRule.responsible_party} onChange={e => setNewRule({ ...newRule, responsible_party: e.target.value })}>
                  <option value="BOTH">Both / NA</option>
                  <option value="BARE_OWNER">Bare Owner</option>
                  <option value="USUFRUCT_HOLDER">Usufruct Holder</option>
                </select>
              </div>
              <div className="form-group">
                <label>Valuation Ratio (e.g. 0.8 for 80%)</label>
                <input 
                  type="number" step="0.01"
                  value={newRule.valuation_ratio} 
                  onChange={e => setNewRule({ ...newRule, valuation_ratio: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Revaluation Frequency (Years)</label>
                <input 
                  type="number"
                  value={newRule.revaluation_freq} 
                  onChange={e => setNewRule({ ...newRule, revaluation_freq: parseInt(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label>LCF Limit (Years, optional)</label>
                <input 
                  type="number"
                  value={newRule.lcf_limit || ""} 
                  onChange={e => setNewRule({ ...newRule, lcf_limit: e.target.value ? parseInt(e.target.value) : null })}
                />
              </div>
            </div>
            
            <div style={{ display: "flex", gap: "1rem", marginTop: "2rem" }}>
              <button className="btn btn-primary" onClick={handleCreateRule} disabled={saving}>
                Create Rule
              </button>
              <button className="btn btn-outline" onClick={() => setShowRuleModal(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaxationManagementTab;
