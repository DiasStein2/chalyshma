from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import AttendanceStatus, Role


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=120)
    role: Role = Role.OLYMPIAD_LEAD
    active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    password: str | None = Field(default=None, min_length=8)
    role: Role | None = None
    active: bool | None = None


class UserOut(ORMModel):
    id: int
    username: str
    full_name: str
    role: Role
    active: bool
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class OlympiadIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    lead_user_id: int | None = None


class OlympiadOut(ORMModel):
    id: int
    name: str
    description: str | None
    lead_user_id: int | None
    lead: UserOut | None = None


class StudentIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    class_name: str = Field(min_length=1, max_length=30)
    olympiad_id: int
    active: bool = True


class StudentOut(ORMModel):
    id: int
    full_name: str
    class_name: str
    olympiad_id: int
    active: bool
    created_at: datetime


class AttendanceEntry(BaseModel):
    student_id: int
    status: AttendanceStatus


class AttendanceBatch(BaseModel):
    date: date
    entries: list[AttendanceEntry]


class AttendanceUpdate(BaseModel):
    status: AttendanceStatus


class AttendanceOut(ORMModel):
    id: int
    student_id: int
    date: date
    status: AttendanceStatus
    marked_by_user_id: int


class EventIn(BaseModel):
    date: date
    end_date: date | None = None
    title: str = Field(min_length=1, max_length=180)

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_date is not None and self.end_date < self.date:
            raise ValueError("Event end date must be on or after its start date")
        return self


class EventOut(ORMModel):
    id: int
    date: date
    end_date: date | None
    title: str
    created_by_user_id: int
