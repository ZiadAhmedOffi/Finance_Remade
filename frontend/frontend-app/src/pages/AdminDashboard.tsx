import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/api";
import "./AdminDashboard.css";
import NotFound from "./NotFound";

interface Role {
  id: string;
  name: string;
}

interface Fund {
  id: string;
  name: string;
  description: string;
  tag: string;
  created_by_email: string;
  steering_committee: string[];
  status: "ESTABLISHED" | "FUTURE" | "DEACTIVATED";
}

interface UserRole {
  role: {
    id: string;
    name: string;
  };
  fund: string | null;
  fund_name?: string | null;
}

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  company: string;
  status: string;
  is_staff: boolean;
  roles: UserRole[];
}

interface AuditLog {
  id: string;
  actor_email: string;
  target_user_email: string;
  action: string;
  fund_name: string;
  metadata: any;
  ip_address: string;
  timestamp: string;
}

/**
 * AdminDashboard component for users with elevated privileges.
 * Allows managing user applications, active users, role assignments, 
 * and viewing system audit logs with detailed metadata.
 */
const AdminDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<"pending" | "active" | "logs" | "funds">("pending");
  const [pendingUsers, setPendingUsers] = useState<User[]>([]);
  const [activeUsers, setActiveUsers] = useState<User[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [funds, setFunds] = useState<Fund[]>([]);
  
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [logPage, setLogPage] = useState(1);
  const [totalLogPages, setTotalLogPages] = useState(1);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isFundModalOpen, setIsFundModalOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [selectedLogForDetails, setSelectedLogForDetails] = useState<AuditLog | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [selectedFundId, setSelectedFundId] = useState("");

  const [newFundName, setNewFundName] = useState("");
  const [newFundDescription, setNewFundDescription] = useState("");
  const [newFundTag, setNewFundTag] = useState("VC");

  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [privilegeError, setPrivilegeError] = useState<{title: string, message: string} | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await api.get("/users/me/");
        setCurrentUser(response.data);
      } catch (e) {
        console.error("Error fetching profile", e);
      }
    };
    fetchProfile();
  }, []);

  const isSuperAdmin = currentUser?.roles.some(r => r.role.name === "SUPER_ADMIN");

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

  const fetchAuditLogs = useCallback(async (page: number) => {
    try {
      const response = await api.get(`/users/logs/?page=${page}`);
      setAuditLogs(response.data.results);
      setTotalLogPages(Math.ceil(response.data.count / 20)); // Assuming page size is 20
    } catch (err) {
      console.error("Failed to fetch audit logs", err);
    }
  }, []);

  const fetchFunds = useCallback(async () => {
    try {
      const response = await api.get("/funds/");
      setFunds(response.data);
    } catch (err) {
      console.error("Failed to fetch funds", err);
    }
  }, []);

  const fetchRolesOnly = useCallback(async () => {
    try {
      const response = await api.get("/users/roles/");
      setRoles(response.data);
    } catch (err) {
      console.error("Failed to fetch roles", err);
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([
        fetchPendingUsers(),
        fetchActiveUsers(1),
        fetchAuditLogs(1),
        fetchFunds(),
        fetchRolesOnly(),
      ]);
      setLoading(false);
    };
    init();
  }, [fetchPendingUsers, fetchActiveUsers, fetchAuditLogs, fetchFunds, fetchRolesOnly]);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/login");
  };

  const handleApprove = async (userId: string) => {
    try {
      await api.post(`/users/approve/${userId}/`);
      setMessage("User approved successfully.");
      fetchPendingUsers();
      fetchActiveUsers(currentPage);
      fetchAuditLogs(logPage);
    } catch (err) {
      setError("Failed to approve user.");
    }
  };

  const handleReject = async (userId: string) => {
    try {
      await api.post(`/users/reject/${userId}/`);
      setMessage("User rejected successfully.");
      fetchPendingUsers();
      fetchAuditLogs(logPage);
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
      fetchAuditLogs(logPage);
    } catch (err) {
      setError("Failed to deactivate user.");
    }
  };

  const handleCreateFund = async () => {
    if (!isSuperAdmin) {
      setPrivilegeError({
        title: "Privilege Error",
        message: "Only Super Administrators are authorized to create new funds in the system."
      });
      return;
    }
    if (!newFundName) return;
    try {
      await api.post("/funds/", {
        name: newFundName,
        description: newFundDescription,
        tag: newFundTag
      });
      setMessage("Fund created successfully.");
      setNewFundName("");
      setNewFundDescription("");
      setNewFundTag("VC");
      setIsFundModalOpen(false);
      fetchFunds();
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to create fund.");
    }
  };

  const handleDeactivateFund = async (fundId: string) => {
    const canEditStatus = isSuperAdmin || currentUser?.roles.some(r => r.fund === fundId && r.role.name === "STEERING_COMMITTEE");

    if (!canEditStatus) {
      setPrivilegeError({
        title: "Privilege Error",
        message: "You are not authorized to deactivate this fund."
      });
      return;
    }
    if (!window.confirm("Are you sure you want to deactivate this fund?")) return;
    try {
      await api.put(`/funds/${fundId}/`, { status: "DEACTIVATED" });
      setMessage("Fund deactivated successfully.");
      fetchFunds();
    } catch (err) {
      setError("Failed to deactivate fund.");
    }
  };

  const handleChangeFundStatus = async (fund_id: string, newStatus: string) => {
    try {
      await api.put(`/funds/${fund_id}/`, { status: newStatus });
      setMessage(`Fund status updated to ${newStatus}.`);
      fetchFunds();
    } catch (err) {
      setError("Failed to update fund status.");
    }
  };

  const handleChangeFundTag = async (fund_id: string, newTag: string) => {
    try {
      await api.put(`/funds/${fund_id}/`, { tag: newTag });
      setMessage(`Fund tag updated to ${newTag}.`);
      fetchFunds();
    } catch (err) {
      setError("Failed to update fund tag.");
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
      fetchAuditLogs(logPage);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to assign role.");
    }
  };

  const handleRemoveRole = async (userId: string, roleId: string, fundId: string | null) => {
    if (!window.confirm("Are you sure you want to remove this role?")) return;
    try {
      await api.post(`/users/remove-role/${userId}/`, {
        role_id: roleId,
        fund_id: fundId
      });
      setMessage("Role removed successfully.");
      fetchActiveUsers(currentPage);
      fetchAuditLogs(logPage);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to remove role.");
    }
  };

  if (privilegeError) {
    return <NotFound title={privilegeError.title} message={privilegeError.message} />;
  }

  if (loading) return <div className="admin-dashboard-container">Loading Dashboard...</div>;

  return (
    <div className="admin-dashboard-container">
      <header className="dashboard-header">
        <div className="header-top">
          <h1>Admin Dashboard</h1>
          <div className="header-actions">
            <button className="btn btn-primary" onClick={() => navigate("/dashboard")}>Back to My Dashboard</button>
            <button className="btn btn-logout" onClick={handleLogout}>Exit</button>
          </div>
        </div>
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
        <button 
          className={activeTab === "funds" ? "tab-btn active" : "tab-btn"}
          onClick={() => setActiveTab("funds")}
        >
          Funds Management
        </button>
        <button 
          className={activeTab === "logs" ? "tab-btn active" : "tab-btn"}
          onClick={() => setActiveTab("logs")}
        >
          Audit Logs
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
        ) : activeTab === "active" ? (
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
                                {r.role.name} {r.fund_name && `(${r.fund_name})`}
                                <button 
                                  className="remove-role-btn" 
                                  onClick={() => handleRemoveRole(user.id, r.role.id || "", r.fund || null)}
                                  title="Remove Role"
                                >
                                  &times;
                                </button>
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
        ) : activeTab === "funds" ? (
          <section>
            <div className="section-header">
              <h2>Funds Management</h2>
              {isSuperAdmin && (
                <button onClick={() => setIsFundModalOpen(true)} className="btn btn-approve">Create New Fund</button>
              )}
            </div>
            {funds.length > 0 ? (
              <table className="users-table">
                <thead>
                  <tr>
                    <th>Fund Name</th>
                    <th>Tag</th>
                    <th>Status</th>
                    <th>Created By</th>
                    <th>SC Members</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {funds.map((fund) => {
                    const canEditFund = isSuperAdmin || currentUser?.roles.some(r => r.fund === fund.id && r.role.name === "STEERING_COMMITTEE");
                    return (
                      <tr key={fund.id}>
                        <td>{fund.name}</td>
                        <td>
                          {canEditFund ? (
                            <select 
                              value={fund.tag} 
                              onChange={(e) => handleChangeFundTag(fund.id, e.target.value)}
                              style={{padding: '0.2rem', borderRadius: '4px'}}
                            >
                              <option value="BIC">BIC</option>
                              <option value="VC">VC</option>
                              <option value="VS">VS</option>
                              <option value="AIG">AIG</option>
                              <option value="SF">SF</option>
                              <option value="REAL_ESTATE">Real estate</option>
                            </select>
                          ) : (
                            <span>{fund.tag === "REAL_ESTATE" ? "Real estate" : fund.tag}</span>
                          )}
                        </td>
                        <td>
                          {canEditFund ? (
                            <select 
                              value={fund.status} 
                              onChange={(e) => handleChangeFundStatus(fund.id, e.target.value)}
                              style={{padding: '0.2rem', borderRadius: '4px'}}
                            >
                              <option value="ESTABLISHED">Established</option>
                              <option value="FUTURE">Future</option>
                              <option value="DEACTIVATED">Deactivated</option>
                            </select>
                          ) : (
                            <span className={`status-tag ${fund.status.toLowerCase()}`}>{fund.status}</span>
                          )}
                        </td>
                        <td>{fund.created_by_email}</td>
                        <td>
                          <div className="sc-members-list">
                            {fund.steering_committee.length > 0 
                              ? fund.steering_committee.join(", ") 
                              : "No SC Members"}
                          </div>
                        </td>
                        <td className="actions">
                          {canEditFund && fund.status !== "DEACTIVATED" && (
                            <button onClick={() => handleDeactivateFund(fund.id)} className="btn btn-deactivate">Deactivate</button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : <p className="empty-state">No funds found.</p>}
          </section>
        ) : activeTab === "logs" ? (
          <section>
            <h2>Audit Logs</h2>
            {auditLogs.length > 0 ? (
              <>
                <table className="users-table">
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Actor</th>
                      <th>Action</th>
                      <th>Target</th>
                      <th>IP Address</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map((log) => (
                      <tr key={log.id}>
                        <td>{new Date(log.timestamp).toLocaleString()}</td>
                        <td>{log.actor_email || "System"}</td>
                        <td>{log.action}</td>
                        <td>{log.target_user_email || log.fund_name || "-"}</td>
                        <td>{log.ip_address || "-"}</td>
                        <td>
                          <button 
                            className="btn btn-primary"
                            onClick={() => setSelectedLogForDetails(log)}
                          >
                            View Details
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="pagination">
                  <button 
                    disabled={logPage === 1} 
                    onClick={() => {
                      setLogPage(prev => prev - 1);
                      fetchAuditLogs(logPage - 1);
                    }}
                  >
                    Previous
                  </button>
                  <span>Page {logPage} of {totalLogPages}</span>
                  <button 
                    disabled={logPage === totalLogPages} 
                    onClick={() => {
                      setLogPage(prev => prev + 1);
                      fetchAuditLogs(logPage + 1);
                    }}
                  >
                    Next
                  </button>
                </div>
              </>
            ) : <p className="empty-state">No logs found.</p>}
          </section>
        ) : null}
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

      {isFundModalOpen && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Create New Fund</h3>
            <div className="form-group">
              <label>Fund Name</label>
              <input 
                type="text" 
                value={newFundName} 
                onChange={(e) => setNewFundName(e.target.value)}
                placeholder="Enter fund name"
              />
            </div>
            <div className="form-group">
              <label>Fund Tag</label>
              <select 
                value={newFundTag} 
                onChange={(e) => setNewFundTag(e.target.value)}
                className="form-input"
                style={{width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc'}}
              >
                <option value="BIC">BIC</option>
                <option value="VC">VC</option>
                <option value="VS">VS</option>
                <option value="AIG">AIG</option>
                <option value="SF">SF</option>
                <option value="REAL_ESTATE">Real estate</option>
              </select>
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea 
                value={newFundDescription} 
                onChange={(e) => setNewFundDescription(e.target.value)}
                placeholder="Enter fund description"
                rows={4}
              />
            </div>
            <div className="modal-actions">
              <button onClick={handleCreateFund} className="btn btn-approve">Create Fund</button>
              <button onClick={() => setIsFundModalOpen(false)} className="btn btn-reject">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {selectedLogForDetails && (
        <div className="modal-overlay">
          <div className="modal log-details-modal">
            <h3>Log Details</h3>
            <div className="log-details-content">
              <p><strong>Action:</strong> {selectedLogForDetails.action}</p>
              <p><strong>Timestamp:</strong> {new Date(selectedLogForDetails.timestamp).toLocaleString()}</p>
              <p><strong>Actor:</strong> {selectedLogForDetails.actor_email || "System"}</p>
              <p><strong>Target:</strong> {selectedLogForDetails.target_user_email || selectedLogForDetails.fund_name || "-"}</p>
              <p><strong>IP Address:</strong> {selectedLogForDetails.ip_address || "-"}</p>
              <div className="metadata-section">
                <strong>Metadata:</strong>
                <pre>{JSON.stringify(selectedLogForDetails.metadata, null, 2)}</pre>
              </div>
            </div>
            <div className="modal-actions">
              <button onClick={() => setSelectedLogForDetails(null)} className="btn btn-primary">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
