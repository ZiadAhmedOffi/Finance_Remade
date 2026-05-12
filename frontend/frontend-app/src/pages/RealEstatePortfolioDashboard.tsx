import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { realEstateApi } from "../api/api";
import RealEstateAssumptionsTab from "../components/RealEstateAssumptionsTab";
import PropertyDataTab from "../components/PropertyDataTab";
import FinancingModelTab from "../components/FinancingModelTab";
import OffPlanModelTab from "../components/OffPlanModelTab";
import SalesAndDisposalsTab from "../components/SalesAndDisposalsTab";
import CashFlowModelTab from "../components/CashFlowModelTab";
import RealEstateDashboardTab from "../components/RealEstateDashboardTab";
import "./FundDashboard.css"; // Reuse dashboard styles

interface RealEstatePortfolio {
  id: string;
  name: string;
  description: string;
  region: string;
  status: "ACTIVE" | "DEACTIVATED";
}

const RealEstatePortfolioDashboard: React.FC = () => {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const navigate = useNavigate();
  const [portfolio, setPortfolio] = useState<RealEstatePortfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"dashboard" | "properties" | "assumptions" | "financing" | "off-plan" | "sales" | "cash-flow">("dashboard");
  const [canEdit, setCanEdit] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        const roles = payload.roles || [];
        
        const isSuperAdmin = roles.some((r: any) => r.role === "SUPER_ADMIN");
        setIsAdmin(isSuperAdmin);

        const hasEditPrivilege = roles.some((r: any) => 
          r.role === "SUPER_ADMIN" || 
          (r.role === "PORTFOLIO_MANAGER" && r.portfolio_id === portfolioId)
        );
        setCanEdit(hasEditPrivilege);
      } catch (e) {
        console.error("Error decoding token", e);
      }
    }
  }, [portfolioId]);

  const fetchPortfolioData = useCallback(async () => {
    if (!portfolioId) return;
    try {
      setLoading(true);
      const response = await realEstateApi.getPortfolio(portfolioId);
      setPortfolio(response.data);
      setError(null);
    } catch (err: any) {
      setError("Failed to fetch portfolio data.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [portfolioId]);

  useEffect(() => {
    fetchPortfolioData();
  }, [fetchPortfolioData]);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/login");
  };

  if (loading) return <div className="loading-spinner">Loading portfolio dashboard...</div>;
  if (error || !portfolio) return <div className="error-message">{error || "Portfolio not found."}</div>;

  const menuItems = [
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "properties", label: "Property Data", icon: "🏢" },
    { id: "financing", label: "Financing Model", icon: "💰" },
    { id: "off-plan", label: "Off-Plan Model", icon: "🏗️" },
    { id: "cash-flow", label: "Cash Flow Model", icon: "📈" },
    { id: "sales", label: "Sales & Disposals", icon: "🤝" },
    { id: "assumptions", label: "Assumptions", icon: "⚙️" },
  ];

  return (
    <div className="fund-dashboard-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand">Investment Intelligence Tool</div>
          <button className="back-link" onClick={() => navigate("/real-estate")}>
            &larr; Back to Real Estate
          </button>
        </div>

        <nav className="sidebar-nav">
          {menuItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${activeTab === item.id ? "active" : ""}`}
              onClick={() => setActiveTab(item.id as any)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <span className="user-icon">👤</span>
            <span className="user-role">{isAdmin ? "Admin" : (canEdit ? "Portfolio Manager" : "Investor")}</span>
          </div>
          <button className="logout-button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="content-header">
          <div className="header-title">
            <h1>{portfolio.name}</h1>
            <span className={`status-badge ${portfolio.status === "DEACTIVATED" ? "inactive" : "active"}`}>
              {portfolio.status}
            </span>
          </div>
        </header>

        <div className="scrollable-content">
          {activeTab === "dashboard" && portfolioId && (
            <RealEstateDashboardTab portfolioId={portfolioId} />
          )}
          {activeTab === "properties" && portfolioId && (
            <PropertyDataTab portfolioId={portfolioId} canEdit={canEdit} />
          )}
          {activeTab === "assumptions" && portfolioId && (
            <RealEstateAssumptionsTab portfolioId={portfolioId} canEdit={canEdit} />
          )}
          {activeTab === "financing" && portfolioId && (
            <FinancingModelTab portfolioId={portfolioId} canEdit={canEdit} />
          )}
          {activeTab === "off-plan" && portfolioId && (
            <OffPlanModelTab portfolioId={portfolioId} canEdit={canEdit} />
          )}
          {activeTab === "sales" && portfolioId && (
            <SalesAndDisposalsTab portfolioId={portfolioId} canEdit={canEdit} />
          )}
          {activeTab === "cash-flow" && portfolioId && (
            <CashFlowModelTab portfolioId={portfolioId} />
          )}
        </div>
      </main>
    </div>
  );
};

export default RealEstatePortfolioDashboard;
