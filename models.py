from sqlalchemy import Integer, String, Enum, ForeignKey
from database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum


class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), nullable=False)

    created_students: Mapped[list["Student"]] = relationship(
        "Student",
        foreign_keys="Student.created_by",
        back_populates="creator",
        cascade="all, delete"
    )

    student_profile: Mapped["Student"] = relationship(
        "Student",
        foreign_keys="Student.user_id",
        back_populates="user_account",
        uselist=False,
        cascade="all, delete"
    )


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    grade: Mapped[str] = mapped_column(nullable=False)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    user_account: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="student_profile"
    )

    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_students"
    )