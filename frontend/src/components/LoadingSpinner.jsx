import React from 'react';
import Button from './Button';

const LoadingSpinner = ({ message = 'Loading details...' }) => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '48px 24px',
      gap: '16px'
    }}>
      <div style={{
        width: '36px',
        height: '36px',
        border: '3px solid var(--border-color)',
        borderTopColor: 'var(--primary)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite'
      }} />
      <p style={{ color: 'var(--text-muted)', fontSize: '14px', fontWeight: 500 }}>{message}</p>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export const ErrorState = ({
  title = 'Unable to Load Data',
  message = 'An error occurred while fetching information from the server. Please check your connection and try again.',
  onRetry
}) => {
  return (
    <div style={{
      backgroundColor: 'var(--bg-rejected)',
      border: '1px solid #f8b4b4',
      borderRadius: '8px',
      padding: '24px',
      textAlign: 'center',
      margin: '20px 0'
    }}>
      <div style={{ fontSize: '24px', marginBottom: '8px' }}>⚠️</div>
      <h4 style={{ color: 'var(--color-rejected)', margin: '0 0 8px 0', fontSize: '16px' }}>{title}</h4>
      <p style={{ color: '#7f1d1d', fontSize: '13px', maxWidth: '500px', margin: '0 auto 16px auto' }}>{message}</p>
      {onRetry && (
        <Button variant="danger" onClick={onRetry}>
          Retry Action
        </Button>
      )}
    </div>
  );
};

export const EmptyState = ({
  title = 'No Records Found',
  message = 'There are no applications or records matching your current filter criteria.',
  action
}) => {
  return (
    <div style={{
      backgroundColor: 'var(--bg-subtle)',
      border: '1px dashed var(--border-color)',
      borderRadius: '8px',
      padding: '40px 24px',
      textAlign: 'center',
      margin: '20px 0'
    }}>
      <div style={{ fontSize: '32px', marginBottom: '12px' }}>📂</div>
      <h4 style={{ color: 'var(--primary)', margin: '0 0 8px 0', fontSize: '16px' }}>{title}</h4>
      <p style={{ color: 'var(--text-muted)', fontSize: '13px', maxWidth: '450px', margin: '0 auto 16px auto' }}>{message}</p>
      {action && <div>{action}</div>}
    </div>
  );
};

export default LoadingSpinner;
