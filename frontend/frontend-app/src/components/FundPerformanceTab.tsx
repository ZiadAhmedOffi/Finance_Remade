import React, { useState, useEffect } from "react";
import { api } from "../api/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Line,
} from "recharts";

/**
 * Interface representing a single year's entry in the performance table.
 */
interface PerformanceTableEntry {
  year: number;
  start_value: number;
  injection: number;
  appreciation: number;
  total_portfolio_value: number;
  deals_count: number;
  cumulative_deals_count: number;
  cumulative_injection: number;
}

/**
 * Interface for the complete performance data payload from the API.
 */
interface PerformanceData {
  dashboard: {
    total_invested: number;
    gross_exit_value: number;
    moic: number;
    irr: number;
    total_deals: number;
    performance_table: PerformanceTableEntry[];
  };
  aggregated_exits: {
    case: string;
    irr: number;
    [key: string]: any;
  }[];
  admin_fee: {
    total_admin_cost: number;
    operations_fee: number;
    management_fees: number;
    total_costs: number;
    inception_year: number;
    fund_life: number;
  };
}

interface FundPerformanceTabProps {
  fundId: string;
}

/**
 * FundPerformanceTab Component
 * 
 * Provides a high-level overview of fund performance, including:
 * 1. Primary financial metrics (Total Invested, GEV, MOIC, IRR).
 * 2. Detailed annual performance table.
 * 3. Advanced data visualizations (Base Points, Waterfall, Investment Velocity).
 * 
 * @param {string} fundId - The unique identifier of the fund.
 */
