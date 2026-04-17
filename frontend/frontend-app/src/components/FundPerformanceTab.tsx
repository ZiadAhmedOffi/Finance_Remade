import React, { useState, useEffect } from "react";
import { api } from "../api/api";
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
  ReferenceLine,
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  } from "recharts";
  import { calculateLiquidityIndex } from "../utils/liquidityUtils";
  import LiquidityGauge from "./LiquidityGauge";

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
  current_deals_metrics: {
    total_invested: number;
    gross_exit_value: number;
    moic: number;
    irr: number;
    total_deals: number;
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
 * 3. Advanced data visualizations (Waterfall, Capital Allocation Strategy).
 * 
 * @param {string} fundId - The unique identifier of the fund.
 */
const FundPerformanceTab: React.FC<FundPerformanceTabProps> = ({ fundId }) => {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Toggle states for sections
  const [sections, setSections] = useState({
    metrics: true,
    annualPerformance: false,
    capitalAllocation: false,
    intrinsicValue: false,
  });

  const toggleSection = (section: keyof typeof sections) => {
    setSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

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

  const { dashboard, current_deals_metrics } = data;

  // Formatting Utilities
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);

  const formatCurrencyLong = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);
  
  const formatPercent = (val: number) => (val * 100).toFixed(2) + "%";
  const formatMultiple = (val: number) => val.toFixed(2) + "x";

  /* --- Liquidity Index Calculations --- */
  const liData = calculateLiquidityIndex(
    (data as any).current_deals || [],
    data.admin_fee.inception_year || new Date().getFullYear()
  );

  const waterfallData = dashboard.performance_table.map((entry, index) => {
    const prevEntry = index > 0 ? dashboard.performance_table[index - 1] : null;
    const startValue = prevEntry ? prevEntry.total_portfolio_value_with_prognosis : 0;
    return {
      ...entry,
      startValue: startValue
    };
  });

  const currentYear = dashboard.performance_table[0]?.current_year || new Date().getFullYear();
  
  return (
    <section className="performance-tab">
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

      {/* SECTION 1: METRICS */}
      <div className="section-container" style={{marginBottom: '2rem'}}>
        <button 
          onClick={() => toggleSection('metrics')}
          style={{
            width: '100%', 
            padding: '1.25rem 1.5rem', 
            background: 'linear-gradient(to right, #f8fafc, #f1f5f9)', 
            border: '1px solid #e2e8f0', 
            borderRadius: '0.75rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer',
            fontWeight: '700',
            fontSize: '1.1rem',
            color: '#1e293b',
            marginBottom: '1rem',
            transition: 'all 0.2s ease',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
          }}
          className="section-header-btn"
        >
          <span style={{display: 'flex', alignItems: 'center', gap: '0.75rem'}}>
            <span style={{
              background: '#2563eb', 
              color: 'white', 
              width: '24px', 
              height: '24px', 
              borderRadius: '6px', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              fontSize: '0.8rem'
            }}>1</span>
            FUND METRICS (PAST & FUTURE)
          </span>
          <span style={{ 
            transition: 'transform 0.3s ease', 
            transform: sections.metrics ? 'rotate(180deg)' : 'rotate(0deg)',
            fontSize: '1.2rem'
          }}>▼</span>
        </button>

        {sections.metrics && (
          <div className="section-content animate-fade-in">
            {/* Current Deals Metrics Card (Past) */}
            <div className="content-card" style={{background: '#f8fafc', borderColor: '#64748b', marginBottom: '2rem'}}>
              <h3 style={{textAlign: 'center', color: '#475569', marginBottom: '2rem', textTransform: 'uppercase', letterSpacing: '0.05em'}}>Performance of Deals Already Made (Past)</h3>
              <div style={{display: 'flex', flexDirection: 'column', gap: '2.5rem', textAlign: 'center'}}>
                <div style={{display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: '2rem'}}>
                  <div className="summary-item">
                    <label style={{color: '#64748b', fontSize: '1rem', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.5rem', display: 'block'}}>Total Amount Invested</label>
                    <div className="summary-value" style={{fontSize: '2.5rem', fontWeight: '900', color: '#1e293b'}}>
                      {formatCurrencyLong(current_deals_metrics.total_invested)}
                    </div>
                  </div>
                  <div className="summary-item">
                    <label style={{color: '#64748b', fontSize: '1rem', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.5rem', display: 'block'}}>Gross Exit Value Achieved</label>
                    <div className="summary-value" style={{fontSize: '2.5rem', fontWeight: '900', color: '#1e293b'}}>
                      {formatCurrencyLong(current_deals_metrics.gross_exit_value)}
                    </div>
                  </div>
                </div>

                <div className="divider-h" style={{margin: '0 auto', width: '80%', opacity: '0.2', borderTop: '1px solid #64748b'}} />

                <div style={{display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: '2rem'}}>
                  <div className="summary-item">
                    <label style={{color: '#64748b', fontSize: '0.9rem', fontWeight: '600', textTransform: 'uppercase', marginBottom: '0.3rem', display: 'block'}}>MOIC Achieved</label>
                    <div className="summary-value" style={{fontSize: '1.6rem', fontWeight: '700', color: '#1e293b'}}>
                      {formatMultiple(current_deals_metrics.moic)}
                    </div>
                  </div>
                  <div className="summary-item">
                    <label style={{color: '#64748b', fontSize: '0.9rem', fontWeight: '600', textTransform: 'uppercase', marginBottom: '0.3rem', display: 'block'}}>IRR (Realized/Current)</label>
                    <div className="summary-value" style={{fontSize: '1.6rem', fontWeight: '700', color: '#1e293b'}}>
                      {formatPercent(current_deals_metrics.irr)}
                    </div>
                  </div>
                  <div className="summary-item">
                    <label style={{color: '#64748b', fontSize: '0.9rem', fontWeight: '600', textTransform: 'uppercase', marginBottom: '0.3rem', display: 'block'}}>Number of Deals Made</label>
                    <div className="summary-value" style={{fontSize: '1.6rem', fontWeight: '700', color: '#1e293b'}}>
                      {current_deals_metrics.total_deals}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Deal Prognosis Metrics Card (Future) */}
            <div className="content-card" style={{background: '#f0f7ff', borderColor: '#007bff', marginBottom: '2rem'}}>
              <h3 style={{textAlign: 'center', color: '#0056b3', marginBottom: '2rem', textTransform: 'uppercase', letterSpacing: '0.05em'}}>Prognosis for Future Deals (Future)</h3>
              <div style={{display: 'flex', flexDirection: 'column', gap: '2.5rem', textAlign: 'center'}}>
                <div style={{display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: '2rem'}}>
                  <div className="summary-item">
                    <label style={{color: '#0056b3', fontSize: '1rem', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.5rem', display: 'block'}}>Total Amount to be Invested</label>
                    <div className="summary-value" style={{fontSize: '2.5rem', fontWeight: '900', color: '#007bff'}}>
                      {formatCurrencyLong(dashboard.total_invested)}
                    </div>
                  </div>
                  <div className="summary-item">
                    <label style={{color: '#0056b3', fontSize: '1rem', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.5rem', display: 'block'}}>Expected Gross Exit Value</label>
                    <div className="summary-value" style={{fontSize: '2.5rem', fontWeight: '900', color: '#007bff'}}>
                      {formatCurrencyLong(dashboard.gross_exit_value)}
                    </div>
                  </div>
                </div>

                <div className="divider-h" style={{margin: '0 auto', width: '80%', opacity: '0.3', borderTop: '1px solid #007bff'}} />

                <div style={{display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: '2rem'}}>
                  <div className="summary-item">
                    <label style={{color: '#0056b3', fontSize: '0.9rem', fontWeight: '600', textTransform: 'uppercase', marginBottom: '0.3rem', display: 'block'}}>Target MOIC</label>
                    <div className="summary-value" style={{fontSize: '1.6rem', fontWeight: '700', color: '#007bff'}}>
                      {formatMultiple(dashboard.moic)}
                    </div>
                  </div>
                  <div className="summary-item">
                    <label style={{color: '#0056b3', fontSize: '0.9rem', fontWeight: '600', textTransform: 'uppercase', marginBottom: '0.3rem', display: 'block'}}>Expected IRR</label>
                    <div className="summary-value" style={{fontSize: '1.6rem', fontWeight: '700', color: '#007bff'}}>
                      {formatPercent(dashboard.irr)}
                    </div>
                  </div>
                  <div className="summary-item">
                    <label style={{color: '#0056b3', fontSize: '0.9rem', fontWeight: '600', textTransform: 'uppercase', marginBottom: '0.3rem', display: 'block'}}>Total Deals to be Made</label>
                    <div className="summary-value" style={{fontSize: '1.6rem', fontWeight: '700', color: '#007bff'}}>
                      {dashboard.total_deals}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* SECTION 2: ANNUAL PORTFOLIO PERFORMANCE */}
      <div className="section-container" style={{marginBottom: '2rem'}}>
        <button 
          onClick={() => toggleSection('annualPerformance')}
          style={{
            width: '100%', 
            padding: '1.25rem 1.5rem', 
            background: 'linear-gradient(to right, #f8fafc, #f1f5f9)', 
            border: '1px solid #e2e8f0', 
            borderRadius: '0.75rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer',
            fontWeight: '700',
            fontSize: '1.1rem',
            color: '#1e293b',
            marginBottom: '1rem',
            transition: 'all 0.2s ease',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
          }}
          className="section-header-btn"
        >
          <span style={{display: 'flex', alignItems: 'center', gap: '0.75rem'}}>
            <span style={{
              background: '#2563eb', 
              color: 'white', 
              width: '24px', 
              height: '24px', 
              borderRadius: '6px', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              fontSize: '0.8rem'
            }}>2</span>
            ANNUAL PORTFOLIO PERFORMANCE
          </span>
          <span style={{ 
            transition: 'transform 0.3s ease', 
            transform: sections.annualPerformance ? 'rotate(180deg)' : 'rotate(0deg)',
            fontSize: '1.2rem'
          }}>▼</span>
        </button>

        {sections.annualPerformance && (
          <div className="section-content animate-fade-in">
            {/* Annual Performance Table */}
            <div className="content-card" style={{marginBottom: '2rem'}}>
              <h3>Annual Portfolio Performance Data</h3>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Year</th>
                      <th>Cap Injection (Current)</th>
                      <th>Cap Appr (Current)</th>
                      <th>Cap Injection (Prognosis)</th>
                      <th>Cap Appr (Prognosis)</th>
                      <th>Total Portfolio Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.performance_table.map((row) => (
                      <tr key={row.year} style={row.year === currentYear ? {backgroundColor: '#f1f5f9', fontWeight: 'bold'} : {}}>
                        <td>{row.year} {row.year === currentYear && "(Current)"}</td>
                        <td>{formatCurrencyLong(row.injection_current)}</td>
                        <td>{formatCurrencyLong(row.appreciation_current)}</td>
                        <td>{formatCurrencyLong(row.injection_prognosis)}</td>
                        <td>{formatCurrencyLong(row.appreciation_prognosis)}</td>
                        <td>{formatCurrencyLong(row.total_portfolio_value_with_prognosis)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="chart-container wide" style={{marginBottom: '2rem'}}>
              <h3>Annual Portfolio Value Expansion</h3>
              <ResponsiveContainer width="100%" height={400}>
                <ComposedChart data={waterfallData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="year" />
                  <YAxis tickFormatter={formatCurrency} />
                  <Tooltip formatter={(value: any) => formatCurrencyLong(Number(value))} />
                  <Legend />
                  <ReferenceLine x={currentYear} stroke="#e74c3c" strokeDasharray="3 3" label={{ position: 'top', value: 'Current Year', fill: '#e74c3c', fontSize: 12 }} />
                  
                  <Bar dataKey="startValue" stackId="a" fill="transparent" legendType="none" />
                  
                  {/* Injections grouped */}
                  <Bar dataKey="injection_current" stackId="a" fill="#3498db" name="Capital Injection (Current)" />
                  <Bar dataKey="injection_prognosis" stackId="a" fill="url(#hash-injection)" name="Capital Injection (Prognosis)" />
                  
                  {/* Appreciations grouped */}
                  <Bar dataKey="appreciation_current" stackId="a" fill="#2ecc71" name="Capital Appreciation (Current)" />
                  <Bar dataKey="appreciation_prognosis" stackId="a" fill="url(#hash-appreciation)" name="Capital Appreciation (Prognosis)" />
                  
                  <Line type="stepAfter" dataKey="total_portfolio_value_with_prognosis" stroke="#7f8c8d" strokeWidth={2} dot={false} name="Value Step" legendType="none" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>

      {/* SECTION 3: STRATEGY & APPRECIATION */}
      <div className="section-container" style={{marginBottom: '2rem'}}>
        <button 
          onClick={() => toggleSection('capitalAllocation')}
          style={{
            width: '100%', 
            padding: '1.25rem 1.5rem', 
            background: 'linear-gradient(to right, #f8fafc, #f1f5f9)', 
            border: '1px solid #e2e8f0', 
            borderRadius: '0.75rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer',
            fontWeight: '700',
            fontSize: '1.1rem',
            color: '#1e293b',
            marginBottom: '1rem',
            transition: 'all 0.2s ease',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
          }}
          className="section-header-btn"
        >
          <span style={{display: 'flex', alignItems: 'center', gap: '0.75rem'}}>
            <span style={{
              background: '#2563eb', 
              color: 'white', 
              width: '24px', 
              height: '24px', 
              borderRadius: '6px', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              fontSize: '0.8rem'
            }}>3</span>
            CAPITAL ALLOCATION STRATEGY & APPRECIATION
          </span>
          <span style={{ 
            transition: 'transform 0.3s ease', 
            transform: sections.capitalAllocation ? 'rotate(180deg)' : 'rotate(0deg)',
            fontSize: '1.2rem'
          }}>▼</span>
        </button>

        {sections.capitalAllocation && (
          <div className="section-content animate-fade-in">
            <div className="charts-grid">
              <div className="chart-container">
                <h3>Capital Allocation Strategy (Deals)</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={dashboard.performance_table}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="year" />
                    <YAxis yAxisId="left" label={{ value: 'Deals', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <ReferenceLine x={currentYear} stroke="#e74c3c" strokeDasharray="3 3" />
                    
                    <Bar yAxisId="left" dataKey="deals_count_current" fill="#9b59b6" name="Deals (Current)" />
                    <Bar yAxisId="left" dataKey="deals_count_prognosis" fill="url(#hash-deals)" name="Deals (Prognosis)" stroke="#9b59b6" strokeDasharray="5 5" />
                    
                    <Line yAxisId="left" type="monotone" dataKey="cumulative_deals_count_current" stroke="#f1c40f" name="Cum. Deals (Current)" strokeWidth={2} dot={false} />
                    <Line yAxisId="left" type="monotone" dataKey="cumulative_deals_count_prognosis" stroke="#f1c40f" name="Cum. Deals (Total)" strokeWidth={3} strokeDasharray="5 5" dot={{ r: 3 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              <div className="chart-container">
                <h3>Capital Allocation Strategy (Amount)</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={dashboard.performance_table}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="year" />
                    <YAxis yAxisId="left" tickFormatter={formatCurrency} />
                    <Tooltip formatter={(v: any) => formatCurrencyLong(Number(v))} />
                    <Legend />
                    <ReferenceLine x={currentYear} stroke="#e74c3c" strokeDasharray="3 3" />
                    
                    <Bar yAxisId="left" dataKey="injection_current" fill="#e67e22" name="Amount (Current)" />
                    <Bar yAxisId="left" dataKey="injection_prognosis" fill="url(#hash-amount)" name="Amount (Prognosis)" stroke="#e67e22" strokeDasharray="5 5" />
                    
                    <Line yAxisId="left" type="monotone" dataKey="cumulative_injection_no_prognosis" stroke="#e74c3c" name="Cum. Invested (Current)" strokeWidth={2} dot={false} />
                    <Line yAxisId="left" type="monotone" dataKey="cumulative_injection_with_prognosis" stroke="#e74c3c" name="Cum. Invested (Total)" strokeWidth={3} strokeDasharray="5 5" dot={{ r: 3 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              <div className="chart-container wide">
                <h3>Capital Appreciation: Scenario Comparison</h3>
                <ResponsiveContainer width="100%" height={400}>
                  <ComposedChart data={dashboard.performance_table}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="year" />
                    <YAxis tickFormatter={formatCurrency} />
                    <Tooltip formatter={(v: any) => formatCurrencyLong(Number(v))} />
                    <Legend />
                    <ReferenceLine x={currentYear - 1} stroke="#e74c3c" strokeDasharray="3 3" label={{ position: 'top', value: 'Last Closed Year', fill: '#e74c3c', fontSize: 12 }} />
                    
                    {/* No Future Deals Scenario (Solid) */}
                    <Line type="monotone" dataKey="cumulative_injection_no_prognosis" stroke="#34495e" name="Invested (No Future Deals)" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="total_portfolio_value_no_prognosis" stroke="#27ae60" name="Portfolio Value (No Future Deals)" strokeWidth={2} dot={false} />
                    
                    {/* With Future Deals Scenario (Dashed) */}
                    <Line type="monotone" dataKey="cumulative_injection_with_prognosis" stroke="#34495e" name="Invested (With Prognosis)" strokeWidth={3} strokeDasharray="5 5" dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="total_portfolio_value_with_prognosis" stroke="#27ae60" name="Portfolio Value (With Prognosis)" strokeWidth={3} strokeDasharray="5 5" dot={{ r: 3 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}
        {/* Intrinsic Value and Liquidity Index Section */}
        <button 
          onClick={() => toggleSection('intrinsicValue')}
          style={{
            width: '100%', 
            padding: '1.25rem 1.5rem', 
            background: 'linear-gradient(to right, #f8fafc, #f1f5f9)', 
            border: '1px solid #e2e8f0', 
            borderRadius: '0.75rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer',
            fontWeight: '700',
            fontSize: '1.1rem',
            color: '#1e293b',
            marginBottom: '1rem',
            transition: 'all 0.2s ease',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
          }}
          className="section-header-btn"
        >
          <span style={{display: 'flex', alignItems: 'center', gap: '0.75rem'}}>
            <span style={{
              background: '#2563eb', 
              color: 'white', 
              width: '24px', 
              height: '24px', 
              borderRadius: '6px', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              fontSize: '0.8rem'
            }}>4</span>
            INTRINSIC VALUE AND LIQUIDITY INDEX
          </span>
          <span style={{ 
            transition: 'transform 0.3s ease', 
            transform: sections.intrinsicValue ? 'rotate(180deg)' : 'rotate(0deg)',
            fontSize: '1.2rem'
          }}>▼</span>
        </button>

        {sections.intrinsicValue && (
          <div className="section-content animate-fade-in">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '2rem', marginBottom: '2rem' }}>
              
              {/* Intrinsic Value Radar Chart */}
              <div className="content-card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}>
                <h3 style={{ marginBottom: '2rem', textAlign: 'center', border: 'none' }}>Intrinsic Value</h3>
                <div style={{ width: '100%', height: 450 }}>
                  <ResponsiveContainer>
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={(() => {
                      const currentDeals = (data as any).current_deals || [];
                      
                      // Group by company name to handle multiple deals per company
                      const companyMap = new Map();
                      
                      currentDeals.forEach((d: any) => {
                        if (!companyMap.has(d.company_name)) {
                          const entryVal = parseFloat(d.entry_valuation);
                          const currentVal = parseFloat(d.latest_valuation);
                          const exitMultiple = parseFloat(d.expected_exit_multiple || 5.0);
                          const ownership = parseFloat(d.ownership_after_dilution || 0);
                          
                          // Target = Entry Valuation * Multiple
                          const targetVal = entryVal * exitMultiple;
                          
                          companyMap.set(d.company_name, {
                            subject: d.company_name,
                            entry: targetVal > 0 ? (entryVal / targetVal) * 100 : 0,
                            current: targetVal > 0 ? (currentVal / targetVal) * 100 : 0,
                            expected: 100,
                            full_name: d.company_name,
                            raw_entry: entryVal,
                            raw_current: currentVal,
                            raw_expected: targetVal,
                            ownership: ownership
                          });
                        }
                      });
                      
                      return Array.from(companyMap.values());
                    })()}>
                      <PolarGrid />
                      <PolarAngleAxis 
                        dataKey="subject" 
                        tick={(() => {
                          const currentDeals = (data as any).current_deals || [];
                          const uniqueCompanies = new Set(currentDeals.map((d: any) => d.company_name));
                          // Hide labels if there are too many companies to avoid clutter
                          return uniqueCompanies.size > 15 ? false : { fill: '#64748b', fontSize: '0.8rem' };
                        })()}
                      />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                      <Radar
                        name="Entry Valuation"
                        dataKey="entry"
                        stroke="#3498db"
                        fill="#3498db"
                        fillOpacity={0.4}
                      />
                      <Radar
                        name="Current Valuation"
                        dataKey="current"
                        stroke="#2ecc71"
                        fill="#2ecc71"
                        fillOpacity={0.5}
                      />
                      <Radar
                        name="Expected Final Valuation"
                        dataKey="expected"
                        stroke="#10b981"
                        fill="transparent"
                        strokeDasharray="5 5"
                      />
                      <Tooltip content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const d = payload[0].payload;
                          return (
                            <div className="custom-tooltip" style={{ 
                              backgroundColor: '#fff', 
                              padding: '12px', 
                              border: '1px solid #e2e8f0',
                              borderRadius: '8px',
                              boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                              fontSize: '0.85rem',
                              lineHeight: '1.5'
                            }}>
                              <p style={{ fontWeight: 'bold', marginBottom: '8px', color: '#1e293b', borderBottom: '1px solid #f1f5f9', paddingBottom: '4px' }}>{d.full_name}</p>
                              <p style={{ margin: '2px 0' }}><span style={{ color: '#64748b' }}>Ownership:</span> <strong>{d.ownership.toFixed(2)}%</strong></p>
                              <p style={{ margin: '2px 0' }}><span style={{ color: '#3498db' }}>Entry Val:</span> <strong>{formatCurrencyLong(d.raw_entry)}</strong> ({d.entry.toFixed(1)}%)</p>
                              <p style={{ margin: '2px 0' }}><span style={{ color: '#2ecc71' }}>Current Val:</span> <strong>{formatCurrencyLong(d.raw_current)}</strong> ({d.current.toFixed(1)}%)</p>
                              <p style={{ margin: '2px 0' }}><span style={{ color: '#10b981' }}>Expected Exit:</span> <strong>{formatCurrencyLong(d.raw_expected)}</strong> (100%)</p>
                              <p style={{ margin: '8px 0 0', fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic' }}>Scenario: Base Case</p>
                            </div>
                          );
                        }
                        return null;
                      }} />
                      <Legend />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Liquidity Index Gauge */}
              <div className="content-card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div style={{ textAlign: 'center' }}>
                  <h3 style={{ marginBottom: '0.5rem', border: 'none' }}>Liquidity Index</h3>
                  <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '2.5rem' }}>Measures the portfolio's path to realization</p>
                </div>
                
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <LiquidityGauge 
                    value={liData.finalLI} 
                    portfolioL={liData.portfolioL} 
                    ageFactor={liData.ageFactor} 
                    age={liData.age} 
                  />
                </div>

                <div style={{ marginTop: '2rem', padding: '1.25rem', backgroundColor: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                  <h4 style={{ fontSize: '0.9rem', color: '#1e293b', marginBottom: '0.75rem', border: 'none' }}>Index Interpretation</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '4px' }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#10b981' }}></div> 0-20%: Highly Liquid
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#34d399' }}></div> 20-40%: Good
                      </div>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '4px' }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#fbbf24' }}></div> 40-60%: Moderate
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ef4444' }}></div> 60%+: Illiquid
                      </div>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        )}
      </div>
    </section>
  );
};

export default FundPerformanceTab;
