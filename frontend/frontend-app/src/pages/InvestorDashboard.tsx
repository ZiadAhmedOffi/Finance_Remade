import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { fundsApi } from "../api/api";
import "./FundDashboard.css"; // Reuse dashboard styles
import InvestorOverviewTab from "../components/InvestorOverviewTab";
import InvestorPortfolioTab from "../components/InvestorPortfolioTab";
import InvestorRequestsTab from "../components/InvestorRequestsTab";

const InvestorDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<"overview" | "portfolio" | "requests">("overview");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fundsApi.getInvestorDashboard();
      setData(response.data);
      setError(null);
    } catch (err) {
      setError("Failed to fetch dashboard data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/login");
  };

  if (loading) return <div className="fund-dashboard-container">Loading Investor Dashboard...</div>;
  if (error) return <div className="fund-dashboard-container"><div className="error-state">{error}</div></div>;

  const menuItems = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "portfolio", label: "Investor Portfolio", icon: "📁" },
    { id: "requests", label: "Requests", icon: "📨" },
  ];

  return (
    <div className="fund-dashboard-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand">Investment Intelligence Tool</div>
          <button className="back-link" onClick={() => navigate("/dashboard")}>
            &larr; Back to Dashboard
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
            <span className="user-role">Investor</span>
          </div>
          <button className="logout-button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="content-header">
          <div className="header-title">
            <h1>Investor Dashboard</h1>
          </div>
        </header>

        <div className="scrollable-content">
          {activeTab === "overview" && data && (
            <InvestorOverviewTab 
              metrics={data.metrics} 
              lineGraphData={data.line_graph} 
            />
          )}

          {activeTab === "portfolio" && data && (
            <InvestorPortfolioTab 
              portfolio={data.portfolio} 
              pieChartData={data.pie_chart} 
            />
          )}

          {activeTab === "requests" && (
            <InvestorRequestsTab />
          )}
        </div>
      </main>
    </div>
  );
};

export default InvestorDashboard;
