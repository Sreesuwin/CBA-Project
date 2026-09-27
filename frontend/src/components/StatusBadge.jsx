import React from 'react';

const StatusBadge = ({ status }) => {
  const normalizedStatus = (status || 'DRAFT').toUpperCase();

  const statusMap = {
    APPROVED: {
      text: 'Approved',
      icon: '✓',
      className: 'badge-approved',
      ariaLabel: 'Status: Approved'
    },
    REJECTED: {
      text: 'Rejected',
      icon: '✖',
      className: 'badge-rejected',
      ariaLabel: 'Status: Rejected'
    },
    UNDER_REVIEW: {
      text: 'Under Review',
      icon: '⏳',
      className: 'badge-under_review',
      ariaLabel: 'Status: Under Review'
    },
    SUBMITTED: {
      text: 'Submitted',
      icon: '📤',
      className: 'badge-submitted',
      ariaLabel: 'Status: Submitted'
    },
    MORE_INFORMATION_REQUIRED: {
      text: 'More Info Required',
      icon: 'ℹ',
      className: 'badge-more_info',
      ariaLabel: 'Status: More Information Required'
    },
    DRAFT: {
      text: 'Draft',
      icon: '📝',
      className: 'badge-draft',
      ariaLabel: 'Status: Draft'
    }
  };

  const config = statusMap[normalizedStatus] || {
    text: normalizedStatus,
    icon: '•',
    className: 'badge-draft',
    ariaLabel: `Status: ${normalizedStatus}`
  };

  return (
    <span className={`badge ${config.className}`} role="status" aria-label={config.ariaLabel}>
      <span aria-hidden="true" style={{ fontSize: '12px' }}>{config.icon}</span>
      <span>{config.text}</span>
    </span>
  );
};

export default StatusBadge;
