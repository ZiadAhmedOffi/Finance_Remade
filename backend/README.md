# Finance Remade Backend

This is the backend for the Finance Remade application, built with Django and Django REST Framework.

## Project Structure

- `backend_app/`: Main Django project configuration (settings, URLs, ASGI/WSGI).
- `users/`: User management app (Authentication, Roles, Audit Logs, Profiles).
- `static/`: Static files for Django Admin.
- `manage.py`: Django management utility.

## Key Features

- **Custom User Model**: Uses email as the primary identifier and supports soft-deletion.
- **Role-Based Access Control (RBAC)**: Supports roles like `SUPER_ADMIN`, `ACCESS_MANAGER`, `INVESTOR`, and `STEERING_COMMITTEE`.
- **Audit Logging**: Tracks critical system events (logins, role changes, user approvals).
- **JWT Authentication**: Secure stateless authentication using `djangorestframework-simplejwt`.

## Setup and Installation

1. Create and activate a virtual environment:
   ```bash
   python -m venv backend-venv
   source backend-venv/bin/activate
   ```
2. Install dependencies (ensure `requirements.txt` is up-to-date or manually install `django`, `djangorestframework`, `django-cors-headers`, `djangorestframework-simplejwt`).
3. Run migrations:
   ```bash
   python manage.py migrate
   ```
4. Start the server:
   ```bash
   python manage.py runserver
   ```

## Development Standards

- **Models**: Use UUIDs for primary keys to enhance security and portability.
- **API Views**: Prefer class-based views (APIView) for explicit control.
- **Audit Logging**: Use `AuditService.log` to record important actions.
