import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";
import "./Dashboard.css";

interface Fund {
  id: string;
  name: string;
}

/**
 * Dashboard component for authenticated users.
 * Displays personal links, user's funds, and provides conditional access 
 * to the Admin Dashboard for users with 'SUPER_ADMIN' or 'ACCESS_MANAGER' roles.
 */
const Dashboard: React.FC = () => {
  const [isAdmin, setIsAdmin] = useState(false);
  const [funds, setFunds] = useState<Fund[]>([]);
  const [loading, setLoading] = useState(true);

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

  return (
    <div className="dashboard-container">
      <h1>Welcome to Your Dashboard</h1>
      
      <div className="dashboard-section">
        <h3>My Funds</h3>
        {loading ? <p>Loading funds...</p> : (
          <div className="funds-grid">
            {funds.length > 0 ? funds.map(fund => (
              <Link key={fund.id} to={`/funds/${fund.id}`} className="fund-card">
                <h4>{fund.name}</h4>
                <span>View Dashboard &rarr;</span>
              </Link>
            )) : <p>You are not assigned to any funds yet.</p>}
          </div>
        )}
      </div>

      <div className="dashboard-links">
        <Link to="/profile" className="dashboard-link">
          View My Profile
        </Link>
        {isAdmin && (
          <Link to="/admin" className="dashboard-link">
            Admin Dashboard
          </Link>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
