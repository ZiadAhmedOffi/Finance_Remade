import React, { useState, useEffect } from "react";
import { realEstateApi } from "../api/api";
import { formatCurrency } from "../utils/formatters";

interface CashFlowMetadata {
  months_held: number;
  market_value: string;
  effective_rent: string;
  mgmt_fees: string;
  maintenance_fees: string;
  opex: string;
  noi: string;
  debt_service: string;
  purchase_price: string;
  construction_costs: string;
  sale_proceeds: string;
  taxes: string;
  lcf_pool: string;
}

interface CashFlowData {
  inception_year: number;
  years: number[];
  properties: {
    [id: string]: {
      name: string;
      annual_cf: { [year: string]: number | null };
      metadata: { [year: string]: CashFlowMetadata };
    };
  };
  portfolio_totals: { [year: string]: number };
  portfolio_taxes: { [year: string]: number };
  cumulative_cf: { [year: string]: number };
}

const CashFlowModelTab: React.FC<{ portfolioId: string }> = ({ portfolioId }) => {
  const [data, setData] = useState<CashFlowData | null>(null);
  const [loading, setLoading] = useState(true);
  const [startYear, setStartYear] = useState<number | "">("");
  const [endYear, setEndYear] = useState<number | "">("");
  
  // Drill-down state
  const [selectedCell, setSelectedCell] = useState<{ propId: string, year: number } | null>(null);

  useEffect(() => {
    fetchData();
  }, [portfolioId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await realEstateApi.getCashFlow(
        portfolioId, 
        startYear === "" ? undefined : startYear, 
        endYear === "" ? undefined : endYear
      );
      setData(response.data);
    } catch (err) {
      console.error("Failed to fetch cash flow data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyFilter = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData();
  };

  if (loading && !data) return <div style={{ textAlign: 'center', padding: '2rem' }}>Loading cash flow model...</div>;

  const drillMetadata = selectedCell ? data?.properties[selectedCell.propId].metadata[selectedCell.year] : null;

  return (
    <div className="cash-flow-tab-container">
      <style>{`
        .cash-flow-tab-container { padding: 1rem; }
        .filter-bar {
          display: flex;
          gap: 1rem;
          align-items: center;
          margin-bottom: 1.5rem;
          background: #f8fafc;
          padding: 1rem;
          border-radius: 8px;
        }
        .filter-group { display: flex; align-items: center; gap: 0.5rem; }
        .filter-group input {
          width: 80px;
          padding: 0.25rem 0.5rem;
          border: 1px solid #cbd5e1;
          border-radius: 4px;
        }
        .table-scroll-wrapper {
          overflow-x: auto;
          background: white;
          border-radius: 8px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .cf-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.875rem;
        }
        .cf-table th, .cf-table td {
          padding: 0.75rem 1rem;
          text-align: right;
          border-bottom: 1px solid #e2e8f0;
          white-space: nowrap;
        }
        .cf-table th {
          background: #f8fafc;
          font-weight: 600;
          color: #475569;
          text-align: center;
        }
        .year-label {
          font-size: 0.75rem;
          color: #64748b;
          display: block;
          margin-bottom: 0.25rem;
        }
        .cf-table th.sticky-col, .cf-table td.sticky-col {
          position: sticky;
          left: 0;
          background: #f8fafc;
          text-align: left;
          z-index: 10;
          border-right: 2px solid #e2e8f0;
        }
        .cf-table td.sticky-col { background: white; font-weight: 600; }
        .cf-table tr:hover td { background: #f1f5f9; }
        .cf-table .total-row { background: #f1f5f9; font-weight: 700; }
        .cf-table .cumulative-row { background: #e2e8f0; font-weight: 700; }
        .negative-cf { color: #ef4444; }
        .positive-cf { color: #059669; }
        .clickable-cell { cursor: pointer; transition: background 0.2s; }
        .clickable-cell:hover { background: #e2e8f0 !important; }
        
        /* Modal Styles */
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }
        .modal-content {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          max-width: 500px;
          width: 90%;
          box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);
        }
        .metadata-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
          margin-top: 1.5rem;
        }
        .metadata-item {
          display: flex;
          flex-direction: column;
          border-bottom: 1px solid #f1f5f9;
          padding-bottom: 0.5rem;
        }
        .metadata-label {
          font-size: 0.75rem;
          color: #64748b;
          font-weight: 600;
          text-transform: uppercase;
        }
        .metadata-value {
          font-size: 1rem;
          font-weight: 500;
          color: #1e293b;
        }
      `}</style>

      <div className="filter-bar">
        <h3 style={{ margin: 0, marginRight: '1rem', fontSize: '1.125rem' }}>Time Horizon</h3>
        <form onSubmit={handleApplyFilter} style={{ display: 'flex', gap: '1rem' }}>
          <div className="filter-group">
            <label>Start Year:</label>
            <input 
              type="number" 
              value={startYear} 
              onChange={(e) => setStartYear(e.target.value ? parseInt(e.target.value) : "")} 
              placeholder="e.g. 2024"
            />
          </div>
          <div className="filter-group">
            <label>End Year:</label>
            <input 
              type="number" 
              value={endYear} 
              onChange={(e) => setEndYear(e.target.value ? parseInt(e.target.value) : "")} 
              placeholder="e.g. 2033"
            />
          </div>
          <button type="submit" className="btn btn-secondary">Apply Interval</button>
        </form>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Updating data...</div>
      ) : data && (
        <div className="table-scroll-wrapper">
          <table className="cf-table">
            <thead>
              <tr>
                <th className="sticky-col">Property Name</th>
                {data.years.map(year => (
                  <th key={year}>
                    <span className="year-label">Year {year - data.inception_year + 1}</span>
                    {year}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.properties).map(([id, prop]) => (
                <tr key={id}>
                  <td className="sticky-col">{prop.name}</td>
                  {data.years.map(year => (
                    <td 
                      key={year} 
                      className={`${prop.annual_cf[year] !== null && prop.annual_cf[year]! < 0 ? "negative-cf" : "positive-cf"} ${prop.annual_cf[year] !== null ? "clickable-cell" : ""}`}
                      onClick={() => prop.annual_cf[year] !== null && setSelectedCell({ propId: id, year })}
                    >
                      {prop.annual_cf[year] === null ? "(-)" : formatCurrency(prop.annual_cf[year])}
                    </td>
                  ))}
                </tr>
              ))}
              
              <tr className="total-row">
                <td className="sticky-col">Total Portfolio CF</td>
                {data.years.map(year => (
                  <td key={year} className={data.portfolio_totals[year] < 0 ? "negative-cf" : "positive-cf"}>
                    {formatCurrency(data.portfolio_totals[year])}
                  </td>
                ))}
              </tr>

              <tr className="total-row" style={{ color: "#64748b", background: "#f8fafc" }}>
                <td className="sticky-col">Total Portfolio Taxes</td>
                {data.years.map(year => (
                  <td key={year}>
                    {formatCurrency(data.portfolio_taxes[year])}
                  </td>
                ))}
              </tr>
              
              <tr className="cumulative-row">
                <td className="sticky-col">Cumulative CF</td>
                {data.years.map(year => (
                  <td key={year} className={data.cumulative_cf[year] < 0 ? "negative-cf" : "positive-cf"}>
                    {formatCurrency(data.cumulative_cf[year])}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {selectedCell && drillMetadata && (
        <div className="modal-overlay" onClick={() => setSelectedCell(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0 }}>{data?.properties[selectedCell.propId].name} - {selectedCell.year} Breakdown</h3>
              <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem' }} onClick={() => setSelectedCell(null)}>✕</button>
            </div>
            
            <div className="metadata-grid">
              <div className="metadata-item">
                <span className="metadata-label">Months Owned</span>
                <span className="metadata-value">{drillMetadata.months_held} months</span>
              </div>
              <div className="metadata-item">
                <span className="metadata-label">Market Value</span>
                <span className="metadata-value">{formatCurrency(drillMetadata.market_value)}</span>
              </div>
              <div className="metadata-item">
                <span className="metadata-label">Effective Rent</span>
                <span className="metadata-value">{formatCurrency(drillMetadata.effective_rent)}</span>
              </div>
              <div className="metadata-item">
                <span className="metadata-label">Management Fees</span>
                <span className="metadata-value">{formatCurrency(drillMetadata.mgmt_fees)}</span>
              </div>
              <div className="metadata-item">
                <span className="metadata-label">Maintenance Fees</span>
                <span className="metadata-value">{formatCurrency(drillMetadata.maintenance_fees)}</span>
              </div>
              <div className="metadata-item">
                <span className="metadata-label">Total OpEx</span>
                <span className="metadata-value">{formatCurrency(drillMetadata.opex)}</span>
              </div>
              <div className="metadata-item">
                <span className="metadata-label">Net Operating Income (NOI)</span>
                <span className="metadata-value" style={{ fontWeight: 700 }}>{formatCurrency(drillMetadata.noi)}</span>
              </div>
              <div className="metadata-item">
                <span className="metadata-label">Debt Service</span>
                <span className="metadata-value">{formatCurrency(drillMetadata.debt_service)}</span>
              </div>

              <div className="metadata-item">
                <span className="metadata-label">Annual Taxes</span>
                <span className="metadata-value" style={{ color: "#ef4444" }}>{formatCurrency(drillMetadata.taxes)}</span>
              </div>
              
              {parseFloat(drillMetadata.lcf_pool) > 0 && (
                <div className="metadata-item">
                  <span className="metadata-label">LCF Pool Remaining</span>
                  <span className="metadata-value" style={{ color: "#3b82f6" }}>{formatCurrency(drillMetadata.lcf_pool)}</span>
                </div>
              )}
              
              {parseFloat(drillMetadata.purchase_price) !== 0 && (
                <div className="metadata-item">
                  <span className="metadata-label">Purchase Price</span>
                  <span className="metadata-value">{formatCurrency(drillMetadata.purchase_price)}</span>
                </div>
              )}
              
              {parseFloat(drillMetadata.construction_costs) !== 0 && (
                <div className="metadata-item">
                  <span className="metadata-label">Construction Costs</span>
                  <span className="metadata-value">{formatCurrency(drillMetadata.construction_costs)}</span>
                </div>
              )}
              
              {parseFloat(drillMetadata.sale_proceeds) !== 0 && (
                <div className="metadata-item">
                  <span className="metadata-label">Sale Proceeds</span>
                  <span className="metadata-value" style={{ color: '#10b981' }}>{formatCurrency(drillMetadata.sale_proceeds)}</span>
                </div>
              )}
            </div>
            
            <div style={{ marginTop: '2rem', padding: '1rem', background: '#f8fafc', borderRadius: '8px', textAlign: 'center' }}>
              <span className="metadata-label">Net Annual Cash Flow</span>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: data?.properties[selectedCell.propId].annual_cf[selectedCell.year]! < 0 ? '#ef4444' : '#059669' }}>
                {formatCurrency(data?.properties[selectedCell.propId].annual_cf[selectedCell.year])}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CashFlowModelTab;
