from fastapi import Depends, FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import models  # noqa: F401  (import so Base knows about the tables)
from app.database import Base, SessionLocal, engine
from app.deps import get_current_user
from app.limiter import limiter
from app.models import Role, User
from app.routers import auth, bookings, tours, travels, users
from app.schemas import UserOut

Base.metadata.create_all(bind=engine)

DEFAULT_ROLES = ("Admin", "Customer")


def _seed_roles():
    db = SessionLocal()
    try:
        existing = {role.name for role in db.query(Role).all()}
        for name in DEFAULT_ROLES:
            if name not in existing:
                db.add(Role(name=name))
        db.commit()
    finally:
        db.close()


_seed_roles()

app = FastAPI(title="Travel Agency API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth.router)
app.include_router(travels.router)
app.include_router(tours.router)
app.include_router(bookings.router)
app.include_router(users.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
