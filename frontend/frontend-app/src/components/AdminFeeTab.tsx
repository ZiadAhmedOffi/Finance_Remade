import React, { useState, useEffect } from "react";
import { api } from "../api/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";

/**
 * Interface representing the primary fund cost categories.
 */
interface AdminFeeData {
  total_admin_cost: number;
  operations_fee: number;
  management_fees: number;
  total_costs: number;
  inception_year: number;
  fund_life: number;
}

interface PerformanceData {
  admin_fee: AdminFeeData;
}

interface AdminFeeTabProps {
  fundId: string;
}

/**
 * AdminFeeTab Component
 * 
 * Provides a granular breakdown of the fund's General & Administrative (G&A) costs.
 * Logic includes specific allocation rules for:
 * - Legal & Admin Costs (Licensing, Contracts)
 * - Operations (Onboarding, Marketing, Auditing)
 * - Management Fees
 * 
 * @param {string} fundId - The unique identifier of the fund.
 */
const AdminFeeTab: React.FC<AdminFeeTabProps> = ({ fundId }) => {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetches fee and cost data.
   */
  useEffect(() => {
    const fetchPerformance = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/funds/${fundId}/performance/`);
        setData(response.data);
      } catch (err) {
        setError("Failed to fetch admin fee data.");
      } finally {
        setLoading(false);
      }
    };
    fetchPerformance();
  }, [fundId]);

  if (loading) return <div>Loading Admin Fee Data...</div>;
  if (error) return <div className="error-state">{error}</div>;
  if (!data) return null;

  const { admin_fee } = data;
  const { inception_year, fund_life, total_admin_cost, operations_fee, management_fees } = admin_fee;

  // Formatting Utilities
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);

  const formatCurrencyShort = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);

  const years = Array.from({ length: fund_life }, (_, i) => inception_year + i);

  /* --- Cost Allocation Logic --- */

  // 1. Legal & Admin Costs Breakdown
  const estLicensingY1 = total_admin_cost * 0.05;
  const estLicensingLater = estLicensingY1 * 0.5;
  const row1Vals = years.map((_, i) => i === 0 ? estLicensingY1 : estLicensingLater);
  const row1Total = row1Vals.reduce((a, b) => a + b, 0);

  const contractsY1 = operations_fee * 0.2;
  const contractsLater = operations_fee * 0.02;
  const row2Vals = years.map((_, i) => i === 0 ? contractsY1 : contractsLater);
  const row2Total = row2Vals.reduce((a, b) => a + b, 0);

  const othersLegalVal = (total_admin_cost - (row1Total + row2Total)) / fund_life;
  const row3Vals = years.map(() => othersLegalVal);
  const row3Total = othersLegalVal * fund_life;

  const table1TotalsPerYear = years.map((_, i) => row1Vals[i] + row2Vals[i] + row3Vals[i]);

  // 2. Operations Costs Breakdown
  const onboardingVal = operations_fee * 0.05;
  const rowO1Vals = years.map((_, i) => i < 2 ? onboardingVal : 0);
  const rowO1Total = rowO1Vals.reduce((a, b) => a + b, 0);

  const marketingVal = (operations_fee * 0.4) / fund_life;
  const rowO2Vals = years.map(() => marketingVal);
  const rowO2Total = marketingVal * fund_life;

  const reportVal = operations_fee * 0.02;
  const rowO3Vals = years.map(() => reportVal);
  const rowO3Total = rowO3Vals.reduce((a, b) => a + b, 0);

  const accountingVal = operations_fee * 0.04;
  const rowO4Vals = years.map(() => accountingVal);
  const rowO4Total = accountingVal * fund_life;

  const othersOpsVal = (operations_fee - (rowO1Total + rowO2Total + rowO3Total + rowO4Total)) / fund_life;
  const rowO5Vals = years.map(() => othersOpsVal);
  const rowO5Total = othersOpsVal * fund_life;

  const table2TotalsPerYear = years.map((_, i) => 
    rowO1Vals[i] + rowO2Vals[i] + rowO3Vals[i] + rowO4Vals[i] + rowO5Vals[i]
  );

  // 3. Fund Management Fees (Static annual allocation)
  const managementVal = management_fees / fund_life;
  const rowM1Vals = years.map(() => managementVal);

  // 4. Combined G&A Total
  const totalGAVals = years.map((_, i) => table1TotalsPerYear[i] + table2TotalsPerYear[i] + rowM1Vals[i]);

  /**
   * Helper to render yearly cost tables with consistent formatting.
   */
  const renderYearlyTable = (
    title: string, 
    rows: { label: string, values: number[], total: number, isBold?: boolean }[], 
    totals: number[],
    showTotalRow: boolean = true
  ) => (
    <div className="content-card">
      <h3>{title}</h3>
      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Description</th>
              {years.map(y => <th key={y}>{y}</th>)}
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx} className={row.isBold ? "total-row" : ""}>
                <td>{row.isBold ? <strong>{row.label}</strong> : row.label}</td>
                {row.values.map((v, i) => (
                  <td key={i}>{row.isBold ? <strong>{formatCurrency(v)}</strong> : formatCurrency(v)}</td>
                ))}
                <td><strong>{formatCurrency(row.total)}</strong></td>
              </tr>
            ))}
            {showTotalRow && (
              <tr className="total-row">
                <td><strong>Total</strong></td>
                {totals.map((t, i) => <td key={i}><strong>{formatCurrency(t)}</strong></td>)}
                <td><strong>{formatCurrency(totals.reduce((a, b) => a + b, 0))}</strong></td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  // Prepare chart data for breakdown visualizations
  const chartData = years.map((year, i) => ({
    year,
    "Fund Estabilishment & Licensing": row1Vals[i],
    "Contracts & Agreements": row2Vals[i],
    "Legal Others": row3Vals[i],
    "Startups Onboarding": rowO1Vals[i],
    "Marketing & Events": rowO2Vals[i],
    "Annual Fund Performance Report": rowO3Vals[i],
    "Accounting & Auditing": rowO4Vals[i],
    "Ops Others": rowO5Vals[i],
    "Total G&A": totalGAVals[i],
  }));

  return (
    <section className="admin-fee-tab" style={{display: 'flex', flexDirection: 'column', gap: '4rem'}}>
      {/* Master Summary Table */}
      <div className="content-card">
        <h3>Total Fund Costs</h3>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Description</th>
                <th>Total (USD)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Total Admin Cost</td>
                <td>{formatCurrency(admin_fee.total_admin_cost)}</td>
              </tr>
              <tr>
                <td>Operations Fee</td>
                <td>{formatCurrency(admin_fee.operations_fee)}</td>
              </tr>
              <tr>
                <td>Management Fees</td>
                <td>{formatCurrency(admin_fee.management_fees)}</td>
              </tr>
              <tr className="total-row">
                <td><strong>Total Fund Costs</strong></td>
                <td><strong>{formatCurrency(admin_fee.total_costs)}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Segmented Yearly Breakdown Tables */}
      {renderYearlyTable("Legal & Admin Costs", [
        { label: "Fund Estabilishment & Licensing costs", values: row1Vals, total: row1Total },
        { label: "Contracts & Agreements", values: row2Vals, total: row2Total },
        { label: "Others", values: row3Vals, total: row3Total }
      ], table1TotalsPerYear)}

      {renderYearlyTable("Operations", [
        { label: "Startups Onboarding", values: rowO1Vals, total: rowO1Total },
        { label: "Marketing & Events", values: rowO2Vals, total: rowO2Total },
        { label: "Annual Fund Performance Report", values: rowO3Vals, total: rowO3Total },
        { label: "Accounting & Auditing", values: rowO4Vals, total: rowO4Total },
        { label: "Others", values: rowO5Vals, total: rowO5Total }
      ], table2TotalsPerYear)}

      {renderYearlyTable("Fund Management", [
        { label: "Fund Management", values: rowM1Vals, total: management_fees }
      ], rowM1Vals)}

      {renderYearlyTable("Total G&A", [
        { label: "Total G&A", values: totalGAVals, total: totalGAVals.reduce((a, b) => a + b, 0), isBold: true }
      ], totalGAVals, false)}

      {/* Cost Trend Visualizations */}
      <div className="charts-grid">
        <div className="chart-container">
          <h3>Total G&A Costs per Year</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" />
              <YAxis tickFormatter={formatCurrencyShort} />
              <Tooltip formatter={(v: any) => formatCurrency(Number(v))} />
              <Legend />
              <Line type="monotone" dataKey="Total G&A" stroke="#2c3e50" strokeWidth={3} dot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h3>Operations Costs Breakdown</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" />
              <YAxis tickFormatter={formatCurrencyShort} />
              <Tooltip formatter={(v: any) => formatCurrency(Number(v))} />
              <Legend />
              <Line type="monotone" dataKey="Startups Onboarding" stroke="#3498db" strokeWidth={2} />
              <Line type="monotone" dataKey="Marketing & Events" stroke="#e67e22" strokeWidth={2} />
              <Line type="monotone" dataKey="Annual Fund Performance Report" stroke="#9b59b6" strokeWidth={2} />
              <Line type="monotone" dataKey="Accounting & Auditing" stroke="#f1c40f" strokeWidth={2} />
              <Line type="monotone" dataKey="Ops Others" stroke="#7f8c8d" strokeWidth={2} strokeDasharray="5 5" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container wide">
          <h3>Admin Costs Breakdown</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" />
              <YAxis tickFormatter={formatCurrencyShort} />
              <Tooltip formatter={(v: any) => formatCurrency(Number(v))} />
              <Legend />
              <Line type="monotone" dataKey="Fund Estabilishment & Licensing" stroke="#27ae60" strokeWidth={2} />
              <Line type="monotone" dataKey="Contracts & Agreements" stroke="#e74c3c" strokeWidth={2} />
              <Line type="monotone" dataKey="Legal Others" stroke="#95a5a6" strokeWidth={2} strokeDasharray="5 5" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
};

export default AdminFeeTab;
