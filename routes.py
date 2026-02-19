from database import Base,get_db
from models import User,Student
from fastapi import APIRouter,Depends,HTTPException
from auth import get_current_user,verify_password,hash_password,create_access_token
from sqlalchemy.orm import Session
from helpers import can_create_student
import schemas
router=APIRouter()


@router.post("/create-user")
def create_user(data: schemas.CreateUser,db: Session = Depends(get_db),current_user: User = Depends(get_current_user),):
    if current_user.role == "teacher" and data.role == "teacher":
        raise HTTPException(status_code=401, detail="Teacher Cannot Create Teacher")

    if current_user.role == "student":
        raise HTTPException(status_code=401, detail="Student Access denied")

    email_v = db.query(User).filter(User.email == data.email).first()
    if email_v:
        raise HTTPException(status_code=400, detail="Email already exist")
    
        
    hashed_password = hash_password(data.password)

    new_user = User(
        username=data.username,
        email=data.email,
        password=hashed_password,
        role=data.role,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if data.role == "student":
        if current_user.role=="admin":
            if not data.teacher_id:
                raise HTTPException(status_code=400,detail="Provide teacher id")
            if not can_create_student(data.teacher_id,db):
                raise HTTPException(status_code=400,detail="Teacher cannot create more than 30 students")
        if current_user.role=="teacher":
            if data.teacher_id:
                raise HTTPException(status_code=400,detail="Bro no teacher id when you are teacher")
            if not can_create_student(current_user.id,db):
                raise HTTPException(status_code=400,detail="Teacher cannot create more than 30 students")
        
        
        new_student = Student(
            name=data.username,
            email=data.email,
            grade=data.grade,
            created_by=current_user.id,
        )
        db.add(new_student)
        db.commit()
        db.refresh(new_student)

    return {"message": f"User Created successfully role={data.role}"}


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
    if data.role=="admin":
        raise HTTPException(status_code=401, detail="Admin login not allowed")
    if db_admin.username!=data.name:
        raise HTTPException(status_code=400,detail="Incorrect Username")
    if db_admin.role!=data.role:
        raise HTTPException(status_code=401,detail="Access Denied")
    
    access_token=create_access_token(data={"sub":db_admin.email})
    return {"access_token":access_token,"token_type":"bearer"}


@router.get("/get-students", response_model=schemas.CustomRes)
def get_all_students(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Access Denied")

    db_users = db.query(Student).all()

    lst = [
        {"name": user.name,"grade":user.grade}
        for user in db_users
    ]

    return {"data": lst}

@router.get("/my-students",response_model=schemas.CustomRes)
def get_my_students(db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    if current_user.role!="teacher":
        raise HTTPException(status_code=401, detail="Access Denied")
    db_students=db.query(Student).filter(Student.created_by==current_user.id).all()
    lst = [
        {"name":student.name,"grade":student.grade}
        for student in db_students
    ]
    return {"data":lst}

@router.delete("/delete-student")
def delete_student(sid:int,uid:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    if current_user.role!="admin":
        raise HTTPException(status_code=401,detail="Access Denied")
    db_student=db.query(Student).filter(Student.id==sid).first()
    db_user=db.query(User).filter(User.id==uid).first()
    if db_user.email!=db_student.email:
        raise HTTPException(status_code=400,detail="NO no provide perfect user id and student id")
    db.delete(db_student)
    db.delete(db_user)
    db.commit()
    return {"message":"Student deleted successfully"}

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
