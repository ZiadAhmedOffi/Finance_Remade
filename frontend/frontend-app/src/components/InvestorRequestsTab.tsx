import React, { useState, useEffect } from "react";
import { fundsApi } from "../api/api";
import "../pages/FundDashboard.css";

interface Holding {
  fund_id: string;
  fund_name: string;
  units_owned: number;
  ownership_percentage: number;
  price_per_unit: number;
  total_value: number;
  liquidity_index: number;
  is_locked: boolean;
  lockup_until: number;
  min_ticket: number;
}

interface Request {
  id: string;
  fund_name: string;
  type: string;
  status: string;
  requested_amount?: string;
  liquidation_percentage?: string;
  expected_value?: string;
  created_at: string;
}

interface Fund {
  id: string;
  name: string;
  model_inputs?: {
    min_investor_ticket: number;
  };
}

const InvestorRequestsTab: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"investment" | "liquidation">("investment");
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [availableFunds, setAvailableFunds] = useState<Fund[]>([]);
  const [requests, setRequests] = useState<Request[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form states
  const [selectedFundId, setSelectedFundId] = useState("");
  const [amount, setAmount] = useState("");
  const [liqPercentage, setLiqPercentage] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [holdingsRes, fundsRes, requestsRes] = await Promise.all([
        fundsApi.getMyHoldings(),
        fundsApi.getFunds(),
        fundsApi.getInvestorRequests(),
      ]);
      setHoldings(holdingsRes.data);
      setAvailableFunds(fundsRes.data);
      setRequests(requestsRes.data);
    } catch (err) {
      setError("Failed to fetch data.");
    } finally {
      setLoading(false);
    }
  };

  const handleInvestmentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFundId || !amount) return;

    const fund = availableFunds.find(f => f.id === selectedFundId);
    const minTicket = fund?.model_inputs?.min_investor_ticket || 0;
    
    if (parseFloat(amount) < minTicket) {
      if (!window.confirm(`Amount is below minimum ticket ($${minTicket.toLocaleString()}). Request might not be processed. Continue?`)) {
        return;
      }
    }

    try {
      setSubmitting(true);
      await fundsApi.createInvestorRequest({
        fund: selectedFundId,
        type: "INVESTMENT",
        requested_amount: amount
      });
      setSuccessMsg("Investment request submitted successfully!");
      fetchData(); // Refresh list
      setAmount("");
      setSelectedFundId("");
    } catch (err) {
      setError("Failed to submit investment request.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleLiquidationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFundId || !liqPercentage) return;

    const holding = holdings.find(h => h.fund_id === selectedFundId);
    if (!holding) return;

    if (parseFloat(liqPercentage) > 100) {
      setError("Liquidation percentage cannot exceed 100%");
      return;
    }

    const unitsToSell = holding.units_owned * (parseFloat(liqPercentage) / 100);
    const expectedValue = unitsToSell * holding.price_per_unit;

    try {
      setSubmitting(true);
      await fundsApi.createInvestorRequest({
        fund: selectedFundId,
        type: "LIQUIDATION",
        liquidation_percentage: liqPercentage,
        units_to_sell: unitsToSell.toFixed(4),
        expected_value: expectedValue.toFixed(2)
      });
      setSuccessMsg("Liquidation request submitted successfully!");
      fetchData();
      setLiqPercentage("");
      setSelectedFundId("");
    } catch (err) {
      setError("Failed to submit liquidation request.");
    } finally {
      setSubmitting(false);
    }
  };

  const getLIColor = (li: number) => {
    if (li >= 60) return "#10b981"; // Emerald
    if (li >= 40) return "#f59e0b"; // Orange
    return "#ef4444"; // Red
  };

  if (loading) return <div className="p-8 text-center">Loading Requests...</div>;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {error && <div className="alert alert-error mb-4">{error}</div>}
      {successMsg && <div className="alert alert-success mb-4">{successMsg}</div>}

      <div className="flex justify-center mb-8">
        <div className="bg-gray-100 p-1 rounded-xl flex">
          <button
            className={`px-6 py-2 rounded-lg font-bold transition-all ${activeTab === 'investment' ? 'bg-white shadow-sm text-blue-600' : 'text-gray-500'}`}
            onClick={() => { setActiveTab('investment'); setSelectedFundId(""); setError(null); }}
          >
            Invest
          </button>
          <button
            className={`px-6 py-2 rounded-lg font-bold transition-all ${activeTab === 'liquidation' ? 'bg-white shadow-sm text-red-600' : 'text-gray-500'}`}
            onClick={() => { setActiveTab('liquidation'); setSelectedFundId(""); setError(null); }}
          >
            Liquidate
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Form Section */}
        <div className="bg-white p-8 rounded-2xl border border-gray-200 shadow-xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
            {activeTab === 'investment' ? '🚀 New Investment' : '📉 Liquidation Request'}
          </h2>

          <form onSubmit={activeTab === 'investment' ? handleInvestmentSubmit : handleLiquidationSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">Select Fund</label>
              <select
                className="w-full p-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-blue-500 outline-none"
                value={selectedFundId}
                onChange={(e) => setSelectedFundId(e.target.value)}
                required
              >
                <option value="">-- Choose a Fund --</option>
                {activeTab === 'investment' 
                  ? availableFunds.map(f => (
                      <option key={f.id} value={f.id}>{f.name}</option>
                    ))
                  : holdings.map(h => (
                      <option key={h.fund_id} value={h.fund_id} disabled={h.is_locked}>
                        {h.fund_name} {h.is_locked ? "(LOCKUP)" : ""}
                      </option>
                    ))
                }
              </select>
            </div>

            {activeTab === 'investment' ? (
              <div>
                <label className="block text-sm font-bold text-gray-700 mb-2">Amount (USD)</label>
                <input
                  type="number"
                  className="w-full p-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="e.g. 50000"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  required
                />
                {selectedFundId && (
                  <p className="mt-2 text-sm text-gray-500">
                    Min Ticket: ${availableFunds.find(f => f.id === selectedFundId)?.model_inputs?.min_investor_ticket?.toLocaleString()}
                  </p>
                )}
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-2">Liquidation Percentage (%)</label>
                  <input
                    type="number"
                    className="w-full p-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-red-500 outline-none"
                    placeholder="e.g. 25"
                    value={liqPercentage}
                    onChange={(e) => setLiqPercentage(e.target.value)}
                    required
                    max="100"
                  />
                </div>
                {selectedFundId && liqPercentage && (
                  <div className="bg-gray-50 p-4 rounded-xl space-y-2 border border-dashed border-gray-300">
                    <div className="flex justify-between text-sm">
                      <span>Units to sell:</span>
                      <span className="font-bold">
                        {(holdings.find(h => h.fund_id === selectedFundId)!.units_owned * (parseFloat(liqPercentage) / 100)).toFixed(4)}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Expected value:</span>
                      <span className="font-bold text-emerald-600">
                        ${(holdings.find(h => h.fund_id === selectedFundId)!.units_owned * (parseFloat(liqPercentage) / 100) * holdings.find(h => h.fund_id === selectedFundId)!.price_per_unit).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </div>
                  </div>
                )}
              </>
            )}

            <button
              type="submit"
              disabled={submitting || !selectedFundId}
              className={`w-full py-4 rounded-xl font-bold text-white transition-all transform hover:scale-[1.02] active:scale-[0.98] ${
                activeTab === 'investment' ? 'bg-blue-600 hover:bg-blue-700 shadow-blue-200' : 'bg-red-600 hover:bg-red-700 shadow-red-200'
              } shadow-lg disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {submitting ? "Processing..." : `Submit ${activeTab === 'investment' ? 'Investment' : 'Liquidation'} Request`}
            </button>
          </form>
        </div>

        {/* Info / Previous Requests Section */}
        <div className="space-y-8">
          {/* Holdings Summary for Liquidation */}
          {activeTab === 'liquidation' && selectedFundId && (
             <div className="bg-gradient-to-br from-gray-800 to-gray-900 p-8 rounded-2xl text-white shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10 text-6xl">📉</div>
                <h3 className="text-xl font-bold mb-4">Fund Status</h3>
                {(() => {
                  const h = holdings.find(h => h.fund_id === selectedFundId)!;
                  return (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-gray-400 text-xs uppercase font-bold mb-1">Ownership</p>
                        <p className="text-2xl font-bold">{h.ownership_percentage.toFixed(2)}%</p>
                      </div>
                      <div>
                        <p className="text-gray-400 text-xs uppercase font-bold mb-1">Liquidity Index</p>
                        <p className="text-2xl font-bold" style={{ color: getLIColor(h.liquidity_index) }}>
                          {h.liquidity_index.toFixed(1)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-400 text-xs uppercase font-bold mb-1">Current Value</p>
                        <p className="text-2xl font-bold">${h.total_value.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-gray-400 text-xs uppercase font-bold mb-1">Lockup Status</p>
                        <p className={`text-xl font-bold ${h.is_locked ? 'text-red-400' : 'text-emerald-400'}`}>
                          {h.is_locked ? `Locked until ${h.lockup_until}` : "Unlocked"}
                        </p>
                      </div>
                    </div>
                  );
                })()}
             </div>
          )}

          {/* History Table */}
          <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-xl overflow-hidden">
            <h3 className="text-lg font-bold mb-4">Request History</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-gray-500">
                    <th className="pb-3">Type</th>
                    <th className="pb-3">Fund</th>
                    <th className="pb-3">Amount/Units</th>
                    <th className="pb-3 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {requests.length === 0 ? (
                    <tr><td colSpan={4} className="py-8 text-center text-gray-400">No requests yet</td></tr>
                  ) : (
                    requests.map(req => (
                      <tr key={req.id}>
                        <td className="py-4 font-medium">{req.type}</td>
                        <td className="py-4 text-gray-600">{req.fund_name}</td>
                        <td className="py-4 font-mono">
                          {req.type === 'INVESTMENT' ? `$${parseFloat(req.requested_amount!).toLocaleString()}` : `${req.liquidation_percentage}%`}
                        </td>
                        <td className="py-4 text-right">
                          <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                            req.status === 'APPROVED' ? 'bg-emerald-100 text-emerald-700' : 
                            req.status === 'REJECTED' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
                          }`}>
                            {req.status}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvestorRequestsTab;
