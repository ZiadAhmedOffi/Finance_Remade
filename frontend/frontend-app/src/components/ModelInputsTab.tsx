import React, { useState, useEffect } from "react";
import { fundsApi } from "../api/api";

interface ModelInputsTabProps {
  fundId: string;
  canEdit: boolean;
}

/**
 * Interface representing the configurable parameters for a fund's financial model.
 */
interface ModelInputData {
  target_fund_size: number;
  inception_year: number;
  fund_life: number;
  investment_period: number;
  exit_horizon: number;
  min_investor_ticket: number;
  max_investor_ticket: number;
  lock_up_period: number;
  preferred_return: number;
  management_fee: number;
  admin_cost: number;
  least_expected_moic_tier_1: number;
  least_expected_moic_tier_2: number;
  tier_1_carry: number;
  tier_2_carry: number;
  tier_3_carry: number;
  failure_rate: number;
  break_even_rate: number;
  high_growth_rate: number;
  dilution_rate: number;
}

/**
 * ModelInputsTab Component
 * 
 * Allows users to view and update critical fund modeling parameters.
 * Calculates real-time summaries like Average Ticket and Expected Number of Investors.
 * 
 * @param {string} fundId - The unique identifier of the fund.
 * @param {boolean} canEdit - Flag indicating if the current user has write permissions.
 */
