import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";
import {
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Line,
  Area
} from "recharts";

interface RealEstatePortfolio {
  id: string;
  name: string;
  description: string;
  region: string;
}

interface RealEstateCardProps {
  portfolio: RealEstatePortfolio;
}

/**
 * RealEstateCard Component
 * 
 * An interactive card displayed on the main dashboard for Real Estate Portfolios.
 * Shows a graph of total NAV from inception to the latest year.
 */
const RealEstateCard: React.FC<RealEstateCardProps> = ({ portfolio }) => {
  const [investorLog, setInvestorLog] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInvestorLog = async () => {
      try {
        const response = await api.get(`/real-estate/${portfolio.id}/investor-log/`);
        setInvestorLog(response.data);
      } catch (err) {
        console.error(`Failed to fetch investor log for portfolio ${portfolio.id}`, err);
      } finally {
        setLoading(false);
      }
    };
    fetchInvestorLog();
  }, [portfolio.id]);

  if (loading) return <div className="fund-card skeleton">Loading...</div>;

  const currentYear = new Date().getFullYear();
  const graphData = (investorLog?.graph_data || []).filter((item: any) => item.year <= currentYear);
  const navMetrics = investorLog?.nav_metrics || {};

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);
  const formatCurrencyLong = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);

  return (
    <div className="fund-card-revamp">
      <div className="card-carousel-section">
        <div className="chart-view fade-in">
          <h5>Total Portfolio NAV (USD)</h5>
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={graphData} margin={{top: 10, right: 10, left: 0, bottom: 0}}>
              <defs>
                <linearGradient id="colorNav" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f39c12" stopOpacity={0.1}/>
                  <stop offset="95%" stopColor="#f39c12" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" tick={{fontSize: 10}} />
              <YAxis tickFormatter={formatCurrency} tick={{fontSize: 10}} width={40} />
              <Tooltip formatter={(value: any) => formatCurrencyLong(Number(value))} />
              <Area type="monotone" dataKey="portfolio_value" stroke="#f39c12" fillOpacity={1} fill="url(#colorNav)" name="NAV" />
              <Line type="monotone" dataKey="portfolio_value" stroke="#e67e22" dot={false} strokeWidth={2} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card-content">
        <div className="card-header-row" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem'}}>
          <div style={{display: 'flex', flexDirection: 'column', gap: '0.25rem'}}>
            <h3 className="fund-name" style={{margin: 0, fontSize: '1.25rem', fontWeight: '700'}}>
                <Link to={`/real-estate/${portfolio.id}`} style={{color: '#1e293b', textDecoration: 'none'}}>{portfolio.name}</Link>
            </h3>
            <span style={{
              alignSelf: 'flex-start',
              padding: '0.1rem 0.6rem',
              borderRadius: '4px',
              fontSize: '0.7rem',
              fontWeight: '700',
              textTransform: 'uppercase',
              backgroundColor: "#FFF7ED",
              color: "#C2410C"
            }}>
              Real Estate
            </span>
          </div>
          <div className="metric-badges" style={{display: 'flex', gap: '0.4rem', flexShrink: 0}}>
            <span className="metric-badge" title="Price Per Unit" style={{background: '#ffedd5', color: '#9a3412', padding: '0.25rem 0.5rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: '600', whiteSpace: 'nowrap'}}>${navMetrics.price_per_unit?.toFixed(2)} / Unit</span>
          </div>
        </div>
        
        <p className="fund-desc" style={{marginBottom: '1rem', fontSize: '0.875rem', color: '#64748b', lineClamp: 2, overflow: 'hidden'}}>{portfolio.description || "No description provided."}</p>
        
        <div className="stats-container" style={{display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem'}}>
          <div className="stats-group">
            <h6 style={{fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748b', marginBottom: '0.5rem', fontWeight: '700'}}>Portfolio Metrics</h6>
            <div className="quick-stats" style={{display: 'flex', gap: '1.5rem'}}>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>Region</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600'}}>{portfolio.region || "N/A"}</span>
              </div>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>NAV</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600'}}>{formatCurrency(navMetrics.nav)}</span>
              </div>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>Reserves</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600'}}>{formatCurrency(navMetrics.cash_reserves)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card-footer" style={{borderTop: '1px solid #f1f5f9', paddingTop: '1rem'}}>
          <Link to={`/real-estate/${portfolio.id}`} className="view-btn" style={{width: '100%', textAlign: 'center', display: 'block', background: '#c2410c', color: 'white', padding: '0.6rem', borderRadius: '0.5rem', fontWeight: '600', textDecoration: 'none'}}>
            View RE Dashboard &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
};

export default RealEstateCard;
