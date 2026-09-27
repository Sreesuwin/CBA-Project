import React from 'react';
import { formatCurrency } from '../utils/emiCalculator';
import Button from './Button';
import iconPersonal from '../assets/icon-personal.svg';
import iconVehicle from '../assets/icon-vehicle.svg';
import iconHome from '../assets/icon-home.svg';
import iconGeneric from '../assets/icon-generic.svg';

// Icon per product family, matched on the backend's `icon` key (set in the
// product mapper) so a newly added product falls back to the generic mark.
const ICONS = {
  personal: iconPersonal,
  vehicle: iconVehicle,
  home: iconHome,
  generic: iconGeneric
};

const LoanCard = ({ product, onApply }) => {
  const icon = ICONS[product.icon] || iconGeneric;
  return (
    <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <img src={icon} alt="" width="48" height="48" style={{ borderRadius: '10px' }} />
          <div>
            <span style={{
              fontSize: '11px',
              fontWeight: 700,
              textTransform: 'uppercase',
              color: 'var(--accent)',
              backgroundColor: 'var(--primary-light)',
              padding: '2px 8px',
              borderRadius: '4px'
            }}>
              {product.category || 'Loan Product'}
            </span>
            <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--primary)', marginTop: '6px' }}>
              {product.name}
            </h3>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--primary)' }}>
            {product.interestRate}% <span style={{ fontSize: '11px', fontWeight: 500, color: 'var(--text-muted)' }}>p.a.</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Interest Rate</div>
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '12px',
        backgroundColor: 'var(--bg-subtle)',
        padding: '12px',
        borderRadius: '6px',
        margin: '12px 0'
      }}>
        <div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Loan Amount Limit</div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>
            {formatCurrency(product.minAmount)} – {formatCurrency(product.maxAmount)}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Tenure Range</div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>
            {product.minTenure} – {product.maxTenure} Months
          </div>
        </div>
        <div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Min. Monthly Income</div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>
            {formatCurrency(product.minIncome)} / month
          </div>
        </div>
        <div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Status</div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-approved)' }}>
            ✓ {product.status || 'ACTIVE'}
          </div>
        </div>
      </div>

      <p style={{ fontSize: '12px', color: 'var(--text-muted)', flex: 1, marginBottom: '16px' }}>
        <strong>Eligibility:</strong> {product.eligibility}
      </p>

      <Button
        variant="primary"
        onClick={() => onApply && onApply(product)}
        style={{ width: '100%' }}
      >
        Apply for {product.name}
      </Button>
    </div>
  );
};

export default LoanCard;
