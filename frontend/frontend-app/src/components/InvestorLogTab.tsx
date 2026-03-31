import React, { useState, useEffect } from "react";
import { fundsApi } from "../api/api";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  Line,
  ComposedChart,
} from "recharts";

interface InvestorLogData {
  investors: {
    first_name: string;
    last_name: string;
    email: string;
    total_invested: number;
    ownership_percentage: number;
  }[];
  graph_data: {
    year: number;
    total_capital_invested: number;
    total_capital_required: number;
  }[];
}

interface InvestorLogTabProps {
  fundId: string;
}

const InvestorLogTab: React.FC<InvestorLogTabProps> = ({ fundId }) => {
  const [data, setData] = useState<InvestorLogData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInvestorLog = async () => {
      try {
        setLoading(true);
        const response = await fundsApi.getInvestorLog(fundId);
        setData(response.data);
        setError(null);
      } catch (err: any) {
        console.error("Error fetching investor log:", err);
        setError("Failed to load investor log data.");
      } finally {
        setLoading(false);
      }
    };

    fetchInvestorLog();
  }, [fundId]);

  if (loading) return <div className="p-4 text-gray-400">Loading investor log...</div>;
  if (error) return <div className="p-4 text-red-500">{error}</div>;
  if (!data) return <div className="p-4 text-gray-400">No data available.</div>;

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Process data for the area chart to show green/red difference
  const processedGraphData = data.graph_data.map(d => ({
    ...d,
    // When invested > required, the area is between required and invested (Green)
    greenArea: d.total_capital_invested >= d.total_capital_required 
      ? [d.total_capital_required, d.total_capital_invested] 
      : [d.total_capital_required, d.total_capital_required],
    // When required > invested, the area is between invested and required (Red)
    redArea: d.total_capital_required > d.total_capital_invested 
      ? [d.total_capital_invested, d.total_capital_required] 
      : [d.total_capital_invested, d.total_capital_invested]
  }));

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Investors Table */}
      <div className="bg-[#111] rounded-xl border border-white/10 overflow-hidden shadow-2xl">
        <div className="px-6 py-4 border-b border-white/10 bg-white/5">
          <h3 className="text-lg font-semibold text-white">Investor List</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/10 bg-white/5 text-gray-400 text-xs uppercase tracking-wider">
                <th className="px-6 py-4 font-medium">First Name</th>
                <th className="px-6 py-4 font-medium">Last Name</th>
                <th className="px-6 py-4 font-medium">Email</th>
                <th className="px-6 py-4 font-medium text-right">Total Invested</th>
                <th className="px-6 py-4 font-medium text-right">Ownership %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {data.investors.map((investor, idx) => (
                <tr key={idx} className="hover:bg-white/5 transition-colors">
                  <td className="px-6 py-4 text-white text-sm">{investor.first_name}</td>
                  <td className="px-6 py-4 text-white text-sm">{investor.last_name}</td>
                  <td className="px-6 py-4 text-gray-400 text-sm">{investor.email}</td>
                  <td className="px-6 py-4 text-white text-sm text-right font-mono">
                    {formatCurrency(investor.total_invested)}
                  </td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-emerald-400">
                    {investor.ownership_percentage.toFixed(2)}%
                  </td>
                </tr>
              ))}
              {data.investors.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                    No investor actions recorded for this fund.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Comparison Graph */}
      <div className="bg-[#111] rounded-xl border border-white/10 p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-white mb-6">Capital Invested vs. Capital Required</h3>
        <div className="h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={processedGraphData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
              <XAxis 
                dataKey="year" 
                stroke="#666" 
                fontSize={12} 
                tickLine={false} 
                axisLine={false} 
              />
              <YAxis 
                stroke="#666" 
                fontSize={12} 
                tickLine={false} 
                axisLine={false} 
                tickFormatter={(val) => `$${(val / 1000000).toFixed(0)}M`}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: "#111", border: "1px solid #333", borderRadius: "8px" }}
                itemStyle={{ fontSize: "12px" }}
                formatter={(value: any) => {
                  if (Array.isArray(value)) return null; // Don't show range in tooltip
                  return [formatCurrency(value), ""];
                }}
              />
              <Legend verticalAlign="top" height={36} iconType="circle" />
              
              {/* Areas for coloring the difference */}
              <Area
                type="monotone"
                dataKey="greenArea"
                stroke="none"
                fill="#10b981"
                fillOpacity={0.2}
                name="Invested > Required"
                legendType="none"
                tooltipType="none"
              />
              <Area
                type="monotone"
                dataKey="redArea"
                stroke="none"
                fill="#ef4444"
                fillOpacity={0.2}
                name="Required > Invested"
                legendType="none"
                tooltipType="none"
              />

              {/* Lines */}
              <Line 
                type="monotone" 
                dataKey="total_capital_invested" 
                stroke="#10b981" 
                strokeWidth={3} 
                dot={{ r: 4, fill: "#10b981" }} 
                activeDot={{ r: 6 }} 
                name="Total Capital Invested"
              />
              <Line 
                type="monotone" 
                dataKey="total_capital_required" 
                stroke="#3b82f6" 
                strokeWidth={3} 
                dot={{ r: 4, fill: "#3b82f6" }} 
                activeDot={{ r: 6 }} 
                name="Total Capital Required"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default InvestorLogTab;
