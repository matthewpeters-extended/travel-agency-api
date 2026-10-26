def test_login_success(client, admin_user):
    response = client.post("/login", json={"email": "admin@test-suite.dev", "password": "admin12345"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_rejects_wrong_password(client, admin_user):
    response = client.post("/login", json={"email": "admin@test-suite.dev", "password": "wrong"})
    assert response.status_code == 401


def test_login_rejects_unknown_email(client):
    response = client.post("/login", json={"email": "nobody@test-suite.dev", "password": "whatever123"})
    assert response.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/me").status_code == 401


def test_me_returns_roles(client, customer_user, customer_token, auth_header):
    response = client.get("/me", headers=auth_header(customer_token))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "customer@test-suite.dev"
    assert [r["name"] for r in body["roles"]] == ["Customer"]
