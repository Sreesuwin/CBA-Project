import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Card from '../../components/Card';
import Button from '../../components/Button';
import ApplicationTable from '../../components/ApplicationTable';

const CustomerDashboard = () => {
  const { currentUser, applications } = useAuth();
  const navigate = useNavigate();

  // Filter applications for current logged in user (or sample customer data)
  const userApplications = applications.filter(
    (app) => app.applicantEmail === currentUser.email || currentUser.role === 'CUSTOMER'
  );

  const totalApps = userApplications.length;
  const draftApps = userApplications.filter((app) => app.status === 'DRAFT').length;
  const pendingApps = userApplications.filter((app) =>
    ['SUBMITTED', 'UNDER_REVIEW', 'MORE_INFORMATION_REQUIRED'].includes(app.status)
  ).length;
  const approvedApps = userApplications.filter((app) => app.status === 'APPROVED').length;
  const rejectedApps = userApplications.filter((app) => app.status === 'REJECTED').length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Customer Dashboard</h1>
          <p className="page-subtitle">Welcome back, {currentUser.name}. Overview of your credit applications and loan status.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <Link to="/customer/products">
            <Button variant="secondary">View Loan Products</Button>
          </Link>
          <Link to="/customer/apply">
            <Button variant="primary">➕ Apply for New Loan</Button>
          </Link>
        </div>
      </div>

      {/* Metrics Summary Row */}
      <div className="grid-4" style={{ marginBottom: '24px' }}>
        <Card metricValue={totalApps} metricLabel="TOTAL APPLICATIONS" metricTrend="All Time Submissions" />
        <Card metricValue={draftApps} metricLabel="DRAFT APPLICATIONS" metricTrend="In Progress" />
        <Card metricValue={pendingApps} metricLabel="UNDER REVIEW" metricTrend="Pending Officer Action" />
        <Card
          metricValue={approvedApps}
          metricLabel="APPROVED LOANS"
          metricTrend={`+${approvedApps} Successful`}
        />
      </div>

      {/* Recent Applications Table Panel */}
      <Card
        title="Your Recent Applications"
        subtitle="Track application status, credit assessments, and officer remarks"
        action={
          <Link to="/customer/apply">
            <Button variant="secondary" style={{ fontSize: '12px', padding: '4px 10px' }}>
              New Application
            </Button>
          </Link>
        }
      >
        <ApplicationTable
          applications={userApplications}
          onViewDetails={(id) => navigate(`/customer/application/${id}`)}
          showApplicantName={false}
          showRiskLevel={false}
          emptyMessage="You have not created any loan applications yet. Click 'Apply for New Loan' to begin."
        />
      </Card>
    </div>
  );
};

export default CustomerDashboard;
