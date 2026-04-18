import React, { useState, useEffect, useMemo, useRef } from "react";
import { useParams } from "react-router-dom";
import { fundsApi } from "../api/api";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  ReferenceLine,
  ReferenceArea,
  Area,
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from "recharts";
import "./PublicReport.css";
import { calculateLiquidityIndex } from "../utils/liquidityUtils";
import LiquidityGauge from "../components/LiquidityGauge";
import FundPerformanceRadarChart from "../components/FundPerformanceRadarChart";

const COLORS = ["#2563eb", "#7c3aed", "#db2777", "#ea580c", "#16a34a", "#0891b2"];

const PublicReportPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [report, setReport] = useState<any>(null);
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Capital Call Specific State
  const [investmentAmount, setInvestmentAmount] = useState<number>(0);
  const [selectedScenario, setSelectedScenario] = useState<string>("Base Case");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchReportData = async () => {
      if (!slug) return;
      try {
        setLoading(true);
        const response = await fundsApi.getPublicReport(slug);
        setReport(response.data);
        setPerformanceData(response.data.performance_data);
        
        // Set default investment amount for capital call report
        if (response.data.report_type === 'CAPITAL_CALL') {
          const minTicket = parseFloat(response.data.fund_details?.model_inputs?.min_investor_ticket || 0);
          setInvestmentAmount(minTicket);
        }
      } catch (err: any) {
        setError(err.response?.data?.error || "Report not found or inactive.");
      } finally {
        setLoading(false);
      }
    };

    fetchReportData();
  }, [slug]);

  // Auto-scroll logic for "Why Invest"
  useEffect(() => {
    const scrollContainer = scrollRef.current;
    if (!scrollContainer || !report?.fund_details?.reasons_to_invest?.length) return;

    let intervalId: any;
    
    const startScrolling = () => {
      intervalId = setInterval(() => {
        if (scrollContainer.scrollLeft + scrollContainer.clientWidth >= scrollContainer.scrollWidth - 5) {
          scrollContainer.scrollLeft = 0;
        } else {
          scrollContainer.scrollLeft += 1;
        }
      }, 30);
    };

    startScrolling();

    const handleMouseEnter = () => clearInterval(intervalId);
    const handleMouseLeave = () => startScrolling();

    scrollContainer.addEventListener('mouseenter', handleMouseEnter);
    scrollContainer.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      clearInterval(intervalId);
      scrollContainer.removeEventListener('mouseenter', handleMouseEnter);
      scrollContainer.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [report]);

  const { 
    dashboard, 
    current_deals_metrics, 
    current_deals = [], 
    investment_deals = [],
    aggregated_exits = []
  } = performanceData || {};

  const cIrr = current_deals_metrics?.irr || 0;

  const fundIrr = useMemo(() => {
    const dIrr = dashboard?.irr || 0;
    return Math.max(dIrr, cIrr);
  }, [dashboard, cIrr]);

  const currentYear = dashboard?.current_year || new Date().getFullYear();

  // Formatting Utilities
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);

  const formatCurrencyLong = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);
  
  const formatPercent = (val: number) => (val * 100).toFixed(2) + "%";
  const formatMultiple = (val: number) => val.toFixed(2) + "x";

  const avgMoic = useMemo(() => {
    const achieved = current_deals_metrics?.moic || 0;
    const target = dashboard?.moic || 0;
    return (achieved + target) / 2;
  }, [current_deals_metrics, dashboard]);

  // --- Dynamic Report Logic ---

  const waterfallData = useMemo(() => {
    if (!dashboard?.performance_table) return [];
    return dashboard.performance_table.map((entry: any, index: number) => {
      const prevEntry = index > 0 ? dashboard.performance_table[index - 1] : null;
      const startValue = prevEntry ? prevEntry.total_portfolio_value_with_prognosis : 0;
      return {
        ...entry,
        startValue: startValue
      };
    });
  }, [dashboard]);

  const { chartDataSectorCount, chartDataSectorCapital } = useMemo(() => {
    const allDeals = [...current_deals, ...investment_deals];
    const sectorCounts: any = {};
    const sectorCapital: any = {};

    allDeals.forEach(deal => {
      const sector = deal.company_type || "Other";
      sectorCounts[sector] = (sectorCounts[sector] || 0) + 1;
      sectorCapital[sector] = (sectorCapital[sector] || 0) + parseFloat(deal.amount_invested || 0);
    });

    return {
      chartDataSectorCount: Object.keys(sectorCounts).map(name => ({ name, value: sectorCounts[name] })),
      chartDataSectorCapital: Object.keys(sectorCapital).map(name => ({ name, value: sectorCapital[name] }))
    };
  }, [current_deals, investment_deals]);

  // --- Capital Call Report Logic ---

  const cashFlowProjectionData = useMemo(() => {
    if (!report || report.report_type !== 'CAPITAL_CALL' || !aggregated_exits.length) return [];

    const scenario = aggregated_exits.find((c: any) => c.case === selectedScenario) || aggregated_exits[0];
    const irr = scenario.irr || 0;
    
    const inceptionYear = report.fund_details?.model_inputs?.inception_year || currentYear;
    const fundLife = report.fund_details?.model_inputs?.fund_life || 10;
    const endYear = inceptionYear + fundLife;
    
    const data = [];
    let currentValue = investmentAmount;
    
    for (let yr = currentYear; yr <= endYear; yr++) {
      data.push({
        year: yr,
        value: currentValue,
        investment: yr === currentYear ? investmentAmount : 0,
        growth: yr > currentYear ? currentValue - investmentAmount : 0,
        base: yr > currentYear ? investmentAmount : 0,
        isLockup: yr < (inceptionYear + (report.fund_details?.model_inputs?.lock_up_period || 0))
      });
      currentValue = currentValue * (1 + irr);
    }
    
    return data;
  }, [report, selectedScenario, investmentAmount, aggregated_exits, currentYear]);

  const lockupEndYear = report?.fund_details?.model_inputs?.inception_year + (report?.fund_details?.model_inputs?.lock_up_period || 0);
  const maturityYear = report?.fund_details?.model_inputs?.inception_year + report?.fund_details?.model_inputs?.fund_life;
  const hideLockup = lockupEndYear <= currentYear;

  const liData = performanceData ? calculateLiquidityIndex(
    performanceData.current_deals || [],
    performanceData.admin_fee?.inception_year || new Date().getFullYear()
  ) : null;

  const comparisons = [
    { name: 'Public Equities (S&P 500)', li: 5 },
    { name: 'Gold', li: 2 },
    { name: 'Commodities (ETF)', li: 10 },
    { name: 'Our Fund', li: liData?.finalLI || 0, isCurrent: true },
    { name: 'Private Equity (Avg)', li: 75 },
    { name: 'Real Estate (Direct)', li: 85 },
  ];

  if (loading) return (
    <div className="report-loading-container">
      <div className="spinner"></div>
      <p>Preparing institutional report...</p>
    </div>
  );
  
  if (error) return (
    <div className="report-error-container">
      <div className="error-card">
        <h1>Access Restricted</h1>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Retry Access</button>
      </div>
    </div>
  );

  if (report.report_type === 'DYNAMIC') {
    return (
      <div className="public-report-layout">
        <svg width="0" height="0" style={{ position: 'absolute' }}>
          <defs>
            <pattern id="hash-injection" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="10" height="10" fill="#3498db" />
              <line x1="0" y1="0" x2="0" y2="10" stroke="white" strokeWidth="4" />
            </pattern>
            <pattern id="hash-appreciation" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="10" height="10" fill="#2ecc71" />
              <line x1="0" y1="0" x2="0" y2="10" stroke="white" strokeWidth="4" />
            </pattern>
          </defs>
        </svg>

        <header className="report-header">
          <div className="report-container">
            <div className="report-brand">FinanceRemade | Institutional Reporting</div>
            <div className="report-title">
              <h1>{report.name}</h1>
              <span className="fund-tag">{report.fund_name}</span>
            </div>
            <div className="report-meta">
              Investment Portfolio Status Update • Generated on {new Date(report.created_at).toLocaleDateString(undefined, { dateStyle: 'full' })}
            </div>
          </div>
        </header>

        <main className="report-container">
          <section className="report-section">
            <div className="report-section-header"><h2>Executive Summary</h2></div>
            <p className="prose-text">
              This report provides a comprehensive overview of the fund's current standing, realized returns, and future growth projections. 
              As of {currentYear}, the portfolio shows strong resilience with a current MOIC of <strong>{formatMultiple(current_deals_metrics?.moic)}</strong> 
              and a projected IRR of <strong>{formatPercent(dashboard?.irr)}</strong> upon full deployment.
            </p>
            
            <div className="metrics-grid">
              <div className="metric-card-revamp past">
                <span className="card-icon">💼</span>
                <span className="metric-label">Realized MOIC</span>
                <span className="metric-value">{formatMultiple(current_deals_metrics?.moic)}</span>
              </div>
              <div className="metric-card-revamp future">
                <span className="card-icon">🚀</span>
                <span className="metric-label">Target IRR</span>
                <span className="metric-value">{formatPercent(dashboard?.irr)}</span>
              </div>
              <div className="metric-card-revamp past">
                <span className="card-icon">💰</span>
                <span className="metric-label">Capital Deployed</span>
                <span className="metric-value">{formatCurrency(current_deals_metrics?.total_invested)}</span>
              </div>
              <div className="metric-card-revamp future">
                <span className="card-icon">📈</span>
                <span className="metric-label">Projected Value</span>
                <span className="metric-value">{formatCurrency(dashboard?.gross_exit_value)}</span>
              </div>
            </div>
          </section>

          <section className="report-section">
            <div className="report-section-header"><h2>Portfolio Diversification</h2></div>
            <div className="charts-row">
              <div className="chart-wrapper">
                <h3>Allocation by Deal Count</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={chartDataSectorCount} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}>
                      {chartDataSectorCount.map((_, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="chart-wrapper">
                <h3>Allocation by Capital Deployed</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={chartDataSectorCapital} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}>
                      {chartDataSectorCapital.map((_, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                    </Pie>
                    <Tooltip formatter={(v: any) => formatCurrency(Number(v))} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          <section className="report-section">
            <div className="report-section-header"><h2>Growth Dynamics</h2></div>
            <div className="chart-wrapper">
              <h3>Annual Portfolio Value Expansion</h3>
              <ResponsiveContainer width="100%" height={400}>
                <ComposedChart data={waterfallData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="year" />
                  <YAxis tickFormatter={formatCurrency} />
                  <Tooltip formatter={(value: any) => formatCurrencyLong(Number(value))} />
                  <Legend />
                  <ReferenceLine x={currentYear} stroke="#ef4444" strokeDasharray="3 3" label={{ position: 'top', value: 'Current', fill: '#ef4444' }} />
                  <Bar dataKey="startValue" stackId="a" fill="transparent" legendType="none" />
                  <Bar dataKey="injection_current" stackId="a" fill="#3b82f6" name="Past Injections" />
                  <Bar dataKey="injection_prognosis" stackId="a" fill="url(#hash-injection)" name="Future Injections" />
                  <Bar dataKey="appreciation_current" stackId="a" fill="#10b981" name="Past Appreciation" />
                  <Bar dataKey="appreciation_prognosis" stackId="a" fill="url(#hash-appreciation)" name="Future Appreciation" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="report-section">
            <div className="report-section-header"><h2>Strategic Performance Trajectory</h2></div>
            <p className="prose-text">
              The following radar visualization provides an integrated view of the fund's efficiency and growth. 
              The solid line tracks the <strong>Total Portfolio Value</strong>, while 
              <strong>MOIC multiples</strong> and <strong>IRR performance</strong> are integrated into the 
              multi-dimensional assessment, visible on hover for each year.
            </p>
            <FundPerformanceRadarChart 
              data={dashboard?.performance_table || []} 
              irr={cIrr} 
            />
          </section>

          <section className="report-section">
            <div className="report-section-header"><h2>Scenario Sensitivity Analysis</h2></div>
            <div className="table-wrapper">
              <table className="modern-table">
                <thead>
                  <tr>
                    <th>Performance Metric</th>
                    {aggregated_exits.map((c: any) => <th key={c.case}>{c.case}</th>)}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><strong>Gross Exit Value</strong></td>
                    {aggregated_exits.map((c: any) => <td key={c.case}>{formatCurrency(c.gev)}</td>)}
                  </tr>
                  <tr>
                    <td><strong>Gross MOIC</strong></td>
                    {aggregated_exits.map((c: any) => <td key={c.case}>{formatMultiple(c.gross_moic)}</td>)}
                  </tr>
                  <tr>
                    <td><strong>Net to Investors</strong></td>
                    {aggregated_exits.map((c: any) => <td key={c.case}>{formatCurrency(c.net_to_investors)}</td>)}
                  </tr>
                  <tr>
                    <td><strong>Net IRR</strong></td>
                    {aggregated_exits.map((c: any) => <td key={c.case}>{formatPercent(c.irr)}</td>)}
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </main>

        <footer className="report-footer">
          <div className="report-container">
            <div className="report-brand">FinanceRemade</div>
            <p>© 2026 FinanceRemade Asset Management. All rights reserved.</p>
          </div>
        </footer>
      </div>
    );
  }

  // --- Capital Call Report View ---
  return (
    <div className="public-report-layout capital-call-theme">
      
      {/* 1. COVER SECTION */}
      <section className="cover-section" style={{ 
        position: 'relative', 
        minHeight: '60vh', 
        display: 'flex', 
        alignItems: 'center',
        background: '#0f172a',
        overflow: 'hidden'
      }}>
        <div className="cover-image-container" style={{ 
          position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', zIndex: 0 
        }}>
          <img 
            src="/Stock-Market-Arrows-iStock.jpg" 
            alt="Fund Cover" 
            style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
          />
          {/* Dark Overlay */}
          <div style={{ 
            position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', 
            background: 'linear-gradient(to bottom, rgba(15, 23, 42, 0.45), rgba(15, 23, 42, 0.55))' 
          }} />
        </div>
        
        <div className="cover-content report-container" style={{ position: 'relative', zIndex: 1, textAlign: 'center' }}>
          <h1 className="capital-call-title" style={{ fontSize: '4rem', marginBottom: '1rem', color: 'white' }}>{report.name}</h1>
          
          <div className="badge-row" style={{ justifyContent: 'center', marginBottom: '2rem' }}>
            {report.fund_details?.sharia_compliant && <span className="premium-badge sharia">Sharia Compliant</span>}
            {report.fund_details?.region && <span className="premium-badge region">{report.fund_details.region}</span>}
            {report.fund_details?.tag && <span className="premium-badge focus">{report.fund_details.tag}</span>}
          </div>

          <p className="fund-subheadline" style={{ maxWidth: '800px', margin: '0 auto 3rem', fontSize: '1.2rem', opacity: 0.9, color: 'white' }}>
            {report.fund_details?.description}
          </p>
          
          <div style={{ display: 'flex', justifyContent: 'center', gap: '4rem' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', fontWeight: '900', color: '#60a5fa' }}>{formatCurrency(report.config_json?.target_capital)}</div>
              <div style={{ fontSize: '0.9rem', textTransform: 'uppercase', opacity: 0.8, letterSpacing: '0.15em', marginTop: '0.5rem', color: 'white' }}>Target Capital</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', fontWeight: '900', color: '#34d399' }}>{formatCurrency(report.config_json?.capital_raised)}</div>
              <div style={{ fontSize: '0.9rem', textTransform: 'uppercase', opacity: 0.8, letterSpacing: '0.15em', marginTop: '0.5rem', color: 'white' }}>Already Raised</div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. KEY FUND METRICS */}
      <section className="metrics-section report-container">
        <div className="modern-metrics-container">
          
          {/* Row 1: Core Performance & Timing */}
          <div className="metrics-row">
            <div className="metric-card-modern">
              <div className="m-icon">📊</div>
              <span className="m-label">Avg. MOIC</span>
              <span className="m-value">{formatMultiple(avgMoic)}</span>
            </div>
            
            <div className="metric-card-modern">
              <div className="m-icon">⏳</div>
              <span className="m-label">Investment Period</span>
              <span className="m-value">{report.fund_details?.model_inputs?.investment_period} Years</span>
            </div>
            
            {!hideLockup && (
              <div className="metric-card-modern">
                <div className="m-icon">🔒</div>
                <span className="m-label">Lockup Period</span>
                <span className="m-value">{report.fund_details?.model_inputs?.lock_up_period} Years</span>
              </div>
            )}
            
            <div className="metric-card-modern">
              <div className="m-icon">💱</div>
              <span className="m-label">Currency</span>
              <span className="m-value">USD</span>
            </div>
          </div>

          {/* Row 2: Strategy, Structure & Return */}
          <div className="metrics-row secondary">
            <div className="metric-card-modern">
              <div className="m-icon">📈</div>
              <span className="m-label">Annualized Return</span>
              <span className="m-value">{formatPercent(fundIrr)}</span>
              <div className="m-subvalue">
                <span>Yield: 0%</span>
                <span className="highlight">Gain: {formatPercent(fundIrr)}</span>
              </div>
            </div>

            <div className="metric-card-modern">
              <div className="m-icon">🎯</div>
              <span className="m-label">Strategy</span>
              <span className="m-value" style={{ fontSize: '1.1rem' }}>{report.fund_details?.strategy || 'N/A'}</span>
            </div>

            <div className="metric-card-modern">
              <div className="m-icon">🏗️</div>
              <span className="m-label">Structure</span>
              <span className="m-value" style={{ fontSize: '1.1rem' }}>{report.fund_details?.structure || 'N/A'}</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. OVERVIEW SECTION */}
      {report.fund_details?.overview && (
        <section className="overview-section report-container">
          <div className="section-title-premium"><h2>Opportunity Overview</h2></div>
          <div className="prose-container">
            <p className="prose-text-large">{report.fund_details.overview}</p>
          </div>
        </section>
      )}

      {/* 4. INTRINSIC VALUE & LIQUIDITY SECTION */}
      <section className="stability-section report-container" style={{ marginTop: '4rem' }}>
        <div className="section-title-premium"><h2>Portfolio Stability & Liquidity</h2></div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem', marginBottom: '3rem' }}>
          <div className="content-card" style={{ padding: '2rem' }}>
            <h3 style={{ textAlign: 'center', marginBottom: '2rem', border: 'none' }}>Intrinsic Value Radar</h3>
            <div style={{ width: '100%', height: 400 }}>
              <ResponsiveContainer>
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={(() => {
                  const currentDeals = performanceData.current_deals || [];
                  const companyMap = new Map();
                  currentDeals.forEach((d: any) => {
                    if (!companyMap.has(d.company_name)) {
                      const entryVal = parseFloat(d.entry_valuation);
                      const currentVal = parseFloat(d.latest_valuation);
                      const exitMultiple = parseFloat(d.expected_exit_multiple || 5.0);
                      const targetVal = entryVal * exitMultiple;
                      companyMap.set(d.company_name, {
                        subject: d.company_name,
                        entry: targetVal > 0 ? (entryVal / targetVal) * 100 : 0,
                        current: targetVal > 0 ? (currentVal / targetVal) * 100 : 0,
                        expected: 100
                      });
                    }
                  });
                  return Array.from(companyMap.values());
                })()}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: '0.7rem' }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name="Entry" dataKey="entry" stroke="#3498db" fill="#3498db" fillOpacity={0.4} />
                  <Radar name="Current" dataKey="current" stroke="#2ecc71" fill="#2ecc71" fillOpacity={0.5} />
                  <Radar name="Target" dataKey="expected" stroke="#10b981" fill="transparent" strokeDasharray="5 5" />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <p style={{ marginTop: '1.5rem', fontSize: '0.9rem', color: '#64748b', lineHeight: '1.6', textAlign: 'center' }}>
              The Intrinsic Value graph visualizes each portfolio company's journey from entry valuation towards its target exit valuation. 
              The solid areas show historical and current progress, while the dashed line represents the strategic exit objective.
            </p>
          </div>

          <div className="content-card" style={{ padding: '2rem' }}>
            <h3 style={{ textAlign: 'center', marginBottom: '1rem', border: 'none' }}>Liquidity Index</h3>
            <p style={{ textAlign: 'center', color: '#64748b', fontSize: '0.85rem', marginBottom: '2rem' }}>Path to realization & market benchmark</p>
            
            <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {liData && (
                <LiquidityGauge 
                  value={liData.finalLI} 
                  portfolioL={liData.portfolioL} 
                  ageFactor={liData.ageFactor} 
                  age={liData.age} 
                />
              )}
            </div>

            <div style={{ marginTop: '2rem' }}>
              <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#1e293b', marginBottom: '1rem', border: 'none' }}>Liquidity Benchmarks</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                {comparisons.sort((a, b) => a.li - b.li).map((comp) => (
                  <div key={comp.name} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <span style={{ fontSize: '0.7rem', color: '#64748b', width: '140px' }}>{comp.name}</span>
                    <div style={{ flex: 1, height: '4px', backgroundColor: '#e2e8f0', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{ 
                        width: `${comp.li}%`, height: '100%', 
                        background: comp.isCurrent ? '#3b82f6' : '#94a3b8'
                      }} />
                    </div>
                    <span style={{ fontSize: '0.7rem', fontWeight: '700', color: '#1e293b', width: '35px' }}>{comp.li.toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
            <p style={{ marginTop: '1.5rem', fontSize: '0.9rem', color: '#64748b', lineHeight: '1.6', textAlign: 'center' }}>
              Our Liquidity Index assesses the portfolio's maturity and realization potential. 
              A lower percentage indicates higher liquidity (easier to exit), comparing our fund against standard asset classes.
            </p>
          </div>
        </div>
      </section>

      {/* 5. STRATEGIC RADAR PERFORMANCE */}
      <section className="radar-section report-container" style={{ marginTop: '6rem' }}>
        <div className="section-title-premium"><h2>Performance Dynamics</h2></div>
        <FundPerformanceRadarChart 
          data={dashboard?.performance_table || []} 
          irr={cIrr} 
        />
      </section>

      {/* 6. CASH FLOW PROJECTION (CORE) */}
      <section className="projection-section report-container">
        <div className="section-title-premium"><h2>Cash Flow Projection</h2></div>
        
        <div className="projection-controls">
          <div className="control-group">
            <label>Investment Amount (USD)</label>
            <input 
              type="number" 
              value={investmentAmount} 
              onChange={(e) => setInvestmentAmount(parseFloat(e.target.value) || 0)}
              className="premium-input"
            />
          </div>
          <div className="control-group">
            <label>Growth Scenario</label>
            <div className="scenario-pills">
              {aggregated_exits.map((c: any) => (
                <button 
                  key={c.case} 
                  className={`pill ${selectedScenario === c.case ? 'active' : ''}`}
                  onClick={() => setSelectedScenario(c.case)}
                >
                  {c.case}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="chart-container-premium">
          <div style={{ marginBottom: '2rem', padding: '1rem', background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0', fontSize: '0.9rem', color: '#64748b' }}>
            <strong>Understanding the Projection:</strong> This graph illustrates the projected growth of your investment over the fund's lifecycle. 
            The <strong>Blue Bar</strong> represents your initial investment in the current year. 
            The <strong>Green Bars</strong> show the projected capital appreciation starting from your initial investment base. 
            The dashed lines indicate key fund milestones like the end of the lockup period and the secondary market window.
          </div>

          <ResponsiveContainer width="100%" height={450}>
            <ComposedChart data={cashFlowProjectionData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="year" axisLine={false} tickLine={false} tick={{ fill: '#64748b' }} />
              <YAxis tickFormatter={formatCurrency} axisLine={false} tickLine={false} tick={{ fill: '#64748b' }} />
              <Tooltip 
                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}
                formatter={(v: any) => [formatCurrencyLong(v), "Projected Value"]}
              />
              
              {!hideLockup && (
                <ReferenceArea 
                  x1={currentYear} 
                  x2={lockupEndYear} 
                  fill="#d97706" 
                  fillOpacity={0.15}
                  strokeOpacity={0}
                  label={{ value: 'Lockup', position: 'top', fill: '#d97706', fontSize: 10, fontWeight: '700', offset: 10 }}
                />
              )}
              <ReferenceLine x={maturityYear} stroke="#1e293b" strokeWidth={2} label={{ position: 'top', value: 'Maturity', fill: '#1e293b', fontSize: 10, fontWeight: '700' }} />
              
              <Bar dataKey="investment" stackId="a" fill="#2563eb" name="Initial Investment" />
              <Bar dataKey="base" stackId="a" fill="transparent" legendType="none" />
              <Bar dataKey="growth" stackId="a" fill="#10b981" name="Capital Appreciation" />

              <Area 
                type="monotone" 
                dataKey="value" 
                stroke="#2563eb" 
                strokeWidth={4} 
                fillOpacity={1} 
                fill="url(#colorValue)" 
                animationDuration={1500}
                isAnimationActive={true}
              />
            </ComposedChart>
          </ResponsiveContainer>
          <div className="chart-legend-premium">
            <div className="legend-item"><span className="dot" style={{ background: '#2563eb' }}></span> Initial Investment</div>
            <div className="legend-item"><span className="dot" style={{ background: '#10b981' }}></span> Projected Growth</div>
            {!hideLockup && <div className="legend-item"><span className="dot lockup"></span> Lockup Phase</div>}
            <div className="legend-item"><span className="dot maturity"></span> Maturity</div>
          </div>
        </div>
      </section>

      {/* 6. STRATEGY & LIFECYCLE */}
      {report.fund_details?.strategy_and_fund_lifecycle && (
        <section className="strategy-section report-container">
          <div className="section-title-premium"><h2>Strategy & Lifecycle</h2></div>
          <div className="prose-container">
            <p className="prose-text">{report.fund_details.strategy_and_fund_lifecycle}</p>
          </div>
        </section>
      )}

      {/* 7. REASONS TO INVEST */}
      {report.fund_details?.reasons_to_invest?.length > 0 && (
        <section className="reasons-invest-section report-container">
          <div className="section-title-premium"><h2>Why Invest With Us?</h2></div>
          <div className="horizontal-scroll-container" ref={scrollRef}>
            {report.fund_details.reasons_to_invest.map((reason: any, idx: number) => (
              <div key={idx} className="reason-card-premium">
                <div className="reason-num">0{idx + 1}</div>
                <h3>{reason.title}</h3>
                <p>{reason.brief_desc}</p>
              </div>
            ))}
            {/* Duplicate for circular feel */}
            {report.fund_details.reasons_to_invest.map((reason: any, idx: number) => (
              <div key={`dup-${idx}`} className="reason-card-premium">
                <div className="reason-num">0{idx + 1}</div>
                <h3>{reason.title}</h3>
                <p>{reason.brief_desc}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <footer className="capital-call-footer">
        <div className="report-container">
          <div className="footer-grid">
            <div className="footer-main">
              <h3>FinanceRemade</h3>
              <p>Redefining institutional investment through transparency and technology.</p>
            </div>
          </div>
          <div className="footer-bottom">
            <p>© 2026 FinanceRemade. Institutional Investor Relations.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default PublicReportPage;
