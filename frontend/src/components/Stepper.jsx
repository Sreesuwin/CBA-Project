import React from 'react';

const Stepper = ({ currentStep, steps, onStepClick }) => {
  return (
    <div style={{
      backgroundColor: '#ffffff',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      padding: '16px 24px',
      marginBottom: '24px',
      boxShadow: 'var(--shadow-subtle)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'relative'
      }}>
        {steps.map((step, idx) => {
          const stepNum = idx + 1;
          const isCompleted = stepNum < currentStep;
          const isCurrent = stepNum === currentStep;

          return (
            <React.Fragment key={stepNum}>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  cursor: isCompleted ? 'pointer' : 'default',
                  zIndex: 2,
                  flex: 1
                }}
                onClick={() => isCompleted && onStepClick && onStepClick(stepNum)}
              >
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    backgroundColor: isCompleted
                      ? 'var(--color-approved)'
                      : isCurrent
                      ? 'var(--primary)'
                      : 'var(--bg-subtle)',
                    color: isCompleted || isCurrent ? '#ffffff' : 'var(--text-muted)',
                    border: `2px solid ${
                      isCompleted
                        ? 'var(--color-approved)'
                        : isCurrent
                        ? 'var(--primary)'
                        : 'var(--border-color)'
                    }`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 700,
                    fontSize: '13px',
                    marginBottom: '6px',
                    transition: 'all 0.2s ease'
                  }}
                  aria-current={isCurrent ? 'step' : undefined}
                >
                  {isCompleted ? '✓' : stepNum}
                </div>
                <div style={{
                  fontSize: '11px',
                  fontWeight: isCurrent ? 700 : 500,
                  color: isCurrent ? 'var(--primary)' : 'var(--text-muted)',
                  textAlign: 'center',
                  whiteSpace: 'nowrap'
                }}>
                  {step.title}
                </div>
              </div>

              {idx < steps.length - 1 && (
                <div
                  style={{
                    flex: 1,
                    height: '2px',
                    backgroundColor: stepNum < currentStep ? 'var(--color-approved)' : 'var(--border-color)',
                    margin: '0 -10px 20px -10px',
                    zIndex: 1,
                    transition: 'background-color 0.2s ease'
                  }}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

export default Stepper;
