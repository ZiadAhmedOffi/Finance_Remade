import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { getRefreshToken, isAccessTokenValid } from "../utils/auth";

const PrivateRoute: React.FC = () => {
  const isAuthenticated = isAccessTokenValid() || !!getRefreshToken();

  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
};

export default PrivateRoute;
