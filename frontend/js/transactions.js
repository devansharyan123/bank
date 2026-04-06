/**
 * transactions.js — Deposit, withdraw, transfer, and history.
 * Called by app.js when the user navigates to #transactions.
 */

let _txAccounts = [];  // cached account list for the dropdowns

async function renderTransactionsView() {
  const content = document.getElementById('content');

  content.innerHTML = `
    <h2 class="page-title">💸 Transactions</h2>

    <!-- Account selector -->
    <div class="card">
      <div class="card-header"><h3>Select Account</h3></div>
      <div class="card-body">
        <div class="form-group" style="max-width:320px; margin-bottom:0">
          <label>Account</label>
          <select id="tx-account-select" class="input" onchange="onAccountChange()">
            <option value="">— choose an account —</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Action sub-tabs -->
    <div class="sub-tabs">
      <button class="sub-tab-btn active" id="stab-deposit"  onclick="showSubTab('deposit')">💰 Deposit</button>
      <button class="sub-tab-btn"        id="stab-withdraw" onclick="showSubTab('withdraw')">🏧 Withdraw</button>
      <button class="sub-tab-btn"        id="stab-transfer" onclick="showSubTab('transfer')">🔄 Transfer</button>
    </div>

    <!-- Deposit panel -->
    <div id="panel-deposit" class="card">
      <div class="card-header"><h3>Deposit Money</h3></div>
      <div class="card-body">
        <form id="deposit-form" onsubmit="handleDeposit(event)" style="max-width:340px">
          <div class="form-group">
            <label>Amount (₹)</label>
            <input id="deposit-amount" type="number" class="input" min="1" step="1" placeholder="e.g. 5000" required />
          </div>
          <p class="form-error" id="deposit-error"></p>
          <button type="submit" class="btn btn-primary" id="deposit-btn">Deposit</button>
        </form>
      </div>
    </div>

    <!-- Withdraw panel -->
    <div id="panel-withdraw" class="card" style="display:none">
      <div class="card-header"><h3>Withdraw Money</h3></div>
      <div class="card-body">
        <form id="withdraw-form" onsubmit="handleWithdraw(event)" style="max-width:340px">
          <div class="form-group">
            <label>Amount (₹)</label>
            <input id="withdraw-amount" type="number" class="input" min="1" step="1" placeholder="e.g. 2000" required />
          </div>
          <p class="form-error" id="withdraw-error"></p>
          <button type="submit" class="btn btn-danger" id="withdraw-btn">Withdraw</button>
        </form>
      </div>
    </div>

    <!-- Transfer panel -->
    <div id="panel-transfer" class="card" style="display:none">
      <div class="card-header"><h3>Transfer Money</h3></div>
      <div class="card-body">
        <form id="transfer-form" onsubmit="handleTransfer(event)" style="max-width:400px">
          <div class="form-group">
            <label>Recipient Account Number</label>
            <input id="transfer-to" type="text" class="input" placeholder="e.g. ACC1002" required />
          </div>
          <div class="form-group">
            <label>Amount (₹)</label>
            <input id="transfer-amount" type="number" class="input" min="1" step="1" placeholder="e.g. 1000" required />
          </div>
          <div class="form-group" style="display:flex; align-items:center; gap:10px">
            <input type="checkbox" id="simulate-failure" style="width:16px; height:16px" />
            <label for="simulate-failure" style="margin:0; cursor:pointer">
              🧪 Simulate failure (demo ACID rollback)
            </label>
          </div>
          <p style="font-size:0.82rem; color:var(--text-muted); margin-bottom:12px">
            When checked, the transfer will fail midway and money will roll back to your account automatically.
          </p>
          <p class="form-error" id="transfer-error"></p>
          <button type="submit" class="btn btn-primary" id="transfer-btn">Transfer</button>
        </form>
      </div>
    </div>

    <!-- Transaction history -->
    <div class="card" id="history-card" style="display:none">
      <div class="card-header"><h3>Transaction History</h3></div>
      <div class="card-body table-wrap" id="history-body">
        <p style="color:var(--text-muted)">Loading history…</p>
      </div>
    </div>
  `;

  // Load accounts into the dropdown
  try {
    _txAccounts = await api.listAccounts();
    const select = document.getElementById('tx-account-select');
    _txAccounts.forEach(a => {
      const opt = document.createElement('option');
      opt.value = a.account_number;
      opt.textContent = `${a.account_number} — ${a.account_type} — ₹${fmt(a.balance)}`;
      select.appendChild(opt);
    });
    // Auto-select first account
    if (_txAccounts.length > 0) {
      select.value = _txAccounts[0].account_number;
      onAccountChange();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function showSubTab(name) {
  ['deposit', 'withdraw', 'transfer'].forEach(t => {
    document.getElementById(`panel-${t}`).style.display = t === name ? 'block' : 'none';
    document.getElementById(`stab-${t}`).classList.toggle('active', t === name);
  });
}

function onAccountChange() {
  const accountNumber = document.getElementById('tx-account-select').value;
  if (accountNumber) {
    document.getElementById('history-card').style.display = 'block';
    loadHistory(accountNumber);
  }
}

async function loadHistory(accountNumber) {
  const body = document.getElementById('history-body');
  body.innerHTML = '<p style="color:var(--text-muted)">Loading…</p>';
  try {
    const txns = await api.getHistory(accountNumber);
    if (txns.length === 0) {
      body.innerHTML = '<p class="no-data" style="text-align:center; padding:30px; color:var(--text-muted)">No transactions yet.</p>';
      return;
    }
    body.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Reference</th>
            <th>Type</th>
            <th>Amount</th>
            <th>Status</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          ${txns.map(tx => `
            <tr>
              <td style="white-space:nowrap">${new Date(tx.created_at).toLocaleString('en-IN')}</td>
              <td><code style="font-size:0.82rem">${tx.reference_id}</code></td>
              <td>${typeBadge(tx.transaction_type)}</td>
              <td><strong>₹${fmt(tx.amount)}</strong></td>
              <td>${statusBadge(tx.status)}</td>
              <td style="font-size:0.82rem; color:var(--text-muted)">
                ${tx.is_flagged ? `<span class="badge badge-flagged" title="${tx.flagged_reason}">⚠️ Flagged</span> ` : ''}
                ${tx.failure_reason ? `<span title="${tx.failure_reason}" style="color:var(--danger)">↩ Rolled back</span>` : ''}
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

async function handleDeposit(e) {
  e.preventDefault();
  const accountNumber = document.getElementById('tx-account-select').value;
  const amount = parseFloat(document.getElementById('deposit-amount').value);
  const errEl  = document.getElementById('deposit-error');
  errEl.classList.remove('show');

  if (!accountNumber) { errEl.textContent = 'Please select an account.'; errEl.classList.add('show'); return; }

  const btn = document.getElementById('deposit-btn');
  const orig = btn.textContent;
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';

  try {
    await api.deposit(accountNumber, amount);
    showToast(`₹${fmt(amount)} deposited successfully!`, 'success');
    document.getElementById('deposit-form').reset();
    loadHistory(accountNumber);
  } catch (err) {
    errEl.textContent = err.message; errEl.classList.add('show');
  } finally {
    btn.disabled = false; btn.textContent = orig;
  }
}

async function handleWithdraw(e) {
  e.preventDefault();
  const accountNumber = document.getElementById('tx-account-select').value;
  const amount = parseFloat(document.getElementById('withdraw-amount').value);
  const errEl  = document.getElementById('withdraw-error');
  errEl.classList.remove('show');

  if (!accountNumber) { errEl.textContent = 'Please select an account.'; errEl.classList.add('show'); return; }

  const btn = document.getElementById('withdraw-btn');
  const orig = btn.textContent;
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';

  try {
    await api.withdraw(accountNumber, amount);
    showToast(`₹${fmt(amount)} withdrawn successfully!`, 'success');
    document.getElementById('withdraw-form').reset();
    loadHistory(accountNumber);
  } catch (err) {
    errEl.textContent = err.message; errEl.classList.add('show');
  } finally {
    btn.disabled = false; btn.textContent = orig;
  }
}

async function handleTransfer(e) {
  e.preventDefault();
  const fromAccount   = document.getElementById('tx-account-select').value;
  const toAccount     = document.getElementById('transfer-to').value.trim();
  const amount        = parseFloat(document.getElementById('transfer-amount').value);
  const simulateFail  = document.getElementById('simulate-failure').checked;
  const errEl         = document.getElementById('transfer-error');
  errEl.classList.remove('show');

  if (!fromAccount) { errEl.textContent = 'Please select a sender account.'; errEl.classList.add('show'); return; }

  const btn = document.getElementById('transfer-btn');
  const orig = btn.textContent;
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';

  try {
    const result = await api.transfer(fromAccount, toAccount, amount, simulateFail);
    if (result.status === 'failed') {
      showToast(`Transfer failed — money rolled back to your account. Reason: ${result.failure_reason}`, 'error');
    } else {
      showToast(`₹${fmt(amount)} transferred successfully! Ref: ${result.reference_id}`, 'success');
    }
    document.getElementById('transfer-form').reset();
    loadHistory(fromAccount);
  } catch (err) {
    errEl.textContent = err.message; errEl.classList.add('show');
  } finally {
    btn.disabled = false; btn.textContent = orig;
  }
}
