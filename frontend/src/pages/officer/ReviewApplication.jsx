import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Card from '../../components/Card';
import StatusBadge from '../../components/StatusBadge';
import Button from '../../components/Button';
import Modal from '../../components/Modal';
import { formatCurrency } from '../../utils/emiCalculator';
import LoadingSpinner, { ErrorState } from '../../components/LoadingSpinner';

const ReviewApplication = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { applications, decideApplication } = useAuth();

  const [app, setApp] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Modal Decision States
  const [activeModal, setActiveModal] = useState(null); // 'APPROVE' | 'REJECT' | 'REQUEST_INFO'
  const [remarks, setRemarks] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    const found = applications.find((a) => a.id === id);
    setApp(found || null);
    setIsLoading(false);
  }, [id, applications]);

  if (isLoading) return <LoadingSpinner message="Loading underwriting application details..." />;

  if (!app) {
    return (
      <ErrorState
        title="Application Record Not Found"
        message={`No application found for ID ${id}`}
      />
    );
  }

  const handleDecision = async (decisionType) => {
    setIsProcessing(true);
    try {
      await decideApplication(app.id, decisionType, remarks);
      setActiveModal(null);
      setRemarks('');
    } catch (err) {
      alert(err.message || 'Could not record the decision.');
    } finally {
      setIsProcessing(false);
    }
  };

  const credit = app.creditAssessment || {};

  return (
    <div>
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h1 className="page-title">Underwriting Review: {app.id}</h1>
            <StatusBadge status={app.status} />
          </div>
          <p className="page-subtitle">Applicant: {app.applicantName} ({app.applicantEmail})</p>
        </div>
        <Button variant="secondary" onClick={() => navigate('/officer/dashboard')}>
          ← Back to Queue
        </Button>
      </div>

      {/* OFFICER DECISION ACTIONS BAR */}
      <div style={{
        backgroundColor: '#ffffff',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '16px 20px',
        marginBottom: '24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: 'var(--shadow-subtle)'
      }}>
        <div>
          <strong style={{ color: 'var(--primary)' }}>Underwriter Action Controls:</strong>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px' }}>
            Current Status: {app.status}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <Button variant="warning" onClick={() => setActiveModal('REQUEST_INFO')}>
            ℹ️ Request More Info
          </Button>
          <Button variant="danger" onClick={() => setActiveModal('REJECT')}>
            ✖ Reject Application
          </Button>
          <Button variant="success" onClick={() => setActiveModal('APPROVE')}>
            ✓ Approve Application
          </Button>
        </div>
      </div>

      <div className="grid-2">
        {/* APPLICANT & LOAN DETAILS */}
        <Card title="Applicant & Employment Profile">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div><strong>Full Name:</strong> {app.applicantName}</div>
            <div><strong>Email:</strong> {app.applicantEmail}</div>
            <div><strong>Phone:</strong> {app.applicantPhone}</div>
            <div><strong>Date of Birth:</strong> {app.dob}</div>
            <div><strong>Employment Type:</strong> {app.employmentType}</div>
            <div><strong>Employer:</strong> {app.employerName}</div>
            <div><strong>Employment Tenure:</strong> {app.employmentYears} Years</div>
            <div><strong>Address:</strong> {app.address}</div>
          </div>
        </Card>

        {/* FINANCIAL SUMMARY */}
        <Card title="Financial Declaration">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div><strong>Gross Monthly Income:</strong> {formatCurrency(app.monthlyIncome)}</div>
            <div><strong>Monthly Expenses:</strong> {formatCurrency(app.monthlyExpenses)}</div>
            <div><strong>Existing EMI Obligations:</strong> {formatCurrency(app.existingEmi)}</div>
            <div><strong>Active Loans Count:</strong> {app.existingLoans} Accounts</div>
            <div style={{ paddingTop: '8px', borderTop: '1px solid var(--border-color)', marginTop: '6px' }}>
              <strong>Estimated Debt-to-Income (DTI):</strong>{' '}
              <span style={{ fontWeight: 700, color: 'var(--primary)' }}>
                {((app.existingEmi / app.monthlyIncome) * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid-2">
        {/* LOAN REQUEST TERMS */}
        <Card title="Requested Loan Parameters">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div><strong>Product Category:</strong> {app.productName}</div>
            <div><strong>Requested Amount:</strong> {formatCurrency(app.amount)}</div>
            <div><strong>Requested Tenure:</strong> {app.tenure} Months</div>
            <div><strong>Stated Purpose:</strong> {app.purpose}</div>
          </div>
        </Card>

        {/* CREDIT ASSESSMENT (BACKEND DISPLAY) */}
        <Card title="Backend Credit Assessment Engine Output">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>CREDIT SCORE</div>
              <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--primary)' }}>{credit.score || 'N/A'}</div>
            </div>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>RISK LEVEL</div>
              <span style={{
                fontSize: '12px',
                fontWeight: 700,
                padding: '4px 8px',
                borderRadius: '4px',
                backgroundColor: credit.riskLevel === 'LOW' ? '#e6f4ea' : '#fce8e6',
                color: credit.riskLevel === 'LOW' ? '#1e7e34' : '#d9534f'
              }}>
                {credit.riskLevel || 'UNASSESSED'}
              </span>
            </div>
          </div>

          <div><strong>Engine Recommendation:</strong> {credit.recommendation || 'PENDING'}</div>

          <div style={{ marginTop: '12px' }}>
            <strong style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Rule Assessment Reasons:</strong>
            <ul style={{ paddingLeft: '18px', marginTop: '4px', fontSize: '13px' }}>
              {credit.reasons?.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        </Card>
      </div>

      {/* DOCUMENT METADATA */}
      <Card title="Submitted Document Metadata Checklist">
        <table className="data-table">
          <thead>
            <tr>
              <th>Document Type</th>
              <th>File Name</th>
              <th>Metadata Status</th>
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

      {/* APPROVE CONFIRMATION MODAL */}
      <Modal
        isOpen={activeModal === 'APPROVE'}
        onClose={() => setActiveModal(null)}
        title="Approve Loan Application"
        footer={
          <>
            <Button variant="secondary" onClick={() => setActiveModal(null)}>Cancel</Button>
            <Button variant="success" onClick={() => handleDecision('APPROVE')} isLoading={isProcessing}>
              Confirm Approval
            </Button>
          </>
        }
      >
        <p>Are you sure you want to approve application <strong>{app.id}</strong> for {formatCurrency(app.amount)}?</p>
        <div className="form-group" style={{ marginTop: '14px' }}>
          <label className="form-label">Approval Remarks (Optional)</label>
          <textarea
            className="form-control"
            rows="2"
            placeholder="e.g. Approved as per standard credit risk policy."
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
        </div>
      </Modal>

      {/* REJECT CONFIRMATION MODAL */}
      <Modal
        isOpen={activeModal === 'REJECT'}
        onClose={() => setActiveModal(null)}
        title="Reject Loan Application"
        footer={
          <>
            <Button variant="secondary" onClick={() => setActiveModal(null)}>Cancel</Button>
            <Button variant="danger" onClick={() => handleDecision('REJECT')} isLoading={isProcessing}>
              Confirm Rejection
            </Button>
          </>
        }
      >
        <p>Are you sure you want to reject application <strong>{app.id}</strong>?</p>
        <div className="form-group" style={{ marginTop: '14px' }}>
          <label className="form-label">Rejection Remarks / Reason</label>
          <textarea
            className="form-control"
            rows="2"
            placeholder="Specify reason for rejection..."
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
        </div>
      </Modal>

      {/* REQUEST MORE INFO MODAL */}
      <Modal
        isOpen={activeModal === 'REQUEST_INFO'}
        onClose={() => setActiveModal(null)}
        title="Request Additional Information"
        footer={
          <>
            <Button variant="secondary" onClick={() => setActiveModal(null)}>Cancel</Button>
            <Button variant="warning" onClick={() => handleDecision('REQUEST_INFO')} isLoading={isProcessing}>
              Send Request
            </Button>
          </>
        }
      >
        <p>Specify what additional documents or information are required from applicant <strong>{app.applicantName}</strong>:</p>
        <div className="form-group" style={{ marginTop: '14px' }}>
          <label className="form-label">Required Information / Document Details <span className="required">*</span></label>
          <textarea
            className="form-control"
            rows="3"
            placeholder="e.g. Please upload latest 6-month bank statement with employer salary credits."
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
        </div>
      </Modal>
    </div>
  );
};

export default ReviewApplication;
