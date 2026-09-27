import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoadingSpinner from './components/LoadingSpinner';

// Components
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';

// Customer Pages
import CustomerDashboard from './pages/customer/CustomerDashboard';
import LoanProducts from './pages/customer/LoanProducts';
import LoanApplication from './pages/customer/LoanApplication';
import ApplicationDetails from './pages/customer/ApplicationDetails';
import CustomerEmiCalculator from './pages/customer/CustomerEmiCalculator';

// Officer Pages
import OfficerDashboard from './pages/officer/OfficerDashboard';
import ReviewApplication from './pages/officer/ReviewApplication';

// Admin Pages
import AdminDashboard from './pages/admin/AdminDashboard';

/**
 * Frontend Role-based Route Protection Guard
 */
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { isLoggedIn, userRole } = useAuth();

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(userRole)) {
    if (userRole === 'CUSTOMER') return <Navigate to="/customer/dashboard" replace />;
    if (userRole === 'LOAN_OFFICER') return <Navigate to="/officer/dashboard" replace />;
    if (userRole === 'ADMIN') return <Navigate to="/admin/dashboard" replace />;
  }

  return children;
};

/**
 * App Layout Wrapper containing Navbar, Sidebar, and Content Area
 */
const AppLayout = ({ children }) => {
  const { isLoggedIn } = useAuth();

  return (
    <div className="app-container">
      <Navbar />
      <div className="main-layout">
        {isLoggedIn && <Sidebar />}
        <main className="content-area">
          {children}
        </main>
      </div>
    </div>
  );
};

const AppRoutes = () => {
  const { isLoggedIn, userRole, isLoading } = useAuth();

  // Wait for the stored session to be validated before deciding where to send
  // the user, otherwise a page refresh would flash the login screen.
  if (isLoading) {
    return (
      <AppLayout>
        <LoadingSpinner message="Restoring your session..." />
      </AppLayout>
    );
  }

  // Root redirect logic
  const getDefaultHome = () => {
    if (!isLoggedIn) return '/login';
    if (userRole === 'CUSTOMER') return '/customer/dashboard';
    if (userRole === 'LOAN_OFFICER') return '/officer/dashboard';
    if (userRole === 'ADMIN') return '/admin/dashboard';
    return '/login';
  };

  return (
    <AppLayout>
      <Routes>
        {/* Default Home Redirect */}
        <Route path="/" element={<Navigate to={getDefaultHome()} replace />} />

        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Customer Routes */}
        <Route
          path="/customer/dashboard"
          element={
            <ProtectedRoute allowedRoles={['CUSTOMER', 'LOAN_OFFICER', 'ADMIN']}>
              <CustomerDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/customer/products"
          element={
            <ProtectedRoute allowedRoles={['CUSTOMER', 'LOAN_OFFICER', 'ADMIN']}>
              <LoanProducts />
            </ProtectedRoute>
          }
        />
        <Route
          path="/customer/apply"
          element={
            <ProtectedRoute allowedRoles={['CUSTOMER', 'LOAN_OFFICER', 'ADMIN']}>
              <LoanApplication />
            </ProtectedRoute>
          }
        />
        <Route
          path="/customer/application/:id"
          element={
            <ProtectedRoute allowedRoles={['CUSTOMER', 'LOAN_OFFICER', 'ADMIN']}>
              <ApplicationDetails />
            </ProtectedRoute>
          }
        />
        <Route
          path="/customer/emi"
          element={
            <ProtectedRoute allowedRoles={['CUSTOMER', 'LOAN_OFFICER', 'ADMIN']}>
              <CustomerEmiCalculator />
            </ProtectedRoute>
          }
        />

        {/* Loan Officer Routes */}
        <Route
          path="/officer/dashboard"
          element={
            <ProtectedRoute allowedRoles={['LOAN_OFFICER', 'ADMIN']}>
              <OfficerDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/officer/application/:id"
          element={
            <ProtectedRoute allowedRoles={['LOAN_OFFICER', 'ADMIN']}>
              <ReviewApplication />
            </ProtectedRoute>
          }
        />

        {/* Admin Routes */}
        <Route
          path="/admin/dashboard"
          element={
            <ProtectedRoute allowedRoles={['ADMIN']}>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />

        {/* Fallback Catch-all Route */}
        <Route path="*" element={<Navigate to={getDefaultHome()} replace />} />
      </Routes>
    </AppLayout>
  );
};

const App = () => {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
};

export default App;
