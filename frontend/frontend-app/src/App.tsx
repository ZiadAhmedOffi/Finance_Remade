import { useEffect, useCallback } from "react";
import { Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import AdminDashboard from "./pages/AdminDashboard";
import PrivateRoute from "./components/PrivateRoute";

/**
 * Main App component. Handles routing and global user activity tracking
 * to ensure tokens are valid during navigation and interactions.
 */
function App() {
  const navigate = useNavigate();
  const location = useLocation();

  /**
   * Helper function to check if the current JWT token is expired by decoding its payload.
   */
  const isTokenExpired = useCallback(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return true;

    try {
      const payloadBase64 = token.split(".")[1];
      const decodedJson = atob(payloadBase64);
      const decoded = JSON.parse(decodedJson);
      const exp = decoded.exp;
      const now = Date.now() / 1000;
      return now > exp;
    } catch (e) {
      return true;
    }
  }, []);

  /**
   * Monitors user activity to ensure they are still authenticated.
   * Redirects to login if the session has expired.
   */
  const handleUserActivity = useCallback(() => {
    // Only check for public routes if we want to avoid redirect loops, 
    // but the request is to redirect immediately once it runs out.
    // If we are already on login/register, no need to redirect.
    if (location.pathname === "/login" || location.pathname === "/register") {
      return;
    }

    if (isTokenExpired()) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      navigate("/login");
    }
  }, [isTokenExpired, navigate, location.pathname]);

  useEffect(() => {
    window.addEventListener("click", handleUserActivity);
    window.addEventListener("scroll", handleUserActivity);

    return () => {
      window.removeEventListener("click", handleUserActivity);
      window.removeEventListener("scroll", handleUserActivity);
    };
  }, [handleUserActivity]);

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<PrivateRoute />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/admin" element={<AdminDashboard />} />
      </Route>
    </Routes>
  );
}

export default App;