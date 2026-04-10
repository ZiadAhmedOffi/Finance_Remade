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

interface PossibleCapitalSource {
  id: string;
  name: string;
  amount: number;
  year: number;
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
    total_capital_with_possible: number;
    portfolio_value: number;
  }[];
  actions: InvestorAction[];
  possible_capital_sources: PossibleCapitalSource[];
  total_units: number;
}

interface InvestorLogTabProps {
  fundId: string;
  canEdit?: boolean;
}

const InvestorLogTab: React.FC<InvestorLogTabProps> = ({ fundId, canEdit }) => {
  const [data, setData] = useState<InvestorLogData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination for actions table
  const [currentPage, setCurrentPage] = useState(1);
  const actionsPerPage = 5;

  // Pagination for possible capital sources table
  const [currentSourcePage, setCurrentSourcePage] = useState(1);
  const sourcesPerPage = 5;

  // Form Modal state
  const [showModal, setShowModal] = useState(false);
  const [showSourceModal, setShowSourceModal] = useState(false);
  const [editingActionId, setEditingActionId] = useState<string | null>(null);
  const [editingSourceId, setEditingSourceId] = useState<string | null>(null);
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



  const [sourceFormData, setSourceFormData] = useState({
    name: "",
    amount: "",
    year: new Date().getFullYear(),
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

  const handleEdit = (action: any) => {
    setEditingActionId(action.id);
    setFormData({
      type: action.type,
      investor: action.investor || "",
      year: action.year,
      amount: action.amount || "",
      percentage_sold: action.percentage_sold || "",
      discount_percentage: action.discount_percentage || "0",
      investor_selling: action.investor_selling || "",
      investor_sold_to: action.investor_sold_to || "",
    });


    setShowModal(true);
  };

  const handleDelete = async (actionId: string) => {
    if (!window.confirm("Are you sure you want to delete this investor action?")) return;
    try {
      await fundsApi.deleteInvestorAction(actionId);
      fetchInvestorLog();
    } catch (err: any) {
      alert(err.response?.data?.error || "Failed to delete investor action.");
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

      if (editingActionId) {
        await fundsApi.updateInvestorAction(editingActionId, payload);
      } else {
        await fundsApi.createInvestorAction(payload);
      }
      
      setShowModal(false);
      setEditingActionId(null);
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
      alert(err.response?.data?.error || `Failed to ${editingActionId ? 'update' : 'create'} investor action.`);
    }
  };

  const handleSourceEdit = (source: PossibleCapitalSource) => {
    setEditingSourceId(source.id);
    setSourceFormData({
      name: source.name,
      year: source.year,
      amount: source.amount.toString(),
    });


    setShowSourceModal(true);
  };

  const handleSourceDelete = async (sourceId: string) => {
    if (!window.confirm("Are you sure you want to delete this capital source?")) return;
    try {
      await fundsApi.deleteCapitalSource(sourceId);
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
        amount: parseFloat(sourceFormData.amount),
        year: parseInt(sourceFormData.year.toString()),
      };

      if (editingSourceId) {
        await fundsApi.updateCapitalSource(editingSourceId, payload);
      } else {
        await fundsApi.createCapitalSource(fundId, payload);
      }
      
      setShowSourceModal(false);
      setEditingSourceId(null);
      fetchInvestorLog();
      // Reset form
      setSourceFormData({
        name: "",
        amount: "",
        year: new Date().getFullYear(),
      });


    } catch (err: any) {
      const errorData = err.response?.data;
      let errorMessage = `Failed to ${editingSourceId ? 'update' : 'create'} capital source.`;
      
      if (errorData) {
        if (typeof errorData === 'string') {
          errorMessage = errorData;
        } else if (errorData.error) {
          errorMessage = errorData.error;
        } else {
          // Handle nested validation errors (e.g. { year: ["..."] })
          const details = Object.entries(errorData)
            .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`)
            .join('\n');
          if (details) errorMessage += `\n\n${details}`;
        }
      }
      alert(errorMessage);
    }
  };

  const handleSourceInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSourceFormData(prev => ({ ...prev, [name]: value }));
  };

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

  // Helper for calculating price sold at
  const calculatePriceSoldAt = (percentage: number, portfolio: number, discount: number): number => {
    // Ensure percentage is treated as a fraction (e.g., 50% -> 0.50)
    const percentageAsFraction = percentage / 100;
    return percentageAsFraction * portfolio * (1 - (discount / 100));
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => {
      const nextState = { ...prev, [name]: value };
      
      // Automatically update amount if percentage, discount OR year changes for SECONDARY_EXIT
      if (nextState.type === "SECONDARY_EXIT" && (name === "percentage_sold" || name === "discount_percentage" || name === "year")) {
        const percentage = parseFloat(nextState.percentage_sold);
        const discount = parseFloat(nextState.discount_percentage);
        
        if (!isNaN(percentage) && !isNaN(discount) && !isNaN(fundPortfolioValue)) {
          const calculatedPrice = calculatePriceSoldAt(percentage, fundPortfolioValue, discount);
          nextState.amount = calculatedPrice.toFixed(2);
        }
      }
      return nextState;
    });


  };

  // Update discount when price sold at changes for SECONDARY_EXIT
  const handlePriceSoldAtChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPriceStr = e.target.value;
    const newPrice = parseFloat(newPriceStr);
    
    setFormData(prev => {
      const nextState = { ...prev, amount: newPriceStr };
      
      if (nextState.type === "SECONDARY_EXIT" && nextState.percentage_sold && !isNaN(newPrice) && !isNaN(fundPortfolioValue)) {
        const percentage = parseFloat(nextState.percentage_sold);
        const portfolio = fundPortfolioValue;
        
        if (percentage > 0 && portfolio > 0) {
          // Calculate discount: (1 - (price / (percentage/100 * portfolio))) * 100
          const calculatedDiscountPct = (1 - (newPrice / (percentage / 100 * portfolio))) * 100;
          
          // Use 4 decimal places for consistency with DB
          nextState.discount_percentage = calculatedDiscountPct.toFixed(4);
        }
      }
      return nextState;
    });


  };

  // Fetch fund portfolio value for calculations when year changes or on load
  const fetchFundPortfolioValue = useCallback(async (year: number) => {
    try {
      if (data?.graph_data) {
        const yearData = data.graph_data.find(d => d.year === year);
        const portfolioVal = yearData ? (yearData.portfolio_value || 0) : 0;
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

  // Fetch portfolio value when data loads or year changes (using year - 1 for calculations)
  useEffect(() => {
    fetchFundPortfolioValue(formData.year - 1);
  }, [data, formData.year, fetchFundPortfolioValue]);

  // Process graph data for surplus/deficit areas
  const processedGraphData = React.useMemo(() => {
    if (!data?.graph_data) return [];
    
    return data.graph_data.map(d => {
      const invested = d.total_capital_invested;
      const required = d.total_capital_required;
      const withPossible = d.total_capital_with_possible;

      let darkGreenArea: [number, number];
      let redArea: [number, number];
      let lightGreenArea: [number, number] = [invested, withPossible];

      if (invested > required) {
        darkGreenArea = [required, invested]; // Invested > Required surplus
        redArea = [required, required]; // No deficit
      } else { // required >= invested
        redArea = [invested, required]; // Required > Invested deficit
        darkGreenArea = [invested, invested]; // No surplus
      }

      return {
        ...d,
        darkGreenArea,
        redArea,
        lightGreenArea
      };
    });
  }, [data?.graph_data]);

  if (loading) return <div className="p-4 text-gray-400">Loading investor log...</div>;
  if (error) return <div className="p-4 text-red-500">{error}</div>;
  if (!data) return <div className="p-4 text-gray-400">No data available.</div>;

  // Pagination for actions table
  const actions = data.actions || [];
  const indexOfLastAction = currentPage * actionsPerPage;
  const indexOfFirstAction = indexOfLastAction - actionsPerPage;
  const currentActions = actions.slice(indexOfFirstAction, indexOfLastAction);
  const totalPages = Math.ceil(actions.length / actionsPerPage);

  const paginate = (pageNumber: number) => setCurrentPage(pageNumber);

  // Pagination for possible capital sources table
  const sources = data.possible_capital_sources || [];
  const indexOfLastSource = currentSourcePage * sourcesPerPage;
  const indexOfFirstSource = indexOfLastSource - sourcesPerPage;
  const currentSources = sources.slice(indexOfFirstSource, indexOfLastSource);
  const totalSourcePages = Math.ceil(sources.length / sourcesPerPage);

  const paginateSources = (pageNumber: number) => setCurrentSourcePage(pageNumber);


  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      {/* Metrics Summary (Total Units) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-xl flex flex-col items-center justify-center">
          <span className="text-gray-500 text-sm uppercase tracking-wider mb-2 font-medium">Total Fund Units</span>
          <span className="text-3xl font-bold text-emerald-600 font-mono">
            {formatNumber(data.total_units || 0)}
          </span>
        </div>
      </div>

      {/* Investors Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">Investor List</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-gray-600 text-xs uppercase tracking-wider">
                <th className="px-6 py-4 font-semibold">First Name</th>
                <th className="px-6 py-4 font-semibold">Last Name</th>
                <th className="px-6 py-4 font-semibold">Email</th>
                <th className="px-6 py-4 font-semibold text-right">Units Owned</th>
                <th className="px-6 py-4 font-semibold text-right">Ownership %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(data.investors || []).map((investor, idx) => (
                <tr key={idx} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-gray-900 text-sm">{investor.first_name}</td>
                  <td className="px-6 py-4 text-gray-900 text-sm">{investor.last_name}</td>
                  <td className="px-6 py-4 text-gray-600 text-sm">{investor.email}</td>
                  <td className="px-6 py-4 text-gray-900 text-sm text-right font-mono">
                    {formatNumber(investor.units)}
                  </td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-emerald-600 font-semibold">
                    {investor.ownership_percentage.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Investor Actions Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">Investor Actions</h3>
          {canEdit && (
            <button 
              onClick={() => {
                setEditingActionId(null);
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


                setShowModal(true);
              }}
              className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm"
            >
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
                <th className="px-6 py-4 font-semibold">Date</th>
                {canEdit && <th className="px-6 py-4 font-semibold text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {currentActions.map((action) => (
                <tr key={action.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${
                      action.type === 'PRIMARY_INVESTMENT' ? 'bg-emerald-100 text-emerald-700' :
                      action.type === 'SECONDARY_INVESTMENT' ? 'bg-blue-100 text-blue-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {action.type.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-900 text-sm">{action.investor_email}</td>
                  <td className="px-6 py-4 text-gray-900 text-sm">{action.year}</td>
                  <td className="px-6 py-4 text-gray-900 text-sm text-right font-mono">
                    {action.amount ? formatCurrency(parseFloat(action.amount)) : '-'}
                  </td>
                  <td className="px-6 py-4 text-gray-900 text-sm text-right font-mono">
                    {formatNumber(parseFloat(action.units))}
                  </td>
                  <td className="px-6 py-4 text-gray-500 text-xs">
                    {new Date(action.created_at).toLocaleDateString()}
                  </td>
                  {canEdit && (
                    <td className="px-6 py-4 text-right space-x-2">
                      <button 
                        onClick={() => handleEdit(action)}
                        className="text-blue-600 hover:text-blue-800 transition-colors"
                        title="Edit Action"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button 
                        onClick={() => handleDelete(action.id)}
                        className="text-red-600 hover:text-red-800 transition-colors"
                        title="Delete Action"
                      >
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
        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-center gap-2">
            {[...Array(totalPages)].map((_, i) => (
              <button
                key={i}
                onClick={() => paginate(i + 1)}
                className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                  currentPage === i + 1 ? 'bg-emerald-600 text-white' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                }`}
              >
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
            <button 
              onClick={() => {
                setEditingSourceId(null);
                setSourceFormData({
                  name: "",
                  amount: "",
                  year: new Date().getFullYear(),
                });


                setShowSourceModal(true);
              }}
              className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm"
            >
              + Add Capital Source
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-gray-600 text-xs uppercase tracking-wider">
                <th className="px-6 py-4 font-semibold">Capital Source Name</th>
                <th className="px-6 py-4 font-semibold text-right">Amount (USD)</th>
                <th className="px-6 py-4 font-semibold text-center">Year of Intent</th>
                <th className="px-6 py-4 font-semibold">Date Added</th>
                {canEdit && <th className="px-6 py-4 font-semibold text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {currentSources.map((source) => (
                <tr key={source.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-gray-900 text-sm font-medium">{source.name}</td>
                  <td className="px-6 py-4 text-gray-900 text-sm text-right font-mono">
                    {formatCurrency(source.amount)}
                  </td>
                  <td className="px-6 py-4 text-gray-900 text-sm text-center">{source.year}</td>
                  <td className="px-6 py-4 text-gray-500 text-xs">
                    {new Date(source.created_at).toLocaleDateString()}
                  </td>
                  {canEdit && (
                    <td className="px-6 py-4 text-right space-x-2">
                      <button 
                        onClick={() => handleSourceEdit(source)}
                        className="text-blue-600 hover:text-blue-800 transition-colors"
                        title="Edit Source"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button 
                        onClick={() => handleSourceDelete(source.id)}
                        className="text-red-600 hover:text-red-800 transition-colors"
                        title="Delete Source"
                      >
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
                  <td colSpan={canEdit ? 5 : 4} className="px-6 py-8 text-center text-gray-400 italic">
                    No possible capital sources found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {/* Pagination Controls */}
        {totalSourcePages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-center gap-2">
            {[...Array(totalSourcePages)].map((_, i) => (
              <button
                key={i}
                onClick={() => paginateSources(i + 1)}
                className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                  currentSourcePage === i + 1 ? 'bg-emerald-600 text-white' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
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
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-900">{editingActionId ? 'Edit' : 'Add'} Investor Action</h3>
              <button onClick={() => setShowModal(false)} className="text-gray-500 hover:text-gray-900">✕</button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="space-y-2">
                <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Action Type</label>
                <select 
                  name="type" 
                  value={formData.type} 
                  onChange={handleInputChange}
                  className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                >
                  <option value="PRIMARY_INVESTMENT">Primary Investment</option>
                  <option value="SECONDARY_EXIT">Secondary Exit</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Year</label>
                  <input 
                    type="number" 
                    name="year" 
                    value={formData.year} 
                    onChange={handleInputChange}
                    className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                  />
                </div>
                {formData.type === "PRIMARY_INVESTMENT" && (
                  <div className="space-y-2">
                    <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Amount (USD)</label>
                    <input 
                      type="number" 
                      name="amount" 
                      step="0.01"
                      value={formData.amount} 
                      onChange={handleInputChange}
                      className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                    />
                  </div>
                )}
              </div>

              {formData.type === "PRIMARY_INVESTMENT" ? (
                <div className="space-y-2">
                  <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Investor</label>
                  <select 
                    name="investor" 
                    value={formData.investor} 
                    onChange={handleInputChange}
                    className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                    required
                  >
                    <option value="">Select Investor</option>
                    {investors.map(inv => <option key={inv.id} value={inv.id}>{inv.email}</option>)}
                  </select>
                </div>
              ) : ( // Secondary Exit
                <div className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Investor Selling</label>
                    <select 
                      name="investor_selling" 
                      value={formData.investor_selling} 
                      onChange={handleInputChange}
                      className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                      required
                    >
                      <option value="">Select Seller</option>
                      {investors.map(inv => <option key={inv.id} value={inv.id}>{inv.email}</option>)}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Investor Sold To</label>
                    <select 
                      name="investor_sold_to" 
                      value={formData.investor_sold_to} 
                      onChange={handleInputChange}
                      className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                    >
                      <option value="">Select Buyer (Optional)</option>
                      {investors.map(inv => <option key={inv.id} value={inv.id}>{inv.email}</option>)}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Percentage Sold (%)</label>
                      <input 
                        type="number" 
                        step="0.0001"
                        name="percentage_sold" 
                        value={formData.percentage_sold} 
                        onChange={handleInputChange}
                        className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Discount (%)</label>
                      <input 
                        type="number" 
                        name="discount_percentage" 
                        step="0.0001"
                        value={formData.discount_percentage} 
                        onChange={handleInputChange}
                        className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                      />
                    </div>
                    <div className="space-y-2 col-span-2">
                      <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Price Sold At (USD)</label>
                      <input 
                        type="number" 
                        name="amount" 
                        step="0.01"
                        value={formData.amount} 
                        onChange={handlePriceSoldAtChange} // Use dedicated handler for price calculation
                        className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                        required
                      />
                    </div>
                  </div>
                </div>
              )}

              <div className="pt-4 flex gap-4">
                <button 
                  type="submit"
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 rounded-xl transition-all shadow-md"
                >
                  Confirm Action
                </button>
                <button 
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-xl transition-all"
                >
                  Cancel
                </button>
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
              <h3 className="text-lg font-semibold text-gray-900">{editingSourceId ? 'Edit' : 'Add'} Capital Source</h3>
              <button onClick={() => setShowSourceModal(false)} className="text-gray-500 hover:text-gray-900">✕</button>
            </div>
            <form onSubmit={handleSourceSubmit} className="p-6 space-y-4">
              <div className="space-y-2">
                <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Capital Source Name</label>
                <input 
                  type="text" 
                  name="name" 
                  value={sourceFormData.name} 
                  onChange={handleSourceInputChange}
                  className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                  placeholder="e.g. Pension Fund A"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Amount (USD)</label>
                  <input 
                    type="number" 
                    name="amount" 
                    step="0.01"
                    value={sourceFormData.amount} 
                    onChange={handleSourceInputChange}
                    className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Year of Intent</label>
                  <input 
                    type="number" 
                    name="year" 
                    min={new Date().getFullYear()}
                    value={sourceFormData.year} 
                    onChange={handleSourceInputChange}
                    className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                    required
                  />
                </div>
              </div>

              <div className="pt-4 flex gap-4">
                <button 
                  type="submit"
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 rounded-xl transition-all shadow-md"
                >
                  Confirm Source
                </button>
                <button 
                  type="button"
                  onClick={() => setShowSourceModal(false)}
                  className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-xl transition-all"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Comparison Graph */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">Capital Invested vs. Capital Required</h3>
        <div className="h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={processedGraphData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
              <XAxis dataKey="year" stroke="#374151" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#374151" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `$${(val / 1000000).toFixed(0)}M`} />
              <Tooltip contentStyle={{ backgroundColor: "#fff", border: "1px solid #e5e7eb", borderRadius: "8px", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)" }} itemStyle={{ fontSize: "12px", color: "#111827" }} formatter={(value: any, name: any) => [formatCurrency(value), name]} />
              <Legend verticalAlign="top" height={36} iconType="circle" />
              
              {/* Red: Required > Invested */}
              <Area type="monotone" dataKey="redArea" stroke="none" fill="#ef4444" fillOpacity={0.4} name="Deficit (Required > Invested)" legendType="none" tooltipType="none" />
              
              {/* Dark Green: Invested > Required */}
              <Area type="monotone" dataKey="darkGreenArea" stroke="none" fill="#065f46" fillOpacity={0.6} name="Surplus (Invested > Required)" legendType="none" tooltipType="none" />
              
              {/* Light Green: Possible Sources Area */}
              <Area type="monotone" dataKey="lightGreenArea" stroke="none" fill="#10b981" fillOpacity={0.3} name="Possible Capital Area" legendType="none" tooltipType="none" />

              <Line type="monotone" dataKey="total_capital_invested" stroke="#10b981" strokeWidth={3} dot={{ r: 4, fill: "#10b981" }} activeDot={{ r: 6 }} name="Total Capital Invested" />
              <Line type="monotone" dataKey="total_capital_with_possible" stroke="#10b981" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 3, fill: "#10b981" }} activeDot={{ r: 5 }} name="Total + Possible Sources" />
              <Line type="monotone" dataKey="total_capital_required" stroke="#3b82f6" strokeWidth={3} dot={{ r: 4, fill: "#3b82f6" }} activeDot={{ r: 6 }} name="Total Capital Required" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Automatic Status Suggestion */}
      {data.graph_data && data.graph_data.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xl animate-in slide-in-from-bottom-4 duration-700">
          <div className="flex items-center gap-4">
            <div className="flex-shrink-0">
              {(() => {
                const latest = data.graph_data[data.graph_data.length - 1];
                const invested = latest.total_capital_invested;
                const required = latest.total_capital_required;
                const withPossible = latest.total_capital_with_possible;

                if (required > withPossible) {
                  return (
                    <div className="p-3 bg-red-100 rounded-full">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                    </div>
                  );
                } else if (required > invested || withPossible >= 1.5 * invested) {
                  return (
                    <div className="p-3 bg-amber-100 rounded-full">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  );
                } else {
                  return (
                    <div className="p-3 bg-emerald-100 rounded-full">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  );
                }
              })()}
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Strategic Recommendation</h4>
              <p className="text-lg font-medium text-gray-900 mt-1">
                {(() => {
                  const latest = data.graph_data[data.graph_data.length - 1];
                  const invested = latest.total_capital_invested;
                  const required = latest.total_capital_required;
                  const withPossible = latest.total_capital_with_possible;

                  if (required > withPossible) {
                    return <span className="text-red-600 font-bold">The fund needs to restructure its investment strategy and capital allocation plans.</span>;
                  } else if (required > invested || withPossible >= 1.5 * invested) {
                    return <span className="text-amber-600 font-bold">The fund needs to work more on closing deals with investors.</span>;
                  } else {
                    return <span className="text-emerald-600 font-bold">The fund is currently in a healthy status.</span>;
                  }
                })()}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InvestorLogTab;
