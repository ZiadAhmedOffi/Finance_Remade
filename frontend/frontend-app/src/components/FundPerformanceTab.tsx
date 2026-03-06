import React, { useState, useEffect } from "react";
import { api } from "../api/api";

interface PerformanceData {
  dashboard: {
    total_invested: number;
    gross_exit_value: number;
    moic: number;
    irr: number;
    total_deals: number;
    performance_table: Array<{
      year: number;
      injection: number;
      appreciation: number;
      total_portfolio_value: number;
    }>;
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
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);
  
  const formatPercent = (val: number) => (val * 100).toFixed(2) + "%";
  const formatMultiple = (val: number) => val.toFixed(2) + "x";

  return (
    <section className="performance-tab">
      <div className="metric-rows">
        <div className="metric-row">
          <div className="metric-card prominent">
            <label>Total Amount Invested</label>
            <div className="value">{formatCurrency(dashboard.total_invested)}</div>
          </div>
          <div className="metric-card prominent">
            <label>Gross Exit Value</label>
            <div className="value">{formatCurrency(dashboard.gross_exit_value)}</div>
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

      <div className="performance-table-container">
        <h3>Annual Portfolio Performance</h3>
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
                <td>{formatCurrency(row.injection)}</td>
                <td>{formatCurrency(row.appreciation)}</td>
                <td>{formatCurrency(row.total_portfolio_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default FundPerformanceTab;
