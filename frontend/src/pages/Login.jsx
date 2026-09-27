import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth, DEMO_ACCOUNTS } from '../context/AuthContext';
import { validateEmail, validatePassword } from '../utils/validation';
import Button from '../components/Button';
import Card from '../components/Card';
import heroBanking from '../assets/hero-banking.svg';

const DASHBOARD_BY_ROLE = {
  CUSTOMER: '/customer/dashboard',
  LOAN_OFFICER: '/officer/dashboard',
  ADMIN: '/admin/dashboard'
};

const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');

    const emailErr = validateEmail(formData.email);
    const passErr = validatePassword(formData.password);
    if (emailErr || passErr) {
      setErrors({ email: emailErr, password: passErr });
      return;
    }

    setIsLoading(true);
    try {
      const user = await login(formData.email, formData.password);
      navigate(DASHBOARD_BY_ROLE[user.role] || '/');
    } catch (err) {
      setServerError(err.message || 'Invalid credentials. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickDemoLogin = async (role) => {
    const creds = DEMO_ACCOUNTS[role];
    if (!creds) return;
    setServerError('');
    setIsLoading(true);
    try {
      const user = await login(creds.email, creds.password);
      navigate(DASHBOARD_BY_ROLE[user.role] || '/');
    } catch (err) {
      setServerError(
        `${err.message || 'Demo login failed.'} Run "flask seed-db --reset" to create the demo accounts.`
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexWrap: 'wrap',
      justifyContent: 'center',
      alignItems: 'stretch',
      gap: '32px',
      minHeight: 'calc(100vh - 120px)',
      padding: '24px'
    }}>
      {/* HERO PANEL */}
      <div style={{
        flex: '1 1 360px',
        maxWidth: '520px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        background: 'linear-gradient(160deg, #eff6ff 0%, #dbeafe 100%)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '28px'
      }}>
        <h1 style={{ fontSize: '28px', fontWeight: 800, color: 'var(--primary)', lineHeight: 1.2 }}>
          Transparent, rule-based credit assessment
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '10px', maxWidth: '440px' }}>
          Apply for a loan, watch it move through underwriting, and see exactly which
          financial rules produced your score, risk level and recommendation.
        </p>
        <img
          src={heroBanking}
          alt="Banking and credit assessment illustration"
          style={{ width: '100%', maxWidth: '440px', marginTop: '12px', alignSelf: 'center' }}
        />
      </div>

      {/* LOGIN FORM */}
      <div style={{ flex: '0 1 420px', maxWidth: '420px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--primary)' }}>
            Financial Portal Login
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Sign in to access your loan account &amp; credit dashboard
          </p>
        </div>

        <Card>
          {serverError && (
            <div style={{
              backgroundColor: 'var(--bg-rejected)',
              color: 'var(--color-rejected)',
              border: '1px solid #f8b4b4',
              padding: '10px 14px',
              borderRadius: '4px',
              fontSize: '13px',
              marginBottom: '16px'
            }}>
              ⚠️ {serverError}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="form-group">
              <label className="form-label" htmlFor="email">
                Email Address <span className="required">*</span>
              </label>
              <input
                id="email"
                type="email"
                name="email"
                className={`form-control ${errors.email ? 'is-invalid' : ''}`}
                placeholder="e.g. rahul.kumar@example.test"
                value={formData.email}
                onChange={handleChange}
              />
              {errors.email && <div className="form-error">{errors.email}</div>}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="password">
                Password <span className="required">*</span>
              </label>
              <input
                id="password"
                type="password"
                name="password"
                className={`form-control ${errors.password ? 'is-invalid' : ''}`}
                placeholder="••••••••"
                value={formData.password}
                onChange={handleChange}
              />
              {errors.password && <div className="form-error">{errors.password}</div>}
            </div>

            <Button
              type="submit"
              variant="primary"
              isLoading={isLoading}
              style={{ width: '100%', marginTop: '8px' }}
            >
              Sign In
            </Button>
          </form>

          <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-color)', textAlign: 'center' }}>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Don't have an account?{' '}
              <Link to="/register" style={{ fontWeight: 600 }}>Register Now</Link>
            </p>
          </div>
        </Card>

        {/* Quick Demo Access Bar */}
        <div style={{
          backgroundColor: '#ffffff',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '14px',
          marginTop: '16px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase' }}>
            ⚡ Demo Quick Portal Logins
          </div>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <Button variant="secondary" onClick={() => handleQuickDemoLogin('CUSTOMER')} style={{ padding: '4px 8px', fontSize: '11px' }}>
              As Customer
            </Button>
            <Button variant="secondary" onClick={() => handleQuickDemoLogin('LOAN_OFFICER')} style={{ padding: '4px 8px', fontSize: '11px' }}>
              As Officer
            </Button>
            <Button variant="secondary" onClick={() => handleQuickDemoLogin('ADMIN')} style={{ padding: '4px 8px', fontSize: '11px' }}>
              As Admin
            </Button>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
            Seeded accounts · password <code>Password@123</code>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
