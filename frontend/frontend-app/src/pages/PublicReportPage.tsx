import React, { useState, useEffect } from "react";
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
} from "recharts";
import "./PublicReport.css";

const COLORS = ["#2563eb", "#7c3aed", "#db2777", "#ea580c", "#16a34a", "#0891b2"];

const PublicReportPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [report, setReport] = useState<any>(null);
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReportData = async () => {
      if (!slug) return;
      try {
        setLoading(true);
        const response = await fundsApi.getPublicReport(slug);
        setReport(response.data);
        setPerformanceData(response.data.performance_data);
      } catch (err: any) {
        setError(err.response?.data?.error || "Report not found or inactive.");
      } finally {
        setLoading(false);
      }
    };

    fetchReportData();
  }, [slug]);

  if (loading) return (
    <div className="report-loading-container">
      <div className="spinner"></div>
      <p>Preparing interactive report...</p>
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

  // 1. Waterfall Data
  const waterfallData = dashboard?.performance_table.map((entry: any, index: number) => {
    const prevEntry = index > 0 ? dashboard.performance_table[index - 1] : null;
    const startValue = prevEntry ? prevEntry.total_portfolio_value_with_prognosis : 0;
    return {
      ...entry,
      startValue: startValue
    };
  });

  // 2. Pie Chart Data (by Sector/Company Type)
  const allDeals = [...current_deals, ...investment_deals];
  const sectorCounts: any = {};
  const sectorCapital: any = {};

  allDeals.forEach(deal => {
    const sector = deal.company_type || "Other";
    sectorCounts[sector] = (sectorCounts[sector] || 0) + 1;
    sectorCapital[sector] = (sectorCapital[sector] || 0) + parseFloat(deal.amount_invested || 0);
  });

  const chartDataSectorCount = Object.keys(sectorCounts).map(name => ({ name, value: sectorCounts[name] }));
  const chartDataSectorCapital = Object.keys(sectorCapital).map(name => ({ name, value: sectorCapital[name] }));

  // 3. Base Points Chart Calculation
  const calculateBasePointsData = () => {
    if (!admin_fee || !dashboard?.performance_table) return [];
    
    const { inception_year, fund_life, total_admin_cost, operations_fee, management_fees } = admin_fee;
    const years_arr = Array.from({ length: fund_life }, (_, i) => inception_year + i);

    // Simplified G&A allocation for report
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
  };

  const basePointsChartData = calculateBasePointsData();

  return (
    <div className="public-report-layout">
      {/* SVG Patterns for Hashing */}
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
          <pattern id="hash-deals" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="10" height="10" fill="#9b59b6" />
            <line x1="0" y1="0" x2="0" y2="10" stroke="white" strokeWidth="4" />
          </pattern>
          <pattern id="hash-amount" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="10" height="10" fill="#e67e22" />
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
        
        {/* EXECUTIVE SUMMARY */}
        <section className="report-section">
          <div className="report-section-header">
            <h2>Executive Summary</h2>
          </div>
          <p className="prose-text">
            This report provides a comprehensive overview of the fund's current standing, realized returns, and future growth projections. 
            As of {new Date().getFullYear()}, the portfolio shows strong resilience with a current MOIC of <strong>{formatMultiple(current_deals_metrics?.moic)}</strong> 
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

        {/* DIVERSIFICATION ANALYSIS */}
        <section className="report-section">
          <div className="report-section-header">
            <h2>Portfolio Diversification</h2>
          </div>
          <p className="prose-text">
            Our investment strategy focuses on a balanced allocation across high-growth sectors. The charts below illustrate the distribution 
            of our portfolio both by the number of unique deals and by the total capital commitment.
          </p>
          
          <div className="charts-row">
            <div className="chart-wrapper">
              <div className="chart-description">
                <h3>Allocation by Deal Count</h3>
                <p>Visualization of how our partnerships are distributed across different company stages and types.</p>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={chartDataSectorCount}
                    cx="50%" cy="50%"
                    outerRadius={80}
                    dataKey="value"
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  >
                    {chartDataSectorCount.map((_, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-wrapper">
              <div className="chart-description">
                <h3>Allocation by Capital Deployed</h3>
                <p>Deep dive into where the fund's capital is most heavily concentrated by sector value.</p>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={chartDataSectorCapital}
                    cx="50%" cy="50%"
                    outerRadius={80}
                    dataKey="value"
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  >
                    {chartDataSectorCapital.map((_, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v: any) => formatCurrency(Number(v))} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

        {/* GROWTH DYNAMICS */}
        <section className="report-section">
          <div className="report-section-header">
            <h2>Growth Dynamics & Scenarios</h2>
          </div>
          <p className="prose-text">
            Understanding the trajectory of value creation is key to our reporting. We analyze both historical expansion 
            and various future scenarios based on market volatility and exit multiples.
          </p>

          <div className="chart-wrapper">
            <div className="chart-description">
              <h3>Annual Portfolio Value Expansion</h3>
              <p>Waterfall analysis showing the bridge between capital calls and organic portfolio appreciation.</p>
            </div>
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

          <div className="chart-wrapper">
            <div className="chart-description">
              <h3>Relative Performance (Base Points)</h3>
              <p>This institutional-grade visualization treats total invested capital as 100 base points (BP). It tracks the portfolio's net value (after management fees) across Base, Upside, and High Growth scenarios.</p>
            </div>
            <ResponsiveContainer width="100%" height={400}>
              <ComposedChart data={basePointsChartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="year" />
                <YAxis label={{ value: 'Base Points (100 = Capital)', angle: -90, position: 'insideLeft' }} />
                <Tooltip formatter={(value: any) => `${Number(value).toFixed(1)} BP`} />
                <Legend />
                <ReferenceLine y={100} stroke="#64748b" strokeDasharray="5 5" label="Capital Parity" />
                <Bar dataKey="investedBP" fill="#f59e0b" name="Invested Capital (BP)" barSize={40} />
                <Line type="monotone" dataKey="Base Case" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} />
                <Line type="monotone" dataKey="Upside Case" stroke="#3b82f6" strokeWidth={3} dot={{ r: 4 }} />
                <Line type="monotone" dataKey="High Growth Case" stroke="#8b5cf6" strokeWidth={3} dot={{ r: 4 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* SCENARIO COMPARISON TABLE */}
        <section className="report-section">
          <div className="report-section-header">
            <h2>Scenario Sensitivity Analysis</h2>
          </div>
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
          <p style={{ marginTop: '0.5rem', fontSize: '0.75rem', opacity: 0.7 }}>
            DISCLAIMER: This document contains confidential information. Past performance is not indicative of future results. 
            Projections are based on current market data and assumptions that are subject to change.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default PublicReportPage;
