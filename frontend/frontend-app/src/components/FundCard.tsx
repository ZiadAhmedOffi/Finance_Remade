import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

interface Fund {
  id: string;
  name: string;
  description: string;
  tag: string;
}

interface FundCardProps {
  fund: Fund;
}

const TAG_COLORS: Record<string, { bg: string, text: string }> = {
  "BIC": { bg: "#EEF2FF", text: "#4338CA" },
  "VC": { bg: "#ECFDF5", text: "#047857" },
  "VS": { bg: "#FFFBEB", text: "#B45309" },
  "AIG": { bg: "#FEF2F2", text: "#B91C1C" },
  "SF": { bg: "#F5F3FF", text: "#6D28D9" },
  "REAL_ESTATE": { bg: "#FFF7ED", text: "#C2410C" },
};

const getTagLabel = (tag: string) => {
  if (tag === "REAL_ESTATE") return "Real estate";
  return tag;
};

/**
 * FundCard Component
 * 
 * An interactive card displayed on the main dashboard.
 * 
 * Key Features:
 * - **Dual-Graph Carousel:** Automatically rotates between a "Capital Injection & Appreciation" 
 *   waterfall chart and a "Base Points" performance chart.
 * - **Hover-Pause:** Auto-rotation pauses when the user hovers over the card.
 * - **Dynamic Data:** Fetches performance analytics asynchronously for the specific fund.
 * - **Metric Badges:** Shows high-level KPIs like MOIC and IRR.
 * 
 * @param {Fund} fund - The fund object containing ID, name, and description.
 */
