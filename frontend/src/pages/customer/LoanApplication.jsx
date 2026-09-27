import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  validateEmail,
  validatePhone,
  validateRequired,
  validateLoanDetails
} from '../../utils/validation';
import { formatCurrency } from '../../utils/emiCalculator';
import Stepper from '../../components/Stepper';
import Card from '../../components/Card';
import Button from '../../components/Button';
import Modal from '../../components/Modal';

const STEPS = [
  { title: 'Personal Info' },
  { title: 'Employment' },
  { title: 'Financial' },
  { title: 'Loan Details' },
  { title: 'Documents' },
  { title: 'Review & Submit' }
];

const LoanApplication = () => {
  const { currentUser, products, createApplication } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [currentStep, setCurrentStep] = useState(1);

  // Pre-select product if passed from LoanProducts page
  const initialProduct = location.state?.selectedProduct || products[0] || null;

  const [formData, setFormData] = useState({
    fullName: currentUser.name || '',
    dob: '1992-05-14',
    phone: '9876543210',
    address: '123 MG Road, Sector 4, Bengaluru, Karnataka 560001',
    employmentType: 'Salaried',
    employerName: 'TechCorp International',
    employmentYears: '4',
    monthlyIncome: '65000',
    monthlyExpenses: '22000',
    existingEmi: '8000',
    existingLoans: '1',
    productId: initialProduct ? initialProduct.id : '',
    amount: initialProduct ? initialProduct.minAmount.toString() : '200000',
    tenure: initialProduct ? initialProduct.minTenure.toString() : '24',
    purpose: 'Home Improvement & Personal Expenses',
    documents: [
      { id: 'doc-1', type: 'Salary Slip', fileName: 'salary_slip_recent.pdf', status: 'PENDING' },
      { id: 'doc-2', type: 'Identity Proof', fileName: 'pan_aadhaar_scan.pdf', status: 'PENDING' }
    ]
  });

  const [errors, setErrors] = useState({});
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newDocType, setNewDocType] = useState('Bank Statement');
  const [newDocName, setNewDocName] = useState('');

  const selectedProduct = products.find((p) => p.id === formData.productId) || products[0];

  useEffect(() => {
    if (selectedProduct && !formData.productId) {
      setFormData((prev) => ({
        ...prev,
        productId: selectedProduct.id,
        amount: selectedProduct.minAmount.toString(),
        tenure: selectedProduct.minTenure.toString()
      }));
    }
  }, [selectedProduct]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const handleProductSelect = (e) => {
    const prodId = e.target.value;
    const prod = products.find((p) => p.id === prodId);
    setFormData((prev) => ({
      ...prev,
      productId: prodId,
      amount: prod ? prod.minAmount.toString() : prev.amount,
      tenure: prod ? prod.minTenure.toString() : prev.tenure
    }));
  };

  const validateStep = (step) => {
    const newErrors = {};

    if (step === 1) {
      const nameErr = validateRequired(formData.fullName, 'Full Name');
      const phoneErr = validatePhone(formData.phone);
      const dobErr = validateRequired(formData.dob, 'Date of Birth');
      const addrErr = validateRequired(formData.address, 'Address');

      if (nameErr) newErrors.fullName = nameErr;
      if (phoneErr) newErrors.phone = phoneErr;
      if (dobErr) newErrors.dob = dobErr;
      if (addrErr) newErrors.address = addrErr;
    }

    if (step === 2) {
      const empTypeErr = validateRequired(formData.employmentType, 'Employment Type');
      const employerErr = validateRequired(formData.employerName, 'Employer Name');
      const yearsErr = validateRequired(formData.employmentYears, 'Employment Years');

      if (empTypeErr) newErrors.employmentType = empTypeErr;
      if (employerErr) newErrors.employerName = employerErr;
      if (yearsErr) newErrors.employmentYears = yearsErr;
      if (formData.employmentYears && Number(formData.employmentYears) < 0) {
        newErrors.employmentYears = 'Years must be 0 or greater.';
      }
    }

    if (step === 3) {
      const income = Number(formData.monthlyIncome);
      const expenses = Number(formData.monthlyExpenses);
      const emi = Number(formData.existingEmi);
      const loans = Number(formData.existingLoans);

      if (!formData.monthlyIncome || isNaN(income) || income <= 0) {
        newErrors.monthlyIncome = 'Monthly income must be greater than 0.';
      }
      if (isNaN(expenses) || expenses < 0) {
        newErrors.monthlyExpenses = 'Expenses cannot be negative.';
      }
      if (isNaN(emi) || emi < 0) {
        newErrors.existingEmi = 'Existing EMI cannot be negative.';
      }
      if (isNaN(loans) || loans < 0) {
        newErrors.existingLoans = 'Existing loans cannot be negative.';
      }
    }

    if (step === 4) {
      const detailErrors = validateLoanDetails(formData.amount, formData.tenure, selectedProduct);
      Object.assign(newErrors, detailErrors);
      const purposeErr = validateRequired(formData.purpose, 'Loan Purpose');
      if (purposeErr) newErrors.purpose = purposeErr;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep((prev) => Math.min(prev + 1, STEPS.length));
    }
  };

  const handlePrevious = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  const handleAddDocument = (e) => {
    e.preventDefault();
    if (!newDocName.trim()) return;
    const newDoc = {
      id: `doc-${Date.now()}`,
      type: newDocType,
      fileName: newDocName.trim(),
      status: 'PENDING'
    };
    setFormData((prev) => ({
      ...prev,
      documents: [...prev.documents, newDoc]
    }));
    setNewDocName('');
  };

  const handleRemoveDocument = (docId) => {
    setFormData((prev) => ({
      ...prev,
      documents: prev.documents.filter((d) => d.id !== docId)
    }));
  };

  const handleSaveDraft = async () => {
    setIsSubmitting(true);
    try {
      const draftApp = await createApplication(formData, false);
      navigate(`/customer/application/${draftApp.id}`);
    } catch (err) {
      alert(err.message || 'Could not save the draft. Please check the form and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmSubmit = async () => {
    setIsSubmitting(true);
    try {
      const submittedApp = await createApplication(formData, true);
      setIsSubmitModalOpen(false);
      navigate(`/customer/application/${submittedApp.id}`);
    } catch (err) {
      alert(err.message || 'Could not submit the application. Please review the details.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '850px', margin: '0 auto' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Digital Loan Application</h1>
          <p className="page-subtitle">Complete the 6-step form to apply for financing</p>
        </div>
      </div>

      <Stepper currentStep={currentStep} steps={STEPS} onStepClick={(s) => setCurrentStep(s)} />

      <Card>
        {/* STEP 1: PERSONAL INFORMATION */}
        {currentStep === 1 && (
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--primary)', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
              Step 1: Personal Information
            </h3>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Full Name <span className="required">*</span></label>
                <input
                  type="text"
                  name="fullName"
                  className={`form-control ${errors.fullName ? 'is-invalid' : ''}`}
                  value={formData.fullName}
                  onChange={handleChange}
                />
                {errors.fullName && <div className="form-error">{errors.fullName}</div>}
              </div>

              <div className="form-group">
                <label className="form-label">Date of Birth <span className="required">*</span></label>
                <input
                  type="date"
                  name="dob"
                  className={`form-control ${errors.dob ? 'is-invalid' : ''}`}
                  value={formData.dob}
                  onChange={handleChange}
                />
                {errors.dob && <div className="form-error">{errors.dob}</div>}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Mobile Phone Number <span className="required">*</span></label>
              <input
                type="tel"
                name="phone"
                className={`form-control ${errors.phone ? 'is-invalid' : ''}`}
                placeholder="10-digit mobile number"
                value={formData.phone}
                onChange={handleChange}
              />
              {errors.phone && <div className="form-error">{errors.phone}</div>}
            </div>

            <div className="form-group">
              <label className="form-label">Residential Address <span className="required">*</span></label>
              <textarea
                name="address"
                rows="3"
                className={`form-control ${errors.address ? 'is-invalid' : ''}`}
                value={formData.address}
                onChange={handleChange}
              />
              {errors.address && <div className="form-error">{errors.address}</div>}
            </div>
          </div>
        )}

        {/* STEP 2: EMPLOYMENT INFORMATION */}
        {currentStep === 2 && (
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--primary)', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
              Step 2: Employment Information
            </h3>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Employment Type <span className="required">*</span></label>
                <select
                  name="employmentType"
                  className={`form-control ${errors.employmentType ? 'is-invalid' : ''}`}
                  value={formData.employmentType}
                  onChange={handleChange}
                >
                  <option value="Salaried">Salaried Employee</option>
                  <option value="Self-Employed">Self-Employed Professional</option>
                  <option value="Business Owner">Business Owner</option>
                  <option value="Student">Student / Retired</option>
                </select>
                {errors.employmentType && <div className="form-error">{errors.employmentType}</div>}
              </div>

              <div className="form-group">
                <label className="form-label">Employer / Business Name <span className="required">*</span></label>
                <input
                  type="text"
                  name="employerName"
                  className={`form-control ${errors.employerName ? 'is-invalid' : ''}`}
                  value={formData.employerName}
                  onChange={handleChange}
                />
                {errors.employerName && <div className="form-error">{errors.employerName}</div>}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Employment Tenure (Years) <span className="required">*</span></label>
              <input
                type="number"
                name="employmentYears"
                min="0"
                className={`form-control ${errors.employmentYears ? 'is-invalid' : ''}`}
                value={formData.employmentYears}
                onChange={handleChange}
              />
              {errors.employmentYears && <div className="form-error">{errors.employmentYears}</div>}
            </div>
          </div>
        )}

        {/* STEP 3: FINANCIAL INFORMATION */}
        {currentStep === 3 && (
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--primary)', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
              Step 3: Financial Information
            </h3>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Monthly Income (₹) <span className="required">*</span></label>
                <input
                  type="number"
                  name="monthlyIncome"
                  className={`form-control ${errors.monthlyIncome ? 'is-invalid' : ''}`}
                  value={formData.monthlyIncome}
                  onChange={handleChange}
                />
                {errors.monthlyIncome && <div className="form-error">{errors.monthlyIncome}</div>}
              </div>

              <div className="form-group">
                <label className="form-label">Monthly Expenses (₹)</label>
                <input
                  type="number"
                  name="monthlyExpenses"
                  className={`form-control ${errors.monthlyExpenses ? 'is-invalid' : ''}`}
                  value={formData.monthlyExpenses}
                  onChange={handleChange}
                />
                {errors.monthlyExpenses && <div className="form-error">{errors.monthlyExpenses}</div>}
              </div>

              <div className="form-group">
                <label className="form-label">Existing Monthly EMI (₹)</label>
                <input
                  type="number"
                  name="existingEmi"
                  className={`form-control ${errors.existingEmi ? 'is-invalid' : ''}`}
                  value={formData.existingEmi}
                  onChange={handleChange}
                />
                {errors.existingEmi && <div className="form-error">{errors.existingEmi}</div>}
              </div>

              <div className="form-group">
                <label className="form-label">Number of Existing Active Loans</label>
                <input
                  type="number"
                  name="existingLoans"
                  min="0"
                  className={`form-control ${errors.existingLoans ? 'is-invalid' : ''}`}
                  value={formData.existingLoans}
                  onChange={handleChange}
                />
                {errors.existingLoans && <div className="form-error">{errors.existingLoans}</div>}
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: LOAN DETAILS */}
        {currentStep === 4 && (
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--primary)', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
              Step 4: Loan Details & Validation
            </h3>

            <div className="form-group">
              <label className="form-label">Select Loan Product <span className="required">*</span></label>
              <select
                name="productId"
                className={`form-control ${errors.product ? 'is-invalid' : ''}`}
                value={formData.productId}
                onChange={handleProductSelect}
              >
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.interestRate}% APR)
                  </option>
                ))}
              </select>
              {selectedProduct && (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Limits: {formatCurrency(selectedProduct.minAmount)} – {formatCurrency(selectedProduct.maxAmount)} | Tenure: {selectedProduct.minTenure}–{selectedProduct.maxTenure} mos
                </div>
              )}
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Requested Loan Amount (₹) <span className="required">*</span></label>
                <input
                  type="number"
                  name="amount"
                  className={`form-control ${errors.amount ? 'is-invalid' : ''}`}
                  value={formData.amount}
                  onChange={handleChange}
                />
                {errors.amount && <div className="form-error">{errors.amount}</div>}
              </div>

              <div className="form-group">
                <label className="form-label">Tenure (Months) <span className="required">*</span></label>
                <input
                  type="number"
                  name="tenure"
                  className={`form-control ${errors.tenure ? 'is-invalid' : ''}`}
                  value={formData.tenure}
                  onChange={handleChange}
                />
                {errors.tenure && <div className="form-error">{errors.tenure}</div>}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Purpose of Loan <span className="required">*</span></label>
              <textarea
                name="purpose"
                rows="2"
                className={`form-control ${errors.purpose ? 'is-invalid' : ''}`}
                value={formData.purpose}
                onChange={handleChange}
              />
              {errors.purpose && <div className="form-error">{errors.purpose}</div>}
            </div>
          </div>
        )}

        {/* STEP 5: DOCUMENTS METADATA */}
        {currentStep === 5 && (
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--primary)', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
              Step 5: Document Metadata & Upload References
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Specify document metadata for officer verification (Metadata only).
            </p>

            <form onSubmit={handleAddDocument} style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
              <select
                className="form-control"
                style={{ flex: 1 }}
                value={newDocType}
                onChange={(e) => setNewDocType(e.target.value)}
              >
                <option value="Salary Slip">Salary Slip</option>
                <option value="Identity Document">Identity Document (PAN/Aadhaar)</option>
                <option value="Bank Statement">Bank Statement (6 Months)</option>
                <option value="ITR Returns">ITR Tax Returns</option>
                <option value="Address Proof">Address Proof</option>
              </select>
              <input
                type="text"
                className="form-control"
                style={{ flex: 2 }}
                placeholder="Filename (e.g. statement_2025.pdf)"
                value={newDocName}
                onChange={(e) => setNewDocName(e.target.value)}
              />
              <Button type="submit" variant="secondary">Add Metadata</Button>
            </form>

            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Document Type</th>
                    <th>File Name</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {formData.documents.map((doc) => (
                    <tr key={doc.id}>
                      <td><strong>{doc.type}</strong></td>
                      <td style={{ fontFamily: 'monospace' }}>{doc.fileName}</td>
                      <td>
                        <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-pending)' }}>
                          ⏳ {doc.status}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          type="button"
                          onClick={() => handleRemoveDocument(doc.id)}
                          style={{ color: 'var(--color-rejected)', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700 }}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                  {formData.documents.length === 0 && (
                    <tr>
                      <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                        No document metadata added yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* STEP 6: REVIEW & SUBMIT */}
        {currentStep === 6 && (
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--primary)', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
              Step 6: Review & Finalize Application
            </h3>

            <div style={{ backgroundColor: 'var(--bg-subtle)', padding: '16px', borderRadius: '6px', marginBottom: '20px' }}>
              <div className="grid-2" style={{ gap: '16px' }}>
                <div>
                  <h4 style={{ color: 'var(--primary)', fontSize: '13px', textTransform: 'uppercase', marginBottom: '8px' }}>Personal Info</h4>
                  <div><strong>Name:</strong> {formData.fullName}</div>
                  <div><strong>DOB:</strong> {formData.dob}</div>
                  <div><strong>Phone:</strong> {formData.phone}</div>
                </div>

                <div>
                  <h4 style={{ color: 'var(--primary)', fontSize: '13px', textTransform: 'uppercase', marginBottom: '8px' }}>Employment</h4>
                  <div><strong>Type:</strong> {formData.employmentType}</div>
                  <div><strong>Employer:</strong> {formData.employerName}</div>
                  <div><strong>Tenure:</strong> {formData.employmentYears} Years</div>
                </div>

                <div>
                  <h4 style={{ color: 'var(--primary)', fontSize: '13px', textTransform: 'uppercase', marginBottom: '8px' }}>Financials</h4>
                  <div><strong>Monthly Income:</strong> {formatCurrency(formData.monthlyIncome)}</div>
                  <div><strong>Existing EMI:</strong> {formatCurrency(formData.existingEmi)}</div>
                </div>

                <div>
                  <h4 style={{ color: 'var(--primary)', fontSize: '13px', textTransform: 'uppercase', marginBottom: '8px' }}>Loan Terms</h4>
                  <div><strong>Product:</strong> {selectedProduct?.name}</div>
                  <div><strong>Amount:</strong> {formatCurrency(formData.amount)}</div>
                  <div><strong>Tenure:</strong> {formData.tenure} Months</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Navigation Control Bar */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '24px',
          paddingTop: '16px',
          borderTop: '1px solid var(--border-color)'
        }}>
          <div>
            {currentStep > 1 && (
              <Button variant="secondary" onClick={handlePrevious}>
                ← Previous Step
              </Button>
            )}
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <Button variant="secondary" onClick={handleSaveDraft} isLoading={isSubmitting}>
              💾 Save Draft
            </Button>

            {currentStep < STEPS.length ? (
              <Button variant="primary" onClick={handleNext}>
                Next Step →
              </Button>
            ) : (
              <Button variant="success" onClick={() => setIsSubmitModalOpen(true)}>
                🚀 Submit Application
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* SUBMISSION CONFIRMATION MODAL */}
      <Modal
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        title="Confirm Application Submission"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsSubmitModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="success" onClick={handleConfirmSubmit} isLoading={isSubmitting}>
              Confirm Submission
            </Button>
          </>
        }
      >
        <p style={{ fontSize: '14px', color: 'var(--text-main)', marginBottom: '12px' }}>
          Are you sure you want to submit this loan application for credit assessment?
        </p>
        <div style={{ backgroundColor: 'var(--bg-subtle)', padding: '12px', borderRadius: '4px', fontSize: '13px' }}>
          <div><strong>Product:</strong> {selectedProduct?.name}</div>
          <div><strong>Amount:</strong> {formatCurrency(formData.amount)}</div>
          <div><strong>Tenure:</strong> {formData.tenure} Months</div>
        </div>
      </Modal>
    </div>
  );
};

export default LoanApplication;
