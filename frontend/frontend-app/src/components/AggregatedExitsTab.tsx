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
  ResponsiveContainer
} from "recharts";

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

interface PerformanceData {
  dashboard: {
    total_invested: number;
  };
  aggregated_exits: CaseData[];
}

interface AggregatedExitsTabProps {
  fundId: string;
}

const AggregatedExitsTab: React.FC<AggregatedExitsTabProps> = ({ fundId }) => {
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

  const { dashboard, aggregated_exits } = data;

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);

  const formatCurrencyShort = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);
  
  const formatPercent = (val: number) => (val * 100).toFixed(2) + "%";
  const formatRawPercent = (val: number) => val.toFixed(2) + "%";
  const formatMultiple = (val: number) => val.toFixed(2) + "x";

  // Prepare data for the chart
  const chartData = aggregated_exits.map(c => ({
    name: c.case,
    invested: dashboard.total_invested,
    gev: c.gev,
    irr: c.irr * 100 // Convert to percentage for the axis
  }));

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
      <div className="metric-card prominent centered">
        <label>Total Invested Capital</label>
        <div className="value">{formatCurrency(dashboard.total_invested)}</div>
      </div>

      <div className="comparison-table-container">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Case</th>
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

      <div className="exit-chart-container">
        <h3>Exits Analysis by Case</h3>
        <ResponsiveContainer width="100%" height={500}>
          <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" />
            <YAxis yAxisId="left" orientation="left" tickFormatter={formatCurrencyShort} label={{ value: 'Capital (USD)', angle: -90, position: 'insideLeft' }} />
            <YAxis yAxisId="right" orientation="right" tickFormatter={(v) => `${v}%`} label={{ value: 'IRR (%)', angle: 90, position: 'insideRight' }} />
            <Tooltip 
              formatter={(value: any, name: string) => {
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

      <style>{`
        .exit-chart-container {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.05);
          margin-top: 3rem;
          border: 1px solid #eef2f6;
        }
        .exit-chart-container h3 {
          margin-top: 0;
          margin-bottom: 2rem;
          color: #2c3e50;
          font-size: 1.3rem;
          text-align: center;
        }
      `}</style>
    </section>
  );
};

export default AggregatedExitsTab;
