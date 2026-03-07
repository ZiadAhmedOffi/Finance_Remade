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
  Cell
} from "recharts";

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

interface PerformanceData {
  dashboard: {
    total_invested: number;
    gross_exit_value: number;
    moic: number;
    irr: number;
    total_deals: number;
    performance_table: PerformanceTableEntry[];
  };
}

interface FundPerformanceTabProps {
  fundId: string;
}

const FundPerformanceTab: React.FC<FundPerformanceTabProps> = ({ fundId }) => {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
  if (error) return <div className="error-state">{error}</div>;
  if (!data) return null;

  const { dashboard } = data;

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);

  const formatCurrencyLong = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);
  
  const formatPercent = (val: number) => (val * 100).toFixed(2) + "%";
  const formatMultiple = (val: number) => val.toFixed(2) + "x";

  // Prepare data for Waterfall Chart (Annual Portfolio Value Expansion)
  // We use stacked bars: 
  // 1. Transparent bar for "start_value"
  // 2. Bar for "injection"
  // 3. Bar for "appreciation"
  const waterfallData = dashboard.performance_table.map((entry, index) => ({
    ...entry,
    // For connecting lines, we need the start point of next year's bar 
    // which is the end point of current year's bar.
    // Horizontal lines in Recharts can be represented by a Line with 
    // points at (x, y) and (x+1, y). This is hard.
    // Simpler: Just provide the end value.
    end_value: entry.total_portfolio_value
  }));

  // Helper component to render connecting lines for the waterfall
  // This is a custom shape or just another line series?
  // Let's use a "Step" line for connecting the bars if possible.
  
  return (
    <section className="performance-tab">
      <div className="metric-rows">
        <div className="metric-row">
          <div className="metric-card prominent">
            <label>Total Amount Invested</label>
            <div className="value">{formatCurrencyLong(dashboard.total_invested)}</div>
          </div>
          <div className="metric-card prominent">
            <label>Gross Exit Value</label>
            <div className="value">{formatCurrencyLong(dashboard.gross_exit_value)}</div>
          </div>
        </div>
        <div className="metric-row">
          <div className="metric-card">
            <label>MOIC Multiple</label>
            <div className="value">{formatMultiple(dashboard.moic)}</div>
          </div>
          <div className="metric-card">
            <label>IRR</label>
            <div className="value">{formatPercent(dashboard.irr)}</div>
          </div>
          <div className="metric-card">
            <label>Total Deals</label>
            <div className="value">{dashboard.total_deals}</div>
          </div>
        </div>
      </div>

      <div className="charts-grid">
        {/* Graph 1: Annual Portfolio Value Expansion */}
        <div className="chart-container wide">
          <h3>Annual Portfolio Value Expansion</h3>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={waterfallData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" />
              <YAxis tickFormatter={formatCurrency} />
              <Tooltip formatter={(value: number) => formatCurrencyLong(value)} />
              <Legend />
              {/* Transparent "push" bar */}
              <Bar dataKey="start_value" stackId="a" fill="transparent" />
              <Bar dataKey="injection" stackId="a" fill="#3498db" name="Capital Injection" />
              <Bar dataKey="appreciation" stackId="a" fill="#2ecc71" name="Capital Appreciation" />
              {/* Connecting line using a "step" type line */}
              <Line 
                type="stepAfter" 
                dataKey="total_portfolio_value" 
                stroke="#7f8c8d" 
                strokeWidth={2} 
                dot={false}
                name="Value Step"
                legendType="none"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Graph 2: Investment Velocity - Deals */}
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

        {/* Graph 3: Investment Velocity - Amount */}
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

        {/* Graph 4: Capital Appreciation */}
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

      <div className="performance-table-container">
        <h3>Annual Portfolio Performance Data</h3>
        <table className="performance-table">
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

      <style>{`
        .charts-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 2rem;
          margin: 2rem 0;
        }
        .chart-container {
          background: white;
          padding: 1.5rem;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.05);
          border: 1px solid #eef2f6;
        }
        .chart-container.wide {
          grid-column: span 2;
        }
        .chart-container h3 {
          margin-top: 0;
          margin-bottom: 1.5rem;
          color: #2c3e50;
          font-size: 1.1rem;
          border-bottom: 1px solid #f0f0f0;
          padding-bottom: 0.5rem;
        }
      `}</style>
    </section>
  );
};

export default FundPerformanceTab;
