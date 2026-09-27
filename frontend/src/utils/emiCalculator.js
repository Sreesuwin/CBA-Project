/**
 * Standard EMI Calculator Utility
 * Calculates Equated Monthly Installment (EMI), Total Interest, and Total Amount Payable.
 * 
 * Formula: E = P * r * (1 + r)^n / ((1 + r)^n - 1)
 * where:
 *   P = Principal loan amount
 *   r = Monthly interest rate (annual interest rate / 12 / 100)
 *   n = Tenure in months
 */

export const calculateEMI = (principal, annualInterestRate, tenureMonths) => {
  const p = parseFloat(principal);
  const rate = parseFloat(annualInterestRate);
  const n = parseInt(tenureMonths, 10);

  if (isNaN(p) || isNaN(rate) || isNaN(n) || p <= 0 || n <= 0 || rate < 0) {
    return {
      emi: 0,
      totalPayable: 0,
      totalInterest: 0,
      monthlyRatePercent: 0,
      isValid: false,
      error: 'Please enter valid positive values for loan amount and tenure.'
    };
  }

  // Edge case: 0% Interest rate
  if (rate === 0) {
    const emi = p / n;
    return {
      emi: Math.round(emi),
      totalPayable: Math.round(p),
      totalInterest: 0,
      monthlyRatePercent: 0,
      isValid: true,
      error: null
    };
  }

  const monthlyRate = rate / 12 / 100;
  const factor = Math.pow(1 + monthlyRate, n);
  const emi = (p * monthlyRate * factor) / (factor - 1);
  const totalPayable = emi * n;
  const totalInterest = totalPayable - p;

  return {
    emi: Math.round(emi),
    totalPayable: Math.round(totalPayable),
    totalInterest: Math.round(totalInterest),
    monthlyRatePercent: (monthlyRate * 100).toFixed(2),
    isValid: true,
    error: null
  };
};

export const formatCurrency = (amount) => {
  if (isNaN(amount) || amount === null || amount === undefined) return '₹0';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(amount);
};
