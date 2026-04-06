/**
 * app.js — Dashboard bootstrap.
 *
 * Runs first on dashboard.html.
 * 1. Checks the user is logged in, redirects if not.
 * 2. Builds the sidebar based on user role.
 * 3. Listens to hash changes and renders the right view.
 */

// -----------------------------------------------------------------------
// Auth guard — must run before anything else
// -----------------------------------------------------------------------
(function requireAuth() {
  if (!getToken()) window.location.href = 'index.html';
})();

const user = getUser();

// -----------------------------------------------------------------------
// Sidebar
// -----------------------------------------------------------------------

const NAV_ITEMS_CUSTOMER = [
  { hash: '#overview',     icon: '🏠', label: 'Overview'     },
  { hash: '#kyc',          icon: '🪪', label: 'KYC'          },
  { hash: '#accounts',     icon: '💳', label: 'Accounts'     },
  { hash: '#transactions', icon: '💸', label: 'Transactions' },
  { hash: '#loans',        icon: '🏦', label: 'Loans'        },
];

const NAV_ITEMS_ADMIN = [
  ...NAV_ITEMS_CUSTOMER,
  { hash: '#admin-overview', icon: '📊', label: 'Admin Stats'    },
  { hash: '#admin-loans',    icon: '✅', label: 'Loan Approvals' },
  { hash: '#admin-users',    icon: '👥', label: 'All Users'      },
  { hash: '#admin-fraud',    icon: '🚨', label: 'Fraud Alerts'   },
];

function buildSidebar() {
  document.getElementById('sidebar-username').textContent = user?.name || 'User';
  document.getElementById('sidebar-role').textContent =
    user?.role === 'admin' ? 'Admin Portal' : 'Customer Portal';

  const items = user?.role === 'admin' ? NAV_ITEMS_ADMIN : NAV_ITEMS_CUSTOMER;
  const nav   = document.getElementById('sidebar-nav');
  nav.innerHTML = items.map(item => `
    <div class="nav-item" data-hash="${item.hash}" onclick="navigate('${item.hash}')">
      <span class="icon">${item.icon}</span>
      <span>${item.label}</span>
    </div>
  `).join('');
}

function setActiveNav(hash) {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.hash === hash);
  });
}

// -----------------------------------------------------------------------
// Router
// -----------------------------------------------------------------------

function navigate(hash) {
  window.location.hash = hash;
}

function route() {
  const hash = window.location.hash || '#overview';
  setActiveNav(hash);

  const content = document.getElementById('content');
  content.innerHTML = '<p style="color:var(--text-muted); padding:20px">Loading…</p>';

  switch (hash) {
    case '#overview':       renderOverview();           break;
    case '#kyc':            renderKYCView();            break;
    case '#accounts':       renderAccountsView();       break;
    case '#transactions':   renderTransactionsView();   break;
    case '#loans':          renderLoansView();          break;
    case '#admin-overview': renderAdminOverview();      break;
    case '#admin-loans':    renderAdminLoansView();     break;
    case '#admin-users':    renderAdminUsersView();     break;
    case '#admin-fraud':    renderAdminFraudView();     break;
    default:                renderOverview();
  }
}

window.addEventListener('hashchange', route);

// -----------------------------------------------------------------------
// Overview (home) view
// -----------------------------------------------------------------------

async function renderOverview() {
  const content = document.getElementById('content');
  try {
    const [accounts, loans] = await Promise.all([api.listAccounts(), api.getMyLoans()]);
    const totalBalance = accounts.reduce((s, a) => s + parseFloat(a.balance), 0);
    const activeLoans  = loans.filter(l => l.status === 'approved' || l.status === 'active').length;

    content.innerHTML = `
      <h2 class="page-title">Welcome back, ${user.name} 👋</h2>
      ${!user.kyc_verified ? kycBanner() : ''}

      <div class="stat-row">
        <div class="stat-card">
          <div class="label">Total Balance</div>
          <div class="value blue">₹${fmt(totalBalance)}</div>
        </div>
        <div class="stat-card">
          <div class="label">Accounts</div>
          <div class="value">${accounts.length}</div>
        </div>
        <div class="stat-card">
          <div class="label">Active Loans</div>
          <div class="value orange">${activeLoans}</div>
        </div>
        <div class="stat-card">
          <div class="label">KYC Status</div>
          <div class="value ${user.kyc_verified ? 'green' : 'red'}">${user.kyc_verified ? 'Verified' : 'Pending'}</div>
        </div>
      </div>

      ${accounts.length > 0 ? `
        <div class="card">
          <div class="card-header"><h3>Your Accounts</h3></div>
          <div class="card-body">
            <div class="accounts-grid">
              ${accounts.map(a => accountCard(a)).join('')}
            </div>
          </div>
        </div>
      ` : `
        <div class="card">
          <div class="card-body" style="text-align:center; padding:40px; color:var(--text-muted)">
            No accounts yet.
            ${user.kyc_verified
              ? '<br><br><button class="btn btn-primary" onclick="navigate(\'#accounts\')">Open First Account</button>'
              : '<br><br><button class="btn btn-primary" onclick="navigate(\'#kyc\')">Complete KYC First</button>'
            }
          </div>
        </div>
      `}
    `;
  } catch (err) {
    content.innerHTML = `<p style="color:var(--danger)">${err.message}</p>`;
  }
}

