from datetime import date, timedelta


def test_book_tour_requires_auth(client, tour):
    response = client.post(f"/tours/{tour.id}/book")
    assert response.status_code == 401


def test_book_tour(client, customer_token, tour, auth_header):
    response = client.post(f"/tours/{tour.id}/book", headers=auth_header(customer_token))
    assert response.status_code == 201
    assert response.json()["tour_id"] == str(tour.id)


def test_cannot_book_tour_under_private_travel(client, db_session, customer_token, private_travel, auth_header):
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

    response = client.post(f"/tours/{hidden.id}/book", headers=auth_header(customer_token))
    assert response.status_code == 404


def test_cannot_book_ended_tour(client, db_session, customer_token, public_travel, auth_header):
    from app.models import Tour

    today = date.today()
    ended = Tour(
        travel_id=public_travel.id,
        name="Past Tour",
        starting_date=today - timedelta(days=10),
        ending_date=today - timedelta(days=5),
        price=10000,
    )
    db_session.add(ended)
    db_session.commit()
    db_session.refresh(ended)

    response = client.post(f"/tours/{ended.id}/book", headers=auth_header(customer_token))
    assert response.status_code == 400


def test_list_my_bookings_only_shows_own(client, tour, customer_token, other_customer_token, auth_header):
    client.post(f"/tours/{tour.id}/book", headers=auth_header(customer_token))

    mine = client.get("/bookings/me", headers=auth_header(customer_token)).json()
    assert mine["total"] == 1

    others = client.get("/bookings/me", headers=auth_header(other_customer_token)).json()
    assert others["total"] == 0


def test_list_all_bookings_requires_admin(client, customer_token, auth_header):
    response = client.get("/bookings", headers=auth_header(customer_token))
    assert response.status_code == 403


def test_admin_can_list_all_bookings(client, tour, customer_token, admin_token, auth_header):
    client.post(f"/tours/{tour.id}/book", headers=auth_header(customer_token))

    response = client.get("/bookings", headers=auth_header(admin_token))
    assert response.status_code == 200
    assert response.json()["total"] == 1
