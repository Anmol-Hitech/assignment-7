from sqlalchemy import Column,Integer,String,Boolean,DateTime,Enum,ForeignKey
from database import Base
from sqlalchemy.orm import Mapped,mapped_column,foreign,relationship
from sqlalchemy.sql import func
import enum

class RoleEnum(str,enum.Enum):
    ADMIN="admin"
    TEACHER="teacher"
    STUDENT="student"

class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(primary_key=True,nullable=False,index=True)
    username:Mapped[str]=mapped_column(nullable=False)
    email:Mapped[str]=mapped_column(nullable=False,unique=True)
    password:Mapped[str]=mapped_column(nullable=False)
    role:Mapped[RoleEnum]=mapped_column(
        Enum(RoleEnum),nullable=False
    )
    students:Mapped[Student]=relationship("Student",back_populates="users")
class Student(Base):
    __tablename__="students"
    id:Mapped[int]=mapped_column(primary_key=True,nullable=False,index=True)
    name:Mapped[str]=mapped_column(nullable=False)
    grade:Mapped[str]=mapped_column(nullable=False,default=None)
    created_by: Mapped["User"] = mapped_column(ForeignKey('users.id',ondelete="CASCADE"))
    users:Mapped[User]=relationship("User",back_populates="students")