const ModelInputsTab: React.FC<ModelInputsTabProps> = ({ fundId, canEdit }) => {
  const [data, setData] = useState<ModelInputData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [ingestDetails, setIngestDetails] = useState<any>(null);

  /**
   * Fetches the current model inputs from the API.
   * Handles string-to-number conversion for Decimal fields returned by Django.
   */
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fundsApi.getModelInputs(fundId);
        const numericData = { ...response.data };
        Object.keys(numericData).forEach(key => {
          if (typeof numericData[key] === 'string' && !isNaN(parseFloat(numericData[key]))) {
            numericData[key] = parseFloat(numericData[key]);
          }
        });
        setData(numericData);
      } catch (err) {
        setError("Failed to fetch model inputs.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [fundId]);

  /**
   * Syncs local state with form input changes.
   */
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    if (data) {
      const val = value === "" ? 0 : parseFloat(value);
      setData({ ...data, [name]: isNaN(val) ? 0 : val });
    }
  };

  /**
   * Persists the updated model inputs to the backend.
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data) return;

    // Validation: Rates must sum to 100
    const sum = Number(data.failure_rate) + Number(data.break_even_rate) + Number(data.high_growth_rate);
    if (Math.abs(sum - 100) > 0.01) {
      setError("Failure, Break-even, and High Growth rates must sum to exactly 100%.");
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    try {
      await fundsApi.updateModelInputs(fundId, data);
      setMessage("Model inputs updated successfully.");
      setTimeout(() => setMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to update model inputs.");
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const response = await fundsApi.downloadExcelTemplate(fundId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `fund_${fundId}_template.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert("Failed to download template.");
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!window.confirm("Ingesting this Excel file will overwrite existing model inputs and append the deals to this fund's already exisiting deals. Are you sure?")) {
      e.target.value = "";
      return;
    }

    setUploading(true);
    setIngestDetails(null);
    setError(null);
    try {
      const response = await fundsApi.uploadExcelData(fundId, file);
      setIngestDetails(response.data.details);
      setMessage("Data ingested successfully!");
      // Reload inputs
      const reload = await fundsApi.getModelInputs(fundId);
      setData(reload.data);
    } catch (err: any) {
      const errorData = err.response?.data;
      if (errorData?.threat_type === "MACRO_DETECTED") {
        setError("SECURITY ALERT: Malicious content detected. Your account has been flagged.");
      } else {
        setError(errorData?.error || "Ingestion failed.");
        setIngestDetails(errorData?.details); // Might contain specific row errors
      }
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  if (loading) return <div>Loading model inputs...</div>;

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!data) return null;

  // Derive secondary metrics from raw inputs
  const minTicket = Number(data.min_investor_ticket) || 0;
  const maxTicket = Number(data.max_investor_ticket) || 0;
  const targetSize = Number(data.target_fund_size) || 0;

  const averageTicket = (minTicket + maxTicket) / 2;
  const expectedNumberInvestors = averageTicket > 0 ? Math.ceil(targetSize / averageTicket) : 0;

  return (
    <div className="model-inputs-tab">
      {/* Real-time Calculation Summary */}
      <div className="content-card" style={{background: '#f0f7ff', borderColor: '#007bff', marginBottom: '3rem'}}>
        <div style={{display: 'flex', justifyContent: 'space-around', gap: '2rem', flexWrap: 'wrap', textAlign: 'center'}}>
          <div className="summary-item">
            <label style={{color: '#0056b3', fontSize: '1rem'}}>Average Ticket (Calculated)</label>
            <div className="summary-value" style={{fontSize: '2.5rem', fontWeight: '800', color: '#007bff'}}>
              ${averageTicket.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div className="summary-item">
            <label style={{color: '#0056b3', fontSize: '1rem'}}>Expected Number of Investors (Calculated)</label>
            <div className="summary-value" style={{fontSize: '2.5rem', fontWeight: '800', color: '#007bff'}}>
              {expectedNumberInvestors.toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* Excel Ingestion Section */}
      {canEdit && (
        <div className="content-card" style={{border: '1px dashed #cbd5e1', background: '#f8fafc', marginBottom: '3rem'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '2rem'}}>
            <div style={{maxWidth: '600px'}}>
              <h3 style={{border: 'none', marginBottom: '0.5rem'}}>Excel Data Ingestion</h3>
              <p style={{color: '#64748b', fontSize: '0.9rem', margin: 0}}>
                Update all fund data at once using a standardized Excel template.
              </p>
              <p style={{color: '#e74c3c', fontSize: '0.85rem', fontWeight: '600', marginTop: '0.5rem', lineHeight: '1.4'}}>
                Note: Pro-rata (follow-on) deals cannot be uploaded via Excel and must be added manually in the Investment Deals tab.
              </p>
            </div>
            <div style={{display: 'flex', gap: '1rem', alignItems: 'center'}}>
              <button 
                type="button" 
                className="btn btn-secondary" 
                onClick={handleDownloadTemplate}
                style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}
              >
                <span>📥</span> Download Template
              </button>
              <label className={`btn btn-primary ${uploading ? 'disabled' : ''}`} style={{display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: uploading ? 'not-allowed' : 'pointer', margin: 0}}>
                <span>📤</span> {uploading ? 'Processing...' : 'Upload Data'}
                <input type="file" accept=".xlsx" style={{display: 'none'}} onChange={handleFileUpload} disabled={uploading} />
              </label>
            </div>
          </div>
          
          {ingestDetails && (
            <div style={{marginTop: '1.5rem', padding: '1rem', background: error ? '#fff1f2' : '#f0fdf4', borderRadius: '8px', border: `1px solid ${error ? '#fecaca' : '#bbf7d0'}`}}>
              <h4 style={{margin: '0 0 0.5rem 0', fontSize: '0.95rem', color: error ? '#991b1b' : '#166534'}}>
                {error ? 'Ingestion Error Details' : 'Ingestion Summary'}
              </h4>
              {Array.isArray(ingestDetails) ? (
                <ul style={{margin: 0, paddingLeft: '1.5rem', fontSize: '0.85rem', color: '#b91c1c'}}>
                  {ingestDetails.map((err: any, idx: number) => (
                    <li key={idx}>[{err.sheet}] Row {err.row}: {err.message}</li>
                  ))}
                </ul>
              ) : (
                <p style={{margin: 0, fontSize: '0.85rem', color: '#166534'}}>
                  Successfully updated: {ingestDetails.model_inputs} inputs. 
                  Appended: {ingestDetails.current_deals_appended} current deals, {ingestDetails.future_deals_appended} future deals.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Parameter Configuration Form */}
      <form onSubmit={handleSubmit} className="model-inputs-form content-card">

        <div className="form-section">
          <h3>Fund & Timeline</h3>
          <div className="input-grid" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1.5rem'}}>
            <div className="form-group">
              <label>Target Fund Size [USD]</label>
              <input type="number" name="target_fund_size" value={data.target_fund_size} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
            <div className="form-group">
              <label>Inception Year</label>
              <input type="number" name="inception_year" value={data.inception_year} onChange={handleChange} disabled={!canEdit} />
            </div>
            <div className="form-group">
              <label>Fund Life [Years]</label>
              <input type="number" name="fund_life" value={data.fund_life} onChange={handleChange} disabled={!canEdit} />
            </div>
            <div className="form-group">
              <label>Investment Period [Years]</label>
              <input type="number" name="investment_period" value={data.investment_period} onChange={handleChange} disabled={!canEdit} />
            </div>
            <div className="form-group">
              <label>Exit Horizon [Years]</label>
              <input type="number" name="exit_horizon" value={data.exit_horizon} onChange={handleChange} disabled={!canEdit} />
            </div>
            <div className="form-group">
              <label>Lock-up Period [Years]</label>
              <input type="number" name="lock_up_period" value={data.lock_up_period} onChange={handleChange} disabled={!canEdit} />
            </div>
          </div>
        </div>

        <div className="divider-h" />

        <div className="form-section">
          <h3>Tickets & Fees</h3>
          <div className="input-grid" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1.5rem'}}>
            <div className="form-group">
              <label>Minimum Investor Ticket [USD]</label>
              <input type="number" name="min_investor_ticket" value={data.min_investor_ticket} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
            <div className="form-group">
              <label>Maximum Investor Ticket [USD]</label>
              <input type="number" name="max_investor_ticket" value={data.max_investor_ticket} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
            <div className="form-group">
              <label>Preferred Return [%]</label>
              <input type="number" name="preferred_return" value={data.preferred_return} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
            <div className="form-group">
              <label>Management Fee [%]</label>
              <input type="number" name="management_fee" value={data.management_fee} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
            <div className="form-group">
              <label>Admin Cost [%]</label>
              <input type="number" name="admin_cost" value={data.admin_cost} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
          </div>
        </div>

        <div className="divider-h" />

        <div className="form-section">
          <h3>Tiers & Carry</h3>
          <div className="input-grid" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1.5rem'}}>
            <div className="form-group">
              <label>Least Expected MOIC (Tier 1) [x]</label>
              <input type="number" name="least_expected_moic_tier_1" value={data.least_expected_moic_tier_1} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
            <div className="form-group">
              <label>Least Expected MOIC (Tier 2) [x]</label>
              <input type="number" name="least_expected_moic_tier_2" value={data.least_expected_moic_tier_2} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
            <div className="form-group">
              <label>Tier 1 Carry [%]</label>
              <input type="number" name="tier_1_carry" value={data.tier_1_carry} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
            <div className="form-group">
              <label>Tier 2 Carry [%]</label>
              <input type="number" name="tier_2_carry" value={data.tier_2_carry} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
            <div className="form-group">
              <label>Tier 3 Carry [%]</label>
              <input type="number" name="tier_3_carry" value={data.tier_3_carry} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
          </div>
        </div>

        <div className="divider-h" />

        <div className="form-section">
          <h3>Portfolio Outcomes & Rates</h3>
          <div style={{ marginBottom: '1.5rem', padding: '1rem', background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0', fontSize: '0.9rem', color: '#64748b' }}>
            <strong>Note:</strong> Failure, Break-even, and High Growth rates represent the expected distribution of portfolio company outcomes. 
            These three rates <strong>must sum to exactly 100%</strong>.
          </div>
          <div className="input-grid" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1.5rem'}}>
            <div className="form-group">
              <label>Failure Rate [%]</label>
              <input type="number" name="failure_rate" value={data.failure_rate} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
            <div className="form-group">
              <label>Break-even Rate [%]</label>
              <input type="number" name="break_even_rate" value={data.break_even_rate} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
            <div className="form-group">
              <label>High Growth Rate [%]</label>
              <input type="number" name="high_growth_rate" value={data.high_growth_rate} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
            <div className="form-group">
              <label>Dilution Rate [%]</label>
              <input type="number" name="dilution_rate" value={data.dilution_rate} onChange={handleChange} disabled={!canEdit} step="any" />
            </div>
          </div>
        </div>

        {canEdit && (
          <div className="form-actions" style={{marginTop: '2rem', paddingTop: '2rem', borderTop: '1px solid #e2e8f0'}}>
            <button type="submit" className="btn btn-primary">Save Model Inputs</button>
            {message && <div className="alert alert-success" style={{display: 'inline-block', marginLeft: '2rem', marginBottom: 0}}>{message}</div>}
          </div>
        )}
      </form>
    </div>
  );
};

export default ModelInputsTab;
