import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import "./Dashboard.css";

/**
 * Dashboard component for authenticated users.
 * Displays personal links and provides conditional access to the Admin Dashboard
 * for users with 'SUPER_ADMIN' or 'ACCESS_MANAGER' roles.
 */
const Dashboard: React.FC = () => {
  const [isAdmin, setIsAdmin] = useState(false);

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
  }, []);

  return (
    <div className="dashboard-container">
      <h1>Welcome to Your Dashboard</h1>
      <p>This is your personal dashboard. More features coming soon!</p>
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
