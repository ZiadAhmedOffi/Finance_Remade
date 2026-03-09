import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import NotFound from "../pages/NotFound";

/**
 * AdminRoute Component
 * 
 * Protects administrative routes. Checks the user's JWT roles to ensure 
 * they have SUPER_ADMIN or ACCESS_MANAGER privileges.
 */
const AdminRoute: React.FC = () => {
  const token = localStorage.getItem("access_token");
  
  if (!token) return <Navigate to="/login" />;

  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    const roles = payload.roles || [];
    
    const hasAdminPrivilege = roles.some((r: any) => 
      r.role === "SUPER_ADMIN" || r.role === "ACCESS_MANAGER"
    );

    if (!hasAdminPrivilege) {
      return (
        <NotFound 
          title="Privilege Error" 
          message="You do not have the necessary administrative privileges to perform this action or view this page." 
        />
      );
    }

    return <Outlet />;
  } catch (e) {
    console.error("Error decoding token", e);
    return <Navigate to="/login" />;
  }
};

export default AdminRoute;
