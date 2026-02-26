import React, { useState, useEffect } from "react";
import { api } from "../api/api";
import "./AdminDashboard.css";

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  company: string;
  status: string;
}

const AdminDashboard: React.FC = () => {
  const [pendingUsers, setPendingUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const fetchPendingUsers = async () => {
    try {
      setLoading(true);
      const response = await api.get("/users/pending/");
      setPendingUsers(response.data);
    } catch (err) {
      setError("Failed to fetch pending users. You may not have access.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPendingUsers();
  }, []);

  const handleApprove = async (userId: string) => {
    try {
      const response = await api.post(`/users/approve/${userId}/`);
      setMessage(response.data.message);
      // Refresh the list after approval
      fetchPendingUsers();
    } catch (err) {
      setError("Failed to approve user.");
      console.error(err);
    }
  };

  const handleReject = async (userId: string) => {
    try {
      const response = await api.post(`/users/reject/${userId}/`);
      setMessage(response.data.message);
      // Refresh the list after rejection
      fetchPendingUsers();
    } catch (err) {
      setError("Failed to reject user.");
      console.error(err);
    }
  };

  if (loading) {
    return <div className="admin-dashboard-container">Loading...</div>;
  }

  if (error) {
    return <div className="admin-dashboard-container error">{error}</div>;
  }

  return (
    <div className="admin-dashboard-container">
      <h1>Admin Dashboard</h1>
      <h2>Pending User Applications</h2>
      {message && <div className="message">{message}</div>}
      {pendingUsers.length > 0 ? (
        <table className="users-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Company</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {pendingUsers.map((user) => (
              <tr key={user.id}>
                <td>
                  {user.first_name} {user.last_name}
                </td>
                <td>{user.email}</td>
                <td>{user.company}</td>
                <td>
                  <span className={`status-badge status-${user.status.toLowerCase()}`}>
                    {user.status}
                  </span>
                </td>
                <td className="actions">
                  <button onClick={() => handleApprove(user.id)} className="approve-btn">
                    Approve
                  </button>
                  <button onClick={() => handleReject(user.id)} className="reject-btn">
                    Reject
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>No pending user applications.</p>
      )}
    </div>
  );
};

export default AdminDashboard;
