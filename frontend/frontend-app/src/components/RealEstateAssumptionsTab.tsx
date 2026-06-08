import React, { useState, useEffect } from "react";
import { realEstateApi } from "../api/api";

interface Assumptions {
  inception_date: string;
  forecast_horizon: number;
  default_appreciation_rate: string;
  default_rental_growth_rate: string;
  default_vacancy_rate: string;
  default_discount_rate: string;
  acquisition_fee_percentage: string;
  property_mgmt_fee_percentage: string;
  maintenance_percentage_of_value: string;
  selling_fee_percentage: string;
  active_scenario: "BASE" | "BULL" | "BEAR";
  developer: string;
}

const RealEstateAssumptionsTab: React.FC<{ portfolioId: string; canEdit: boolean }> = ({ portfolioId, canEdit }) => {
  const [assumptions, setAssumptions] = useState<Assumptions | null>(null);
  const [coverImage, setCoverImage] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [assumptionsRes, portfolioRes] = await Promise.all([
          realEstateApi.getAssumptions(portfolioId),
          realEstateApi.getPortfolio(portfolioId)
        ]);
        setAssumptions(assumptionsRes.data);
        setCoverImage(portfolioRes.data.cover_image || "");
      } catch (err) {
        console.error("Failed to fetch data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [portfolioId]);

  const handleInputChange = (field: keyof Assumptions, value: any) => {
    if (assumptions) {
      setAssumptions({ ...assumptions, [field]: value });
    }
  };

  const handleSave = async () => {
    if (!assumptions) return;
    setSaving(true);
    setMessage(null);
    try {
      await Promise.all([
        realEstateApi.updateAssumptions(portfolioId, assumptions),
        realEstateApi.updatePortfolio(portfolioId, { cover_image: coverImage })
      ]);
      setMessage({ type: 'success', text: "Changes saved successfully!" });
    } catch (err) {
      setMessage({ type: 'error', text: "Failed to save changes." });
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div>Loading assumptions...</div>;
  if (!assumptions) return <div>No assumptions data found.</div>;

  const getAdjustmentInfo = () => {
    switch (assumptions.active_scenario) {
      case "BULL":
        return [
          { label: "Appreciation Adjustment", value: "+2%", color: "#10b981" },
          { label: "Rental Growth Adjustment", value: "+1%", color: "#10b981" },
          { label: "Vacancy Adjustment", value: "-2%", color: "#10b981" },
          { label: "Interest Rate Adjustment", value: "-0.5%", color: "#10b981" },
        ];
      case "BEAR":
        return [
          { label: "Appreciation Adjustment", value: "-2%", color: "#ef4444" },
          { label: "Rental Growth Adjustment", value: "-1%", color: "#ef4444" },
          { label: "Vacancy Adjustment", value: "+3%", color: "#ef4444" },
          { label: "Interest Rate Adjustment", value: "+1%", color: "#ef4444" },
        ];
      default:
        return null;
    }
  };

  const adjustments = getAdjustmentInfo();

  return (
    <div className="assumptions-container" style={{maxWidth: '900px', margin: '0 auto', animation: 'fadeIn 0.5s ease-out'}}>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .assumptions-section {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          margin-bottom: 2rem;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
          transition: transform 0.2s ease;
        }
        .assumptions-section:hover {
          transform: translateY(-2px);
        }
        .section-title {
          font-size: 1.25rem;
          font-weight: 700;
          color: #1e293b;
          margin-bottom: 1.5rem;
          border-bottom: 2px solid #f1f5f9;
          padding-bottom: 0.75rem;
          display: flex;
          align-items: center;
        }
        .input-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 1.5rem;
        }
        .input-field {
          display: flex;
          flex-direction: column;
        }
        .input-field label {
          font-size: 0.875rem;
          font-weight: 600;
          color: #64748b;
          margin-bottom: 0.5rem;
        }
        .input-field input, .input-field select {
          padding: 0.75rem;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          font-size: 1rem;
          color: #334155;
          transition: all 0.2s;
        }
        .input-field input:focus, .input-field select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        .scenario-effects {
          margin-top: 1.5rem;
          padding: 1rem;
          background: #f8fafc;
          border-radius: 8px;
          border-left: 4px solid #cbd5e1;
        }
        .adjustment-item {
          display: flex;
          justify-content: space-between;
          padding: 0.5rem 0;
          font-size: 0.9375rem;
          font-weight: 500;
        }
        .save-bar {
          position: sticky;
          bottom: 2rem;
          background: rgba(255, 255, 255, 0.9);
          backdrop-filter: blur(8px);
          padding: 1rem 2rem;
          border-radius: 12px;
          box-shadow: 0 -10px 15px -3px rgba(0, 0, 0, 0.1);
          display: flex;
          justify-content: space-between;
          align-items: center;
          z-index: 10;
        }
        .image-preview {
          width: 100%;
          height: 120px;
          border-radius: 8px;
          object-fit: cover;
          margin-top: 1rem;
          border: 1px solid #e2e8f0;
        }
      `}</style>

      <div className="assumptions-section">
        <h3 className="section-title">Portfolio Appearance</h3>
        <div className="input-grid">
          <div className="input-field" style={{ gridColumn: 'span 2' }}>
            <label>Cover Image URL (Immersive Dashboard Card)</label>
            <input 
              type="url" 
              value={coverImage} 
              onChange={(e) => setCoverImage(e.target.value)}
              placeholder="https://images.unsplash.com/photo-..."
              disabled={!canEdit}
            />
          </div>
          <div className="input-field">
            <label>Portfolio Developer</label>
            <input 
              type="text" 
              value={assumptions.developer || ""} 
              onChange={(e) => handleInputChange('developer', e.target.value)}
              placeholder="Developer Name"
              disabled={!canEdit}
            />
          </div>
        </div>
        {coverImage && <img src={coverImage} alt="Preview" className="image-preview" onError={(e) => (e.currentTarget.style.display = 'none')} />}
        <p style={{fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.5rem'}}>
          Provide a high-resolution URL for the dashboard card and the developer name for the portfolio.
        </p>
      </div>

      <div className="assumptions-section">
        <h3 className="section-title">Portfolio Timeline</h3>
        <div className="input-grid">
          <div className="input-field">
            <label>Portfolio Inception Date</label>
            <input 
              type="date" 
              value={assumptions.inception_date} 
              onChange={(e) => handleInputChange('inception_date', e.target.value)}
              disabled={!canEdit}
            />
          </div>
          <div className="input-field">
            <label>Forecast Horizon (Years)</label>
            <input 
              type="number" 
              value={assumptions.forecast_horizon} 
              onChange={(e) => handleInputChange('forecast_horizon', parseInt(e.target.value))}
              disabled={!canEdit}
            />
          </div>
        </div>
      </div>

      <div className="assumptions-section">
        <h3 className="section-title">Default Rates (%)</h3>
        <div className="input-grid">
          <div className="input-field">
            <label>Appreciation Rate</label>
            <input 
              type="number" step="0.01"
              value={assumptions.default_appreciation_rate} 
              onChange={(e) => handleInputChange('default_appreciation_rate', e.target.value)}
              disabled={!canEdit}
            />
          </div>
          <div className="input-field">
            <label>Rental Growth Rate</label>
            <input 
              type="number" step="0.01"
              value={assumptions.default_rental_growth_rate} 
              onChange={(e) => handleInputChange('default_rental_growth_rate', e.target.value)}
              disabled={!canEdit}
            />
          </div>
          <div className="input-field">
            <label>Vacancy Rate</label>
            <input 
              type="number" step="0.01"
              value={assumptions.default_vacancy_rate} 
              onChange={(e) => handleInputChange('default_vacancy_rate', e.target.value)}
              disabled={!canEdit}
            />
          </div>
          <div className="input-field">
            <label>Discount Rate (NPV)</label>
            <input 
              type="number" step="0.01"
              value={assumptions.default_discount_rate} 
              onChange={(e) => handleInputChange('default_discount_rate', e.target.value)}
              disabled={!canEdit}
            />
          </div>
        </div>
      </div>

      <div className="assumptions-section">
        <h3 className="section-title">Fees and Costs (%)</h3>
        <div className="input-grid">
          <div className="input-field">
            <label>Acquisition Fee</label>
            <input 
              type="number" step="0.01"
              value={assumptions.acquisition_fee_percentage} 
              onChange={(e) => handleInputChange('acquisition_fee_percentage', e.target.value)}
              disabled={!canEdit}
            />
          </div>
          <div className="input-field">
            <label>Property Mgmt Fee</label>
            <input 
              type="number" step="0.01"
              value={assumptions.property_mgmt_fee_percentage} 
              onChange={(e) => handleInputChange('property_mgmt_fee_percentage', e.target.value)}
              disabled={!canEdit}
            />
          </div>
          <div className="input-field">
            <label>Maintenance (Annual)</label>
            <input 
              type="number" step="0.01"
              value={assumptions.maintenance_percentage_of_value} 
              onChange={(e) => handleInputChange('maintenance_percentage_of_value', e.target.value)}
              disabled={!canEdit}
            />
          </div>
          <div className="input-field">
            <label>Selling Fee</label>
            <input 
              type="number" step="0.01"
              value={assumptions.selling_fee_percentage} 
              onChange={(e) => handleInputChange('selling_fee_percentage', e.target.value)}
              disabled={!canEdit}
            />
          </div>
        </div>
      </div>

      <div className="assumptions-section">
        <h3 className="section-title">Scenario Analysis</h3>
        <div className="input-grid">
          <div className="input-field">
            <label>Active Scenario</label>
            <select 
              value={assumptions.active_scenario} 
              onChange={(e) => handleInputChange('active_scenario', e.target.value)}
              disabled={!canEdit}
              style={{
                borderColor: assumptions.active_scenario === 'BULL' ? '#10b981' : assumptions.active_scenario === 'BEAR' ? '#ef4444' : '#e2e8f0',
                background: assumptions.active_scenario === 'BULL' ? '#f0fdf4' : assumptions.active_scenario === 'BEAR' ? '#fef2f2' : 'white'
              }}
            >
              <option value="BASE">Base Case</option>
              <option value="BULL">Bull Case</option>
              <option value="BEAR">Bear Case</option>
            </select>
          </div>
        </div>

        <div className="scenario-effects" style={{ borderLeftColor: assumptions.active_scenario === 'BULL' ? '#10b981' : assumptions.active_scenario === 'BEAR' ? '#ef4444' : '#cbd5e1' }}>
          <h4 style={{margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#64748b'}}>Applied Adjustments</h4>
          {!adjustments ? (
            <div style={{color: '#94a3b8', fontStyle: 'italic', fontSize: '0.9375rem'}}>no effects applied</div>
          ) : (
            adjustments.map((adj, i) => (
              <div key={i} className="adjustment-item">
                <span>{adj.label}</span>
                <span style={{color: adj.color}}>{adj.value}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {canEdit && (
        <div className="save-bar">
          <div className="status-message">
            {message && (
              <span style={{ color: message.type === 'success' ? '#10b981' : '#ef4444', fontWeight: 600 }}>
                {message.type === 'success' ? '✓' : '✗'} {message.text}
              </span>
            )}
          </div>
          <button 
            className="btn btn-primary" 
            onClick={handleSave} 
            disabled={saving}
            style={{ minWidth: '150px' }}
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      )}
    </div>
  );
};

export default RealEstateAssumptionsTab;
