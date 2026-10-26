import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.limiter import limiter
from app.main import app
from app.models import Role, Travel, Tour, User
from app.security import hash_password

# The /login rate limit is for real-world abuse prevention; it would otherwise
# fire mid-suite since slowapi keys by client IP and the test client always
# looks like the same IP.
limiter.enabled = False

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    # app.main seeds roles into the real on-disk database at import time; the
    # test database is a separate in-memory engine, so it needs its own copy
    # of the fixed role set.
    for name in ("Admin", "Customer"):
        session.add(Role(name=name))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _role(db_session, name):
    return db_session.query(Role).filter(Role.name == name).first()


def _make_user(db_session, email, password, role_name):
    user = User(email=email, password=hash_password(password), roles=[_role(db_session, role_name)])
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _login(client, email, password):
    response = client.post("/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def admin_user(db_session):
    return _make_user(db_session, "admin@test-suite.dev", "admin12345", "Admin")


@pytest.fixture()
def customer_user(db_session):
    return _make_user(db_session, "customer@test-suite.dev", "customer12345", "Customer")


@pytest.fixture()
def other_customer_user(db_session):
    return _make_user(db_session, "other@test-suite.dev", "other12345", "Customer")


@pytest.fixture()
def admin_token(client, admin_user):
    return _login(client, "admin@test-suite.dev", "admin12345")


@pytest.fixture()
def customer_token(client, customer_user):
    return _login(client, "customer@test-suite.dev", "customer12345")


@pytest.fixture()
def other_customer_token(client, other_customer_user):
    return _login(client, "other@test-suite.dev", "other12345")


@pytest.fixture()
def auth_header():
    def _header(token):
        return {"Authorization": f"Bearer {token}"}

    return _header


@pytest.fixture()
def public_travel(db_session):
    travel = Travel(is_public=True, slug="test-travel", name="Test Travel", number_of_days=5)
    db_session.add(travel)
    db_session.commit()
    db_session.refresh(travel)
    return travel


@pytest.fixture()
def private_travel(db_session):
    travel = Travel(is_public=False, slug="private-travel", name="Private Travel", number_of_days=3)
    db_session.add(travel)
    db_session.commit()
    db_session.refresh(travel)
    return travel


@pytest.fixture()
def tour(db_session, public_travel):
    from datetime import date, timedelta

    today = date.today()
    tour = Tour(
        travel_id=public_travel.id,
        name="Test Tour",
        starting_date=today + timedelta(days=10),
        ending_date=today + timedelta(days=15),
        price=50000,
    )
    db_session.add(tour)
    db_session.commit()
    db_session.refresh(tour)
    return tour
