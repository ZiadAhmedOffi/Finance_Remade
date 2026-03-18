import React, { useState, useEffect } from "react";
import { api } from "../api/api";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from "recharts";

/**
 * Interface representing a single year's entry in the performance table.
 */
interface PerformanceTableEntry {
  year: number;
  current_year: number;
  is_future: boolean;
  injection_current: number;
  appreciation_current: number;
  injection_prognosis: number;
  appreciation_prognosis: number;
  appreciation_of_current_after_cutoff: number;
  injection_of_current_after_cutoff: number;
  total_portfolio_value_no_prognosis: number;
  total_portfolio_value_with_prognosis: number;
  cumulative_injection_no_prognosis: number;
  cumulative_injection_with_prognosis: number;
  deals_count_current: number;
  deals_count_prognosis: number;
  cumulative_deals_count_current: number;
  cumulative_deals_count_prognosis: number;
}

/**
 * Interface representing the performance metrics for a single investment scenario.
 */
interface CaseData {
  case: string;
  gev: number;
  profit_before_carry: number;
  gross_moic: number;
  carry_pct: number;
  carry_amount: number;
  total_fees: number;
  net_to_investors: number;
  real_moic: number;
  irr: number;
}

/**
 * Interface for the API response structure.
 */
interface PerformanceData {
  dashboard: {
    total_invested: number;
    performance_table: PerformanceTableEntry[];
  };
  aggregated_exits: CaseData[];
  admin_fee: {
    total_admin_cost: number;
    operations_fee: number;
    management_fees: number;
    total_costs: number;
    inception_year: number;
    fund_life: number;
  };
}

interface AggregatedExitsTabProps {
  fundId: string;
}

/**
 * AggregatedExitsTab Component
 * 
 * Displays a comparative analysis of different investment scenarios (Base, Upside, High Growth).
 * Includes a detailed metric comparison table and a visual analysis chart.
 * 
 * @param {string} fundId - The unique identifier of the fund.
 */
