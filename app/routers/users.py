from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Booking, Role, User
from app.schemas import PaginatedUsers, UserCreate, UserOut, UserUpdate
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


def _resolve_roles(db: Session, role_names: list[str]) -> list[Role]:
    roles = db.query(Role).filter(Role.name.in_(role_names)).all()
    found_names = {role.name for role in roles}
    missing = set(role_names) - found_names
    if missing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown role(s): {', '.join(sorted(missing))}")
    return roles


@router.get("", response_model=PaginatedUsers)
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    query = db.query(User)
    total = query.count()
    items = query.order_by(User.created_at).offset(skip).limit(limit).all()
    return PaginatedUsers(total=total, skip=skip, limit=limit, items=items)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    roles = _resolve_roles(db, payload.role_names)

    user = User(email=payload.email, password=hash_password(payload.password), roles=roles)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "email already registered")
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    data = payload.model_dump(exclude_unset=True)
    if "role_names" in data:
        user.roles = _resolve_roles(db, data.pop("role_names"))
    if "password" in data:
        data["password"] = hash_password(data.pop("password"))

    for field, value in data.items():
        setattr(user, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "email already registered")
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    has_bookings = db.query(Booking).filter(Booking.user_id == user.id).first() is not None
    if has_bookings:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete a user with existing bookings")

    db.delete(user)
    db.commit()
