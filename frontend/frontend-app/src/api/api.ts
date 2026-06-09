import axios from "axios";
import { createDPoPProof } from "../utils/dpopUtils";

// Priority: Environment Variable (Vercel/Production), then local default
// Using a relative path if possible, or protocol-relative to avoid mixed content
const API_BASE = import.meta.env.VITE_API_BASE_URL || (window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1") 
  ? "http://127.0.0.1:8000/api" 
  : "/api"); 

const api = axios.create({
  baseURL: API_BASE,
});

const publicApi = axios.create({
  baseURL: API_BASE,
});

// Interceptor for private api...
api.interceptors.request.use(
  async (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers["Authorization"] = `DPoP ${token}`;
    }
    
    // Attach DPoP Proof
    try {
      const fullUrl = config.baseURL ? `${config.baseURL}${config.url}` : config.url || "";
      const proof = await createDPoPProof(config.method || "GET", fullUrl);
      config.headers["DPoP"] = proof;
    } catch (e) {
      console.error("Failed to generate DPoP proof", e);
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status } = error.response;
      if (status === 401 || status === 403) {
        // Only redirect if not already on login or error page
        if (!window.location.pathname.includes("/login") && !window.location.pathname.includes("/error")) {
          window.location.href = `/error?code=${status}&message=${encodeURIComponent(error.response.data.error || "Access Denied")}`;
        }
      }
    }
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
  
  // Excel Operations
  downloadExcelTemplate: (fundId: string) => api.get(`/funds/${fundId}/excel-template/`, { responseType: 'blob' }),
  uploadExcelData: (fundId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/funds/${fundId}/excel-ingest/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  getRiskAssessments: (fundId: string) => api.get(`/funds/${fundId}/risk-assessments/`),
  saveRiskAssessments: (fundId: string, data: any[]) => api.post(`/funds/${fundId}/risk-assessments/`, data),
  getInvestorLog: (fundId: string) => api.get(`/funds/${fundId}/investor-log/`),

  // Capital Sources
  getCapitalSources: (fundId: string) => api.get(`/funds/${fundId}/capital-sources/`),
  createCapitalSource: (fundId: string, data: any) => api.post(`/funds/${fundId}/capital-sources/`, data),
  updateCapitalSource: (sourceId: string, data: any) => api.put(`/funds/capital-sources/${sourceId}/`, data),
  deleteCapitalSource: (sourceId: string) => api.delete(`/funds/capital-sources/${sourceId}/`),

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

  // Reports
  getReports: () => api.get("/funds/reports/"),
  createReport: (data: any) => api.post("/funds/reports/", data),
  updateReport: (id: string, data: any) => api.patch(`/funds/reports/${id}/`, data),
  deleteReport: (id: string) => api.delete(`/funds/reports/${id}/`),
  regenerateReport: (id: string) => api.post(`/funds/reports/${id}/regenerate/`),
  getPublicReport: (slug: string) => publicApi.get(`/funds/reports/public/${slug}/`),

  getCapitalCallReports: () => api.get("/funds/capital-call-reports/"),
  createCapitalCallReport: (data: any) => api.post("/funds/capital-call-reports/", data),
  updateCapitalCallReport: (id: string, data: any) => api.patch(`/funds/capital-call-reports/${id}/`, data),
  deleteCapitalCallReport: (id: string) => api.delete(`/funds/capital-call-reports/${id}/`),

  // Investor Requests
  getInvestorRequests: () => api.get("/funds/requests/"),
  createInvestorRequest: (data: any) => api.post("/funds/requests/", data),
  getMyHoldings: () => api.get("/funds/my-holdings/"),
};

