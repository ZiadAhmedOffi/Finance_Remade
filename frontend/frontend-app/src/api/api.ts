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
};

export { api };
