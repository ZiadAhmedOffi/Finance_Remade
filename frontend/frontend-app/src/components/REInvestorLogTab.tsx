import React, { useState, useEffect } from "react";
import ReactECharts from 'echarts-for-react';
import { realEstateApi } from "../api/api";
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
  amount: string;
  percentage_sold: string;
  discount_percentage: string;
  investor_selling_email: string;
  investor_sold_to_email: string;
  units: string;
  created_at: string;
}

interface PossibleCapitalSource {
  id: string;
  name: string;
  amount: number;
  year: number;
  created_at: string;
}

interface REInvestorLogData {
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
    total_capital_with_possible: number;
    portfolio_value: number;
    units_at_year: number;
    price_per_unit: number;
    cash_reserves: number;
    assets_value: number;
    capital_breakdown: { name: string; amount: number; type: string }[];
    yearly_required: number;
    assets_breakdown: { name: string; value: number; status: string }[];
    cash_breakdown: { name: string; amount: number; type: string }[];
  }[];
  actions: InvestorAction[];
  possible_capital_sources: PossibleCapitalSource[];
  total_units: number;
  nav_metrics: {
    total_market_value_held: number;
    total_investments: number;
    total_net_proceeds: number;
    cash_reserves: number;
    nav: number;
    total_units: number;
    price_per_unit: number;
    prev_year_nav: number;
    prev_year_price_per_unit: number;
    prev_year: number;
  };
}

interface REInvestorLogTabProps {
  portfolioId: string;
  canEdit?: boolean;
}