// -----------------------------------------------------------------------
// KYC view
// -----------------------------------------------------------------------

function renderKYCView() {
  const content = document.getElementById('content');
  const already = user.kyc_verified;

  content.innerHTML = `
    <h2 class="page-title">🪪 KYC Verification</h2>
    <p class="page-subtitle">Submit your Aadhaar and PAN to activate your account</p>

    ${already ? `
      <div class="card">
        <div class="card-body" style="text-align:center; padding:40px">
          <div style="font-size:3rem">✅</div>
          <h3 style="margin-top:12px; color:var(--success)">KYC Verified</h3>
          <p style="color:var(--text-muted); margin-top:8px">Your identity has been verified. You can open bank accounts and apply for loans.</p>
        </div>
      </div>
    ` : `
      <div class="card">
        <div class="card-header"><h3>Submit KYC Details</h3></div>
        <div class="card-body">
          <form id="kyc-form" onsubmit="submitKYC(event)" style="max-width:400px">
            <div class="form-group">
              <label>Aadhaar Number</label>
              <input class="input" id="kyc-aadhaar" type="text"
                placeholder="XXXX-XXXX-XXXX"
                pattern="\\d{4}-\\d{4}-\\d{4}"
                title="Format: XXXX-XXXX-XXXX"
                required />
              <span style="font-size:0.78rem; color:var(--text-muted)">Format: 1234-5678-9012</span>
            </div>
            <div class="form-group">
              <label>PAN Number</label>
              <input class="input" id="kyc-pan" type="text"
                placeholder="ABCDE1234F"
                pattern="[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}"
                title="Format: ABCDE1234F"
                maxlength="10"
                style="text-transform:uppercase"
                required />
              <span style="font-size:0.78rem; color:var(--text-muted)">Format: ABCDE1234F</span>
            </div>
            <p class="form-error" id="kyc-error"></p>
            <button type="submit" class="btn btn-primary" id="kyc-btn">Verify KYC</button>
          </form>
        </div>
      </div>
    `}
  `;
}

async function submitKYC(e) {
  e.preventDefault();
  const aadhaar = document.getElementById('kyc-aadhaar').value;
  const pan     = document.getElementById('kyc-pan').value.toUpperCase();
  const errEl   = document.getElementById('kyc-error');
  errEl.classList.remove('show');

  try {
    const updated = await api.submitKYC(aadhaar, pan);
    // Update local user object so the banner disappears
    user.kyc_verified = true;
    saveSession(getToken(), user);
    showToast('KYC verified successfully! You can now open accounts.', 'success');
    renderKYCView();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add('show');
  }
}

// -----------------------------------------------------------------------
// Shared helpers
// -----------------------------------------------------------------------

function kycBanner() {
  return `
    <div class="kyc-banner">
      <span class="kyc-icon">⚠️</span>
      <span>
        Your KYC is not verified yet.
        <a href="#" onclick="navigate('#kyc')">Complete KYC</a>
        to open accounts and apply for loans.
      </span>
    </div>
  `;
}

function accountCard(a) {
  return `
    <div class="account-card">
      <div class="acc-type">${a.account_type} account</div>
      <div class="acc-num">${a.account_number}</div>
      <div class="acc-bal">₹${fmt(a.balance)}</div>
      <div class="acc-meta">Min balance: ₹${fmt(a.minimum_balance)} &nbsp;|&nbsp; Interest: ${a.interest_rate}% p.a.</div>
    </div>
  `;
}

function fmt(n) {
  return parseFloat(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function statusBadge(status) {
  const map = {
    success: 'badge-success', failed: 'badge-danger',
    pending: 'badge-pending', approved: 'badge-success',
    rejected: 'badge-danger', active: 'badge-info', closed: 'badge-info',
  };
  return `<span class="badge ${map[status] || 'badge-info'}">${status}</span>`;
}

function typeBadge(type) {
  return `<span class="badge badge-${type}">${type}</span>`;
}

// -----------------------------------------------------------------------
// Toast
// -----------------------------------------------------------------------

let toastTimer;
function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className   = `show ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.className = ''; }, 3500);
}

// -----------------------------------------------------------------------
// Logout
// -----------------------------------------------------------------------

function logout() {
  clearSession();
  window.location.href = 'index.html';
}

// -----------------------------------------------------------------------
// Boot
// -----------------------------------------------------------------------

buildSidebar();
route();
