"""Tests for account creation, listing, and interest application."""


def register_and_login(client, email="user@test.com", password="pass1234"):
    """Helper: register a user, complete KYC, and return auth headers."""
    client.post("/auth/register", json={"name": "Test User", "email": email, "password": password})
    login = client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Complete KYC
    client.post("/auth/kyc", json={"aadhaar_number": "1234-5678-9012", "pan_number": "ABCDE1234F"}, headers=headers)
    return headers


def test_open_savings_account(client):
    headers = register_and_login(client, "savings_user@test.com")
    response = client.post("/accounts/", json={
        "account_type": "savings",
        "initial_deposit": 1000,
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["account_type"] == "savings"
    assert float(data["balance"]) == 1000.0


def test_open_account_without_kyc(client):
    """Opening an account should fail if KYC is not done."""
    client.post("/auth/register", json={"name": "NoKYC", "email": "nokyc@test.com", "password": "pass1234"})
    login = client.post("/auth/login", json={"email": "nokyc@test.com", "password": "pass1234"})
    token = login.json()["access_token"]

    response = client.post("/accounts/", json={
        "account_type": "savings",
        "initial_deposit": 1000,
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_open_account_below_minimum_balance(client):
    headers = register_and_login(client, "minbal@test.com")
    response = client.post("/accounts/", json={
        "account_type": "savings",
        "initial_deposit": 100,   # below ₹500 minimum
    }, headers=headers)
    assert response.status_code == 400


def test_list_accounts(client):
    headers = register_and_login(client, "listuser@test.com")
    client.post("/accounts/", json={"account_type": "savings", "initial_deposit": 1000}, headers=headers)
    client.post("/accounts/", json={"account_type": "current", "initial_deposit": 2000}, headers=headers)

    response = client.get("/accounts/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_apply_monthly_interest(client):
    headers = register_and_login(client, "interest_user@test.com")
    acc = client.post("/accounts/", json={"account_type": "savings", "initial_deposit": 10000}, headers=headers).json()

    response = client.post(f"/accounts/{acc['account_number']}/apply-interest", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert float(data["interest_earned"]) > 0
    assert float(data["new_balance"]) > 10000
