import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState
} from 'react';
import { apiService, TOKEN_KEY } from '../services/api';
import {
  mapApplication,
  mapAuditLog,
  mapProduct,
  mapUser,
  toApplicationPayload,
  toDocumentType,
  toEmploymentType,
  toProductPayload
} from '../services/mappers';

/**
 * Application state, backed by the Flask API.
 *
 * This replaces the earlier localStorage mock layer. The component-facing
 * surface is kept intentionally similar (same field names, same action names
 * where possible) so the pages did not all need rewriting - but every piece of
 * data now comes from the backend, and nothing is fabricated when the API is
 * unreachable.
 */

const AuthContext = createContext();

const USER_KEY = 'cba_user';

// Seeded demo accounts (see backend `flask seed-db`). Used by the "quick demo
// login" controls so a reviewer can switch roles without knowing passwords.
export const DEMO_ACCOUNTS = {
  CUSTOMER: { email: 'rahul.kumar@example.test', password: 'Password@123' },
  LOAN_OFFICER: { email: 'officer@loanplatform.test', password: 'Password@123' },
  ADMIN: { email: 'admin@loanplatform.test', password: 'Password@123' }
};

// The credit policy is fixed in the backend engine today, so the admin screen
// shows it read-only. Kept as state so the edit UI still has somewhere to write.
const SCORING_RULES = [
  { id: 'rule-1', name: 'Base score', metric: 'Every valid application', value: '+300', status: 'ACTIVE' },
  { id: 'rule-2', name: 'Income > 75,000', metric: 'Monthly income', value: '+100', status: 'ACTIVE' },
  { id: 'rule-3', name: 'EMI ratio < 20%', metric: 'Existing EMI / income', value: '+80', status: 'ACTIVE' },
  { id: 'rule-4', name: 'Employment > 5 years', metric: 'Years', value: '+60', status: 'ACTIVE' },
  { id: 'rule-5', name: 'No existing loans', metric: 'Active accounts', value: '+50', status: 'ACTIVE' },
  { id: 'rule-6', name: 'Low risk threshold', metric: 'Score band', value: '>= 700 (LOW)', status: 'ACTIVE' },
  { id: 'rule-7', name: 'Very high risk threshold', metric: 'Score band', value: '< 500 (VERY_HIGH)', status: 'ACTIVE' }
];

function persistUser(user) {
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(USER_KEY);
  }
}

