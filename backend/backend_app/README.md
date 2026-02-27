# Finance Remade Backend Configuration

The `backend_app` directory contains the project configuration, including settings, URLs, and ASGI/WSGI applications.

## Key Files

- `settings.py`: Main configuration for the Django project (database, middleware, installed apps, JWT, CORS).
- `urls.py`: Root URL configuration, delegating sub-paths to appropriate apps (e.g., `/api/users/`).
- `asgi.py` / `wsgi.py`: ASGI/WSGI entry points for development and production deployment.

## Settings Details

- **Database**: Configured to use SQLite by default for development.
- **REST Framework**: Configured for JWT authentication using `rest_framework_simplejwt.authentication.JWTAuthentication`.
- **CORS**: Configured to allow requests from `http://localhost:5173` (Vite dev server) and `http://127.0.0.1:5173`.
- **JWT**: Access tokens expire after 5 minutes by default, and refresh tokens expire after 1 day.
