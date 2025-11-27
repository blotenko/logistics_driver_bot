from sqlalchemy import Column, Integer, Text, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from db import Base

class Driver(Base):
    __tablename__ = 'drivers'

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    assignments: Mapped[list["Assignment"]] = relationship(back_populates="driver")

class Vehicle(Base):
    __tablename__ = 'vehicles'

    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    brand: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="active")
    notes: Mapped[str | None] = mapped_column(Text)

    assignments: Mapped[list["Assignment"]] = relationship(back_populates="vehicle")

class Assignment(Base):
    __tablename__ = 'assignments'

    id: Mapped[int] = mapped_column(primary_key=True)
    work_date: Mapped[Date] = mapped_column(Date, nullable=False)

    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"))
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"))

    task_type: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    manager: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="planned")

    driver: Mapped[Driver] = relationship(back_populates="assignments")
    vehicle: Mapped[Vehicle | None] = relationship(back_populates="assignments")
