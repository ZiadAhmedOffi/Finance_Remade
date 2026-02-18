import React, { useState } from 'react';

interface RegisterData {
  fullName: string;
  email: string;
  company: string;
  fund: string;
}

interface FormErrors {
  fullName?: string;
  email?: string;
  company?: string;
  fund?: string;
}

const RegisterPage: React.FC = () => {
  const [formData, setFormData] = useState<RegisterData>({
    fullName: '',
    email: '',
    company: '',
    fund: '',
  });

  const [errors, setErrors] = useState<FormErrors>({});

  const validate = (): boolean => {
    const newErrors: FormErrors = {};
    if (!formData.fullName.trim()) newErrors.fullName = 'Full name is required';
    if (!formData.email.includes('@')) newErrors.email = 'Please enter a valid email';
    if (formData.company.length < 2) newErrors.company = 'Company name is too short';
    if (formData.fund === '') newErrors.fund = 'Please select a fund of interest';
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (validate()) {
      console.log('Application Submitted:', formData);
      // Proceed with API call
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] flex items-center justify-center p-4">
      <div className="w-full max-w-[480px]">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 md:p-10">
          <header className="mb-8 text-center">
            <h1 className="text-2xl font-bold text-slate-900">Join the Beta</h1>
            <p className="text-slate-500 mt-2 text-sm">Submit your application to get early access.</p>
          </header>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Full Name */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Full Name</label>
              <input
                name="fullName"
                type="text"
                className={`w-full px-4 py-2.5 bg-white border ${errors.fullName ? 'border-red-500' : 'border-slate-300'} rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-600/20`}
                placeholder="Jane Doe"
                onChange={handleChange}
              />
              {errors.fullName && <p className="text-red-500 text-xs mt-1">{errors.fullName}</p>}
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Work Email</label>
              <input
                name="email"
                type="email"
                className={`w-full px-4 py-2.5 bg-white border ${errors.email ? 'border-red-500' : 'border-slate-300'} rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-600/20`}
                placeholder="jane@company.com"
                onChange={handleChange}
              />
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
            </div>

            {/* Company */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Company Name</label>
              <input
                name="company"
                type="text"
                className={`w-full px-4 py-2.5 bg-white border ${errors.company ? 'border-red-500' : 'border-slate-300'} rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-600/20`}
                placeholder="Acme Corp"
                onChange={handleChange}
              />
              {errors.company && <p className="text-red-500 text-xs mt-1">{errors.company}</p>}
            </div>

            {/* Fund of Interest */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Fund of Interest</label>
              <select
                name="fund"
                className={`w-full px-4 py-2.5 bg-white border ${errors.fund ? 'border-red-500' : 'border-slate-300'} rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-600/20`}
                value={formData.fund}
                onChange={handleChange}
              >
                <option value="">Select a role</option>
                <option value="iv1">IV1 - Secondary Exits</option>
                <option value="iv2">IV2 - Cross Border Opportunities</option>
              </select>
              {errors.fund && <p className="text-red-500 text-xs mt-1">{errors.fund}</p>}
            </div>

            <button
              type="submit"
              className="w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3 px-4 rounded-xl transition-colors duration-200 mt-2"
            >
              Apply
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;