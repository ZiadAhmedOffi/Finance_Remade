import { logout } from "../api/api";

function Dashboard() {
  return (
    <div style={{ textAlign: "center", marginTop: "100px" }}>
      <h2>Dashboard</h2>
      <p>You are authenticated.</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

export default Dashboard;