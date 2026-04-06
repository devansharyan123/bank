/**
 * loans.js — EMI calculator, apply for loan, view my loans.
 * Called by app.js when the user navigates to #loans.
 */

async function renderLoansView() {
  const content = document.getElementById('content');

  content.innerHTML = `
    <h2 class="page-title">🏦 Loans</h2>
    ${!user.kyc_verified ? kycBanner() : ''}

    <!-- EMI Calculator -->
    <div class="card">
      <div class="card-header"><h3>📐 EMI Calculator</h3></div>
      <div class="card-body">
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:24px; align-items:start">
          <form id="emi-calc-form" onsubmit="calculateEMI(event)" style="max-width:360px">
            <div class="form-group">
              <label>Principal Amount (₹)</label>
              <input id="emi-principal" type="number" class="input" min="1000" step="1000" placeholder="e.g. 100000" required />
            </div>
            <div class="form-group">
              <label>Annual Interest Rate (%)</label>
              <input id="emi-rate" type="number" class="input" min="1" max="50" step="0.1" placeholder="e.g. 10.5" required />
            </div>
            <div class="form-group">
              <label>Tenure (months)</label>
              <input id="emi-tenure" type="number" class="input" min="1" max="360" step="1" placeholder="e.g. 24" required />
            </div>
            <div style="display:flex; gap:10px">
              <button type="submit" class="btn btn-primary">Calculate EMI</button>
            </div>
          </form>

          <div id="emi-result" style="display:none">
            <!-- filled by calculateEMI() -->
          </div>
        </div>
      </div>
    </div>

    <!-- Apply for loan (hidden until EMI calc or direct click) -->
    ${user.kyc_verified ? `
      <div class="card" id="apply-loan-card" style="display:none">
        <div class="card-header">
          <h3>Apply for Loan</h3>
          <button class="btn btn-outline btn-sm" onclick="document.getElementById('apply-loan-card').style.display='none'">✕</button>
        </div>
        <div class="card-body">
          <form id="apply-loan-form" onsubmit="handleApplyLoan(event)" style="max-width:380px">
            <div class="form-group">
              <label>Principal Amount (₹)</label>
              <input id="loan-principal" type="number" class="input" min="1000" step="1000" required />
            </div>
            <div class="form-group">
              <label>Annual Interest Rate (%)</label>
              <input id="loan-rate" type="number" class="input" min="1" max="50" step="0.1" required />
            </div>
            <div class="form-group">
              <label>Tenure (months)</label>
              <input id="loan-tenure" type="number" class="input" min="1" max="360" step="1" required />
            </div>
            <p class="form-error" id="loan-error"></p>
            <button type="submit" class="btn btn-primary" id="loan-apply-btn">Submit Application</button>
          </form>
        </div>
      </div>
    ` : ''}

    <!-- My Loans -->
    <div class="card">
      <div class="card-header">
        <h3>My Loan Applications</h3>
        ${user.kyc_verified
          ? `<button class="btn btn-primary btn-sm" onclick="document.getElementById('apply-loan-card').style.display='block'">+ Apply for Loan</button>`
          : ''}
      </div>
      <div class="card-body table-wrap" id="loans-table-body">
        <p style="color:var(--text-muted)">Loading…</p>
      </div>
    </div>
  `;

  loadMyLoans();
}

async function calculateEMI(e) {
  e.preventDefault();
  const principal = parseFloat(document.getElementById('emi-principal').value);
  const rate      = parseFloat(document.getElementById('emi-rate').value);
  const tenure    = parseInt(document.getElementById('emi-tenure').value);
  const resultDiv = document.getElementById('emi-result');

  try {
    const r = await api.calculateEMI(principal, rate, tenure);
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = `
      <div class="emi-result">
        <div class="emi-label">Monthly EMI</div>
        <div class="emi-main">₹${fmt(r.monthly_emi)}</div>
        <div class="emi-row">
          <span>Principal: ₹${fmt(r.principal)}</span>
          <span>Rate: ${r.annual_rate}% p.a.</span>
          <span>Tenure: ${r.tenure_months} months</span>
        </div>
        <div class="emi-row" style="margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.2)">
          <span>Total Payment: ₹${fmt(r.total_payment)}</span>
          <span>Total Interest: ₹${fmt(r.total_interest)}</span>
        </div>
        ${user.kyc_verified ? `
          <button class="btn btn-outline btn-sm" style="margin-top:14px; color:#fff; border-color:rgba(255,255,255,0.5)"
            onclick="prefillApplyForm(${r.principal}, ${r.annual_rate}, ${r.tenure_months})">
            Apply for this Loan →
          </button>
        ` : ''}
      </div>
    `;
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function prefillApplyForm(principal, rate, tenure) {
  document.getElementById('loan-principal').value = principal;
  document.getElementById('loan-rate').value      = rate;
  document.getElementById('loan-tenure').value    = tenure;
  document.getElementById('apply-loan-card').style.display = 'block';
  document.getElementById('apply-loan-card').scrollIntoView({ behavior: 'smooth' });
}

async function handleApplyLoan(e) {
  e.preventDefault();
  const principal = parseFloat(document.getElementById('loan-principal').value);
  const rate      = parseFloat(document.getElementById('loan-rate').value);
  const tenure    = parseInt(document.getElementById('loan-tenure').value);
  const errEl     = document.getElementById('loan-error');
  const btn       = document.getElementById('loan-apply-btn');
  errEl.classList.remove('show');

  const orig = btn.textContent;
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Submitting…';

  try {
    const loan = await api.applyLoan(principal, rate, tenure);
    showToast(`Loan application submitted! EMI: ₹${fmt(loan.emi_amount)}/month`, 'success');
    document.getElementById('apply-loan-card').style.display = 'none';
    document.getElementById('apply-loan-form').reset();
    loadMyLoans();
  } catch (err) {
    errEl.textContent = err.message; errEl.classList.add('show');
  } finally {
    btn.disabled = false; btn.textContent = orig;
  }
}

async function loadMyLoans() {
  const body = document.getElementById('loans-table-body');
  try {
    const loans = await api.getMyLoans();
    if (loans.length === 0) {
      body.innerHTML = '<p style="text-align:center; padding:30px; color:var(--text-muted)">No loan applications yet.</p>';
      return;
    }
    body.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Principal</th>
            <th>Rate</th>
            <th>Tenure</th>
            <th>Monthly EMI</th>
            <th>Status</th>
            <th>Applied On</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          ${loans.map(l => `
            <tr>
              <td>${l.id}</td>
              <td><strong>₹${fmt(l.principal)}</strong></td>
              <td>${l.annual_rate}%</td>
              <td>${l.tenure_months} months</td>
              <td>₹${fmt(l.emi_amount)}</td>
              <td>${statusBadge(l.status)}</td>
              <td style="white-space:nowrap; font-size:0.82rem">${new Date(l.created_at).toLocaleDateString('en-IN')}</td>
              <td style="font-size:0.82rem; color:var(--danger)">${l.rejection_reason || ''}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    body.innerHTML = `<p style="color:var(--danger)">${err.message}</p>`;
  }
}
