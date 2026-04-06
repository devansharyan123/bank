/**
 * admin.js — Admin-only views: stats, loan approvals, user list, fraud alerts.
 * app.js only renders these nav items when role === 'admin'.
 */

// -----------------------------------------------------------------------
// Admin Overview — stats dashboard
// -----------------------------------------------------------------------

async function renderAdminOverview() {
  if (user?.role !== 'admin') { navigate('#overview'); return; }

  const content = document.getElementById('content');
  content.innerHTML = `<h2 class="page-title">📊 Admin Dashboard</h2><p style="color:var(--text-muted)">Loading stats…</p>`;

  try {
    const stats = await api.getDashboard();
    content.innerHTML = `
      <h2 class="page-title">📊 Admin Dashboard</h2>
      <div class="stat-row">
        <div class="stat-card">
          <div class="label">Total Users</div>
          <div class="value blue">${stats.total_users}</div>
        </div>
        <div class="stat-card">
          <div class="label">Total Accounts</div>
          <div class="value">${stats.total_accounts}</div>
        </div>
        <div class="stat-card">
          <div class="label">Transactions</div>
          <div class="value">${stats.total_transactions}</div>
        </div>
        <div class="stat-card">
          <div class="label">Pending Loans</div>
          <div class="value orange">${stats.pending_loans}</div>
        </div>
        <div class="stat-card">
          <div class="label">Fraud Flags</div>
          <div class="value red">${stats.flagged_transactions}</div>
        </div>
        <div class="stat-card">
          <div class="label">Total Deposits</div>
          <div class="value green">₹${fmt(stats.total_deposits)}</div>
        </div>
        <div class="stat-card">
          <div class="label">Total Withdrawals</div>
          <div class="value red">₹${fmt(stats.total_withdrawals)}</div>
        </div>
        <div class="stat-card">
          <div class="label">Total Loans</div>
          <div class="value">${stats.total_loans}</div>
        </div>
      </div>
    `;
  } catch (err) {
    content.innerHTML += `<p style="color:var(--danger)">${err.message}</p>`;
  }
}

// -----------------------------------------------------------------------
// Admin Loan Approvals
// -----------------------------------------------------------------------

async function renderAdminLoansView() {
  if (user?.role !== 'admin') { navigate('#overview'); return; }

  const content = document.getElementById('content');
  content.innerHTML = `
    <h2 class="page-title">✅ Loan Approvals</h2>
    <div class="card">
      <div class="card-body table-wrap" id="admin-loans-body">
        <p style="color:var(--text-muted)">Loading…</p>
      </div>
    </div>
  `;

  loadAdminLoans();
}

