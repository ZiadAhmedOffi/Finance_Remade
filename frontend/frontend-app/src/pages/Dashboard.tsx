import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/api";
import "./Dashboard.css";
import FundCard from "../components/FundCard";

interface Fund {
  id: string;
  name: string;
  description: string;
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

  /**
   * Initializes component state:
   * 1. Checks JWT for admin privileges.
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
      } catch (e) {
        console.error("Error decoding token", e);
        setIsAdmin(false);
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

  return (
    <div className="dashboard-container-revamp">
      <header className="main-header">
        <div className="header-brand">FinanceRemade</div>
        <div className="header-nav">
          <Link to="/profile" className="nav-link">My Profile</Link>
          {isAdmin && <Link to="/admin" className="nav-link">Admin Console</Link>}
          <button className="btn-logout" onClick={handleLogout}>Logout</button>
        </div>
      </header>
      
      <main className="dashboard-content">
        <section className="funds-section">
          <h2 className="section-title">Available Funds</h2>
          
          {loading ? (
            <div className="loading-spinner">Loading funds...</div>
          ) : (
            <div className="funds-grid-revamp">
              {funds.length > 0 ? (
                funds.map(fund => (
                  <FundCard key={fund.id} fund={fund} />
                ))
              ) : (
                <div className="empty-state">
                  <p>You are not assigned to any funds yet.</p>
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default Dashboard;
