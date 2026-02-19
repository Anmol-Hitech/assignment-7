from database import Base,get_db
from models import User,Student
from fastapi import APIRouter,Depends,HTTPException
from auth import get_current_user,verify_password,hash_password,create_access_token
from sqlalchemy.orm import Session
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
        new_student = Student(
            name=data.username,
            grade=data.grade,
            created_by=current_user.id,
        )
        db.add(new_student)
        db.commit()
        db.refresh(new_student)

    return {"message": f"User Created successfully role={data.role}"}


@router.post("/create-admin")
def create_admin(db:Session=Depends(get_db)):
    db_admin=User(username="Anmol",email="anmol@gmail.com",password=hash_password("1234"),role="admin")
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return {"message":"Admin created!!"}

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

