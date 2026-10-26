def test_list_travels_only_shows_public(client, public_travel, private_travel):
    response = client.get("/travels")
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["slug"] == "test-travel"


def test_get_private_travel_is_404_for_everyone(client, private_travel):
    response = client.get(f"/travels/{private_travel.id}")
    assert response.status_code == 404


def test_get_public_travel(client, public_travel):
    response = client.get(f"/travels/{public_travel.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Travel"


def test_list_travels_filters_by_days(client, db_session):
    from app.models import Travel

    db_session.add_all(
        [
            Travel(is_public=True, slug="short-trip", name="Short Trip", number_of_days=3),
            Travel(is_public=True, slug="long-trip", name="Long Trip", number_of_days=20),
        ]
    )
    db_session.commit()

    response = client.get("/travels?min_days=10")
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["slug"] == "long-trip"


def test_list_travels_search_by_name(client, db_session):
    from app.models import Travel

    db_session.add(Travel(is_public=True, slug="desert-safari", name="Desert Safari", number_of_days=4))
    db_session.commit()

    response = client.get("/travels?q=safari")
    assert response.json()["total"] == 1


def test_create_travel_requires_admin(client, customer_token, auth_header):
    response = client.post(
        "/travels",
        json={"name": "New Trip", "number_of_days": 5},
        headers=auth_header(customer_token),
    )
    assert response.status_code == 403


def test_create_travel_auto_generates_unique_slug(client, admin_token, auth_header):
    first = client.post(
        "/travels",
        json={"name": "Coastal Tour", "number_of_days": 7, "is_public": True},
        headers=auth_header(admin_token),
    )
    assert first.status_code == 201
    assert first.json()["slug"] == "coastal-tour"

    second = client.post(
        "/travels",
        json={"name": "Coastal Tour", "number_of_days": 7, "is_public": True},
        headers=auth_header(admin_token),
    )
    assert second.status_code == 201
    assert second.json()["slug"] == "coastal-tour-2"


def test_update_travel(client, admin_token, public_travel, auth_header):
    response = client.put(
        f"/travels/{public_travel.id}",
        json={"number_of_days": 99},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["number_of_days"] == 99


def test_delete_travel_blocked_when_tours_exist(client, admin_token, tour, auth_header):
    response = client.delete(f"/travels/{tour.travel_id}", headers=auth_header(admin_token))
    assert response.status_code == 400


def test_delete_travel_without_tours(client, admin_token, public_travel, auth_header):
    response = client.delete(f"/travels/{public_travel.id}", headers=auth_header(admin_token))
    assert response.status_code == 204
    assert client.get(f"/travels/{public_travel.id}").status_code == 404
