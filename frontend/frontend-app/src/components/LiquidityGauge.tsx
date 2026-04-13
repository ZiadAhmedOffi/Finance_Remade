import React from 'react';

interface LiquidityGaugeProps {
  value: number;
  portfolioL: number;
  ageFactor: number;
  age: number;
}

/**
 * Premium Radial Gauge for Liquidity Index Visualization
 */
const LiquidityGauge: React.FC<LiquidityGaugeProps> = ({ value, portfolioL, ageFactor, age }) => {
  // Determine color based on value (Lower is better/greener)
  const getColor = (v: number) => {
    if (v <= 20) return "#10b981"; // Highly Liquid (Green)
    if (v <= 40) return "#34d399"; // Good (Light Green)
    if (v <= 60) return "#fbbf24"; // Moderate (Yellow)
    if (v <= 80) return "#f59e0b"; // Illiquid (Orange)
    return "#ef4444"; // Highly Illiquid (Red)
  };

  const getStatus = (v: number) => {
    if (v <= 20) return "Highly Liquid";
    if (v <= 40) return "Good Liquidity";
    if (v <= 60) return "Moderate";
    if (v <= 80) return "Illiquid";
    return "Highly Illiquid";
  };

  const color = getColor(value);
  const radius = 80;
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference / 2;
  const offset = arcLength - (value / 100) * arcLength;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
      <div style={{ position: 'relative', width: '220px', height: '140px' }}>
        <svg width="220" height="140" viewBox="0 0 200 120">
          {/* Background Arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#e2e8f0"
            strokeWidth="12"
            strokeLinecap="round"
          />
          {/* Colored Value Arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={arcLength}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1), stroke 1s ease' }}
          />
          <text x="100" y="90" textAnchor="middle" style={{ fontSize: '2.25rem', fontWeight: '800', fill: '#1e293b' }}>
            {value.toFixed(1)}%
          </text>
          <text x="100" y="115" textAnchor="middle" style={{ fontSize: '0.8rem', fontWeight: '700', fill: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {getStatus(value)}
          </text>
        </svg>
      </div>
      
      <div style={{ marginTop: '1.5rem', width: '100%', maxWidth: '280px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.6rem', padding: '0.5rem 0', borderBottom: '1px solid #f1f5f9' }}>
          <span style={{ color: '#64748b' }}>Portfolio Weighted:</span>
          <span style={{ fontWeight: '700', color: '#1e293b' }}>{(portfolioL * 100).toFixed(1)}%</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', padding: '0.25rem 0' }}>
          <span style={{ color: '#64748b' }}>Age Adjustment ({age}y):</span>
          <span style={{ fontWeight: '700', color: '#10b981' }}>-{((1 - ageFactor) * 100).toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
};

export default LiquidityGauge;
