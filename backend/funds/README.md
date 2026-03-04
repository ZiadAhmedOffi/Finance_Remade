# Funds App

The `funds` app manages the core business entities: Funds, their financial modeling parameters (Model Inputs), and their investment portfolios (Deals).

## Models

- **Fund**: The central entity representing a private equity or venture capital fund.
- **ModelInput**: A one-to-one relationship with `Fund` that stores 15 financial parameters used for projections and dashboards.
- **InvestmentDeal**: Represents individual investments made by a fund, tracking amounts and statuses.
- **FundLog**: A fund-specific audit log for tracking changes to fund information, model inputs, and deals.

## Features

- **Model Inputs**: Provides a specialized set of parameters (fees, carries, tickers, etc.) to model fund performance.
- **Calculated Metrics**: Real-time calculation of "Average Ticket" and "Expected Number of Investors" based on model inputs.
- **Investment Tracking**: CRUD operations for investment deals tied to specific funds.
- **Role-Based Access**:
    - **View**: Accessible to anyone assigned a role (SC or Investor) in the fund.
    - **Edit**: Restricted to **Super Admins** and **Steering Committee** members for that specific fund.

## Logic and Flow

1. **Automatic Initialization**: When a new `Fund` is created, a `ModelInput` instance is automatically generated with system default values via a Django `post_save` signal.
2. **Permission Enforcement**: All views utilize the `PermissionService` to ensure only authorized users can modify sensitive financial data or portfolio details.
3. **Audit Logging**: Every modification (updating inputs, creating/deleting deals) is logged twice:
    - In `FundLog` for a granular, fund-focused history.
    - In the global `AuditLog` (via `AuditService`) for centralized security monitoring.
4. **Serialization**: Special care is taken in views to ensure `UUID` and `Decimal` objects are JSON-serialized (converted to strings) before being stored in audit log metadata.

## API Endpoints

- `GET /api/funds/`: List all funds the current user is associated with (or all active funds for Super Admins).
- `POST /api/funds/`: Create a new fund (Super Admin only).
- `GET /api/funds/<uuid:id>/`: Get detailed information about a fund.
- `PUT /api/funds/<uuid:id>/`: Update fund name or description (SC/Admin only).
- `DELETE /api/funds/<uuid:id>/`: Deactivate a fund (Super Admin only).
- `GET /api/funds/<uuid:id>/logs/`: View the audit log for a specific fund.
- `GET /api/funds/<uuid:id>/model-inputs/`: Retrieve modeling parameters.
- `PUT /api/funds/<uuid:id>/model-inputs/`: Update modeling parameters (SC/Admin only).
- `GET /api/funds/<uuid:id>/deals/`: List all investment deals for the fund.
- `POST /api/funds/<uuid:id>/deals/`: Create a new investment deal (SC/Admin only).
- `PUT /api/funds/<uuid:id>/deals/<uuid:deal_id>/`: Update a specific deal.
- `DELETE /api/funds/<uuid:id>/deals/<uuid:deal_id>/`: Remove an investment deal.
