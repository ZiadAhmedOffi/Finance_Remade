import React, { useState } from "react";
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, LineChart, Line, Legend
} from "recharts";

interface LineGraphData {
  year: number;
  value: number;
  injection: number;      // Gross Capital Injected (Cumulative)
  distributions: number;  // Gross Distributions Received (Cumulative)
  net_cash_flow: number;  // Net Flow
  injection_breakdown?: { name: string; amount: number }[];
  yoy_gain: number | null;
}

interface YieldHistoryEntry {
  year: number;
  total: number;
  [key: string]: number;
}

interface InvestorOverviewTabProps {
  metrics: {
    total_capital_deployed: number;
    realized_gains: number;
    unrealized_gains: number;
    realized_multiple: number;
    unrealized_multiple: number;
    total_yield: number;
  };
  lineGraphData: LineGraphData[];
  yieldHistory: YieldHistoryEntry[];
}

const InvestorOverviewTab: React.FC<InvestorOverviewTabProps> = ({ metrics, lineGraphData, yieldHistory }) => {
  const [selectedBreakdown, setSelectedBreakdown] = useState<{ year: number; items: { name: string; amount: number }[] } | null>(null);

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);

  const formatCurrencyShort = (val: number) => 
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact' }).format(val);

  const formatMultiple = (val: number) => val.toFixed(2) + "x";
  const formatPercent = (val: number) => val.toFixed(2) + "%";
  
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

  // Get unique asset names from yield history for chart keys
  const assetNames = Array.from(new Set(
    yieldHistory.flatMap(entry => Object.keys(entry).filter(key => key !== 'year' && key !== 'total'))
  ));

  const COLORS = ["#6366f1", "#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#ec4899"];

  return (
    <div className="investor-overview">
      {/* High-Impact Primary Metrics */}
      <div className="metrics-vibrant-grid">
        <div className="vibrant-card blue">
          <div className="card-content">
            <label>Gross Capital Deployed</label>
            <div className="value">{formatCurrency(metrics.total_capital_deployed)}</div>
            <div className="footer">Total Capital Committed & Called</div>
          </div>
          <div className="card-icon">💰</div>
        </div>
        
        <div className="vibrant-card green">
          <div className="card-content">
            <label>Realized Gains</label>
            <div className="value">{formatCurrency(metrics.realized_gains)}</div>
            <div className="footer">Actual Profits & Distributions</div>
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

        <div className="vibrant-card indigo" style={{ transform: 'scale(1.05)', boxShadow: '0 20px 25px -5px rgba(79, 70, 229, 0.4)' }}>
          <div className="card-content">
            <label>Portfolio Yield</label>
            <div className="value">{formatPercent(metrics.total_yield)}</div>
            <div className="footer">Annualized Return Capacity</div>
          </div>
          <div className="card-icon">💵</div>
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
            <p className="chart-subtitle">Comparison of Injections, Distributions and Residual Portfolio Value</p>
          </div>
          <div className="chart-actions">
            <span className="badge year-badge">All-Time Performance</span>
          </div>
        </div>
        <div style={{ width: '100%', height: 450 }}>
          <ResponsiveContainer>
            <LineChart data={lineGraphData} margin={{ top: 20, right: 30, left: 20, bottom: 0 }}>
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
                formatter={(value, name) => [formatCurrency(Number(value ?? 0)), String(name)] as const}
                contentStyle={{ 
                  borderRadius: '16px', 
                  border: 'none', 
                  boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
                  padding: '16px'
                }}
                labelStyle={{ fontWeight: '800', marginBottom: '8px', color: '#1e293b', fontSize: '14px' }}
              />
              <Legend verticalAlign="top" height={36}/>
              <ReferenceLine x={currentYear} stroke="#ef4444" strokeDasharray="5 5" label={{ position: 'top', value: 'Current Year', fill: '#ef4444', fontSize: 12, fontWeight: '700' }} />
              
              <Line 
                type="monotone" 
                dataKey="value" 
                name="Portfolio Value (NAV)"
                stroke="#10b981" 
                strokeWidth={4}
                dot={{ r: 4 }}
                activeDot={{ r: 8 }}
              />
              <Line 
                type="stepAfter" 
                dataKey="injection" 
                name="Cumulative Injected"
                stroke="#3b82f6" 
                strokeWidth={3}
                strokeDasharray="5 5"
                dot={false}
              />
              <Line 
                type="stepAfter" 
                dataKey="distributions" 
                name="Cumulative Distributions"
                stroke="#f59e0b" 
                strokeWidth={3}
                strokeDasharray="3 3"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Yield Analytics Section - High Visibility */}
      <div className="yield-analytics-section space-y-8 mt-12 mb-12">
        <div className="section-header text-center">
          <div className="inline-block bg-indigo-50 text-indigo-600 px-4 py-1 rounded-full text-xs font-bold uppercase tracking-widest mb-4">
            Cash Income Tracking
          </div>
          <h2 className="text-3xl font-extrabold text-gray-900">Yearly Dividend & Yield Analysis</h2>
          <p className="text-gray-500 max-w-2xl mx-auto mt-2 text-lg">
            A comprehensive breakdown of the liquid returns distributed from your funds and real estate portfolios.
          </p>
        </div>

        {yieldHistory.length > 0 ? (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-10">
            {/* Yield Table */}
            <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm">
              <div className="px-6 py-5 bg-gray-50/50 border-b border-gray-100 flex justify-between items-center">
                <h3 className="font-bold text-gray-800 m-0">Annual Yield Breakdown</h3>
                <span className="text-xs text-gray-400 font-medium">Figures in USD</span>
              </div>
              <div className="table-responsive !border-0">
                <table className="data-table modern-investor-table">
                  <thead>
                    <tr>
                      <th className="!bg-transparent">Year</th>
                      {assetNames.map(name => <th key={name} className="!bg-transparent">{name}</th>)}
                      <th className="!bg-transparent text-indigo-600 font-bold">Total Yield</th>
                    </tr>
                  </thead>
                  <tbody>
                    {yieldHistory.map((row) => (
                      <tr key={row.year} className={row.year === currentYear ? "bg-indigo-50/30" : ""}>
                        <td className="font-bold">
                          {row.year}
                          {row.year === currentYear && <span className="ml-2 text-[10px] text-indigo-500 font-black">NOW</span>}
                        </td>
                        {assetNames.map(name => (
                          <td key={name} className="font-mono text-gray-600">
                            {row[name] > 0 ? formatCurrency(row[name]) : <span className="text-gray-300">—</span>}
                          </td>
                        ))}
                        <td className="font-bold font-mono text-indigo-600 bg-indigo-50/20">
                          {formatCurrency(row.total)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Yield Line Graph */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
              <div className="mb-6">
                <h3 className="font-bold text-gray-800 m-0">Yield Growth Trajectory</h3>
                <p className="text-xs text-gray-400 mt-1">Comparison of asset distributions vs. portfolio total</p>
              </div>
              <div style={{ width: '100%', height: 380 }}>
                <ResponsiveContainer>
                  <LineChart data={yieldHistory} margin={{ top: 20, right: 30, left: 10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="year" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} tickFormatter={formatCurrencyShort} />
                    <Tooltip 
                      formatter={(val: any) => formatCurrency(Number(val || 0))}
                      contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)', padding: '12px' }}
                    />
                    <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
                    {assetNames.map((name, index) => (
                      <Line 
                        key={name} 
                        type="monotone" 
                        dataKey={name} 
                        stroke={COLORS[index % COLORS.length]} 
                        strokeWidth={2} 
                        dot={{ r: 4, strokeWidth: 2, fill: '#fff' }} 
                        activeDot={{ r: 6 }}
                      />
                    ))}
                    <Line 
                      type="monotone" 
                      dataKey="total" 
                      name="Portfolio Total" 
                      stroke="#4f46e5" 
                      strokeWidth={4} 
                      dot={{ r: 6, fill: '#4f46e5' }} 
                      strokeDasharray="5 5"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border-2 border-dashed border-gray-200 text-center py-20">
            <div className="text-6xl mb-6">🏦</div>
            <h3 className="text-gray-900 font-black text-2xl mb-2">No Yield Performance History</h3>
            <p className="text-gray-500 max-w-lg mx-auto text-lg">
              Distributions from your Equity Funds and Real Estate Portfolios (Positive Cash Flows) will be automatically tracked and displayed here.
            </p>
          </div>
        )}
      </div>

      {/* Historical Breakdown Table */}
      <div className="content-card modern-table-card mt-12">
        <div className="card-header">
          <h3>Annual Portfolio Performance</h3>
        </div>
        <div className="table-responsive">
          <table className="data-table modern-investor-table">
            <thead>
              <tr>
                <th>Year</th>
                <th>Capital Injected (Gross)</th>
                <th>Distributions Received</th>
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
                  <td className="font-mono text-blue-600">
                    {row.injection !== 0 ? formatCurrency(row.injection) : "—"}
                  </td>
                  <td className="font-mono text-orange-600">
                    {row.distributions !== 0 ? formatCurrency(row.distributions) : "—"}
                  </td>
                  <td 
                    className={`font-mono cursor-pointer hover:bg-gray-100 transition-colors ${row.net_cash_flow >= 0 ? "text-green" : "text-red"}`}
                    onClick={() => {
                      if (row.injection_breakdown && row.injection_breakdown.length > 0) {
                        setSelectedBreakdown({ year: row.year, items: row.injection_breakdown });
                      }
                    }}
                    title="Click to see breakdown"
                  >
                    {row.net_cash_flow !== 0 ? formatCurrency(row.net_cash_flow) : "—"}
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
                  <td colSpan={6} className="empty-msg">No historical data available.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Flow Breakdown Modal */}
      {selectedBreakdown && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in zoom-in duration-200">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
              <h3 className="text-lg font-bold text-gray-900">Flow Breakdown - {selectedBreakdown.year}</h3>
              <button onClick={() => setSelectedBreakdown(null)} className="text-gray-500 hover:text-gray-900 text-2xl font-bold">✕</button>
            </div>
            <div className="p-6 max-h-[60vh] overflow-y-auto">
              <div className="space-y-4">
                {selectedBreakdown.items.map((item, idx) => (
                  <div key={idx} className="flex justify-between items-center p-3 rounded-xl bg-gray-50 border border-gray-100 hover:border-indigo-200 hover:bg-indigo-50/30 transition-all">
                    <span className="font-semibold text-gray-700">{item.name}</span>
                    <span className={`font-bold font-mono ${item.amount >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                      {item.amount >= 0 ? "+" : ""}{formatCurrency(item.amount)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-between items-center">
              <span className="text-sm font-bold text-gray-500 uppercase">Yearly Net Flow</span>
              <span className={`text-xl font-black font-mono ${selectedBreakdown.items.reduce((acc, i) => acc + i.amount, 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                {formatCurrency(selectedBreakdown.items.reduce((acc, i) => acc + i.amount, 0))}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InvestorOverviewTab;
