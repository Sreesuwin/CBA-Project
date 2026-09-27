import axios from 'axios';

/**
 * Axios client for the Flask loan-platform API.
 *
 * There are deliberately **no mock fallbacks** here. The earlier version
 * silently returned fake data whenever the backend was unreachable, which made
 * a broken connection look like a working app - the worst possible behaviour
 * for a demo. Now a failure is a failure, surfaced to the caller.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10000
});

export const TOKEN_KEY = 'auth_token';

// Attach the bearer token to every request.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Turn any axios failure into a plain Error carrying the API's own message.
 *
 * The backend returns `{ error: { status, code, message, details } }` for every
 * failure, so the UI can show a real reason ("Monthly income must be at least
 * 25000.00") instead of a generic "something went wrong".
 */
export function normalizeError(error) {
  if (error.response) {
    const payload = error.response.data?.error || {};
    const wrapped = new Error(payload.message || `Request failed (${error.response.status}).`);
    wrapped.status = error.response.status;
    wrapped.code = payload.code || 'HTTP_ERROR';
    wrapped.details = payload.details || {};
    return wrapped;
  }
  if (error.request) {
    const wrapped = new Error(
      `Cannot reach the API at ${API_BASE_URL}. Is the backend running?`
    );
    wrapped.status = 0;
    wrapped.code = 'NETWORK_ERROR';
    return wrapped;
  }
  return error;
}

// Reject with the normalized error so every `catch` gets the same shape.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(normalizeError(error))
);

const unwrap = (promise) => promise.then((response) => response.data);

/** Pull the first field-level detail out of a 400, for inline form errors. */
export function firstDetail(error) {
  const details = error?.details || {};
  const key = Object.keys(details)[0];
  if (!key) return null;
  const value = details[key];
  return Array.isArray(value) ? value[0] : String(value);
}

export const apiService = {
  // --- Auth -----------------------------------------------------------------
  login: (credentials) => unwrap(apiClient.post('/auth/login', credentials)),

  register: (userData) => unwrap(apiClient.post('/auth/register', userData)),

  changePassword: (data) => unwrap(apiClient.post('/auth/change-password', data)),

  getCurrentUser: () => unwrap(apiClient.get('/users/me')),

  updateProfile: (data) => unwrap(apiClient.put('/users/me', data)),

  listUsers: () => unwrap(apiClient.get('/users')),

  // --- Loan products --------------------------------------------------------
  getLoanProducts: (includeInactive = false) =>
    unwrap(apiClient.get('/loan-products', { params: includeInactive ? { all: 1 } : {} })),

  createLoanProduct: (data) => unwrap(apiClient.post('/loan-products', data)),

  updateLoanProduct: (id, data) => unwrap(apiClient.put(`/loan-products/${id}`, data)),

  // --- Applications ---------------------------------------------------------
  createApplication: (data) => unwrap(apiClient.post('/applications', data)),

  getApplications: (status) =>
    unwrap(apiClient.get('/applications', { params: status ? { status } : {} })),

  getApplicationById: (id) => unwrap(apiClient.get(`/applications/${id}`)),

  updateApplication: (id, data) => unwrap(apiClient.put(`/applications/${id}`, data)),

  submitApplication: (id) => unwrap(apiClient.post(`/applications/${id}/submit`)),

  assessApplication: (id) => unwrap(apiClient.post(`/applications/${id}/assess`)),

  // --- Officer decisions ----------------------------------------------------
  approveApplication: (id, remarks = '') =>
    unwrap(apiClient.post(`/applications/${id}/approve`, { remarks })),

  rejectApplication: (id, remarks = '') =>
    unwrap(apiClient.post(`/applications/${id}/reject`, { remarks })),

  requestMoreInfo: (id, remarks = '') =>
    unwrap(apiClient.post(`/applications/${id}/request-info`, { remarks })),

  // --- Documents & audit ----------------------------------------------------
  getAuditLogs: (id) => unwrap(apiClient.get(`/applications/${id}/audit`)),

  listAllAudit: () => unwrap(apiClient.get('/audit')),

  getDocuments: (id) => unwrap(apiClient.get(`/applications/${id}/documents`)),

  addDocument: (id, data) => unwrap(apiClient.post(`/applications/${id}/documents`, data))
};

export default apiService;
