import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import LoanCard from '../../components/LoanCard';

const LoanProducts = () => {
  const { products } = useAuth();
  const navigate = useNavigate();

  const handleApply = (product) => {
    navigate('/customer/apply', { state: { selectedProduct: product } });
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Available Loan Products</h1>
          <p className="page-subtitle">
            Explore retail banking loan options, interest rates, tenure ranges, and eligibility criteria.
          </p>
        </div>
      </div>

      <div className="grid-2">
        {products.map((product) => (
          <LoanCard
            key={product.id}
            product={product}
            onApply={handleApply}
          />
        ))}
      </div>
    </div>
  );
};

export default LoanProducts;
