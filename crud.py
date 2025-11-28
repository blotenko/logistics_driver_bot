from datetime import date
from typing import List, Optional

from sqlalchemy.orm import joinedload

from db import get_session
from models import Driver, Vehicle, Assignment


def list_drivers() -> List[Driver]:
    with get_session() as s:
        return (
            s.query(Driver)
            .order_by(Driver.full_name)
            .all()
        )


def list_vehicles() -> List[Vehicle]:
    with get_session() as s:
        return (
            s.query(Vehicle)
            .order_by(Vehicle.plate)
            .all()
        )


def get_assignments_for_driver(
    name: str,
    d: Optional[date] = None,
) -> List[Assignment]:
    with get_session() as s:
        q = (
            s.query(Assignment)
            .options(
                joinedload(Assignment.driver),
                joinedload(Assignment.vehicle),
            )
            .join(Driver)
            .filter(Driver.full_name == name)
        )

        if d:
            q = q.filter(Assignment.work_date == d)

        return q.order_by(Assignment.work_date).all()


def get_assignments_for_date(d: date) -> List[Assignment]:
    with get_session() as s:
        return (
            s.query(Assignment)
            .options(
                joinedload(Assignment.driver),
                joinedload(Assignment.vehicle),
            )
            .filter(Assignment.work_date == d)
            .order_by(Assignment.driver_id)
            .all()
        )


def create_driver(full_name: str):
    """Создаёт водителя, если его ещё нет."""
    full_name = full_name.strip()
    if not full_name:
        return None

    with get_session() as s:
        drv = (
            s.query(Driver)
            .filter(Driver.full_name == full_name)
            .first()
        )
        if drv:
            return drv

        drv = Driver(full_name=full_name, active=True)
        s.add(drv)
        s.flush()
        return drv


def create_assignment(work_date, driver_id, vehicle_id, task_type, description, manager="Система"):
    with get_session() as s:
        a = Assignment(
            work_date=work_date,
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            task_type=task_type,
            description=description,
            manager=manager,
            status="planned",
        )
        s.add(a)
        s.flush()
        return a
