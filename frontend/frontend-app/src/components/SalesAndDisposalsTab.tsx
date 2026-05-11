import React, { useState, useEffect } from "react";
import { realEstateApi } from "../api/api";

interface PropertySale {
  id: string;
  property: string;
  property_name: string;
  sale_date: string;
  selling_price: string;
  selling_fee_percentage: string;
}

interface SaleMetrics {
  selling_costs: number;
  cost_basis: number;
  loan_payoff: number;
  net_proceeds: number;
  realized_gain: number;
  roi: number;
}

interface SaleWithMetrics {
  sale: PropertySale;
  metrics: SaleMetrics;
}

const SalesAndDisposalsTab: React.FC<{ portfolioId: string; canEdit: boolean }> = ({ portfolioId, canEdit }) => {
  const [sales, setSales] = useState<SaleWithMetrics[]>([]);
  const [properties, setProperties] = useState<any[]>([]);
  const [assumptions, setAssumptions] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingSale, setEditingSale] = useState<PropertySale | null>(null);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Form state
  const [formData, setFormData] = useState({
    property: "",
    sale_date: "",
    selling_price: "",
    selling_fee_percentage: "",
  });

  useEffect(() => {
    fetchData();
  }, [portfolioId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [salesRes, propsRes, assumptionsRes] = await Promise.all([
        realEstateApi.getSales(portfolioId),
        realEstateApi.getProperties(portfolioId),
        realEstateApi.getAssumptions(portfolioId)
      ]);
      setSales(salesRes.data);
      setProperties(propsRes.data.map((p: any) => p.property));
      setAssumptions(assumptionsRes.data);
    } catch (err) {
      console.error("Failed to fetch sales data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingSale) {
        await realEstateApi.updateSale(portfolioId, editingSale.id, formData);
      } else {
        await realEstateApi.createSale(portfolioId, formData);
      }
      setShowModal(false);
      resetForm();
      fetchData();
    } catch (err: any) {
      console.error("Failed to save sale entry", err);
      alert(err.response?.data?.error || "Failed to save sale entry. Please check your inputs.");
    }
  };

  const resetForm = () => {
    setFormData({
      property: "",
      sale_date: "",
      selling_price: "",
      selling_fee_percentage: assumptions?.selling_fee_percentage || "",
    });
    setEditingSale(null);
  };

  const handleAddSale = () => {
    resetForm();
    setFormData(prev => ({
        ...prev,
        selling_fee_percentage: assumptions?.selling_fee_percentage || ""
    }));
    setShowModal(true);
  };

  const handleEdit = (sale: PropertySale) => {
    setEditingSale(sale);
    setFormData({
      property: sale.property,
      sale_date: sale.sale_date,
      selling_price: sale.selling_price,
      selling_fee_percentage: sale.selling_fee_percentage,
    });
    setShowModal(true);
  };

  const handleDelete = async (saleId: string) => {
    if (window.confirm("Are you sure you want to delete this sale entry?")) {
      try {
        await realEstateApi.deleteSale(portfolioId, saleId);
        fetchData();
      } catch (err) {
        console.error("Failed to delete sale entry", err);
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

  const formatROI = (val: number) => {
    return val.toFixed(2) + "x";
  };

  // Pagination logic
  const paginatedSales = sales.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);
  const totalPages = Math.ceil(sales.length / itemsPerPage);

  // Filter properties that don't have a sale yet
  const availableProperties = properties.filter(p => 
    !sales.some(s => s.sale.property === p.id) || (editingSale && editingSale.property === p.id)
  );

  // Totals calculation
  const totals = sales.reduce((acc, curr) => ({
    selling_price: acc.selling_price + parseFloat(curr.sale.selling_price),
    selling_costs: acc.selling_costs + curr.metrics.selling_costs,
    net_proceeds: acc.net_proceeds + curr.metrics.net_proceeds,
    realized_gain: acc.realized_gain + curr.metrics.realized_gain,
  }), { selling_price: 0, selling_costs: 0, net_proceeds: 0, realized_gain: 0 });

  return (
    <div className="sales-disposals-container">
      <style>{`
        .sales-disposals-container { padding: 1rem; }
        .tab-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
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
        .data-table .totals-row {
          background: #f1f5f9;
          font-weight: 700;
        }
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
        .roi-positive { color: #059669; }
        .roi-negative { color: #dc2626; }
      `}</style>

      <div className="tab-header">
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#1e293b' }}>Sales and Disposals</h2>
        {canEdit && (
          <button className="btn btn-primary" onClick={handleAddSale}>
            + Add Sale
          </button>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading sales data...</div>
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Property Name</th>
                <th>Sale Date</th>
                <th>Selling Price</th>
                <th>Selling Fee %</th>
                <th>Selling Costs</th>
                <th>Cost Basis</th>
                <th>Loan Payoff</th>
                <th>Net Proceeds</th>
                <th>Realized Gain</th>
                <th>ROI</th>
                {canEdit && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {paginatedSales.map(({ sale, metrics }) => (
                <tr key={sale.id}>
                  <td style={{ fontWeight: 600 }}>{sale.property_name}</td>
                  <td>{sale.sale_date}</td>
                  <td>{formatCurrency(sale.selling_price)}</td>
                  <td>{formatPercent(sale.selling_fee_percentage)}</td>
                  <td>{formatCurrency(metrics.selling_costs)}</td>
                  <td>{formatCurrency(metrics.cost_basis)}</td>
                  <td>{formatCurrency(metrics.loan_payoff)}</td>
                  <td>{formatCurrency(metrics.net_proceeds)}</td>
                  <td className={metrics.realized_gain >= 0 ? "roi-positive" : "roi-negative"}>
                    {formatCurrency(metrics.realized_gain)}
                  </td>
                  <td className={metrics.roi >= 1 ? "roi-positive" : "roi-negative"}>
                    {formatROI(metrics.roi)}
                  </td>
                  {canEdit && (
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => handleEdit(sale)}>Edit</button>
                        <button 
                          className="btn-sm" 
                          style={{ background: '#fee2e2', color: '#991b1b', border: '1px solid #fecaca', cursor: 'pointer', borderRadius: '4px' }}
                          onClick={() => handleDelete(sale.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
              {sales.length > 0 && (
                <tr className="totals-row">
                  <td colSpan={2}>Total</td>
                  <td>{formatCurrency(totals.selling_price)}</td>
                  <td>-</td>
                  <td>{formatCurrency(totals.selling_costs)}</td>
                  <td colSpan={2}>-</td>
                  <td>{formatCurrency(totals.net_proceeds)}</td>
                  <td>{formatCurrency(totals.realized_gain)}</td>
                  <td>-</td>
                  {canEdit && <td></td>}
                </tr>
              )}
              {sales.length === 0 && (
                <tr><td colSpan={canEdit ? 11 : 10} style={{ textAlign: 'center', padding: '2rem' }}>No sales entries found.</td></tr>
              )}
            </tbody>
          </table>
          {totalPages > 1 && (
            <div className="pagination">
              <button className="btn-pagination" disabled={currentPage === 1} onClick={() => setCurrentPage(currentPage - 1)}>Prev</button>
              <span>Page {currentPage} of {totalPages}</span>
              <button className="btn-pagination" disabled={currentPage === totalPages} onClick={() => setCurrentPage(currentPage + 1)}>Next</button>
            </div>
          )}
        </div>
      )}

      {/* Modal for Add/Edit */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '500px' }}>
            <h2>{editingSale ? "Edit Sale Entry" : "Create New Sale Entry"}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Property</label>
                <select name="property" value={formData.property} onChange={handleInputChange} required disabled={!!editingSale}>
                  <option value="">Select a property</option>
                  {availableProperties.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Sale Date</label>
                <input type="date" name="sale_date" value={formData.sale_date} onChange={handleInputChange} required />
              </div>
              <div className="form-group">
                <label>Selling Price ($)</label>
                <input type="number" step="0.01" name="selling_price" value={formData.selling_price} onChange={handleInputChange} required />
              </div>
              <div className="form-group">
                <label>Selling Fee (%)</label>
                <input 
                    type="number" 
                    step="0.01" 
                    name="selling_fee_percentage" 
                    value={formData.selling_fee_percentage} 
                    onChange={handleInputChange} 
                    required 
                    placeholder={assumptions?.selling_fee_percentage ? `Default: ${assumptions.selling_fee_percentage}%` : ""}
                />
              </div>
              <div className="modal-actions" style={{ marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">{editingSale ? "Update" : "Create"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SalesAndDisposalsTab;