export const realEstateApi = {
  getPortfolios: () => api.get("/real-estate/"),
  getPortfolio: (id: string) => api.get(`/real-estate/${id}/`),
  getDashboard: (id: string, referenceDate?: string) => {
    const params = referenceDate ? { reference_date: referenceDate } : {};
    return api.get(`/real-estate/${id}/dashboard/`, { params });
  },
  createPortfolio: (data: any) => api.post("/real-estate/", data),
  updatePortfolio: (id: string, data: any) => api.patch(`/real-estate/${id}/`, data),
  getAssumptions: (id: string) => api.get(`/real-estate/${id}/assumptions/`),
  updateAssumptions: (id: string, data: any) => api.patch(`/real-estate/${id}/assumptions/`, data),
  
  getProperties: (portfolioId: string, referenceDate?: string) => {
    const params = referenceDate ? { reference_date: referenceDate } : {};
    return api.get(`/real-estate/${portfolioId}/properties/`, { params });
  },
  createProperty: (portfolioId: string, data: any) => api.post(`/real-estate/${portfolioId}/properties/`, data),
  updateProperty: (portfolioId: string, propertyId: string, data: any) => 
    api.patch(`/real-estate/${portfolioId}/properties/${propertyId}/`, data),
  deleteProperty: (portfolioId: string, propertyId: string) => 
    api.delete(`/real-estate/${portfolioId}/properties/${propertyId}/`),

  getFinancing: (portfolioId: string) => api.get(`/real-estate/${portfolioId}/financing/`),
  createFinancing: (portfolioId: string, data: any) => api.post(`/real-estate/${portfolioId}/financing/`, data),
  updateFinancing: (portfolioId: string, entryId: string, data: any) => 
    api.patch(`/real-estate/${portfolioId}/financing/${entryId}/`, data),
  deleteFinancing: (portfolioId: string, entryId: string) => 
    api.delete(`/real-estate/${portfolioId}/financing/${entryId}/`),
  getPortfolioAmortization: (portfolioId: string) => 
    api.get(`/real-estate/${portfolioId}/financing/amortization-total/`),
  getEntryAmortization: (portfolioId: string, entryId: string) => 
    api.get(`/real-estate/${portfolioId}/financing/${entryId}/amortization/`),

  // Installment Endpoints
  createInstallment: (portfolioId: string, data: any) => api.post(`/real-estate/${portfolioId}/installments/`, data),
  updateInstallment: (portfolioId: string, installmentId: string, data: any) => 
    api.patch(`/real-estate/${portfolioId}/installments/${installmentId}/`, data),
  deleteInstallment: (portfolioId: string, installmentId: string) => 
    api.delete(`/real-estate/${portfolioId}/installments/${installmentId}/`),
  getPortfolioInstallmentsSchedule: (portfolioId: string) => 
    api.get(`/real-estate/${portfolioId}/installments-schedule-total/`),
  getEntryInstallmentsSchedule: (portfolioId: string, installmentId: string) => 
    api.get(`/real-estate/${portfolioId}/installments/${installmentId}/schedule/`),

  getOffPlanModel: (portfolioId: string) => api.get(`/real-estate/${portfolioId}/off-plan/`),
  updateOffPlanDetails: (portfolioId: string, propertyId: string, data: any) => 
    api.patch(`/real-estate/${portfolioId}/off-plan/${propertyId}/details/`, data),
  getOffPlanSchedule: (portfolioId: string, propertyId: string) => 
    api.get(`/real-estate/${portfolioId}/off-plan/${propertyId}/schedule/`),
  createOffPlanMilestone: (portfolioId: string, propertyId: string, data: any) =>
    api.post(`/real-estate/${portfolioId}/off-plan/${propertyId}/schedule/`, data),
  updateOffPlanMilestone: (portfolioId: string, milestoneId: string, data: any) => 
    api.patch(`/real-estate/${portfolioId}/off-plan/milestones/${milestoneId}/`, data),
  deleteOffPlanMilestone: (portfolioId: string, milestoneId: string) =>
    api.delete(`/real-estate/${portfolioId}/off-plan/milestones/${milestoneId}/`),


  getCashFlow: (portfolioId: string, startYear?: number, endYear?: number) => {
    const params: any = {};
    if (startYear) params.start_year = startYear;
    if (endYear) params.end_year = endYear;
    return api.get(`/real-estate/${portfolioId}/cash-flow/`, { params });
  },

  getSales: (portfolioId: string) => api.get(`/real-estate/${portfolioId}/sales/`),
  createSale: (portfolioId: string, data: any) => api.post(`/real-estate/${portfolioId}/sales/`, data),
  updateSale: (portfolioId: string, saleId: string, data: any) => 
    api.patch(`/real-estate/${portfolioId}/sales/${saleId}/`, data),
  deleteSale: (portfolioId: string, saleId: string) => 
    api.delete(`/real-estate/${portfolioId}/sales/${saleId}/`),

  // Investor Log Endpoints
  getInvestorLog: (portfolioId: string) => api.get(`/real-estate/${portfolioId}/investor-log/`),
  getInvestors: (portfolioId: string) => api.get(`/real-estate/${portfolioId}/investors/`),
  getInvestorActions: (portfolioId: string) => api.get(`/real-estate/${portfolioId}/investor-actions/`),
  createInvestorAction: (portfolioId: string, data: any) => api.post(`/real-estate/${portfolioId}/investor-actions/`, data),
  deleteInvestorAction: (portfolioId: string, actionId: string) => api.delete(`/real-estate/${portfolioId}/investor-actions/${actionId}/`),
  getPossibleSources: (portfolioId: string) => api.get(`/real-estate/${portfolioId}/possible-capital-sources/`),
  createPossibleSource: (portfolioId: string, data: any) => api.post(`/real-estate/${portfolioId}/possible-capital-sources/`, data),
  deletePossibleSource: (portfolioId: string, sourceId: string) => api.delete(`/real-estate/${portfolioId}/possible-capital-sources/${sourceId}/`),

  // Bookkeeping Endpoints
  getLedgers: (portfolioId: string) => api.get(`/real-estate/${portfolioId}/ledgers/`),
  initializeLedger: (portfolioId: string, year: number) => api.post(`/real-estate/${portfolioId}/ledgers/initialize/`, { year }),
  getTrialBalance: (portfolioId: string, yearId: string) => api.get(`/real-estate/${portfolioId}/ledgers/${yearId}/trial-balance/`),
  getPLStatement: (portfolioId: string, yearId: string) => api.get(`/real-estate/${portfolioId}/ledgers/${yearId}/pl-statement/`),
  getTAccount: (portfolioId: string, yearId: string, accountId: string) => 
    api.get(`/real-estate/${portfolioId}/ledgers/${yearId}/accounts/${accountId}/t-account/`),
  createManualTransaction: (portfolioId: string, yearId: string, data: any) => 
    api.post(`/real-estate/${portfolioId}/ledgers/${yearId}/transactions/`, data),
  getTransactionTemplates: (portfolioId: string) => api.get(`/real-estate/${portfolioId}/ledgers/templates/`),
  syncCashFlow: (portfolioId: string, yearId: string) => api.post(`/real-estate/${portfolioId}/ledgers/${yearId}/sync-cash-flow/`),
  closeLedger: (portfolioId: string, yearId: string) => api.post(`/real-estate/${portfolioId}/ledgers/${yearId}/close/`),
  deleteLedger: (portfolioId: string, yearId: string) => api.delete(`/real-estate/${portfolioId}/ledgers/${yearId}/delete/`),


  // Jurisdictions & Tax Rules
  getJurisdictions: () => api.get("/real-estate/jurisdictions/"),
  createJurisdiction: (data: any) => api.post("/real-estate/jurisdictions/", data),
  updateJurisdiction: (id: string, data: any) => api.patch(`/real-estate/jurisdictions/${id}/`, data),
  deleteJurisdiction: (id: string) => api.delete(`/real-estate/jurisdictions/${id}/`),
  
  getTaxRules: (jurisdictionId?: string) => {
    const params = jurisdictionId ? { jurisdiction: jurisdictionId } : {};
    return api.get("/real-estate/tax-rules/", { params });
  },
  createTaxRule: (data: any) => api.post("/real-estate/tax-rules/", data),
  updateTaxRule: (id: string, data: any) => api.patch(`/real-estate/tax-rules/${id}/`, data),
  deleteTaxRule: (id: string) => api.delete(`/real-estate/tax-rules/${id}/`),
  getTaxAnalysis: (portfolioId: string) => api.get(`/real-estate/${portfolioId}/tax-analysis/`),

  // Reports
  getReports: (portfolioId: string) => api.get("/real-estate/reports/", { params: { portfolio_id: portfolioId } }),
  createReport: (data: any) => api.post("/real-estate/reports/", data),
  updateReport: (id: string, data: any) => api.patch(`/real-estate/reports/${id}/`, data),
  deleteReport: (id: string) => api.delete(`/real-estate/reports/${id}/`),
  regenerateReport: (id: string) => api.post(`/real-estate/reports/${id}/regenerate/`),
  getPublicReport: (slug: string) => publicApi.get(`/real-estate/reports/public/${slug}/`),
};

export { api, publicApi };
