import React, { useState, useEffect, useCallback } from "react";
import { api } from "../api/api";
import "./AdminDashboard.css";

interface Role {
  id: string;
  name: string;
}

interface Fund {
  id: string;
  name: string;
}

interface UserRole {
  role: {
    name: string;
  };
  fund: string | null;
}

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  company: string;
  status: string;
  is_active: boolean;
  is_staff: boolean;
  roles: UserRole[];
}

const AdminDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"pending" | "active">("pending");
  const [pendingUsers, setPendingUsers] = useState<User[]>([]);
  const [activeUsers, setActiveUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [funds, setFunds] = useState<Fund[]>([]);
  
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [selectedFundId, setSelectedFundId] = useState("");

  const fetchPendingUsers = useCallback(async () => {
    try {
      const response = await api.get("/users/pending/");
      setPendingUsers(response.data);
    } catch (err) {
      console.error("Failed to fetch pending users", err);
    }
  }, []);

  const fetchActiveUsers = useCallback(async (page: number) => {
    try {
      const response = await api.get(`/users/active/?page=${page}`);
      setActiveUsers(response.data.results);
      setTotalPages(Math.ceil(response.data.count / 10)); // Assuming page size is 10
    } catch (err) {
      console.error("Failed to fetch active users", err);
    }
  }, []);

  const fetchRolesAndFunds = useCallback(async () => {
    try {
      const [rolesRes, fundsRes] = await Promise.all([
        api.get("/users/roles/"),
        api.get("/users/funds/"),
      ]);
      setRoles(rolesRes.data);
      setFunds(fundsRes.data);
    } catch (err) {
      console.error("Failed to fetch roles or funds", err);
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([
        fetchPendingUsers(),
        fetchActiveUsers(1),
        fetchRolesAndFunds(),
      ]);
      setLoading(false);
    };
    init();
  }, [fetchPendingUsers, fetchActiveUsers, fetchRolesAndFunds]);

  const handleApprove = async (userId: string) => {
    try {
      await api.post(`/users/approve/${userId}/`);
      setMessage("User approved successfully.");
      fetchPendingUsers();
      fetchActiveUsers(currentPage);
    } catch (err) {
      setError("Failed to approve user.");
    }
  };

  const handleReject = async (userId: string) => {
    try {
      await api.post(`/users/reject/${userId}/`);
      setMessage("User rejected successfully.");
      fetchPendingUsers();
    } catch (err) {
      setError("Failed to reject user.");
    }
  };

  const handleDeactivate = async (userId: string) => {
    if (!window.confirm("Are you sure you want to deactivate this user?")) return;
    try {
      await api.post(`/users/deactivate/${userId}/`);
      setMessage("User deactivated successfully.");
      fetchActiveUsers(currentPage);
    } catch (err) {
      setError("Failed to deactivate user.");
    }
  };

  const handleAssignRole = async () => {
    if (!selectedUserId || !selectedRoleId) return;
    
    const role = roles.find(r => r.id === selectedRoleId);
    if (role && (role.name === "INVESTOR" || role.name === "STEERING_COMMITTEE") && !selectedFundId) {
      alert("Please select a fund for this role.");
      return;
    }

    try {
      await api.post(`/users/assign-role/${selectedUserId}/`, {
        role_id: selectedRoleId,
        fund_id: selectedFundId || null
      });
      setMessage("Role assigned successfully.");
      setIsModalOpen(false);
      fetchActiveUsers(currentPage);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to assign role.");
    }
  };

  if (loading) return <div className="admin-dashboard-container">Loading Dashboard...</div>;

  return (
    <div className="admin-dashboard-container">
      <header className="dashboard-header">
        <h1>Admin Dashboard</h1>
        {message && <div className="alert alert-success">{message}</div>}
        {error && <div className="alert alert-error">{error}</div>}
      </header>

      <div className="tabs">
        <button 
          className={activeTab === "pending" ? "tab-btn active" : "tab-btn"}
          onClick={() => setActiveTab("pending")}
        >
          Pending Applications ({pendingUsers.length})
        </button>
        <button 
          className={activeTab === "active" ? "tab-btn active" : "tab-btn"}
          onClick={() => setActiveTab("active")}
        >
          Active Users
        </button>
      </div>

      <div className="tab-content">
        {activeTab === "pending" ? (
          <section>
            <h2>Pending User Applications</h2>
            {pendingUsers.length > 0 ? (
              <table className="users-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Company</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingUsers.map((user) => (
                    <tr key={user.id}>
                      <td>{user.first_name} {user.last_name}</td>
                      <td>{user.email}</td>
                      <td>{user.company}</td>
                      <td className="actions">
                        <button onClick={() => handleApprove(user.id)} className="btn btn-approve">Approve</button>
                        <button onClick={() => handleReject(user.id)} className="btn btn-reject">Reject</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="empty-state">No pending applications found.</p>}
          </section>
        ) : (
          <section>
            <h2>Active Users</h2>
            {activeUsers.length > 0 ? (
              <>
                <table className="users-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Roles</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeUsers.map((user) => (
                      <tr key={user.id}>
                        <td>{user.first_name} {user.last_name}</td>
                        <td>{user.email}</td>
                        <td>
                          <div className="role-tags">
                            {user.roles.length > 0 ? user.roles.map((r, i) => (
                              <span key={i} className="role-tag">
                                {r.role.name} {r.fund && `(${r.fund})`}
                              </span>
                            )) : <span className="no-roles">No roles</span>}
                          </div>
                        </td>
                        <td className="actions">
                          <button 
                            onClick={() => {
                              setSelectedUserId(user.id);
                              setIsModalOpen(true);
                            }} 
                            className="btn btn-primary"
                          >
                            Assign Role
                          </button>
                          <button onClick={() => handleDeactivate(user.id)} className="btn btn-deactivate">Deactivate</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="pagination">
                  <button 
                    disabled={currentPage === 1} 
                    onClick={() => {
                      setCurrentPage(prev => prev - 1);
                      fetchActiveUsers(currentPage - 1);
                    }}
                  >
                    Previous
                  </button>
                  <span>Page {currentPage} of {totalPages}</span>
                  <button 
                    disabled={currentPage === totalPages} 
                    onClick={() => {
                      setCurrentPage(prev => prev + 1);
                      fetchActiveUsers(currentPage + 1);
                    }}
                  >
                    Next
                  </button>
                </div>
              </>
            ) : <p className="empty-state">No active users found.</p>}
          </section>
        )}
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Assign Role</h3>
            <div className="form-group">
              <label>Select Role</label>
              <select 
                value={selectedRoleId} 
                onChange={(e) => {
                  setSelectedRoleId(e.target.value);
                  setSelectedFundId("");
                }}
              >
                <option value="">-- Select Role --</option>
                {roles.map(role => (
                  <option key={role.id} value={role.id}>{role.name}</option>
                ))}
              </select>
            </div>

            {(roles.find(r => r.id === selectedRoleId)?.name === "INVESTOR" || 
              roles.find(r => r.id === selectedRoleId)?.name === "STEERING_COMMITTEE") && (
              <div className="form-group">
                <label>Select Fund</label>
                <select value={selectedFundId} onChange={(e) => setSelectedFundId(e.target.value)}>
                  <option value="">-- Select Fund --</option>
                  {funds.map(fund => (
                    <option key={fund.id} value={fund.id}>{fund.name}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="modal-actions">
              <button onClick={handleAssignRole} className="btn btn-approve">Confirm Assignment</button>
              <button onClick={() => setIsModalOpen(false)} className="btn btn-reject">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