const FundPerformanceTab: React.FC<FundPerformanceTabProps> = ({ fundId }) => {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetches performance data from the backend.
   */
  useEffect(() => {
    const fetchPerformance = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/funds/${fundId}/performance/`);
        setData(response.data);
      } catch (err) {
        setError("Failed to fetch performance data.");
      } finally {
        setLoading(false);
      }
    };
    fetchPerformance();
  }, [fundId]);

  if (loading) return <div>Loading Dashboard Data...</div>;
  if (error) return <div className="alert alert-error">{error}</div>;
  if (!data) return null;

  const { dashboard, aggregated_exits, admin_fee } = data;

  /**
   * Calculates data for the "Base Points" chart.
   * Treats total invested capital as 100 base points.
   * Lines represent portfolio value net of annual G&A fees.
   * 
   * @returns {Array} Array of objects formatted for Recharts.
   */
  const calculateBasePointsData = () => {
    if (!admin_fee || !dashboard.performance_table) return [];

    const { inception_year, fund_life, total_admin_cost, operations_fee, management_fees } = admin_fee;
    const years_arr = Array.from({ length: fund_life }, (_, i) => inception_year + i);

    // Reconstruct G&A allocation logic (consistent with AdminFeeTab)
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

    const totalInvested = dashboard.total_invested;
    const irrBase = aggregated_exits.find(c => c.case === "Base Case")?.irr || 0;
    const irrUpside = aggregated_exits.find(c => c.case === "Upside Case")?.irr || 0;
    const irrHighGrowth = aggregated_exits.find(c => c.case === "High Growth Case")?.irr || 0;

    let portfolioBase = 0;
    let portfolioUpside = 0;
    let portfolioHighGrowth = 0;

    return dashboard.performance_table.map((row) => {
      const injection = row.injection;
      const gaYearly = gaMap[row.year] || 0;

      portfolioBase = portfolioBase * (1 + irrBase) + injection;
      portfolioUpside = portfolioUpside * (1 + irrUpside) + injection;
      portfolioHighGrowth = portfolioHighGrowth * (1 + irrHighGrowth) + injection;

      const investedBP = totalInvested > 0 ? (injection / totalInvested) * 100 : 0;
      const lineBase = totalInvested > 0 ? ((portfolioBase - gaYearly) / totalInvested) * 100 : 0;
      const lineUpside = totalInvested > 0 ? ((portfolioUpside - gaYearly) / totalInvested) * 100 : 0;
      const lineHighGrowth = totalInvested > 0 ? ((portfolioHighGrowth - gaYearly) / totalInvested) * 100 : 0;

      return {
        year: row.year,
        investedBP: investedBP,
        "Base Case": lineBase,
        "Upside Case": lineUpside,
        "High Growth Case": lineHighGrowth
      };
    });
  };

  const basePointsChartData = calculateBasePointsData();

  // Formatting Utilities
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);

  const formatCurrencyLong = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);
  
  const formatPercent = (val: number) => (val * 100).toFixed(2) + "%";
  const formatMultiple = (val: number) => val.toFixed(2) + "x";

  const waterfallData = dashboard.performance_table.map((entry) => ({
    ...entry,
    end_value: entry.total_portfolio_value
  }));
  
  return (
    <section className="performance-tab">
      {/* Top Metrics Card */}
      <div className="content-card" style={{background: '#f0f7ff', borderColor: '#007bff', marginBottom: '3rem'}}>
        <div style={{display: 'flex', flexDirection: 'column', gap: '2.5rem', textAlign: 'center'}}>
          {/* Row 1: Primary Metrics */}
          <div style={{display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: '2rem'}}>
            <div className="summary-item">
              <label style={{color: '#0056b3', fontSize: '1.1rem', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.5rem', display: 'block'}}>Total Invested</label>
              <div className="summary-value" style={{fontSize: '3rem', fontWeight: '900', color: '#007bff'}}>
                {formatCurrencyLong(dashboard.total_invested)}
              </div>
            </div>
            <div className="summary-item">
              <label style={{color: '#0056b3', fontSize: '1.1rem', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.5rem', display: 'block'}}>Gross Exit Value</label>
              <div className="summary-value" style={{fontSize: '3rem', fontWeight: '900', color: '#007bff'}}>
                {formatCurrencyLong(dashboard.gross_exit_value)}
              </div>
            </div>
          </div>

          <div className="divider-h" style={{margin: '0 auto', width: '80%', opacity: '0.3'}} />

          {/* Row 2: Secondary Metrics */}
          <div style={{display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: '2rem'}}>
            <div className="summary-item">
              <label style={{color: '#0056b3', fontSize: '0.9rem', fontWeight: '600', textTransform: 'uppercase', marginBottom: '0.3rem', display: 'block'}}>MOIC Multiple</label>
              <div className="summary-value" style={{fontSize: '1.8rem', fontWeight: '700', color: '#007bff'}}>
                {formatMultiple(dashboard.moic)}
              </div>
            </div>
            <div className="summary-item">
              <label style={{color: '#0056b3', fontSize: '0.9rem', fontWeight: '600', textTransform: 'uppercase', marginBottom: '0.3rem', display: 'block'}}>IRR</label>
              <div className="summary-value" style={{fontSize: '1.8rem', fontWeight: '700', color: '#007bff'}}>
                {formatPercent(dashboard.irr)}
              </div>
            </div>
            <div className="summary-item">
              <label style={{color: '#0056b3', fontSize: '0.9rem', fontWeight: '600', textTransform: 'uppercase', marginBottom: '0.3rem', display: 'block'}}>Total Deals</label>
              <div className="summary-value" style={{fontSize: '1.8rem', fontWeight: '700', color: '#007bff'}}>
                {dashboard.total_deals}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Annual Performance Table */}
      <div className="content-card" style={{marginBottom: '4rem'}}>
        <h3>Annual Portfolio Performance Data</h3>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Year</th>
                <th>Capital Injection (USD)</th>
                <th>Capital Appreciation</th>
                <th>Total Portfolio Value</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.performance_table.map((row) => (
                <tr key={row.year}>
                  <td>{row.year}</td>
                  <td>{formatCurrencyLong(row.injection)}</td>
                  <td>{formatCurrencyLong(row.appreciation)}</td>
                  <td>{formatCurrencyLong(row.total_portfolio_value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Visualizations Grid */}
      <div className="charts-grid">
        <div className="chart-container wide">
          <h3>Fund Performance (Base Points)</h3>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={basePointsChartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" />
              <YAxis label={{ value: 'Base Points', angle: -90, position: 'insideLeft' }} />
              <Tooltip formatter={(value: number) => value.toFixed(2)} />
              <Legend />
              <Bar dataKey="investedBP" fill="#e67e22" name="Invested Capital (BP)" barSize={40} />
              <Line type="monotone" dataKey="Base Case" stroke="#2ecc71" strokeWidth={3} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="Upside Case" stroke="#3498db" strokeWidth={3} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="High Growth Case" stroke="#9b59b6" strokeWidth={3} dot={{ r: 4 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container wide">
          <h3>Annual Portfolio Value Expansion</h3>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={waterfallData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" />
              <YAxis tickFormatter={formatCurrency} />
              <Tooltip formatter={(value: number) => formatCurrencyLong(value)} />
              <Legend />
              <Bar dataKey="start_value" stackId="a" fill="transparent" />
              <Bar dataKey="injection" stackId="a" fill="#3498db" name="Capital Injection" />
              <Bar dataKey="appreciation" stackId="a" fill="#2ecc71" name="Capital Appreciation" />
              <Line type="stepAfter" dataKey="total_portfolio_value" stroke="#7f8c8d" strokeWidth={2} dot={false} name="Value Step" legendType="none" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h3>Investment Velocity (Deals)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={dashboard.performance_table}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="deals_count" fill="#9b59b6" name="Deals per Year" />
              <Line yAxisId="right" dataKey="cumulative_deals_count" stroke="#f1c40f" name="Cumulative Deals" strokeWidth={3} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h3>Investment Velocity (Amount)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={dashboard.performance_table}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" />
              <YAxis yAxisId="left" tickFormatter={formatCurrency} />
              <YAxis yAxisId="right" orientation="right" tickFormatter={formatCurrency} />
              <Tooltip formatter={(v: number) => formatCurrencyLong(v)} />
              <Legend />
              <Bar yAxisId="left" dataKey="injection" fill="#e67e22" name="Amount Invested" />
              <Line yAxisId="right" dataKey="cumulative_injection" stroke="#e74c3c" name="Cumulative Amount" strokeWidth={3} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container wide">
          <h3>Capital Appreciation</h3>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={dashboard.performance_table}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" />
              <YAxis tickFormatter={formatCurrency} />
              <Tooltip formatter={(v: number) => formatCurrencyLong(v)} />
              <Legend />
              <Line type="monotone" dataKey="cumulative_injection" stroke="#34495e" name="Total Invested Amount" strokeWidth={3} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="total_portfolio_value" stroke="#27ae60" name="Total Portfolio Value" strokeWidth={3} dot={{ r: 4 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
};

export default FundPerformanceTab;
