import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { validateEmail, validatePassword, validateRequired } from '../utils/validation';
import Button from '../components/Button';
import Card from '../components/Card';
import heroBanking from '../assets/hero-banking.svg';

const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: ''
  });

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

    const newErrors = {};
    const nameErr = validateRequired(formData.fullName, 'Full Name');
    const emailErr = validateEmail(formData.email);
    const passErr = validatePassword(formData.password);

    if (nameErr) newErrors.fullName = nameErr;
    if (emailErr) newErrors.email = emailErr;
    if (passErr) newErrors.password = passErr;
    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match.';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setIsLoading(true);
    try {
      await register({
        name: formData.fullName,
        email: formData.email,
        password: formData.password
      });
      navigate('/customer/dashboard');
    } catch (err) {
      setServerError(err.message || 'Registration failed. Please try again.');
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
          Join the CBA lending platform
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '10px', maxWidth: '440px' }}>
          Create an account to browse products, submit a loan application and track
          its assessment transparently from draft to decision.
        </p>
        <img
          src={heroBanking}
          alt="Banking and credit assessment illustration"
          style={{ width: '100%', maxWidth: '440px', marginTop: '12px', alignSelf: 'center' }}
        />
      </div>

      {/* REGISTRATION FORM */}
      <div style={{ flex: '0 1 460px', maxWidth: '460px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--primary)' }}>
            Create Customer Account
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Register to apply for digital loans &amp; track assessments
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
              <label className="form-label" htmlFor="fullName">
                Full Name <span className="required">*</span>
              </label>
              <input
                id="fullName"
                type="text"
                name="fullName"
                className={`form-control ${errors.fullName ? 'is-invalid' : ''}`}
                placeholder="e.g. Rahul Kumar"
                value={formData.fullName}
                onChange={handleChange}
              />
              {errors.fullName && <div className="form-error">{errors.fullName}</div>}
            </div>

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
                placeholder="Min 8 characters with letters & numbers"
                value={formData.password}
                onChange={handleChange}
              />
              {errors.password && <div className="form-error">{errors.password}</div>}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="confirmPassword">
                Confirm Password <span className="required">*</span>
              </label>
              <input
                id="confirmPassword"
                type="password"
                name="confirmPassword"
                className={`form-control ${errors.confirmPassword ? 'is-invalid' : ''}`}
                placeholder="Re-enter password"
                value={formData.confirmPassword}
                onChange={handleChange}
              />
              {errors.confirmPassword && <div className="form-error">{errors.confirmPassword}</div>}
            </div>

            <Button
              type="submit"
              variant="primary"
              isLoading={isLoading}
              style={{ width: '100%', marginTop: '8px' }}
            >
              Complete Registration
            </Button>
          </form>

          <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-color)', textAlign: 'center' }}>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Already registered?{' '}
              <Link to="/login" style={{ fontWeight: 600 }}>Sign In</Link>
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Register;
