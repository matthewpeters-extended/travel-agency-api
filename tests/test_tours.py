from datetime import date, timedelta


def test_list_tours_hides_tours_under_private_travels(client, db_session, private_travel):
    from app.models import Tour

    today = date.today()
    db_session.add(
        Tour(
            travel_id=private_travel.id,
            name="Hidden Tour",
            starting_date=today + timedelta(days=5),
            ending_date=today + timedelta(days=10),
            price=10000,
        )
    )
    db_session.commit()

    response = client.get("/tours")
    assert response.json()["total"] == 0


def test_get_tour_under_private_travel_is_404(client, db_session, private_travel):
    from app.models import Tour

    today = date.today()
    hidden = Tour(
        travel_id=private_travel.id,
        name="Hidden Tour",
        starting_date=today + timedelta(days=5),
        ending_date=today + timedelta(days=10),
        price=10000,
    )
    db_session.add(hidden)
    db_session.commit()
    db_session.refresh(hidden)

    assert client.get(f"/tours/{hidden.id}").status_code == 404


def test_list_tours_filters_by_price(client, tour):
    response = client.get("/tours?min_price=60000")
    assert response.json()["total"] == 0

    response = client.get("/tours?min_price=10000&max_price=100000")
    assert response.json()["total"] == 1


def test_create_tour_requires_existing_travel(client, admin_token, auth_header):
    response = client.post(
        "/tours",
        json={
            "travel_id": "00000000-0000-0000-0000-000000000000",
            "name": "Ghost Tour",
            "starting_date": "2030-01-01",
            "ending_date": "2030-01-05",
            "price": 10000,
        },
        headers=auth_header(admin_token),
    )
    assert response.status_code == 400


def test_create_tour_rejects_ending_before_starting(client, admin_token, public_travel, auth_header):
    response = client.post(
        "/tours",
        json={
            "travel_id": str(public_travel.id),
            "name": "Backwards Tour",
            "starting_date": "2030-01-10",
            "ending_date": "2030-01-05",
            "price": 10000,
        },
        headers=auth_header(admin_token),
    )
    assert response.status_code == 400


def test_create_tour_requires_admin(client, customer_token, public_travel, auth_header):
    response = client.post(
        "/tours",
        json={
            "travel_id": str(public_travel.id),
            "name": "Unauthorized Tour",
            "starting_date": "2030-01-01",
            "ending_date": "2030-01-05",
            "price": 10000,
        },
        headers=auth_header(customer_token),
    )
    assert response.status_code == 403


def test_delete_tour_blocked_when_booked(client, admin_token, customer_token, tour, auth_header):
    client.post(f"/tours/{tour.id}/book", headers=auth_header(customer_token))

    response = client.delete(f"/tours/{tour.id}", headers=auth_header(admin_token))
    assert response.status_code == 400


def test_delete_tour_without_bookings(client, admin_token, tour, auth_header):
    response = client.delete(f"/tours/{tour.id}", headers=auth_header(admin_token))
    assert response.status_code == 204
