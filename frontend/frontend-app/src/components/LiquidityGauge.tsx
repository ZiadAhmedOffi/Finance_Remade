import React from 'react';

interface LiquidityGaugeProps {
  value: number;
  portfolioL: number;
  ageFactor: number;
  age: number;
}

/**
 * Vertical Bar Gauge for Liquidity Index Visualization
 * Features a fixed color gradient from green (0%) to yellow (50%) to red (100%).
 * The filled portion represents a partial "crop" of this absolute gradient.
 */
const LiquidityGauge: React.FC<LiquidityGaugeProps> = ({ value, portfolioL, ageFactor, age }) => {
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
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%', padding: '1rem' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '2.5rem', height: '320px' }}>
        
        {/* Vertical Bar Container */}
        <div style={{ 
          position: 'relative', 
          width: '40px', 
          height: '100%', 
          backgroundColor: '#f1f5f9', 
          borderRadius: '20px',
          boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.05)',
          border: '1px solid #e2e8f0',
          overflow: 'hidden'
        }}>
          {/* Background Track (Always visible at low opacity) */}
          <div style={{ 
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            background: 'linear-gradient(to top, #10b981 0%, #fbbf24 50%, #ef4444 100%)',
            opacity: 0.15
          }} />
          
          {/* Filled Bar (Clipped part of the full gradient) */}
          <div style={{ 
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            background: 'linear-gradient(to top, #10b981 0%, #fbbf24 50%, #ef4444 100%)',
            clipPath: `inset(${100 - clampedValue}% 0 0 0)`,
            transition: 'clip-path 1.5s cubic-bezier(0.4, 0, 0.2, 1)',
            borderRadius: '20px'
          }}>
            {/* Glossy Reflection Overlay */}
            <div style={{
              position: 'absolute',
              top: 0,
              left: '20%',
              width: '25%',
              height: '100%',
              background: 'linear-gradient(to right, rgba(255,255,255,0.3) 0%, rgba(255,255,255,0) 100%)',
              borderRadius: '20px'
            }} />
          </div>

          {/* Scale Markers */}
          {[20, 40, 60, 80].map(mark => (
            <div key={mark} style={{
              position: 'absolute',
              bottom: `${mark}%`,
              left: 0,
              width: '100%',
              height: '1px',
              backgroundColor: 'rgba(255,255,255,0.3)',
              zIndex: 2
            }} />
          ))}
        </div>

        {/* Labels and Scale Details */}
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          justifyContent: 'space-between', 
          height: '100%', 
          padding: '5px 0' 
        }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '2.5rem', fontWeight: '900', color: '#1e293b', lineHeight: '1' }}>
              {value.toFixed(1)}%
            </span>
            <span style={{ 
              fontSize: '0.85rem', 
              fontWeight: '700', 
              color: '#64748b', 
              textTransform: 'uppercase', 
              letterSpacing: '0.05em',
              marginTop: '0.5rem'
            }}>
              {getStatus(value)}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
            <div style={{ padding: '0.75rem 1rem', background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '2rem', fontSize: '0.8rem', marginBottom: '0.4rem' }}>
                <span style={{ color: '#64748b' }}>Portfolio Weighted:</span>
                <span style={{ fontWeight: '700', color: '#1e293b' }}>{(portfolioL * 100).toFixed(1)}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '2rem', fontSize: '0.8rem' }}>
                <span style={{ color: '#64748b' }}>Age Adjustment ({age}y):</span>
                <span style={{ fontWeight: '700', color: '#10b981' }}>-{((1 - ageFactor) * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiquidityGauge;
