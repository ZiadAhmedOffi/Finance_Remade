# FinanceRemade - Backend API

The backend is built with Django and Django Rest Framework, providing a secure and performant API for fund management.

## 🧱 Architecture

### Data Models (`funds/models.py`)
- **Fund:** The root entity.
- **ModelInput:** One-to-one relationship with Fund, stores modeling parameters.
- **InvestmentDeal:** Many-to-one with Fund, represents individual investments.
- **FundLog:** Audit trail for fund-specific changes.

### Core Logic (`funds/views.py`)
- **FundPerformanceView:** The "Engine" of the application. Calculates IRR, MOIC, and yearly performance tables on-the-fly based on current deals and model inputs.
- **InvestmentDealListView/DetailView:** CRUD operations for deals with automatic financial metric calculation via serializers.

### Permissions (`users/permissions.py`)
- Implements custom permission classes to enforce RBAC.
- Uses JWT claims to verify user roles and fund assignments.

## 🧪 Calculations

### Internal Rate of Return (IRR)
The system calculates IRR as a geometric mean based on the Real MOIC to Investors and the Fund's Exit Horizon:
`IRR = [(Real MOIC to Investors) ^ (1 / Exit Horizon)] - 1`

### Multiples (MOIC)
- **Gross MOIC:** Gross Exit Value / Total Invested.
- **Real MOIC:** Net to Investors / Total Invested (after fees and carry).

## 🛠 Management Commands
- `python manage.py createsuperuser`: Create an initial admin account.
- `python manage.py migrate`: Apply database schema changes.
