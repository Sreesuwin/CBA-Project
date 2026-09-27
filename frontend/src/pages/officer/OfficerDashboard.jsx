import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Card from '../../components/Card';
import ApplicationTable from '../../components/ApplicationTable';

const OfficerDashboard = () => {
  const { applications } = useAuth();
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [riskFilter, setRiskFilter] = useState('ALL');

  const pendingCount = applications.filter((app) => app.status === 'SUBMITTED').length;
  const underReviewCount = applications.filter((app) => app.status === 'UNDER_REVIEW').length;
  const approvedCount = applications.filter((app) => app.status === 'APPROVED').length;
  const rejectedCount = applications.filter((app) => app.status === 'REJECTED').length;

  const filteredApplications = applications.filter((app) => {
    const matchesSearch =
      app.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      app.applicantName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      app.productName.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = statusFilter === 'ALL' || app.status === statusFilter;
    const matchesRisk =
      riskFilter === 'ALL' || app.creditAssessment?.riskLevel === riskFilter;

    return matchesSearch && matchesStatus && matchesRisk;
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Loan Officer Review Portal</h1>
          <p className="page-subtitle">Underwriting & Credit Assessment Queue</p>
        </div>
      </div>

      {/* METRICS CARDS */}
      <div className="grid-4" style={{ marginBottom: '24px' }}>
        <Card metricValue={pendingCount} metricLabel="PENDING SUBMISSIONS" metricTrend="Awaiting Underwriting" />
        <Card metricValue={underReviewCount} metricLabel="UNDER REVIEW" metricTrend="In Progress" />
        <Card metricValue={approvedCount} metricLabel="APPROVED APPLICATIONS" metricTrend="Sanctioned" />
        <Card metricValue={rejectedCount} metricLabel="REJECTED APPLICATIONS" metricTrend="Declined" />
      </div>

      {/* SEARCH AND FILTER BAR */}
      <Card title="Application Assessment Queue">
        <div style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr 1fr',
          gap: '12px',
          marginBottom: '16px'
        }}>
          <div>
            <input
              type="text"
              className="form-control"
              placeholder="🔍 Search by Application ID, Applicant Name, Product..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div>
            <select
              className="form-control"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="UNDER_REVIEW">Under Review</option>
              <option value="MORE_INFORMATION_REQUIRED">More Info Required</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          <div>
            <select
              className="form-control"
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
            >
              <option value="ALL">All Risk Ratings</option>
              <option value="LOW">Low Risk</option>
              <option value="MODERATE">Moderate Risk</option>
              <option value="HIGH">High Risk</option>
            </select>
          </div>
        </div>

        <ApplicationTable
          applications={filteredApplications}
          onViewDetails={(id) => navigate(`/officer/application/${id}`)}
          showApplicantName={true}
          showRiskLevel={true}
          emptyMessage="No applications found matching your search or filter parameters."
        />
      </Card>
    </div>
  );
};

export default OfficerDashboard;
