import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Card from '../../components/Card';
import StatusBadge from '../../components/StatusBadge';
import { formatCurrency } from '../../utils/emiCalculator';
import Button from '../../components/Button';
import LoadingSpinner, { ErrorState } from '../../components/LoadingSpinner';

const ApplicationDetails = () => {
  const { id } = useParams();
  const { applications } = useAuth();
  const [app, setApp] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    const found = applications.find((a) => a.id === id);
    setApp(found || null);
    setIsLoading(false);
  }, [id, applications]);

  if (isLoading) {
    return <LoadingSpinner message="Loading application details..." />;
  }

  if (!app) {
    return (
      <ErrorState
        title="Application Not Found"
        message={`No loan application matching ID ${id} was found.`}
      />
    );
  }

  // Visual status timeline steps mapping
  const timelineSteps = [
    { key: 'DRAFT', title: 'Draft Created' },
    { key: 'SUBMITTED', title: 'Submitted' },
    { key: 'UNDER_REVIEW', title: 'Under Officer Review' },
    { key: 'FINAL_DECISION', title: 'Decision Rendered' }
  ];

  const getTimelineStatus = (stepKey) => {
    const status = app.status;
    if (stepKey === 'DRAFT') return 'completed';
    if (stepKey === 'SUBMITTED') {
      return ['SUBMITTED', 'UNDER_REVIEW', 'MORE_INFORMATION_REQUIRED', 'APPROVED', 'REJECTED'].includes(status) ? 'completed' : 'pending';
    }
    if (stepKey === 'UNDER_REVIEW') {
      return ['UNDER_REVIEW', 'MORE_INFORMATION_REQUIRED', 'APPROVED', 'REJECTED'].includes(status) ? 'completed' : 'pending';
    }
    if (stepKey === 'FINAL_DECISION') {
      if (status === 'APPROVED') return 'approved';
      if (status === 'REJECTED') return 'rejected';
      if (status === 'MORE_INFORMATION_REQUIRED') return 'more_info';
      return 'pending';
    }
    return 'pending';
  };

  const credit = app.creditAssessment || {};

  return (
    <div>
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h1 className="page-title">Application Details: {app.id}</h1>
            <StatusBadge status={app.status} />
          </div>
          <p className="page-subtitle">Submitted on {new Date(app.createdDate || Date.now()).toLocaleDateString('en-IN')}</p>
        </div>
        <Link to="/customer/dashboard">
          <Button variant="secondary">← Back to Dashboard</Button>
        </Link>
      </div>

      {/* VISUAL STATUS TIMELINE */}
      <Card title="Application Status Timeline">
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 0',
          position: 'relative'
        }}>
          {timelineSteps.map((step, idx) => {
            const state = getTimelineStatus(step.key);
            let bgColor = 'var(--bg-subtle)';
            let textColor = 'var(--text-muted)';
            let label = step.title;

            if (state === 'completed') {
              bgColor = 'var(--color-approved)';
              textColor = '#ffffff';
            } else if (state === 'approved') {
              bgColor = 'var(--color-approved)';
              textColor = '#ffffff';
              label = 'Approved';
            } else if (state === 'rejected') {
              bgColor = 'var(--color-rejected)';
              textColor = '#ffffff';
              label = 'Rejected';
            } else if (state === 'more_info') {
              bgColor = 'var(--color-info)';
              textColor = '#ffffff';
              label = 'More Info Needed';
            }

            return (
              <React.Fragment key={step.key}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
                  <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '50%',
                    backgroundColor: bgColor,
                    color: textColor,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 700,
                    fontSize: '13px',
                    marginBottom: '8px',
                    border: '2px solid var(--border-color)'
                  }}>
                    {state === 'completed' || state === 'approved' ? '✓' : state === 'rejected' ? '✖' : idx + 1}
                  </div>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-main)', textAlign: 'center' }}>
                    {label}
                  </div>
                </div>

                {idx < timelineSteps.length - 1 && (
                  <div style={{
                    flex: 1,
                    height: '2px',
                    backgroundColor: state === 'completed' ? 'var(--color-approved)' : 'var(--border-color)',
                    margin: '0 -10px 20px -10px'
                  }} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </Card>

      <div className="grid-2">
        {/* LOAN & APPLICANT INFO */}
        <Card title="Loan Summary">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div><strong>Loan Product:</strong> {app.productName}</div>
            <div><strong>Requested Amount:</strong> {formatCurrency(app.amount)}</div>
            <div><strong>Tenure:</strong> {app.tenure} Months</div>
            <div><strong>Purpose:</strong> {app.purpose}</div>
            <div><strong>Monthly Income:</strong> {formatCurrency(app.monthlyIncome)}</div>
            <div><strong>Existing EMI:</strong> {formatCurrency(app.existingEmi)}</div>
          </div>
        </Card>

        {/* CREDIT ASSESSMENT RESULTS (BACKEND CALCULATED) */}
        <Card title="Credit Assessment Results">
          {credit.score ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>CREDIT SCORE</div>
                  <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--primary)' }}>{credit.score}</div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>RISK RATING</div>
                  <span style={{
                    fontSize: '12px',
                    fontWeight: 700,
                    padding: '4px 8px',
                    borderRadius: '4px',
                    backgroundColor: credit.riskLevel === 'LOW' ? '#e6f4ea' : credit.riskLevel === 'HIGH' ? '#fce8e6' : '#fef3c7',
                    color: credit.riskLevel === 'LOW' ? '#1e7e34' : credit.riskLevel === 'HIGH' ? '#d9534f' : '#d97706'
                  }}>
                    {credit.riskLevel} RISK
                  </span>
                </div>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <strong>Recommendation:</strong>{' '}
                <span style={{ fontWeight: 700, color: 'var(--accent)' }}>{credit.recommendation}</span>
              </div>

              <div style={{ marginTop: '12px' }}>
                <strong style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Assessment Rationale & Reasons:</strong>
                <ul style={{ paddingLeft: '18px', marginTop: '6px', fontSize: '13px', color: 'var(--text-main)' }}>
                  {credit.reasons?.map((reason, i) => (
                    <li key={i} style={{ marginBottom: '4px' }}>{reason}</li>
                  ))}
                </ul>
              </div>

              {app.officerRemarks && (
                <div style={{ marginTop: '16px', backgroundColor: 'var(--bg-subtle)', padding: '12px', borderRadius: '4px', borderLeft: '3px solid var(--primary)' }}>
                  <strong style={{ fontSize: '12px', color: 'var(--primary)' }}>Loan Officer Remarks:</strong>
                  <p style={{ fontSize: '13px', margin: '4px 0 0 0' }}>{app.officerRemarks}</p>
                </div>
              )}
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
              Credit assessment pending officer evaluation.
            </div>
          )}
        </Card>
      </div>

      {/* DOCUMENT METADATA PANEL */}
      <Card title="Submitted Document Metadata">
        <table className="data-table">
          <thead>
            <tr>
              <th>Document Type</th>
              <th>File Reference</th>
              <th>Verification Status</th>
            </tr>
          </thead>
          <tbody>
            {app.documents?.map((doc) => (
              <tr key={doc.id}>
                <td><strong>{doc.type}</strong></td>
                <td style={{ fontFamily: 'monospace' }}>{doc.fileName}</td>
                <td>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-approved)' }}>
                    ✓ {doc.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

export default ApplicationDetails;
