import React from "react";
import { useNavigate } from "react-router-dom";

interface NotFoundProps {
  title?: string;
  message?: string;
}

/**
 * Generic Not Found / Access Denied page.
 * Provides a clear message to the user and a way to return to the dashboard.
 */
const NotFound: React.FC<NotFoundProps> = ({ 
  title = "404 - Page Not Found", 
  message = "The page you are looking for doesn't exist or you don't have permission to access it." 
}) => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#f8fafc] flex items-center justify-center p-4 font-sans">
      <div className="max-width-[500px] text-center bg-white p-12 rounded-2xl shadow-sm border border-slate-200">
        <div className="text-6xl mb-6">🚫</div>
        <h1 className="text-3xl font-extrabold text-slate-900 mb-4">{title}</h1>
        <p className="text-slate-600 mb-8 text-lg leading-relaxed">
          {message}
        </p>
        <button 
          onClick={() => navigate("/dashboard")}
          className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-8 rounded-xl transition-all shadow-lg hover:shadow-indigo-200"
        >
          Return to Dashboard
        </button>
      </div>
    </div>
  );
};

export default NotFound;
