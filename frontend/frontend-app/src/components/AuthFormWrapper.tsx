import React from "react";

const AuthFormWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        {children}
      </div>
    </div>
  );
};

const styles = {
  container: {
    height: "100vh",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#f5f7fa",
  } as React.CSSProperties,
  card: {
    width: "400px",
    padding: "40px",
    borderRadius: "8px",
    backgroundColor: "#ffffff",
    boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
  } as React.CSSProperties,
};

export default AuthFormWrapper;
