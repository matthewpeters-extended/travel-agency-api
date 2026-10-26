def test_create_user_requires_admin(client, customer_token, auth_header):
    response = client.post(
        "/users",
        json={"email": "new@test-suite.dev", "password": "newpass123"},
        headers=auth_header(customer_token),
    )
    assert response.status_code == 403


def test_create_user_defaults_to_customer_role(client, admin_token, auth_header):
    response = client.post(
        "/users",
        json={"email": "new@test-suite.dev", "password": "newpass123"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201
    assert [r["name"] for r in response.json()["roles"]] == ["Customer"]


def test_create_user_rejects_unknown_role(client, admin_token, auth_header):
    response = client.post(
        "/users",
        json={"email": "new@test-suite.dev", "password": "newpass123", "role_names": ["Superuser"]},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 400


def test_create_user_rejects_duplicate_email(client, admin_token, customer_user, auth_header):
    response = client.post(
        "/users",
        json={"email": "customer@test-suite.dev", "password": "whatever123"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 400


def test_list_users_requires_admin(client, customer_token, auth_header):
    assert client.get("/users", headers=auth_header(customer_token)).status_code == 403


def test_admin_can_list_and_get_users(client, admin_token, customer_user, auth_header):
    listing = client.get("/users", headers=auth_header(admin_token))
    assert listing.status_code == 200
    assert listing.json()["total"] == 2  # admin + customer

    response = client.get(f"/users/{customer_user.id}", headers=auth_header(admin_token))
    assert response.status_code == 200
    assert response.json()["email"] == "customer@test-suite.dev"


def test_update_user_roles(client, admin_token, customer_user, auth_header):
    response = client.put(
        f"/users/{customer_user.id}",
        json={"role_names": ["Admin", "Customer"]},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert {r["name"] for r in response.json()["roles"]} == {"Admin", "Customer"}


def test_delete_user_blocked_when_booked(client, admin_token, customer_token, tour, customer_user, auth_header):
    client.post(f"/tours/{tour.id}/book", headers=auth_header(customer_token))

    response = client.delete(f"/users/{customer_user.id}", headers=auth_header(admin_token))
    assert response.status_code == 400


def test_delete_user_without_bookings(client, admin_token, customer_user, auth_header):
    response = client.delete(f"/users/{customer_user.id}", headers=auth_header(admin_token))
    assert response.status_code == 204
