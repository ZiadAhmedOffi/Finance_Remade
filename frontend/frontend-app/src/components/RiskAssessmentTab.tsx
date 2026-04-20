
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
  valuation?: number;
  ownership?: number;
  moic?: number;
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

// Better Fish SVG with more detail
const FishIcon = ({ color, size, direction }: { color: string, size: number, direction: number }) => (
  <svg 
    width={size} 
    height={size * 0.7} 
    viewBox="0 0 120 80" 
    style={{ 
      filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.3))',
      transform: `scaleX(${direction})`,
      transition: 'transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275)'
    }}
  >
    {/* Tail Fin */}
    <path d="M15,40 L-5,15 Q0,40 -5,65 Z" fill={color} opacity="0.9" />
    {/* Body */}
    <path d="M10,40 C10,10 50,0 90,0 C115,0 125,20 125,40 C125,60 115,80 90,80 C50,80 10,70 10,40 Z" fill={color} />
    {/* Top Fin */}
    <path d="M45,10 Q65,-15 85,10" fill={color} opacity="0.7" />
    {/* Side Fin */}
    <path d="M60,45 C75,40 85,50 70,65" fill="white" opacity="0.4" />
    {/* Eye */}
    <circle cx="105" cy="30" r="7" fill="white" />
    <circle cx="107" cy="28" r="3.5" fill="black" />
    <circle cx="104" cy="27" r="1.5" fill="white" />
    {/* Gills */}
    <path d="M35,30 Q40,40 35,50" stroke="rgba(255,255,255,0.3)" strokeWidth="2" fill="none" />
  </svg>
);

const Seaweed = ({ x, height, color, delay }: any) => (
  <svg 
    style={{ 
      position: 'absolute', 
      bottom: -5, 
      left: x, 
      zIndex: 1,
      animation: `sway ${3 + Math.random() * 2}s infinite ease-in-out ${delay}s`,
      transformOrigin: 'bottom center'
    }} 
    width="40" 
    height={height} 
    viewBox="0 0 40 100"
  >
    <path 
      d="M20,100 Q10,75 20,50 Q30,25 20,0" 
      fill="none" 
      stroke={color} 
      strokeWidth="6" 
      strokeLinecap="round" 
    />
  </svg>
);

const Fish = ({ data, containerWidth, containerHeight, maxValuation, onHover, onLeave }: any) => {
  const [pos, setPos] = useState({ 
    x: Math.random() * (containerWidth - 100), 
    y: Math.random() * (containerHeight - 80) 
  });
  const [vel, setVel] = useState({ 
    x: (Math.random() - 0.5) * 1.8, 
    y: (Math.random() - 0.5) * 1.2 
  });
  const [isHovered, setIsHovered] = useState(false);
  const [direction, setDirection] = useState(vel.x > 0 ? 1 : -1);

  useEffect(() => {
    if (isHovered) return;

    let frameId: number;
    let lastTime = performance.now();

    const move = (time: number) => {
      const dt = Math.min((time - lastTime) / 16, 2); 
      lastTime = time;

      setPos(prev => {
        let newX = prev.x + vel.x * dt;
        let newY = prev.y + vel.y * dt;
        let newVelX = vel.x;
        let newVelY = vel.y;

        const padX = 100;
        const padY = 80;

        if (newX < 0) {
          newX = 0;
          newVelX = Math.abs(vel.x);
          setDirection(1);
        } else if (newX > containerWidth - padX) {
          newX = containerWidth - padX;
          newVelX = -Math.abs(vel.x);
          setDirection(-1);
        }

        if (newY < 20) {
          newY = 20;
          newVelY = Math.abs(vel.y);
        } else if (newY > containerHeight - padY) {
          newY = containerHeight - padY;
          newVelY = -Math.abs(vel.y);
        }

        // Very subtle random movement adjustments
        if (Math.random() < 0.02) {
          newVelX += (Math.random() - 0.5) * 0.2;
          newVelY += (Math.random() - 0.5) * 0.2;
        }

        if (newVelX !== vel.x || newVelY !== vel.y) {
          setVel({ x: newVelX, y: newVelY });
        }

        return { x: newX, y: newY };
      });
      frameId = requestAnimationFrame(move);
    };

    frameId = requestAnimationFrame(move);
    return () => cancelAnimationFrame(frameId);
  }, [vel, isHovered, containerWidth, containerHeight]);

  const baseSize = 45;
  const size = baseSize + (maxValuation > 0 ? (data.valuation / maxValuation) * 55 : 0);

  return (
    <div 
      style={{ 
        position: 'absolute', 
        left: pos.x, 
        top: pos.y, 
        cursor: 'pointer',
        zIndex: isHovered ? 100 : 10,
        transition: 'scale 0.3s ease',
        scale: isHovered ? 1.15 : 1
      }}
      onMouseEnter={(e) => {
        setIsHovered(true);
        const rect = e.currentTarget.getBoundingClientRect();
        onHover(data, rect.left + rect.width / 2, rect.top);
      }}
      onMouseLeave={() => {
        setIsHovered(false);
        onLeave();
      }}
    >
      <FishIcon color={getStatusColor(data.status)} size={size} direction={direction} />
    </div>
  );
};

