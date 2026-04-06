/**
 * accounts.js — Open accounts, list them, apply monthly interest.
 * Called by app.js when the user navigates to #accounts.
 */

async function renderAccountsView() {
  const content = document.getElementById('content');

  content.innerHTML = `
    <h2 class="page-title">💳 Bank Accounts</h2>
    ${!user.kyc_verified ? kycBanner() : ''}

    <div class="card" id="accounts-list-card">
      <div class="card-header">
        <h3>Your Accounts</h3>
        ${user.kyc_verified
          ? `<button class="btn btn-primary btn-sm" onclick="showOpenAccountForm()">+ Open New Account</button>`
          : ''}
      </div>
      <div class="card-body" id="accounts-list-body">
        <p style="color:var(--text-muted)">Loading…</p>
      </div>
    </div>

    <!-- Open Account form (hidden until button click) -->
    <div class="card" id="open-account-card" style="display:none">
      <div class="card-header">
        <h3>Open New Account</h3>
        <button class="btn btn-outline btn-sm" onclick="hideOpenAccountForm()">✕ Cancel</button>
      </div>
      <div class="card-body">
        <form id="open-account-form" onsubmit="handleOpenAccount(event)" style="max-width:380px">
          <div class="form-group">
            <label>Account Type</label>
            <select id="acc-type" class="input">
              <option value="savings">Savings (min ₹500, 4% p.a.)</option>
              <option value="current">Current (min ₹1,000, 2% p.a.)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Opening Deposit (₹)</label>
            <input id="acc-deposit" type="number" class="input" min="500" step="1" placeholder="e.g. 5000" required />
          </div>
          <p class="form-error" id="acc-error"></p>
          <button type="submit" class="btn btn-primary" id="open-btn">Open Account</button>
        </form>
      </div>
    </div>
  `;

  loadAccountsList();
}

async function loadAccountsList() {
  const body = document.getElementById('accounts-list-body');
  try {
    const accounts = await api.listAccounts();

    if (accounts.length === 0) {
      body.innerHTML = `
        <p style="text-align:center; padding:30px; color:var(--text-muted)">
          You have no accounts yet.
          ${user.kyc_verified ? 'Click "Open New Account" above to get started.' : ''}
        </p>
      `;
      return;
    }

    body.innerHTML = `
      <div class="accounts-grid">
        ${accounts.map(a => `
          <div class="account-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start">
              <div>
                <div class="acc-type"><span class="badge badge-${a.account_type}">${a.account_type}</span></div>
                <div class="acc-num">${a.account_number}</div>
              </div>
              <span class="badge ${a.is_active ? 'badge-success' : 'badge-danger'}">${a.is_active ? 'Active' : 'Inactive'}</span>
            </div>
            <div class="acc-bal">₹${fmt(a.balance)}</div>
            <div class="acc-meta">Min balance: ₹${fmt(a.minimum_balance)}</div>
            <div class="acc-meta" style="margin-bottom:12px">Interest rate: ${a.interest_rate}% p.a.</div>
            <button class="btn btn-outline btn-sm" onclick="applyInterest('${a.account_number}', this)">
              📈 Apply Monthly Interest
            </button>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    body.innerHTML = `<p style="color:var(--danger)">${err.message}</p>`;
  }
}

function showOpenAccountForm() {
  document.getElementById('open-account-card').style.display = 'block';
  document.getElementById('acc-deposit').focus();
}

function hideOpenAccountForm() {
  document.getElementById('open-account-card').style.display = 'none';
}

async function handleOpenAccount(e) {
  e.preventDefault();
  const type    = document.getElementById('acc-type').value;
  const deposit = parseFloat(document.getElementById('acc-deposit').value);
  const errEl   = document.getElementById('acc-error');
  const btn     = document.getElementById('open-btn');
  errEl.classList.remove('show');

  const original = btn.textContent;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Opening…';

  try {
    await api.openAccount(type, deposit);
    showToast(`${type} account opened successfully!`, 'success');
    hideOpenAccountForm();
    document.getElementById('open-account-form').reset();
    loadAccountsList();   // refresh the list
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add('show');
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

async function applyInterest(accountNumber, btn) {
  const original = btn.textContent;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>';

  try {
    const result = await api.applyInterest(accountNumber);
    showToast(`Interest ₹${fmt(result.interest_earned)} added. New balance: ₹${fmt(result.new_balance)}`, 'success');
    loadAccountsList();   // refresh to show updated balance
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}