const FundCard: React.FC<FundCardProps> = ({ fund }) => {
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeGraphIndex, setActiveGraphIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const timerRef = useRef<any>(null);

  /**
   * Fetches fund performance on mount.
   */
  useEffect(() => {
    const fetchPerformance = async () => {
      try {
        const response = await api.get(`/funds/${fund.id}/performance/`);
        setPerformanceData(response.data);
      } catch (err) {
        console.error(`Failed to fetch performance for fund ${fund.id}`, err);
      } finally {
        setLoading(false);
      }
    };
    fetchPerformance();
  }, [fund.id]);

  /**
   * Manages the auto-rotation timer.
   * Clears and restarts based on the `isHovered` state.
   */
  useEffect(() => {
    const startTimer = () => {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = setInterval(() => {
        setActiveGraphIndex((prev) => (prev === 0 ? 1 : 0));
      }, 5000);
    };

    if (!isHovered) {
      startTimer();
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isHovered]);

  const handleGraphSwitch = (index: number) => {
    setActiveGraphIndex(index);
  };

  if (loading) return <div className="fund-card skeleton">Loading...</div>;

  /* --- Analytics Logic (Mirrors FundPerformanceTab) --- */

  const { dashboard, current_deals_metrics, aggregated_exits, admin_fee } = performanceData || {};
  
  // Prepare waterfall chart data
  const waterfallData = dashboard?.performance_table?.map((entry: any, index: number) => {
    const prevEntry = index > 0 ? dashboard.performance_table[index - 1] : null;
    const start_value = prevEntry ? prevEntry.total_portfolio_value_with_prognosis : 0;
    return {
      ...entry,
      start_value: start_value,
      // Use clean injection and appreciation fields from backend
      injection: (entry.injection_current ?? 0) + (entry.injection_prognosis ?? 0),
      appreciation: (entry.appreciation_current ?? 0) + (entry.appreciation_prognosis ?? 0)
    };
  }) || [];

  // Calculate base points (Portfolio Value - G&A) / Total Invested
  const calculateBasePointsData = () => {
    if (!admin_fee || !dashboard?.performance_table) return [];
    
    // ... (Constants logic for gaMap remains correct as per fund structure)
    const { inception_year, fund_life, total_admin_cost, operations_fee, management_fees } = admin_fee;
    const years_arr = Array.from({ length: fund_life }, (_, i) => inception_year + i);

    const estLicensingY1 = total_admin_cost * 0.05;
    const estLicensingLater = estLicensingY1 * 0.5;
    const row1Vals = years_arr.map((_, i) => i === 0 ? estLicensingY1 : estLicensingLater);
    const row1Total = row1Vals.reduce((a, b) => a + b, 0);

    const contractsY1 = operations_fee * 0.2;
    const contractsLater = operations_fee * 0.02;
    const row2Vals = years_arr.map((_, i) => i === 0 ? contractsY1 : contractsLater);
    const row2Total = row2Vals.reduce((a, b) => a + b, 0);

    const othersLegalVal = (total_admin_cost - (row1Total + row2Total)) / fund_life;
    const row3Vals = years_arr.map(() => othersLegalVal);

    const table1TotalsPerYear = years_arr.map((_, i) => row1Vals[i] + row2Vals[i] + row3Vals[i]);

    const onboardingVal = operations_fee * 0.05;
    const rowO1Vals = years_arr.map((_, i) => i < 2 ? onboardingVal : 0);
    const rowO1Total = rowO1Vals.reduce((a, b) => a + b, 0);

    const marketingVal = (operations_fee * 0.4) / fund_life;
    const rowO2Vals = years_arr.map(() => marketingVal);
    const rowO2Total = marketingVal * fund_life;

    const reportVal = operations_fee * 0.02;
    const rowO3Vals = years_arr.map(() => reportVal);
    const rowO3Total = rowO3Vals.reduce((a, b) => a + b, 0);

    const accountingVal = operations_fee * 0.04;
    const rowO4Vals = years_arr.map(() => accountingVal);
    const rowO4Total = accountingVal * fund_life;

    const othersOpsVal = (operations_fee - (rowO1Total + rowO2Total + rowO3Total + rowO4Total)) / fund_life;
    const rowO5Vals = years_arr.map(() => othersOpsVal);

    const table2TotalsPerYear = years_arr.map((_, i) => 
      rowO1Vals[i] + rowO2Vals[i] + rowO3Vals[i] + rowO4Vals[i] + rowO5Vals[i]
    );

    const managementVal = management_fees / fund_life;
    const rowM1Vals = years_arr.map(() => managementVal);

    const totalGAVals = years_arr.map((_, i) => table1TotalsPerYear[i] + table2TotalsPerYear[i] + rowM1Vals[i]);
    const gaMap: Record<number, number> = {};
    years_arr.forEach((year, i) => { gaMap[year] = totalGAVals[i]; });

    // For BP calculations, we use combined metrics
    const totalInvested = dashboard.total_invested + current_deals_metrics.total_invested;
    const { fund_end_year } = dashboard.performance_table[0] || {};
    const currentYear = dashboard.performance_table[0]?.current_year || new Date().getFullYear();
    
    const irrBase = aggregated_exits?.find((c: any) => c.case === "Base Case")?.irr || 0;
    const irrUpside = aggregated_exits?.find((c: any) => c.case === "Upside Case")?.irr || 0;
    const irrHighGrowth = aggregated_exits?.find((c: any) => c.case === "High Growth Case")?.irr || 0;

    // Split each portfolio into historical and future parts for correct compounding
    let pBase = 0;
    let pUpside = 0;
    let pHighGrowth = 0;

    return dashboard.performance_table.map((row: any) => {
      const injection = (row.injection_current ?? 0) + (row.injection_prognosis ?? 0);
      const gaYearly = gaMap[row.year] || 0;
      const year = row.year;

      // Until current_year - 1, they use the same IRR (irrBase)
      // From current_year onwards, they use their respective scenario IRRs
      const useScenarioIRR = year >= currentYear;

      const effectiveIRRBase = irrBase;
      const effectiveIRRUpside = useScenarioIRR ? irrUpside : irrBase;
      const effectiveIRRHighGrowth = useScenarioIRR ? irrHighGrowth : irrBase;

      const apprBase = pBase * effectiveIRRBase;
      const apprUpside = pUpside * effectiveIRRUpside;
      const apprHighGrowth = pHighGrowth * effectiveIRRHighGrowth;

      // Appreciation applies until fund_end_year
      const currentApprBase = year <= fund_end_year ? apprBase : 0;
      const currentApprUpside = year <= fund_end_year ? apprUpside : 0;
      const currentApprHighGrowth = year <= fund_end_year ? apprHighGrowth : 0;

      pBase += injection + currentApprBase;
      pUpside += injection + currentApprUpside;
      pHighGrowth += injection + currentApprHighGrowth;

      const investedBP = totalInvested > 0 ? (injection / totalInvested) * 100 : 0;
      const lineBase = totalInvested > 0 ? ((pBase - gaYearly) / totalInvested) * 100 : 0;
      const lineUpside = totalInvested > 0 ? ((pUpside - gaYearly) / totalInvested) * 100 : 0;
      const lineHighGrowth = totalInvested > 0 ? ((pHighGrowth - gaYearly) / totalInvested) * 100 : 0;

      return {
        year: row.year,
        investedBP: investedBP,
        "Base Case": lineBase,
        "Upside Case": lineUpside,
        "High Growth Case": lineHighGrowth
      };
    });
  };

  const basePointsChartData = calculateBasePointsData();

  // Formatting Utilities
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact" }).format(val);
  const formatCurrencyLong = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);
  const formatPercent = (val: number) => (val * 100).toFixed(1) + "%";

  return (
    <div 
      className="fund-card-revamp"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="card-carousel-section">
        {/* Manual Navigation Controls */}
        <div className="carousel-controls">
           <button 
             className={`dot ${activeGraphIndex === 0 ? "active" : ""}`} 
             onClick={() => handleGraphSwitch(0)}
             aria-label="Show Capital Injection Graph"
           />
           <button 
             className={`dot ${activeGraphIndex === 1 ? "active" : ""}`} 
             onClick={() => handleGraphSwitch(1)}
             aria-label="Show Base Points Graph"
           />
        </div>

        {/* Carousel Views */}
        {activeGraphIndex === 0 ? (
          <div className="chart-view fade-in">
            <h5>Capital Injection & Appreciation</h5>
            <ResponsiveContainer width="100%" height={220}>
              <ComposedChart data={waterfallData} margin={{top: 10, right: 10, left: 0, bottom: 0}}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="year" tick={{fontSize: 10}} />
                <YAxis tickFormatter={formatCurrency} tick={{fontSize: 10}} width={40} />
                <Tooltip formatter={(value: any) => formatCurrencyLong(Number(value))} />
                <Bar dataKey="start_value" stackId="a" fill="transparent" />
                <Bar dataKey="injection" stackId="a" fill="#3498db" name="Injection" />
                <Bar dataKey="appreciation" stackId="a" fill="#2ecc71" name="Appreciation" />
                <Line type="stepAfter" dataKey="total_portfolio_value_with_prognosis" stroke="#7f8c8d" dot={false} strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="chart-view fade-in">
            <h5>Fund Performance (Base Points)</h5>
            <ResponsiveContainer width="100%" height={220}>
              <ComposedChart data={basePointsChartData} margin={{top: 10, right: 10, left: 0, bottom: 0}}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="year" tick={{fontSize: 10}} />
                <YAxis label={{ value: 'BP', angle: -90, position: 'insideLeft', fontSize: 10 }} tick={{fontSize: 10}} width={30} />
                <Tooltip formatter={(value: any) => Number(value).toFixed(2)} />
                <ReferenceLine x={dashboard.performance_table[0]?.current_year - 1} stroke="#e74c3c" strokeDasharray="3 3" />
                <Bar dataKey="investedBP" fill="#e67e22" name="Inv. Cap (BP)" />
                <Line type="monotone" dataKey="Base Case" stroke="#2ecc71" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="Upside Case" stroke="#3498db" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="High Growth Case" stroke="#9b59b6" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Fund Metadata */}
      <div className="card-content">
        <div className="card-header-row" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem'}}>
          <div style={{display: 'flex', flexDirection: 'column', gap: '0.25rem'}}>
            <h3 className="fund-name" style={{margin: 0, fontSize: '1.25rem', fontWeight: '700'}}>
                <Link to={`/funds/${fund.id}`} style={{color: '#1e293b', textDecoration: 'none'}}>{fund.name}</Link>
            </h3>
            <span style={{
              alignSelf: 'flex-start',
              padding: '0.1rem 0.6rem',
              borderRadius: '4px',
              fontSize: '0.7rem',
              fontWeight: '700',
              textTransform: 'uppercase',
              backgroundColor: TAG_COLORS[fund.tag]?.bg || '#f1f5f9',
              color: TAG_COLORS[fund.tag]?.text || '#475569'
            }}>
              {getTagLabel(fund.tag)}
            </span>
          </div>
          <div className="metric-badges" style={{display: 'flex', gap: '0.4rem', flexShrink: 0}}>
            <span className="metric-badge moic" title="Prognosis MOIC" style={{background: '#dbeafe', color: '#1e40af', padding: '0.25rem 0.5rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: '600', whiteSpace: 'nowrap'}}>{dashboard?.moic.toFixed(2)}x (Fut)</span>
            <span className="metric-badge moic-past" title="Achieved MOIC" style={{background: '#e2e8f0', color: '#475569', padding: '0.25rem 0.5rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: '600', whiteSpace: 'nowrap'}}>{current_deals_metrics?.moic.toFixed(2)}x (Past)</span>
          </div>
        </div>
        
        <p className="fund-desc" style={{marginBottom: '1rem', fontSize: '0.875rem', color: '#64748b', lineClamp: 2, overflow: 'hidden'}}>{fund.description || "No description provided."}</p>
        
        <div className="stats-container" style={{display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem'}}>
          {/* Current Deals (Past) */}
          <div className="stats-group">
            <h6 style={{fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748b', marginBottom: '0.5rem', fontWeight: '700'}}>Deals Already Made (Past)</h6>
            <div className="quick-stats" style={{display: 'flex', gap: '1.5rem'}}>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>Invested</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600'}}>{formatCurrency(current_deals_metrics?.total_invested)}</span>
              </div>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>Deals</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600'}}>{current_deals_metrics?.total_deals}</span>
              </div>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>Ventures</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600'}}>{current_deals_metrics?.total_companies}</span>
              </div>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>IRR</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600'}}>{formatPercent(current_deals_metrics?.irr)}</span>
              </div>
            </div>
          </div>

          {/* Deal Prognosis (Future) */}
          <div className="stats-group">
            <h6 style={{fontSize: '0.7rem', textTransform: 'uppercase', color: '#3b82f6', marginBottom: '0.5rem', fontWeight: '700'}}>Prognosis for Future Deals (Future)</h6>
            <div className="quick-stats" style={{display: 'flex', gap: '1.5rem'}}>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>To Invest</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600', color: '#1e40af'}}>{formatCurrency(dashboard?.total_invested)}</span>
              </div>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>Est. Deals</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600', color: '#1e40af'}}>{dashboard?.total_deals}</span>
              </div>
              <div className="stat" style={{display: 'flex', flexDirection: 'column'}}>
                <span className="stat-label" style={{fontSize: '0.65rem', color: '#94a3b8'}}>Exp. IRR</span>
                <span className="stat-value" style={{fontSize: '0.85rem', fontWeight: '600', color: '#1e40af'}}>{formatPercent(dashboard?.irr)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card-footer" style={{borderTop: '1px solid #f1f5f9', paddingTop: '1rem'}}>
          <Link to={`/funds/${fund.id}`} className="view-btn" style={{width: '100%', textAlign: 'center', display: 'block', background: '#1e293b', color: 'white', padding: '0.6rem', borderRadius: '0.5rem', fontWeight: '600', textDecoration: 'none'}}>
            View Full Analytics &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
};

export default FundCard;
