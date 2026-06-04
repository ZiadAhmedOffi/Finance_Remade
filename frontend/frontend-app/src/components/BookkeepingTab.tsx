import React, { useState, useEffect, useCallback } from "react";
import { realEstateApi } from "../api/api";
import "./BookkeepingTab.css";

interface LedgerYear {
  id: string;
  year: number;
  is_closed: boolean;
  closed_at: string | null;
  closed_by_email: string | null;
}

interface TrialBalanceAccount {
  account_id: string;
  account_name: string;
  account_type: string;
  debit: string;
  credit: string;
  net_balance: string;
}

interface TrialBalance {
  year: number;
  is_closed: boolean;
  accounts: TrialBalanceAccount[];
  total_debit: number;
  total_credit: number;
  is_balanced: boolean;
}

interface TAccountEntry {
  id: string;
  transaction_id: string;
  date: string;
  description: string;
  amount: string;
}

interface TAccountDetails {
  account_name: string;
  account_type: string;
  debits: TAccountEntry[];
  credits: TAccountEntry[];
  total_debit: number;
  total_credit: number;
}

interface BookkeepingTabProps {
  portfolioId: string;
  canEdit: boolean;
  isAdmin?: boolean;
}

const formatCurrency = (val: number) => 
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);

const BookkeepingTab: React.FC<BookkeepingTabProps> = ({ portfolioId, canEdit, isAdmin }) => {
  const [ledgerYears, setLedgerYears] = useState<LedgerYear[]>([]);
  const [selectedYear, setSelectedYear] = useState<LedgerYear | null>(null);
  const [trialBalance, setTrialBalance] = useState<TrialBalance | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<TAccountDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAddTransaction, setShowAddTransaction] = useState(false);

  const fetchLedgers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await realEstateApi.getLedgers(portfolioId);
      setLedgerYears(response.data);
      if (response.data.length > 0 && !selectedYear) {
        setSelectedYear(response.data[0]);
      }
    } catch (err) {
      setError("Failed to fetch ledger years.");
    } finally {
      setLoading(false);
    }
  }, [portfolioId, selectedYear]);

  const fetchTrialBalance = useCallback(async (yearId: string) => {
    try {
      setLoading(true);
      const response = await realEstateApi.getTrialBalance(portfolioId, yearId);
      setTrialBalance(response.data);
    } catch (err) {
      setError("Failed to fetch trial balance.");
    } finally {
      setLoading(false);
    }
  }, [portfolioId]);

  useEffect(() => {
    fetchLedgers();
  }, [fetchLedgers]);

  useEffect(() => {
    if (selectedYear) {
      fetchTrialBalance(selectedYear.id);
    }
  }, [selectedYear, fetchTrialBalance]);

  const handleInitialize = async () => {
    const year = prompt("Enter year to initialize (e.g. 2024):");
    if (!year) return;
    try {
      setLoading(true);
      await realEstateApi.initializeLedger(portfolioId, parseInt(year));
      fetchLedgers();
    } catch (err: any) {
      alert(err.response?.data?.error || "Failed to initialize ledger.");
    } finally {
      setLoading(false);
    }
  };

  const handleAccountClick = async (accountId: string) => {
    if (!selectedYear) return;
    try {
      setLoading(true);
      const response = await realEstateApi.getTAccount(portfolioId, selectedYear.id, accountId);
      setSelectedAccount(response.data);
    } catch (err) {
      alert("Failed to fetch T-account details.");
    } finally {
      setLoading(false);
    }
  };

  const handleCloseYear = async () => {
    if (!selectedYear || !window.confirm(`Are you sure you want to close the fiscal year ${selectedYear.year}? This will zero out income/expenses and carry forward balances.`)) return;
    try {
      setLoading(true);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteYear = async () => {
    if (!selectedYear || !isAdmin) return;
    if (!window.confirm(`DANGER: Are you sure you want to PERMANENTLY DELETE the fiscal year ${selectedYear.year}? All transactions and entries for this year will be lost. This cannot be undone.`)) return;
    
    try {
      setLoading(true);
      await realEstateApi.deleteLedger(portfolioId, selectedYear.id);
      const remainingYears = ledgerYears.filter(y => y.id !== selectedYear.id);
      setLedgerYears(remainingYears);
      setSelectedYear(remainingYears.length > 0 ? remainingYears[0] : null);
      if (remainingYears.length === 0) setTrialBalance(null);
    } catch (err: any) {
      alert(err.response?.data?.error || "Failed to delete year.");
    } finally {
      setLoading(false);
    }
  };

  if (loading && ledgerYears.length === 0) return <div>Loading bookkeeping...</div>;

  return (
    <div className="bookkeeping-container">
      <div className="bookkeeping-header">
        <h2>Bookkeeping & T-Balance</h2>
        <div className="ledger-actions">
          <select 
            value={selectedYear?.id || ""} 
            onChange={(e) => setSelectedYear(ledgerYears.find(y => y.id === e.target.value) || null)}
          >
            {ledgerYears.map(y => (
              <option key={y.id} value={y.id}>{y.year} {y.is_closed ? "(Closed)" : "(Open)"}</option>
            ))}
          </select>
          {canEdit && (
            <button className="btn-secondary" onClick={handleInitialize}>
              Initialize New Year
            </button>
          )}
          {isAdmin && selectedYear && (
            <button className="btn-delete-ledger" onClick={handleDeleteYear}>
              <span style={{ fontSize: '1rem' }}>🗑️</span> Delete Year
            </button>
          )}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {trialBalance ? (
        <div className="trial-balance-section">
          <div className="section-header">
            <h3>Trial Balance - {trialBalance.year}</h3>
            {!trialBalance.is_closed && canEdit && (
              <div className="action-buttons">
                <button className="btn-secondary" onClick={async () => {
                  if (window.confirm("Sync projected Rent, Opex, and Taxes for this year?")) {
                    try {
                      setLoading(true);
                      await realEstateApi.syncCashFlow(portfolioId, selectedYear!.id);
                      fetchTrialBalance(selectedYear!.id);
                    } catch (err: any) {
                      alert(err.response?.data?.error || "Failed to sync cash flow.");
                    } finally {
                      setLoading(false);
                    }
                  }
                }}>
                  🔄 Sync Cash Flow
                </button>
                <button className="btn-primary" onClick={() => setShowAddTransaction(true)}>
                  + Add Transaction
                </button>
                <button className="btn-danger" onClick={handleCloseYear}>
                  🔒 Close Year
                </button>
              </div>
            )}
          </div>

          <table className="data-table tb-table">
            <thead>
              <tr>
                <th>Account</th>
                <th>Type</th>
                <th>Debit</th>
                <th>Credit</th>
                <th>Net Balance</th>
              </tr>
            </thead>
            <tbody>
              {trialBalance.accounts.map(acc => (
                <tr key={acc.account_id} onClick={() => handleAccountClick(acc.account_id)} className="clickable-row">
                  <td>{acc.account_name}</td>
                  <td><span className={`type-badge ${acc.account_type.toLowerCase()}`}>{acc.account_type}</span></td>
                  <td className="amount">{acc.debit !== "0.00" ? `$${parseFloat(acc.debit).toLocaleString()}` : "-"}</td>
                  <td className="amount">{acc.credit !== "0.00" ? `$${parseFloat(acc.credit).toLocaleString()}` : "-"}</td>
                  <td className="amount bold">
                    ${parseFloat(acc.net_balance).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className={trialBalance.is_balanced ? "balanced-row" : "unbalanced-row"}>
                <td colSpan={2}>Total</td>
                <td className="amount bold">${trialBalance.total_debit.toLocaleString()}</td>
                <td className="amount bold">${trialBalance.total_credit.toLocaleString()}</td>
                <td>
                  {trialBalance.is_balanced ? 
                    <span className="status-ok">✅ Balanced</span> : 
                    <span className="status-error">⚠️ Unbalanced</span>
                  }
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <p>No ledger initialized for this portfolio yet.</p>
          {canEdit && <button className="btn-primary" onClick={handleInitialize}>Initialize Ledger</button>}
        </div>
      )}

      {selectedAccount && (
        <div className="modal-overlay" onClick={() => setSelectedAccount(null)}>
          <div className="modal-content t-account-modal" onClick={e => e.stopPropagation()}>
            <header className="modal-header">
              <h3>T-Account: {selectedAccount.account_name}</h3>
              <button className="close-button" onClick={() => setSelectedAccount(null)}>&times;</button>
            </header>
            
            <div className="t-account-view">
              <div className="t-column debit-column">
                <h4>Debit</h4>
                <div className="entry-list">
                  {selectedAccount.debits.map(e => (
                    <div key={e.id} className="entry-item">
                      <span className="entry-date">{e.date}</span>
                      <span className="entry-desc" title={e.description}>{e.description}</span>
                      <span className="entry-amount">{formatCurrency(parseFloat(e.amount))}</span>
                    </div>
                  ))}
                  {selectedAccount.debits.length === 0 && <p className="muted">No debit entries</p>}
                </div>
                <div className="column-total">
                  Total Dr: {formatCurrency(selectedAccount.total_debit)}
                </div>
              </div>
              
              <div className="t-column credit-column">
                <h4>Credit</h4>
                <div className="entry-list">
                  {selectedAccount.credits.map(e => (
                    <div key={e.id} className="entry-item">
                      <span className="entry-date">{e.date}</span>
                      <span className="entry-desc" title={e.description}>{e.description}</span>
                      <span className="entry-amount">{formatCurrency(parseFloat(e.amount))}</span>
                    </div>
                  ))}
                  {selectedAccount.credits.length === 0 && <p className="muted">No credit entries</p>}
                </div>
                <div className="column-total">
                  Total Cr: {formatCurrency(selectedAccount.total_credit)}
                </div>
              </div>
            </div>
            
            <div className="t-account-footer" style={{ borderTop: '2px solid #1e293b', marginTop: 0 }}>
              <strong>Net Balance: { formatCurrency(Math.abs(selectedAccount.total_debit - selectedAccount.total_credit)) } { (selectedAccount.total_debit > selectedAccount.total_credit ? 'Dr' : 'Cr') }</strong>
            </div>
          </div>
        </div>
      )}

      {showAddTransaction && selectedYear && (
        <ManualTransactionModal 
          portfolioId={portfolioId}
          ledgerYear={selectedYear}
          onClose={() => setShowAddTransaction(false)}
          onSuccess={() => {
            setShowAddTransaction(false);
            fetchTrialBalance(selectedYear.id);
          }}
          accounts={trialBalance?.accounts || []}
        />
      )}
    </div>
  );
};

interface ManualTransactionModalProps {
  portfolioId: string;
  ledgerYear: LedgerYear;
  onClose: () => void;
  onSuccess: () => void;
  accounts: TrialBalanceAccount[];
}

const ManualTransactionModal: React.FC<ManualTransactionModalProps> = ({ 
  portfolioId, ledgerYear, onClose, onSuccess, accounts 
}) => {
  const [description, setDescription] = useState("");
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [entries, setEntries] = useState<{account_id: string, amount: string, entry_type: "DEBIT" | "CREDIT"}[]>([
    { account_id: "", amount: "", entry_type: "DEBIT" },
    { account_id: "", amount: "", entry_type: "CREDIT" }
  ]);
  const [templates, setTemplates] = useState<any[]>([]);

  useEffect(() => {
    realEstateApi.getTransactionTemplates(portfolioId).then(res => setTemplates(res.data));
  }, [portfolioId]);

  const handleAddEntry = () => {
    setEntries([...entries, { account_id: "", amount: "", entry_type: "DEBIT" }]);
  };

  const handleRemoveEntry = (index: number) => {
    setEntries(entries.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    const debitTotal = entries.filter(e => e.entry_type === "DEBIT").reduce((sum, e) => sum + parseFloat(e.amount || "0"), 0);
    const creditTotal = entries.filter(e => e.entry_type === "CREDIT").reduce((sum, e) => sum + parseFloat(e.amount || "0"), 0);
    
    if (Math.abs(debitTotal - creditTotal) > 0.01) {
      alert(`Transaction is not balanced! Debits: ${debitTotal}, Credits: ${creditTotal}`);
      return;
    }

    try {
      await realEstateApi.createManualTransaction(portfolioId, ledgerYear.id, {
        description,
        date,
        entries
      });
      onSuccess();
    } catch (err: any) {
      alert(err.response?.data?.error || "Failed to create transaction.");
    }
  };

  const applyTemplate = (template: any) => {
    setDescription(template.name);
    setEntries(template.entries.map((e: any) => ({
      account_id: e.account_id || "",
      amount: "",
      entry_type: e.entry_type
    })));
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content transaction-modal" onClick={e => e.stopPropagation()}>
        <header className="modal-header">
          <h3>Add Manual Transaction - {ledgerYear.year}</h3>
          <button className="close-button" onClick={onClose}>&times;</button>
        </header>

        <div className="template-bar">
          <span>Popular Options:</span>
          {templates.map((t, i) => (
            <button key={i} className="btn-template" onClick={() => applyTemplate(t)}>{t.name}</button>
          ))}
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Description</label>
            <input 
              type="text" 
              value={description} 
              onChange={e => setDescription(e.target.value)} 
              required 
              placeholder="e.g. Annual Maintenance Fee"
            />
          </div>
          <div className="form-group">
            <label>Date</label>
            <input 
              type="date" 
              value={date} 
              onChange={e => setDate(e.target.value)} 
              required 
              min={`${ledgerYear.year}-01-01`}
              max={`${ledgerYear.year}-12-31`}
            />
          </div>

          <div className="entries-section">
            <div className="flex justify-between items-center mb-2">
              <label className="m-0">Transaction Entries</label>
              <div className="flex gap-4 text-xs font-bold">
                <span className="text-blue-600">Total Debit: {formatCurrency(entries.filter(e => e.entry_type === "DEBIT").reduce((sum, e) => sum + parseFloat(e.amount || "0"), 0))}</span>
                <span className="text-emerald-600">Total Credit: {formatCurrency(entries.filter(e => e.entry_type === "CREDIT").reduce((sum, e) => sum + parseFloat(e.amount || "0"), 0))}</span>
              </div>
            </div>
            
            <div className="entry-row-header" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1.2fr auto', gap: '0.75rem', padding: '0 0.5rem', marginBottom: '0.5rem' }}>
               <span style={{ fontSize: '0.65rem', fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase' }}>Account</span>
               <span style={{ fontSize: '0.65rem', fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase' }}>Type</span>
               <span style={{ fontSize: '0.65rem', fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase' }}>Amount ($)</span>
               <span></span>
            </div>

            {entries.map((entry, index) => (
              <div key={index} className="entry-row">
                <select 
                  value={entry.account_id} 
                  onChange={e => {
                    const newEntries = [...entries];
                    newEntries[index].account_id = e.target.value;
                    setEntries(newEntries);
                  }}
                  required
                >
                  <option value="">Select Account</option>
                  {accounts.map(acc => (
                    <option key={acc.account_id} value={acc.account_id}>{acc.account_name}</option>
                  ))}
                </select>
                <select 
                  value={entry.entry_type} 
                  onChange={e => {
                    const newEntries = [...entries];
                    newEntries[index].entry_type = e.target.value as any;
                    setEntries(newEntries);
                  }}
                  style={{ 
                    color: entry.entry_type === "DEBIT" ? "#2563eb" : "#059669",
                    fontWeight: 'bold',
                    background: entry.entry_type === "DEBIT" ? "#eff6ff" : "#ecfdf5"
                  }}
                >
                  <option value="DEBIT">Debit</option>
                  <option value="CREDIT">Credit</option>
                </select>
                <input 
                  type="number" 
                  step="0.01" 
                  value={entry.amount} 
                  onChange={e => {
                    const newEntries = [...entries];
                    newEntries[index].amount = e.target.value;
                    setEntries(newEntries);
                  }}
                  placeholder="0.00"
                  required
                  style={{ fontFamily: 'JetBrains Mono, monospace' }}
                />
                <button type="button" className="btn-remove" onClick={() => handleRemoveEntry(index)} title="Remove Line">&times;</button>
              </div>
            ))}
            <button type="button" className="btn-add-entry" onClick={handleAddEntry}>+ Add New Entry Line</button>
          </div>

          <div className="modal-footer" style={{ borderTop: '1px solid #e2e8f0', paddingTop: '1.5rem', marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="balance-status">
              {(() => {
                const d = entries.filter(e => e.entry_type === "DEBIT").reduce((sum, e) => sum + parseFloat(e.amount || "0"), 0);
                const c = entries.filter(e => e.entry_type === "CREDIT").reduce((sum, e) => sum + parseFloat(e.amount || "0"), 0);
                const balanced = Math.abs(d - c) < 0.01;
                return (
                  <span style={{ 
                    fontSize: '0.85rem', 
                    fontWeight: 700, 
                    color: balanced ? '#059669' : '#dc2626',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem'
                  }}>
                    {balanced ? '✅ Ledger Balanced' : `⚠️ Unbalanced: ${formatCurrency(Math.abs(d-c))} diff`}
                  </span>
                );
              })()}
            </div>
            <div className="flex gap-3">
              <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
              <button type="submit" className="btn-primary">Save Transaction</button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default BookkeepingTab;
