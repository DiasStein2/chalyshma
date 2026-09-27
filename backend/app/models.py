from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def now_utc():
    return datetime.now(timezone.utc)


class Role(str, Enum):
    GLOBAL_ADMIN = "GLOBAL_ADMIN"
    OLYMPIAD_LEAD = "OLYMPIAD_LEAD"


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(SAEnum(Role, native_enum=False), default=Role.OLYMPIAD_LEAD)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    olympiads: Mapped[list["Olympiad"]] = relationship(back_populates="lead")


class Olympiad(Base):
    __tablename__ = "olympiads"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    lead: Mapped[User | None] = relationship(back_populates="olympiads")
    students: Mapped[list["Student"]] = relationship(back_populates="olympiad")


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (Index("ix_students_olympiad_active", "olympiad_id", "active"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), index=True)
    class_name: Mapped[str] = mapped_column(String(30))
    olympiad_id: Mapped[int] = mapped_column(ForeignKey("olympiads.id", ondelete="RESTRICT"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    olympiad: Mapped[Olympiad] = relationship(back_populates="students")
    attendance: Mapped[list["Attendance"]] = relationship(back_populates="student")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("student_id", "date", name="uq_attendance_student_date"), Index("ix_attendance_date", "date"), Index("ix_attendance_student_date", "student_id", "date"))
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), index=True)
    # Keep SQL date columns explicitly typed. Avoid annotation inference here:
    # `date` is also the mapped attribute name and older SQLAlchemy releases
    # can resolve it as a SQL expression while scanning this declarative class.
    date = mapped_column(Date, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(SAEnum(AttendanceStatus, native_enum=False))
    marked_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    student: Mapped[Student] = relationship(back_populates="attendance")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (Index("ix_calendar_events_date", "date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    date = mapped_column(Date, index=True)
    end_date = mapped_column(Date, nullable=True)
    title: Mapped[str] = mapped_column(String(180))
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
