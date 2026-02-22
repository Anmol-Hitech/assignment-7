from database import Base,get_db
from models import User,Student
from fastapi import APIRouter,Depends,HTTPException,Body
from auth import get_current_user,verify_password,hash_password,create_access_token
from sqlalchemy.orm import Session
from helpers import can_create_student
import schemas
router=APIRouter()


@router.post("/create-user")
def create_user(
    data: schemas.CreateUser | list[schemas.CreateUser] = Body(...),
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "student":
        raise HTTPException(status_code=401, detail="Student Access denied")

    if isinstance(data, list):
        if current_user.role not in ["teacher", "admin"]:
            raise HTTPException(status_code=401, detail="Bulk creation not allowed")

        students_to_create = []

        for student_data in data:
            effective_role = "student"
            teacher_id = student_data.teacher_id if current_user.role == "admin" else current_user.id
            if current_user.role == "admin" and not teacher_id:
                raise HTTPException(status_code=400, detail="Provide teacher_id for each student")
            if not can_create_student(teacher_id, db):
                raise HTTPException(status_code=400, detail="Teacher cannot create more than 30 students")
            hashed_password = hash_password(student_data.password)
            new_user = User(
                username=student_data.username,
                email=f"{student_data.username}@student.local",
                password=hashed_password,
                role=effective_role,
            )
            students_to_create.append(new_user)

        db.add_all(students_to_create)
        db.commit()

        for u in students_to_create:
            db.refresh(u)

        student_records = [
            Student(
                user_id=u.id,
                name=u.username,
                grade=data[i].grade,
                created_by=current_user.id if current_user.role == "teacher" else data[i].teacher_id
            )
            for i, u in enumerate(students_to_create)
        ]

        db.bulk_save_objects(student_records)
        db.commit()

        return {"message": f"{len(students_to_create)} students created successfully"}

    else:
        effective_role = "student" if current_user.role == "teacher" else data.role
        if effective_role != "student" and not data.email:
            raise HTTPException(status_code=400, detail="Email is required for teacher/admin")
        if data.email:
            email_v = db.query(User).filter(User.email == data.email).first()
            if email_v:
                raise HTTPException(status_code=400, detail="Email already exists")
        hashed_password = hash_password(data.password)
        new_user = User(
            username=data.username,
            email=data.email if effective_role != "student" else f"{data.username}@student.local",
            password=hashed_password,
            role=effective_role,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        teacher_id = current_user.id if current_user.role == "teacher" else data.teacher_id
        if effective_role == "student":
            if current_user.role == "admin" and not teacher_id:
                raise HTTPException(status_code=400, detail="Provide teacher_id")
            if not can_create_student(teacher_id, db):
                raise HTTPException(status_code=400, detail="Teacher cannot create more than 30 students")
            new_student = Student(
                user_id=new_user.id,
                name=data.username,
                grade=data.grade,
                created_by=teacher_id
            )
            db.add(new_student)
            db.commit()
            db.refresh(new_student)

        return {"message": f"User Created successfully role={effective_role}"}

@router.post("/create-super-admin")
def create_super_admin(db:Session=Depends(get_db)):
    db_admin=User(username="Anmol",email="anmol@gmail.com",password=hash_password("1234"),role="admin")
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return {"message":"Super Admin created!!"}

@router.post("/create-admin")
def create_admin(data:schemas.CreateUser,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    if current_user.role!="admin":
        raise HTTPException(status_code=401,detail="Unauthorized")
    if data.role!='admin':
        raise HTTPException(status_code=400,detail="Only admin creation allowed")
    db_admin=User(username=data.username,email=data.email,password=hash_password(data.password),role=data.role)
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return {"message":"Admin created!!!"}


@router.post("/login-admin")
def login_admin(data:schemas.AdminLogin,db:Session=Depends(get_db)):
    db_admin=db.query(User).filter(User.email==data.email).first()
    if not db_admin:
        raise HTTPException(status_code=400,detail="User not found")
    if not verify_password(data.password,db_admin.password):
        raise HTTPException(status_code=400,detail="Incorrect password")
    if data.role!="admin":
        raise HTTPException(status_code=401, detail="Only admin login")
    if db_admin.username!=data.name:
        raise HTTPException(status_code=400,detail="Incorrect Username")
    
    access_token=create_access_token(data={"sub":db_admin.email})
    return {"access_token":access_token,"token_type":"bearer"}

@router.post("/login")
def login_admin(data:schemas.AdminLogin,db:Session=Depends(get_db)):
    db_admin=db.query(User).filter(User.email==data.email).first()
    if not db_admin:
        raise HTTPException(status_code=400,detail="User not found")
    if not verify_password(data.password,db_admin.password):
        raise HTTPException(status_code=400,detail="Incorrect password")
    if data.role=="admin" or data.role=="student":
        raise HTTPException(status_code=401, detail="Admin and Student login not allowed")
    if db_admin.username!=data.name:
        raise HTTPException(status_code=400,detail="Incorrect Username")
    if db_admin.role!=data.role:
        raise HTTPException(status_code=401,detail="Access Denied")
    
    access_token=create_access_token(data={"sub":db_admin.email})
    return {"access_token":access_token,"token_type":"bearer"}


@router.get("/get-students", response_model=schemas.CustomRes)
async def get_all_students(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == "admin":
        db_users = db.query(Student).all()
        lst = [
                {"name": user.name,"grade":user.grade,"user_id":user.user_id}
                for user in db_users
            ]
        return {"data": lst}
    if current_user.role=="teacher":
        db_students=db.query(Student).filter(Student.created_by==current_user.id).all()
        lst = [
            {"name":student.name,"grade":student.grade,"user_id":student.user_id}
            for student in db_students
        ]
        return {"data":lst}
    if current_user.role=="student":
        raise HTTPException(status_code=401,detail="Student cannot access")
     
@router.delete("/delete-student/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access Denied")

    db_student = db.query(Student).filter(Student.id == student_id).first()

    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")

    db_user = db.query(User).filter(User.id == db_student.user_id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="user not found")

    db.delete(db_student)
    db.delete(db_user)
    db.commit()

    return {"message": "Student deleted successfully"}

@router.put("/update-student/{student_id}", response_model=schemas.StudentRes)
def update_student(
    student_id: int,
    data: schemas.StudentRes,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_student = db.query(Student).filter(Student.id == student_id).first()

    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")

    if db_student.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot modify other teacher's student")

    db_student.name = data.name
    db_student.grade = data.grade

    db.commit()
    db.refresh(db_student)

    return {"name": db_student.name, "grade": db_student.grade}

@router.get("/get/{admin}/{teacher_id}")
async def uni_get(
    admin: bool | None = None,
    teacher: bool | None = None,
    teacher_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    if admin:
        admins = db.query(User).filter(User.role == "admin").all()
        return [
            {"id": user.id, "username": user.username, "email": user.email}
            for user in admins
        ]

    if teacher:
        teachers = db.query(User).filter(User.role == "teacher").all()
        return [
            {"id": user.id, "username": user.username, "email": user.email}
            for user in teachers
        ]

    if teacher_id:
        teacher_obj = db.query(User).filter(
            User.id == teacher_id,
            User.role == "teacher"
        ).first()

        if not teacher_obj:
            raise HTTPException(status_code=404, detail="Teacher not found")

        return {
            "id": teacher_obj.id,
            "username": teacher_obj.username,
            "email": teacher_obj.email,
        }

    raise HTTPException(status_code=400, detail="Provide valid query parameter")