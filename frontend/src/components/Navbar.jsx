import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Button from './Button';
import brandLogo from '../assets/brand-logo.svg';

const Navbar = () => {
  const { currentUser, isLoggedIn, logout, switchRole } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleRoleChange = async (e) => {
    const selectedRole = e.target.value;
    try {
      // Switching roles means signing in as the seeded account for that role;
      // it is a real login, not a local flag flip.
      await switchRole(selectedRole);
      if (selectedRole === 'CUSTOMER') navigate('/customer/dashboard');
      if (selectedRole === 'LOAN_OFFICER') navigate('/officer/dashboard');
      if (selectedRole === 'ADMIN') navigate('/admin/dashboard');
    } catch (err) {
      alert(err.message || 'Could not switch demo role.');
      logout();
      navigate('/login');
    }
  };

  return (
    <header style={{
      backgroundColor: 'var(--primary)',
      color: '#ffffff',
      borderBottom: '3px solid var(--accent)',
      padding: '12px 24px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
    }}>
      <div style={{
        maxWidth: '1400px',
        margin: '0 auto',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Link to="/" style={{ color: '#ffffff', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <img
              src={brandLogo}
              alt="CBA Financial logo"
              width="34"
              height="34"
              style={{ borderRadius: '6px', display: 'block' }}
            />
            <div>
              <div style={{ fontSize: '16px', fontWeight: 800, letterSpacing: '0.5px' }}>
                CBA FINANCIAL
              </div>
              <div style={{ fontSize: '10px', color: '#a0aec0', letterSpacing: '1px' }}>
                LOAN & CREDIT ASSESSMENT PLATFORM
              </div>
            </div>
          </Link>
        </div>

        {isLoggedIn ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            {/* Quick Demo Role Switcher */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: 'rgba(255,255,255,0.1)', padding: '4px 12px', borderRadius: '20px' }}>
              <span style={{ fontSize: '11px', color: '#cbd5e1', fontWeight: 600 }}>DEMO ROLE:</span>
              <select
                value={currentUser.role}
                onChange={handleRoleChange}
                style={{
                  background: 'transparent',
                  color: '#ffffff',
                  border: 'none',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  outline: 'none'
                }}
              >
                <option value="CUSTOMER" style={{ color: '#000' }}>CUSTOMER</option>
                <option value="LOAN_OFFICER" style={{ color: '#000' }}>LOAN OFFICER</option>
                <option value="ADMIN" style={{ color: '#000' }}>ADMINISTRATOR</option>
              </select>
            </div>

            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '13px', fontWeight: 700 }}>{currentUser.name}</div>
              <div style={{ fontSize: '11px', color: '#94a3b8' }}>{currentUser.role}</div>
            </div>

            <Button variant="secondary" onClick={handleLogout} style={{ padding: '6px 12px', fontSize: '12px' }}>
              Logout
            </Button>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: '12px' }}>
            <Link to="/login">
              <Button variant="secondary" style={{ padding: '6px 14px', fontSize: '12px' }}>Login</Button>
            </Link>
            <Link to="/register">
              <Button variant="primary" style={{ padding: '6px 14px', fontSize: '12px', backgroundColor: 'var(--accent)' }}>Register</Button>
            </Link>
          </div>
        )}
      </div>
    </header>
  );
};

export default Navbar;
