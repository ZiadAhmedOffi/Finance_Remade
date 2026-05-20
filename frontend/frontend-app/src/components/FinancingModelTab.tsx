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

interface InstallmentEntry {
  id: string;
  property: string;
  property_name: string;
  purchase_price: string;
  down_payment: string;
  tenor: number;
  payments_per_year: number;
  start_date: string;
}

interface InstallmentMetrics {
  balance: number;
  periodic_payment: number;
  annual_payment: number;
  total_periods: number;
}

interface InstallmentWithMetrics {
  entry: InstallmentEntry;
  metrics: InstallmentMetrics;
}

interface ScheduleRow {
  period?: number;
  date?: string;
  beginning_balance?: number;
  periodic_payment?: number;
  principal_payment?: number;
  interest_payment?: number;
  payment?: number;
  ending_balance?: number;
}

const FinancingModelTab: React.FC<{ portfolioId: string; canEdit: boolean }> = ({ portfolioId, canEdit }) => {
  const [mortgages, setMortgages] = useState<FinancingWithMetrics[]>([]);
  const [installments, setInstallments] = useState<InstallmentWithMetrics[]>([]);
  const [properties, setProperties] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Visibility toggles for the two halves
  const [showMortgages, setShowMortgages] = useState(true);
  const [showInstallments, setShowInstallments] = useState(true);
  
  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState<"MORTGAGE" | "INSTALLMENT">("MORTGAGE");
  const [editingEntry, setEditingEntry] = useState<any | null>(null);
  
  // Pagination
  const [mortgagePage, setMortgagePage] = useState(1);
  const [installmentPage, setInstallmentPage] = useState(1);
  const [schedulePage, setSchedulePage] = useState(1);
  const itemsPerPage = 10;
  
  // Schedule state
  const [scheduleMode, setScheduleMode] = useState<"MORTGAGE" | "INSTALLMENT">("MORTGAGE");
  const [selectedEntryId, setSelectedEntryId] = useState<string>("total");
  const [scheduleData, setScheduleData] = useState<ScheduleRow[]>([]);
  const [scheduleLoading, setScheduleLoading] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    property: "",
    loan_amount: "",
    base_interest_rate: "",
    tenor: "",
    payments_per_year: "12",
    loan_start_date: "",
    down_payment: "",
    start_date: "",
  });

  useEffect(() => {
    fetchData();
  }, [portfolioId]);

  useEffect(() => {
    fetchSchedule();
  }, [selectedEntryId, scheduleMode, mortgages, installments]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [finResponse, propResponse] = await Promise.all([
        realEstateApi.getFinancing(portfolioId),
        realEstateApi.getProperties(portfolioId),
      ]);
      setMortgages(finResponse.data.mortgages || []);
      setInstallments(finResponse.data.installments || []);
      setProperties(propResponse.data.map((p: any) => p.property).filter((p: any) => p.status !== "USUFRUCT"));
    } catch (err) {
      console.error("Failed to fetch financing data", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSchedule = async () => {
    if (!portfolioId) return;
    try {
      setScheduleLoading(true);
      let response;
      if (scheduleMode === "MORTGAGE") {
        if (selectedEntryId === "total") {
          response = await realEstateApi.getPortfolioAmortization(portfolioId);
        } else {
          response = await realEstateApi.getEntryAmortization(portfolioId, selectedEntryId);
        }
      } else {
        if (selectedEntryId === "total") {
          response = await realEstateApi.getPortfolioInstallmentsSchedule(portfolioId);
        } else {
          response = await realEstateApi.getEntryInstallmentsSchedule(portfolioId, selectedEntryId);
        }
      }
      setScheduleData(response.data);
      setSchedulePage(1);
    } catch (err) {
      console.error("Failed to fetch schedule", err);
      setScheduleData([]);
    } finally {
      setScheduleLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    let nextFormData = { ...formData, [name]: value };

    // Auto-calculate default down payment if property changes
    if (name === "property" && modalType === "INSTALLMENT") {
      const prop = properties.find(p => p.id === value);
      if (prop) {
        nextFormData.down_payment = (parseFloat(prop.purchase_price) * 0.2).toFixed(2);
        nextFormData.start_date = prop.purchase_date;
      }
    }

    setFormData(nextFormData);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (modalType === "MORTGAGE") {
        if (editingEntry) {
          await realEstateApi.updateFinancing(portfolioId, editingEntry.id, formData);
        } else {
          await realEstateApi.createFinancing(portfolioId, formData);
        }
      } else {
        if (editingEntry) {
          await realEstateApi.updateInstallment(portfolioId, editingEntry.id, formData);
        } else {
          await realEstateApi.createInstallment(portfolioId, formData);
        }
      }
      setShowModal(false);
      resetForm();
      fetchData();
    } catch (err: any) {
      console.error("Failed to save entry", err);
      alert(err.response?.data?.error || "Failed to save entry. Please check your inputs.");
    }
  };

  const resetForm = () => {
    setFormData({
      property: "",
      loan_amount: "",
      base_interest_rate: "",
      tenor: "",
      payments_per_year: modalType === "MORTGAGE" ? "12" : "1",
      loan_start_date: "",
      down_payment: "",
      start_date: "",
    });
    setEditingEntry(null);
  };

  const handleAddMortgage = () => {
    setModalType("MORTGAGE");
    resetForm();
    setShowModal(true);
  };

  const handleAddInstallment = () => {
    setModalType("INSTALLMENT");
    resetForm();
    setShowModal(true);
  };

  const handleEditMortgage = (entry: FinancingEntry) => {
    setModalType("MORTGAGE");
    setEditingEntry(entry);
    setFormData({
      property: entry.property,
      loan_amount: entry.loan_amount,
      base_interest_rate: entry.base_interest_rate,
      tenor: entry.tenor.toString(),
      payments_per_year: entry.payments_per_year.toString(),
      loan_start_date: entry.loan_start_date,
      down_payment: "",
      start_date: "",
    });
    setShowModal(true);
  };

  const handleEditInstallment = (entry: InstallmentEntry) => {
    setModalType("INSTALLMENT");
    setEditingEntry(entry);
    setFormData({
      property: entry.property,
      loan_amount: "",
      base_interest_rate: "",
      tenor: entry.tenor.toString(),
      payments_per_year: entry.payments_per_year.toString(),
      loan_start_date: "",
      down_payment: entry.down_payment,
      start_date: entry.start_date,
    });
    setShowModal(true);
  };

  const handleDeleteMortgage = async (entryId: string) => {
    if (window.confirm("Are you sure you want to delete this mortgage?")) {
      try {
        await realEstateApi.deleteFinancing(portfolioId, entryId);
        fetchData();
      } catch (err) {
        console.error("Failed to delete mortgage", err);
      }
    }
  };

  const handleDeleteInstallment = async (entryId: string) => {
    if (window.confirm("Are you sure you want to delete this installment entry?")) {
      try {
        await realEstateApi.deleteInstallment(portfolioId, entryId);
        fetchData();
      } catch (err) {
        console.error("Failed to delete installment entry", err);
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
  const paginatedMortgages = mortgages.slice((mortgagePage - 1) * itemsPerPage, mortgagePage * itemsPerPage);
  const totalMortgagePages = Math.ceil(mortgages.length / itemsPerPage);

  const paginatedInstallments = installments.slice((installmentPage - 1) * itemsPerPage, installmentPage * itemsPerPage);
  const totalInstallmentPages = Math.ceil(installments.length / itemsPerPage);

  const paginatedSchedule = scheduleData.slice((schedulePage - 1) * itemsPerPage, schedulePage * itemsPerPage);
  const totalSchedulePages = Math.ceil(scheduleData.length / itemsPerPage);

  // Available properties for Mortgages
  const availableMortgageProps = properties.filter(p => 
    p.financing_type === "MORTGAGED" && 
    (!mortgages.some(m => m.entry.property === p.id) || (editingEntry && editingEntry.property === p.id))
  );

  // Available properties for Installments
  const availableInstallmentProps = properties.filter(p => 
    p.financing_type === "PRIMARY_INSTALLMENTS" && 
    (!installments.some(i => i.entry.property === p.id) || (editingEntry && editingEntry.property === p.id))
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
        .toggle-btn {
          background: #e2e8f0;
          border: none;
          padding: 0.25rem 0.75rem;
          border-radius: 4px;
          font-size: 0.75rem;
          font-weight: 600;
          color: #475569;
          cursor: pointer;
        }
        .toggle-btn.active {
          background: #2563eb;
          color: white;
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
        .controls-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
          gap: 1rem;
        }
        .mode-toggles {
          display: flex;
          gap: 0.5rem;
          background: #f1f5f9;
          padding: 0.25rem;
          border-radius: 6px;
        }
      `}</style>

      {/* Mortgages Section */}
      <div className="section">
        <div className="section-header" onClick={() => setShowMortgages(!showMortgages)}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ transform: showMortgages ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>▶</span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1e293b', margin: 0 }}>Mortgage Financing</h2>
          </div>
          {canEdit && (
            <button className="btn btn-primary" onClick={(e) => { e.stopPropagation(); handleAddMortgage(); }}>
              + Add Mortgage
            </button>
          )}
        </div>
        
        <div className={`section-content ${showMortgages ? '' : 'collapsed'}`}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>Loading mortgages...</div>
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Property Name</th>
                    <th>Loan Amount</th>
                    <th>LTV</th>
                    <th>Base Rate</th>
                    <th>Tenor (yrs)</th>
                    <th>Periodic Pmt</th>
                    <th>Annual Debt Service</th>
                    {canEdit && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {paginatedMortgages.map(({ entry, metrics }) => (
                    <tr key={entry.id}>
                      <td style={{ fontWeight: 600 }}>{entry.property_name}</td>
                      <td>{formatCurrency(entry.loan_amount)}</td>
                      <td className={metrics.ltv > 100 ? "text-red-600 font-bold" : ""}>{formatPercent(metrics.ltv)}</td>
                      <td>{formatPercent(entry.base_interest_rate)}</td>
                      <td>{entry.tenor}</td>
                      <td>{formatCurrency(metrics.periodic_payment)}</td>
                      <td>{formatCurrency(metrics.annual_debt_service)}</td>
                      {canEdit && (
                        <td>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button className="btn btn-secondary btn-sm" onClick={() => handleEditMortgage(entry)}>Edit</button>
                            <button 
                              className="btn-sm" 
                              style={{ background: '#fee2e2', color: '#991b1b', border: '1px solid #fecaca', cursor: 'pointer', borderRadius: '4px' }}
                              onClick={() => handleDeleteMortgage(entry.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                  {mortgages.length === 0 && (
                    <tr><td colSpan={8} style={{ textAlign: 'center', padding: '2rem' }}>No mortgages found.</td></tr>
                  )}
                </tbody>
              </table>
              {totalMortgagePages > 1 && (
                <div className="pagination">
                  <button className="btn-pagination" disabled={mortgagePage === 1} onClick={() => setMortgagePage(mortgagePage - 1)}>Prev</button>
                  <span>Page {mortgagePage} of {totalMortgagePages}</span>
                  <button className="btn-pagination" disabled={mortgagePage === totalMortgagePages} onClick={() => setMortgagePage(mortgagePage + 1)}>Next</button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Installments Section */}
      <div className="section" style={{ marginTop: '1.5rem' }}>
        <div className="section-header" onClick={() => setShowInstallments(!showInstallments)}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ transform: showInstallments ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>▶</span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1e293b', margin: 0 }}>Primary Sales Installments</h2>
          </div>
          {canEdit && (
            <button className="btn btn-primary" onClick={(e) => { e.stopPropagation(); handleAddInstallment(); }}>
              + Add Installment Plan
            </button>
          )}
        </div>
        
        <div className={`section-content ${showInstallments ? '' : 'collapsed'}`}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>Loading installments...</div>
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Property Name</th>
                    <th>Purchase Price</th>
                    <th>Down Payment</th>
                    <th>Balance</th>
                    <th>Tenor (yrs)</th>
                    <th>Annual Pmt</th>
                    {canEdit && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {paginatedInstallments.map(({ entry, metrics }) => (
                    <tr key={entry.id}>
                      <td style={{ fontWeight: 600 }}>{entry.property_name}</td>
                      <td>{formatCurrency(entry.purchase_price)}</td>
                      <td>{formatCurrency(entry.down_payment)}</td>
                      <td>{formatCurrency(metrics.balance)}</td>
                      <td>{entry.tenor}</td>
                      <td>{formatCurrency(metrics.annual_payment)}</td>
                      {canEdit && (
                        <td>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button className="btn btn-secondary btn-sm" onClick={() => handleEditInstallment(entry)}>Edit</button>
                            <button 
                              className="btn-sm" 
                              style={{ background: '#fee2e2', color: '#991b1b', border: '1px solid #fecaca', cursor: 'pointer', borderRadius: '4px' }}
                              onClick={() => handleDeleteInstallment(entry.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                  {installments.length === 0 && (
                    <tr><td colSpan={7} style={{ textAlign: 'center', padding: '2rem' }}>No installment plans found.</td></tr>
                  )}
                </tbody>
              </table>
              {totalInstallmentPages > 1 && (
                <div className="pagination">
                  <button className="btn-pagination" disabled={installmentPage === 1} onClick={() => setInstallmentPage(installmentPage - 1)}>Prev</button>
                  <span>Page {installmentPage} of {totalInstallmentPages}</span>
                  <button className="btn-pagination" disabled={installmentPage === totalInstallmentPages} onClick={() => setInstallmentPage(installmentPage + 1)}>Next</button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Schedule Section */}
      <div className="section" style={{ marginTop: '1.5rem' }}>
        <div className="section-header">
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1e293b', margin: 0 }}>Payment Schedule</h2>
          <div className="mode-toggles">
            <button 
              className={`toggle-btn ${scheduleMode === "MORTGAGE" ? "active" : ""}`}
              onClick={() => { setScheduleMode("MORTGAGE"); setSelectedEntryId("total"); }}
            >
              Mortgages
            </button>
            <button 
              className={`toggle-btn ${scheduleMode === "INSTALLMENT" ? "active" : ""}`}
              onClick={() => { setScheduleMode("INSTALLMENT"); setSelectedEntryId("total"); }}
            >
              Installments
            </button>
          </div>
        </div>

        <div className="controls-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <label style={{ fontWeight: 500 }}>Select Property:</label>
            <select 
              className="select-input" 
              value={selectedEntryId} 
              onChange={(e) => setSelectedEntryId(e.target.value)}
            >
              <option value="total">Portfolio Total</option>
              {scheduleMode === "MORTGAGE" ? (
                mortgages.map(({ entry }) => (
                  <option key={entry.id} value={entry.id}>{entry.property_name}</option>
                ))
              ) : (
                installments.map(({ entry }) => (
                  <option key={entry.id} value={entry.id}>{entry.property_name}</option>
                ))
              )}
            </select>
          </div>
        </div>

        {scheduleLoading ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>Loading schedule...</div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  {selectedEntryId === "total" ? <th>Month</th> : <th>Period</th>}
                  {scheduleMode === "MORTGAGE" && selectedEntryId !== "total" && <th>Beginning Balance</th>}
                  <th>{scheduleMode === "MORTGAGE" ? "Periodic Payment" : "Installment Pmt"}</th>
                  {scheduleMode === "MORTGAGE" && <th>Principal</th>}
                  {scheduleMode === "MORTGAGE" && <th>Interest</th>}
                  {scheduleMode === "MORTGAGE" && selectedEntryId !== "total" && <th>Ending Balance</th>}
                </tr>
              </thead>
              <tbody>
                {paginatedSchedule.map((row, idx) => (
                  <tr key={idx}>
                    <td>{selectedEntryId === "total" ? row.date : row.period}</td>
                    {scheduleMode === "MORTGAGE" && selectedEntryId !== "total" && <td>{formatCurrency(row.beginning_balance || 0)}</td>}
                    <td>{formatCurrency(scheduleMode === "MORTGAGE" ? row.periodic_payment || 0 : row.payment || 0)}</td>
                    {scheduleMode === "MORTGAGE" && <td>{formatCurrency(row.principal_payment || 0)}</td>}
                    {scheduleMode === "MORTGAGE" && <td>{formatCurrency(row.interest_payment || 0)}</td>}
                    {scheduleMode === "MORTGAGE" && selectedEntryId !== "total" && <td>{formatCurrency(row.ending_balance || 0)}</td>}
                  </tr>
                ))}
                {scheduleData.length === 0 && (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>No schedule data available.</td></tr>
                )}
              </tbody>
            </table>
            {totalSchedulePages > 1 && (
              <div className="pagination">
                <button className="btn-pagination" disabled={schedulePage === 1} onClick={() => setSchedulePage(schedulePage - 1)}>Prev</button>
                <span>Page {schedulePage} of {totalSchedulePages}</span>
                <button className="btn-pagination" disabled={schedulePage === totalSchedulePages} onClick={() => setSchedulePage(schedulePage + 1)}>Next</button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal for Add/Edit */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '500px' }}>
            <h2>{editingEntry ? "Edit" : "Create New"} {modalType === "MORTGAGE" ? "Mortgage" : "Installment Plan"}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Property</label>
                <select name="property" value={formData.property} onChange={handleInputChange} required disabled={!!editingEntry}>
                  <option value="">Select a property</option>
                  {(modalType === "MORTGAGE" ? availableMortgageProps : availableInstallmentProps).map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              {modalType === "MORTGAGE" ? (
                <>
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
                </>
              ) : (
                <>
                  <div className="form-group">
                    <label>Down Payment ($)</label>
                    <input type="number" name="down_payment" value={formData.down_payment} onChange={handleInputChange} required />
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
                    <label>Start Date</label>
                    <input type="date" name="start_date" value={formData.start_date} onChange={handleInputChange} required />
                  </div>
                </>
              )}

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
