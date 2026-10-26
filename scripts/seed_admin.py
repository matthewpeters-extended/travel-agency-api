"""One-off: create the first Admin user so you can log in and create the rest via the API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models import Role, User
from app.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

for name in ("Admin", "Customer"):
    if db.query(Role).filter(Role.name == name).first() is None:
        db.add(Role(name=name))
db.commit()

existing = db.query(User).filter(User.email == "admin@mytravelagency.dev").first()
if existing:
    print("Admin already exists.")
else:
    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    admin = User(
        email="admin@mytravelagency.dev",
        password=hash_password("admin123"),
        roles=[admin_role],
    )
    db.add(admin)
    db.commit()
    print("Created admin@mytravelagency.dev / admin123")

db.close()
