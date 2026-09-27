import React, { useState } from 'react';
import { calculateEMI, formatCurrency } from '../../utils/emiCalculator';
import Card from '../../components/Card';
import Button from '../../components/Button';

const CustomerEmiCalculator = () => {
  const [inputs, setInputs] = useState({
    amount: '500000',
    rate: '10.5',
    tenure: '48'
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setInputs((prev) => ({ ...prev, [name]: value }));
  };

  const result = calculateEMI(inputs.amount, inputs.rate, inputs.tenure);

  const handleReset = () => {
    setInputs({ amount: '500000', rate: '10.5', tenure: '48' });
  };

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">EMI & Financial Loan Calculator</h1>
          <p className="page-subtitle">
            Calculate your estimated monthly installment (EMI), total interest payable, and total loan cost.
          </p>
        </div>
      </div>

      <div className="grid-2">
        {/* INPUT FORM PANEL */}
        <Card title="Loan Calculation Parameters">
          <div className="form-group">
            <label className="form-label">Loan Principal Amount (₹)</label>
            <input
              type="number"
              name="amount"
              min="0"
              className="form-control"
              value={inputs.amount}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Annual Interest Rate (% p.a.)</label>
            <input
              type="number"
              name="rate"
              step="0.1"
              min="0"
              className="form-control"
              value={inputs.rate}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Loan Tenure (Months)</label>
            <input
              type="number"
              name="tenure"
              min="1"
              className="form-control"
              value={inputs.tenure}
              onChange={handleChange}
            />
          </div>

          <Button variant="secondary" onClick={handleReset} style={{ width: '100%', marginTop: '8px' }}>
            Reset Parameters
          </Button>
        </Card>

        {/* CALCULATION BREAKDOWN RESULTS */}
        <Card title="Payment Summary Breakdown">
          {result.isValid ? (
            <div>
              <div style={{
                backgroundColor: 'var(--primary-light)',
                padding: '20px',
                borderRadius: '6px',
                textAlign: 'center',
                marginBottom: '20px',
                border: '1px solid #bfdbfe'
              }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>
                  ESTIMATED MONTHLY EMI
                </div>
                <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--primary)' }}>
                  {formatCurrency(result.emi)}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Per Month for {inputs.tenure} Months
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Principal Amount:</span>
                  <strong>{formatCurrency(inputs.amount)}</strong>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Total Interest Payable:</span>
                  <strong style={{ color: 'var(--color-pending)' }}>{formatCurrency(result.totalInterest)}</strong>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Total Amount Payable:</span>
                  <strong style={{ color: 'var(--primary)', fontSize: '16px' }}>{formatCurrency(result.totalPayable)}</strong>
                </div>
              </div>
            </div>
          ) : (
            <div style={{
              backgroundColor: 'var(--bg-rejected)',
              color: 'var(--color-rejected)',
              padding: '16px',
              borderRadius: '6px',
              fontSize: '13px'
            }}>
              ⚠️ {result.error}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default CustomerEmiCalculator;
