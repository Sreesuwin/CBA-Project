/**
 * Form Validation Utilities for Loan Application & Auth Forms
 */

export const validateEmail = (email) => {
  if (!email || !email.trim()) return 'Email address is required.';
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email.trim())) return 'Please enter a valid email address (e.g., user@domain.com).';
  return null;
};

export const validatePassword = (password) => {
  if (!password) return 'Password is required.';
  if (password.length < 8) return 'Password must be at least 8 characters long.';
  if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
    return 'Password must contain at least one letter and one number.';
  }
  return null;
};

export const validatePhone = (phone) => {
  if (!phone || !phone.trim()) return 'Phone number is required.';
  const phoneRegex = /^[6-9]\d{9}$/;
  if (!phoneRegex.test(phone.trim().replace(/[\s-]/g, ''))) {
    return 'Please enter a valid 10-digit mobile number.';
  }
  return null;
};

export const validateRequired = (value, fieldName = 'This field') => {
  if (value === null || value === undefined || (typeof value === 'string' && !value.trim())) {
    return `${fieldName} is required.`;
  }
  return null;
};

export const validateNumberMin = (value, min, fieldName = 'Value') => {
  const num = Number(value);
  if (isNaN(num)) return `${fieldName} must be a valid number.`;
  if (num < min) return `${fieldName} must be at least ${min}.`;
  return null;
};

/**
 * Validates step 4 (Loan Details) against selected product bounds
 */
export const validateLoanDetails = (amount, tenure, product) => {
  const errors = {};

  if (!product) {
    errors.product = 'Please select a loan product.';
    return errors;
  }

  const numAmount = Number(amount);
  if (!amount || isNaN(numAmount)) {
    errors.amount = 'Please enter a valid loan amount.';
  } else if (numAmount < product.minAmount) {
    errors.amount = `Loan amount cannot be less than ₹${product.minAmount.toLocaleString('en-IN')} for ${product.name}.`;
  } else if (numAmount > product.maxAmount) {
    errors.amount = `Loan amount cannot exceed ₹${product.maxAmount.toLocaleString('en-IN')} for ${product.name}.`;
  }

  const numTenure = Number(tenure);
  if (!tenure || isNaN(numTenure)) {
    errors.tenure = 'Please enter a valid tenure in months.';
  } else if (numTenure < product.minTenure) {
    errors.tenure = `Tenure cannot be less than ${product.minTenure} months for ${product.name}.`;
  } else if (numTenure > product.maxTenure) {
    errors.tenure = `Tenure cannot exceed ${product.maxTenure} months for ${product.name}.`;
  }

  return errors;
};
