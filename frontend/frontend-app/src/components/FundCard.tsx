import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Line
} from "recharts";

interface Fund {
  id: string;
  name: string;
  description: string;
  tag: string;
}

interface FundCardProps {
  fund: Fund;
}

const TAG_COLORS: Record<string, { bg: string, text: string }> = {
  "BIC": { bg: "#EEF2FF", text: "#4338CA" },
  "VC": { bg: "#ECFDF5", text: "#047857" },
  "VS": { bg: "#FFFBEB", text: "#B45309" },
  "AIG": { bg: "#FEF2F2", text: "#B91C1C" },
  "SF": { bg: "#F5F3FF", text: "#6D28D9" },
  "REAL_ESTATE": { bg: "#FFF7ED", text: "#C2410C" },
};

const getTagLabel = (tag: string) => {
  if (tag === "REAL_ESTATE") return "Real estate";
  return tag;
};

/**
 * FundCard Component
 * 
 * An interactive card displayed on the main dashboard.
 * 
 * Key Features:
 * - **Dual-Graph Carousel:** Automatically rotates between a "Capital Injection & Appreciation" 
 *   waterfall chart and a "Base Points" performance chart.
 * - **Hover-Pause:** Auto-rotation pauses when the user hovers over the card.
 * - **Dynamic Data:** Fetches performance analytics asynchronously for the specific fund.
 * - **Metric Badges:** Shows high-level KPIs like MOIC and IRR.
 * 
 * @param {Fund} fund - The fund object containing ID, name, and description.
 */
const FundCard: React.FC<FundCardProps> = ({ fund }) => {
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  /**
   * Fetches fund performance on mount.
   */
  useEffect(() => {
    const fetchPerformance = async () => {
      try {
        const response = await api.get(`/funds/${fund.id}/performance/`);
        setPerformanceData(response.data);
      } catch (err) {
        console.error(`Failed to fetch performance for fund ${fund.id}`, err);
      } finally {
        setLoading(false);
      }
    };
    fetchPerformance();
  }, [fund.id]);

  if (loading) return <div className="fund-card skeleton">Loading...</div>;

  /* --- Analytics Logic --- */

  const { dashboard, current_deals_metrics } = performanceData || {};
  
  // Prepare waterfall chart data
  const waterfallData = dashboard?.performance_table?.map((entry: any, index: number) => {
    const prevEntry = index > 0 ? dashboard.performance_table[index - 1] : null;
    const start_value = prevEntry ? prevEntry.total_portfolio_value_with_prognosis : 0;
    return {
      ...entry,
      start_value: start_value,
      injection: (entry.injection_current ?? 0) + (entry.injection_prognosis ?? 0),
      appreciation: (entry.appreciation_current ?? 0) + (entry.appreciation_prognosis ?? 0)
    };
  }) || [];

  // Formatting Utilities
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);
  const formatCurrencyLong = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);
  const formatPercent = (val: number) => (val * 100).toFixed(1) + "%";

  return (
    <div className="fund-card-revamp">
      <div className="card-carousel-section">
        <div className="chart-view fade-in">
          <h5>Capital Injection & Appreciation</h5>
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={waterfallData} margin={{top: 10, right: 10, left: 0, bottom: 0}}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" tick={{fontSize: 10}} />
              <YAxis tickFormatter={formatCurrency} tick={{fontSize: 10}} width={40} />
              <Tooltip formatter={(value: any) => formatCurrencyLong(Number(value))} />
              <Bar dataKey="start_value" stackId="a" fill="transparent" />
              <Bar dataKey="injection" stackId="a" fill="#3498db" name="Injection" />
              <Bar dataKey="appreciation" stackId="a" fill="#2ecc71" name="Appreciation" />
              <Line type="stepAfter" dataKey="total_portfolio_value_with_prognosis" stroke="#7f8c8d" dot={false} strokeWidth={2} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Fund Metadata */}
      <div className="card-content">
        <div className="card-header-row" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem'}}>
          <div style={{display: 'flex', flexDirection: 'column', gap: '0.25rem'}}>
            <h3 className="fund-name" style={{margin: 0, fontSize: '1.25rem', fontWeight: '700'}}>
                <Link to={`/funds/${fund.id}`} style={{color: '#1e293b', textDecoration: 'none'}}>{fund.name}</Link>
            </h3>
            <span style={{
              alignSelf: 'flex-start',
              padding: '0.1rem 0.6rem',
              borderRadius: '4px',
              fontSize: '0.7rem',
              fontWeight: '700',
              textTransform: 'uppercase',
              backgroundColor: TAG_COLORS[fund.tag]?.bg || '#f1f5f9',
              color: TAG_COLORS[fund.tag]?.text || '#475569'
            }}>
              {getTagLabel(fund.tag)}
            </span>
          </div>
          <div className="metric-badges" style={{display: 'flex', gap: '0.4rem', flexShrink: 0}}>
            <span className="metric-badge moic" title="Prognosis MOIC" style={{background: '#dbeafe', color: '#1e40af', padding: '0.25rem 0.5rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: '600', whiteSpace: 'nowrap'}}>{dashboard?.moic.toFixed(2)}x (Fut)</span>
            <span className="metric-badge moic-past" title="Achieved MOIC" style={{background: '#e2e8f0', color: '#475569', padding: '0.25rem 0.5rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: '600', whiteSpace: 'nowrap'}}>{current_deals_metrics?.moic.toFixed(2)}x (Past)</span>
          </div>
        </div>
        
        <p className="fund-desc" style={{marginBottom: '1rem', fontSize: '0.875rem', color: '#64748b', lineClamp: 2, overflow: 'hidden'}}>{fund.description || "No description provided."}</p>
        
        <div className="stats-container" style={{display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem'}}>
          {/* Current Deals (Past) */}
          <div className="stats-group">
            <h6 style={{fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748b', marginBottom: '0.5rem', fontWeight: '700'}}>Deals Already Made (Past)</h6>
            <div className="quick-stats" style={{display: 'flex', gap: '1.5rem'}}>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>Invested</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600'}}>{formatCurrency(current_deals_metrics?.total_invested)}</span>
              </div>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>Deals</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600'}}>{current_deals_metrics?.total_deals}</span>
              </div>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>Ventures</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600'}}>{current_deals_metrics?.total_companies}</span>
              </div>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>IRR</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600'}}>{formatPercent(current_deals_metrics?.irr)}</span>
              </div>
            </div>
          </div>

          {/* Deal Prognosis (Future) */}
          <div className="stats-group">
            <h6 style={{fontSize: '0.7rem', textTransform: 'uppercase', color: '#3b82f6', marginBottom: '0.5rem', fontWeight: '700'}}>Prognosis for Future Deals (Future)</h6>
            <div className="quick-stats" style={{display: 'flex', gap: '1.5rem'}}>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>To Invest</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600', color: '#1e40af'}}>{formatCurrency(dashboard?.total_invested)}</span>
              </div>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>Est. Deals</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600', color: '#1e40af'}}>{dashboard?.total_deals}</span>
              </div>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>Exp. IRR</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600', color: '#1e40af'}}>{formatPercent(dashboard?.irr)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card-footer" style={{borderTop: '1px solid #f1f5f9', paddingTop: '1rem'}}>
          <Link to={`/funds/${fund.id}`} className="view-btn" style={{width: '100%', textAlign: 'center', display: 'block', background: '#1e293b', color: 'white', padding: '0.6rem', borderRadius: '0.5rem', fontWeight: '600', textDecoration: 'none'}}>
            View Full Analytics &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
};

export default FundCard;
