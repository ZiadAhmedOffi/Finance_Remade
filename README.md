# FinanceRemade - Fund Management & Performance Analytics

FinanceRemade is a robust, enterprise-grade web application designed for private equity and venture capital fund managers. It provides comprehensive tools for financial modeling, deal prognosis, performance tracking, and automated reporting.

## 🚀 Features

- **Dynamic Dashboards:** Real-time visualization of fund performance using interactive charts (Waterfall, Base Points, Capital Appreciation).
- **Deal Prognosis:** Manage investment deals with scenario-based modeling (Base, Upside, Downside) and automated holding period calculations.
- **Financial Modeling:** Configurable fund parameters including management fees, admin costs, and carry tiers.
- **Automated Reporting:** Year-by-year breakdown of G&A costs, operations fees, and capital injections.
- **Audit & Compliance:** Detailed action logs and role-based access control (Super Admin, Steering Committee, Investor).
- **Modern UI:** Responsive, intuitive interface built with React 19 and styled for enterprise efficiency.

## 🛠 Tech Stack

### Backend
- **Framework:** Django 5.x
- **API:** Django Rest Framework (DRF)
- **Database:** PostgreSQL (recommended) / SQLite (development)
- **Authentication:** JWT (JSON Web Tokens)
- **Calculations:** NumPy-inspired IRR and MOIC algorithms

### Frontend
- **Framework:** React 19 (TypeScript)
- **Tooling:** Vite
- **Visualization:** Recharts
- **Styling:** Vanilla CSS3 with modern CSS variables
- **State Management:** React Hooks (useState, useEffect, useMemo)

## 📦 Project Structure

```text
.
├── backend/                # Django project root
│   ├── backend_app/        # Project configuration (settings, urls)
│   ├── funds/              # Core business logic (Funds, Deals, Performance)
│   └── users/              # User management, roles, and permissions
├── frontend/               # Frontend root
│   └── frontend-app/       # React application source code
└── README.md               # Project documentation
```

## 🛠 Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 20+
- npm 10+

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the development server:
   ```bash
   python manage.py runserver
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend/frontend-app
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## 🔐 Role-Based Access Control

- **Super Admin:** Full access to all funds, user management, and system logs.
- **Steering Committee:** Edit access to specific assigned funds (Deals, Model Inputs, Basic Info).
- **Investor:** Read-only access to assigned fund performance dashboards and reports.

## 📄 License

This project is proprietary and confidential. Unauthorized copying or distribution is strictly prohibited.
