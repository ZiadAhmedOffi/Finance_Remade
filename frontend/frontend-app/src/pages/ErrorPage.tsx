import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./AdminDashboard.css"; // Reuse some styles or we can create ErrorPage.css

const ErrorPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const queryParams = new URLSearchParams(location.search);
  
  const code = queryParams.get("code") || "Error";
  const message = queryParams.get("message") || "An unexpected error occurred.";

  const getErrorDescription = (code: string) => {
    switch (code) {
      case "401":
        return "Authentication Required. Please log in to access this page.";
      case "403":
        return "Access Denied. You do not have permission to view this resource.";
      case "404":
        return "Page Not Found. The resource you are looking for does not exist.";
      default:
        return "An error occurred while processing your request.";
    }
  };

  return (
    <div className="admin-dashboard-container flex flex-col items-center justify-center min-h-screen text-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-12 max-w-lg w-full border border-gray-100 animate-in fade-in zoom-in duration-300">
        <div className="w-20 h-20 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-6">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 15c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        
        <h1 className="text-6xl font-black text-gray-900 mb-2 font-mono">{code}</h1>
        <h2 className="text-xl font-bold text-gray-800 mb-4">{message}</h2>
        <p className="text-gray-500 mb-8 leading-relaxed">
          {getErrorDescription(code)}
        </p>

        <div className="flex flex-col gap-3">
          <button 
            onClick={() => navigate("/login")}
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl transition-all shadow-lg shadow-emerald-200"
          >
            Go to Login
          </button>
          <button 
            onClick={() => navigate(-1)}
            className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold py-3 rounded-xl transition-all"
          >
            Go Back
          </button>
        </div>
      </div>
      
      <p className="mt-8 text-gray-400 text-sm">
        If you believe this is a mistake, please contact your system administrator.
      </p>
    </div>
  );
};

export default ErrorPage;
