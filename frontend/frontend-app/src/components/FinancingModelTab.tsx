import React, { useState, useEffect } from "react";
import { realEstateApi } from "../api/api";

interface FinancingEntry {
  id: string;
  property: string;
  property_name: string;
  purchase_price: string;
  loan_amount: string;
  base_interest_rate: string;
  tenor: number;
  payments_per_year: number;
  loan_start_date: string;
}

interface FinancingMetrics {
  ltv: number;
  effective_rate: number;
  periodic_payment: number;
  annual_debt_service: number;
  total_interest: number;
}

interface FinancingWithMetrics {
  entry: FinancingEntry;
  metrics: FinancingMetrics;
}

interface AmortizationRow {
  period?: number;
  date?: string;
  beginning_balance?: number;
  periodic_payment: number;
  principal_payment: number;
  interest_payment: number;
  ending_balance?: number;
}

const FinancingModelTab: React.FC<{ portfolioId: string; canEdit: boolean }> = ({ portfolioId, canEdit }) => {
  const [entries, setEntries] = useState<FinancingWithMetrics[]>([]);
  const [properties, setProperties] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState<FinancingEntry | null>(null);
  
  // Visibility toggles
  const [showEntriesTable, setShowEntriesTable] = useState(true);
  const [showAmortization, setShowAmortization] = useState(true);
  
  // Pagination
  const [entriesPage, setEntriesPage] = useState(1);
  const [amortPage, setAmortPage] = useState(1);
  const itemsPerPage = 10;
  
  // Amortization state
  const [selectedEntryId, setSelectedEntryId] = useState<string>("total");
  const [amortizationSchedule, setAmortizationSchedule] = useState<AmortizationRow[]>([]);
  const [amortLoading, setAmortLoading] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    property: "",
    loan_amount: "",
    base_interest_rate: "",
    tenor: "",
    payments_per_year: "12",
    loan_start_date: "",
  });

  useEffect(() => {
    fetchData();
  }, [portfolioId]);

  useEffect(() => {
    fetchAmortization();
  }, [selectedEntryId, entries]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [finResponse, propResponse] = await Promise.all([
        realEstateApi.getFinancing(portfolioId),
        realEstateApi.getProperties(portfolioId),
      ]);
      setEntries(finResponse.data);
      setProperties(propResponse.data.map((p: any) => p.property));
    } catch (err) {
      console.error("Failed to fetch financing data", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAmortization = async () => {
    if (!portfolioId) return;
    try {
      setAmortLoading(true);
      let response;
      if (selectedEntryId === "total") {
        response = await realEstateApi.getPortfolioAmortization(portfolioId);
      } else {
        response = await realEstateApi.getEntryAmortization(portfolioId, selectedEntryId);
      }
      setAmortizationSchedule(response.data);
      setAmortPage(1); // Reset to first page when changing selection
    } catch (err) {
      console.error("Failed to fetch amortization schedule", err);
    } finally {
      setAmortLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingEntry) {
        await realEstateApi.updateFinancing(portfolioId, editingEntry.id, formData);
      } else {
        await realEstateApi.createFinancing(portfolioId, formData);
      }
      setShowModal(false);
      resetForm();
      fetchData();
    } catch (err: any) {
      console.error("Failed to save financing entry", err);
      alert(err.response?.data?.error || "Failed to save financing entry. Please check your inputs.");
    }
  };

  const resetForm = () => {
    setFormData({
      property: "",
      loan_amount: "",
      base_interest_rate: "",
      tenor: "",
      payments_per_year: "12",
      loan_start_date: "",
    });
    setEditingEntry(null);
  };

  const handleAddEntry = () => {
    resetForm();
    setShowModal(true);
  };

  const handleEdit = (entry: FinancingEntry) => {
    setEditingEntry(entry);
    setFormData({
      property: entry.property,
      loan_amount: entry.loan_amount,
      base_interest_rate: entry.base_interest_rate,
      tenor: entry.tenor.toString(),
      payments_per_year: entry.payments_per_year.toString(),
      loan_start_date: entry.loan_start_date,
    });
    setShowModal(true);
  };

  const handleDelete = async (entryId: string) => {
    if (window.confirm("Are you sure you want to delete this financing entry?")) {
      try {
        await realEstateApi.deleteFinancing(portfolioId, entryId);
        fetchData();
      } catch (err) {
        console.error("Failed to delete financing entry", err);
      }
    }
  };

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);
  };

  const formatPercent = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return num.toFixed(2) + "%";
  };

  // Pagination logic
  const paginatedEntries = entries.slice((entriesPage - 1) * itemsPerPage, entriesPage * itemsPerPage);
  const totalEntriesPages = Math.ceil(entries.length / itemsPerPage);

  const paginatedAmort = amortizationSchedule.slice((amortPage - 1) * itemsPerPage, amortPage * itemsPerPage);
  const totalAmortPages = Math.ceil(amortizationSchedule.length / itemsPerPage);

  // Filter properties that don't have financing yet and are not ALL_CASH
  const availableProperties = properties.filter(p => 
    p.financing_type !== "ALL_CASH" && 
    (!entries.some(e => e.entry.property === p.id) || (editingEntry && editingEntry.property === p.id))
  );

  return (
    <div className="financing-model-container">
      <style>{`
        .financing-model-container { padding: 1rem; }
        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
          background: #f8fafc;
          padding: 0.75rem 1rem;
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.2s;
        }
        .section-header:hover { background: #f1f5f9; }
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
          margin-bottom: 1.5rem;
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
        .data-table th {
          background: #f8fafc;
          font-weight: 600;
          color: #475569;
        }
        .data-table tr:hover { background: #f1f5f9; }
        .pagination {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 1rem;
          padding: 1rem;
          background: white;
          border-top: 1px solid #e2e8f0;
        }
        .btn-pagination {
          padding: 0.25rem 0.75rem;
          border: 1px solid #cbd5e1;
          background: white;
          border-radius: 4px;
          cursor: pointer;
        }
        .btn-pagination:disabled { opacity: 0.5; cursor: not-allowed; }
        .ltv-warning { color: #ef4444; font-weight: 700; }
        .amortization-controls {
          display: flex;
          gap: 1rem;
          align-items: center;
          margin-bottom: 1rem;
        }
        .select-input {
          padding: 0.5rem;
          border: 1px solid #cbd5e1;
          border-radius: 4px;
          background: white;
        }
      `}</style>

      {/* Section 1: Financing Entries */}
      <div className="section">
        <div className="section-header" onClick={() => setShowEntriesTable(!showEntriesTable)}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ transform: showEntriesTable ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>▶</span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1e293b', margin: 0 }}>Financing Entries</h2>
          </div>
          {canEdit && (
            <button className="btn btn-primary" onClick={(e) => { e.stopPropagation(); handleAddEntry(); }}>
              + Add Entry
            </button>
          )}
        </div>
        
        <div className={`section-content ${showEntriesTable ? '' : 'collapsed'}`}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>Loading entries...</div>
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Property Name</th>
                    <th>Loan Amount</th>
                    <th>LTV</th>
                    <th>Base Rate</th>
                    <th>Effective Rate</th>
                    <th>Tenor (yrs)</th>
                    <th>Pmts/Year</th>
                    <th>Periodic Pmt</th>
                    <th>Annual Debt Service</th>
                    <th>Total Interest</th>
                    {canEdit && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {paginatedEntries.map(({ entry, metrics }) => (
                    <tr key={entry.id}>
                      <td style={{ fontWeight: 600 }}>{entry.property_name}</td>
                      <td>{formatCurrency(entry.loan_amount)}</td>
                      <td className={metrics.ltv > 100 ? "ltv-warning" : ""}>
                        {formatPercent(metrics.ltv)}
                      </td>
                      <td>{formatPercent(entry.base_interest_rate)}</td>
                      <td>{formatPercent(metrics.effective_rate)}</td>
                      <td>{entry.tenor}</td>
                      <td>{entry.payments_per_year}</td>
                      <td>{formatCurrency(metrics.periodic_payment)}</td>
                      <td>{formatCurrency(metrics.annual_debt_service)}</td>
                      <td>{formatCurrency(metrics.total_interest)}</td>
                      {canEdit && (
                        <td>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button className="btn btn-secondary btn-sm" onClick={() => handleEdit(entry)}>Edit</button>
                            <button 
                              className="btn-sm" 
                              style={{ background: '#fee2e2', color: '#991b1b', border: '1px solid #fecaca', cursor: 'pointer', borderRadius: '4px' }}
                              onClick={() => handleDelete(entry.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                  {entries.length === 0 && (
                    <tr><td colSpan={canEdit ? 11 : 10} style={{ textAlign: 'center', padding: '2rem' }}>No financing entries found.</td></tr>
                  )}
                </tbody>
              </table>
              {totalEntriesPages > 1 && (
                <div className="pagination">
                  <button className="btn-pagination" disabled={entriesPage === 1} onClick={() => setEntriesPage(entriesPage - 1)}>Prev</button>
                  <span>Page {entriesPage} of {totalEntriesPages}</span>
                  <button className="btn-pagination" disabled={entriesPage === totalEntriesPages} onClick={() => setEntriesPage(entriesPage + 1)}>Next</button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Section 2: Amortization Schedule */}
      <div className="section" style={{ marginTop: '1rem' }}>
        <div className="section-header" onClick={() => setShowAmortization(!showAmortization)}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ transform: showAmortization ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>▶</span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1e293b', margin: 0 }}>Amortization Schedule</h2>
          </div>
        </div>

        <div className={`section-content ${showAmortization ? '' : 'collapsed'}`}>
          <div className="amortization-controls">
            <label style={{ fontWeight: 500 }}>Select Property:</label>
            <select 
              className="select-input" 
              value={selectedEntryId} 
              onChange={(e) => setSelectedEntryId(e.target.value)}
            >
              <option value="total">Portfolio Total</option>
              {entries.map(({ entry }) => (
                <option key={entry.id} value={entry.id}>{entry.property_name}</option>
              ))}
            </select>
          </div>

          {amortLoading ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>Loading schedule...</div>
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    {selectedEntryId === "total" ? <th>Month</th> : <th>Period</th>}
                    {selectedEntryId !== "total" && <th>Beginning Balance</th>}
                    <th>Periodic Payment</th>
                    <th>Principal</th>
                    <th>Interest</th>
                    {selectedEntryId !== "total" && <th>Ending Balance</th>}
                  </tr>
                </thead>
                <tbody>
                  {paginatedAmort.map((row, idx) => (
                    <tr key={idx}>
                      <td>{selectedEntryId === "total" ? row.date : row.period}</td>
                      {selectedEntryId !== "total" && <td>{formatCurrency(row.beginning_balance || 0)}</td>}
                      <td>{formatCurrency(row.periodic_payment)}</td>
                      <td>{formatCurrency(row.principal_payment)}</td>
                      <td>{formatCurrency(row.interest_payment)}</td>
                      {selectedEntryId !== "total" && <td>{formatCurrency(row.ending_balance || 0)}</td>}
                    </tr>
                  ))}
                  {amortizationSchedule.length === 0 && (
                    <tr><td colSpan={selectedEntryId === "total" ? 4 : 6} style={{ textAlign: 'center', padding: '2rem' }}>No schedule data available.</td></tr>
                  )}
                </tbody>
              </table>
              {totalAmortPages > 1 && (
                <div className="pagination">
                  <button className="btn-pagination" disabled={amortPage === 1} onClick={() => setAmortPage(amortPage - 1)}>Prev</button>
                  <span>Page {amortPage} of {totalAmortPages}</span>
                  <button className="btn-pagination" disabled={amortPage === totalAmortPages} onClick={() => setAmortPage(amortPage + 1)}>Next</button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Modal for Add/Edit */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '500px' }}>
            <h2>{editingEntry ? "Edit Financing Entry" : "Create New Financing Entry"}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Property</label>
                <select name="property" value={formData.property} onChange={handleInputChange} required disabled={!!editingEntry}>
                  <option value="">Select a property</option>
                  {availableProperties.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Loan Amount ($)</label>
                <input type="number" name="loan_amount" value={formData.loan_amount} onChange={handleInputChange} required />
              </div>
              <div className="form-group">
                <label>Base Interest Rate (%)</label>
                <input type="number" step="0.01" name="base_interest_rate" value={formData.base_interest_rate} onChange={handleInputChange} required />
              </div>
              <div className="form-group">
                <label>Tenor (Years)</label>
                <input type="number" name="tenor" value={formData.tenor} onChange={handleInputChange} required />
              </div>
              <div className="form-group">
                <label>Payments per Year</label>
                <select name="payments_per_year" value={formData.payments_per_year} onChange={handleInputChange}>
                  <option value="1">Annual (1)</option>
                  <option value="2">Semi-Annual (2)</option>
                  <option value="4">Quarterly (4)</option>
                  <option value="12">Monthly (12)</option>
                </select>
              </div>
              <div className="form-group">
                <label>Loan Start Date</label>
                <input type="date" name="loan_start_date" value={formData.loan_start_date} onChange={handleInputChange} required />
              </div>
              <div className="modal-actions" style={{ marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">{editingEntry ? "Update" : "Create"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default FinancingModelTab;
