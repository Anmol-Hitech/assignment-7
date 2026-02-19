from models import Student
from sqlalchemy.orm import Session
from fastapi import Depends
from database import get_db
def can_create_student(teacher_id: int, db: Session):
    count = db.query(Student).filter(
        Student.created_by == teacher_id
    ).count()

    return count <= 30