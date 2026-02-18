import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/Login';
import RegisterPage from './pages/Register';

function App() {
  return (
    // 1. BrowserRouter: Syncs your UI with the URL in the browser address bar.
    <BrowserRouter>
      {/* 2. Routes: Looks through all its child routes to find a match. */}
      <Routes>
        {/* 3. Route: Links a specific path (like /login) to a Component. */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        {/* Redirect empty path to login by default */}
        <Route path="/" element={<Navigate to="/login" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;