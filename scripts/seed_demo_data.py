"""One-off: add a sample public travel with two tours, and a Customer
account, for manual testing. Run seed_admin.py first."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models import Role, Travel, Tour, User
from app.security import hash_password
from app.utils import slugify

Base.metadata.create_all(bind=engine)

db = SessionLocal()

travel = db.query(Travel).filter(Travel.slug == "patagonia-trek").first()
if travel is None:
    travel = Travel(
        is_public=True,
        slug=slugify("Patagonia Trek"),
        name="Patagonia Trek",
        description="Multi-day trekking through Torres del Paine.",
        number_of_days=9,
    )
    db.add(travel)
    db.commit()
    db.refresh(travel)

    today = date.today()
    db.add_all(
        [
            Tour(
                travel_id=travel.id,
                name="Spring departure",
                starting_date=today + timedelta(days=30),
                ending_date=today + timedelta(days=39),
                price=249900,
            ),
            Tour(
                travel_id=travel.id,
                name="Autumn departure",
                starting_date=today + timedelta(days=120),
                ending_date=today + timedelta(days=129),
                price=219900,
            ),
        ]
    )
    db.commit()
    print("Created Patagonia Trek travel with two tours.")
else:
    print("Demo travel already exists.")

customer = db.query(User).filter(User.email == "customer@mytravelagency.dev").first()
if customer is None:
    customer_role = db.query(Role).filter(Role.name == "Customer").first()
    customer = User(
        email="customer@mytravelagency.dev",
        password=hash_password("customer123"),
        roles=[customer_role],
    )
    db.add(customer)
    db.commit()
    print("Created customer@mytravelagency.dev / customer123")
else:
    print("Demo customer already exists.")

db.close()