const REInvestorLogTab: React.FC<REInvestorLogTabProps> = ({ portfolioId, canEdit }) => {
  const [data, setData] = useState<REInvestorLogData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const actionsPerPage = 10;
  const [currentSourcePage, setCurrentSourcePage] = useState(1);
  const sourcesPerPage = 5;

  // Form Modal state
  const [showModal, setShowModal] = useState(false);
  const [showSourceModal, setShowSourceModal] = useState(false);
  const [investors, setInvestors] = useState<{id: string, email: string}[]>([]);
  const [portfolioNAV, setPortfolioNAV] = useState<number>(0); 
  const [selectedYearData, setSelectedYearData] = useState<any>(null);
  const [selectedCompYearData, setSelectedCompYearData] = useState<any>(null);

  const [formData, setFormData] = useState({
    type: "PRIMARY_INVESTMENT",
    investor: "",
    year: new Date().getFullYear(),
    amount: "",
    percentage_sold: "",
    discount_percentage: "0",
    investor_selling: "",
    investor_sold_to: "",
  });

  const [sourceFormData, setSourceFormData] = useState({
    name: "",
    amount: "",
    year: new Date().getFullYear(),
  });

  const fetchInvestorLog = async () => {
    try {
      setLoading(true);
      const response = await realEstateApi.getInvestorLog(portfolioId);
      setData(response.data);
      setError(null);
    } catch (err: any) {
      console.error("Error fetching RE investor log:", err);
      setError("Failed to load investor log data.");
    } finally {
      setLoading(false);
    }
  };

  const fetchInvestors = async () => {
    try {
      const response = await realEstateApi.getInvestors(portfolioId);
      setInvestors(response.data);
    } catch (err) {
      console.error("Error fetching investors:", err);
    }
  };

  const handleDeleteAction = async (actionId: string) => {
    if (!window.confirm("Are you sure you want to delete this investor action?")) return;
    try {
      await realEstateApi.deleteInvestorAction(portfolioId, actionId);
      fetchInvestorLog();
    } catch (err: any) {
      alert(err.response?.data?.error || "Failed to delete investor action.");
    }
  };

  const handleSubmitAction = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = {
        ...formData,
        year: parseInt(formData.year.toString()),
      };
      
      if (formData.type === "PRIMARY_INVESTMENT") {
        payload.amount = parseFloat(formData.amount || "0");
      } else if (formData.type === "SECONDARY_EXIT") {
        payload.percentage_sold = parseFloat(formData.percentage_sold || "0");
        payload.discount_percentage = parseFloat(formData.discount_percentage || "0");
        payload.investor = formData.investor_selling;
        payload.amount = parseFloat(formData.amount || "0");
      }

      await realEstateApi.createInvestorAction(portfolioId, payload);
      setShowModal(false);
      fetchInvestorLog();
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

  const handleSourceDelete = async (sourceId: string) => {
    if (!window.confirm("Are you sure you want to delete this capital source?")) return;
    try {
      await realEstateApi.deletePossibleSource(portfolioId, sourceId);
      fetchInvestorLog();
    } catch (err: any) {
      alert(err.response?.data?.error || "Failed to delete capital source.");
    }
  };

  const handleSourceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...sourceFormData,
        amount: parseFloat(sourceFormData.amount || "0"),
        year: parseInt(sourceFormData.year.toString()),
      };
      await realEstateApi.createPossibleSource(portfolioId, payload);
      setShowSourceModal(false);
      fetchInvestorLog();
      setSourceFormData({
        name: "",
        amount: "",
        year: new Date().getFullYear(),
      });
    } catch (err: any) {
      alert(err.response?.data?.error || "Failed to create capital source.");
    }
  };

  const formatCurrency = (value: number) => {
    if (isNaN(value) || value === null) return "$0";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatCurrencyWithDecimals = (value: number) => {
    if (isNaN(value) || value === null) return "$0.00";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatNumber = (value: number) => {
    if (isNaN(value) || value === null) return "0.00";
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    }).format(value);
  };

  const calculatePriceSoldAt = (percentage: number, portfolio: number, discount: number): number => {
    const percentageAsFraction = percentage / 100;
    return percentageAsFraction * (portfolio || 0) * (1 - (discount / 100));
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => {
      const nextState = { ...prev, [name]: value };
      if (nextState.type === "SECONDARY_EXIT" && (name === "percentage_sold" || name === "discount_percentage" || name === "year")) {
        const percentage = parseFloat(nextState.percentage_sold || "0");
        const discount = parseFloat(nextState.discount_percentage || "0");
        const calculatedPrice = calculatePriceSoldAt(percentage, portfolioNAV, discount);
        nextState.amount = calculatedPrice.toFixed(2);
      }
      return nextState;
    });
  };

  const handlePriceSoldAtChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPriceStr = e.target.value;
    const newPrice = parseFloat(newPriceStr || "0");
    setFormData(prev => {
      const nextState = { ...prev, amount: newPriceStr };
      if (nextState.type === "SECONDARY_EXIT" && nextState.percentage_sold && !isNaN(newPrice) && portfolioNAV > 0) {
        const percentage = parseFloat(nextState.percentage_sold);
        const calculatedDiscountPct = (1 - (newPrice / (percentage / 100 * portfolioNAV))) * 100;
        nextState.discount_percentage = calculatedDiscountPct.toFixed(4);
      }
      return nextState;
    });
  };

  useEffect(() => {
    fetchInvestorLog();
    fetchInvestors();
  }, [portfolioId]);

  useEffect(() => {
    if (data?.graph_data) {
      const yearData = data.graph_data.find(d => d.year === (formData.year - 1));
      setPortfolioNAV(yearData ? (yearData.portfolio_value || 0) : (data.nav_metrics?.nav || 0));
    }
  }, [data, formData.year]);

  const handleChartClick = (state: any) => {
    if (state && state.activePayload && state.activePayload.length > 0) {
      setSelectedYearData(state.activePayload[0].payload);
    }
  };

  const handleCompChartClick = (state: any) => {
    if (state && state.activePayload && state.activePayload.length > 0) {
      setSelectedCompYearData(state.activePayload[0].payload);
    }
  };

  const processedGraphData = React.useMemo(() => {
    if (!data?.graph_data) return [];
    const results = data.graph_data.map(d => {
      const invested = d.total_capital_invested || 0;
      const required = d.total_capital_required || 0;
      const withPossible = d.total_capital_with_possible || 0;
      
      const deficit = required > invested ? (required - invested) : 0;
      const surplus = invested > required ? (invested - required) : 0;

      let darkGreenArea: [number, number];
      let redArea: [number, number];
      
      if (invested > required) {
        darkGreenArea = [required, invested];
        redArea = [required, required];
      } else {
        redArea = [invested, required];
        darkGreenArea = [invested, invested];
      }

      return {
        ...d,
        deficit,
        surplus,
        darkGreenArea,
        redArea,
        lightGreenArea: [invested, withPossible]
      };
    });

    if (results.length > 0) {
      if (!selectedYearData) {
        const curYear = new Date().getFullYear();
        const match = results.find(r => r.year === curYear) || results[results.length - 1];
        setSelectedYearData(match);
      }
      if (!selectedCompYearData) {
        const curYear = new Date().getFullYear();
        const match = results.find(r => r.year === curYear) || results[results.length - 1];
        setSelectedCompYearData(match);
      }
    }
    
    return results;
  }, [data?.graph_data, selectedYearData, selectedCompYearData]);

  if (loading) return <div className="p-4 text-gray-400">Loading investor log...</div>;
  if (error) return <div className="p-4 text-red-500">{error}</div>;
  if (!data) return <div className="p-4 text-gray-400">No data available.</div>;

  const actionsList = data.actions || [];
  const currentActions = actionsList.slice((currentPage - 1) * actionsPerPage, currentPage * actionsPerPage);
  const totalPages = Math.ceil(actionsList.length / actionsPerPage);

  const sources = data.possible_capital_sources || [];
  const currentSources = sources.slice((currentSourcePage - 1) * sourcesPerPage, currentSourcePage * sourcesPerPage);
  const totalSourcePages = Math.ceil(sources.length / sourcesPerPage);

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      {/* Metrics Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-xl flex flex-col items-center justify-center">
          <span className="text-gray-500 text-sm uppercase tracking-wider mb-2 font-medium">Total Portfolio Units</span>
          <span className="text-3xl font-bold text-emerald-600 font-mono">
            {formatNumber(data.total_units || 0)}
          </span>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-xl flex flex-col items-center justify-center">
          <span className="text-gray-500 text-sm uppercase tracking-wider mb-2 font-medium">Price per Unit (End of {data.nav_metrics?.prev_year})</span>
          <span className="text-3xl font-bold text-emerald-600 font-mono">
            {formatCurrencyWithDecimals(data.nav_metrics?.prev_year_price_per_unit || 0)}
          </span>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-xl flex flex-col items-center justify-center">
          <span className="text-gray-500 text-sm uppercase tracking-wider mb-2 font-medium">Total NAV (End of {data.nav_metrics?.prev_year})</span>
          <span className="text-3xl font-bold text-blue-600 font-mono">
            {formatCurrency(data.nav_metrics?.prev_year_nav || 0)}
          </span>
        </div>
      </div>

      {/* Comparison Graph & Breakdown */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="xl:col-span-2 bg-white rounded-xl border border-gray-200 p-6 shadow-xl">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Capital Invested vs. Capital Required</h3>
            <span className="text-xs text-gray-400 italic">Click a point on the graph to see breakdown</span>
          </div>
          <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={processedGraphData} onClick={handleChartClick}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                <XAxis dataKey="year" stroke="#374151" fontSize={12} tickLine={false} axisLine={false} interval={0} />
                <YAxis 
                  stroke="#374151" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  tickFormatter={(val) => val >= 1000000 ? `$${(val / 1000000).toFixed(1)}M` : `$${(val / 1000).toFixed(1)}k`} 
                />
                <Tooltip 
                  formatter={(value: any, name: any) => {
                    if (name === "Deficit Area" || name === "Surplus Area" || name === "Possible Capital Area") return null;
                    if ((name.includes("Deficit") || name.includes("Surplus")) && (value === 0 || !value)) return null;
                    return [formatCurrency(value), name];
                  }} 
                />
                <Legend verticalAlign="top" height={36} iconType="circle" />
                <Area type="monotone" dataKey="redArea" stroke="none" fill="#ef4444" fillOpacity={0.4} name="Deficit Area" legendType="none" tooltipType="none" />
                <Area type="monotone" dataKey="darkGreenArea" stroke="none" fill="#065f46" fillOpacity={0.6} name="Surplus Area" legendType="none" tooltipType="none" />
                <Area type="monotone" dataKey="lightGreenArea" stroke="none" fill="#10b981" fillOpacity={0.3} name="Possible Capital Area" legendType="none" tooltipType="none" />
                
                <Line type="monotone" dataKey="total_capital_invested" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} name="Total Capital Invested" />
                <Line type="monotone" dataKey="total_capital_with_possible" stroke="#10b981" strokeWidth={2} strokeDasharray="5 5" name="Total + Possible Sources" />
                <Line type="monotone" dataKey="total_capital_required" stroke="#3b82f6" strokeWidth={3} dot={{ r: 4 }} name="Total Capital Required" />
                <Line type="monotone" dataKey="deficit" stroke="#ef4444" strokeOpacity={0} name="Deficit (Required - Invested)" dot={false} strokeWidth={0} legendType="none" />
                <Line type="monotone" dataKey="surplus" stroke="#065f46" strokeOpacity={0} name="Surplus (Invested - Required)" dot={false} strokeWidth={0} legendType="none" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xl flex flex-col h-full">
          <div className="flex flex-col gap-4 mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Capital Breakdown</h3>
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-500 font-medium">Select Year:</label>
              <select 
                value={selectedYearData?.year || ""} 
                onChange={(e) => {
                  const yr = parseInt(e.target.value);
                  const match = processedGraphData.find(d => d.year === yr);
                  if (match) setSelectedYearData(match);
                }}
                className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2"
              >
                {processedGraphData.map(d => (
                  <option key={d.year} value={d.year}>{d.year}</option>
                ))}
              </select>
            </div>
            {selectedYearData && (
              <div className="bg-emerald-50 text-emerald-700 px-4 py-2 rounded-lg text-sm font-bold flex justify-between items-center">
                <span>Total for {selectedYearData.year}</span>
                <span className="font-mono">{formatCurrency(selectedYearData.yearly_required)}</span>
              </div>
            )}
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-4 pr-2">
            {selectedYearData?.capital_breakdown?.length > 0 ? (
              selectedYearData.capital_breakdown.map((item: any, idx: number) => (
                <div key={idx} className="p-4 rounded-lg bg-gray-50 border border-gray-100 transition-all hover:border-blue-200 hover:bg-blue-50 group">
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-bold text-gray-900 text-sm group-hover:text-blue-700">{item.name}</span>
                    <span className="font-mono text-emerald-600 font-bold text-sm">{formatCurrency(item.amount)}</span>
                  </div>
                  <div className="text-xs text-gray-500 uppercase tracking-tighter font-semibold">{item.type}</div>
                </div>
              ))
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 bg-gray-50 rounded-xl border border-dashed border-gray-300">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-gray-500 font-medium">No additional capital requirements for {selectedYearData?.year}</p>
                <p className="text-xs text-gray-400 mt-2">All previous obligations are met or no new events occurred this year.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Portfolio Composition Graph & Breakdown */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="xl:col-span-2 bg-white rounded-xl border border-gray-200 p-6 shadow-xl">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Assets Value vs. Cash Reserves</h3>
            <span className="text-xs text-gray-400 italic">Click a point on the graph to see composition</span>
          </div>
          <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={processedGraphData} onClick={handleCompChartClick}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                <XAxis dataKey="year" stroke="#374151" fontSize={12} tickLine={false} axisLine={false} interval={0} />
                <YAxis 
                  stroke="#374151" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  tickFormatter={(val) => val >= 1000000 ? `$${(val / 1000000).toFixed(1)}M` : `$${(val / 1000).toFixed(1)}k`} 
                />
                <Tooltip 
                  formatter={(value: any, name: any) => {
                    return [formatCurrency(value), name];
                  }} 
                />
                <Legend verticalAlign="top" height={36} iconType="circle" />
                <Area type="monotone" dataKey="assets_value" stackId="a" stroke="#10b981" fill="#10b981" fillOpacity={0.3} name="Total Assets Value" />
                <Area type="monotone" dataKey="cash_reserves" stackId="a" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} name="Cash Reserves" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xl flex flex-col h-full">
          <div className="flex flex-col gap-4 mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Portfolio Composition</h3>
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-500 font-medium">Select Year:</label>
              <select 
                value={selectedCompYearData?.year || ""} 
                onChange={(e) => {
                  const yr = parseInt(e.target.value);
                  const match = processedGraphData.find(d => d.year === yr);
                  if (match) setSelectedCompYearData(match);
                }}
                className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2"
              >
                {processedGraphData.map(d => (
                  <option key={d.year} value={d.year}>{d.year}</option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-6 pr-2">
            <div>
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Asset Changes ({formatCurrency(selectedCompYearData?.assets_value || 0)} Total Held)</h4>
              <div className="space-y-2">
                {selectedCompYearData?.assets_change_breakdown?.length > 0 ? (
                  selectedCompYearData.assets_change_breakdown.map((item: any, idx: number) => (
                    <div key={idx} className={`flex justify-between items-center p-2 rounded ${item.type === 'REMOVAL' ? 'bg-red-50 border border-red-100' : 'bg-emerald-50 border border-emerald-100'}`}>
                      <span className="text-sm font-medium text-gray-900">{item.name}</span>
                      <span className={`text-sm font-mono font-bold ${item.type === 'REMOVAL' ? 'text-red-700' : 'text-emerald-700'}`}>
                        {item.type === 'REMOVAL' ? '-' : '+'}{formatCurrency(item.amount)}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="p-4 rounded-lg bg-gray-50 border border-dashed border-gray-300 text-center">
                    <p className="text-xs text-gray-400 italic">No asset additions or removals this year.</p>
                  </div>
                )}
                
                {selectedCompYearData?.assets_breakdown?.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <h5 className="text-[10px] font-bold text-gray-400 uppercase mb-2">Properties Held End of Year</h5>
                    {selectedCompYearData.assets_breakdown.map((item: any, idx: number) => (
                      <div key={idx} className="flex justify-between items-center py-1">
                        <span className="text-xs text-gray-600">{item.name}</span>
                        <span className="text-xs font-mono font-semibold text-gray-900">{formatCurrency(item.value)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Cash Reserve Changes ({formatCurrency(selectedCompYearData?.cash_reserves || 0)} Total)</h4>
              <div className="space-y-2">
                {selectedCompYearData?.cash_breakdown?.length > 0 ? (
                  selectedCompYearData.cash_breakdown.map((item: any, idx: number) => (
                    <div key={idx} className="flex justify-between items-center p-2 rounded bg-blue-50 border border-blue-100">
                      <span className="text-sm font-medium text-blue-900">{item.name}</span>
                      <span className={`text-sm font-mono font-bold ${item.type === 'OUTFLOW' ? 'text-red-600' : 'text-blue-700'}`}>
                        {item.type === 'OUTFLOW' ? '-' : '+'}{formatCurrency(item.amount)}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="p-4 rounded-lg bg-gray-50 border border-dashed border-gray-300 text-center">
                    <p className="text-xs text-gray-400 italic">No change in the cash reserves for this year.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* NAV Trajectory Graph */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xl">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">NAV & Price per Unit Trajectory</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data.graph_data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                <XAxis dataKey="year" stroke="#374151" fontSize={12} tickLine={false} axisLine={false} interval={0} />
                <YAxis 
                  yAxisId="left" 
                  stroke="#374151" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  tickFormatter={(val) => val >= 1000000 ? `$${(val / 1000000).toFixed(1)}M` : `$${(val / 1000).toFixed(1)}k`} 
                />
                <YAxis 
                  yAxisId="right" 
                  orientation="right" 
                  stroke="#10b981" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  tickFormatter={(val) => `$${val.toFixed(2)}`} 
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: "#fff", border: "1px solid #e5e7eb", borderRadius: "8px" }} 
                  formatter={(value: any, name: any) => {
                    if (name === "Price per Unit") return [formatCurrencyWithDecimals(value), name];
                    return [formatCurrency(value), name];
                  }}
                />
                <Legend />
                <Area yAxisId="left" type="monotone" dataKey="portfolio_value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.1} name="Total NAV" />
                <Line yAxisId="right" type="monotone" dataKey="price_per_unit" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} name="Price per Unit" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* NAV Distribution Pie Chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xl">
          <h3 className="text-lg font-semibold text-gray-900 mb-6 text-center">NAV Distribution for {selectedCompYearData?.year}</h3>
          <div className="h-[300px]">
            <ReactECharts 
              option={{
                tooltip: { 
                  trigger: 'item', 
                  formatter: (params: any) => {
                    const val = formatCurrency(params.value);
                    return `<b>${params.seriesName}</b><br/>${params.name}: ${val} (${params.percent}%)`;
                  },
                  backgroundColor: 'rgba(255, 255, 255, 0.95)',
                  borderWidth: 0,
                  shadowBlur: 10,
                  shadowColor: 'rgba(0,0,0,0.1)',
                  textStyle: { color: '#1f2937' }
                },
                series: [
                  {
                    name: 'Category',
                    type: 'pie',
                    selectedMode: 'single',
                    radius: [0, '40%'],
                    label: { position: 'inner', fontSize: 11, color: '#fff', fontWeight: 'bold' },
                    labelLine: { show: false },
                    data: [
                      { 
                        name: 'Assets', 
                        value: selectedCompYearData?.assets_value || 0, 
                        itemStyle: { color: '#10b981' }
                      },
                      { 
                        name: 'Cash', 
                        value: selectedCompYearData?.cash_reserves || 0, 
                        itemStyle: { color: '#3b82f6' } 
                      }
                    ],
                    emphasis: {
                        focus: 'descendant',
                        itemStyle: { shadowBlur: 15, shadowColor: 'rgba(0, 0, 0, 0.4)' }
                    }
                  },
                  {
                    name: 'Composition',
                    type: 'pie',
                    radius: ['52%', '72%'],
                    labelLine: { length: 20 },
                    label: {
                      formatter: '{b|{b}}\n{d|{d}%}',
                      rich: {
                        b: { color: '#6b7280', fontSize: 10, lineHeight: 16 },
                        d: { color: '#374151', fontSize: 10, fontWeight: 'bold' }
                      }
                    },
                    data: [
                      ...(selectedCompYearData?.assets_breakdown?.map((a: any, idx: number) => {
                        const colors = [
                          '#10b981', // Emerald
                          '#059669', // Dark Emerald
                          '#34d399', // Light Emerald
                          '#047857', // Deeper Emerald
                          '#6ee7b7', // Pale Emerald
                          '#065f46', // Forest
                          '#a7f3d0'  // Mint
                        ];
                        return {
                          name: a.name,
                          value: a.value,
                          itemStyle: { 
                            color: colors[idx % colors.length],
                          }
                        };
                      }) || []),
                      { 
                        name: 'Cash Reserves', 
                        value: selectedCompYearData?.cash_reserves || 0, 
                        itemStyle: { color: '#eff6ff' },
                        label: { show: false }
                      }
                    ],
                    emphasis: {
                      focus: 'self',
                      itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.2)' }
                    }
                  }
                ]
              }}
              style={{ height: '100%', width: '100%' }}
            />
          </div>
        </div>
      </div>

      {/* Portfolio Ownership & Investor List */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h3 className="text-lg font-semibold text-gray-900">Portfolio Ownership & Investor List</h3>
        </div>
        <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
          {/* Ownership Pie Chart */}
          <div className="h-[300px]">
            <ReactECharts 
              option={{
                tooltip: { 
                  trigger: 'item', 
                  formatter: (params: any) => {
                    return `<b>${params.name}</b><br/>Ownership: ${params.value.toFixed(2)}%`;
                  }
                },
                series: [
                  {
                    name: 'Ownership',
                    type: 'pie',
                    radius: ['50%', '80%'],
                    avoidLabelOverlap: false,
                    itemStyle: {
                      borderRadius: 10,
                      borderColor: '#fff',
                      borderWidth: 2
                    },
                    label: {
                      show: false,
                      position: 'center'
                    },
                    emphasis: {
                      label: {
                        show: true,
                        fontSize: '18',
                        fontWeight: 'bold',
                        formatter: '{d}%'
                      }
                    },
                    labelLine: {
                      show: false
                    },
                    data: data.investors.map(inv => ({
                      name: `${inv.first_name} ${inv.last_name}`,
                      value: inv.ownership_percentage
                    }))
                  }
                ]
              }}
              style={{ height: '100%', width: '100%' }}
            />
          </div>
          
          {/* Investor List Table */}
          <div className="lg:col-span-2 overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-gray-600 text-xs uppercase tracking-wider">
                  <th className="px-4 py-3 font-semibold">Name</th>
                  <th className="px-4 py-3 font-semibold">Email</th>
                  <th className="px-4 py-3 font-semibold text-right">Units</th>
                  <th className="px-4 py-3 font-semibold text-right">Share %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.investors.map((investor, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-900 text-sm font-medium">
                      {investor.first_name} {investor.last_name}
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-sm">
                      {investor.email}
                    </td>
                    <td className="px-4 py-3 text-gray-900 text-sm text-right font-mono">
                      {formatNumber(investor.units)}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-mono text-emerald-600 font-bold">
                      {investor.ownership_percentage.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Investor Actions Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">Investor Actions</h3>
          {canEdit && (
            <button onClick={() => setShowModal(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
              + Add Action
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-gray-600 text-xs uppercase tracking-wider">
                <th className="px-6 py-4 font-semibold">Type</th>
                <th className="px-6 py-4 font-semibold">Investor</th>
                <th className="px-6 py-4 font-semibold">Year</th>
                <th className="px-6 py-4 font-semibold text-right">Amount</th>
                <th className="px-6 py-4 font-semibold text-right">Units</th>
                {canEdit && <th className="px-6 py-4 font-semibold text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {currentActions.map((action) => (
                <tr key={action.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${
                      action.type === 'PRIMARY_INVESTMENT' ? 'bg-emerald-100 text-emerald-700' :
                      action.type === 'SECONDARY_INVESTMENT' ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {action.type.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-900 text-sm">{action.investor_email}</td>
                  <td className="px-6 py-4 text-gray-900 text-sm">{action.year}</td>
                  <td className="px-6 py-4 text-gray-900 text-sm text-right font-mono">{action.amount ? formatCurrency(parseFloat(action.amount)) : '-'}</td>
                  <td className="px-6 py-4 text-gray-900 text-sm text-right font-mono">{formatNumber(parseFloat(action.units))}</td>
                  {canEdit && (
                    <td className="px-6 py-4 text-right">
                      <button onClick={() => handleDeleteAction(action.id)} className="text-red-600 hover:text-red-800 transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-center gap-2">
            {[...Array(totalPages)].map((_, i) => (
              <button key={i} onClick={() => setCurrentPage(i + 1)} className={`w-8 h-8 rounded-lg text-sm font-medium ${currentPage === i + 1 ? 'bg-emerald-600 text-white' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'}`}>
                {i + 1}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Possible Capital Sources Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">Possible Capital Sources</h3>
          {canEdit && (
            <button onClick={() => setShowSourceModal(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
              + Add Source
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-gray-600 text-xs uppercase tracking-wider">
                <th className="px-6 py-4 font-semibold">Name</th>
                <th className="px-6 py-4 font-semibold">Year</th>
                <th className="px-6 py-4 font-semibold text-right">Amount</th>
                {canEdit && <th className="px-6 py-4 font-semibold text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {currentSources.map((source) => (
                <tr key={source.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-gray-900 text-sm font-medium">{source.name}</td>
                  <td className="px-6 py-4 text-gray-900 text-sm">{source.year}</td>
                  <td className="px-6 py-4 text-gray-900 text-sm text-right font-mono">{formatCurrency(source.amount)}</td>
                  {canEdit && (
                    <td className="px-6 py-4 text-right">
                      <button onClick={() => handleSourceDelete(source.id)} className="text-red-600 hover:text-red-800 transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </td>
                  )}
                </tr>
              ))}
              {currentSources.length === 0 && (
                <tr>
                  <td colSpan={canEdit ? 4 : 3} className="px-6 py-8 text-center text-gray-400 italic">No possible capital sources found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {totalSourcePages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-center gap-2">
            {[...Array(totalSourcePages)].map((_, i) => (
              <button key={i} onClick={() => setCurrentSourcePage(i + 1)} className={`w-8 h-8 rounded-lg text-sm font-medium ${currentSourcePage === i + 1 ? 'bg-emerald-600 text-white' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'}`}>
                {i + 1}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Modal for adding action */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-900">Add Investor Action</h3>
              <button onClick={() => setShowModal(false)} className="text-gray-500 hover:text-gray-900">✕</button>
            </div>
            <form onSubmit={handleSubmitAction} className="p-6 space-y-4">
              <div className="space-y-2">
                <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Action Type</label>
                <select name="type" value={formData.type} onChange={handleInputChange} className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2">
                  <option value="PRIMARY_INVESTMENT">Primary Investment</option>
                  <option value="SECONDARY_EXIT">Secondary Exit</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Year</label>
                  <input type="number" name="year" value={formData.year} onChange={handleInputChange} className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2" />
                </div>
                {formData.type === "PRIMARY_INVESTMENT" && (
                  <div className="space-y-2">
                    <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Amount (USD)</label>
                    <input type="number" name="amount" step="0.01" value={formData.amount} onChange={handleInputChange} className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2" />
                  </div>
                )}
              </div>
              {formData.type === "PRIMARY_INVESTMENT" ? (
                <div className="space-y-2">
                  <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Investor</label>
                  <select name="investor" value={formData.investor} onChange={handleInputChange} className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2" required>
                    <option value="">Select Investor</option>
                    {investors.map(inv => <option key={inv.id} value={inv.id}>{inv.email}</option>)}
                  </select>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="space-y-2"><label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Investor Selling</label>
                    <select name="investor_selling" value={formData.investor_selling} onChange={handleInputChange} className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2" required>
                      <option value="">Select Seller</option>
                      {investors.map(inv => <option key={inv.id} value={inv.id}>{inv.email}</option>)}
                    </select>
                  </div>
                  <div className="space-y-2"><label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Investor Sold To</label>
                    <select name="investor_sold_to" value={formData.investor_sold_to} onChange={handleInputChange} className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2">
                      <option value="">Select Buyer (Optional)</option>
                      {investors.map(inv => <option key={inv.id} value={inv.id}>{inv.email}</option>)}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2"><label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Percentage Sold (%)</label>
                      <input type="number" step="0.0001" name="percentage_sold" value={formData.percentage_sold} onChange={handleInputChange} className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2" required />
                    </div>
                    <div className="space-y-2"><label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Discount (%)</label>
                      <input type="number" name="discount_percentage" step="0.0001" value={formData.discount_percentage} onChange={handleInputChange} className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2" />
                    </div>
                    <div className="space-y-2 col-span-2"><label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Price Sold At (USD)</label>
                      <input type="number" name="amount" step="0.01" value={formData.amount} onChange={handlePriceSoldAtChange} className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2" required />
                    </div>
                  </div>
                </div>
              )}
              <div className="pt-4 flex gap-4">
                <button type="submit" className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 rounded-xl shadow-md">Confirm Action</button>
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-xl">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal for adding/editing capital source */}
      {showSourceModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-900">Add Capital Source</h3>
              <button onClick={() => setShowSourceModal(false)} className="text-gray-500 hover:text-gray-900">✕</button>
            </div>
            <form onSubmit={handleSourceSubmit} className="p-6 space-y-4">
              <div className="space-y-2">
                <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Capital Source Name</label>
                <input type="text" name="name" value={sourceFormData.name} onChange={(e) => setSourceFormData(prev => ({ ...prev, name: e.target.value }))} className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2" required />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Amount (USD)</label>
                  <input type="number" name="amount" step="0.01" value={sourceFormData.amount} onChange={(e) => setSourceFormData(prev => ({ ...prev, amount: e.target.value }))} className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2" required />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Year</label>
                  <input type="number" name="year" value={sourceFormData.year} onChange={(e) => setSourceFormData(prev => ({ ...prev, year: parseInt(e.target.value) || 0 }))} className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2" required />
                </div>
              </div>
              <div className="pt-4 flex gap-4">
                <button type="submit" className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 rounded-xl shadow-md">Confirm Source</button>
                <button type="button" onClick={() => setShowSourceModal(false)} className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-xl">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};

export default REInvestorLogTab;