const AggregatedExitsTab: React.FC<AggregatedExitsTabProps> = ({ fundId }) => {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetches the comparative scenario data.
   */
  useEffect(() => {
    const fetchPerformance = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/funds/${fundId}/performance/`);
        setData(response.data);
      } catch (err) {
        setError("Failed to fetch aggregated exits data.");
      } finally {
        setLoading(false);
      }
    };
    fetchPerformance();
  }, [fundId]);

  if (loading) return <div>Loading Aggregated Exits Data...</div>;
  if (error) return <div className="error-state">{error}</div>;
  if (!data) return null;

  const { dashboard, aggregated_exits, admin_fee } = data;

  // Formatting Utilities
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);

  const formatCurrencyShort = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);
  
  const formatPercent = (val: number) => (val * 100).toFixed(2) + "%";
  const formatRawPercent = (val: number) => val.toFixed(2) + "%";
  const formatMultiple = (val: number) => val.toFixed(2) + "x";

  // Data mapping for Recharts
  const chartData = aggregated_exits.map(c => ({
    name: c.case,
    invested: dashboard.total_invested,
    gev: c.gev,
    irr: c.irr * 100 
  }));

  const currentYear = dashboard.performance_table[0]?.current_year || new Date().getFullYear();

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

    // ... (G&A logic remains same as it's based on fund constants)
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
    
    // Multipliers for cases
    const multipliers: Record<string, number> = {
        "Base Case": 1.0,
        "Upside Case": 1.2,
        "High Growth Case": 1.5
    };

    let portfolioBase = 0;
    let portfolioUpside = 0;
    let portfolioHighGrowth = 0;

    return dashboard.performance_table.map((row) => {
      const injection = row.injection_current + row.injection_prognosis + row.injection_of_current_after_cutoff;
      const baseAppreciation = row.appreciation_current + row.appreciation_prognosis + row.appreciation_of_current_after_cutoff;
      
      const gaYearly = gaMap[row.year] || 0;

      portfolioBase += injection + (baseAppreciation * multipliers["Base Case"]);
      portfolioUpside += injection + (baseAppreciation * multipliers["Upside Case"]);
      portfolioHighGrowth += injection + (baseAppreciation * multipliers["High Growth Case"]);

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

  // Define table rows for consistent rendering
  const rows = [
    { label: "Gross Exit Value", key: "gev", type: "currency" },
    { label: "Profit Before Carry", key: "profit_before_carry", type: "currency" },
    { label: "Gross MOIC", key: "gross_moic", type: "multiple" },
    { label: "Carry (%)", key: "carry_pct", type: "raw_percent" },
    { label: "Carry Amount", key: "carry_amount", type: "currency" },
    { label: "Total Fees", key: "total_fees", type: "currency" },
    { label: "Net to Investors", key: "net_to_investors", type: "currency" },
    { label: "Real MOIC", key: "real_moic", type: "multiple" },
    { label: "IRR", key: "irr", type: "percent" },
  ];

  return (
    <section className="aggregated-exits-tab">
      {/* High-Visibility Summary Metric */}
      <div className="content-card" style={{background: '#f0f7ff', borderColor: '#007bff', marginBottom: '3rem'}}>
        <div style={{display: 'flex', justifyContent: 'center', textAlign: 'center'}}>
          <div className="summary-item">
            <label style={{color: '#0056b3', fontSize: '1rem', fontWeight: '600', textTransform: 'uppercase'}}>Total Invested Capital</label>
            <div className="summary-value" style={{fontSize: '2.5rem', fontWeight: '800', color: '#007bff'}}>
              {formatCurrency(dashboard.total_invested)}
            </div>
          </div>
        </div>
      </div>

      {/* Comparison Matrix */}
      <div className="content-card" style={{marginBottom: '4rem'}}>
        <h3>Exits Comparison by Scenario</h3>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Metric</th>
                {aggregated_exits.map(c => <th key={c.case}>{c.case}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map(row => (
                <tr key={row.key}>
                  <td><strong>{row.label}</strong></td>
                  {aggregated_exits.map(c => {
                      const val = (c as any)[row.key];
                      let formatted = val;
                      if (row.type === "currency") formatted = formatCurrency(val);
                      if (row.type === "multiple") formatted = formatMultiple(val);
                      if (row.type === "percent") formatted = formatPercent(val);
                      if (row.type === "raw_percent") formatted = formatRawPercent(val);
                      return <td key={c.case}>{formatted}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Scenarios Visualization */}
      <div className="charts-grid">
        <div className="chart-container wide">
          <h3>Exits Analysis by Case</h3>
          <ResponsiveContainer width="100%" height={500}>
            <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" />
              <YAxis yAxisId="left" orientation="left" tickFormatter={formatCurrencyShort} label={{ value: 'Capital (USD)', angle: -90, position: 'insideLeft' }} />
              <YAxis yAxisId="right" orientation="right" tickFormatter={(v) => `${v}%`} label={{ value: 'IRR (%)', angle: 90, position: 'insideRight' }} />
              <Tooltip 
                formatter={(value: any, name: any) => {
                  if (name === "irr") return [`${Number(value).toFixed(2)}%`, "IRR"];
                  return [formatCurrency(Number(value)), name === "invested" ? "Total Invested" : "Gross Exit Value"];
                }}
              />
              <Legend />
              <Bar yAxisId="left" dataKey="invested" fill="#34495e" name="Total Invested Amount" barSize={40} />
              <Bar yAxisId="left" dataKey="gev" fill="#3498db" name="Gross Exit Value" barSize={40} />
              <Line yAxisId="right" type="monotone" dataKey="irr" stroke="#e74c3c" name="IRR (%)" strokeWidth={3} dot={{ r: 6 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container wide">
          <h3>Fund Performance (Base Points)</h3>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={basePointsChartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" />
              <YAxis label={{ value: 'Base Points', angle: -90, position: 'insideLeft' }} />
              <Tooltip formatter={(value: any) => Number(value).toFixed(2)} />
              <Legend />
              <ReferenceLine x={currentYear} stroke="#e74c3c" strokeDasharray="3 3" label={{ position: 'top', value: 'Current Year', fill: '#e74c3c', fontSize: 12 }} />
              <Bar dataKey="investedBP" fill="#e67e22" name="Invested Capital (BP)" barSize={40} />
              <Line type="monotone" dataKey="Base Case" stroke="#2ecc71" strokeWidth={3} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="Upside Case" stroke="#3498db" strokeWidth={3} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="High Growth Case" stroke="#9b59b6" strokeWidth={3} dot={{ r: 4 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
};

export default AggregatedExitsTab;
