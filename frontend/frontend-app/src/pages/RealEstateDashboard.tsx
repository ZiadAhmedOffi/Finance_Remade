import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { realEstateApi } from "../api/api";
import RealEstateCard from "../components/RealEstateCard";
import "./Dashboard.css"; // Reuse dashboard styles for consistency

interface RealEstatePortfolio {
  id: string;
  name: string;
  description: string;
  region: string;
  status: "ACTIVE" | "DEACTIVATED";
  created_by_email: string;
  cover_image?: string;
}

const RealEstateDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [isAdmin, setIsAdmin] = useState(false);
  const [portfolios, setPortfolios] = useState<RealEstatePortfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  // New Portfolio Form State
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newRegion, setNewRegion] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        const roles = payload.roles || [];
        const hasAdminPrivilege = roles.some((r: any) => 
          r.role === "SUPER_ADMIN" || r.role === "ACCESS_MANAGER"
        );
        setIsAdmin(hasAdminPrivilege);
      } catch (e) {
        console.error("Error decoding token", e);
      }
    }

    fetchPortfolios();
  }, []);

  const fetchPortfolios = async () => {
    try {
      setLoading(true);
      const response = await realEstateApi.getPortfolios();
      setPortfolios(response.data);
    } catch (err) {
      console.error("Failed to fetch portfolios", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePortfolio = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await realEstateApi.createPortfolio({
        name: newName,
        description: newDescription,
        region: newRegion,
      });
      setShowCreateModal(false);
      setNewName("");
      setNewDescription("");
      setNewRegion("");
      fetchPortfolios();
    } catch (err) {
      console.error("Failed to create portfolio", err);
      alert("Failed to create portfolio. Please ensure the name is unique.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/login");
  };

  return (
    <div className="dashboard-container-revamp">
      <header className="main-header">
        <div className="header-brand">Investment Intelligence Tool</div>
        <div className="header-nav">
          <Link to="/dashboard" className="nav-link">Funds Dashboard</Link>
          <Link to="/profile" className="nav-link">My Profile</Link>
          <button className="btn-logout" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <main className="dashboard-content">
        <div className="section-header-row" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem'}}>
          <h1 className="dashboard-title">Real Estate Portfolios</h1>
          {isAdmin && (
            <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
              + Create Portfolio
            </button>
          )}
        </div>

        {loading ? (
          <div className="loading-spinner" style={{textAlign: 'center', padding: '4rem'}}>Loading portfolios...</div>
        ) : (
          <div className="funds-grid">
            {portfolios.length === 0 ? (
              <p style={{gridColumn: '1/-1', textAlign: 'center', color: '#64748b', padding: '4rem'}}>No real estate portfolios found.</p>
            ) : (
              portfolios.map(portfolio => (
                <RealEstateCard key={portfolio.id} portfolio={portfolio} />
              ))
            )}
          </div>
        )}
      </main>

      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2>Create New Real Estate Portfolio</h2>
            <form onSubmit={handleCreatePortfolio}>
              <div className="form-group">
                <label>Portfolio Name</label>
                <input 
                  type="text" 
                  value={newName} 
                  onChange={(e) => setNewName(e.target.value)} 
                  required 
                  placeholder="e.g. European Logistics Hub"
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea 
                  value={newDescription} 
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Portfolio objectives and strategy..."
                />
              </div>
              <div className="form-group">
                <label>Region</label>
                <input 
                  type="text" 
                  value={newRegion} 
                  onChange={(e) => setNewRegion(e.target.value)}
                  placeholder="e.g. Western Europe"
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Portfolio</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default RealEstateDashboard;
