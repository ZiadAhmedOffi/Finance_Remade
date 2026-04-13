import React, { useState, useEffect, useMemo } from "react";
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
  Line,
  Bar,
  PieChart,
  Pie,
  Cell,
  ReferenceLine,
  ReferenceArea,
  Area,
  AreaChart,
} from "recharts";
import "./PublicReport.css";

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

  const { 
    dashboard, 
    current_deals_metrics, 
    current_deals = [], 
    investment_deals = [],
    aggregated_exits = [],
    admin_fee 
  } = performanceData || {};

  const currentYear = dashboard?.current_year || new Date().getFullYear();

  // Formatting Utilities
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);

  const formatCurrencyLong = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);
  
  const formatPercent = (val: number) => (val * 100).toFixed(2) + "%";
  const formatMultiple = (val: number) => val.toFixed(2) + "x";

  // --- Dynamic Report Logic ---

  // 1. Waterfall Data
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

  // 2. Pie Chart Data
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

  // 3. Base Points Chart
  const basePointsChartData = useMemo(() => {
    if (!admin_fee || !dashboard?.performance_table) return [];
    
    const { inception_year, fund_life, total_admin_cost, operations_fee, management_fees } = admin_fee;
    const years_arr = Array.from({ length: fund_life }, (_, i) => inception_year + i);

    const gaPerYear = (total_admin_cost + operations_fee + (management_fees || 0)) / fund_life;
    const gaMap: Record<number, number> = {};
    years_arr.forEach(year => { gaMap[year] = gaPerYear; });

    const totalInvested = current_deals_metrics?.total_invested || 1;
    let pBase = 0, pUpside = 0, pHigh = 0;

    return dashboard.performance_table.map((row: any) => {
      const inj = row.injection_current || 0;
      const appr = row.appreciation_current || 0;
      const ga = gaMap[row.year] || 0;

      pBase += inj + appr;
      pUpside += inj + (appr * 1.2);
      pHigh += inj + (appr * 1.5);

      return {
        year: row.year,
        investedBP: (inj / totalInvested) * 100,
        "Base Case": ((pBase - ga) / totalInvested) * 100,
        "Upside Case": ((pUpside - ga) / totalInvested) * 100,
        "High Growth Case": ((pHigh - ga) / totalInvested) * 100
      };
    });
  }, [admin_fee, dashboard, current_deals_metrics]);

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
        // For Lockup overlay
        isLockup: yr < (inceptionYear + (report.fund_details?.model_inputs?.lock_up_period || 0))
      });
      currentValue = currentValue * (1 + irr);
    }
    
    return data;
  }, [report, selectedScenario, investmentAmount, aggregated_exits, currentYear]);

  const lockupEndYear = report?.fund_details?.model_inputs?.inception_year + (report?.fund_details?.model_inputs?.lock_up_period || 0);
  const maturityYear = report?.fund_details?.model_inputs?.inception_year + report?.fund_details?.model_inputs?.fund_life;

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
        {/* SVG Patterns */}
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
      <section className="cover-section">
        {report.config_json?.cover_image && (
          <div className="cover-image-container">
            <img src={report.config_json.cover_image} alt="Fund Cover" className="cover-image" />
          </div>
        )}
        <div className="cover-content report-container">
          <div className="badge-row">
            {report.fund_details?.sharia_compliant && <span className="premium-badge sharia">Sharia Compliant</span>}
            {report.fund_details?.region && <span className="premium-badge region">{report.fund_details.region}</span>}
            {report.fund_details?.focus && <span className="premium-badge focus">{report.fund_details.focus === 'GROWTH' ? 'Growth Focused' : 'Yield Focused'}</span>}
          </div>
          <h1 className="capital-call-title">{report.name}</h1>
          <p className="fund-subheadline">{report.fund_details?.description}</p>
        </div>
      </section>

      {/* 2. KEY FUND METRICS */}
      <section className="metrics-section report-container">
        <div className="glass-metrics-grid">
          <div className="glass-metric">
            <span className="g-label">Avg. MOIC</span>
            <span className="g-value">{formatMultiple(dashboard?.moic || 0)}</span>
          </div>
          <div className="glass-metric">
            <span className="g-label">Currency</span>
            <span className="g-value">USD</span>
          </div>
          <div className="glass-metric">
            <span className="g-label">Investment Period</span>
            <span className="g-value">{report.fund_details?.model_inputs?.investment_period} Years</span>
          </div>
          <div className="glass-metric">
            <span className="g-label">Lockup Period</span>
            <span className="g-value">{report.fund_details?.model_inputs?.lock_up_period} Years</span>
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

      {/* 4. CASH FLOW PROJECTION (CORE) */}
      <section className="projection-section report-container">
        <div className="section-title-premium"><h2>Cash Flow Projection</h2></div>
        
        <div className="projection-controls">
          <div className="control-group">
            <label>Investment Amount (USD)</label>
            <input 
              type="number" 
              value={investmentAmount} 
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                const min = parseFloat(report.fund_details?.model_inputs?.min_investor_ticket || 0);
                const max = parseFloat(report.fund_details?.model_inputs?.max_investor_ticket || 100000000);
                if (val >= min && val <= max) setInvestmentAmount(val);
                else if (val < min) setInvestmentAmount(min);
              }}
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
          <ResponsiveContainer width="100%" height={450}>
            <AreaChart data={cashFlowProjectionData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                </linearGradient>
                <pattern id="lockupPattern" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                  <rect width="2" height="4" transform="translate(0,0)" fill="rgba(245, 158, 11, 0.1)" />
                </pattern>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="year" axisLine={false} tickLine={false} tick={{ fill: '#64748b' }} />
              <YAxis tickFormatter={formatCurrency} axisLine={false} tickLine={false} tick={{ fill: '#64748b' }} />
              <Tooltip 
                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}
                formatter={(v: any) => [formatCurrencyLong(v), "Projected Value"]}
              />
              
              {/* Lockup Zone */}
              <ReferenceArea 
                x1={report.fund_details?.model_inputs?.inception_year} 
                x2={lockupEndYear} 
                fill="rgba(245, 158, 11, 0.05)" 
                strokeOpacity={0}
              />
              <ReferenceLine x={lockupEndYear} stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" label={{ position: 'top', value: 'End of Lockup', fill: '#f59e0b', fontSize: 10, fontWeight: '700' }} />
              
              {/* Secondary Zone (Year before maturity) */}
              <ReferenceLine x={maturityYear - 1} stroke="#2563eb" strokeWidth={1} strokeDasharray="3 3" label={{ position: 'top', value: 'Secondary Window', fill: '#2563eb', fontSize: 10, fontWeight: '700' }} />

              {/* Maturity Line */}
              <ReferenceLine x={maturityYear} stroke="#1e293b" strokeWidth={2} label={{ position: 'top', value: 'Maturity', fill: '#1e293b', fontSize: 10, fontWeight: '700' }} />
              
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke="#2563eb" 
                strokeWidth={4} 
                fillOpacity={1} 
                fill="url(#colorValue)" 
                animationDuration={1500}
              />
            </AreaChart>
          </ResponsiveContainer>
          <div className="chart-legend-premium">
            <div className="legend-item"><span className="dot lockup"></span> Lockup Phase</div>
            <div className="legend-item"><span className="dot secondary"></span> Secondary Window</div>
            <div className="legend-item"><span className="dot maturity"></span> Maturity</div>
          </div>
        </div>
      </section>

      {/* 5. STRATEGY & LIFECYCLE */}
      {report.fund_details?.strategy_and_fund_lifecycle && (
        <section className="strategy-section report-container">
          <div className="section-title-premium"><h2>Strategy & Lifecycle</h2></div>
          <div className="prose-container">
            <p className="prose-text">{report.fund_details.strategy_and_fund_lifecycle}</p>
          </div>
        </section>
      )}

      {/* 6. REASONS TO INVEST */}
      {report.fund_details?.reasons_to_invest?.length > 0 && (
        <section className="reasons-invest-section report-container">
          <div className="section-title-premium"><h2>Why Invest With Us?</h2></div>
          <div className="horizontal-scroll-container">
            {report.fund_details.reasons_to_invest.map((reason: any, idx: number) => (
              <div key={idx} className="reason-card-premium">
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
            <div className="footer-stats">
              <div className="f-stat">
                <span className="fs-val">{formatCurrency(report.config_json?.target_capital)}</span>
                <span className="fs-lab">Target Capital</span>
              </div>
              <div className="f-stat">
                <span className="fs-val">{formatCurrency(report.config_json?.capital_raised)}</span>
                <span className="fs-lab">Already Raised</span>
              </div>
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
