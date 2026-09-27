import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Sidebar = () => {
  const { userRole } = useAuth();

  const customerLinks = [
    { path: '/customer/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/customer/products', label: 'Loan Products', icon: '💳' },
    { path: '/customer/apply', label: 'Apply for Loan', icon: '📝' },
    { path: '/customer/emi', label: 'EMI Calculator', icon: '🧮' },
  ];

  const officerLinks = [
    { path: '/officer/dashboard', label: 'Review Queue', icon: '📋' },
  ];

  const adminLinks = [
    { path: '/admin/dashboard', label: 'Admin Panel', icon: '⚙️' },
  ];

  let links = [];
  if (userRole === 'CUSTOMER') links = customerLinks;
  if (userRole === 'LOAN_OFFICER') links = officerLinks;
  if (userRole === 'ADMIN') links = adminLinks;

  return (
    <aside style={{
      width: '240px',
      backgroundColor: '#ffffff',
      borderRight: '1px solid var(--border-color)',
      padding: '20px 12px',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      minHeight: 'calc(100vh - 60px)'
    }}>
      <div style={{
        fontSize: '11px',
        fontWeight: 700,
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        padding: '0 12px 8px 12px'
      }}>
        {userRole.replace('_', ' ')} PORTAL
      </div>

      {links.map((link) => (
        <NavLink
          key={link.path}
          to={link.path}
          className={({ isActive }) =>
            `sidebar-link ${isActive ? 'active' : ''}`
          }
          style={({ isActive }) => ({
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '10px 14px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: isActive ? 700 : 500,
            color: isActive ? 'var(--primary)' : 'var(--text-main)',
            backgroundColor: isActive ? 'var(--primary-light)' : 'transparent',
            textDecoration: 'none',
            transition: 'background-color 0.15s ease'
          })}
        >
          <span style={{ fontSize: '16px' }}>{link.icon}</span>
          <span>{link.label}</span>
        </NavLink>
      ))}

      <div style={{ marginTop: 'auto', padding: '12px', borderTop: '1px solid var(--border-color)', fontSize: '11px', color: 'var(--text-muted)' }}>
        <div>CBA Platform v1.0</div>
        <div>REST API Ready Mode</div>
      </div>
    </aside>
  );
};

export default Sidebar;
