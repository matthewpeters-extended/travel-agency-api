from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import Booking, Tour, Travel, User
from app.schemas import BookingOut, PaginatedTours, TourCreate, TourOut, TourUpdate

router = APIRouter(prefix="/tours", tags=["tours"])

SORT_FIELDS = {
    "price": Tour.price,
    "starting_date": Tour.starting_date,
}


@router.get("", response_model=PaginatedTours)
def list_tours(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    travel_id: UUID | None = Query(None),
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    starting_after: date | None = Query(None),
    starting_before: date | None = Query(None),
    sort: str = Query("starting_date", pattern="^(price|starting_date)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """Public: only ever returns tours that belong to a public travel."""
    query = db.query(Tour).join(Travel).filter(Travel.is_public.is_(True))

    if travel_id is not None:
        query = query.filter(Tour.travel_id == travel_id)
    if min_price is not None:
        query = query.filter(Tour.price >= min_price)
    if max_price is not None:
        query = query.filter(Tour.price <= max_price)
    if starting_after is not None:
        query = query.filter(Tour.starting_date >= starting_after)
    if starting_before is not None:
        query = query.filter(Tour.starting_date <= starting_before)

    column = SORT_FIELDS[sort]
    query = query.order_by(column.desc() if order == "desc" else column.asc())

    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return PaginatedTours(total=total, skip=skip, limit=limit, items=items)


@router.get("/{tour_id}", response_model=TourOut)
def get_tour(tour_id: UUID, db: Session = Depends(get_db)):
    tour = db.get(Tour, tour_id)
    if tour is None or not tour.travel.is_public:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tour not found")
    return tour


@router.post("", response_model=TourOut, status_code=status.HTTP_201_CREATED)
def create_tour(
    payload: TourCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    travel = db.get(Travel, payload.travel_id)
    if travel is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "travel_id does not exist")
    if payload.ending_date < payload.starting_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ending_date cannot be before starting_date")

    tour = Tour(
        travel_id=payload.travel_id,
        name=payload.name,
        starting_date=payload.starting_date,
        ending_date=payload.ending_date,
        price=payload.price,
    )
    db.add(tour)
    db.commit()
    db.refresh(tour)
    return tour


@router.put("/{tour_id}", response_model=TourOut)
def update_tour(
    tour_id: UUID,
    payload: TourUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    tour = db.get(Tour, tour_id)
    if tour is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tour not found")

    data = payload.model_dump(exclude_unset=True)
    starting_date = data.get("starting_date", tour.starting_date)
    ending_date = data.get("ending_date", tour.ending_date)
    if ending_date < starting_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ending_date cannot be before starting_date")

    for field, value in data.items():
        setattr(tour, field, value)

    db.commit()
    db.refresh(tour)
    return tour


@router.delete("/{tour_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tour(
    tour_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    tour = db.get(Tour, tour_id)
    if tour is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tour not found")

    has_bookings = db.query(Booking).filter(Booking.tour_id == tour.id).first() is not None
    if has_bookings:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete a tour with existing bookings")

    db.delete(tour)
    db.commit()


@router.post("/{tour_id}/book", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def book_tour(
    tour_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tour = db.get(Tour, tour_id)
    if tour is None or not tour.travel.is_public:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tour not found")

    if tour.ending_date < datetime.utcnow().date():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This tour has already ended")

    booking = Booking(user_id=current_user.id, tour_id=tour.id)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking
