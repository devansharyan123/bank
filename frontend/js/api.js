/**
 * api.js — All communication with the backend lives here.
 *
 * Every other JS file calls functions from this module.
 * Auth headers, error handling, and the 401 redirect happen here once.
 */

const BASE_URL = 'http://localhost:8000';

// -----------------------------------------------------------------------
// Token helpers
// -----------------------------------------------------------------------

function getToken() {
  return localStorage.getItem('bank_token');
}

function getUser() {
  const raw = localStorage.getItem('bank_user');
  return raw ? JSON.parse(raw) : null;
}

function saveSession(token, user) {
  localStorage.setItem('bank_token', token);
  localStorage.setItem('bank_user', JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem('bank_token');
  localStorage.removeItem('bank_user');
}

// -----------------------------------------------------------------------
// Core fetch wrapper
// -----------------------------------------------------------------------

async function request(method, path, body = null, requiresAuth = true) {
  const headers = { 'Content-Type': 'application/json' };

  if (requiresAuth) {
    const token = getToken();
    if (!token) {
      window.location.href = 'index.html';
      return;
    }
    headers['Authorization'] = `Bearer ${token}`;
  }

  const options = { method, headers };
  if (body !== null) options.body = JSON.stringify(body);

  const response = await fetch(`${BASE_URL}${path}`, options);

  // Session expired — send back to login
  if (response.status === 401) {
    clearSession();
    window.location.href = 'index.html';
    return;
  }

  const data = await response.json();

  if (!response.ok) {
    // Backend sends errors as { detail: "..." }
    const message = data.detail || `Request failed (${response.status})`;
    throw new Error(message);
  }

  return data;
}

// -----------------------------------------------------------------------
// Auth endpoints
// -----------------------------------------------------------------------

const api = {

  async register(name, email, password) {
    return request('POST', '/auth/register', { name, email, password }, false);
  },

  async login(email, password) {
    const data = await request('POST', '/auth/login', { email, password }, false);
    // Fetch the full user profile to know their role and KYC status
    const tempToken = data.access_token;
    localStorage.setItem('bank_token', tempToken);
    const user = await request('GET', '/auth/me');
    saveSession(tempToken, user);
    return user;
  },

  async getMe() {
    return request('GET', '/auth/me');
  },

  async submitKYC(aadhaar_number, pan_number) {
    const user = await request('POST', '/auth/kyc', { aadhaar_number, pan_number });
    // Update the stored user so kyc_verified reflects the new state
    saveSession(getToken(), user);
    return user;
  },

  // -----------------------------------------------------------------------
  // Account endpoints
  // -----------------------------------------------------------------------

  async openAccount(account_type, initial_deposit) {
    return request('POST', '/accounts/', { account_type, initial_deposit });
  },

  async listAccounts() {
    return request('GET', '/accounts/');
  },

  async getAccount(account_number) {
    return request('GET', `/accounts/${account_number}`);
  },

  async applyInterest(account_number) {
    return request('POST', `/accounts/${account_number}/apply-interest`);
  },

  // -----------------------------------------------------------------------
  // Transaction endpoints
  // -----------------------------------------------------------------------

  async deposit(account_number, amount) {
    return request('POST', '/transactions/deposit', { account_number, amount });
  },

  async withdraw(account_number, amount) {
    return request('POST', '/transactions/withdraw', { account_number, amount });
  },

  async transfer(from_account_number, to_account_number, amount, simulate_failure = false) {
    return request('POST', '/transactions/transfer', {
      from_account_number,
      to_account_number,
      amount,
      simulate_failure,
    });
  },

  async getHistory(account_number) {
    return request('GET', `/transactions/history/${account_number}`);
  },

  // -----------------------------------------------------------------------
  // Loan endpoints
  // -----------------------------------------------------------------------

  async calculateEMI(principal, annual_rate, tenure_months) {
    return request('POST', '/loans/calculate-emi', { principal, annual_rate, tenure_months }, false);
  },

  async applyLoan(principal, annual_rate, tenure_months) {
    return request('POST', '/loans/apply', { principal, annual_rate, tenure_months });
  },

  async getMyLoans() {
    return request('GET', '/loans/my-loans');
  },

  // -----------------------------------------------------------------------
  // Admin endpoints
  // -----------------------------------------------------------------------

  async getDashboard() {
    return request('GET', '/admin/dashboard');
  },

  async getFraudAlerts() {
    return request('GET', '/admin/fraud-alerts');
  },

  async getAllUsers() {
    return request('GET', '/admin/users');
  },

  async getAllLoans() {
    return request('GET', '/loans/all');
  },

  async approveLoan(loan_id) {
    return request('POST', `/loans/${loan_id}/approve`);
  },

  async rejectLoan(loan_id, rejection_reason) {
    return request('POST', `/loans/${loan_id}/reject`, { rejection_reason });
  },
};
