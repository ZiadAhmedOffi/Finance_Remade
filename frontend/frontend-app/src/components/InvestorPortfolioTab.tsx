import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

interface PortfolioItem {
  fund_name: string;
  ownership_pct: number;
  current_value: number;
  net_deployed: number;
}

interface PieChartItem {
  name: string;
  value: number;
}

interface InvestorPortfolioTabProps {
  portfolio: PortfolioItem[];
  pieChartData: PieChartItem[];
}

const InvestorPortfolioTab: React.FC<InvestorPortfolioTabProps> = ({ portfolio, pieChartData }) => {
  const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8", "#82ca9d"];

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);

  return (
    <div className="investor-portfolio">
      <section className="content-card">
        <h3>Investment Portfolio</h3>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Fund</th>
                <th>Ownership (%)</th>
                <th>Net Deployed Capital</th>
                <th>Current Value</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.map((item, idx) => (
                <tr key={idx}>
                  <td className="font-bold">{item.fund_name}</td>
                  <td>{item.ownership_pct.toFixed(4)}%</td>
                  <td>{formatCurrency(item.net_deployed)}</td>
                  <td className="font-bold">{formatCurrency(item.current_value)}</td>
                </tr>
              ))}
              {portfolio.length === 0 && (
                <tr>
                  <td colSpan={4} className="empty-msg">No investments found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {pieChartData.length > 0 && (
        <section className="chart-container content-card">
          <h3>Distribution Across Funds</h3>
          <div style={{ width: '100%', height: 400 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={pieChartData}
                  cx="50%"
                  cy="50%"
                  labelLine={true}
                  label={({ name, percent }) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}
                  outerRadius={120}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieChartData.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(val: any) => formatCurrency(Number(val || 0))} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}
    </div>
  );
};

export default InvestorPortfolioTab;
