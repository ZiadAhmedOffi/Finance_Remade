import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../api/axios";
import { useAuth } from "../auth/useAuth";
import AuthFormWrapper from "../components/AuthFormWrapper";

const Login: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const response = await api.post("/api/login/", {
        email,
        password,
      });

      login(response.data.user);
      navigate("/dashboard");
    } catch (error) {
      alert("Invalid credentials:" + error);
    }
  };

  return (
    <AuthFormWrapper>
      <h2>Login</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          required
          onChange={(e) => setEmail(e.target.value)}
          style={styles.input}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          required
          onChange={(e) => setPassword(e.target.value)}
          style={styles.input}
        />
        <button type="submit" style={styles.button}>
          Login
        </button>
      </form>
      <p>
        Don't have an account? <Link to="/register">Create one</Link>
      </p>
    </AuthFormWrapper>
  );
};

const styles = {
  input: {
    width: "100%",
    padding: "10px",
    marginBottom: "15px",
  },
  button: {
    width: "100%",
    padding: "10px",
    backgroundColor: "#1976d2",
    color: "white",
    border: "none",
  },
};

export default Login;
