import React from 'react';

const Card = ({
  title,
  subtitle,
  action,
  children,
  className = '',
  metricValue = null,
  metricLabel = null,
  metricTrend = null
}) => {
  return (
    <div className={`card-panel ${className}`}>
      {(title || action || metricValue) && (
        <div className="card-header-bar">
          <div>
            {title && <h3 className="card-title">{title}</h3>}
            {subtitle && <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{subtitle}</p>}
          </div>
          {action && <div className="card-action">{action}</div>}
        </div>
      )}

      {metricValue !== null && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '28px', fontWeight: '700', color: 'var(--primary)' }}>
            {metricValue}
          </div>
          {metricLabel && (
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '600' }}>
              {metricLabel}
            </div>
          )}
          {metricTrend && (
            <div style={{ fontSize: '11px', marginTop: '4px', color: metricTrend.startsWith('+') ? 'var(--color-approved)' : 'var(--text-muted)' }}>
              {metricTrend}
            </div>
          )}
        </div>
      )}

      {children}
    </div>
  );
};

export default Card;
