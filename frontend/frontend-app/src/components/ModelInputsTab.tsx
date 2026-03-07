import React, { useState, useEffect } from "react";
import { fundsApi } from "../api/api";

interface ModelInputsTabProps {
  fundId: string;
  canEdit: boolean;
}

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
}

const ModelInputsTab: React.FC<ModelInputsTabProps> = ({ fundId, canEdit }) => {
  const [data, setData] = useState<ModelInputData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fundsApi.getModelInputs(fundId);
        // Ensure all numeric fields are actually numbers (DRF Decimals come as strings)
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

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    if (data) {
      // Use parseFloat and handle empty string or invalid number
      const val = value === "" ? 0 : parseFloat(value);
      setData({ ...data, [name]: isNaN(val) ? 0 : val });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data) return;
    try {
      await fundsApi.updateModelInputs(fundId, data);
      setMessage("Model inputs updated successfully.");
      setTimeout(() => setMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to update model inputs.");
    }
  };

  if (loading) return <div>Loading model inputs...</div>;
  if (error) return <div className="alert alert-error">{error}</div>;
  if (!data) return null;

  // Real-time calculations with explicit casting
  const minTicket = Number(data.min_investor_ticket) || 0;
  const maxTicket = Number(data.max_investor_ticket) || 0;
  const targetSize = Number(data.target_fund_size) || 0;

  const averageTicket = (minTicket + maxTicket) / 2;
  const expectedNumberInvestors = averageTicket > 0 ? Math.ceil(targetSize / averageTicket) : 0;

  return (
    <div className="model-inputs-tab">
      <div className="calculated-summary-card">
        <div className="summary-item">
          <label>Average Ticket (Calculated)</label>
          <div className="summary-value highlight-value" key={`avg-${averageTicket}`}>
            ${averageTicket.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>
        <div className="summary-item">
          <label>Expected Number of Investors (Calculated)</label>
          <div className="summary-value highlight-value" key={`exp-${expectedNumberInvestors}`}>
            {expectedNumberInvestors.toLocaleString()}
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="model-inputs-form">
        <div className="form-section">
          <h3>Fund & Timeline</h3>
          <div className="input-grid">
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

        <div className="form-section">
          <h3>Tickets & Fees</h3>
          <div className="input-grid">
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

        <div className="form-section">
          <h3>Tiers & Carry</h3>
          <div className="input-grid">
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

        {canEdit && (
          <div className="form-actions">
            {message && <div className="alert alert-success">{message}</div>}
            <button type="submit" className="btn btn-primary">Save Model Inputs</button>
          </div>
        )}
      </form>

      <style>{`
        .model-inputs-tab {
          margin-top: 1rem;
        }
        .calculated-summary-card {
          display: flex;
          gap: 2rem;
          background: #f0f7ff;
          padding: 2rem;
          border-radius: 12px;
          border: 2px solid #007bff;
          margin-bottom: 2rem;
          box-shadow: 0 4px 12px rgba(0,123,255,0.1);
          transition: all 0.3s ease;
        }
        .summary-item {
          flex: 1;
        }
        .summary-item label {
          display: block;
          font-weight: 600;
          color: #0056b3;
          margin-bottom: 0.5rem;
          font-size: 0.9rem;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .summary-value {
          font-size: 2rem;
          font-weight: 800;
          color: #007bff;
          transition: all 0.2s ease;
        }
        .highlight-value {
          display: inline-block;
          animation: pulse 0.4s ease-out;
        }
        @keyframes pulse {
          0% { transform: scale(1); }
          50% { transform: scale(1.05); color: #0056b3; }
          100% { transform: scale(1); }
        }
        .model-inputs-form {
          background: #fff;
          padding: 2rem;
          border-radius: 12px;
          border: 1px solid #eee;
        }
        .form-section {
          margin-bottom: 2.5rem;
        }
        .form-section h3 {
          margin-top: 0;
          margin-bottom: 1.5rem;
          font-size: 1.25rem;
          color: #444;
          border-bottom: 2px solid #f0f0f0;
          padding-bottom: 0.5rem;
        }
        .input-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
          gap: 1.5rem;
        }
        .form-actions {
          display: flex;
          align-items: center;
          gap: 2rem;
          border-top: 1px solid #eee;
          padding-top: 2rem;
        }
        @media (max-width: 768px) {
          .calculated-summary-card {
            flex-direction: column;
            gap: 1.5rem;
          }
        }
      `}</style>
    </div>
  );
};

export default ModelInputsTab;
