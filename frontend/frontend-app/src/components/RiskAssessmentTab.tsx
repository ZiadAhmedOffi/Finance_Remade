
import React, { useState, useEffect } from 'react';
import { 
  ScatterChart, 
  Scatter, 
  XAxis, 
  YAxis, 
  ZAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ReferenceArea,
  ReferenceLine,
  Label,
  Cell,
  LabelList,
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Legend
} from 'recharts';
import { fundsApi } from '../api/api';
import { calculateLiquidityIndex } from "../utils/liquidityUtils";
import LiquidityGauge from "./LiquidityGauge";
import FundPerformanceRadarChart from "./FundPerformanceRadarChart";

interface RiskAssessmentTabProps {
  fundId: string;
  canEdit: boolean;
}

interface RiskAssessment {
  id?: string;
  company_name: string;
  execution_capacity_score: number;
  market_validation_score: number;
  status: string;
  company_type?: string;
}

const STATUS_OPTIONS = [
  { value: 'MONETIZE', label: 'Monetize', color: '#007bff' },
  { value: 'ON_TRACK', label: 'On-Track', color: '#28a745' },
  { value: 'RESTRUCTURE', label: 'Restructure', color: '#fd7e14' },
  { value: 'SHUTDOWN', label: 'Shutdown', color: '#dc3545' },
];

const getStatusColor = (status: string) => {
  const option = STATUS_OPTIONS.find(o => o.value === status);
  return option ? option.color : '#6c757d';
};

// Custom Label component for company names
const CustomLabel = (props: any) => {
  const { x, y, value } = props;
  return (
    <text
      x={x}
      y={y}
      dy={-15}
      textAnchor="middle"
      fill="#000"
      style={{ 
        fontSize: '11px', 
        fontWeight: '700',
        paintOrder: 'stroke',
        stroke: '#ffffff',
        strokeWidth: '4px',
      }}
    >
      {value}
    </text>
  );
};

// Custom Arrow Icons based on Company Type
const CustomArrow = (props: any) => {
  const { cx, cy, fill, company_type } = props;
  
  let path = "";
  if (company_type === 'BMF-') {
    path = "M10,0 L0,5 L10,10 L10,0 Z";
  } else if (['BMF', 'BMF+', 'Scaling-'].includes(company_type)) {
    path = "M0,0 L10,5 L0,10 L0,0 Z";
  } else if (company_type === 'PMF-') {
    path = "M0,0 L10,0 L5,10 L0,0 Z";
  } else if (['PMF', 'PMF+'].includes(company_type)) {
    path = "M0,10 L10,10 L5,0 L0,10 Z";
  } else {
    return <circle cx={cx} cy={cy} r={6} fill={fill} stroke="white" strokeWidth={1} />;
  }

  return (
    <g transform={`translate(${cx - 8}, ${cy - 8})`}>
      <path d={path} fill={fill} stroke="white" strokeWidth={1} transform="scale(1.6)" />
    </g>
  );
};

