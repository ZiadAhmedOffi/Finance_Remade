import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';

interface PerformanceEntry {
  year: number;
  total_portfolio_value_with_prognosis: number;
  cumulative_injection_with_prognosis: number;
  is_future: boolean;
}

interface FundPerformanceRadarChartProps {
  data: PerformanceEntry[];
  fundIrr: number;
}

const FundPerformanceRadarChart: React.FC<FundPerformanceRadarChartProps> = ({ data, fundIrr }) => {
  const chartOptions = useMemo(() => {
    if (!data || data.length === 0) return {};

    const years = data.map(item => item.year);
    const portfolioValues = data.map(item => item.total_portfolio_value_with_prognosis);
    
    // Calculate MOIC for each year
    const moicValues = data.map(item => 
      item.cumulative_injection_with_prognosis > 0 
        ? item.total_portfolio_value_with_prognosis / item.cumulative_injection_with_prognosis 
        : 0
    );

    // Normalize all values to a 0-100 scale for the radial display
    const maxPortfolio = Math.max(...portfolioValues, 1);
    const normalizedPortfolio = portfolioValues.map(v => (v / maxPortfolio) * 100);
    
    const maxMoic = Math.max(...moicValues, 1);
    // Scale MOIC to 85% of radius to prevent it from overlapping perfectly with portfolio peak
    const normalizedMoic = moicValues.map(v => (v / maxMoic) * 85);

    // Target IRR Path (simulated growth)
    const irrPath = data.map((_, idx) => Math.pow(1 + fundIrr, idx));
    const maxIrrPath = Math.max(...irrPath, 1);
    // Scale IRR to 70% of radius for clear layering
    const normalizedIrr = irrPath.map(v => (v / maxIrrPath) * 70);

    const lastAchievedIndex = data.findLastIndex(d => !d.is_future);

    // Data for split portfolio line
    const portfolioAchieved = normalizedPortfolio.map((v, i) => i <= lastAchievedIndex ? v : '-');
    const portfolioProjected = normalizedPortfolio.map((v, i) => i >= lastAchievedIndex ? v : '-');

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.98)',
        borderColor: '#e2e8f0',
        textStyle: { color: '#1e293b' },
        extraCssText: 'box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); border-radius: 12px;',
        formatter: (params: any) => {
          const idx = params[0].dataIndex;
          const entry = data[idx];
          const moic = moicValues[idx].toFixed(2);
          const val = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact' }).format(entry.total_portfolio_value_with_prognosis);
          return `
            <div style="padding: 5px;">
              <div style="font-weight: 800; margin-bottom: 5px; color: #64748b;">${entry.year} ${entry.is_future ? '(Projected)' : '(Achieved)'}</div>
              <div style="color: #2563eb;">Portfolio: <b>${val}</b></div>
              <div style="color: #f59e0b;">MOIC: <b>${moic}x</b></div>
              <div style="color: #8b5cf6;">IRR Target: <b>${(fundIrr * 100).toFixed(2)}%</b></div>
            </div>
          `;
        }
      },
      polar: {
        radius: '70%',
        center: ['50%', '50%']
      },
      angleAxis: {
        type: 'category',
        data: years,
        boundaryGap: false,
        splitLine: {
          show: true,
          lineStyle: { color: '#e2e8f0', type: 'dashed' }
        },
        axisLabel: {
          color: '#64748b',
          fontSize: 10,
          fontWeight: 700
        },
        axisLine: { show: false }
      },
      radiusAxis: {
        type: 'value',
        max: 100,
        axisLine: { show: false },
        axisLabel: { show: false },
        splitLine: {
          show: true,
          lineStyle: {
            color: '#f1f5f9',
            type: 'solid'
          }
        },
        splitNumber: 5
      },
      series: [
        {
          name: 'Portfolio (Achieved)',
          type: 'line',
          coordinateSystem: 'polar',
          smooth: true,
          data: portfolioAchieved,
          symbolSize: 8,
          symbol: 'circle',
          lineStyle: {
            width: 4,
            color: '#2563eb',
            shadowBlur: 10,
            shadowColor: 'rgba(37, 99, 235, 0.2)'
          },
          itemStyle: {
            color: '#2563eb',
            borderWidth: 2,
            borderColor: '#fff'
          },
          areaStyle: {
            color: 'rgba(37, 99, 235, 0.1)'
          },
          zIndex: 10
        },
        {
          name: 'Portfolio (Projected)',
          type: 'line',
          coordinateSystem: 'polar',
          smooth: true,
          data: portfolioProjected,
          symbol: 'none',
          lineStyle: {
            width: 4,
            color: '#10b981',
            type: 'dashed'
          },
          areaStyle: {
            color: 'rgba(16, 185, 129, 0.05)'
          },
          zIndex: 5
        },
        {
          name: 'MOIC Path',
          type: 'line',
          coordinateSystem: 'polar',
          smooth: true,
          data: normalizedMoic,
          symbol: 'diamond',
          symbolSize: 6,
          lineStyle: {
            width: 3,
            color: '#f59e0b',
            type: 'solid'
          },
          itemStyle: {
            color: '#f59e0b'
          },
          zIndex: 15
        },
        {
          name: 'IRR Performance',
          type: 'line',
          coordinateSystem: 'polar',
          smooth: true,
          data: normalizedIrr,
          symbol: 'none',
          lineStyle: {
            width: 2,
            color: '#8b5cf6',
            type: 'solid',
            opacity: 0.6
          },
          zIndex: 3
        }
      ]
    };
  }, [data, fundIrr]);

  return (
    <div className="radar-chart-wrapper" style={{ 
      width: '100%', 
      height: '720px', 
      background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
      borderRadius: '32px',
      overflow: 'hidden',
      padding: '2.5rem',
      border: '1px solid #e2e8f0',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{ marginBottom: '1.5rem', textAlign: 'center' }}>
        <h3 style={{ color: '#1e293b', fontSize: '1.75rem', fontWeight: '800', margin: 0 }}>Strategic Performance Trajectory</h3>
        <p style={{ color: '#64748b', fontSize: '1rem', marginTop: '0.5rem' }}>Portfolio, MOIC & IRR Projections</p>
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ReactECharts 
          option={chartOptions} 
          style={{ height: '100%', width: '100%' }} 
          notMerge={true}
          lazyUpdate={true}
        />
      </div>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        flexWrap: 'wrap', 
        gap: '2rem', 
        marginTop: '1.5rem',
        padding: '1.25rem',
        background: 'rgba(248, 250, 252, 0.8)',
        borderRadius: '20px',
        border: '1px solid #f1f5f9'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div style={{ width: '14px', height: '14px', borderRadius: '50%', background: '#2563eb' }}></div>
          <span style={{ color: '#475569', fontSize: '0.85rem', fontWeight: '700' }}>Portfolio (Achieved)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div style={{ width: '16px', height: '0', borderTop: '3px dashed #10b981' }}></div>
          <span style={{ color: '#475569', fontSize: '0.85rem', fontWeight: '700' }}>Portfolio (Projected)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div style={{ width: '14px', height: '14px', transform: 'rotate(45deg)', background: '#f59e0b' }}></div>
          <span style={{ color: '#475569', fontSize: '0.85rem', fontWeight: '700' }}>MOIC Path</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div style={{ width: '14px', height: '3px', background: '#8b5cf6', opacity: 0.6 }}></div>
          <span style={{ color: '#475569', fontSize: '0.85rem', fontWeight: '700' }}>IRR Target</span>
        </div>
      </div>
    </div>
  );
};

export default FundPerformanceRadarChart;
