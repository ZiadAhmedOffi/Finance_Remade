import React, { useState, useEffect, useCallback } from "react";
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

interface InvestorAction {
  id: string;
  investor_email: string;
  type: string;
  year: number;
  amount: string; // Storing as string for input, converting for calculations
  percentage_sold: string;
  discount_percentage: string;
  investor_selling_email: string;
  investor_sold_to_email: string;
  units: string;
  created_at: string;
}

interface InvestorLogData {
  investors: {
    first_name: string;
    last_name: string;
    email: string;
    units: number;
    ownership_percentage: number;
  }[];
  graph_data: {
    year: number;
    total_capital_invested: number;
    total_capital_required: number;
  }[];
  actions: InvestorAction[];
  total_units: number;
}

interface InvestorLogTabProps {
  fundId: string;
}

const InvestorLogTab: React.FC<InvestorLogTabProps> = ({ fundId }) => {
  const [data, setData] = useState<InvestorLogData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination for actions table
  const [currentPage, setCurrentPage] = useState(1);
  const actionsPerPage = 5;

  // Form Modal state
  const [showModal, setShowModal] = useState(false);
  const [investors, setInvestors] = useState<{id: string, email: string}[]>([]);
  const [fundPortfolioValue, setFundPortfolioValue] = useState<number>(0); // To store portfolio value for calculations

  const [formData, setFormData] = useState({
    type: "PRIMARY_INVESTMENT",
    investor: "",
    year: new Date().getFullYear(),
    amount: "", // Corresponds to 'price_sold_at' for secondary exit
    percentage_sold: "",
    discount_percentage: "0",
    investor_selling: "",
    investor_sold_to: "",
  });

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

  const fetchInvestors = async () => {
    try {
      const response = await fundsApi.getInvestors();
      setInvestors(response.data);
    } catch (err) {
      console.error("Error fetching investors:", err);
    }
  };

  // Fetch fund portfolio value for calculations when year changes or on load
  const fetchFundPortfolioValue = useCallback(async (year: number) => {
    try {
      if (data?.graph_data) {
        const yearData = data.graph_data.find(d => d.year === year);
        const portfolioVal = yearData ? yearData.total_capital_invested + yearData.total_capital_required : 0;
        setFundPortfolioValue(portfolioVal);
      } else {
        setFundPortfolioValue(0);
      }
    } catch (err) {
      console.error("Error fetching fund portfolio value:", err);
      setFundPortfolioValue(0); // Default to 0 on error
    }
  }, [data?.graph_data]);


  useEffect(() => {
    fetchInvestorLog();
    fetchInvestors();
  }, [fundId]);

  // Fetch portfolio value when data loads or year changes
  useEffect(() => {
    if (data) {
      fetchFundPortfolioValue(formData.year);
    }
  }, [data, formData.year, fetchFundPortfolioValue]);


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

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    }).format(value);
  };

  // Pagination logic
  const indexOfLastAction = currentPage * actionsPerPage;
  const indexOfFirstAction = indexOfLastAction - actionsPerPage;
  const currentActions = data.actions.slice(indexOfFirstAction, indexOfLastAction);
  const totalPages = Math.ceil(data.actions.length / actionsPerPage);

  const paginate = (pageNumber: number) => setCurrentPage(pageNumber);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };
  
  // Helper for calculating price sold at
  const calculatePriceSoldAt = (percentage: number, portfolio: number, discount: number): number => {
    // Ensure percentage is treated as a fraction (e.g., 50% -> 0.50)
    const percentageAsFraction = percentage / 100;
    return percentageAsFraction * portfolio * (1 - (discount / 100));
  };

  // Update price when percentage or discount changes for SECONDARY_EXIT
  useEffect(() => {
    if (formData.type === "SECONDARY_EXIT" && formData.percentage_sold && formData.discount_percentage) {
      const percentage = parseFloat(formData.percentage_sold);
      const discount = parseFloat(formData.discount_percentage);
      
      if (!isNaN(percentage) && !isNaN(discount) && !isNaN(fundPortfolioValue)) {
        const calculatedPrice = calculatePriceSoldAt(percentage, fundPortfolioValue, discount);
        setFormData(prev => ({ ...prev, amount: calculatedPrice.toString() }));
      }
    }
  }, [formData.type, formData.percentage_sold, formData.discount_percentage, fundPortfolioValue]);

  // Update discount when price sold at changes for SECONDARY_EXIT
  const handlePriceSoldAtChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPriceStr = e.target.value;
    setFormData(prev => ({ ...prev, amount: newPriceStr })); // Update amount field

    const newPrice = parseFloat(newPriceStr);
    if (formData.type === "SECONDARY_EXIT" && formData.percentage_sold && !isNaN(newPrice) && !isNaN(fundPortfolioValue)) {
      const percentage = parseFloat(formData.percentage_sold);
      const portfolio = fundPortfolioValue;
      
      if (percentage > 0 && portfolio > 0) {
        // Calculate discount: 1 - (price / (percentage * portfolio))
        const calculatedDiscount = 1 - (newPrice / (percentage * portfolio));
        // Ensure discount is not negative (e.g., if price exceeds expected)
        const clampedDiscount = Math.max(0, calculatedDiscount); 
        setFormData(prev => ({ ...prev, discount_percentage: (clampedDiscount * 100).toString() }));
      } else {
        // Reset discount if inputs are invalid
        setFormData(prev => ({ ...prev, discount_percentage: "0" }));
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = {
        ...formData,
        fund: fundId,
        year: parseInt(formData.year.toString()),
      };
      
      if (formData.type === "PRIMARY_INVESTMENT") {
        payload.amount = parseFloat(formData.amount);
      } else if (formData.type === "SECONDARY_EXIT") {
        payload.percentage_sold = parseFloat(formData.percentage_sold);
        payload.discount_percentage = parseFloat(formData.discount_percentage);
        payload.investor = formData.investor_selling; // Seller is the primary investor for the action
        payload.amount = parseFloat(formData.amount); // Amount is the price sold at
      }

      await fundsApi.createInvestorAction(payload);
      setShowModal(false);
      fetchInvestorLog();
      // Reset form
      setFormData({
        type: "PRIMARY_INVESTMENT",
        investor: "",
        year: new Date().getFullYear(),
        amount: "",
        percentage_sold: "",
        discount_percentage: "0",
        investor_selling: "",
        investor_sold_to: "",
      });
    } catch (err: any) {
      alert(err.response?.data?.error || "Failed to create investor action.");
    }
  };

  // Process data for the area chart
  const processedGraphData = data.graph_data.map(d => ({
    ...d,
    greenArea: d.total_capital_invested >= d.total_capital_required 
      ? [d.total_capital_required, d.total_capital_invested] 
      : [d.total_capital_required, d.total_capital_required],
    redArea: d.total_capital_required > d.total_capital_invested 
      ? [d.total_capital_invested, d.total_capital_required] 
      : [d.total_capital_invested, d.total_capital_invested]
  }));

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      {/* Metrics Summary (Total Units) */}
      <div className="grid grid-cols-1 md:grid-grid-cols-3 gap-6">
        <div className="bg-[#111] p-6 rounded-xl border border-white/10 shadow-2xl flex flex-col items-center justify-center">
          <span className="text-gray-400 text-sm uppercase tracking-wider mb-2">Total Fund Units</span>
          <span className="text-3xl font-bold text-emerald-400 font-mono">
            {formatNumber(data.total_units)}
          </span>
        </div>
      </div>

      {/* Investors Table */}
      <div className="bg-[#111] rounded-xl border border-white/10 overflow-hidden shadow-2xl">
        <div className="px-6 py-4 border-b border-white/10 bg-white/5 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-white">Investor List</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/10 bg-white/5 text-gray-400 text-xs uppercase tracking-wider">
                <th className="px-6 py-4 font-medium">First Name</th>
                <th className="px-6 py-4 font-medium">Last Name</th>
                <th className="px-6 py-4 font-medium">Email</th>
                <th className="px-6 py-4 font-medium text-right">Units Owned</th>
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
                    {formatNumber(investor.units)}
                  </td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-emerald-400">
                    {investor.ownership_percentage.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Investor Actions Table */}
      <div className="bg-[#111] rounded-xl border border-white/10 overflow-hidden shadow-2xl">
        <div className="px-6 py-4 border-b border-white/10 bg-white/5 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-white">Investor Actions</h3>
          <button 
            onClick={() => setShowModal(true)}
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            + Add Action
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/10 bg-white/5 text-gray-400 text-xs uppercase tracking-wider">
                <th className="px-6 py-4 font-medium">Type</th>
                <th className="px-6 py-4 font-medium">Investor</th>
                <th className="px-6 py-4 font-medium">Year</th>
                <th className="px-6 py-4 font-medium text-right">Amount</th>
                <th className="px-6 py-4 font-medium text-right">Units</th>
                <th className="px-6 py-4 font-medium">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {currentActions.map((action) => (
                <tr key={action.id} className="hover:bg-white/5 transition-colors">
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${
                      action.type === 'PRIMARY_INVESTMENT' ? 'bg-emerald-500/20 text-emerald-400' :
                      action.type === 'SECONDARY_INVESTMENT' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>
                      {action.type.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-white text-sm">{action.investor_email}</td>
                  <td className="px-6 py-4 text-white text-sm">{action.year}</td>
                  <td className="px-6 py-4 text-white text-sm text-right font-mono">
                    {action.amount ? formatCurrency(parseFloat(action.amount)) : '-'}
                  </td>
                  <td className="px-6 py-4 text-white text-sm text-right font-mono">
                    {formatNumber(parseFloat(action.units))}
                  </td>
                  <td className="px-6 py-4 text-gray-500 text-xs">
                    {new Date(action.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-white/10 bg-white/5 flex justify-center gap-2">
            {[...Array(totalPages)].map((_, i) => (
              <button
                key={i}
                onClick={() => paginate(i + 1)}
                className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                  currentPage === i + 1 ? 'bg-emerald-600 text-white' : 'bg-white/5 text-gray-400 hover:bg-white/10'
                }`}
              >
                {i + 1}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Modal for adding action */}
      {showModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#111] border border-white/10 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-white/10 bg-white/5 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-white">Add Investor Action</h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-white">✕</button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="space-y-2">
                <label className="text-xs text-gray-400 uppercase tracking-wider">Action Type</label>
                <select 
                  name="type" 
                  value={formData.type} 
                  onChange={handleInputChange}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white outline-none focus:border-emerald-500"
                >
                  <option value="PRIMARY_INVESTMENT">Primary Investment</option>
                  <option value="SECONDARY_EXIT">Secondary Exit</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-gray-400 uppercase tracking-wider">Year</label>
                  <input 
                    type="number" 
                    name="year" 
                    value={formData.year} 
                    onChange={handleInputChange}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white outline-none focus:border-emerald-500"
                  />
                </div>
                {formData.type === "PRIMARY_INVESTMENT" && (
                  <div className="space-y-2">
                    <label className="text-xs text-gray-400 uppercase tracking-wider">Amount (USD)</label>
                    <input 
                      type="number" 
                      name="amount" 
                      value={formData.amount} 
                      onChange={handleInputChange}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white outline-none focus:border-emerald-500"
                    />
                  </div>
                )}
              </div>

              {formData.type === "PRIMARY_INVESTMENT" ? (
                <div className="space-y-2">
                  <label className="text-xs text-gray-400 uppercase tracking-wider">Investor</label>
                  <select 
                    name="investor" 
                    value={formData.investor} 
                    onChange={handleInputChange}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white outline-none focus:border-emerald-500"
                    required
                  >
                    <option value="">Select Investor</option>
                    {investors.map(inv => <option key={inv.id} value={inv.id}>{inv.email}</option>)}
                  </select>
                </div>
              ) : ( // Secondary Exit
                <div className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-xs text-gray-400 uppercase tracking-wider">Investor Selling</label>
                    <select 
                      name="investor_selling" 
                      value={formData.investor_selling} 
                      onChange={handleInputChange}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white outline-none focus:border-emerald-500"
                      required
                    >
                      <option value="">Select Seller</option>
                      {investors.map(inv => <option key={inv.id} value={inv.id}>{inv.email}</option>)}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-gray-400 uppercase tracking-wider">Investor Sold To</label>
                    <select 
                      name="investor_sold_to" 
                      value={formData.investor_sold_to} 
                      onChange={handleInputChange}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white outline-none focus:border-emerald-500"
                    >
                      <option value="">Select Buyer (Optional)</option>
                      {investors.map(inv => <option key={inv.id} value={inv.id}>{inv.email}</option>)}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-xs text-gray-400 uppercase tracking-wider">Percentage Sold (%)</label>
                      <input 
                        type="number" 
                        step="0.0001"
                        name="percentage_sold" 
                        value={formData.percentage_sold} 
                        onChange={handleInputChange}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white outline-none focus:border-emerald-500"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs text-gray-400 uppercase tracking-wider">Discount (%)</label>
                      <input 
                        type="number" 
                        name="discount_percentage" 
                        value={formData.discount_percentage} 
                        onChange={handleInputChange}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white outline-none focus:border-emerald-500"
                      />
                    </div>
                    <div className="space-y-2 col-span-2">
                      <label className="text-xs text-gray-400 uppercase tracking-wider">Price Sold At (USD)</label>
                      <input 
                        type="number" 
                        name="amount" 
                        value={formData.amount} 
                        onChange={handlePriceSoldAtChange} // Use dedicated handler for price calculation
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white outline-none focus:border-emerald-500"
                        readOnly // Make it read-only, calculated from percentage and discount
                      />
                    </div>
                  </div>
                </div>
              )}

              <div className="pt-4 flex gap-4">
                <button 
                  type="submit"
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 rounded-xl transition-all"
                >
                  Confirm Action
                </button>
                <button 
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 bg-white/5 hover:bg-white/10 text-white font-semibold py-3 rounded-xl transition-all"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Comparison Graph */}
      <div className="bg-[#111] rounded-xl border border-white/10 p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-white mb-6">Capital Invested vs. Capital Required</h3>
        <div className="h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={processedGraphData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
              <XAxis dataKey="year" stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#666" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `$${(val / 1000000).toFixed(0)}M`} />
              <Tooltip contentStyle={{ backgroundColor: "#111", border: "1px solid #333", borderRadius: "8px" }} itemStyle={{ fontSize: "12px" }} formatter={(value: any) => [formatCurrency(value), ""]} />
              <Legend verticalAlign="top" height={36} iconType="circle" />
              <Area type="monotone" dataKey="greenArea" stroke="none" fill="#10b981" fillOpacity={0.2} name="Invested > Required" legendType="none" tooltipType="none" />
              <Area type="monotone" dataKey="redArea" stroke="none" fill="#ef4444" fillOpacity={0.2} name="Required > Invested" legendType="none" tooltipType="none" />
              <Line type="monotone" dataKey="total_capital_invested" stroke="#10b981" strokeWidth={3} dot={{ r: 4, fill: "#10b981" }} activeDot={{ r: 6 }} name="Total Capital Invested" />
              <Line type="monotone" dataKey="total_capital_required" stroke="#3b82f6" strokeWidth={3} dot={{ r: 4, fill: "#3b82f6" }} activeDot={{ r: 6 }} name="Total Capital Required" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default InvestorLogTab;
