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
  Line,
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
    aggregated_exits = [],
    end_of_life_exits = [],
    admin_fee
  } = performanceData || {};

  const config = useMemo(() => {
    const rawConfig = report?.config_json?.report_config;
    if (!rawConfig) return { sections: [] };
    
    // If it's the old format (enabled_sections + custom_sections), migrate it for display
    if (rawConfig.enabled_sections || rawConfig.custom_sections) {
      const isDynamic = report.report_type === 'DYNAMIC';
      const defaults = isDynamic ? [
        { id: "perf_overview", title: "Performance Overview" },
        { id: "portfolio_comp", title: "Portfolio Composition" },
        { id: "value_appreciation", title: "Value Appreciation" },
        { id: "risk_assessment", title: "Risk Assessment" },
        { id: "deal_prognosis", title: "Deal Prognosis" }
      ] : [
        { id: "cc_overview", title: "Capital Call Overview" },
        { id: "investment_case", title: "Investment Case" },
        { id: "projected_growth_graph", title: "Projected Growth Graph" },
        { id: "why_invest", title: "Why Invest" },
        { id: "liquidity_analysis", title: "Liquidity Analysis" }
      ];

      return {
        sections: [
          ...defaults.map(d => ({ ...d, enabled: (rawConfig.enabled_sections || []).includes(d.id), type: 'DEFAULT' })),
          ...(rawConfig.custom_sections || []).map((s: any) => ({ ...s, enabled: true, type: 'CUSTOM' }))
        ]
      };
    }
    
    return rawConfig;
  }, [report]);

  const sections = config?.sections || [];

  const isEnabled = (id: string) => {
    if (!report?.config_json?.report_config) return true;
    
    // Support both old format (if any remain) and new 'sections' array
    const rawConfig = report.config_json.report_config;
    if (rawConfig.sections) {
      const section = rawConfig.sections.find((s: any) => s.id === id);
      return section ? section.enabled : false;
    }
    
    // Legacy support for enabled_sections
    if (rawConfig.enabled_sections) {
      return rawConfig.enabled_sections.includes(id);
    }
    
    return true;
  };

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

  const getMetricColor = (val: number) => val > 0 ? "#10b981" : "#94a3b8";

  const avgMoic = useMemo(() => {
    const achieved = current_deals_metrics?.moic || 0;
    const target = dashboard?.moic || 0;
    return (achieved + target) / 2;
  }, [current_deals_metrics, dashboard]);

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

  const targetAppreciation = parseFloat(report?.fund_details?.target_appreciation || 0);
  const targetYield = parseFloat(report?.fund_details?.target_yield || 0);

  const inceptionYear = report?.fund_details?.model_inputs?.inception_year || currentYear;
  const fundLife = report?.fund_details?.model_inputs?.fund_life || 10;

  const cashFlowProjectionData = useMemo(() => {
    if (!report || report.report_type !== 'CAPITAL_CALL') return [];
    
    const multipliers: Record<string, number> = {
        "Base Case": 1.0,
        "Upside Case": 1.3,
        "High Growth Case": 1.6
    };
    const rateFactor = multipliers[selectedScenario] || 1.0;
    let appreciationRate = (targetAppreciation / 100) * rateFactor;
    if(inceptionYear < currentYear){
      appreciationRate = cIrr;
    }
    
    const endYear = inceptionYear + fundLife;
    
    const data = [];
    let currentValue = investmentAmount;
    
    for (let yr = currentYear; yr <= endYear; yr++) {
      data.push({
        year: `Year ${yr - inceptionYear}`,
        value: currentValue,
        investment: yr === currentYear ? investmentAmount : 0,
        growth: yr > currentYear ? currentValue - investmentAmount : 0,
        base: yr > currentYear ? investmentAmount : 0,
      });
      currentValue = currentValue * (1 + appreciationRate);
    }
    
    return data;
  }, [report, targetAppreciation, investmentAmount, currentYear, selectedScenario, inceptionYear, fundLife]);

  const basePointsData = useMemo(() => {
    if (!admin_fee || !dashboard?.performance_table) {
      // Fallback for reports without full performance data or for future-only reports
      const fundLife = report?.fund_details?.model_inputs?.fund_life || 10;
      const appreciationRate = targetAppreciation / 100;
      const multipliers = { "Base Case": 1.0, "Upside Case": 1.2, "High Growth Case": 1.5 };
      let pBase = 100, pUpside = 100, pHighGrowth = 100;
      const inceptionYear = report?.fund_details?.model_inputs?.inception_year || currentYear;

      return Array.from({ length: fundLife + 1 }).map((_, i) => {
          const entry = {
              year: inceptionYear + i,
              "Base Case": pBase,
              "Upside Case": pUpside,
              "High Growth Case": pHighGrowth,
              investedBP: i === 0 ? 100 : 0
          };
          pBase *= (1 + appreciationRate * multipliers["Base Case"]);
          pUpside *= (1 + appreciationRate * multipliers["Upside Case"]);
          pHighGrowth *= (1 + appreciationRate * multipliers["High Growth Case"]);
          return entry;
      });
    }

    const { inception_year, fund_life, total_admin_cost, operations_fee, management_fees } = admin_fee;
    const years_arr = Array.from({ length: fund_life }, (_, i) => inception_year + i);

    // G&A calculations
    const estLicensingY1 = total_admin_cost * 0.05;
    const estLicensingLater = estLicensingY1 * 0.5;
    const row1Vals = years_arr.map((_, i) => i === 0 ? estLicensingY1 : estLicensingLater);
    const row1Total = row1Vals.reduce((a, b) => a + b, 0);

    const contractsY1 = operations_fee * 0.2;
    const contractsLater = operations_fee * 0.02;
    const row2Vals = years_arr.map((_, i) => i === 0 ? contractsY1 : contractsLater);
    const row2Total = row2Vals.reduce((a, b) => a + b, 0);

    const othersLegalVal = (total_admin_cost - (row1Total + row2Total)) / fund_life;
    const row3Vals = years_arr.map(() => othersLegalVal);

    const table1TotalsPerYear = years_arr.map((_, i) => row1Vals[i] + row2Vals[i] + row3Vals[i]);

    const onboardingVal = operations_fee * 0.05;
    const rowO1Vals = years_arr.map((_, i) => i < 2 ? onboardingVal : 0);
    const rowO1Total = rowO1Vals.reduce((a, b) => a + b, 0);

    const marketingVal = (operations_fee * 0.4) / fund_life;
    const rowO2Vals = years_arr.map(() => marketingVal);
    const rowO2Total = marketingVal * fund_life;

    const reportVal = operations_fee * 0.02;
    const rowO3Vals = years_arr.map(() => reportVal);
    const rowO3Total = rowO3Vals.reduce((a, b) => a + b, 0);

    const accountingVal = operations_fee * 0.04;
    const rowO4Vals = years_arr.map(() => accountingVal);
    const rowO4Total = accountingVal * fund_life;

    const othersOpsVal = (operations_fee - (rowO1Total + rowO2Total + rowO3Total + rowO4Total)) / fund_life;
    const rowO5Vals = years_arr.map(() => othersOpsVal);

    const table2TotalsPerYear = years_arr.map((_, i) => 
      rowO1Vals[i] + rowO2Vals[i] + rowO3Vals[i] + rowO4Vals[i] + rowO5Vals[i]
    );

    const managementVal = management_fees / fund_life;
    const rowM1Vals = years_arr.map(() => managementVal);

    const totalGAVals = years_arr.map((_, i) => table1TotalsPerYear[i] + table2TotalsPerYear[i] + rowM1Vals[i]);
    const gaMap: Record<number, number> = {};
    years_arr.forEach((year, i) => { gaMap[year] = totalGAVals[i]; });

    const totalInvested = (current_deals_metrics?.total_invested || 0) + (dashboard?.total_invested || 0);
    
    const irrBase = end_of_life_exits?.find((c: any) => c.case === "Base Case")?.irr || 0;
    const irrUpside = end_of_life_exits?.find((c: any) => c.case === "Upside Case")?.irr || 0;
    const irrHighGrowth = end_of_life_exits?.find((c: any) => c.case === "High Growth Case")?.irr || 0;

    let pBase = 0;
    let pUpside = 0;
    let pHighGrowth = 0;

    return dashboard.performance_table.map((row: any) => {
      const year = row.year;
      const injection = (row.injection_current || 0) + (row.injection_prognosis || 0);
      const gaYearly = gaMap[year] || 0;

      const useScenarioIRR = year >= currentYear;
      
      const effectiveIRRBase = irrBase;
      const effectiveIRRUpside = useScenarioIRR ? irrUpside : irrBase;
      const effectiveIRRHighGrowth = useScenarioIRR ? irrHighGrowth : irrBase;

      const currentApprBase = pBase * effectiveIRRBase;
      const currentApprUpside = pUpside * effectiveIRRUpside;
      const currentApprHighGrowth = pHighGrowth * effectiveIRRHighGrowth;

      pBase += injection + currentApprBase;
      pUpside += injection + currentApprUpside;
      pHighGrowth += injection + currentApprHighGrowth;

      const investedBP = totalInvested > 0 ? (injection / totalInvested) * 100 : 0;
      
      return {
        year: year,
        investedBP: investedBP,
        "Base Case": totalInvested > 0 ? ((pBase - gaYearly) / totalInvested) * 100 : 0,
        "Upside Case": totalInvested > 0 ? ((pUpside - gaYearly) / totalInvested) * 100 : 0,
        "High Growth Case": totalInvested > 0 ? ((pHighGrowth - gaYearly) / totalInvested) * 100 : 0,
      };
    });
  }, [report, targetAppreciation, dashboard, current_deals_metrics, admin_fee, end_of_life_exits, currentYear]);

  const lockupEndYear = report?.fund_details?.model_inputs?.inception_year + (report?.fund_details?.model_inputs?.lock_up_period || 0);
  const hideLockup = lockupEndYear <= currentYear;

  const liData = performanceData ? calculateLiquidityIndex(
    performanceData.current_deals || [],
    performanceData.admin_fee?.inception_year || new Date().getFullYear(),
    report?.fund_details?.model_inputs?.fund_life || 10
  ) : null;

  const fundName = report?.fund_details?.name || 'Our Fund';

  const comparisons = [
    { name: 'Public Equities (S&P 500)', li: 95 },
    { name: 'Gold', li: 98 },
    { name: 'Commodities (ETF)', li: 90 },
    { name: fundName, li: liData?.finalLI || 0, isCurrent: true },
    { name: 'Private Equity (Avg)', li: 25 },
    { name: 'Real Estate (Direct)', li: 15 },
  ];

  // --- Capital Call Report Render Helpers ---
  // --- Report Processing ---

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
            <div className="report-brand">Investment Intelligence Tool | Institutional Reporting</div>
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
          {sections.map((section: any) => {
            if (!section.enabled) return null;

            switch (section.id) {
              case 'perf_overview':
                return (
                  <section key={section.id} className="report-section">
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
                );

              case 'portfolio_comp':
                return (
                  <section key={section.id} className="report-section">
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
                );

              case 'value_appreciation':
                return (
                  <section key={section.id} className="report-section">
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
                );

              case 'risk_assessment':
                return (
                  <section key={section.id} className="report-section">
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
                );

              case 'deal_prognosis':
                return (
                  <section key={section.id} className="report-section">
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
                );

              default:
                if (section.type === 'CUSTOM') {
                  return (
                    <section key={section.id} className="report-section">
                      <div className="report-section-header"><h2>{section.title}</h2></div>
                      <p className="prose-text" style={{ textAlign: 'justify', whiteSpace: 'pre-wrap' }}>{section.text}</p>
                    </section>
                  );
                }
                return null;
            }
          })}
        </main>

        <footer className="report-footer">
          <div className="report-container">
            <div className="report-brand">Investment Intelligence Tool</div>
            <p>© 2026 Investment Intelligence Tool Asset Management. All rights reserved.</p>
          </div>
        </footer>
      </div>
    );
  }

  // --- Capital Call Report View ---
  
  return (
    <div className="public-report-layout capital-call-theme">
      <svg width="0" height="0" style={{ position: 'absolute' }}>
        <defs>
          <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3}/><stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
          </linearGradient>
        </defs>
      </svg>
      
      {/* 1. COVER SECTION (Always shown if enabled) */}
      {isEnabled('cc_overview') && (
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
      )}

      {/* Main Content Sections (In saved order) */}
      {sections.map((section: any) => {
        if (!section.enabled) return null;
        const total = (targetAppreciation + targetYield === 0) ? cIrr : (targetAppreciation + targetYield) / 100;
        const gain = (targetAppreciation + targetYield === 0) ? cIrr : (targetAppreciation) / 100;
        switch (section.id) {
          case 'cc_overview':
            return (
              <section key={section.id} className="metrics-section report-container">
                <div className="modern-metrics-container">
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
                      <div className="m-icon">💒</div>
                      <span className="m-label">Currency</span>
                      <span className="m-value">USD</span>
                    </div>
                  </div>

                  <div className="metrics-row secondary">
                    <div className="metric-card-modern">
                      <div className="m-icon">📈</div>
                      <span className="m-label">Annualized Return</span>
                      <span className="m-value">{formatPercent(total)}</span>
                      <div className="m-subvalue">
                        <span style={{ color: getMetricColor(targetYield) }}>Yield: {formatPercent(targetYield / 100)}</span>
                        <span style={{ color: getMetricColor(targetAppreciation) }}>Gain: {formatPercent(gain)}</span>
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
                {report.fund_details?.overview && (
                  <div className="overview-sub-section" style={{ marginTop: '3rem' }}>
                    <div className="section-title-premium"><h2>Opportunity Overview</h2></div>
                    <div className="prose-container">
                      <p className="prose-text-large">{report.fund_details.overview}</p>
                    </div>
                  </div>
                )}
              </section>
            );

          case 'fund_strategy':
            return report.fund_details?.strategy_and_fund_lifecycle ? (
              <section key={section.id} className="report-container" style={{ marginTop: '4rem' }}>
                <div className="section-title-premium"><h2>Fund Strategy & Lifecycle</h2></div>
                <div className="prose-container">
                  <p className="prose-text-large" style={{ whiteSpace: 'pre-wrap' }}>{report.fund_details.strategy_and_fund_lifecycle}</p>
                </div>
              </section>
            ) : null;

          case 'capital_allocation':
            const source = report.fund_details || {};
            const allocationData = (source.target_capital_allocation || []).map((a: any) => ({ 
              name: a.name || "N/A", 
              value: parseFloat(a.percentage || 0), 
              rationale: a.rationale || "No rationale provided" 
            }));
            const compositionData = (source.investment_composition || []).map((c: any) => ({ 
              name: c.label || "N/A", 
              value: parseFloat(c.value || 0) 
            }));

            return (
              <section key={section.id} className="report-container" style={{ marginTop: '4rem' }}>
                <div className="section-title-premium"><h2>Fund Allocation & Composition</h2></div>
                
                <div className="charts-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                  {/* Capital Allocation Pie */}
                  <div className="chart-wrapper">
                    <h3>Capital Allocation Model</h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie 
                          data={allocationData} 
                          cx="50%" cy="50%" outerRadius={80} dataKey="value"
                          label={({ name, percent }) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}
                        >
                          {allocationData.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                        </Pie>
                        <Tooltip formatter={(v: any, _name: any, entry: any) => [v + '%', entry.payload.rationale]} />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Investment Composition Pie */}
                  <div className="chart-wrapper">
                    <h3>Investment Composition</h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie 
                          data={compositionData} 
                          cx="50%" cy="50%" outerRadius={80} dataKey="value"
                          label={({ name, percent }) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}
                        >
                          {compositionData.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                        </Pie>
                        <Tooltip />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                    {source.risk_measures && source.risk_measures.length > 0 && (
                      <div className="risk-measures-box" style={{ marginTop: '1.5rem', borderTop: '1px solid #e2e8f0', paddingTop: '1rem' }}>
                        <strong style={{ color: '#181a1e', fontSize: '1.2rem', display: 'block', marginBottom: '0.2rem'}}>Risk Measures</strong>
                        <ul style={{ listStyleType: 'none', padding: 0, margin: 0, textAlign: 'left' }}>
                          {source.risk_measures.map((risk: any, idx: number) => (
                            <li key={idx} style={{ marginBottom: '0.75rem', fontSize: '0.9rem' }}>
                              <strong style={{ color: '#334155', display: 'block', marginBottom: '0.2rem' }}>{risk.title}</strong>
                              <span style={{ color: '#64748b', lineHeight: '1.4' }}>{risk.description}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>

                <div className="composition-explanatory-text" style={{ marginTop: '2rem', textAlign: 'center' }}>
                  <p className="prose-text-large" style={{ fontSize: '1.1rem', maxWidth: '800px', margin: '0 auto' }}>
                    Our fund maintains a strategic balance across various investment types, optimizing for both capital appreciation 
                    and consistent yield. This diversified approach mitigates sector-specific risks while capturing high-growth opportunities.
                  </p>
                </div>

                <div className="future-deals-table-wrapper" style={{ marginTop: '3rem' }}>
                  <h3 style={{ marginBottom: '1.5rem', textAlign: 'center' }}>Future Deals (Deal Prognosis)</h3>
                  <table className="modern-table">
                    <thead>
                      <tr>
                        <th>Company Name</th>
                        <th>Stages</th>
                        <th>Entry</th>
                        <th>Expected Exit Year</th>
                        <th>Entry Valuation</th>
                        <th>Expected Exit Valuation</th>
                        <th>Investment Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {investment_deals.map((deal: any) => {
                        const factor = selectedScenario === "High Growth Case" ? (parseFloat(deal.upside_factor) * 1.2) : 
                                      selectedScenario === "Upside Case" ? parseFloat(deal.upside_factor) : 
                                      parseFloat(deal.base_factor);
                        const exitValuation = parseFloat(deal.entry_valuation) * factor;
                        const investmentTypeLabel = {
                          'EQUITY': 'Equity Financing',
                          'VENTURE_DEBT': 'Venture Debt',
                          'VENTURE_DEBT_ROYALTIES': 'Venture Debt with Royalties (Shariah Compliant)'
                        }[deal.investment_type as string] || deal.investment_type || 'Equity Financing';

                        return (
                          <tr key={deal.id}>
                            <td>{deal.company_name}</td>
                            <td>{deal.company_type || 'N/A'}</td>
                            <td>{deal.entry_year}</td>
                            <td>{deal.exit_year}</td>
                            <td>{formatCurrency(deal.entry_valuation)}</td>
                            <td>{formatCurrency(exitValuation)}</td>
                            <td>{investmentTypeLabel}</td>
                          </tr>
                        );
                      })}
                      {investment_deals.length === 0 && (
                        <tr>
                          <td colSpan={7} style={{ textAlign: 'center', opacity: 0.6 }}>No future deals projected yet.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            );

          case 'investment_composition':
            // Skip this because we merged it with capital_allocation above as per PLAN.md
            return null;

          case 'investment_case':
            return (
              <section key={section.id} className="projection-section report-container" style={{ marginTop: '4rem' }}>
                <div className="section-title-premium"><h2>Investment Case & Yield</h2></div>
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
                      {["Base Case", "Upside Case", "High Growth Case"].map((c: any) => (
                        <button key={c} className={`pill ${selectedScenario === c ? 'active' : ''}`} onClick={() => setSelectedScenario(c)}>{c}</button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="chart-container-premium">
                  <ResponsiveContainer width="100%" height={450}>
                    <ComposedChart data={cashFlowProjectionData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis dataKey="year" axisLine={false} tickLine={false} tick={{ fill: '#64748b' }} />
                      <YAxis tickFormatter={formatCurrency} axisLine={false} tickLine={false} tick={{ fill: '#64748b' }} />
                      <Tooltip formatter={(v: any) => formatCurrencyLong(Number(v))} />
                      <Legend />
                      <defs>
                        <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#2563eb" stopOpacity={0.1}/>
                          <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      {lockupEndYear > currentYear && (
                        <ReferenceArea 
                          x1={`Year ${currentYear - inceptionYear}`} 
                          x2={`Year ${Math.min(lockupEndYear - inceptionYear, fundLife)}`} 
                          fill="#facc15" 
                          fillOpacity={0.15} 
                          label={{ position: 'top', value: 'Lock-up Period', fill: '#854d0e', fontSize: 12, fontWeight: 600 }}
                        />
                      )}
                      <Bar dataKey="investment" stackId="a" fill="#2563eb" name="Initial Investment" />
                      <Bar dataKey="base" stackId="a" fill="transparent" legendType="none" />
                      <Bar dataKey="growth" stackId="a" fill="#10b981" name="Capital Appreciation" />
                      <Area type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={4} fillOpacity={1} fill="url(#colorValue)" />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                {targetYield > 0 &&
                <div className="table-wrapper" style={{ marginTop: '2rem' }}>
                   <table className="modern-table">
                      <thead>
                        <tr>
                          <th>Year</th>
                          <th>Projected Value</th>
                          <th>Annual Yield</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(() => {
                          const rows = [];
                          let val = investmentAmount;
                          const appreciationRate = targetAppreciation / 100;
                          const yieldRate = targetYield / 100;
                          const investmentPeriod = report.fund_details?.model_inputs?.investment_period || 5;

                          for (let i = 0; i <= investmentPeriod; i++) {
                            rows.push(
                              <tr key={i}>
                                <td>Year {i}</td>
                                <td>{formatCurrency(val)}</td>
                                <td>{formatCurrency(val * yieldRate)}</td>
                              </tr>
                            );
                            val *= (1 + appreciationRate);
                          }
                          return rows;
                        })()}
                      </tbody>
                   </table>
                </div>
                }
              </section>
            );

          case 'projected_growth_graph':
            return (
              <section key={section.id} className="report-container" style={{ marginTop: '4rem' }}>
                <div className="section-title-premium"><h2>Projected Growth Graph</h2></div>
                <p className="prose-text-large" style={{ textAlign: 'center', marginBottom: '2rem' }}>
                  This graph visualizes the projected portfolio valuation growth based on current injections and target appreciation rates. 
                  The multi-dimensional view integrates total portfolio value, MOIC, and IRR performance over the fund lifecycle.
                </p>
                <FundPerformanceRadarChart 
                  data={dashboard?.performance_table || []} 
                  irr={fundIrr} 
                />
              </section>
            );

          case 'basepoints_graph':
            return (
              <section key={section.id} className="report-container" style={{ marginTop: '4rem' }}>
                <div className="section-title-premium"><h2>Basepoints Analysis</h2></div>
                <div className="prose-container" style={{ marginBottom: '2rem' }}>
                  <p className="prose-text-large" style={{ fontSize: '1rem', textAlign: 'center' }}>
                    The following chart illustrates the growth of 100 Base Points (BP) of capital invested at inception. 
                    The performance tracks the net value expansion, taking into account the annual target appreciation defined for this fund lifecycle.
                  </p>
                </div>
                <div className="chart-wrapper">
                   <ResponsiveContainer width="100%" height={400}>
                    <ComposedChart data={basePointsData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="year" />
                      <YAxis label={{ value: 'Base Points', angle: -90, position: 'insideLeft' }} />
                      <Tooltip formatter={(value: any) => Number(value).toFixed(2)} />
                      <Legend />
                      <ReferenceLine x={currentYear - 1} stroke="#e74c3c" strokeDasharray="3 3" label={{ position: 'top', value: 'Current Year - 1', fill: '#e74c3c', fontSize: 12 }} />
                      <Bar dataKey="investedBP" fill="#e67e22" name="Invested Capital (BP)" barSize={40} />
                      <Line type="monotone" dataKey="Base Case" stroke="#6ee7b7" strokeWidth={3} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="Upside Case" stroke="#10b981" strokeWidth={3} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="High Growth Case" stroke="#065f46" strokeWidth={3} dot={{ r: 3 }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </section>
            );

          case 'why_invest':
            return report.fund_details?.reasons_to_invest?.length > 0 ? (
              <section key={section.id} className="reasons-invest-section report-container">
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
            ) : null;

          case 'liquidity_analysis':
            return (
                  <section className="stability-liquidity-section report-container" style={{ marginTop: '4rem' }}>
                    <div className="section-title-premium"><h2>Portfolio Stability & Market Liquidity</h2></div>
                    
                    <div className="stability-liquidity-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '2rem' }}>
                      {/* Intrinsic Value Radar */}
                      <div className="content-card" style={{ padding: '2.5rem' }}>
                        <h3 style={{ textAlign: 'center', marginBottom: '2rem', border: 'none' }}>Intrinsic Value</h3>
                        <div style={{ width: '100%', height: 450 }}>
                          <ResponsiveContainer>
                            <RadarChart cx="50%" cy="50%" outerRadius="80%" data={(() => {
                              const farthestDealsMap = new Map();
                              
                              current_deals.forEach((d: any) => {
                                const dist = Math.abs(d.entry_year - currentYear);
                                const existingDeal = farthestDealsMap.get(d.company_name);
                                if (!existingDeal || dist > Math.abs(existingDeal.entry_year - currentYear)) {
                                  farthestDealsMap.set(d.company_name, d);
                                }
                              });
                              
                              const result: any[] = [];
                              farthestDealsMap.forEach((d) => {
                                const entryVal = parseFloat(d.entry_valuation);
                                const currentVal = parseFloat(d.latest_valuation);
                                const exitMultiple = parseFloat(d.expected_exit_multiple || 5.0);
                                const ownership = parseFloat(d.ownership_after_dilution || 0);
                                const targetVal = entryVal * exitMultiple;
                                
                                result.push({
                                  subject: d.company_name,
                                  entry: targetVal > 0 ? (entryVal / targetVal) * 100 : 0,
                                  current: targetVal > 0 ? (currentVal / targetVal) * 100 : 0,
                                  expected: 100,
                                  upside: 120,
                                  highGrowth: 150,
                                  full_name: d.company_name,
                                  raw_entry: entryVal,
                                  raw_current: currentVal,
                                  raw_expected: targetVal,
                                  ownership: ownership
                                });
                              });
                              
                              return result;
                            })()}>
                              <PolarGrid />
                              <PolarAngleAxis 
                                dataKey="subject" 
                                tick={(() => {
                                  const uniqueCompanies = new Set(current_deals.map((d: any) => d.company_name));
                                  return uniqueCompanies.size > 15 ? false : { fill: '#64748b', fontSize: '0.8rem' };
                                })()}
                              />
                              <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
                              <Radar name="Entry Valuation" dataKey="entry" stroke="#3498db" fill="#3498db" fillOpacity={0.4} />
                              <Radar name="Current Valuation" dataKey="current" stroke="#2ecc71" fill="#2ecc71" fillOpacity={0.5} />
                              <Radar name="Base Case" dataKey="expected" stroke="#6ee7b7" fill="transparent" strokeDasharray="5 5" />
                              <Radar name="Upside Case" dataKey="upside" stroke="#10b981" fill="transparent" strokeDasharray="5 5" />
                              <Radar name="High Growth Case" dataKey="highGrowth" stroke="#065f46" fill="transparent" strokeDasharray="5 5" />
                              <Tooltip content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                  const d = payload[0].payload;
                                  let achievedScenario = "In Progress";
                                  if (d.current >= 150) achievedScenario = "High Growth Scenario";
                                  else if (d.current >= 120) achievedScenario = "Upward Scenario";
                                  else if (d.current >= 100) achievedScenario = "Base Scenario";

                                  return (
                                    <div className="custom-tooltip" style={{ 
                                      backgroundColor: '#fff', padding: '12px', border: '1px solid #e2e8f0',
                                      borderRadius: '8px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                                      fontSize: '0.85rem', lineHeight: '1.5'
                                    }}>
                                      <p style={{ fontWeight: 'bold', marginBottom: '8px', color: '#1e293b', borderBottom: '1px solid #f1f5f9', paddingBottom: '4px' }}>{d.full_name}</p>
                                      <p style={{ margin: '2px 0' }}><span style={{ color: '#64748b' }}>Ownership:</span> <strong>{d.ownership.toFixed(2)}%</strong></p>
                                      <p style={{ margin: '2px 0' }}><span style={{ color: '#3498db' }}>Entry Val:</span> <strong>{formatCurrencyLong(d.raw_entry)}</strong> ({d.entry.toFixed(1)}%)</p>
                                      <p style={{ margin: '2px 0' }}><span style={{ color: '#2ecc71' }}>Current Val:</span> <strong>{formatCurrencyLong(d.raw_current)}</strong> ({d.current.toFixed(1)}%)</p>
                                      <p style={{ margin: '2px 0' }}><span style={{ color: '#129448' }}>Expected Exit Val:</span> <strong>{formatCurrencyLong(d.raw_expected)}</strong> ({100}%)</p>
                                      <p style={{ margin: '8px 0 0', fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic' }}>Achieved Scenario: {achievedScenario}</p>
                                    </div>
                                  );
                                }
                                return null;
                              }} />
                              <Legend />
                            </RadarChart>
                          </ResponsiveContainer>
                        </div>
                        <p style={{ marginTop: '1.5rem', fontSize: '0.9rem', color: '#64748b', lineHeight: '1.6', textAlign: 'center' }}>
                          The Intrinsic Value graph visualizes each portfolio company's journey from entry valuation towards its target exit valuation. 
                        </p>
                      </div>

                      {/* Liquidity Index */}
                      <div className="content-card" style={{ padding: '2.5rem' }}>
                        <h3 style={{ textAlign: 'center', marginBottom: '2rem', border: 'none' }}>Liquidity Index</h3>
                        <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          {liData && (
                            <LiquidityGauge 
                              value={liData.finalLI} 
                              portfolioL={liData.portfolioL} 
                              ageFactor={liData.ageFactor} 
                              age={liData.age} 
                              fundName={fundName}
                            />
                          )}
                        </div>

                        <div style={{ marginTop: '0.75rem' }}>
                          <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#1e293b', marginTop: '2rem', border: 'none', fontWeight: 700 }}>Liquidity Benchmarks</h4>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                            {comparisons.sort((a, b) => b.li - a.li).map((comp) => {
                              const barColor = comp.li >= 60 ? '#10b981' : comp.li >= 40 ? '#fbbf24' : '#ef4444';
                              return (
                                <div key={comp.name} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                  <span style={{ fontSize: '0.7rem', color: '#64748b', width: '140px' }}>{comp.name} {comp.isCurrent && "(Current)"}</span>
                                  <div style={{ flex: 1, height: '6px', backgroundColor: '#e2e8f0', borderRadius: '3px', overflow: 'hidden', border: comp.isCurrent ? '1px solid #1e293b' : 'none' }}>
                                    <div style={{ 
                                      width: `${comp.li}%`, height: '100%', 
                                      background: barColor,
                                      opacity: comp.isCurrent ? 1 : 0.7
                                    }} />
                                  </div>
                                  <span style={{ fontSize: '0.7rem', fontWeight: '700', color: '#1e293b', width: '35px' }}>{comp.li.toFixed(0)}%</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                        <p style={{ marginTop: '1.5rem', fontSize: '0.9rem', color: '#64748b', lineHeight: '1.6', textAlign: 'center' }}>
                          The Liquidity Index assesses the portfolio's realization potential and risk maturity.
                        </p>
                      </div>
                    </div>
                  </section>
            );

          case 'call_timeline':
            return (
              <section key={section.id} className="report-container" style={{ marginTop: '4rem' }}>
                <div className="section-title-premium"><h2>Call Timeline</h2></div>
                <div style={{ position: 'relative', padding: '2rem 0' }}>
                   {/* Vertical line */}
                   <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '2px', background: '#e2e8f0', transform: 'translateX(-50%)' }} />
                   
                   {[
                     { step: 'Commitment Period', date: 'T-30 Days', desc: 'Investors confirm their commitment amounts.' },
                     { step: 'Capital Call Notice', date: 'T-15 Days', desc: 'Formal notice issued to all partners.' },
                     { step: 'Funding Deadline', date: 'T-Day', desc: 'Capital must be received in the fund account.' },
                     { step: 'Investment Execution', date: 'T+5 Days', desc: 'Fund deploys capital into target assets.' }
                   ].map((item, i) => (
                     <div key={i} style={{ display: 'flex', justifyContent: i % 2 === 0 ? 'flex-end' : 'flex-start', alignItems: 'center', marginBottom: '2rem', width: '100%' }}>
                        <div style={{ 
                          width: '45%', 
                          padding: '1.5rem', 
                          background: 'white', 
                          borderRadius: '12px', 
                          boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                          textAlign: i % 2 === 0 ? 'right' : 'left'
                        }}>
                          <h4 style={{ margin: 0, color: '#2563eb' }}>{item.step}</h4>
                          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#64748b', margin: '0.25rem 0' }}>{item.date}</div>
                          <p style={{ margin: 0, fontSize: '0.9rem' }}>{item.desc}</p>
                        </div>
                     </div>
                   ))}
                </div>
              </section>
            );

          case 'contact_info':
            return (
              <section key={section.id} className="report-container" style={{ marginTop: '4rem', textAlign: 'center' }}>
                <div className="section-title-premium"><h2>Contact Information</h2></div>
                <div className="content-card" style={{ display: 'inline-block', padding: '3rem', maxWidth: '600px' }}>
                  <p className="prose-text-large" style={{ marginBottom: '2rem' }}>
                    For any inquiries regarding this capital call or the fund's current strategy, please reach out to our investor relations team.
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
                    <div style={{ fontWeight: 700, fontSize: '1.2rem' }}>Investor Relations Team</div>
                    <div style={{ color: '#2563eb' }}>ir@investmentintelligence.com</div>
                    <div style={{ color: '#64748b' }}>+1 (555) 123-4567</div>
                  </div>
                </div>
              </section>
            );

          default:
            // Custom sections are handled separately
            if (section.type === 'CUSTOM') {
              return (
                <section key={section.id} className="report-container" style={{ marginTop: '4rem' }}>
                  <div className="section-title-premium"><h2>{section.title}</h2></div>
                  <div className="prose-container">
                    <p className="prose-text-large" style={{ textAlign: 'justify', whiteSpace: 'pre-wrap' }}>{section.text}</p>
                  </div>
                </section>
              );
            }
            return null;
        }
      })}

      <footer className="capital-call-footer" style={{ marginTop: '6rem' }}>
        <div className="report-container">
          <div className="footer-grid">
            <div className="footer-main">
              <h3>Investment Intelligence Tool</h3>
              <p>Redefining institutional investment through transparency and technology.</p>
            </div>
          </div>
          <div className="footer-bottom">
            <p>© 2026 Investment Intelligence Tool. Institutional Investor Relations.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default PublicReportPage;
