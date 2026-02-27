# Finance Remade Frontend

This is the frontend for the Finance Remade application, built with React, TypeScript, and Vite.

## Project Structure

- `src/`: Main source code directory.
  - `api/`: API configuration and Axios interceptors for handling authentication.
  - `components/`: Reusable UI components.
  - `pages/`: Page-level components (Login, Dashboard, Admin, Profile).
  - `App.tsx`: Root component with routing and session expiry logic.
- `public/`: Static public assets.
- `package.json`: Project dependencies and scripts.
- `vite.config.ts`: Vite configuration for development and building.

## Key Features

- **Authentication Flow**: Supports user login, registration, and private routes.
- **Admin Dashboard**: Comprehensive management of user applications, roles, and audit logs.
- **Session Expiry Management**: Automatically detects expired sessions and redirects users to the login page.
- **Role-Based Views**: Conditionally renders UI elements based on the current user's role.
- **Paginated Lists**: Efficiently displays large numbers of active users and audit logs.

## Setup and Installation

1. Install dependencies:
   ```bash
   npm install
   ```
2. Start the development server:
   ```bash
   npm run dev
   ```
3. Build for production:
   ```bash
   npm run build
   ```

## Development Standards

- **TypeScript**: Use strong typing for all interfaces and state variables.
- **API Requests**: Always use the central `api` instance from `src/api/api.ts` to ensure authentication headers are included.
- **Hooks**: Use `useCallback` for functions passed as dependencies to `useEffect` to prevent unnecessary re-renders.
- **Styling**: Prefer vanilla CSS for maximum flexibility and consistency across the application.
