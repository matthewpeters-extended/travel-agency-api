import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Uuid,
)
from sqlalchemy.orm import relationship

from app.database import Base

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Uuid, ForeignKey("roles.id"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True, index=True)

    users = relationship("User", secondary=user_roles, back_populates="roles")


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    roles = relationship("Role", secondary=user_roles, back_populates="users")
    bookings = relationship("Booking", back_populates="user")

    def has_role(self, name: str) -> bool:
        return any(role.name == name for role in self.roles)


class Travel(Base):
    __tablename__ = "travels"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    is_public = Column(Boolean, nullable=False, default=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    number_of_days = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    tours = relationship("Tour", back_populates="travel")


class Tour(Base):
    __tablename__ = "tours"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    travel_id = Column(Uuid, ForeignKey("travels.id"), nullable=False)
    name = Column(String, nullable=False)
    starting_date = Column(Date, nullable=False)
    ending_date = Column(Date, nullable=False)
    price = Column(Integer, nullable=False)  # integer cents, e.g. 99900 for 999.00
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    travel = relationship("Travel", back_populates="tours")
    bookings = relationship("Booking", back_populates="tour")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    tour_id = Column(Uuid, ForeignKey("tours.id"), nullable=False)
    booked_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="bookings")
    tour = relationship("Tour", back_populates="bookings")
