from database import Base, get_db
from models import User, Student
from fastapi import APIRouter, Depends, HTTPException, Body
from auth import get_current_user, verify_password, hash_password, create_access_token
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from helpers import can_create_student
from sqlalchemy import select
import schemas

router = APIRouter()

def role_required(required_role: str, current_user: User = Depends(get_current_user)):
    if current_user.role != required_role:
        raise HTTPException(status_code=403, detail="Access Denied")
    return current_user


@router.post("/create-user")
async def create_user(
    data: schemas.CreateUser | list[schemas.CreateUser] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "student":
        raise HTTPException(status_code=401, detail="Student Access denied")

    if isinstance(data, list):
        if current_user.role not in ["teacher", "admin"]:
            raise HTTPException(status_code=401, detail="Bulk creation not allowed")
        created_count = 0
        for student_data in data:
            teacher_id = student_data.teacher_id if current_user.role == "admin" else current_user.id
            if current_user.role == "admin" and not teacher_id:
                raise HTTPException(status_code=400, detail="Provide teacher_id for each student")
            if not await can_create_student(teacher_id, db):
                raise HTTPException(status_code=400, detail="Teacher cannot create more than 30 students")
            new_user = User(
                username=student_data.username,
                email=f"{student_data.username}@student.local",
                password=hash_password(student_data.password),
                role="student",
            )
            db.add(new_user)
            await db.flush()
            db.add(Student(
                user_id=new_user.id,
                name=student_data.username,
                grade=student_data.grade,
                created_by=teacher_id
            ))
            created_count += 1
        await db.commit()
        return {"message": f"{created_count} students created successfully"}

    effective_role = "student" if current_user.role == "teacher" else data.role
    if effective_role != "student" and not data.email:
        raise HTTPException(status_code=400, detail="Email is required for teacher/admin")
    if data.email:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Email already exists")
    new_user = User(
        username=data.username,
        email=data.email if effective_role != "student" else f"{data.username}@student.local",
        password=hash_password(data.password),
        role=effective_role
    )
    db.add(new_user)
    await db.flush()
    if effective_role == "student":
        teacher_id = current_user.id if current_user.role == "teacher" else data.teacher_id
        if not teacher_id:
            raise HTTPException(status_code=400, detail="Provide teacher_id for student")
        if not await can_create_student(teacher_id, db):
            raise HTTPException(status_code=400, detail="Teacher cannot create more than 30 students")
        db.add(Student(
            user_id=new_user.id,
            name=data.username,
            grade=data.grade,
            created_by=teacher_id
        ))
    await db.commit()
    return {"message": f"User created successfully with role={effective_role}"}


@router.post("/create-super-admin")
async def create_super_admin(db: AsyncSession = Depends(get_db)):
    new_admin = User(username="Anmol", email="anmol@gmail.com", password=hash_password("1234"), role="admin")
    db.add(new_admin)
    await db.commit()
    await db.flush()
    return {"message": "Super Admin created!!"}


@router.post("/create-admin")
async def create_admin(
    data: schemas.CreateUser,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(lambda: role_required("admin"))
):
    if data.role != "admin":
        raise HTTPException(status_code=400, detail="Only admin allowed")
    new_admin = User(
        username=data.username,
        email=data.email,
        password=hash_password(data.password),
        role="admin"
    )
    db.add(new_admin)
    await db.commit()
    return {"message": "Admin created!!!"}


@router.post("/login-admin")
async def login_admin(
    data: schemas.AdminLogin,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == data.email))
    db_admin = result.scalars().first()
    if not db_admin:
        raise HTTPException(status_code=400, detail="User not found")
    if not verify_password(data.password, db_admin.password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if db_admin.role != "admin":
        raise HTTPException(status_code=401, detail="Only admin login")
    token = create_access_token({"sub": db_admin.email})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login")
async def login(
    data: schemas.AdminLogin,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == data.email))
    db_user = result.scalars().first()
    if not db_user:
        raise HTTPException(status_code=400, detail="User not found")
    if not verify_password(data.password, db_user.password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if data.role in ["admin"]:
        raise HTTPException(status_code=401, detail="Admin login not allowed")
    if db_user.username != data.name:
        raise HTTPException(status_code=400, detail="Incorrect Username")
    if db_user.role != data.role:
        raise HTTPException(status_code=401, detail="Access Denied")
    token = create_access_token({"sub": db_user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/get-students", response_model=schemas.CustomRes)
async def get_all_students(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == "student":
        raise HTTPException(status_code=401, detail="Student cannot access")
    result = await db.execute(select(Student) if current_user.role == "admin" else select(Student).where(Student.created_by == current_user.id))
    students = result.scalars().all()
    return {"data": [{"name": s.name, "grade": s.grade, "user_id": s.user_id} for s in students]}


@router.delete("/delete-student/{student_id}")
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(lambda: role_required("admin"))
):
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=404)
    result = await db.execute(select(User).where(User.id == student.user_id))
    user = result.scalars().first()
    await db.delete(student)
    if user:
        await db.delete(user)
    await db.commit()
    return {"message": "Student Deleted successfully"}


@router.put("/update-student/{student_id}")
async def update_student(
    student_id: int,
    data: schemas.StudentRes,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=404)
    if student.created_by != current_user.id:
        raise HTTPException(status_code=403)
    student.name = data.name
    student.grade = data.grade
    await db.commit()
    await db.refresh(student)
    return student


@router.get("/get")
async def uni_get(
    admin: bool | None = None,
    teacher: bool | None = None,
    teacher_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(lambda: role_required("admin"))
):
    if admin:
        result = await db.execute(select(User).where(User.role == "admin"))
        admins = result.scalars().all()
        return [{"id": u.id, "username": u.username, "email": u.email} for u in admins]
    if teacher:
        result = await db.execute(select(User).where(User.role == "teacher"))
        teachers = result.scalars().all()
        return [{"id": u.id, "username": u.username, "email": u.email} for u in teachers]
    if teacher_id:
        result = await db.execute(select(User).where(User.id == teacher_id, User.role == "teacher"))
        teacher_obj = result.scalars().first()
        if not teacher_obj:
            raise HTTPException(status_code=404, detail="Teacher not found")
        return {"id": teacher_obj.id, "username": teacher_obj.username, "email": teacher_obj.email}
    raise HTTPException(status_code=400, detail="Provide valid query parameter")


@router.get("/my-profile")
async def my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.id == current_user.id).options(
        joinedload(User.student_profile),
        joinedload(User.created_students)
    )
    result = await db.execute(query)
    user = result.unique().scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else user.role
    }
    if user.role == "student" and user.student_profile:
        profile_data["student_profile"] = {
            "id": user.student_profile.id,
            "name": user.student_profile.name,
            "grade": user.student_profile.grade,
            "created_by": user.student_profile.created_by
        }
    if user.role == "teacher" and user.created_students:
        profile_data["created_students"] = [
            {"id": s.id, "name": s.name, "grade": s.grade, "user_id": s.user_id}
            for s in user.created_students
        ]
    return profile_data