const RiskAssessmentTab: React.FC<RiskAssessmentTabProps> = ({ fundId, canEdit }) => {
  const [assessments, setAssessments] = useState<RiskAssessment[]>([]);
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [showTable, setShowTable] = useState(false);
  const [showIntrinsic, setShowIntrinsic] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const dealsRes = await fundsApi.getCurrentDeals(fundId);
        const deals = dealsRes.data;
        
        const assessmentsRes = await fundsApi.getRiskAssessments(fundId);
        const existingAssessments = assessmentsRes.data;

        const perfRes = await fundsApi.getFundPerformance(fundId);
        setPerformanceData(perfRes.data);
        
        const companyMap: Record<string, string> = {};
        deals.forEach((d: any) => {
          companyMap[d.company_name] = d.company_type;
        });

        const distinctCompanies = Object.keys(companyMap);
        
        const merged: RiskAssessment[] = distinctCompanies.map(name => {
          const existing = existingAssessments.find((a: any) => a.company_name === name);
          return {
            company_name: name,
            execution_capacity_score: existing ? parseFloat(existing.execution_capacity_score) : 5.0,
            market_validation_score: existing ? parseFloat(existing.market_validation_score) : 5.0,
            status: existing ? existing.status : 'ON_TRACK',
            company_type: companyMap[name]
          };
        });

        setAssessments(merged);
      } catch (err) {
        console.error(err);
        setError("Failed to load stability and risk data.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [fundId]);

  const handleScoreChange = (index: number, field: keyof RiskAssessment, value: string) => {
    const numValue = parseFloat(value);
    if (isNaN(numValue) || numValue < 0 || numValue > 10) return;
    
    const newAssessments = [...assessments];
    newAssessments[index] = { ...newAssessments[index], [field]: numValue };
    setAssessments(newAssessments);
  };

  const handleStatusChange = (index: number, value: string) => {
    const newAssessments = [...assessments];
    newAssessments[index] = { ...newAssessments[index], status: value };
    setAssessments(newAssessments);
  };

  const handleSave = async () => {
    try {
      setSaveSuccess(false);
      await fundsApi.saveRiskAssessments(fundId, assessments);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      setError("Failed to save changes.");
    }
  };

  const formatCurrencyLong = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);

  if (loading) return <div className="loading">Loading Stability and Risk...</div>;

  const liData = performanceData ? calculateLiquidityIndex(
    performanceData.current_deals || [],
    performanceData.admin_fee?.inception_year || new Date().getFullYear()
  ) : null;

  const comparisons = [
    { name: 'Public Equities (S&P 500)', li: 5 },
    { name: 'Gold', li: 2 },
    { name: 'Commodities (ETF)', li: 10 },
    { name: 'Our Fund', li: liData?.finalLI || 0, isCurrent: true },
    { name: 'Private Equity (Avg)', li: 75 },
    { name: 'Real Estate (Direct)', li: 85 },
  ];

  return (
    <div className="risk-assessment-tab">
      {error && <div className="alert alert-error">{error}</div>}
      {saveSuccess && <div className="alert alert-success">Changes saved successfully!</div>}

      <div className="content-card mb-4" style={{ padding: '1.5rem' }}>
        <div 
          onClick={() => setShowTable(!showTable)}
          style={{ 
            cursor: 'pointer', 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            background: 'linear-gradient(to right, #f8fafc, #f1f5f9)',
            padding: '1rem 1.5rem',
            borderRadius: '0.75rem',
            border: '1px solid #e2e8f0',
            transition: 'all 0.2s ease',
            marginBottom: '0.5rem'
          }}
          className="section-header-btn"
        >
          <h3 className="tab-title" style={{ margin: 0, border: 'none' }}>Portfolio Stability and Risk Assessment</h3>
          <span style={{ 
            transition: 'transform 0.3s ease', 
            transform: showTable ? 'rotate(180deg)' : 'rotate(0deg)',
            fontSize: '1.2rem'
          }}>▼</span>
        </div>

        <div style={{ 
          maxHeight: showTable ? '2000px' : '0', 
          overflow: 'hidden', 
          transition: 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
          opacity: showTable ? 1 : 0
        }}>
          <div className="section-content animate-fade-in" style={{ padding: '1rem 0' }}>
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Company Name</th>
                    <th>Execution Capacity Score (0-10)</th>
                    <th>Market Validation Score (0-10)</th>
                    <th>Current Status</th>
                  </tr>
                </thead>
                <tbody>
                  {assessments.map((item, idx) => (
                    <tr key={item.company_name}>
                      <td style={{ fontWeight: '600' }}>{item.company_name}</td>
                      <td>
                        <input 
                          type="number" 
                          className="form-input-sm"
                          value={item.execution_capacity_score}
                          onChange={(e) => handleScoreChange(idx, 'execution_capacity_score', e.target.value)}
                          min="0"
                          max="10"
                          step="0.1"
                          disabled={!canEdit}
                        />
                      </td>
                      <td>
                        <input 
                          type="number" 
                          className="form-input-sm"
                          value={item.market_validation_score}
                          onChange={(e) => handleScoreChange(idx, 'market_validation_score', e.target.value)}
                          min="0"
                          max="10"
                          step="0.1"
                          disabled={!canEdit}
                        />
                      </td>
                      <td>
                        <select 
                          className="form-input-sm"
                          value={item.status}
                          onChange={(e) => handleStatusChange(idx, e.target.value)}
                          disabled={!canEdit}
                          style={{ 
                            backgroundColor: getStatusColor(item.status) + '20', 
                            color: getStatusColor(item.status),
                            borderColor: getStatusColor(item.status),
                            fontWeight: '600'
                          }}
                        >
                          {STATUS_OPTIONS.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {canEdit && (
              <div className="form-actions mt-3">
                <button className="btn btn-primary" onClick={handleSave}>Save Assessment</button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="content-card mb-4" style={{ padding: '2rem' }}>
        <h3 className="tab-title" style={{ marginBottom: '2.5rem' }}>Execution Capacity vs. Market Validation</h3>
        
        <div style={{ width: '100%', height: 600, position: 'relative' }}>
          <ResponsiveContainer>
            <ScatterChart margin={{ top: 40, right: 30, bottom: 60, left: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              
              <ReferenceArea 
                x1={0} x2={2} y1={0} y2={2} 
                fill="#FF6666" 
                fillOpacity={0.6} 
                label={{ value: 'Sunset', position: 'insideTopRight', fill: '#333', fontSize: 14, fontWeight: 'bold', dx: -10, dy: 10 }}
              />
              <ReferenceArea 
                x1={2} x2={8} y1={2} y2={8} 
                fill="#F5DEB3" 
                fillOpacity={0.8} 
                label={{ value: 'High-Growth Potential', position: 'insideTopRight', fill: '#333', fontSize: 14, fontWeight: 'bold', dx: -10, dy: 10 }}
              />
              <ReferenceArea 
                x1={8} x2={10} y1={8} y2={10} 
                fill="#90EE90" 
                fillOpacity={0.6} 
                label={{ value: 'Champions - Exit Track', position: 'insideTopRight', fill: '#333', fontSize: 14, fontWeight: 'bold', dx: -10, dy: 10 }}
              />

              <ReferenceLine x={2} stroke="#ccc" strokeDasharray="5 5" />
              <ReferenceLine x={8} stroke="#ccc" strokeDasharray="5 5" />
              <ReferenceLine y={2} stroke="#ccc" strokeDasharray="5 5" />
              <ReferenceLine y={8} stroke="#ccc" strokeDasharray="5 5" />

              <XAxis 
                type="number" 
                dataKey="execution_capacity_score" 
                name="Execution Capacity" 
                domain={[0, 10]} 
                ticks={[0, 2, 4, 6, 8, 10]}
              >
                <Label value="Execution Capacity" offset={-10} position="insideBottom" style={{ fontWeight: 'bold', fontSize: '1.1rem' }} />
                <Label value="(Runway health, governance/process maturity, team strength)" offset={-35} position="insideBottom" style={{ fontSize: '0.85rem', fontStyle: 'italic', fill: '#666' }} />
              </XAxis>
              
              <YAxis 
                type="number" 
                dataKey="market_validation_score" 
                name="Market Validation" 
                domain={[0, 10]} 
                ticks={[0, 2, 4, 6, 8, 10]}
              >
                <Label value="Market Validation" angle={-90} position="insideLeft" offset={-40} style={{ fontWeight: 'bold', fontSize: '1.1rem', textAnchor: 'middle' }} />
                <Label value="(contracts/revenue, partnerships, regulatory position)" angle={-90} position="insideLeft" offset={-20} style={{ fontSize: '0.85rem', fontStyle: 'italic', fill: '#666', textAnchor: 'middle' }} />
              </YAxis>
              
              <ZAxis range={[100, 100]} />
              
              <Tooltip 
                cursor={{ strokeDasharray: '3 3' }}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="custom-tooltip" style={{ 
                        backgroundColor: '#fff', padding: '10px', border: '1px solid #ccc',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)', borderRadius: '4px'
                      }}>
                        <p style={{ margin: '0 0 5px', fontWeight: 'bold', color: '#333' }}>{data.company_name}</p>
                        <p style={{ margin: '0', fontSize: '0.9rem' }}>Type: {data.company_type}</p>
                        <p style={{ margin: '0', fontSize: '0.9rem' }}>Status: {data.status}</p>
                        <p style={{ margin: '0', fontSize: '0.9rem' }}>Execution: {data.execution_capacity_score}</p>
                        <p style={{ margin: '0', fontSize: '0.9rem' }}>Market: {data.market_validation_score}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              
              <Scatter 
                name="Portfolio Companies" 
                data={assessments}
                shape={(props: any) => (
                  <CustomArrow 
                    {...props} 
                    company_type={props.payload.company_type} 
                    fill={getStatusColor(props.payload.status)} 
                  />
                )}
              >
                {assessments.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getStatusColor(entry.status)} />
                ))}
                <LabelList dataKey="company_name" content={<CustomLabel />} />
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        <div className="graph-legend mt-4" style={{ 
          display: 'flex', justifyContent: 'center', gap: '2rem', flexWrap: 'wrap',
          padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '8px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontWeight: 'bold' }}>Status:</span>
            {STATUS_OPTIONS.map(opt => (
              <div key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.85rem' }}>
                <div style={{ width: 12, height: 12, backgroundColor: opt.color, borderRadius: '2px' }}></div>
                <span>{opt.label}</span>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontWeight: 'bold' }}>Company Type (Icons):</span>
            <span style={{ fontSize: '0.85rem' }}>◀ BMF- | ▶ BMF/Scaling | ▼ PMF- | ▲ PMF</span>
          </div>
        </div>
      </div>

      <div className="section-container">
        <button 
          onClick={() => setShowIntrinsic(!showIntrinsic)}
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
            INTRINSIC VALUE AND LIQUIDITY INDEX
          </span>
          <span style={{ 
            transition: 'transform 0.3s ease', 
            transform: showIntrinsic ? 'rotate(180deg)' : 'rotate(0deg)',
            fontSize: '1.2rem'
          }}>▼</span>
        </button>

        <div style={{ 
          maxHeight: (showIntrinsic && performanceData) ? '3000px' : '0', 
          overflow: 'hidden', 
          transition: 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
          opacity: showIntrinsic ? 1 : 0
        }}>
          <div className="section-content animate-fade-in" style={{ padding: '1rem 0' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '2rem', marginBottom: '2rem' }}>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                <div className="content-card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}>
                  <h3 style={{ marginBottom: '2rem', textAlign: 'center', border: 'none' }}>Intrinsic Value</h3>
                  <div style={{ width: '100%', height: 450 }}>
                    <ResponsiveContainer>
                      <RadarChart cx="50%" cy="50%" outerRadius="80%" data={(() => {
                        const currentDeals = performanceData.current_deals || [];
                        const companyMap = new Map();
                        
                        currentDeals.forEach((d: any) => {
                          if (!companyMap.has(d.company_name)) {
                            const entryVal = parseFloat(d.entry_valuation);
                            const currentVal = parseFloat(d.latest_valuation);
                            const exitMultiple = parseFloat(d.expected_exit_multiple || 5.0);
                            const ownership = parseFloat(d.ownership_after_dilution || 0);
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
                            const currentDeals = performanceData.current_deals || [];
                            const uniqueCompanies = new Set(currentDeals.map((d: any) => d.company_name));
                            return uniqueCompanies.size > 15 ? false : { fill: '#64748b', fontSize: '0.8rem' };
                          })()}
                        />
                        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                        <Radar name="Entry Valuation" dataKey="entry" stroke="#3498db" fill="#3498db" fillOpacity={0.4} />
                        <Radar name="Current Valuation" dataKey="current" stroke="#2ecc71" fill="#2ecc71" fillOpacity={0.5} />
                        <Radar name="Expected Final Valuation" dataKey="expected" stroke="#10b981" fill="transparent" strokeDasharray="5 5" />
                        <Tooltip content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const d = payload[0].payload;
                            return (
                              <div className="custom-tooltip" style={{ 
                                backgroundColor: '#fff', padding: '12px', border: '1px solid #e2e8f0',
                                borderRadius: '8px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                                fontSize: '0.85rem', lineHeight: '1.5'
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

                <div className="content-card" style={{ padding: '1.5rem' }}>
                  <h4 style={{ marginBottom: '1.5rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.75rem', color: '#1e293b' }}>Portfolio Outcome Probabilities</h4>
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Outcome Type</th>
                          <th style={{ textAlign: 'right' }}>Expected Rate</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td>Failure Rate</td>
                          <td style={{ textAlign: 'right', fontWeight: '700', color: '#ef4444' }}>{(performanceData.admin_fee?.failure_rate || 0).toFixed(1)}%</td>
                        </tr>
                        <tr>
                          <td>Break-even Rate</td>
                          <td style={{ textAlign: 'right', fontWeight: '700', color: '#fbbf24' }}>{(performanceData.admin_fee?.break_even_rate || 0).toFixed(1)}%</td>
                        </tr>
                        <tr>
                          <td>High Growth Rate</td>
                          <td style={{ textAlign: 'right', fontWeight: '700', color: '#10b981' }}>{(performanceData.admin_fee?.high_growth_rate || 0).toFixed(1)}%</td>
                        </tr>
                        <tr style={{ borderTop: '2px solid #e2e8f0' }}>
                          <td style={{ fontWeight: '600' }}>Expected Dilution</td>
                          <td style={{ textAlign: 'right', fontWeight: '700', color: '#3b82f6' }}>{(performanceData.admin_fee?.dilution_rate || 0).toFixed(1)}%</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <div className="content-card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}>
                <div style={{ textAlign: 'center' }}>
                  <h3 style={{ marginBottom: '0.5rem', border: 'none' }}>Liquidity Index</h3>
                  <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '2.5rem' }}>Measures the portfolio's path to realization</p>
                </div>
                
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {liData && (
                    <LiquidityGauge 
                      value={liData.finalLI} 
                      portfolioL={liData.portfolioL} 
                      ageFactor={liData.ageFactor} 
                      age={liData.age} 
                    />
                  )}
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

                  <div className="divider-h" style={{ margin: '1.5rem 0', opacity: 0.1, borderTop: '1px solid #1e293b' }} />

                  <h4 style={{ fontSize: '0.9rem', color: '#1e293b', marginBottom: '1rem', border: 'none' }}>Liquidity Comparison</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {comparisons.sort((a, b) => a.li - b.li).map((comp) => (
                      <div key={comp.name} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: comp.isCurrent ? '#1e293b' : '#64748b', fontWeight: comp.isCurrent ? '700' : '400' }}>
                          <span>{comp.name}</span>
                          <span>{comp.li.toFixed(1)}%</span>
                        </div>
                        <div style={{ width: '100%', height: '6px', backgroundColor: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ 
                            width: `${comp.li}%`, 
                            height: '100%', 
                            background: comp.isCurrent ? 'linear-gradient(to right, #3b82f6, #2563eb)' : '#94a3b8',
                            borderRadius: '3px'
                          }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {performanceData?.dashboard?.performance_table && (
              <div className="content-card" style={{marginTop: '2rem', border: 'none'}}>
                <div style={{ padding: '1.5rem', color: '#94a3b8', fontSize: '0.95rem', textAlign: 'center', maxWidth: '800px', margin: '0 auto' }}>
                  <strong style={{ color: '#0f172a', display: 'block', marginBottom: '0.5rem', fontSize: '1.1rem' }}>Strategic Performance Visualization</strong>
                  This radar chart maps the fund's growth trajectory based on Total Portfolio Value. It provides a multi-dimensional assessment of capital appreciation efficiency over the fund's lifecycle, with MOIC and IRR visible on hover.
                </div>
                <FundPerformanceRadarChart 
                  data={performanceData.dashboard.performance_table} 
                  irr={performanceData.current_deals_metrics?.irr || 0} 
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskAssessmentTab;
