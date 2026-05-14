import React, { useState, useEffect } from "react";
import { realEstateApi } from "../api/api";
import { formatCurrency, formatPercent } from "../utils/formatters";

interface Property {
  id: string;
  name: string;
  city: string;
  country: string;
  submarket: string;
  property_type: string;
  financing_type: string;
  status: "HELD" | "OFF_PLAN";
  purchase_date: string;
  purchase_price: string;
  size: string;
  monthly_rent: string;
  other_operational_expenses: string;
  acq_fee_percentage: string;
  appreciation_rate_percentage: string;
  vacancy_rate_percentage: string;
}

interface Metrics {
  acq_fee_amount: number;
  total_cost_basis: number;
  years_held: number;
  current_market_value: number;
  unrealized_gain: number;
  annual_rent: number;
  effective_rent: number;
  management_fees: number;
  maintenance_fees: number;
  total_operational_expenses: number;
  noi: number;
  gross_yield: number;
  net_yield: number;
  cost_per_sqm: number;
}

interface PropertyWithMetrics {
  property: Property;
  metrics: Metrics;
}

const PropertyDataTab: React.FC<{ portfolioId: string; canEdit: boolean }> = ({ portfolioId, canEdit }) => {
  const [data, setData] = useState<PropertyWithMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingProperty, setEditingProperty] = useState<Property | null>(null);
  const [assumptions, setAssumptions] = useState<any>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    city: "",
    country: "",
    submarket: "",
    property_type: "RESIDENTIAL",
    financing_type: "ALL_CASH",
    status: "HELD",
    purchase_date: "",
    purchase_price: "",
    size: "0",
    monthly_rent: "",
    other_operational_expenses: "0",
    acq_fee_percentage: "",
    appreciation_rate_percentage: "",
    vacancy_rate_percentage: "",
  });

  useEffect(() => {
    fetchProperties();
    fetchAssumptions();
  }, [portfolioId]);

  useEffect(() => {
    console.log("PropertyDataTab canEdit:", canEdit);
    console.log("Portfolio Assumptions:", assumptions);
  }, [canEdit, assumptions]);

  const fetchProperties = async () => {
    try {
      setLoading(true);
      const response = await realEstateApi.getProperties(portfolioId);
      setData(response.data);
    } catch (err) {
      console.error("Failed to fetch properties", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAssumptions = async () => {
    try {
      const response = await realEstateApi.getAssumptions(portfolioId);
      setAssumptions(response.data);
    } catch (err) {
      console.error("Failed to fetch assumptions", err);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingProperty) {
        await realEstateApi.updateProperty(portfolioId, editingProperty.id, formData);
      } else {
        await realEstateApi.createProperty(portfolioId, formData);
      }
      setShowModal(false);
      resetForm();
      fetchProperties();
    } catch (err) {
      console.error("Failed to save property", err);
      alert("Failed to save property. Please check your inputs.");
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      city: "",
      country: "",
      submarket: "",
      property_type: "RESIDENTIAL",
      financing_type: "ALL_CASH",
      status: "HELD",
      purchase_date: "",
      purchase_price: "",
      size: "0",
      monthly_rent: "",
      other_operational_expenses: "0",
      acq_fee_percentage: assumptions?.acquisition_fee_percentage?.toString() || "",
      appreciation_rate_percentage: assumptions?.default_appreciation_rate?.toString() || "",
      vacancy_rate_percentage: assumptions?.default_vacancy_rate?.toString() || "",
    });
    setEditingProperty(null);
  };

  const handleAddProperty = () => {
    resetForm();
    setShowModal(true);
  };

  const handleEdit = (prop: Property) => {
    setEditingProperty(prop);
    setFormData({
      name: prop.name,
      city: prop.city,
      country: prop.country,
      submarket: prop.submarket,
      property_type: prop.property_type,
      financing_type: prop.financing_type,
      status: prop.status,
      purchase_date: prop.purchase_date,
      purchase_price: prop.purchase_price,
      size: prop.size,
      monthly_rent: prop.monthly_rent,
      other_operational_expenses: prop.other_operational_expenses,
      acq_fee_percentage: prop.acq_fee_percentage,
      appreciation_rate_percentage: prop.appreciation_rate_percentage,
      vacancy_rate_percentage: prop.vacancy_rate_percentage,
    });
    setShowModal(true);
  };

  const handleDelete = async (propertyId: string) => {
    if (window.confirm("Are you sure you want to delete this property?")) {
      try {
        await realEstateApi.deleteProperty(portfolioId, propertyId);
        fetchProperties();
      } catch (err) {
        console.error("Failed to delete property", err);
      }
    }
  };

  return (
    <div className="property-data-container">
      <style>{`
        .property-data-container {
          padding: 1rem;
        }
        .table-wrapper {
          overflow-x: auto;
          background: white;
          border-radius: 8px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          margin-top: 1rem;
        }
        .property-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.875rem;
        }
        .property-table th, .property-table td {
          padding: 0.75rem 1rem;
          text-align: left;
          border-bottom: 1px solid #e2e8f0;
          white-space: nowrap;
        }
        .property-table th {
          background: #f8fafc;
          font-weight: 600;
          color: #475569;
          position: sticky;
          top: 0;
        }
        .property-table tr:hover {
          background: #f1f5f9;
        }
        .metric-cell {
          font-weight: 500;
          color: #0f172a;
        }
        .status-held { color: #10b981; font-weight: 600; }
        .status-offplan { color: #f59e0b; font-weight: 600; }
        .action-btns {
          display: flex;
          gap: 0.5rem;
        }
        .btn-sm {
          padding: 0.25rem 0.5rem;
          font-size: 0.75rem;
        }
        .actions-cell {
          width: 150px;
          min-width: 150px;
          text-align: center;
        }
        .sticky-left {
          position: sticky;
          left: 0;
          z-index: 10;
          background: white;
          box-shadow: 2px 0 5px -2px rgba(0,0,0,0.1);
        }
        th.sticky-left {
          z-index: 30;
          background: #f8fafc !important;
        }
        .btn-logout {
          transition: background-color 0.2s;
        }
        .btn-logout:hover {
          background-color: #fecaca !important;
        }
      `}</style>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1e293b' }}>Portfolio Properties</h2>
        {canEdit && (
          <button className="btn btn-primary" onClick={handleAddProperty}>
            + Add Property
          </button>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>Loading property data...</div>
      ) : (
        <div className="table-wrapper">
          <table className="property-table">
            <thead>
              <tr>
                <th colSpan={9} className="group-header">Basic Information</th>
                <th colSpan={3} className="group-header">Investment Inputs</th>
                <th colSpan={3} className="group-header">Rates & Assumptions</th>
                <th colSpan={14} className="group-header">Derived Metrics & Performance</th>
                {canEdit && <th rowSpan={2} className="group-header">Actions</th>}
              </tr>
              <tr>
                <th className="sticky-left">Property Name</th>
                <th>City</th>
                <th>Country</th>
                <th>Submarket</th>
                <th>Type</th>
                <th>Size (Sqm)</th>
                <th>Financing</th>
                <th>Status</th>
                <th>Purchase Date</th>
                
                <th>Purchase Price</th>
                <th>Monthly Rent</th>
                <th>Annual Ops Exp</th>
                
                <th>Acq Fee%</th>
                <th>App Rate%</th>
                <th>Vacancy%</th>
                
                <th>Acq Fee$</th>
                <th>Total Cost Basis</th>
                <th>Cost/Sqm</th>
                <th>Years Held</th>
                <th>Market Value</th>
                <th>Unrealized Gain</th>
                <th>Annual Rent</th>
                <th>Effective Rent</th>
                <th>Mgmt Fees</th>
                <th>Maintenance</th>
                <th>Total Ops Exp</th>
                <th>NOI</th>
                <th>Gross Yield</th>
                <th>Net Yield</th>
              </tr>
            </thead>
            <tbody>
              {data.map(({ property, metrics }) => (
                <tr key={property.id}>
                  <td className="sticky-left" style={{ fontWeight: 600 }}>{property.name}</td>
                  <td>{property.city}</td>
                  <td>{property.country}</td>
                  <td>{property.submarket}</td>
                  <td>{property.property_type}</td>
                  <td>{parseFloat(property.size).toFixed(2)}</td>
                  <td>{property.financing_type}</td>
                  <td>
                    <span className={property.status === "HELD" ? "status-held" : "status-offplan"}>
                      {property.status}
                    </span>
                  </td>
                  <td>{property.purchase_date}</td>
                  
                  <td>{formatCurrency(parseFloat(property.purchase_price))}</td>
                  <td>{formatCurrency(parseFloat(property.monthly_rent))}</td>
                  <td>{formatCurrency(parseFloat(property.other_operational_expenses))}</td>
                  
                  <td>{formatPercent(parseFloat(property.acq_fee_percentage))}</td>
                  <td>{formatPercent(parseFloat(property.appreciation_rate_percentage))}</td>
                  <td>{formatPercent(parseFloat(property.vacancy_rate_percentage))}</td>
                  
                  <td className="metric-cell">{formatCurrency(metrics.acq_fee_amount)}</td>
                  <td className="metric-cell">{formatCurrency(metrics.total_cost_basis)}</td>
                  <td className="metric-cell">{formatCurrency(metrics.cost_per_sqm)}</td>
                  <td className="metric-cell">{metrics.years_held.toFixed(2)}</td>
                  <td className="metric-cell" style={{color: '#2563eb'}}>{formatCurrency(metrics.current_market_value)}</td>
                  <td className="metric-cell" style={{color: metrics.unrealized_gain >= 0 ? '#10b981' : '#ef4444'}}>
                    {formatCurrency(metrics.unrealized_gain)}
                  </td>
                  <td className="metric-cell">{formatCurrency(metrics.annual_rent)}</td>
                  <td className="metric-cell">{formatCurrency(metrics.effective_rent)}</td>
                  <td className="metric-cell">{formatCurrency(metrics.management_fees)}</td>
                  <td className="metric-cell">{formatCurrency(metrics.maintenance_fees)}</td>
                  <td className="metric-cell">{formatCurrency(metrics.total_operational_expenses)}</td>
                  <td className="metric-cell" style={{fontWeight: 700}}>{formatCurrency(metrics.noi)}</td>
                  <td className="metric-cell">{formatPercent(metrics.gross_yield)}</td>
                  <td className="metric-cell">{formatPercent(metrics.net_yield)}</td>
                  
                  {canEdit && (
                    <td className="actions-cell">
                      <div className="action-btns" style={{ display: 'flex', gap: '0.5rem' }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => handleEdit(property)}>Edit</button>
                        <button 
                          className="btn btn-logout btn-sm" 
                          style={{
                            background: '#fee2e2', 
                            color: '#991b1b', 
                            border: '1px solid #fecaca',
                            padding: '0.25rem 0.5rem',
                            fontSize: '0.75rem',
                            cursor: 'pointer'
                          }} 
                          onClick={() => handleDelete(property.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '800px' }}>
            <h2>{editingProperty ? "Edit Property" : "Add New Property"}</h2>
            <form onSubmit={handleSubmit}>
              <div className="input-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label>Property Name</label>
                  <input type="text" name="name" value={formData.name} onChange={handleInputChange} required />
                </div>
                <div className="form-group">
                  <label>City</label>
                  <input type="text" name="city" value={formData.city} onChange={handleInputChange} required />
                </div>
                <div className="form-group">
                  <label>Country</label>
                  <input type="text" name="country" value={formData.country} onChange={handleInputChange} required />
                </div>
                <div className="form-group">
                  <label>Submarket</label>
                  <input type="text" name="submarket" value={formData.submarket} onChange={handleInputChange} />
                </div>
                <div className="form-group">
                  <label>Property Type</label>
                  <select name="property_type" value={formData.property_type} onChange={handleInputChange}>
                    <option value="RESIDENTIAL">Residential</option>
                    <option value="COMMERCIAL">Commercial</option>
                    <option value="INDUSTRIAL">Industrial</option>
                    <option value="RETAIL">Retail</option>
                    <option value="MIXED_USE">Mixed-Use</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Financing</label>
                  <select name="financing_type" value={formData.financing_type} onChange={handleInputChange}>
                    <option value="ALL_CASH">All Cash</option>
                    <option value="MORTGAGED">Mortgaged</option>
                    <option value="MEZZANINE">Mezzanine</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Status</label>
                  <select name="status" value={formData.status} onChange={handleInputChange}>
                    <option value="HELD">Held</option>
                    <option value="OFF_PLAN">Off-Plan</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Purchase Date</label>
                  <input type="date" name="purchase_date" value={formData.purchase_date} onChange={handleInputChange} required />
                </div>
                <div className="form-group">
                  <label>Purchase Price ($)</label>
                  <input type="number" name="purchase_price" value={formData.purchase_price} onChange={handleInputChange} required />
                </div>
                <div className="form-group">
                  <label>Size (Sqm)</label>
                  <input type="number" step="0.01" name="size" value={formData.size} onChange={handleInputChange} required />
                </div>
                <div className="form-group">
                  <label>Monthly Rent ($)</label>
                  <input type="number" name="monthly_rent" value={formData.monthly_rent} onChange={handleInputChange} required />
                </div>
                <div className="form-group">
                  <label>Annual Ops Exp ($)</label>
                  <input type="number" name="other_operational_expenses" value={formData.other_operational_expenses} onChange={handleInputChange} required />
                </div>
                <div className="form-group">
                  <label>Acq Fee % (Optional)</label>
                  <input type="number" step="0.01" name="acq_fee_percentage" value={formData.acq_fee_percentage} onChange={handleInputChange} placeholder="Default from assumptions" />
                </div>
                <div className="form-group">
                  <label>App Rate % (Optional)</label>
                  <input type="number" step="0.01" name="appreciation_rate_percentage" value={formData.appreciation_rate_percentage} onChange={handleInputChange} placeholder="Default from assumptions" />
                </div>
                <div className="form-group">
                  <label>Vacancy % (Optional)</label>
                  <input type="number" step="0.01" name="vacancy_rate_percentage" value={formData.vacancy_rate_percentage} onChange={handleInputChange} placeholder="Default from assumptions" />
                </div>
              </div>
              <div className="modal-actions" style={{ marginTop: '2rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">
                  {editingProperty ? "Update Property" : "Add Property"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default PropertyDataTab;
