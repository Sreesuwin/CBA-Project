import React from 'react';
import StatusBadge from './StatusBadge';
import { formatCurrency } from '../utils/emiCalculator';
import Button from './Button';
import { EmptyState } from './LoadingSpinner';

const ApplicationTable = ({
  applications = [],
  onViewDetails,
  showApplicantName = false,
  showRiskLevel = false,
  emptyMessage = "No loan applications found."
}) => {
  if (!applications || applications.length === 0) {
    return <EmptyState title="No Applications" message={emptyMessage} />;
  }

  const getRiskBadge = (risk) => {
    if (!risk || risk === 'NOT_ASSESSED') return <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>-</span>;
    const colors = {
      LOW: { bg: '#e6f4ea', text: '#1e7e34', border: '#b7e4c7' },
      MODERATE: { bg: '#fef3c7', text: '#d97706', border: '#fde68a' },
      HIGH: { bg: '#fce8e6', text: '#d9534f', border: '#f8b4b4' }
    };
    const style = colors[risk] || { bg: '#f3f4f6', text: '#4b5563', border: '#e5e7eb' };
    return (
      <span style={{
        backgroundColor: style.bg,
        color: style.text,
        border: `1px solid ${style.border}`,
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: 700
      }}>
        {risk}
      </span>
    );
  };

  return (
    <div className="table-responsive">
      <table className="data-table">
        <thead>
          <tr>
            <th>Application No.</th>
            {showApplicantName && <th>Applicant</th>}
            <th>Loan Product</th>
            <th>Amount</th>
            <th>Tenure</th>
            {showRiskLevel && <th>Risk Level</th>}
            <th>Date</th>
            <th>Status</th>
            <th style={{ textAlign: 'right' }}>Action</th>
          </tr>
        </thead>
        <tbody>
          {applications.map((app) => (
            <tr key={app.id}>
              <td>
                <strong style={{ color: 'var(--primary)', fontFamily: 'monospace' }}>{app.id}</strong>
              </td>
              {showApplicantName && (
                <td>
                  <div><strong>{app.applicantName}</strong></div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{app.applicantEmail}</div>
                </td>
              )}
              <td>{app.productName}</td>
              <td style={{ fontWeight: 600 }}>{formatCurrency(app.amount)}</td>
              <td>{app.tenure} mos</td>
              {showRiskLevel && (
                <td>{getRiskBadge(app.creditAssessment?.riskLevel)}</td>
              )}
              <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                {new Date(app.createdDate || Date.now()).toLocaleDateString('en-IN')}
              </td>
              <td>
                <StatusBadge status={app.status} />
              </td>
              <td style={{ textAlign: 'right' }}>
                <Button
                  variant="secondary"
                  style={{ padding: '4px 10px', fontSize: '12px' }}
                  onClick={() => onViewDetails && onViewDetails(app.id)}
                >
                  View Application
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ApplicationTable;
