"""Tests for deposit, withdraw, transfer, and the ACID rollback demo."""


def setup_user_with_account(client, email, deposit=5000, account_type="savings"):
    """Helper: register, KYC, open account, return (headers, account_number)."""
    client.post("/auth/register", json={"name": "User", "email": email, "password": "pass1234"})
    login = client.post("/auth/login", json={"email": email, "password": "pass1234"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/auth/kyc", json={"aadhaar_number": "1234-5678-9012", "pan_number": "ABCDE1234F"}, headers=headers)
    acc = client.post("/accounts/", json={"account_type": account_type, "initial_deposit": deposit}, headers=headers).json()
    return headers, acc["account_number"]


def test_deposit(client):
    headers, account_number = setup_user_with_account(client, "deposit_user@test.com")
    response = client.post("/transactions/deposit", json={
        "account_number": account_number,
        "amount": 2000,
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_withdraw_within_balance(client):
    headers, account_number = setup_user_with_account(client, "withdraw_user@test.com", deposit=5000)
    response = client.post("/transactions/withdraw", json={
        "account_number": account_number,
        "amount": 1000,
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_withdraw_below_minimum_balance(client):
    """Withdrawing too much should be rejected to protect the minimum balance."""
    headers, account_number = setup_user_with_account(client, "minbal_withdraw@test.com", deposit=600)
    response = client.post("/transactions/withdraw", json={
        "account_number": account_number,
        "amount": 500,   # would leave only ₹100, below ₹500 minimum
    }, headers=headers)
    assert response.status_code == 400


def test_successful_transfer(client):
    """Transfer money between two accounts — both balances should update."""
    h1, acc1 = setup_user_with_account(client, "sender@test.com", deposit=5000)
    h2, acc2 = setup_user_with_account(client, "receiver@test.com", deposit=1000)

    response = client.post("/transactions/transfer", json={
        "from_account_number": acc1,
        "to_account_number": acc2,
        "amount": 1000,
        "simulate_failure": False,
    }, headers=h1)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_transfer_rollback_demo(client):
    """
    ACID rollback demo: simulate_failure=True should fail the transfer
    and leave the sender's balance unchanged.
    """
    h1, acc1 = setup_user_with_account(client, "rollback_sender@test.com", deposit=5000)
    h2, acc2 = setup_user_with_account(client, "rollback_receiver@test.com", deposit=1000)

    # Get sender's balance before the failed transfer
    before = client.get(f"/accounts/{acc1}", headers=h1).json()["balance"]

    response = client.post("/transactions/transfer", json={
        "from_account_number": acc1,
        "to_account_number": acc2,
        "amount": 1000,
        "simulate_failure": True,  # intentionally fail mid-transfer
    }, headers=h1)
    assert response.status_code == 200
    assert response.json()["status"] == "failed"

    # Sender's balance must be exactly the same as before — rollback worked
    after = client.get(f"/accounts/{acc1}", headers=h1).json()["balance"]
    assert float(before) == float(after)


def test_transaction_history(client):
    headers, account_number = setup_user_with_account(client, "history_user@test.com", deposit=5000)
    client.post("/transactions/deposit", json={"account_number": account_number, "amount": 500}, headers=headers)
    client.post("/transactions/withdraw", json={"account_number": account_number, "amount": 200}, headers=headers)

    response = client.get(f"/transactions/history/{account_number}", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 2
