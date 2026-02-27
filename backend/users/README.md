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
