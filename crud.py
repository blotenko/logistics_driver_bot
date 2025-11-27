from datetime import date
from db import get_session
from models import Driver, Vehicle, Assignment

def list_drivers():
    with get_session() as s:
        return s.query(Driver).order_by(Driver.full_name).all()

def get_assignments_for_driver(name, d=None):
    with get_session() as s:
        q = s.query(Assignment).join(Driver).filter(Driver.full_name == name)
        if d:
            q = q.filter(Assignment.work_date == d)
        return q.order_by(Assignment.work_date).all()

def get_assignments_for_date(d):
    with get_session() as s:
        return (
            s.query(Assignment)
            .filter(Assignment.work_date == d)
            .order_by(Assignment.driver_id)
            .all()
        )
