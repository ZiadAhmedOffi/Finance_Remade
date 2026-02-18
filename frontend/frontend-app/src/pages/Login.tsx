import React, { useState } from 'react';

// Using a standard interface for our state
interface LoginCredentials {
  email: string;
  password: string;
  rememberMe: boolean;
}

const LoginPage: React.FC = () => {
  const [credentials, setCredentials] = useState<LoginCredentials>({
    email: '',
    password: '',
    rememberMe: false,
  });

  // Updated ChangeEvent handling for React 18+
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    
    setCredentials((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  // Updated FormEvent with explicit HTMLFormElement type
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    // Implementation of login logic
    console.log('Submitted:', credentials);
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] flex items-center justify-center p-4">
      <div className="w-full max-w-[440px]">
        {/* Card Container */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 md:p-10">
          <header className="mb-8">
            <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center mb-6">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-slate-900">Sign in</h1>
            <p className="text-slate-500 mt-2 text-sm">Enter your details to access the application.</p>
          </header>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-semibold text-slate-700 mb-2">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-xl text-slate-900 text-sm focus:ring-2 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all outline-none"
                placeholder="name@company.com"
                value={credentials.email}
                onChange={handleChange}
              />
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <label htmlFor="password" className="text-sm font-semibold text-slate-700">
                  Password
                </label>
                <a href="#" className="text-xs font-semibold text-indigo-600 hover:text-indigo-500">
                  Forgot?
                </a>
              </div>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-xl text-slate-900 text-sm focus:ring-2 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all outline-none"
                value={credentials.password}
                onChange={handleChange}
              />
            </div>

            <div className="flex items-center">
              <input
                id="rememberMe"
                name="rememberMe"
                type="checkbox"
                className="w-4 h-4 text-indigo-600 border-slate-300 rounded focus:ring-indigo-600 cursor-pointer"
                checked={credentials.rememberMe}
                onChange={handleChange}
              />
              <label htmlFor="rememberMe" className="ml-2 text-sm text-slate-600 cursor-pointer select-none">
                Keep me signed in
              </label>
            </div>

            <button
              type="submit"
              className="w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3 px-4 rounded-xl transition-colors duration-200 mt-2"
            >
              Sign in
            </button>
          </form>

          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-slate-200"></span></div>
            <div className="relative flex justify-center text-xs uppercase"><span className="bg-white px-2 text-slate-400">Or</span></div>
          </div>

          <button className="w-full flex items-center justify-center gap-3 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-semibold py-2.5 px-4 rounded-xl transition-all">
            <img src="https://www.svgrepo.com/show/355037/google.svg" className="w-5 h-5" alt="Google" />
            <span className="text-sm">Sign in with Google</span>
          </button>
        </div>

        <p className="text-center text-sm text-slate-500 mt-8">
          New here? <a href="#" className="font-semibold text-indigo-600 hover:text-indigo-500">Create an account</a>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;