import React from "react";
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, ReferenceLine 
} from "recharts";

interface LineGraphData {
  year: number;
  value: number;
  injection: number;
  yoy_gain: number | null;
}

interface InvestorOverviewTabProps {
  metrics: {
    total_capital_deployed: number;
    realized_gains: number;
    unrealized_gains: number;
    realized_multiple: number;
    unrealized_multiple: number;
  };
  lineGraphData: LineGraphData[];
}

const InvestorOverviewTab: React.FC<InvestorOverviewTabProps> = ({ metrics, lineGraphData }) => {
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);

  const formatCurrencyShort = (val: number) => 
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact' }).format(val);

  const formatMultiple = (val: number) => val.toFixed(2) + "x";
  
  const renderYoY = (val: number | null) => {
    if (val === null) return <span className="text-muted">N/A</span>;
    const isPositive = val >= 0;
    return (
      <span className={`font-bold ${isPositive ? "text-green" : "text-red"}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
        {isPositive ? "↑" : "↓"} {Math.abs(val).toFixed(2)}%
      </span>
    );
  };

  const currentYear = new Date().getFullYear();

  return (
    <div className="investor-overview">
      {/* High-Impact Primary Metrics */}
      <div className="metrics-vibrant-grid">
        <div className="vibrant-card blue">
          <div className="card-content">
            <label>Capital Deployed</label>
            <div className="value">{formatCurrency(metrics.total_capital_deployed)}</div>
            <div className="footer">Net Investment Position</div>
          </div>
          <div className="card-icon">💰</div>
        </div>
        
        <div className="vibrant-card green">
          <div className="card-content">
            <label>Realized Gains</label>
            <div className="value">{formatCurrency(metrics.realized_gains)}</div>
            <div className="footer">Actual Profits Withdrawn</div>
          </div>
          <div className="card-icon">📈</div>
        </div>

        <div className="vibrant-card emerald">
          <div className="card-content">
            <label>Unrealized Gains</label>
            <div className="value">{formatCurrency(metrics.unrealized_gains)}</div>
            <div className="footer">Current Market Appreciation</div>
          </div>
          <div className="card-icon">💎</div>
        </div>
      </div>

      {/* Multiples Row with Glassmorphism / Modern styling */}
      <div className="multiples-container content-card">
        <div className="multiple-item">
          <div className="m-label">DPI (Realized X)</div>
          <div className="m-value">{formatMultiple(metrics.realized_multiple)}</div>
        </div>
        <div className="multiple-divider" />
        <div className="multiple-item">
          <div className="m-label">RVPI (Unrealized X)</div>
          <div className="m-value">{formatMultiple(metrics.unrealized_multiple)}</div>
        </div>
        <div className="multiple-divider" />
        <div className="multiple-item highlight">
          <div className="m-label">TVPI (Total X)</div>
          <div className="m-value">{formatMultiple(metrics.realized_multiple + metrics.unrealized_multiple)}</div>
        </div>
      </div>

      {/* Main Portfolio Chart */}
      <div className="chart-container content-card wide-chart modern-chart">
        <div className="chart-header">
          <div>
            <h3>Portfolio Growth Analysis</h3>
            <p className="chart-subtitle">Historical aggregate value of your holdings across all funds</p>
          </div>
          <div className="chart-actions">
            <span className="badge year-badge">All-Time Performance</span>
          </div>
        </div>
        <div style={{ width: '100%', height: 450 }}>
          <ResponsiveContainer>
            <AreaChart data={lineGraphData} margin={{ top: 20, right: 30, left: 20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis 
                dataKey="year" 
                stroke="#64748b" 
                tick={{fill: '#64748b', fontSize: 12, fontWeight: 500}}
                tickLine={false}
                axisLine={false}
                dy={10}
              />
              <YAxis 
                stroke="#64748b" 
                tick={{fill: '#64748b', fontSize: 12, fontWeight: 500}}
                tickFormatter={formatCurrencyShort}
                tickLine={false}
                axisLine={false}
                dx={-10}
              />
              <Tooltip 
                formatter={(val: any) => [formatCurrency(Number(val || 0)), "Portfolio Value"]}
                contentStyle={{ 
                  borderRadius: '16px', 
                  border: 'none', 
                  boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
                  padding: '16px'
                }}
                labelStyle={{ fontWeight: '800', marginBottom: '8px', color: '#1e293b', fontSize: '14px' }}
              />
              <ReferenceLine x={currentYear} stroke="#ef4444" strokeDasharray="5 5" label={{ position: 'top', value: 'Current Year', fill: '#ef4444', fontSize: 12, fontWeight: '700' }} />
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke="#10b981" 
                fillOpacity={1} 
                fill="url(#colorValue)" 
                strokeWidth={4}
                activeDot={{ r: 8, strokeWidth: 0, fill: '#059669' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Historical Breakdown Table */}
      <div className="content-card modern-table-card">
        <div className="card-header">
          <h3>Annual Performance Breakdown</h3>
        </div>
        <div className="table-responsive">
          <table className="data-table modern-investor-table">
            <thead>
              <tr>
                <th>Year</th>
                <th>Net Cash Flow</th>
                <th>Portfolio Value</th>
                <th>YoY Performance</th>
              </tr>
            </thead>
            <tbody>
              {lineGraphData.map((row) => (
                <tr key={row.year} className={row.year === currentYear ? "current-year-row" : ""}>
                  <td className="year-cell">
                    <span className="year-text">{row.year}</span>
                    {row.year === currentYear && <span className="current-indicator">Current</span>}
                  </td>
                  <td className={`font-mono ${row.injection >= 0 ? "text-green" : "text-red"}`}>
                    {row.injection !== 0 ? formatCurrency(row.injection) : "—"}
                  </td>
                  <td className="font-bold font-mono text-dark">
                    {formatCurrency(row.value)}
                  </td>
                  <td>
                    {renderYoY(row.yoy_gain)}
                  </td>
                </tr>
              ))}
              {lineGraphData.length === 0 && (
                <tr>
                  <td colSpan={4} className="empty-msg">No historical data available.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default InvestorOverviewTab;
