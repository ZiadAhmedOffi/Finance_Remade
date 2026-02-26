import React from "react";
import { Link } from "react-router-dom";
import "./Dashboard.css";

const Dashboard: React.FC = () => {
  return (
    <div className="dashboard-container">
      <h1>Welcome to Your Dashboard</h1>
      <p>This is your personal dashboard. More features coming soon!</p>
      <div className="dashboard-links">
        <Link to="/profile" className="dashboard-link">
          View My Profile
        </Link>
        <Link to="/admin" className="dashboard-link">
          Admin Dashboard
        </Link>
      </div>
    </div>
  );
};

export default Dashboard;
