import React, { useState, useEffect, useCallback } from "react";
import { fundsApi } from "../api/api";

interface Distribution {
  id: string;
  fund: string;
  amount: string;
  date: string;
  type: "DIVIDEND" | "EXIT";
  allocated: boolean;
  created_at: string;
}

interface Investor {
  first_name: string;
  last_name: string;
  email: string;
  dividend_treatment: string;
}

interface DistributionsTabProps {
  fundId: string;
  canEdit?: boolean;
}

const DistributionsTab: React.FC<DistributionsTabProps> = ({ fundId, canEdit }) => {
  const [distributions, setDistributions] = useState<Distribution[]>([]);
  const [investors, setInvestors] = useState<Investor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [showAllocateModal, setShowAllocateModal] = useState(false);
  const [selectedDist, setSelectedDist] = useState<Distribution | null>(null);
  
  const [formData, setFormData] = useState({
    amount: "",
    date: new Date().toISOString().split('T')[0],
    type: "DIVIDEND"
  });

  const fetchDistributions = useCallback(async () => {
    try {
      setLoading(true);
      const [distRes, logRes] = await Promise.all([
        fundsApi.getDistributions(fundId),
        fundsApi.getInvestorLog(fundId)
      ]);
      setDistributions(distRes.data);
      setInvestors(logRes.data.investors || []);
      setError(null);
    } catch (err) {
      setError("Failed to load data.");
    } finally {
      setLoading(false);
    }
  }, [fundId]);

  useEffect(() => {
    fetchDistributions();
  }, [fetchDistributions]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fundsApi.createDistribution(fundId, {
        ...formData,
        amount: parseFloat(formData.amount),
        fund: fundId
      });
      setShowModal(false);
      fetchDistributions();
    } catch (err: any) {
      alert(err.response?.data?.error || "Failed to create distribution.");
    }
  };

  const handleAllocate = async () => {
    if (!selectedDist) return;
    try {
      await fundsApi.allocateDistribution(selectedDist.id);
      alert("Distribution allocated successfully!");
      setShowAllocateModal(false);
      fetchDistributions();
    } catch (err: any) {
      alert(err.response?.data?.error || "Failed to allocate distribution.");
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure? This will also delete all associated investor actions if already allocated.")) return;
    try {
      await fundsApi.deleteDistribution(id);
      fetchDistributions();
    } catch (err) {
      alert("Failed to delete distribution.");
    }
  };

  if (loading) return <div className="p-4 text-gray-400">Loading distributions...</div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Investor Preferences Summary */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h3 className="text-md font-semibold text-gray-700">Investor Dividend Preferences</h3>
          <p className="text-[10px] text-gray-500 uppercase tracking-tighter">Current configuration for pro-rata distributions</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-200 bg-white text-gray-400 text-[10px] uppercase font-bold">
                <th className="px-6 py-3">Investor</th>
                <th className="px-6 py-3">Email</th>
                <th className="px-6 py-3 text-center">Preference</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {investors.map((inv, idx) => (
                <tr key={idx} className="hover:bg-gray-50/50">
                  <td className="px-6 py-3 text-sm text-gray-700">{inv.first_name} {inv.last_name}</td>
                  <td className="px-6 py-3 text-sm text-gray-500 font-mono">{inv.email}</td>
                  <td className="px-6 py-3 text-center">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      inv.dividend_treatment === 'CASH' ? 'bg-blue-50 text-blue-600' :
                      inv.dividend_treatment === 'REINVEST' ? 'bg-emerald-50 text-emerald-600' :
                      'bg-gray-100 text-gray-500'
                    }`}>
                      {inv.dividend_treatment}
                    </span>
                  </td>
                </tr>
              ))}
              {investors.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-6 py-8 text-center text-gray-400 italic text-sm">No investors found for this fund.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">Fund Distributions</h3>
          {canEdit && (
            <button 
              onClick={() => {
                setFormData({ amount: "", date: new Date().toISOString().split('T')[0], type: "DIVIDEND" });
                setShowModal(true);
              }}
              className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm"
            >
              + Record Distribution
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-gray-600 text-xs uppercase tracking-wider">
                <th className="px-6 py-4 font-semibold">Date</th>
                <th className="px-6 py-4 font-semibold">Type</th>
                <th className="px-6 py-4 font-semibold text-right">Total Amount</th>
                <th className="px-6 py-4 font-semibold text-center">Status</th>
                {canEdit && <th className="px-6 py-4 font-semibold text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {distributions.map((dist) => (
                <tr key={dist.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-gray-900 text-sm">{dist.date}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${
                      dist.type === 'DIVIDEND' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'
                    }`}>
                      {dist.type}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-900 text-sm text-right font-mono">
                    ${parseFloat(dist.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4 text-center">
                    {dist.allocated ? (
                      <span className="px-2 py-1 rounded-full text-[10px] font-bold uppercase bg-emerald-100 text-emerald-700">Allocated</span>
                    ) : (
                      <span className="px-2 py-1 rounded-full text-[10px] font-bold uppercase bg-amber-100 text-amber-700">Pending Allocation</span>
                    )}
                  </td>
                  {canEdit && (
                    <td className="px-6 py-4 text-right space-x-2">
                      {!dist.allocated && (
                        <button 
                          onClick={() => { setSelectedDist(dist); setShowAllocateModal(true); }}
                          className="text-emerald-600 hover:text-emerald-800 text-sm font-bold uppercase tracking-tighter"
                        >
                          Allocate
                        </button>
                      )}
                      <button 
                        onClick={() => handleDelete(dist.id)}
                        className="text-red-600 hover:text-red-800 transition-colors"
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
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-900">Record Fund Distribution</h3>
              <button onClick={() => setShowModal(false)} className="text-gray-500 hover:text-gray-900">✕</button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="space-y-2">
                <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Amount (USD)</label>
                <input 
                  type="number" 
                  step="0.01"
                  value={formData.amount} 
                  onChange={(e) => setFormData({...formData, amount: e.target.value})}
                  className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Date</label>
                <input 
                  type="date" 
                  value={formData.date} 
                  onChange={(e) => setFormData({...formData, date: e.target.value})}
                  className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Type</label>
                <select 
                  value={formData.type} 
                  onChange={(e) => setFormData({...formData, type: e.target.value as any})}
                  className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                >
                  <option value="DIVIDEND">Dividend</option>
                  <option value="EXIT">Exit Proceed</option>
                </select>
              </div>
              <div className="pt-4 flex gap-4">
                <button type="submit" className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 rounded-xl transition-all shadow-md">Confirm</button>
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-xl transition-all">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showAllocateModal && selectedDist && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-900">Allocation Preview</h3>
              <button onClick={() => setShowAllocateModal(false)} className="text-gray-500 hover:text-gray-900">✕</button>
            </div>
            <div className="p-6">
              <p className="text-sm text-gray-600 mb-4">
                You are about to allocate <strong>${parseFloat(selectedDist.amount).toLocaleString()}</strong> to investors pro-rata based on units held on <strong>{selectedDist.date}</strong>.
              </p>
              
              <div className="bg-amber-50 border border-amber-200 p-4 rounded-lg mb-6 text-xs text-amber-800">
                <strong>Note:</strong> Reinvestments will be calculated based on the fund's NAV and Price Per Unit at the distribution date.
              </div>

              <div className="flex gap-4 pt-4 border-t border-gray-100">
                <button 
                  onClick={handleAllocate}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 rounded-xl transition-all shadow-md"
                >
                  Confirm Allocation
                </button>
                <button 
                  onClick={() => setShowAllocateModal(false)}
                  className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 rounded-xl transition-all"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DistributionsTab;
