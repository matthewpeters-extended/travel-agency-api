from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth --------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Roles / users -----------------------------------------------------------


class RoleOut(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role_names: list[str] = Field(default_factory=lambda: ["Customer"])


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    role_names: list[str] | None = None


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    roles: list[RoleOut]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedUsers(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[UserOut]


# --- Travels -----------------------------------------------------------------


class TravelCreate(BaseModel):
    name: str
    description: str | None = None
    number_of_days: int = Field(gt=0)
    is_public: bool = False
    slug: str | None = None


class TravelUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    number_of_days: int | None = Field(default=None, gt=0)
    is_public: bool | None = None
    slug: str | None = None


class TravelOut(BaseModel):
    id: UUID
    is_public: bool
    slug: str
    name: str
    description: str | None
    number_of_days: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedTravels(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[TravelOut]


# --- Tours ---------------------------------------------------------------------


class TourCreate(BaseModel):
    travel_id: UUID
    name: str
    starting_date: date
    ending_date: date
    price: int = Field(gt=0, description="Integer cents, e.g. 99900 for 999.00")


class TourUpdate(BaseModel):
    name: str | None = None
    starting_date: date | None = None
    ending_date: date | None = None
    price: int | None = Field(default=None, gt=0)


class TourOut(BaseModel):
    id: UUID
    travel_id: UUID
    name: str
    starting_date: date
    ending_date: date
    price: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedTours(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[TourOut]


# --- Bookings ------------------------------------------------------------------


class BookingOut(BaseModel):
    id: UUID
    user_id: UUID
    tour_id: UUID
    booked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedBookings(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[BookingOut]
