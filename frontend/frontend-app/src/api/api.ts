const API_BASE = "http://127.0.0.1:8000/api";

export async function login(email: string, password: string) {
  const response = await fetch(`${API_BASE}/users/token/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Login failed");
  }

  localStorage.setItem("access_token", data.access);
  localStorage.setItem("refresh_token", data.refresh);

  return data;
}

export async function applyForAccess(email: string, password: string) {
  const response = await fetch(`${API_BASE}/users/apply/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      Object.values(data).flat().join(" ") || "Application failed"
    );
  }

  return data;
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}