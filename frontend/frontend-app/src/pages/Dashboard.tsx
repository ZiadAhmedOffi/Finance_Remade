import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/api";
import "./Dashboard.css";
import FundCard from "../components/FundCard";

interface Fund {
  id: string;
  name: string;
  description: string;
  status: "ESTABLISHED" | "FUTURE" | "DEACTIVATED";
}

/**
 * Dashboard Component
 * 
 * The landing page for authenticated users.
 * Displays all funds the user has access to in a modern card-based layout.
 * Provides navigation to fund-specific dashboards and the system-wide admin console.
 */
const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [isAdmin, setIsAdmin] = useState(false);
  const [funds, setFunds] = useState<Fund[]>([]);
  const [loading, setLoading] = useState(true);
  const [isInvestor, setIsInvestor] = useState(false);

  /**
   * Initializes component state:
   * 1. Checks JWT for admin privileges and investor role.
   * 2. Fetches the list of funds assigned to the user.
   */
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      try {
        const payloadBase64 = token.split(".")[1];
        const decodedJson = atob(payloadBase64);
        const decoded = JSON.parse(decodedJson);
        const roles = decoded.roles || [];
        
        const hasAdminPrivilege = roles.some((r: any) => 
          r.role === "SUPER_ADMIN" || r.role === "ACCESS_MANAGER"
        );
        setIsAdmin(hasAdminPrivilege);

        const hasInvestorRole = roles.some((r: any) => r.role === "INVESTOR");
        setIsInvestor(hasInvestorRole);
      } catch (e) {
        console.error("Error decoding token", e);
        setIsAdmin(false);
        setIsInvestor(false);
      }
    }

    const fetchMyFunds = async () => {
      try {
        const response = await api.get("/funds/");
        setFunds(response.data);
      } catch (err) {
        console.error("Failed to fetch funds", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMyFunds();
  }, []);

  /**
   * Clears session and redirects to login.
   */
  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/login");
  };

  const establishedFunds = funds.filter(f => f.status === "ESTABLISHED");
  const futureFunds = funds.filter(f => f.status === "FUTURE");

  return (
    <div className="dashboard-container-revamp">
      <header className="main-header">
        <div className="header-brand">FinanceRemade</div>
        <div className="header-nav">
          <Link to="/profile" className="nav-link">My Profile</Link>
          {isInvestor && <Link to="/investor-dashboard" className="nav-link">Investor Dashboard</Link>}
          {isAdmin && <Link to="/admin" className="nav-link">Admin Console</Link>}
          <button className="btn-logout" onClick={handleLogout}>Logout</button>
        </div>
      </header>
      
      <main className="dashboard-content">
        {loading ? (
          <div className="loading-spinner" style={{textAlign: 'center', padding: '4rem'}}>Loading funds...</div>
        ) : (
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
        )}
      </main>
    </div>
  );
};

export default Dashboard;
