import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import NotFound from "../pages/NotFound";
import { getRefreshToken, getTokenPayload, isAccessTokenValid } from "../utils/auth";

/**
 * AdminRoute Component
 * 
 * Protects administrative routes. Checks the user's JWT roles to ensure 
 * they have SUPER_ADMIN or ACCESS_MANAGER privileges.
 */
const AdminRoute: React.FC = () => {
  if (!isAccessTokenValid() && !getRefreshToken()) return <Navigate to="/login" replace />;

  const roles = getTokenPayload()?.roles || [];
  const hasAdminPrivilege = roles.some((r) => r.role === "SUPER_ADMIN" || r.role === "ACCESS_MANAGER");

  if (!hasAdminPrivilege) {
    return (
      <NotFound
        title="Privilege Error"
        message="You do not have the necessary administrative privileges to perform this action or view this page."
      />
    );
  }

  return <Outlet />;
};

export default AdminRoute;