async function loadAdminLoans() {
  const body = document.getElementById('admin-loans-body');
  try {
    const loans = await api.getAllLoans();
    if (loans.length === 0) {
      body.innerHTML = '<p style="text-align:center; padding:30px; color:var(--text-muted)">No loan applications yet.</p>';
      return;
    }
    body.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>#</th>
            <th>User ID</th>
            <th>Principal</th>
            <th>Rate</th>
            <th>Tenure</th>
            <th>EMI/Month</th>
            <th>Status</th>
            <th>Date</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${loans.map(l => `
            <tr id="loan-row-${l.id}">
              <td>${l.id}</td>
              <td>${l.user_id || '—'}</td>
              <td>₹${fmt(l.principal)}</td>
              <td>${l.annual_rate}%</td>
              <td>${l.tenure_months}m</td>
              <td>₹${fmt(l.emi_amount)}</td>
              <td>${statusBadge(l.status)}</td>
              <td style="white-space:nowrap; font-size:0.82rem">${new Date(l.created_at).toLocaleDateString('en-IN')}</td>
              <td>
                ${l.status === 'pending' ? `
                  <div style="display:flex; gap:6px; flex-wrap:wrap">
                    <button class="btn btn-success btn-sm" onclick="approveLoan(${l.id}, this)">Approve</button>
                    <button class="btn btn-danger  btn-sm" onclick="showRejectInput(${l.id})">Reject</button>
                  </div>
                  <div class="reject-input" id="reject-input-${l.id}">
                    <input class="input" id="reject-reason-${l.id}" placeholder="Rejection reason…" style="font-size:0.82rem; padding:5px 8px" />
                    <button class="btn btn-danger btn-sm" onclick="rejectLoan(${l.id})">Confirm</button>
                    <button class="btn btn-outline btn-sm" onclick="hideRejectInput(${l.id})">✕</button>
                  </div>
                ` : `<span style="color:var(--text-muted); font-size:0.82rem">${l.rejection_reason || '—'}</span>`}
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    body.innerHTML = `<p style="color:var(--danger)">${err.message}</p>`;
  }
}

function showRejectInput(loanId) {
  document.getElementById(`reject-input-${loanId}`).classList.add('show');
}
function hideRejectInput(loanId) {
  document.getElementById(`reject-input-${loanId}`).classList.remove('show');
}

async function approveLoan(loanId, btn) {
  const orig = btn.textContent;
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
  try {
    await api.approveLoan(loanId);
    showToast(`Loan #${loanId} approved.`, 'success');
    loadAdminLoans();
  } catch (err) {
    showToast(err.message, 'error');
    btn.disabled = false; btn.textContent = orig;
  }
}

async function rejectLoan(loanId) {
  const reason = document.getElementById(`reject-reason-${loanId}`).value.trim();
  if (!reason) { showToast('Please enter a rejection reason.', 'error'); return; }
  try {
    await api.rejectLoan(loanId, reason);
    showToast(`Loan #${loanId} rejected.`, 'info');
    loadAdminLoans();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// -----------------------------------------------------------------------
// Admin Users list
// -----------------------------------------------------------------------

async function renderAdminUsersView() {
  if (user?.role !== 'admin') { navigate('#overview'); return; }

  const content = document.getElementById('content');
  content.innerHTML = `
    <h2 class="page-title">👥 All Users</h2>
    <div class="card">
      <div class="card-body table-wrap" id="admin-users-body">
        <p style="color:var(--text-muted)">Loading…</p>
      </div>
    </div>
  `;

  try {
    const users = await api.getAllUsers();
    const body  = document.getElementById('admin-users-body');
    body.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>KYC</th>
            <th>Accounts</th>
          </tr>
        </thead>
        <tbody>
          ${users.map(u => `
            <tr>
              <td>${u.id}</td>
              <td>${u.name}</td>
              <td>${u.email}</td>
              <td><span class="badge ${u.role === 'admin' ? 'badge-warning' : 'badge-info'}">${u.role}</span></td>
              <td>${u.kyc_verified
                ? '<span class="badge badge-success">Verified</span>'
                : '<span class="badge badge-danger">Pending</span>'}</td>
              <td>${u.account_count}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    document.getElementById('admin-users-body').innerHTML = `<p style="color:var(--danger)">${err.message}</p>`;
  }
}

// -----------------------------------------------------------------------
// Admin Fraud Alerts
// -----------------------------------------------------------------------

async function renderAdminFraudView() {
  if (user?.role !== 'admin') { navigate('#overview'); return; }

  const content = document.getElementById('content');
  content.innerHTML = `
    <h2 class="page-title">🚨 Fraud Alerts</h2>
    <div class="card">
      <div class="card-body table-wrap" id="fraud-alerts-body">
        <p style="color:var(--text-muted)">Loading…</p>
      </div>
    </div>
  `;

  try {
    const alerts = await api.getFraudAlerts();
    const body   = document.getElementById('fraud-alerts-body');

    if (alerts.length === 0) {
      body.innerHTML = '<p style="text-align:center; padding:30px; color:var(--success)">✅ No fraud alerts. All clear.</p>';
      return;
    }

    body.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Reference</th>
            <th>Amount</th>
            <th>From Account</th>
            <th>To Account</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          ${alerts.map(a => `
            <tr>
              <td style="white-space:nowrap; font-size:0.82rem">${new Date(a.created_at).toLocaleString('en-IN')}</td>
              <td><code style="font-size:0.8rem">${a.reference_id}</code></td>
              <td><strong style="color:var(--danger)">₹${fmt(a.amount)}</strong></td>
              <td>${a.from_account_number || '—'}</td>
              <td>${a.to_account_number   || '—'}</td>
              <td style="font-size:0.82rem; color:var(--warning)">${a.flagged_reason || '—'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    document.getElementById('fraud-alerts-body').innerHTML = `<p style="color:var(--danger)">${err.message}</p>`;
  }
}