const Aquarium = ({ bucket, title, bgColor, maxValuation, onHover, onLeave }: any) => {
  return (
    <div style={{ 
      flex: 1, 
      height: '550px', 
      background: bgColor, 
      borderRadius: '32px', 
      border: '3px solid rgba(255,255,255,0.8)',
      position: 'relative',
      overflow: 'hidden',
      boxShadow: '0 15px 35px -5px rgba(0,0,0,0.1), inset 0 0 50px rgba(255,255,255,0.5)'
    }}>
      {/* Light rays effect */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'linear-gradient(135deg, rgba(255,255,255,0.2) 0%, transparent 50%, rgba(0,0,0,0.05) 100%)',
        pointerEvents: 'none',
        zIndex: 2
      }} />

      <div style={{ 
        position: 'absolute', 
        top: '25px', 
        left: '0', 
        right: '0', 
        textAlign: 'center', 
        zIndex: 10,
        pointerEvents: 'none'
      }}>
        <h4 style={{ 
          margin: 0, 
          fontSize: '1.1rem', 
          fontWeight: '900', 
          color: 'rgba(30, 41, 59, 0.8)',
          textTransform: 'uppercase',
          letterSpacing: '0.1em'
        }}>{title}</h4>
        <div style={{ 
          display: 'inline-block', 
          marginTop: '4px',
          padding: '2px 10px', 
          backgroundColor: 'rgba(255,255,255,0.5)', 
          borderRadius: '20px',
          fontSize: '0.75rem', 
          color: '#475569', 
          fontWeight: '700' 
        }}>
          {bucket.length} Companies
        </div>
      </div>
      
      {/* Seaweed */}
      <Seaweed x="15%" height="80" color="rgba(16, 185, 129, 0.4)" delay="0" />
      <Seaweed x="25%" height="120" color="rgba(5, 150, 105, 0.3)" delay="1" />
      <Seaweed x="70%" height="90" color="rgba(16, 185, 129, 0.4)" delay="0.5" />
      <Seaweed x="85%" height="110" color="rgba(5, 150, 105, 0.3)" delay="1.5" />

      {/* Bubbles */}
      <div className="bubbles-container" style={{ position: 'absolute', bottom: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 1 }}>
        {[...Array(8)].map((_, i) => (
          <div key={i} className="bubble" style={{
            position: 'absolute',
            bottom: '-20px',
            left: `${Math.random() * 100}%`,
            width: `${Math.random() * 12 + 4}px`,
            height: `${Math.random() * 12 + 4}px`,
            borderRadius: '50%',
            backgroundColor: 'rgba(255,255,255,0.4)',
            border: '1px solid rgba(255,255,255,0.6)',
            animation: `bubble-up ${Math.random() * 5 + 5}s infinite ease-in ${Math.random() * 8}s`
          }}></div>
        ))}
      </div>

      <div style={{ position: 'relative', width: '100%', height: '100%', zIndex: 5 }}>
        {bucket.map((a: any, idx: number) => (
          <Fish 
            key={idx} 
            data={a} 
            containerWidth={350} 
            containerHeight={550} 
            maxValuation={maxValuation}
            onHover={onHover}
            onLeave={onLeave}
          />
        ))}
      </div>
      
      <style>{`
        @keyframes bubble-up {
          0% { transform: translateY(0) translateX(0); opacity: 0; }
          20% { opacity: 0.6; }
          100% { transform: translateY(-600px) translateX(20px); opacity: 0; }
        }
        @keyframes sway {
          0%, 100% { transform: rotate(-5deg); }
          50% { transform: rotate(5deg); }
        }
      `}</style>
    </div>
  );
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
  const [viewMode, setViewMode] = useState<'scatter' | 'aquarium'>('scatter');
  const [hoveredFish, setHoveredFish] = useState<{
    data: RiskAssessment;
    x: number;
    y: number;
  } | null>(null);

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
        
        // Find the deal farthest from the current year for each company
        const currentYear = new Date().getFullYear();
        const oldestDealsMap: Record<string, any> = {};
        deals.forEach((d: any) => {
          const dist = Math.abs(d.entry_year - currentYear);
          const existingDist = oldestDealsMap[d.company_name] ? Math.abs(oldestDealsMap[d.company_name].entry_year - currentYear) : -1;
          if (!oldestDealsMap[d.company_name] || dist > existingDist) {
            oldestDealsMap[d.company_name] = d;
          }
        });

        const distinctCompanies = Object.keys(oldestDealsMap);
        
        const merged: RiskAssessment[] = distinctCompanies.map(name => {
          const existing = existingAssessments.find((a: any) => a.company_name === name);
          const deal = oldestDealsMap[name];
          return {
            company_name: name,
            execution_capacity_score: existing ? parseFloat(existing.execution_capacity_score) : 5.0,
            market_validation_score: existing ? parseFloat(existing.market_validation_score) : 5.0,
            status: existing ? existing.status : 'ON_TRACK',
            company_type: deal.company_type,
            valuation: parseFloat(deal.latest_valuation || 0),
            ownership: parseFloat(deal.ownership_after_dilution || 0),
            moic: parseFloat(deal.moic || 0)
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

  const fundName = performanceData?.fund_details?.name || 'Our Fund';

  const comparisons = [
    { name: 'Public Equities (S&P 500)', li: 96 },
    { name: 'Gold', li: 91 },
    { name: 'US Treasuries', li: 88 },
    { name: fundName, li: liData?.finalLI || 0, isCurrent: true },
    { name: 'MENA Real Estate', li: 62 },
    { name: 'MENA VC/PE', li: 54 },
    { name: 'Global PE', li: 32 },
    { name: 'Venture Capital', li: 22 },
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
          <h3 className="tab-title" style={{ margin: 0 }}>Execution Capacity vs. Market Validation</h3>
          
          <div style={{ 
            display: 'flex', 
            backgroundColor: '#f1f5f9', 
            padding: '4px', 
            borderRadius: '12px',
            border: '1px solid #e2e8f0'
          }}>
            <button 
              onClick={() => setViewMode('scatter')}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: '600',
                transition: 'all 0.2s',
                border: 'none',
                backgroundColor: viewMode === 'scatter' ? '#fff' : 'transparent',
                color: viewMode === 'scatter' ? '#2563eb' : '#64748b',
                boxShadow: viewMode === 'scatter' ? '0 2px 4px rgba(0,0,0,0.05)' : 'none',
                cursor: 'pointer'
              }}
            >
              Scatter Plot
            </button>
            <button 
              onClick={() => setViewMode('aquarium')}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: '600',
                transition: 'all 0.2s',
                border: 'none',
                backgroundColor: viewMode === 'aquarium' ? '#fff' : 'transparent',
                color: viewMode === 'aquarium' ? '#2563eb' : '#64748b',
                boxShadow: viewMode === 'aquarium' ? '0 2px 4px rgba(0,0,0,0.05)' : 'none',
                cursor: 'pointer'
              }}
            >
              Aquarium View
            </button>
          </div>
        </div>
        
        {viewMode === 'scatter' ? (
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
        ) : (
          <div style={{ position: 'relative', width: '100%' }}>
            {/* Global Tooltip for Fish - Avoids clipping */}
            {hoveredFish && (
              <div style={{
                position: 'fixed',
                left: hoveredFish.x,
                top: hoveredFish.y - 10,
                transform: 'translate(-50%, -100%)',
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                backdropFilter: 'blur(8px)',
                padding: '16px',
                borderRadius: '16px',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
                border: '1px solid rgba(226, 232, 240, 0.8)',
                width: '240px',
                pointerEvents: 'none',
                zIndex: 9999,
                animation: 'scale-up 0.2s ease-out'
              }}>
                <p style={{ fontWeight: '800', margin: '0 0 10px', color: '#0f172a', fontSize: '1rem', borderBottom: '2px solid #f1f5f9', paddingBottom: '6px' }}>{hoveredFish.data.company_name}</p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.85rem' }}>
                  <span style={{ color: '#64748b', fontWeight: '500' }}>Valuation:</span>
                  <span style={{ fontWeight: '700', textAlign: 'right', color: '#1e293b' }}>{formatCurrencyLong(hoveredFish.data.valuation || 0)}</span>
                  <span style={{ color: '#64748b', fontWeight: '500' }}>Ownership:</span>
                  <span style={{ fontWeight: '700', textAlign: 'right', color: '#1e293b' }}>{(hoveredFish.data.ownership || 0).toFixed(2)}%</span>
                  <span style={{ color: '#64748b', fontWeight: '500' }}>MOIC:</span>
                  <span style={{ fontWeight: '700', textAlign: 'right', color: '#1e293b' }}>{(hoveredFish.data.moic || 0).toFixed(2)}x</span>
                </div>
                <div style={{ 
                  marginTop: '10px', 
                  padding: '4px 8px', 
                  borderRadius: '6px', 
                  backgroundColor: getStatusColor(hoveredFish.data.status) + '15',
                  color: getStatusColor(hoveredFish.data.status),
                  fontSize: '0.75rem',
                  fontWeight: '700',
                  textAlign: 'center'
                }}>
                  Status: {hoveredFish.data.status}
                </div>
                {/* Tooltip arrow */}
                <div style={{
                  position: 'absolute',
                  bottom: '-8px',
                  left: '50%',
                  transform: 'translateX(-50%) rotate(45deg)',
                  width: '16px',
                  height: '16px',
                  backgroundColor: '#fff',
                  borderRight: '1px solid rgba(226, 232, 240, 0.8)',
                  borderBottom: '1px solid rgba(226, 232, 240, 0.8)',
                }} />
              </div>
            )}

            <div style={{ display: 'flex', gap: '24px', width: '100%' }}>
              {(() => {
                const maxVal = Math.max(...assessments.map(a => a.valuation || 0), 1);
                const buckets = {
                  sunset: assessments.filter(a => a.execution_capacity_score <= 2 && a.market_validation_score <= 2),
                  champions: assessments.filter(a => a.execution_capacity_score >= 8 && a.market_validation_score >= 8),
                  highGrowth: assessments.filter(a => 
                    !(a.execution_capacity_score <= 2 && a.market_validation_score <= 2) && 
                    !(a.execution_capacity_score >= 8 && a.market_validation_score >= 8)
                  )
                };
                return (
                  <>
                    <Aquarium 
                      bucket={buckets.sunset} 
                      title="Sunset" 
                      bgColor="linear-gradient(180deg, #fee2e2 0%, #fca5a5 100%)" 
                      maxValuation={maxVal} 
                      onHover={(data: any, x: number, y: number) => setHoveredFish({ data, x, y })}
                      onLeave={() => setHoveredFish(null)}
                    />
                    <Aquarium 
                      bucket={buckets.highGrowth} 
                      title="High-Growth Potential" 
                      bgColor="linear-gradient(180deg, #fef3c7 0%, #fcd34d 100%)" 
                      maxValuation={maxVal} 
                      onHover={(data: any, x: number, y: number) => setHoveredFish({ data, x, y })}
                      onLeave={() => setHoveredFish(null)}
                    />
                    <Aquarium 
                      bucket={buckets.champions} 
                      title="Champions - Exit Track" 
                      bgColor="linear-gradient(180deg, #dcfce7 0%, #86efac 100%)" 
                      maxValuation={maxVal} 
                      onHover={(data: any, x: number, y: number) => setHoveredFish({ data, x, y })}
                      onLeave={() => setHoveredFish(null)}
                    />
                  </>
                );
              })()}
            </div>
            
            <style>{`
              @keyframes scale-up {
                from { opacity: 0; transform: translate(-50%, -90%) scale(0.95); }
                to { opacity: 1; transform: translate(-50%, -100%) scale(1); }
              }
            `}</style>
          </div>
        )}

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
                        const currentYear = performanceData.dashboard?.current_year || new Date().getFullYear();
                        const farthestDealsMap = new Map();
                        
                        currentDeals.forEach((d: any) => {
                          const dist = Math.abs(d.entry_year - currentYear);
                          const existingDeal = farthestDealsMap.get(d.company_name);
                          if (!existingDeal || dist > Math.abs(existingDeal.entry_year - currentYear)) {
                            farthestDealsMap.set(d.company_name, d);
                          }
                        });
                        
                        const result: any[] = [];
                        farthestDealsMap.forEach((d) => {
                          const entryVal = parseFloat(d.entry_valuation);
                          const currentVal = parseFloat(d.latest_valuation);
                          const exitMultiple = parseFloat(d.expected_exit_multiple || 5.0);
                          const ownership = parseFloat(d.ownership_after_dilution || 0);
                          const targetVal = entryVal * exitMultiple;
                          
                          result.push({
                            subject: d.company_name,
                            entry: targetVal > 0 ? (entryVal / targetVal) * 100 : 0,
                            current: targetVal > 0 ? (currentVal / targetVal) * 100 : 0,
                            expected: 100,
                            upside: 120,
                            highGrowth: 150,
                            full_name: d.company_name,
                            raw_entry: entryVal,
                            raw_current: currentVal,
                            raw_expected: targetVal,
                            ownership: ownership
                          });
                        });
                        
                        return result;
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
                        <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
                        <Radar name="Entry Valuation" dataKey="entry" stroke="#3498db" fill="#3498db" fillOpacity={0.4} />
                        <Radar name="Current Valuation" dataKey="current" stroke="#2ecc71" fill="#2ecc71" fillOpacity={0.5} />
                        <Radar name="Base Case" dataKey="expected" stroke="#6ee7b7" fill="transparent" strokeDasharray="5 5" />
                        <Radar name="Upside Case" dataKey="upside" stroke="#10b981" fill="transparent" strokeDasharray="5 5" />
                        <Radar name="High Growth Case" dataKey="highGrowth" stroke="#065f46" fill="transparent" strokeDasharray="5 5" />
                        <Tooltip content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const d = payload[0].payload;
                            let achievedScenario = "In Progress";
                            if (d.current >= 150) achievedScenario = "High Growth Scenario";
                            else if (d.current >= 120) achievedScenario = "Upward Scenario";
                            else if (d.current >= 100) achievedScenario = "Base Scenario";

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
                                <p style={{ margin: '2px 0' }}><span style={{ color: '#129448' }}>Expected Exit Val:</span> <strong>{formatCurrencyLong(d.raw_expected)}</strong> ({100}%)</p>
                                <p style={{ margin: '8px 0 0', fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic' }}>Achieved Scenario: {achievedScenario}</p>
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
                      fundName={fundName}
                    />
                  )}
                </div>

                <div style={{ marginTop: '0.75rem', padding: '1.25rem', backgroundColor: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                  <h4 style={{ fontSize: '0.9rem', color: '#1e293b', marginBottom: '0.75rem', border: 'none' }}>Index Interpretation</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '4px' }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#10b981' }}></div> 60-100%: Liquid / Good
                      </div>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '4px' }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#fbbf24' }}></div> 40-60%: Moderate
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ef4444' }}></div> 0-40%: Illiquid
                      </div>
                    </div>
                  </div>

                  <div className="divider-h" style={{ margin: '1.5rem 0', opacity: 0.1, borderTop: '1px solid #1e293b' }} />

                  <h4 style={{ fontSize: '0.9rem', color: '#1e293b', marginBottom: '1rem', border: 'none' }}>Liquidity Comparison</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {comparisons.sort((a, b) => b.li - a.li).map((comp) => {
                      const barColor = comp.li >= 60 ? '#10b981' : comp.li >= 40 ? '#fbbf24' : '#ef4444';
                      return (
                        <div key={comp.name} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: comp.isCurrent ? '#1e293b' : '#64748b', fontWeight: comp.isCurrent ? '700' : '400' }}>
                            <span>{comp.name} {comp.isCurrent && "(Current)"}</span>
                            <span>{comp.li.toFixed(1)}%</span>
                          </div>
                          <div style={{ 
                            width: '100%', 
                            height: '8px', 
                            backgroundColor: '#e2e8f0', 
                            borderRadius: '4px', 
                            overflow: 'hidden',
                            border: comp.isCurrent ? '1px solid #1e293b' : 'none'
                          }}>
                            <div style={{ 
                              width: `${comp.li}%`, 
                              height: '100%', 
                              background: barColor,
                              borderRadius: '4px',
                              opacity: comp.isCurrent ? 1 : 0.7,
                              transition: 'width 1s ease-out'
                            }} />
                          </div>
                        </div>
                      );
                    })}
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
