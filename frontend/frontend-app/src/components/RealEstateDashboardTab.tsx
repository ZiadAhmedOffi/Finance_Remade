import React, { useState, useEffect } from "react";
import { realEstateApi } from "../api/api";
import { formatCurrency, formatPercent } from "../utils/formatters";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
  LineChart, Line
} from 'recharts';
import LiquidityGauge from "./LiquidityGauge";

interface DashboardData {
  metrics: {
    property_count_active: number;
    portfolio_market_value: number;
    total_invested_capital: number;
    unrealized_gains: number;
    realized_gains: number;
    total_annual_rent: number;
    total_noi: number;
    total_annual_debt_service: number;
    net_cash_flow_y1: number;
    portfolio_gross_yield: number;
    portfolio_net_yield: number;
    portfolio_roi: number;
  };
  distribution: {
    by_type: { type: string; value: number; percentage: number }[];
    by_country: { country: string; value: number; percentage: number }[];
  };
  value_gain_table: {
    id: string;
    name: string;
    cost_basis: number;
    current_market_value: number | null;
    unrealized_gain: number | null;
    realized_gain: number;
    status: string;
  }[];
  appreciation_projection: {
    years: number[];
    properties: { [key: string]: { name: string; values: number[] } };
    portfolio_total: number[];
  };
  liquidation_index: {
    table: {
      id: string;
      name: string;
      status: string;
      years_held: number;
      net_yield: number;
      gain_percentage: number;
      liquidation_index: number;
    }[];
    portfolio_average: number;
  };
  off_plan_stages: {
    id: string;
    name: string;
    start_date: string;
    completion_date: string;
    time_elapsed_percentage: number;
    capital_deployed_percentage: number;
    stage: string;
  }[];
  yield_analysis: {
    id: string;
    name: string;
    annual_rent: number;
    noi: number;
    annual_debt_service: number;
    gross_yield: number;
    net_yield: number;
  }[];
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#a4de6c', '#d0ed57', '#ffc658'];

const DashboardSection: React.FC<{ 
  title: string; 
  id: string; 
  children: React.ReactNode;
  defaultOpen?: boolean;
}> = ({ title, id, children, defaultOpen = true }) => {
  const storageKey = `re_dashboard_section_${id}`;
  const [isOpen, setIsOpen] = useState(() => {
    const saved = localStorage.getItem(storageKey);
    return saved !== null ? JSON.parse(saved) : defaultOpen;
  });

  const toggle = () => {
    const newState = !isOpen;
    setIsOpen(newState);
    localStorage.setItem(storageKey, JSON.stringify(newState));
  };

  return (
    <div className="dashboard-section" style={{ marginBottom: '1.5rem', background: 'white', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
      <div 
        onClick={toggle}
        style={{ 
          padding: '1rem 1.5rem', 
          background: '#f8fafc', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          cursor: 'pointer',
          borderBottom: isOpen ? '1px solid #e2e8f0' : 'none'
        }}
      >
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#334155' }}>{title}</h3>
        <span style={{ 
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)', 
          transition: 'transform 0.3s ease',
          fontSize: '1.2rem',
          color: '#64748b'
        }}>
          ▼
        </span>
      </div>
      <div style={{ 
        maxHeight: isOpen ? '5000px' : '0', 
        opacity: isOpen ? 1 : 0,
        overflow: 'hidden',
        transition: 'all 0.4s ease-in-out',
        padding: isOpen ? '1.5rem' : '0 1.5rem'
      }}>
        {children}
      </div>
    </div>
  );
};

const RealEstateDashboardTab: React.FC<{ portfolioId: string }> = ({ portfolioId }) => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, [portfolioId]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await realEstateApi.getDashboard(portfolioId);
      setData(response.data);
    } catch (err) {
      console.error("Failed to fetch dashboard data", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading Dashboard...</div>;
  if (!data) return <div style={{ padding: '2rem', textAlign: 'center' }}>Failed to load dashboard data.</div>;

  const { metrics, distribution, value_gain_table, appreciation_projection, liquidation_index, off_plan_stages, yield_analysis } = data;

  // Prepare data for distribution charts
  const typeChartData = distribution.by_type.map(item => ({ name: item.type, value: parseFloat(item.value.toString()) }));
  const countryChartData = distribution.by_country.map(item => ({ name: item.country, value: parseFloat(item.value.toString()) }));

  // Prepare data for Projection Chart
  const projectionChartData = appreciation_projection.years.map((year, index) => {
    const entry: any = { year: year.toString() };
    Object.keys(appreciation_projection.properties).forEach(id => {
      entry[appreciation_projection.properties[id].name] = appreciation_projection.properties[id].values[index];
    });
    entry["Portfolio Total"] = appreciation_projection.portfolio_total[index];
    return entry;
  });

  return (
    <div className="re-dashboard-container" style={{ padding: '1rem' }}>
      <style>{`
        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }
        .metric-card {
          padding: 1.25rem;
          background: #f1f5f9;
          border-radius: 10px;
          border: 1px solid #e2e8f0;
        }
        .metric-label {
          font-size: 0.75rem;
          color: #64748b;
          font-weight: 600;
          text-transform: uppercase;
          margin-bottom: 0.5rem;
        }
        .metric-value {
          font-size: 1.25rem;
          font-weight: 700;
          color: #0f172a;
        }
        .dashboard-table-container {
          overflow-x: auto;
          margin-top: 1rem;
          border-radius: 8px;
          border: 1px solid #e2e8f0;
        }
        .dashboard-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.875rem;
        }
        .dashboard-table th, .dashboard-table td {
          padding: 0.75rem;
          text-align: left;
          border-bottom: 1px solid #e2e8f0;
          white-space: nowrap;
        }
        .dashboard-table th {
          background: #f8fafc;
          font-weight: 600;
          color: #475569;
          position: sticky;
          top: 0;
          z-index: 5;
        }
        .sticky-col {
          position: sticky;
          left: 0;
          background: white;
          z-index: 10;
          min-width: 200px;
          box-shadow: 2px 0 5px -2px rgba(0,0,0,0.1);
        }
        th.sticky-col {
          background: #f8fafc !important;
          z-index: 20;
        }
        .chart-container {
          height: 400px;
          width: 100%;
          margin-top: 1.5rem;
          padding: 0.5rem;
        }
        .status-badge {
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-size: 0.75rem;
          font-weight: 600;
        }
        .status-HELD { background: #dcfce7; color: #166534; }
        .status-OFF_PLAN { background: #fef9c3; color: #854d0e; }
        .status-SOLD { background: #fee2e2; color: #991b1b; }
      `}</style>

      {/* Section 1: Metrics & Distribution */}
      <DashboardSection title="Portfolio Overview & Capital Distribution" id="overview">
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-label">Active Properties</div>
            <div className="metric-value">{metrics.property_count_active}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Market Value</div>
            <div className="metric-value">{formatCurrency(metrics.portfolio_market_value)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Invested Capital</div>
            <div className="metric-value">{formatCurrency(metrics.total_invested_capital)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Unrealized Gains</div>
            <div className="metric-value" style={{ color: '#10b981' }}>{formatCurrency(metrics.unrealized_gains)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Realized Gains</div>
            <div className="metric-value" style={{ color: '#059669' }}>{formatCurrency(metrics.realized_gains)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Annual Rent (Gross)</div>
            <div className="metric-value">{formatCurrency(metrics.total_annual_rent)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Total NOI</div>
            <div className="metric-value">{formatCurrency(metrics.total_noi)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Debt Service</div>
            <div className="metric-value">{formatCurrency(metrics.total_annual_debt_service)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Net Cash Flow (Y1)</div>
            <div className="metric-value" style={{ color: metrics.net_cash_flow_y1 >= 0 ? '#10b981' : '#ef4444' }}>
              {formatCurrency(metrics.net_cash_flow_y1)}
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Gross Yield</div>
            <div className="metric-value">{formatPercent(metrics.portfolio_gross_yield)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Net Yield</div>
            <div className="metric-value">{formatPercent(metrics.portfolio_net_yield)}</div>
          </div>
          <div className="metric-card" style={{ background: '#e0f2fe' }}>
            <div className="metric-label">Portfolio ROI</div>
            <div className="metric-value" style={{ color: '#0369a1' }}>{formatPercent(metrics.portfolio_roi)}</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginTop: '2rem' }}>
          <div>
            <h4 style={{ fontSize: '1rem', marginBottom: '1rem' }}>Capital Distribution by Type</h4>
            <div className="dashboard-table-container">
              <table className="dashboard-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Value</th>
                    <th>% of Portfolio</th>
                  </tr>
                </thead>
                <tbody>
                  {distribution.by_type.map(item => (
                    <tr key={item.type}>
                      <td>{item.type}</td>
                      <td>{formatCurrency(item.value)}</td>
                      <td>{formatPercent(item.percentage)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="chart-container" style={{ height: '450px' }}>
              <ResponsiveContainer>
                <PieChart margin={{ top: 40, right: 60, left: 60, bottom: 40 }}>
                  <Pie 
                    data={typeChartData} 
                    dataKey="value" 
                    nameKey="name" 
                    cx="50%" 
                    cy="50%" 
                    outerRadius={120} 
                    label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    labelLine={true}
                    paddingAngle={2}
                  >
                    {typeChartData.map((_, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(value: any) => formatCurrency(value)} />
                  <Legend verticalAlign="bottom" height={40} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div>
            <h4 style={{ fontSize: '1rem', marginBottom: '1rem' }}>Capital Distribution by Country</h4>
            <div className="dashboard-table-container">
              <table className="dashboard-table">
                <thead>
                  <tr>
                    <th>Country</th>
                    <th>Value</th>
                    <th>% of Portfolio</th>
                  </tr>
                </thead>
                <tbody>
                  {distribution.by_country.map(item => (
                    <tr key={item.country}>
                      <td>{item.country}</td>
                      <td>{formatCurrency(item.value)}</td>
                      <td>{formatPercent(item.percentage)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="chart-container" style={{ height: '450px' }}>
              <ResponsiveContainer>
                <PieChart margin={{ top: 40, right: 60, left: 60, bottom: 40 }}>
                  <Pie 
                    data={countryChartData} 
                    dataKey="value" 
                    nameKey="name" 
                    cx="50%" 
                    cy="50%" 
                    outerRadius={120} 
                    label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    labelLine={true}
                    paddingAngle={2}
                  >
                    {countryChartData.map((_, index) => <Cell key={`cell-${index}`} fill={COLORS[(index + 2) % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(value: any) => formatCurrency(value)} />
                  <Legend verticalAlign="bottom" height={40} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </DashboardSection>

      {/* Section 2: Value & Gain by Property */}
      <DashboardSection title="Value & Gain Analysis By Property" id="value_gain">
        <div className="dashboard-table-container">
          <table className="dashboard-table">
            <thead>
              <tr>
                <th className="sticky-col">Property Name</th>
                <th>Status</th>
                <th>Cost Basis</th>
                <th>Market Value</th>
                <th>Unrealized Gain</th>
                <th>Realized Gain</th>
              </tr>
            </thead>
            <tbody>
              {value_gain_table.map(row => (
                <tr key={row.id}>
                  <td className="sticky-col" style={{ fontWeight: 600 }}>{row.name}</td>
                  <td><span className={`status-badge status-${row.status}`}>{row.status}</span></td>
                  <td>{formatCurrency(row.cost_basis)}</td>
                  <td>{row.current_market_value !== null ? formatCurrency(row.current_market_value) : "-"}</td>
                  <td>{row.unrealized_gain !== null ? formatCurrency(row.unrealized_gain) : "-"}</td>
                  <td>
                    <span style={{ color: row.realized_gain >= 0 ? '#059669' : '#ef4444', fontWeight: 600 }}>
                      {formatCurrency(row.realized_gain)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="chart-container" style={{ height: '500px' }}>
          <ResponsiveContainer>
            <BarChart data={value_gain_table} layout="vertical" margin={{ top: 20, right: 50, left: 150, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={(v) => formatCurrency(v)} />
              <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value: any) => formatCurrency(value)} />
              <Legend verticalAlign="top" height={36} />
              <Bar dataKey="cost_basis" name="Cost Basis" stackId="a" fill="#94a3b8" />
              <Bar dataKey="unrealized_gain" name="Unrealized Gain" stackId="a" fill="#10b981" />
              <Bar dataKey="realized_gain" name="Realized Gain" stackId="a" fill="#059669" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </DashboardSection>

      {/* Section 3: 10-Year Value Appreciation Projection */}
      <DashboardSection title="10-Year Value Appreciation Projection" id="appreciation">
        <div className="dashboard-table-container">
          <table className="dashboard-table">
            <thead>
              <tr>
                <th className="sticky-col">Property / Year</th>
                {appreciation_projection.years.map(y => <th key={y}>{y}</th>)}
              </tr>
            </thead>
            <tbody>
              {Object.keys(appreciation_projection.properties).map(id => (
                <tr key={id}>
                  <td className="sticky-col" style={{ fontWeight: 600 }}>{appreciation_projection.properties[id].name}</td>
                  {appreciation_projection.properties[id].values.map((v, i) => (
                    <td key={i}>{v !== null ? formatCurrency(v) : "-"}</td>
                  ))}
                </tr>
              ))}
              <tr style={{ fontWeight: 700, background: '#f8fafc' }}>
                <td className="sticky-col">Portfolio Total</td>
                {appreciation_projection.portfolio_total.map((v, i) => (
                  <td key={i}>{formatCurrency(v)}</td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
        <div className="chart-container" style={{ height: '500px' }}>
          <ResponsiveContainer>
            <LineChart data={projectionChartData} margin={{ top: 20, right: 60, left: 40, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" padding={{ left: 30, right: 30 }} />
              <YAxis tickFormatter={(v) => formatCurrency(v)} width={100} />
              <Tooltip formatter={(value: any) => value !== null ? formatCurrency(value) : "-"} />
              <Legend verticalAlign="bottom" height={40} />
              {Object.keys(appreciation_projection.properties).map((id, index) => (
                <Line 
                  key={id} 
                  type="monotone" 
                  dataKey={appreciation_projection.properties[id].name} 
                  stroke={COLORS[index % COLORS.length]} 
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  connectNulls={false}
                />
              ))}
              <Line type="monotone" dataKey="Portfolio Total" stroke="#1e293b" strokeWidth={4} dot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </DashboardSection>

      {/* Section 4: Liquidation Readiness Index */}
      <DashboardSection title="Liquidation Readiness Index" id="liquidation">
        <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2rem' }}>
          <div className="dashboard-table-container">
            <table className="dashboard-table">
              <thead>
                <tr>
                  <th className="sticky-col">Property Name</th>
                  <th>Status</th>
                  <th>Years Held</th>
                  <th>Net Yield</th>
                  <th>Gain %</th>
                  <th>Index (0-100)</th>
                </tr>
              </thead>
              <tbody>
                {liquidation_index.table.map(row => (
                  <tr key={row.id}>
                    <td className="sticky-col" style={{ fontWeight: 600 }}>{row.name}</td>
                    <td><span className={`status-badge status-${row.status}`}>{row.status}</span></td>
                    <td>{row.years_held.toFixed(2)}</td>
                    <td>{formatPercent(row.net_yield)}</td>
                    <td>{formatPercent(row.gain_percentage)}</td>
                    <td style={{ fontWeight: 700 }}>{row.liquidation_index}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <h4 style={{ marginBottom: '1rem' }}>Portfolio Liquidity Gauge</h4>
            <LiquidityGauge 
              value={liquidation_index.portfolio_average} 
              portfolioL={0.5} 
              ageFactor={0.1} 
              age={5} 
              fundName="Portfolio Average"
            />
          </div>
        </div>
      </DashboardSection>

      {/* Section 5: Off-Plan Development Stage */}
      <DashboardSection title="Off-Plan/Primary Development Stage" id="off_plan">
        <div className="dashboard-table-container">
          <table className="dashboard-table">
            <thead>
              <tr>
                <th className="sticky-col">Property Name</th>
                <th>Start Date</th>
                <th>Completion Date</th>
                <th>Time Elapsed %</th>
                <th>Capital Deployed %</th>
                <th>Stage</th>
              </tr>
            </thead>
            <tbody>
              {off_plan_stages.map(row => (
                <tr key={row.id}>
                  <td className="sticky-col" style={{ fontWeight: 600 }}>{row.name}</td>
                  <td>{row.start_date}</td>
                  <td>{row.completion_date}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <div style={{ flex: 1, height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden', minWidth: '60px' }}>
                        <div style={{ width: `${row.time_elapsed_percentage}%`, height: '100%', background: '#3b82f6' }} />
                      </div>
                      <span>{formatPercent(row.time_elapsed_percentage)}</span>
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <div style={{ flex: 1, height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden', minWidth: '60px' }}>
                        <div style={{ width: `${row.capital_deployed_percentage}%`, height: '100%', background: '#10b981' }} />
                      </div>
                      <span>{formatPercent(row.capital_deployed_percentage)}</span>
                    </div>
                  </td>
                  <td style={{ fontWeight: 600 }}>{row.stage}</td>
                </tr>
              ))}
              {off_plan_stages.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>No off-plan properties in this portfolio.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </DashboardSection>

      {/* Section 6: Yield Analysis By Property */}
      <DashboardSection title="Yield Analysis By Property" id="yield">
        <div className="dashboard-table-container">
          <table className="dashboard-table">
            <thead>
              <tr>
                <th className="sticky-col">Property Name</th>
                <th>Annual Rent</th>
                <th>NOI</th>
                <th>Debt Service</th>
                <th>Gross Yield</th>
                <th>Net Yield</th>
              </tr>
            </thead>
            <tbody>
              {yield_analysis.map(row => (
                <tr key={row.id} style={row.id === "total" ? { fontWeight: 700, background: '#f8fafc' } : {}}>
                  <td className="sticky-col" style={{ fontWeight: 600 }}>{row.name}</td>
                  <td>{formatCurrency(row.annual_rent)}</td>
                  <td>{formatCurrency(row.noi)}</td>
                  <td>{formatCurrency(row.annual_debt_service)}</td>
                  <td>{formatPercent(row.gross_yield)}</td>
                  <td>{formatPercent(row.net_yield)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="chart-container" style={{ height: '450px' }}>
          <ResponsiveContainer>
            <BarChart data={yield_analysis.filter(r => r.id !== "total")} margin={{ top: 20, right: 30, left: 40, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" angle={-45} textAnchor="end" interval={0} height={80} />
              <YAxis tickFormatter={(v) => formatCurrency(v)} width={100} />
              <Tooltip formatter={(value: any) => formatCurrency(value)} />
              <Legend verticalAlign="top" height={36} />
              <Bar dataKey="annual_rent" name="Annual Rent" fill="#3b82f6" />
              <Bar dataKey="noi" name="NOI" fill="#10b981" />
              <Bar dataKey="annual_debt_service" name="Debt Service" fill="#f43f5e" />
            </BarChart>
          </ResponsiveContainer>
        </div>

      </DashboardSection>
    </div>
  );
};

export default RealEstateDashboardTab;
