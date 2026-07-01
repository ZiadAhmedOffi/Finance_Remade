import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, realEstateApi } from "../api/api";
import { clearAuthTokens, getTokenPayload } from "../utils/auth";
import "./Dashboard.css";
import FundCard from "../components/FundCard";
import RealEstateCard from "../components/RealEstateCard";

interface Fund {
  id: string;
  name: string;
  description: string;
  tag: string;
  status: "ESTABLISHED" | "FUTURE" | "DEACTIVATED";
}

interface RealEstatePortfolio {
  id: string;
  name: string;
  description: string;
  region: string;
  status: "ACTIVE" | "DEACTIVATED";
  cover_image?: string;
  card_metrics?: {
    graph_data?: { year: number; portfolio_value: number }[];
    nav_metrics?: {
      price_per_unit?: number;
      nav?: number;
      developer?: string;
      property_count_active?: number;
      portfolio_irr?: number;
      irr_yield?: number;
      irr_capital_growth?: number;
      weighted_occupancy?: number;
      liquidation_index?: number;
      annual_cash_flow_current?: number;
      annual_cash_flow_prev?: number;
    };
  };
}

/**
 * Dashboard Component
 * 
 * The landing page for authenticated users.
 * Displays all funds or real estate portfolios the user has access to.
 * Features a slider-switch to toggle between asset classes.
 */
const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [isAdmin, setIsAdmin] = useState(false);
  const [funds, setFunds] = useState<Fund[]>([]);
  const [portfolios, setPortfolios] = useState<RealEstatePortfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [isInvestor, setIsInvestor] = useState(false);
  const [viewMode, setViewMode] = useState<"FUND" | "REAL_ESTATE">("FUND");

  /**
   * Initializes component state:
   * 1. Checks JWT for admin privileges and investor role.
   * 2. Fetches both funds and real estate portfolios.
   */
  useEffect(() => {
    const roles = getTokenPayload()?.roles || [];
    setIsAdmin(roles.some((r) => r.role === "SUPER_ADMIN" || r.role === "ACCESS_MANAGER"));
    setIsInvestor(roles.some((r) => r.role === "INVESTOR"));

    const fetchData = async () => {
      try {
        setLoading(true);
        const [fundsRes, portfoliosRes] = await Promise.all([
          api.get("/funds/"),
          realEstateApi.getPortfolios(true)
        ]);
        setFunds(fundsRes.data);
        setPortfolios(portfoliosRes.data);
      } catch (err) {
        console.error("Failed to fetch data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  /**
   * Clears session and redirects to login.
   */
  const handleLogout = () => {
    clearAuthTokens();
    navigate("/login");
  };

  const establishedFunds = funds.filter(f => f.status === "ESTABLISHED");
  const futureFunds = funds.filter(f => f.status === "FUTURE");
  const activePortfolios = portfolios.filter(p => p.status === "ACTIVE");

  return (
    <div className="dashboard-container-revamp">
      <header className="main-header">
        <div className="header-brand">Investment Intelligence Tool</div>
        <div className="header-nav">
          <Link to="/profile" className="nav-link">My Profile</Link>
          <Link to="/compliance" className="nav-link">Compliance</Link>
          {isInvestor && <Link to="/investor-dashboard" className="nav-link">Investor Dashboard</Link>}
          {isAdmin && <Link to="/admin" className="nav-link">Admin Console</Link>}
          <button className="btn-logout" onClick={handleLogout}>Logout</button>
        </div>
      </header>
      
      <main className="dashboard-content">
        <div className="switch-container">
          <button 
            className={`switch-button ${viewMode === "FUND" ? "active" : ""}`}
            onClick={() => setViewMode("FUND")}
          >
            Equity Funds
          </button>
          <button 
            className={`switch-button ${viewMode === "REAL_ESTATE" ? "active" : ""}`}
            onClick={() => setViewMode("REAL_ESTATE")}
          >
            Real Estate
          </button>
        </div>

        {loading ? (
          <div className="loading-spinner" style={{textAlign: 'center', padding: '4rem'}}>Loading...</div>
        ) : (
          <div className="view-content animate-fade-in" key={viewMode}>
            {viewMode === "FUND" ? (
              <>
                <section className="funds-section" style={{marginBottom: '4rem'}}>
                  <h2 className="section-title">Established Funds</h2>
                  <div className="funds-grid-revamp">
                    {establishedFunds.length > 0 ? (
                      establishedFunds.map(fund => (
                        <FundCard key={fund.id} fund={fund} />
                      ))
                    ) : (
                      <div className="empty-state">
                        <p>No established funds found.</p>
                      </div>
                    )}
                  </div>
                </section>

                <section className="funds-section">
                  <h2 className="section-title">Future Funds</h2>
                  <div className="funds-grid-revamp">
                    {futureFunds.length > 0 ? (
                      futureFunds.map(fund => (
                        <FundCard key={fund.id} fund={fund} />
                      ))
                    ) : (
                      <div className="empty-state">
                        <p>No future funds found.</p>
                      </div>
                    )}
                  </div>
                </section>
              </>
            ) : (
              <section className="funds-section">
                <h2 className="section-title">Real Estate Portfolios</h2>
                <div className="funds-grid-revamp">
                  {activePortfolios.length > 0 ? (
                    activePortfolios.map(portfolio => (
                      <RealEstateCard key={portfolio.id} portfolio={portfolio} />
                    ))
                  ) : (
                    <div className="empty-state">
                      <p>No active real estate portfolios found.</p>
                    </div>
                  )}
                </div>
              </section>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
