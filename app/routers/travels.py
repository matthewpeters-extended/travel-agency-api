from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Travel, User
from app.schemas import PaginatedTravels, TravelCreate, TravelOut, TravelUpdate
from app.utils import slugify

router = APIRouter(prefix="/travels", tags=["travels"])

SORT_FIELDS = {
    "name": Travel.name,
    "number_of_days": Travel.number_of_days,
    "created_at": Travel.created_at,
}


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    suffix = 2
    while db.query(Travel).filter(Travel.slug == slug).first() is not None:
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


@router.get("", response_model=PaginatedTravels)
def list_travels(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, description="Keyword match against name/description"),
    min_days: int | None = Query(None, ge=1),
    max_days: int | None = Query(None, ge=1),
    sort: str = Query("created_at", pattern="^(name|number_of_days|created_at)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """Public: only ever returns travels marked is_public. Admins manage
    (and receive full objects back for) private travels through the write
    endpoints below instead of browsing for them here."""
    query = db.query(Travel).filter(Travel.is_public.is_(True))

    if q:
        query = query.filter(
            (Travel.name.ilike(f"%{q}%")) | (Travel.description.ilike(f"%{q}%"))
        )
    if min_days is not None:
        query = query.filter(Travel.number_of_days >= min_days)
    if max_days is not None:
        query = query.filter(Travel.number_of_days <= max_days)

    column = SORT_FIELDS[sort]
    query = query.order_by(column.desc() if order == "desc" else column.asc())

    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return PaginatedTravels(total=total, skip=skip, limit=limit, items=items)


@router.get("/{travel_id}", response_model=TravelOut)
def get_travel(travel_id: UUID, db: Session = Depends(get_db)):
    travel = db.get(Travel, travel_id)
    if travel is None or not travel.is_public:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Travel not found")
    return travel


@router.post("", response_model=TravelOut, status_code=status.HTTP_201_CREATED)
def create_travel(
    payload: TravelCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    slug = slugify(payload.slug) if payload.slug else slugify(payload.name)
    slug = _unique_slug(db, slug)

    travel = Travel(
        is_public=payload.is_public,
        slug=slug,
        name=payload.name,
        description=payload.description,
        number_of_days=payload.number_of_days,
    )
    db.add(travel)
    db.commit()
    db.refresh(travel)
    return travel


@router.put("/{travel_id}", response_model=TravelOut)
def update_travel(
    travel_id: UUID,
    payload: TravelUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    travel = db.get(Travel, travel_id)
    if travel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Travel not found")

    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"]:
        candidate = slugify(data["slug"])
        if candidate != travel.slug:
            data["slug"] = _unique_slug(db, candidate)
        else:
            data.pop("slug")

    for field, value in data.items():
        setattr(travel, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "slug already exists")
    db.refresh(travel)
    return travel


@router.delete("/{travel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_travel(
    travel_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    travel = db.get(Travel, travel_id)
    if travel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Travel not found")

    if travel.tours:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete a travel with existing tours")

    db.delete(travel)
    db.commit()
