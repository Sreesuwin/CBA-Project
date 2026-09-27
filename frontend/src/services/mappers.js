/**
 * Field mapping between the Flask API (snake_case, decimal strings) and the
 * React UI (camelCase, numbers).
 *
 * Keeping the translation here means neither side has to compromise: the API
 * stays idiomatic Python, and the components keep the prop shapes they were
 * already written against.
 */

const num = (value, fallback = 0) => {
  if (value === null || value === undefined || value === '') return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

// Presentation metadata the backend does not model (it has no "category" or
// marketing copy). Keyed by product name so it stays in step with the catalogue.
const PRODUCT_META = {
  'Personal Loan': {
    category: 'Unsecured',
    icon: 'personal',
    eligibility: 'Salaried or self-employed individuals with at least 1 year of income history.'
  },
  'Vehicle Loan': {
    category: 'Secured',
    icon: 'vehicle',
    eligibility: 'Applicants with a valid driving licence and a stable income source.'
  },
  'Home Loan': {
    category: 'Secured',
    icon: 'home',
    eligibility: 'Salaried or self-employed applicants, property documents and co-applicant on request.'
  },
  'Education Loan': {
    category: 'Unsecured',
    icon: 'generic',
    eligibility: 'Students admitted to a recognised higher-education institution.'
  }
};

const DEFAULT_META = {
  category: 'Loan Product',
  icon: 'generic',
  eligibility: 'Contact the branch to confirm eligibility for this product.'
};

// Backend EmploymentType vocabulary <-> UI labels.
const EMPLOYMENT_LABELS = {
  SALARIED: 'Salaried',
  SELF_EMPLOYED: 'Self-Employed',
  BUSINESS_OWNER: 'Business Owner',
  STUDENT: 'Student',
  UNEMPLOYED: 'Unemployed',
  RETIRED: 'Retired'
};

const EMPLOYMENT_TYPES = {
  Salaried: 'SALARIED',
  'Self-Employed': 'SELF_EMPLOYED',
  'Business Owner': 'BUSINESS_OWNER',
  Student: 'STUDENT',
  Unemployed: 'UNEMPLOYED',
  Retired: 'RETIRED'
};

export function toEmploymentType(label) {
  return EMPLOYMENT_TYPES[label] || undefined;
}

export function mapProduct(product) {
  const meta = PRODUCT_META[product.name] || DEFAULT_META;
  return {
    id: String(product.id),
    name: product.name,
    category: meta.category,
    icon: meta.icon,
    minAmount: num(product.min_amount),
    maxAmount: num(product.max_amount),
    interestRate: num(product.interest_rate),
    minTenure: num(product.min_tenure),
    maxTenure: num(product.max_tenure),
    minIncome: num(product.min_income),
    eligibility: meta.eligibility,
    status: product.active ? 'ACTIVE' : 'INACTIVE'
  };
}

// Human label <-> backend DocumentType vocabulary.
const DOC_LABEL_TO_TYPE = {
  'Salary Slip': 'SALARY_SLIP',
  'Identity Document': 'ID_PROOF',
  'Identity Proof': 'ID_PROOF',
  'Bank Statement': 'BANK_STATEMENT',
  'ITR Returns': 'ITR',
  'Address Proof': 'ADDRESS_PROOF'
};

const DOC_TYPE_TO_LABEL = {
  SALARY_SLIP: 'Salary Slip',
  ID_PROOF: 'Identity Document',
  BANK_STATEMENT: 'Bank Statement',
  ITR: 'ITR Returns',
  ADDRESS_PROOF: 'Address Proof',
  OTHER: 'Other'
};

export function toDocumentType(labelOrType) {
  if (!labelOrType) return 'OTHER';
  if (DOC_TYPE_TO_LABEL[labelOrType]) return labelOrType; // already an enum value
  return DOC_LABEL_TO_TYPE[labelOrType] || 'OTHER';
}

export function mapDocument(doc, index = 0) {
  return {
    id: doc._id !== undefined && doc._id !== null ? String(doc._id) : `doc-${index}`,
    type: DOC_TYPE_TO_LABEL[doc.type] || doc.type,
    enumType: doc.type,
    fileName: doc.filename || doc.file_name || '',
    status: doc.status || 'PENDING',
    uploadedAt: doc.uploaded_at || null
  };
}

export function mapApplication(application) {
  const financials = application.financial_details || {};
  const applicant = application.applicant || {};
  const assessment = application.assessment || null;

  return {
    id: String(application.id),
    applicationNo: application.application_no,
    applicantName: applicant.name || '',
    applicantEmail: applicant.email || '',
    applicantPhone: applicant.phone || '',
    // The application form collects these, but they live on the borrower's
    // customer profile; the API joins them onto the applicant object.
    dob: applicant.dob || '',
    address: applicant.address || '',
    employmentType: EMPLOYMENT_LABELS[applicant.employment_type] || applicant.employment_type || '',
    employerName: application.employer_name || '',
    employmentYears: num(financials.employment_years),
    monthlyIncome: num(financials.monthly_income),
    monthlyExpenses: num(financials.monthly_expenses),
    existingEmi: num(financials.existing_emi),
    existingLoans: num(financials.existing_loans),
    productName: application.product ? application.product.name : '',
    productId: application.product_id != null ? String(application.product_id) : '',
    product: application.product ? mapProduct(application.product) : null,
    amount: num(application.amount),
    tenure: num(application.tenure),
    purpose: application.purpose || '',
    status: application.status,
    createdDate: application.created_at,
    updatedDate: application.updated_at || application.created_at,
    submittedDate: application.submitted_at,
    documents: (application.documents || []).map(mapDocument),
    creditAssessment: assessment
      ? {
          score: assessment.score,
          riskLevel: assessment.risk_level,
          recommendation: assessment.recommendation,
          assessmentDate: assessment.assessed_at,
          reasons: assessment.reasons || []
        }
      : null,
    decision: application.decision || null,
    officerRemarks: application.officer_remarks || ''
  };
}

export function mapUser(user) {
  return {
    id: String(user.id),
    name: user.name,
    email: user.email,
    role: user.role,
    status: user.is_active === false ? 'INACTIVE' : 'ACTIVE'
  };
}

export function mapAuditLog(entry, index = 0) {
  return {
    id: entry.id != null ? String(entry.id) : `log-${index}`,
    applicationId: entry.application_id != null ? String(entry.application_id) : '',
    actorId: entry.actor_id,
    actor: entry.actor_id != null ? `User #${entry.actor_id}` : 'System',
    action: entry.action,
    metadata: entry.metadata || {},
    timestamp: entry.timestamp
  };
}

/** Convert the UI form state into the API's create payload. */
export function toApplicationPayload(formData) {
  return {
    product_id: Number(formData.productId),
    amount: Number(formData.amount),
    tenure: Number(formData.tenure),
    purpose: formData.purpose || null,
    financials: {
      monthly_income: Number(formData.monthlyIncome),
      monthly_expenses: Number(formData.monthlyExpenses || 0),
      existing_emi: Number(formData.existingEmi || 0),
      existing_loans: Number(formData.existingLoans || 0),
      employment_years: Number(formData.employmentYears || 0)
    }
  };
}

/** Convert the admin modal's product state into the API payload. */
export function toProductPayload(product) {
  return {
    name: product.name,
    min_amount: Number(product.minAmount),
    max_amount: Number(product.maxAmount),
    interest_rate: Number(product.interestRate),
    min_tenure: Number(product.minTenure),
    max_tenure: Number(product.maxTenure),
    min_income: Number(product.minIncome)
  };
}
