from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import Booking, User
from app.schemas import PaginatedBookings

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("/me", response_model=PaginatedBookings)
def list_my_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Booking).filter(Booking.user_id == current_user.id)
    total = query.count()
    items = query.order_by(Booking.booked_at.desc()).offset(skip).limit(limit).all()
    return PaginatedBookings(total=total, skip=skip, limit=limit, items=items)


@router.get("", response_model=PaginatedBookings)
def list_all_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    query = db.query(Booking)
    total = query.count()
    items = query.order_by(Booking.booked_at.desc()).offset(skip).limit(limit).all()
    return PaginatedBookings(total=total, skip=skip, limit=limit, items=items)
