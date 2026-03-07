import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/api";
import "./Profile.css";

interface RoleAssignment {
  role: {
    name: string;
    description: string;
  };
  fund: string | null;
  fund_name: string | null;
}

interface UserProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  company: string;
  job_title: string;
  phone_number: string;
  status: string;
  is_active: boolean;
  is_staff: boolean;
  roles: RoleAssignment[];
}

const Profile: React.FC = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await api.get("/users/me/");
        setUser(response.data);
      } catch (err) {
        setError("Failed to fetch user profile. Please log in again.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/login");
  };

  if (loading) {
    return <div className="profile-container">Loading...</div>;
  }

  if (error) {
    return <div className="profile-container error">{error}</div>;
  }

  if (!user) {
    return <div className="profile-container">No user data found.</div>;
  }

  return (
    <div className="profile-container">
      <header className="profile-header-main">
        <button className="back-btn" onClick={() => navigate("/dashboard")}>&larr; Back to Dashboard</button>
        <h1>User Profile</h1>
        <button className="btn-logout" onClick={handleLogout}>Exit</button>
      </header>
      <div className="profile-card">
        <div className="profile-header">
          <h2>
            {user.first_name} {user.last_name}
          </h2>
          <p className="status">
            Account Status:{" "}
            <span className={`status-badge status-${user.status.toLowerCase()}`}>
              {user.status}
            </span>
          </p>
        </div>
        <div className="profile-details">
          <p>
            <strong>Email:</strong> {user.email}
          </p>
          <p>
            <strong>Company:</strong> {user.company || "N/A"}
          </p>
          <p>
            <strong>Job Title:</strong> {user.job_title || "N/A"}
          </p>
          <p>
            <strong>Phone Number:</strong> {user.phone_number || "N/A"}
          </p>
        </div>
        <div className="profile-roles">
          <h3>Assigned Roles</h3>
          {user.roles.length > 0 ? (
            <ul>
              {user.roles.map((assignment, index) => (
                <li key={index}>
                  <strong>{assignment.role.name}</strong>
                  {assignment.fund_name && ` for ${assignment.fund_name}`}
                </li>
              ))}
            </ul>
          ) : (
            <p>No roles assigned.</p>
          )}
        </div>
        <div className="profile-permissions">
          <h3>Permissions</h3>
          <p>
            <strong>Staff Access:</strong> {user.is_staff ? "Yes" : "No"}
          </p>
        </div>
      </div>
    </div>
  );
};

export default Profile;
