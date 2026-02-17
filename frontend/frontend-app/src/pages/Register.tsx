import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../api/axios";
import AuthFormWrapper from "../components/AuthFormWrapper";

const Register: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await api.post("/api/register/", {
        email,
        password,
      });

      alert("Account created successfully!");
      navigate("/");
    } catch (error) {
      alert("Error creating account:" + error);
    }
  };

  return (
    <AuthFormWrapper>
      <h2>Create Account</h2>
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
          Register
        </button>
      </form>
      <p>
        Already have an account? <Link to="/">Login</Link>
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
    backgroundColor: "#2e7d32",
    color: "white",
    border: "none",
  },
};

export default Register;
