import React, { useState, useEffect, useMemo } from "react";
import { useParams } from "react-router-dom";
import { realEstateApi } from "../api/api";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Line,
} from "recharts";
import "./RealEstatePublicReport.css";
import { formatCurrency, formatPercent, formatNumber } from "../utils/formatters";

const COLORS = ["#2563eb", "#7c3aed", "#db2777", "#ea580c", "#16a34a", "#0891b2"];

const RealEstatePublicReportPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [investmentAmount, setInvestmentAmount] = useState<number>(100000);

  useEffect(() => {
    const fetchReportData = async () => {
      if (!slug) return;
      try {
        setLoading(true);
        const response = await realEstateApi.getPublicReport(slug);
        setReport(response.data);
      } catch (err: any) {
        setError(err.response?.data?.error || "Report not found or inactive.");
      } finally {
        setLoading(false);
      }
    };

    fetchReportData();
  }, [slug]);

  const performanceData = report?.performance_data;
  const metrics = performanceData?.metrics;
  const instMetrics = performanceData?.institutional_metrics;
  const textualInfo = performanceData?.portfolio_textual_info;
  const typeDistribution = performanceData?.distribution?.by_type || [];
  const countryDistribution = performanceData?.distribution?.by_country || [];
  const unitDistribution = performanceData?.unit_distribution || [];
  const valueExpansion = performanceData?.value_expansion_ladder || [];
  const properties = performanceData?.value_gain_table || [];

  const calculatorData = useMemo(() => {
    if (!metrics?.portfolio_avg_appreciation) return [];
    const appreciationRate = metrics.portfolio_avg_appreciation / 100;
    const data = [];
    for (let year = 0; year <= 10; year++) {
      const value = investmentAmount * Math.pow(1 + appreciationRate, year);
      data.push({
        year: `Year ${year}`,
        value: Math.round(value),
        appreciation: Math.round(value - investmentAmount),
      });
    }
    return data;
  }, [investmentAmount, metrics?.portfolio_avg_appreciation]);

  const config = useMemo(() => {
    const rawConfig = report?.config_json?.report_config;
    if (!rawConfig) {
        return {
            sections: [
                { id: "overview", title: "Portfolio Overview", enabled: true },
                { id: "units", title: "Digital Units & Asset Backing", enabled: true },
                { id: "calculator", title: "Investment Appreciation Calculator", enabled: true },
                { id: "allocation", title: "Strategic Allocation", enabled: true },
                { id: "growth", title: "Capital Appreciation", enabled: true },
                { id: "financing", title: "Debt & Financing", enabled: true },
                { id: "assets", title: "Asset Performance", enabled: true },
            ]
        };
    }
    
    // Inject new sections if not present in saved config
    const sections = [...rawConfig.sections];
    if (!sections.find(s => s.id === 'units')) {
      sections.splice(1, 0, { id: "units", title: "Digital Units & Asset Backing", enabled: true });
    }
    if (!sections.find(s => s.id === 'calculator')) {
      sections.splice(2, 0, { id: "calculator", title: "Investment Appreciation Calculator", enabled: true });
    }
    
    return { ...rawConfig, sections };
  }, [report]);

  const headerStyle = useMemo(() => {
    const imageUrl = textualInfo?.cover_image || "";
    if (!imageUrl) return {};
    return {
      backgroundImage: `linear-gradient(rgba(15, 23, 42, 0.8), rgba(15, 23, 42, 0.8)), url("${imageUrl}")`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat'
    };
  }, [textualInfo?.cover_image]);

  if (loading) return (
    <div className="re-report-loading">
      <div className="re-spinner"></div>
      <p>Generating Institutional Real Estate Report...</p>
    </div>
  );
  
  if (error) return (
    <div className="re-report-error">
      <div className="re-error-card">
        <h1>Access Restricted</h1>
        <p>{error}</p>
      </div>
    </div>
  );

  return (
    <div className="re-public-report-layout">
      <header className={`re-report-header ${textualInfo?.cover_image ? 're-header-immersive' : ''}`} style={headerStyle}>
        <div className="re-container">
          <div className="re-brand">Real Estate Intelligence | Institutional Reporting</div>
          <div className="re-header-content">
            <div className="re-title-group">
                <h1>{report.name}</h1>
                <div className="re-header-tags">
                  <span className="re-portfolio-tag">{report.portfolio_name}</span>
                  {textualInfo?.developer && (
                    <span className="re-developer-tag">Developed by {textualInfo.developer}</span>
                  )}
                </div>
            </div>
            <div className="re-header-metrics">
                <div className="re-h-metric">
                    <span className="re-h-label">AUM</span>
                    <span className="re-h-value">{formatCurrency(metrics?.portfolio_market_value, { notation: "compact" })}</span>
                </div>
                <div className="re-h-metric">
                    <span className="re-h-label">Loan-to-Value</span>
                    <span className="re-h-value">{formatPercent(instMetrics?.ltv_percentage)}</span>
                </div>
            </div>
          </div>
          <div className="re-report-meta">
            Portfolio Performance Snapshot • Prepared on {new Date(report.created_at).toLocaleDateString(undefined, { dateStyle: 'long' })}
          </div>
        </div>
      </header>

      <main className="re-container">
        {config.sections.map((section: any) => {
          if (!section.enabled) return null;

          if (section.type === 'CUSTOM') {
            return (
              <section key={section.id} className="re-section">
                <div className="re-section-header"><h2>{section.title}</h2></div>
                <div className="re-prose">
                   <p style={{ whiteSpace: 'pre-wrap' }}>{section.text}</p>
                </div>
              </section>
            );
          }

          switch (section.id) {
            case 'overview':
            case 'annual_summary':
              return (
                <section key={section.id} className="re-section">
                  <div className="re-section-header"><h2>{section.title || (section.id === 'overview' ? 'Executive Summary' : 'Annual Performance Summary')}</h2></div>
                  <div className="re-prose">
                    <p style={{ whiteSpace: 'pre-wrap' }}>
                        {textualInfo?.overview || `The portfolio currently comprises ${metrics?.property_count_active} active assets with a total market valuation of ${formatCurrency(metrics?.portfolio_market_value)}. Financial performance remains robust with a current Net Yield of ${formatPercent(metrics?.portfolio_net_yield)} and an annualized FFO of ${formatCurrency(instMetrics?.ffo)}.`}
                    </p>
                  </div>
                  
                  <div className="re-kpi-grid">
                    <div className="re-kpi-card">
                        <span className="re-kpi-label">FFO (Annual)</span>
                        <span className="re-kpi-value">{formatCurrency(instMetrics?.ffo, { notation: "compact" })}</span>
                        <span className="re-kpi-sub">Funds From Operations</span>
                    </div>
                    <div className="re-kpi-card">
                        <span className="re-kpi-label">AFFO (Annual)</span>
                        <span className="re-kpi-value">{formatCurrency(instMetrics?.affo, { notation: "compact" })}</span>
                        <span className="re-kpi-sub">Adjusted FFO</span>
                    </div>
                    <div className="re-kpi-card">
                        <span className="re-kpi-label">Net Yield</span>
                        <span className="re-kpi-value">{formatPercent(metrics?.portfolio_net_yield)}</span>
                        <span className="re-kpi-sub">On Current Value</span>
                    </div>
                    <div className="re-kpi-card">
                        <span className="re-kpi-label">Portfolio ROI</span>
                        <span className="re-kpi-value">{formatPercent(metrics?.portfolio_roi)}</span>
                        <span className="re-kpi-sub">Total Return</span>
                    </div>
                  </div>
                </section>
              );

            case 'units':
              return (
                <section key={section.id} className="re-section">
                  <div className="re-section-header"><h2>{section.title || "Digital Units & Asset Backing"}</h2></div>
                  <div className="re-prose">
                    <p>The portfolio is divided into {formatNumber(Math.floor(textualInfo?.total_units || 0), { maximumFractionDigits: 0 })} digital units. Each unit represents a fractional interest in the underlying real estate assets, providing direct exposure to rental income and capital appreciation.</p>
                  </div>
                  <div className="re-units-container">
                    <div className="re-units-visuals">
                      <div className="re-total-units-card">
                        <span className="re-u-label">Total Portfolio Units</span>
                        <span className="re-u-value">{formatNumber(Math.floor(textualInfo?.total_units || 0), { maximumFractionDigits: 0 })}</span>
                      </div>
                      <div className="re-units-chart">
                        <ResponsiveContainer width="100%" height={250}>
                          <PieChart>
                            <Pie 
                              data={unitDistribution} 
                              cx="50%" cy="50%" 
                              innerRadius={60}
                              outerRadius={80} 
                              dataKey="units" 
                              nameKey="name"
                              paddingAngle={5}
                            >
                              {unitDistribution.map((_: any, index: number) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                            </Pie>
                            <Tooltip formatter={(v: any) => formatNumber(Math.floor(v), { maximumFractionDigits: 0 })} />
                          </PieChart>
                        </ResponsiveContainer>
                        <div className="re-chart-caption">Unit Distribution Map</div>
                      </div>
                    </div>
                    <div className="re-units-table-wrapper">
                      <table className="re-units-table">
                        <thead>
                          <tr>
                            <th>Asset Name</th>
                            <th>Units</th>
                            <th>%</th>
                          </tr>
                        </thead>
                        <tbody>
                          {unitDistribution.map((u: any) => (
                            <tr key={u.id}>
                              <td>{u.name}</td>
                              <td className="re-fw-bold">{formatNumber(Math.floor(u.units), { maximumFractionDigits: 0 })}</td>
                              <td>{formatPercent(u.percentage)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </section>
              );

            case 'calculator':
              return (
                <section key={section.id} className="re-section re-calculator-section">
                  <div className="re-section-header"><h2>{section.title || "Investment Appreciation Calculator"}</h2></div>
                  <div className="re-calculator-layout">
                    <div className="re-calc-inputs">
                      <div className="re-calc-field">
                        <label>Investment Amount</label>
                        <div className="re-input-with-symbol">
                          <span className="re-symbol">$</span>
                          <input 
                            type="number" 
                            value={investmentAmount} 
                            onChange={(e) => setInvestmentAmount(Number(e.target.value))}
                            step="1000"
                          />
                        </div>
                        <p className="re-hint">Adjust the amount to see projected appreciation based on the portfolio's average growth rate of {formatPercent(metrics?.portfolio_avg_appreciation)}.</p>
                      </div>
                      <div className="re-calc-summary">
                        <div className="re-cs-item">
                          <span className="re-cs-label">Value in 5 Years</span>
                          <span className="re-cs-value">{formatCurrency(calculatorData[5]?.value)}</span>
                        </div>
                        <div className="re-cs-item">
                          <span className="re-cs-label">Value in 10 Years</span>
                          <span className="re-cs-value">{formatCurrency(calculatorData[10]?.value)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="re-calc-chart">
                      <ResponsiveContainer width="100%" height={300}>
                        <ComposedChart data={calculatorData}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                          <XAxis dataKey="year" />
                          <YAxis tickFormatter={(v) => formatCurrency(v, { notation: "compact" })} />
                          <Tooltip formatter={(v: any) => formatCurrency(v)} />
                          <Bar dataKey="value" name="Projected Value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </section>
              );

            case 'allocation':
              return (
                <section key={section.id} className="re-section">
                  <div className="re-section-header"><h2>{section.title || "Strategic Allocation"}</h2></div>
                  <div className="re-charts-row">
                    <div className="re-chart-box">
                      <h3>Allocation by Asset Class</h3>
                      <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                          <Pie 
                            data={typeDistribution} 
                            cx="50%" cy="50%" 
                            outerRadius={80} 
                            dataKey="value" 
                            nameKey="type"
                            label={({ name, percent }) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}
                          >
                            {typeDistribution.map((_: any, index: number) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                          </Pie>
                          <Tooltip formatter={(v: any) => formatCurrency(v, { notation: "compact" })} />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="re-chart-box">
                      <h3>Geographic Concentration</h3>
                      <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                          <Pie 
                            data={countryDistribution} 
                            cx="50%" cy="50%" 
                            outerRadius={80} 
                            dataKey="value" 
                            nameKey="country"
                            label={({ name, percent }) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}
                          >
                            {countryDistribution.map((_: any, index: number) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                          </Pie>
                          <Tooltip formatter={(v: any) => formatCurrency(v, { notation: "compact" })} />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </section>
              );

            case 'growth':
              return (
                <section key={section.id} className="re-section">
                  <div className="re-section-header"><h2>{section.title || "Capital Appreciation & Expansion"}</h2></div>
                  <div className="re-chart-full">
                    <ResponsiveContainer width="100%" height={400}>
                      <ComposedChart data={valueExpansion}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis dataKey="year" />
                        <YAxis tickFormatter={(v) => formatCurrency(v, { notation: "compact" })} />
                        <Tooltip formatter={(v: any) => formatCurrency(v)} />
                        <Legend />
                        <Bar dataKey="injection" name="Capital Injection" stackId="a" fill="#3b82f6" />
                        <Bar dataKey="appreciation" name="Market Appreciation" stackId="a" fill="#10b981" />
                        <Line type="monotone" dataKey="total_portfolio_value" name="Total Portfolio Value" stroke="#1e293b" strokeWidth={3} dot={{ r: 6 }} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </section>
              );

            case 'financing':
                return (
                  <section key={section.id} className="re-section">
                    <div className="re-section-header"><h2>{section.title || "Debt & Financing Profile"}</h2></div>
                    <div className="re-debt-grid">
                        <div className="re-debt-card">
                            <span className="re-debt-label">Total Outstanding Debt</span>
                            <span className="re-debt-value">{formatCurrency(instMetrics?.total_debt)}</span>
                        </div>
                        <div className="re-debt-card">
                            <span className="re-debt-label">Loan-to-Value (LTV)</span>
                            <span className="re-debt-value">{formatPercent(instMetrics?.ltv_percentage)}</span>
                        </div>
                    </div>
                  </section>
                );

            case 'assets':
            case 'asset_highlights':
              return (
                <section key={section.id} className="re-section">
                  <div className="re-section-header"><h2>{section.title || "Asset Performance Details"}</h2></div>
                  <div className="re-table-wrapper">
                    <table className="re-asset-table">
                      <thead>
                        <tr>
                          <th>Asset Name</th>
                          <th>Status</th>
                          <th>Cost Basis</th>
                          <th>Market Value</th>
                          <th>Unrealized Gain</th>
                          <th>Realized Gain</th>
                        </tr>
                      </thead>
                      <tbody>
                        {properties.map((prop: any) => (
                          <tr key={prop.id}>
                            <td className="re-td-name">{prop.name}</td>
                            <td><span className={`re-badge ${prop.status.toLowerCase()}`}>{prop.status}</span></td>
                            <td>{formatCurrency(prop.cost_basis)}</td>
                            <td>{prop.current_market_value ? formatCurrency(prop.current_market_value) : "-"}</td>
                            <td className={prop.unrealized_gain > 0 ? "re-positive" : ""}>
                                {prop.unrealized_gain ? formatCurrency(prop.unrealized_gain) : "-"}
                            </td>
                            <td className={prop.realized_gain > 0 ? "re-positive" : ""}>
                                {formatCurrency(prop.realized_gain)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              );

            case 'cash_flow':
              return (
                <section key={section.id} className="re-section">
                  <div className="re-section-header"><h2>{section.title || "Cash Flow Analysis"}</h2></div>
                  <div className="re-prose">
                    <p>The portfolio generates consistent cash flow through rental income and realized capital gains. Operating expenses and financing costs are managed to optimize Net Operating Income (NOI).</p>
                    <div style={{ marginTop: '1rem' }}>
                        <p style={{ whiteSpace: 'pre-wrap' }}>{textualInfo?.structure || ""}</p>
                    </div>
                  </div>
                  <div className="re-kpi-grid">
                    <div className="re-kpi-card">
                        <span className="re-kpi-label">Annual NOI</span>
                        <span className="re-kpi-value">{formatCurrency(metrics?.total_noi, { notation: "compact" })}</span>
                    </div>
                    <div className="re-kpi-card">
                        <span className="re-kpi-label">Occupancy Rate</span>
                        <span className="re-kpi-value">{formatPercent(100 - (metrics?.portfolio_vacancy_rate || 0))}</span>
                    </div>
                  </div>
                </section>
              );

            case 'portfolio_strategy':
              return (
                <section key={section.id} className="re-section">
                  <div className="re-section-header"><h2>{section.title || "Portfolio Strategy"}</h2></div>
                  <div className="re-prose">
                    <p style={{ whiteSpace: 'pre-wrap' }}>{textualInfo?.strategy || "The portfolio employs a disciplined investment strategy focused on acquiring high-quality assets in resilient submarkets, aiming for sustainable yield and long-term capital appreciation."}</p>
                  </div>
                </section>
              );

            case 'financial_statements':
              return (
                <section key={section.id} className="re-section">
                  <div className="re-section-header"><h2>{section.title || "Portfolio Structure"}</h2></div>
                  <div className="re-prose">
                    <p style={{ whiteSpace: 'pre-wrap' }}>{textualInfo?.structure || "The portfolio is structured as a diversified real estate investment vehicle, optimized for tax efficiency and operational transparency across multiple jurisdictions."}</p>
                  </div>
                </section>
              );

            case 'market_review':
              return (
                <section key={section.id} className="re-section">
                  <div className="re-section-header"><h2>{section.title || "Portfolio Lifecycle & Market Review"}</h2></div>
                  <div className="re-prose">
                    <p style={{ whiteSpace: 'pre-wrap' }}>{textualInfo?.portfolio_lifecycle || "The portfolio is currently in its growth and stabilization phase, actively identifying expansion opportunities while optimizing the performance of held assets."}</p>
                  </div>
                </section>
              );

            case 'risk_measures':
              return (
                <section key={section.id} className="re-section">
                  <div className="re-section-header"><h2>{section.title || "Risk Profile & Measures"}</h2></div>
                  <div className="re-prose">
                    <p>Our risk management framework focuses on asset-level stability, geographic diversification, and prudent leverage ratios to protect investor capital against market volatility.</p>
                  </div>
                </section>
              );

            case 'why_invest':
              return (textualInfo?.reasons_to_invest?.length > 0) ? (
                <section key={section.id} className="re-section">
                  <div className="re-section-header"><h2>Why Invest With Us?</h2></div>
                  <div className="re-reasons-grid">
                    {textualInfo.reasons_to_invest.map((reason: any, idx: number) => (
                      <div key={idx} className="re-reason-card">
                        <div className="re-reason-num">0{idx + 1}</div>
                        <h3>{reason.title}</h3>
                        <p>{reason.brief_desc}</p>
                      </div>
                    ))}
                  </div>
                </section>
              ) : null;

            default:
              return (
                <section key={section.id} className="re-section">
                   <div className="re-section-header"><h2>{section.title}</h2></div>
                   <div className="re-prose">
                     <p>Detailed analysis for {section.title} is available in the full institutional data package.</p>
                   </div>
                </section>
              );
          }
        })}
      </main>

      <footer className="re-report-footer">
        <div className="re-container">
          <p>&copy; {new Date().getFullYear()} FinanceRemade Portfolio Management. Confidential Institutional Report.</p>
          <div className="re-footer-disclaimer">
            The values presented are estimates based on current market data and internal financial models. Past performance is not indicative of future results.
          </div>
        </div>
      </footer>
    </div>
  );
};

export default RealEstatePublicReportPage;
