import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api/api";

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();

  React.useEffect(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }, []);

  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    first_name: "",
    last_name: "",
    company: "",
    job_title: "",
    phone_number: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    try {
      const response = await api.post("/users/apply/", {
        email: formData.email,
        password: formData.password,
        first_name: formData.first_name,
        last_name: formData.last_name,
        company: formData.company,
        job_title: formData.job_title,
        phone_number: formData.phone_number,
      });

      setSuccess(response.data.message);
      // clear form
      setFormData({
        email: "",
        password: "",
        confirmPassword: "",
        first_name: "",
        last_name: "",
        company: "",
        job_title: "",
        phone_number: "",
      });

      setTimeout(() => {
        navigate("/login");
      }, 3000);
    } catch (err: any) {
      if (err.response && err.response.data) {
        const errorMessages = Object.values(err.response.data).flat();
        setError(errorMessages.join(" "));
      } else {
        setError("Registration failed. Please try again.");
      }
      console.error(err);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] flex items-center justify-center p-4">
      <div className="w-full max-w-[480px]">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 md:p-10">
          <header className="mb-8 text-center">
            <h1 className="text-2xl font-bold text-slate-900">
              Apply for Access
            </h1>
            <p className="text-slate-500 mt-2 text-sm">
              Submit your application to get access to the platform.
            </p>
          </header>

          {error && (
            <div
              className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4"
              role="alert"
            >
              <span className="block sm:inline">{error}</span>
            </div>
          )}

          {success && (
            <div
              className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mb-4"
              role="alert"
            >
              <span className="block sm:inline">{success}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="flex space-x-4">
              <div className="w-1/2">
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  First Name
                </label>
                <input
                  name="first_name"
                  type="text"
                  className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-600/20"
                  placeholder="John"
                  onChange={handleChange}
                  value={formData.first_name}
                  required
                />
              </div>
              <div className="w-1/2">
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  Last Name
                </label>
                <input
                  name="last_name"
                  type="text"
                  className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-600/20"
                  placeholder="Doe"
                  onChange={handleChange}
                  value={formData.last_name}
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Work Email
              </label>
              <input
                name="email"
                type="email"
                className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-600/20"
                placeholder="john.doe@company.com"
                onChange={handleChange}
                value={formData.email}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Password
              </label>
              <input
                name="password"
                type="password"
                className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-600/20"
                placeholder="Enter your password"
                onChange={handleChange}
                value={formData.password}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Confirm Password
              </label>
              <input
                name="confirmPassword"
                type="password"
                className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-600/20"
                placeholder="Re-enter your password"
                onChange={handleChange}
                value={formData.confirmPassword}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Company Name
              </label>
              <input
                name="company"
                type="text"
                className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-600/20"
                placeholder="Acme Inc."
                onChange={handleChange}
                value={formData.company}
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Job Title
              </label>
              <input
                name="job_title"
                type="text"
                className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-600/20"
                placeholder="Software Engineer"
                onChange={handleChange}
                value={formData.job_title}
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Phone Number
              </label>
              <input
                name="phone_number"
                type="text"
                className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-600/20"
                placeholder="+1234567890"
                onChange={handleChange}
                value={formData.phone_number}
              />
            </div>

            <button
              type="submit"
              className="w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3 px-4 rounded-xl transition-colors duration-200 mt-2"
            >
              Apply for Access
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-8">
            Already have an account?{" "}
            <Link
              to="/login"
              className="font-semibold text-indigo-600 hover:text-indigo-500"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;