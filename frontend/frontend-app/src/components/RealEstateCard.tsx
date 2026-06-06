import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";
import {
  AreaChart,
  ResponsiveContainer,
  Area,
} from "recharts";
import LiquidityGauge from "./LiquidityGauge";
import "./RealEstateCard.css";

interface RealEstatePortfolio {
  id: string;
  name: string;
  description: string;
  region: string;
  cover_image?: string;
}

interface RealEstateCardProps {
  portfolio: RealEstatePortfolio;
}

const RealEstateCard: React.FC<RealEstateCardProps> = ({ portfolio }) => {
  const [investorLog, setInvestorLog] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const FALLBACK_IMAGE = "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=2070&auto=format&fit=crop";
  const [imgSrc, setImgSrc] = useState(portfolio.cover_image || FALLBACK_IMAGE);

  useEffect(() => {
    setImgSrc(portfolio.cover_image || FALLBACK_IMAGE);
  }, [portfolio.cover_image]);

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

  if (loading) return <div className="fund-card-immersive skeleton"></div>;

  const currentYear = new Date().getFullYear();
  const graphData = (investorLog?.graph_data || []).filter((item: any) => item.year <= currentYear);
  const m = investorLog?.nav_metrics || {};

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);

  const formatPercent = (val: number) => `${val.toFixed(1)}%`;

  // Calculate Cash Flow YOY
  const cfCurrent = m.annual_cash_flow_current || 0;
  const cfPrev = m.annual_cash_flow_prev || 0;
  const cfChange = cfPrev !== 0 ? ((cfCurrent - cfPrev) / Math.abs(cfPrev)) * 100 : 0;
  const isInitialYear = cfPrev === 0;

  return (
    <div className="fund-card-immersive">
      {/* PART 1: Top Immersive Section */}
      <div className="card-top-section">
        <img 
          src={imgSrc} 
          alt={portfolio.name} 
          className="card-bg-image" 
          onError={() => setImgSrc(FALLBACK_IMAGE)}
        />
        <div className="card-overlay"></div>
        
        <div className="top-content-overlay">
          <header className="top-header">
            <span className="portfolio-tag-badge">Real Estate</span>
            <div className="unit-price-badge">
              ${m.price_per_unit?.toFixed(2)} <small style={{opacity: 0.7, fontSize: '0.6rem'}}>UPU</small>
            </div>
          </header>

          <div className="nav-main-display">
            <div className="nav-label-small">Total NAV</div>
            <div className="nav-value-large">{formatCurrency(m.nav || 0)}</div>
          </div>

          <div className="performance-grid">
            {/* Blurred NAV Chart */}
            <div className="chart-container-blurred">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={graphData}>
                  <defs>
                    <linearGradient id="navGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f39c12" stopOpacity={0.6}/>
                      <stop offset="95%" stopColor="#f39c12" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <Area 
                    type="monotone" 
                    dataKey="portfolio_value" 
                    stroke="#f39c12" 
                    strokeWidth={3}
                    fillOpacity={1} 
                    fill="url(#navGrad)" 
                    isAnimationActive={true}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Top KPIs Side List */}
            <div className="kpi-side-list">
              <div className="kpi-item">
                <span className="lab">Props</span>
                <span className="val">{m.property_count_active}</span>
              </div>
              <div className="kpi-item">
                <span className="lab">Yield</span>
                <span className="val">{formatPercent(m.weighted_net_yield)}</span>
              </div>
              <div className="kpi-item">
                <span className="lab">Occupancy</span>
                <span className="val">{formatPercent(m.weighted_occupancy)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* PART 2: Bottom Operational Section */}
      <div className="card-bottom-section">
        <div className="bottom-metrics-row">
          <div className="region-display">
            <span className="reg-lab">Region</span>
            <span className="reg-val">{portfolio.region || "Global"}</span>
          </div>

          <div className="liquidity-gauge-mini">
            <span className="reg-lab" style={{display: 'block', marginBottom: '0.2rem'}}>Liquidity</span>
            <LiquidityGauge 
              value={m.liquidation_index || 0} 
              portfolioL={0.5} 
              ageFactor={0.1} 
              age={5} 
              fundName=""
              isMini={true}
            />
          </div>

          <div className="cash-flow-yoy">
            <span className="reg-lab">Annual CF</span>
            <span className="cf-val">{formatCurrency(cfCurrent)}</span>
            {!isInitialYear && (
              <div className={`yoy-indicator ${cfChange >= 0 ? 'yoy-up' : 'yoy-down'}`}>
                {cfChange >= 0 ? '▲' : '▼'} {Math.abs(cfChange).toFixed(1)}%
              </div>
            )}
            {isInitialYear && <div className="yoy-indicator" style={{color: '#94a3b8'}}>Initial</div>}
          </div>
        </div>

        <Link to={`/real-estate/${portfolio.id}`} className="view-details-btn">
          View Dashboard &rarr;
        </Link>
      </div>
    </div>
  );
};

export default RealEstateCard;
