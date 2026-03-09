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
    return (
      <div className="profile-page-container">
        <div className="loading-state">Loading Profile...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="profile-page-container">
        <div className="error-card">{error}</div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="profile-page-container">
      <header className="profile-top-nav">
        <div className="nav-left">
          <button className="back-btn" onClick={() => navigate("/dashboard")}>
            &larr; Back to Dashboard
          </button>
        </div>
        <div className="nav-brand">FinanceRemade</div>
        <div className="nav-right">
          <button className="logout-btn-minimal" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <main className="profile-content">
        <div className="profile-grid">
          {/* Left Column: User Summary Card */}
          <aside className="profile-sidebar-card">
            <div className="avatar-circle">
              {user.first_name[0]}{user.last_name[0]}
            </div>
            <h2 className="user-full-name">{user.first_name} {user.last_name}</h2>
            <p className="user-email-sub">{user.email}</p>
            <div className={`status-pill status-${user.status.toLowerCase()}`}>
              {user.status}
            </div>
            
            <div className="sidebar-stats">
              <div className="sidebar-stat">
                <span className="label">Staff Status</span>
                <span className="value">{user.is_staff ? "Administrator" : "Standard User"}</span>
              </div>
              <div className="sidebar-stat">
                <span className="label">Account Active</span>
                <span className="value">{user.is_active ? "Yes" : "No"}</span>
              </div>
            </div>
          </aside>

          {/* Right Column: Detailed Info and Roles */}
          <div className="profile-main-details">
            <section className="detail-section content-card">
              <h3>Personal Information</h3>
              <div className="info-grid">
                <div className="info-item">
                  <label>First Name</label>
                  <p>{user.first_name}</p>
                </div>
                <div className="info-item">
                  <label>Last Name</label>
                  <p>{user.last_name}</p>
                </div>
                <div className="info-item">
                  <label>Company</label>
                  <p>{user.company || "Not provided"}</p>
                </div>
                <div className="info-item">
                  <label>Job Title</label>
                  <p>{user.job_title || "Not provided"}</p>
                </div>
                <div className="info-item">
                  <label>Phone Number</label>
                  <p>{user.phone_number || "Not provided"}</p>
                </div>
              </div>
            </section>

            <section className="detail-section content-card">
              <h3>Role Assignments</h3>
              {user.roles.length > 0 ? (
                <div className="roles-list">
                  {user.roles.map((assignment, index) => (
                    <div key={index} className="role-card-item">
                      <div className="role-icon">🛡️</div>
                      <div className="role-text">
                        <span className="role-name">{assignment.role.name}</span>
                        {assignment.fund_name && (
                          <span className="role-fund">Fund: {assignment.fund_name}</span>
                        )}
                        <p className="role-desc">{assignment.role.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-roles">No active roles assigned to this account.</p>
              )}
            </section>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Profile;
