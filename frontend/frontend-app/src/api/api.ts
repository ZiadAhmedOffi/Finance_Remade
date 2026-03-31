import axios from "axios";

// Priority: Environment Variable (Vercel/Production), then local default
// Using a relative path if possible, or protocol-relative to avoid mixed content
const API_BASE = import.meta.env.VITE_API_BASE_URL || (window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1") 
  ? "http://127.0.0.1:8000/api" 
  : "/api"); 

const api = axios.create({
  baseURL: API_BASE,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const fundsApi = {
  getFunds: () => api.get("/funds/"),
  getFund: (id: string) => api.get(`/funds/${id}/`),
  updateFund: (id: string, data: any) => api.put(`/funds/${id}/`, data),
  getFundLogs: (id: string) => api.get(`/funds/${id}/logs/`),
  
  getModelInputs: (fundId: string) => api.get(`/funds/${fundId}/model-inputs/`),
  updateModelInputs: (fundId: string, data: any) => api.put(`/funds/${fundId}/model-inputs/`, data),
  
  getDeals: (fundId: string) => api.get(`/funds/${fundId}/deals/`),
  createDeal: (fundId: string, data: any) => api.post(`/funds/${fundId}/deals/`, data),
  updateDeal: (fundId: string, dealId: string, data: any) => api.put(`/funds/${fundId}/deals/${dealId}/`, data),
  deleteDeal: (fundId: string, dealId: string) => api.delete(`/funds/${fundId}/deals/${dealId}/`),

  getCurrentDeals: (fundId: string) => api.get(`/funds/${fundId}/current-deals/`),
  createCurrentDeal: (fundId: string, data: any) => api.post(`/funds/${fundId}/current-deals/`, data),
  updateCurrentDeal: (fundId: string, dealId: string, data: any) => api.put(`/funds/${fundId}/current-deals/${dealId}/`, data),
  deleteCurrentDeal: (fundId: string, dealId: string) => api.delete(`/funds/${fundId}/current-deals/${dealId}/`),

  getInvestmentRounds: (fundId: string, companyName?: string) => {
    const params = companyName ? { company_name: companyName } : {};
    return api.get(`/funds/${fundId}/investment-rounds/`, { params });
  },
  createInvestmentRound: (fundId: string, data: any) => api.post(`/funds/${fundId}/investment-rounds/`, data),
  updateInvestmentRound: (fundId: string, roundId: string, data: any) => api.put(`/funds/${fundId}/investment-rounds/${roundId}/`, data),
  deleteInvestmentRound: (fundId: string, roundId: string) => api.delete(`/funds/${fundId}/investment-rounds/${roundId}/`),
  getFundPerformance: (fundId: string) => api.get(`/funds/${fundId}/performance/`),

  getRiskAssessments: (fundId: string) => api.get(`/funds/${fundId}/risk-assessments/`),
  saveRiskAssessments: (fundId: string, data: any[]) => api.post(`/funds/${fundId}/risk-assessments/`, data),
  getInvestorLog: (fundId: string) => api.get(`/funds/${fundId}/investor-log/`),

  // Investor Dashboard & Actions
  getInvestors: () => api.get("/funds/investors/"),
  getInvestorActions: () => api.get("/funds/investor-actions/"),
  createInvestorAction: (data: any) => api.post("/funds/investor-actions/", data),
  updateInvestorAction: (actionId: string, data: any) => api.put(`/funds/investor-actions/${actionId}/`, data),
  deleteInvestorAction: (actionId: string) => api.delete(`/funds/investor-actions/${actionId}/`),
  getInvestorDashboard: (investorId?: string) => {
    const params = investorId ? { investor_id: investorId } : {};
    return api.get("/funds/investor-dashboard/", { params });
  },
};

export { api };
