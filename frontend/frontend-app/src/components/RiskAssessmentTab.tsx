
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
  Cell
} from 'recharts';
import { fundsApi } from '../api/api';

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

// Custom Arrow Icons based on Company Type
const CustomArrow = (props: any) => {
  const { cx, cy, fill, company_type } = props;
  
  // Icon Logic:
  // BMF- -> Arrow Left
  // BMF, BMF+, Scaling- -> Arrow Right
  // PMF- -> Arrow Down
  // PMF, PMF+ -> Arrow Up
  
  let path = "";
  if (company_type === 'BMF-') {
    // Left
    path = "M10,0 L0,5 L10,10 L10,0 Z";
  } else if (['BMF', 'BMF+', 'Scaling-'].includes(company_type)) {
    // Right
    path = "M0,0 L10,5 L0,10 L0,0 Z";
  } else if (company_type === 'PMF-') {
    // Down
    path = "M0,0 L10,0 L5,10 L0,0 Z";
  } else if (['PMF', 'PMF+'].includes(company_type)) {
    // Up
    path = "M0,10 L10,10 L5,0 L0,10 Z";
  } else {
    // Circle fallback
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // 1. Get all current deals to find distinct companies and their types
        const dealsRes = await fundsApi.getCurrentDeals(fundId);
        const deals = dealsRes.data;
        
        // 2. Get existing assessments
        const assessmentsRes = await fundsApi.getRiskAssessments(fundId);
        const existingAssessments = assessmentsRes.data;
        
        // Map companies to their types (taking the latest one if multiple rounds)
        const companyMap: Record<string, string> = {};
        deals.forEach((d: any) => {
          companyMap[d.company_name] = d.company_type;
        });

        const distinctCompanies = Object.keys(companyMap);
        
        // Merge existing assessments with companies that don't have one yet
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
        setError("Failed to load risk assessment data.");
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

  if (loading) return <div className="loading">Loading Risk Assessment...</div>;

  return (
    <div className="risk-assessment-tab">
      {error && <div className="alert alert-error">{error}</div>}
      {saveSuccess && <div className="alert alert-success">Changes saved successfully!</div>}

      <div className="content-card mb-4" style={{ padding: '1.5rem' }}>
        <h3 className="tab-title">Portfolio Risk Assessment</h3>
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

      <div className="content-card" style={{ padding: '2rem' }}>
        <h3 className="tab-title" style={{ marginBottom: '2.5rem' }}>Execution Capacity vs. Market Validation</h3>
        
        <div style={{ width: '100%', height: 600, position: 'relative' }}>
          <ResponsiveContainer>
            <ScatterChart margin={{ top: 20, right: 30, bottom: 60, left: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              
              {/* Background Color Zones */}
              <ReferenceArea x1={0} x2={2} y1={0} y2={2} fill="#ff000015" />
              <ReferenceArea x1={2} x2={8} y1={2} y2={8} fill="#f5f5dc80" />
              <ReferenceArea x1={8} x2={10} y1={8} y2={10} fill="#00ff0015" />

              {/* Grid Lines */}
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
                <Label 
                  value="Execution Capacity" 
                  offset={-10} 
                  position="insideBottom" 
                  style={{ fontWeight: 'bold', fontSize: '1.1rem' }}
                />
                <Label 
                  value="(Runway health, governance/process maturity, team strength)" 
                  offset={-35} 
                  position="insideBottom" 
                  style={{ fontSize: '0.85rem', fontStyle: 'italic', fill: '#666' }}
                />
              </XAxis>
              
              <YAxis 
                type="number" 
                dataKey="market_validation_score" 
                name="Market Validation" 
                domain={[0, 10]} 
                ticks={[0, 2, 4, 6, 8, 10]}
              >
                <Label 
                  value="Market Validation" 
                  angle={-90} 
                  position="insideLeft" 
                  offset={-40}
                  style={{ fontWeight: 'bold', fontSize: '1.1rem', textAnchor: 'middle' }}
                />
                <Label 
                  value="(contracts/revenue, partnerships, regulatory position)" 
                  angle={-90} 
                  position="insideLeft" 
                  offset={-20}
                  style={{ fontSize: '0.85rem', fontStyle: 'italic', fill: '#666', textAnchor: 'middle' }}
                />
              </YAxis>
              
              <ZAxis range={[100, 100]} />
              
              <Tooltip 
                cursor={{ strokeDasharray: '3 3' }}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="custom-tooltip" style={{ 
                        backgroundColor: '#fff', 
                        padding: '10px', 
                        border: '1px solid #ccc',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        borderRadius: '4px'
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
              
              <Scatter name="Portfolio Companies" data={assessments}>
                {assessments.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={getStatusColor(entry.status)} 
                  />
                ))}
                {/* 
                  Passing custom components to Scatter is tricky with Recharts if we want dynamic shape.
                  We use shape property which can be a function or component.
                */}
                {assessments.map((entry, index) => (
                  <Scatter 
                    key={`scatter-${index}`}
                    data={[entry]} 
                    shape={(props: any) => <CustomArrow {...props} company_type={entry.company_type} />}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        <div className="graph-legend mt-4" style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          gap: '2rem', 
          flexWrap: 'wrap',
          padding: '1rem',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px'
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
    </div>
  );
};

export default RiskAssessmentTab;
