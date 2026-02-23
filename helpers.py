from models import Student
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from database import get_db
from sqlalchemy import select,func
async def can_create_student(teacher_id: int, db: AsyncSession):
    result = await db.execute(
        select(func.count(Student.id)).where(Student.created_by == teacher_id)
    )
    count = result.scalar() or 0
    return count < 30