function readStoredUser() {
  try {
    const saved = localStorage.getItem(USER_KEY);
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
}

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(readStoredUser);
  const [isLoggedIn, setIsLoggedIn] = useState(() => Boolean(localStorage.getItem(TOKEN_KEY)));
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [products, setProducts] = useState([]);
  const [applications, setApplications] = useState([]);
  const [usersList, setUsersList] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [scoringRules, setScoringRules] = useState(SCORING_RULES);

  // The role of the signed-in user, readable from callbacks without re-creating
  // them on every role change.
  const roleRef = useRef(currentUser ? currentUser.role : null);

  const setUser = useCallback((user) => {
    setCurrentUser(user);
    roleRef.current = user ? user.role : null;
    persistUser(user);
  }, []);

  const loadProducts = useCallback(async () => {
    const data = await apiService.getLoanProducts();
    const mapped = (data.products || []).map(mapProduct);
    setProducts(mapped);
    return mapped;
  }, []);

  const loadApplications = useCallback(async () => {
    const data = await apiService.getApplications();
    const mapped = (data.applications || []).map(mapApplication);
    setApplications(mapped);
    return mapped;
  }, []);

  const loadAdminData = useCallback(async () => {
    const [users, audit] = await Promise.all([
      apiService.listUsers().catch(() => null),
      apiService.listAllAudit().catch(() => null)
    ]);
    if (users) setUsersList((users.users || []).map(mapUser));
    if (audit) setAuditLogs((audit.audit || []).map(mapAuditLog));
  }, []);

  /** Reload everything the current role is allowed to see. */
  const refreshData = useCallback(
    async (role) => {
      const effectiveRole = role || roleRef.current;
      await loadProducts();
      if (effectiveRole === 'CUSTOMER' || effectiveRole === 'LOAN_OFFICER') {
        await loadApplications();
      } else if (effectiveRole === 'ADMIN') {
        await loadApplications();
        await loadAdminData();
      }
    },
    [loadProducts, loadApplications, loadAdminData]
  );

  // Restore the session on first load: a stored token is validated against
  // /users/me, and a rejected token is dropped rather than trusted.
  useEffect(() => {
    let active = true;

    (async () => {
      if (!localStorage.getItem(TOKEN_KEY)) {
        setIsLoading(false);
        return;
      }
      try {
        const { user } = await apiService.getCurrentUser();
        if (!active) return;
        const mapped = {
          id: String(user.id),
          name: user.name,
          email: user.email,
          role: user.role,
          profile: user.profile || null
        };
        setUser(mapped);
        setIsLoggedIn(true);
        await refreshData(mapped.role);
      } catch (err) {
        if (!active) return;
        localStorage.removeItem(TOKEN_KEY);
        setUser(null);
        setIsLoggedIn(false);
      } finally {
        if (active) setIsLoading(false);
      }
    })();

    return () => {
      active = false;
    };
    // Runs once on mount; refreshData/setUser are stable callbacks.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(
    async (email, password) => {
      setError(null);
      const data = await apiService.login({ email, password });
      localStorage.setItem(TOKEN_KEY, data.access_token);
      const user = {
        id: String(data.user.id),
        name: data.user.name,
        email: data.user.email,
        role: data.user.role
      };
      setUser(user);
      setIsLoggedIn(true);
      await refreshData(user.role);
      return user;
    },
    [refreshData, setUser]
  );

  const register = useCallback(
    async ({ name, email, password, phone }) => {
      setError(null);
      const payload = { name, email, password };
      if (phone) payload.phone = phone;
      const data = await apiService.register(payload);
      localStorage.setItem(TOKEN_KEY, data.access_token);
      const user = {
        id: String(data.user.id),
        name: data.user.name,
        email: data.user.email,
        role: data.user.role
      };
      setUser(user);
      setIsLoggedIn(true);
      await refreshData(user.role);
      return user;
    },
    [refreshData, setUser]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setIsLoggedIn(false);
    setApplications([]);
    setUsersList([]);
    setAuditLogs([]);
  }, [setUser]);

  /** Log in as a seeded demo account (used by the navbar role switcher). */
  const switchRole = useCallback(
    async (role) => {
      const creds = DEMO_ACCOUNTS[role];
      if (!creds) return null;
      return login(creds.email, creds.password);
    },
    [login]
  );

  /**
   * Create a draft (and optionally submit it), attaching any document metadata
   * the wizard collected. Returns the mapped application so the caller can
   * navigate straight to it.
   */
  const createApplication = useCallback(
    async (formData, isSubmitted = false) => {
      // The wizard collects profile details that belong on the borrower record,
      // so persist them first - that is what the officer's review screen reads.
      const profile = {};
      if (formData.phone) profile.phone = formData.phone;
      if (formData.dob) profile.dob = formData.dob;
      if (formData.address) profile.address = formData.address;
      const employmentType = toEmploymentType(formData.employmentType);
      if (employmentType) profile.employment_type = employmentType;
      if (Object.keys(profile).length) {
        await apiService.updateProfile(profile).catch(() => null);
      }

      const created = await apiService.createApplication(toApplicationPayload(formData));
      const applicationId = created.application.id;

      const documents = formData.documents || [];
      if (documents.length) {
        await Promise.all(
          documents.map((doc) =>
            apiService
              .addDocument(applicationId, {
                type: toDocumentType(doc.enumType || doc.type),
                filename: doc.fileName
              })
              .catch(() => null)
          )
        );
      }

      let finalApplication = created.application;
      if (isSubmitted) {
        const submitted = await apiService.submitApplication(applicationId);
        finalApplication = submitted.application;
      }

      await loadApplications();
      return mapApplication(finalApplication);
    },
    [loadApplications]
  );

  /** Record an officer decision and refresh the queue. */
  const decideApplication = useCallback(
    async (applicationId, decision, remarks = '') => {
      let response;
      if (decision === 'APPROVE') {
        response = await apiService.approveApplication(applicationId, remarks);
      } else if (decision === 'REJECT') {
        response = await apiService.rejectApplication(applicationId, remarks);
      } else {
        response = await apiService.requestMoreInfo(applicationId, remarks);
      }
      await loadApplications();
      return mapApplication(response.application);
    },
    [loadApplications]
  );

  const addLoanProduct = useCallback(
    async (productData) => {
      const response = await apiService.createLoanProduct(toProductPayload(productData));
      await loadProducts();
      return mapProduct(response.product);
    },
    [loadProducts]
  );

  const updateScoringRule = useCallback((ruleId, newValue) => {
    setScoringRules((prev) =>
      prev.map((rule) => (rule.id === ruleId ? { ...rule, value: newValue } : rule))
    );
  }, []);

  const value = {
    currentUser,
    userRole: currentUser ? currentUser.role : 'GUEST',
    isLoggedIn,
    isLoading,
    error,
    login,
    register,
    logout,
    switchRole,
    refreshData,
    applications,
    products,
    scoringRules,
    auditLogs,
    usersList,
    createApplication,
    decideApplication,
    addLoanProduct,
    updateScoringRule
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
