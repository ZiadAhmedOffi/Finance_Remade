import { useEffect, useCallback, useRef } from "react";
import { Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { api, publicApi } from "./api/api";
import { createDPoPProof } from "./utils/dpopUtils";
import { clearAuthTokens, getAccessToken, getRefreshToken, setAuthTokens } from "./utils/auth";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import AdminDashboard from "./pages/AdminDashboard";
import FundDashboard from "./pages/FundDashboard";
import RealEstateDashboard from "./pages/RealEstateDashboard";
import RealEstatePortfolioDashboard from "./pages/RealEstatePortfolioDashboard";
import InvestorDashboard from "./pages/InvestorDashboard";
import PrivateRoute from "./components/PrivateRoute";
import AdminRoute from "./components/AdminRoute";
import NotFound from "./pages/NotFound";
import ErrorPage from "./pages/ErrorPage";
import PublicReportPage from "./pages/PublicReportPage";
import RealEstatePublicReportPage from "./pages/RealEstatePublicReportPage";
import CompliancePortal from "./pages/CompliancePortal";
import ComplianceAdmin from "./pages/ComplianceAdmin";

/**
 * Main App component. Handles routing and global user activity tracking
 * to ensure tokens are valid during navigation and interactions.
 */
function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const lastRefreshTime = useRef<number>(0);

  /**
   * Keep-alive ping to prevent Render free tier from sleeping.
   * Runs every 10 minutes as long as the app is open.
   */
  useEffect(() => {
    const pingServer = async () => {
      try {
        await publicApi.get("/ping/");
      } catch (e) {
        // Silently ignore ping errors
        console.debug("Keep-alive ping failed", e);
      }
    };

    // Initial ping on mount
    pingServer();

    const interval = setInterval(pingServer, 60000); // 1 minute in milliseconds

    return () => clearInterval(interval);
  }, []);

  /**
   * Refreshes the access token using the refresh token.
   */
  const refreshToken = useCallback(async () => {
    const refresh = getRefreshToken();
    if (!refresh) return false;

    // Prevent multiple refreshes in a short period (e.g., 30 seconds)
    if (Date.now() - lastRefreshTime.current < 30000) return true;

    try {
      const refreshUrl = api.defaults.baseURL ? `${api.defaults.baseURL}/users/token/refresh/` : "/api/users/token/refresh/";
      const proof = await createDPoPProof("POST", refreshUrl);
      const response = await publicApi.post(
        "/users/token/refresh/",
        { refresh },
        { headers: { DPoP: proof } }
      );
      setAuthTokens(response.data.access, response.data.refresh || refresh);
      lastRefreshTime.current = Date.now();
      return true;
    } catch (e) {
      console.error("Failed to refresh token", e);
      return false;
    }
  }, []);

  /**
   * Helper function to check if the current JWT token is expired by decoding its payload.
   */
  const isTokenExpired = useCallback(() => {
    const token = getAccessToken();
    if (!token) return { expired: true, almostExpired: false };

    try {
      const payloadBase64 = token.split(".")[1];
      const decodedJson = atob(payloadBase64);
      const decoded = JSON.parse(decodedJson);
      const exp = decoded.exp;
      const now = Date.now() / 1000;
      
      // If token expires in less than 5 minutes, we consider it "almost expired"
      // and will try to refresh it during activity.
      const isAlmostExpired = (exp - now) < 300; 
      
      return { expired: now > exp, almostExpired: isAlmostExpired };
    } catch (e) {
      return { expired: true, almostExpired: false };
    }
  }, []);

  /**
   * Monitors user activity to ensure they are still authenticated.
   * Redirects to login if the session has expired and cannot be refreshed.
   */
  const handleUserActivity = useCallback(async () => {
    if (
      location.pathname === "/" ||
      location.pathname === "/login" || 
      location.pathname === "/register" || 
      location.pathname.startsWith("/reports/public/")
    ) {
      return;
    }

    const { expired, almostExpired } = isTokenExpired();

    if (expired) {
      const success = await refreshToken();
      if (!success) {
        clearAuthTokens();
        navigate("/login");
      }
    } else if (almostExpired) {
      // Proactively refresh if almost expired and user is active
      await refreshToken();
    }
  }, [isTokenExpired, refreshToken, navigate, location.pathname]);

  useEffect(() => {
    handleUserActivity();
  }, [handleUserActivity]);

  useEffect(() => {
    const events = ["mousedown", "keydown", "scroll", "touchstart", "click"];
    const throttledActivity = () => {
        handleUserActivity();
    };

    events.forEach(event => window.addEventListener(event, throttledActivity));

    return () => {
      events.forEach(event => window.removeEventListener(event, throttledActivity));
    };
  }, [handleUserActivity]);

  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/error" element={<ErrorPage />} />
      <Route element={<PrivateRoute />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/compliance" element={<CompliancePortal />} />
        
        {/* Admin routes protected by AdminRoute */}
        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/compliance" element={<ComplianceAdmin />} />
        </Route>

        <Route path="/investor-dashboard" element={<InvestorDashboard />} />
        <Route path="/funds/:fundId" element={<FundDashboard />} />
        <Route path="/real-estate" element={<RealEstateDashboard />} />
        <Route path="/real-estate/:portfolioId" element={<RealEstatePortfolioDashboard />} />
      </Route>
      
      <Route path="/reports/public/:slug" element={<PublicReportPage />} />
      <Route path="/real-estate/reports/public/:slug" element={<RealEstatePublicReportPage />} />

      {/* Catch-all route for 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default App;
