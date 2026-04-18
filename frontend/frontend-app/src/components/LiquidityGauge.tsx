import React from 'react';

interface LiquidityGaugeProps {
  value: number;
  portfolioL: number;
  ageFactor: number;
  age: number;
  fundName?: string;
}

/**
 * Horizontal Bar Gauge for Liquidity Index Visualization
 * Features color gradients: 
 * - 0-40%: Green gradient
 * - 40-60%: Yellow gradient
 * - 60-100%: Red gradient
 */
const LiquidityGauge: React.FC<LiquidityGaugeProps> = ({ value, portfolioL, ageFactor, age, fundName }) => {
  // Clamp value between 0 and 100
  const clampedValue = Math.min(Math.max(value, 0), 100);

  const getStatus = (v: number) => {
    if (v <= 20) return "Highly Liquid";
    if (v <= 40) return "Good Liquidity";
    if (v <= 60) return "Moderate";
    if (v <= 80) return "Illiquid";
    return "Highly Illiquid";
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%', padding: '1.5rem 1.5rem 0' }}>
      <div style={{ marginBottom: '2.5rem', textAlign: 'center' }}>
        <span style={{ 
          fontSize: '3.5rem', 
          fontWeight: '900', 
          color: '#1e293b', 
          lineHeight: '1',
          display: 'block'
        }}>
          {value.toFixed(1)}%
        </span>
        <span style={{ 
          fontSize: '1rem', 
          fontWeight: '800', 
          color: '#64748b', 
          textTransform: 'uppercase', 
          letterSpacing: '0.1em',
          marginTop: '0.5rem',
          display: 'inline-block',
          padding: '4px 12px',
          background: '#f1f5f9',
          borderRadius: '20px'
        }}>
          {getStatus(value)}
        </span>
      </div>

      <div style={{ position: 'relative', width: '100%', height: '100px', padding: '0 10px' }}>
        {/* Scale Labels */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          marginBottom: '12px', 
          fontSize: '0.75rem', 
          color: '#94a3b8', 
          fontWeight: '800',
          position: 'relative'
        }}>
          <span>0%</span>
          <span style={{ position: 'absolute', left: '40%', transform: 'translateX(-50%)' }}>40%</span>
          <span style={{ position: 'absolute', left: '60%', transform: 'translateX(-50%)' }}>60%</span>
          <span>100%</span>
        </div>

        {/* The Bar */}
        <div style={{
          height: '40px',
          width: '100%',
          borderRadius: '20px',
          // Smoother gradient transition
          background: 'linear-gradient(to right, #10b981 0%, #22c55e 30%, #facc15 50%, #f97316 70%, #ef4444 100%)',
          boxShadow: 'inset 0 4px 6px rgba(0,0,0,0.15)',
          position: 'relative',
          border: '1px solid rgba(0,0,0,0.05)'
        }}>
          {/* Subtle Section Dividers */}
          <div style={{ position: 'absolute', left: '40%', top: '20%', bottom: '20%', width: '1px', background: 'rgba(255,255,255,0.2)', zIndex: 1 }} />
          <div style={{ position: 'absolute', left: '60%', top: '20%', bottom: '20%', width: '1px', background: 'rgba(255,255,255,0.2)', zIndex: 1 }} />
          
          {/* Glossy Overlay */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '50%',
            background: 'linear-gradient(to bottom, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0) 100%)',
            borderRadius: '20px 20px 0 0'
          }} />

          {/* Indicator Marker */}
          <div style={{
            position: 'absolute',
            left: `${clampedValue}%`,
            top: 0,
            bottom: 0,
            width: '0px',
            zIndex: 10,
            transition: 'left 1.5s cubic-bezier(0.4, 0, 0.2, 1)'
          }}>
            {/* The Indicator Line (through the bar) */}
            <div style={{ 
              position: 'absolute',
              top: '-15px',
              bottom: '-15px',
              left: '50%',
              transform: 'translateX(-50%)',
              width: '6px', 
              backgroundColor: '#1e293b', 
              borderRadius: '3px',
              boxShadow: '0 0 10px rgba(0,0,0,0.3)',
              border: '2px solid #fff'
            }} />
            
            {/* Triangle pointing DOWN towards the text */}
            <div style={{
              position: 'absolute',
              bottom: '-45px',
              left: '50%',
              transform: 'translateX(-50%)',
              width: 0,
              height: 0,
              borderLeft: '10px solid transparent',
              borderRight: '10px solid transparent',
              borderTop: '12px solid #1e293b',
              zIndex: 11
            }} />

            {/* Label Below */}
            <div style={{
              position: 'absolute',
              bottom: '-85px',
              left: '50%',
              transform: 'translateX(-50%)',
              backgroundColor: '#1e293b',
              color: 'white',
              padding: '6px 14px',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: '900',
              whiteSpace: 'nowrap',
              boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.04)',
              zIndex: 11,
              letterSpacing: '0.025em',
              border: '1px solid rgba(255,255,255,0.1)'
            }}>
              {fundName || "OUR FUND"}
            </div>
          </div>
        </div>
      </div>

      <div style={{ 
        marginTop: '6.5rem', 
        width: '100%',
        display: 'grid', 
        gridTemplateColumns: '1fr 1fr', 
        gap: '1rem' 
      }}>
        <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '16px', border: '1px solid #e2e8f0' }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.4rem' }}>Portfolio Weighted</div>
          <div style={{ fontSize: '1.25rem', fontWeight: '900', color: '#1e293b' }}>{(portfolioL * 100).toFixed(1)}%</div>
        </div>
        <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '16px', border: '1px solid #e2e8f0' }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.4rem' }}>Age Adjustment ({age}y)</div>
          <div style={{ fontSize: '1.25rem', fontWeight: '900', color: '#10b981' }}>-{((1 - ageFactor) * 100).toFixed(1)}%</div>
        </div>
      </div>
    </div>
  );
};

export default LiquidityGauge;
