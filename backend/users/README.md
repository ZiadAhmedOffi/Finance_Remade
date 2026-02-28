# Users App

The `users` app handles all authentication, authorization, and audit logging for the application.

## Models

- **User**: Custom user model inheriting from `AbstractBaseUser` and `PermissionsMixin`.
- **Role**: Flexible system of roles (SUPER_ADMIN, ACCESS_MANAGER, etc.).
- **Fund**: Reference for fund associations with roles.
- **UserRoleAssignment**: Pivot model linking users, roles, and funds.
- **AuditLog**: Immutable log of security and administrative events.

## Services

- **PermissionService**: Contains logic for checking if a user has specific permissions or roles.
- **AuditService**: Provides a centralized way to log security-sensitive events.

## Authentication Flow

This project uses **JWT (JSON Web Tokens)** for stateless authentication.

### Flow of Requests

1. **Login Submission**: The user submits their credentials (email and password) to the `/api/users/token/` endpoint via the frontend `LoginPage`.
2. **Credential Validation**:
    - The `CustomTokenObtainPairSerializer` in the backend receives the request.
    - It validates the user's existence, checks if the password is correct using Django's `check_password`.
    - It verifies that the user is `ACTIVE` and not `DELETED`.
3. **Token Generation**:
    - If valid, `get_token` is called on the serializer to generate a **Refresh Token** and an **Access Token**.
    - Custom claims are injected into the token: `email`, `is_staff`, `is_superuser`, and a list of `roles` (including fund names).
4. **Token Storage**:
    - The backend returns both tokens in the response.
    - The frontend stores these tokens in `localStorage` as `access_token` and `refresh_token`.
5. **Authenticated Requests**:
    - For every subsequent API call, the frontend `api` interceptor (in `api.ts`) automatically attaches the `access_token` to the `Authorization: Bearer <token>` header.
6. **Token Invalidation**:
    - When a user visits the `Login` or `Register` pages, any existing tokens are removed from `localStorage` to ensure a clean session.

### Tokens and Their Purposes

- **Access Token**: Short-lived token used to authenticate requests to protected API endpoints. It contains user claims allowing the backend to identify the user and their roles without a database lookup for every request.
- **Refresh Token**: Longer-lived token used to obtain a new Access Token once it expires, without requiring the user to re-enter their credentials.

### Key Endpoints & Functions

- `POST /api/users/token/`: Handled by `CustomTokenObtainPairView`.
- `CustomTokenObtainPairSerializer.validate()`: Performs user validation and audit logging.
- `CustomTokenObtainPairSerializer.get_token()`: Injects custom role-based claims into the JWT payload.

## API Endpoints

- `POST /api/users/token/`: Obtain JWT access and refresh tokens.
- `POST /api/users/apply/`: Submit a user application for review.
- `GET /api/users/pending/`: List all pending applications (Admin/Manager only).
- `GET /api/users/active/`: List all active users with pagination (Admin/Manager only).
- `POST /api/users/approve/<uuid:user_id>/`: Approve a pending application.
- `POST /api/users/reject/<uuid:user_id>/`: Reject a pending application.
- `POST /api/users/assign-role/<uuid:user_id>/`: Assign a new role and optionally a fund.
- `POST /api/users/remove-role/<uuid:user_id>/`: Remove an assigned role from a user.
- `GET /api/users/logs/`: List all system audit logs with pagination and user emails.

## Internal Logic

1. **User Approval**: When a user is approved, their `status` is set to `ACTIVE` and `is_active` to `True`.
2. **Audit Retention**: Soft-deletion (`is_deleted`) is preferred over physical deletion to maintain audit integrity.
3. **Role Validation**: Super Admin roles can only be assigned or removed by other Super Admins.
