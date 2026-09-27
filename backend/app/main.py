from datetime import date, datetime
from zoneinfo import ZoneInfo
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import Attendance, AttendanceStatus, CalendarEvent, Olympiad, Role, Student, User
from app.schemas import AttendanceBatch, AttendanceOut, AttendanceUpdate, EventIn, EventOut, LoginIn, OlympiadIn, OlympiadOut, StudentIn, StudentOut, TokenOut, UserCreate, UserOut, UserUpdate
from app.security import create_token, hash_password, token_user_id, verify_password
from app.services import ensure_olympiad_access, lead_olympiad, olympiad_stats, student_stats

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
oauth = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def current_user(token: str | None = Depends(oauth), db: Session = Depends(get_db)) -> User:
    uid = token_user_id(token) if token else None
    user = db.get(User, uid) if uid else None
    if not user or not user.active: raise HTTPException(401, "Authentication required")
    return user


def admin(user: User = Depends(current_user)) -> User:
    if user.role != Role.GLOBAL_ADMIN: raise HTTPException(403, "Global admin access required")
    return user


def safe_commit(db: Session):
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A record with these details already exists")


@app.get("/health")
def health(): return {"status": "ok"}


@app.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not user.active or not verify_password(body.password, user.password_hash): raise HTTPException(401, "Invalid username or password")
    return {"access_token": create_token(user.id), "user": user}


@app.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)): return user


@app.get("/users", response_model=list[UserOut])
def users(_: User = Depends(admin), db: Session = Depends(get_db)): return db.scalars(select(User).order_by(User.full_name)).all()


@app.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, _: User = Depends(admin), db: Session = Depends(get_db)):
    user = User(username=body.username, password_hash=hash_password(body.password), full_name=body.full_name, role=body.role, active=body.active)
    db.add(user); safe_commit(db); db.refresh(user); return user


@app.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, _: User = Depends(admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user: raise HTTPException(404, "User not found")
    for key, val in body.model_dump(exclude_unset=True).items(): setattr(user, "password_hash" if key == "password" else key, hash_password(val) if key == "password" else val)
    safe_commit(db); db.refresh(user); return user


@app.delete("/users/{user_id}", status_code=204)
def deactivate_user(user_id: int, actor: User = Depends(admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user: raise HTTPException(404, "User not found")
    if user.id == actor.id: raise HTTPException(409, "You cannot deactivate your own account")
    user.active = False
    safe_commit(db)


@app.get("/olympiads", response_model=list[OlympiadOut])
def olympiads(user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Olympiad).order_by(Olympiad.name)
    if user.role == Role.OLYMPIAD_LEAD: q = q.where(Olympiad.lead_user_id == user.id)
    return db.scalars(q).all()


@app.post("/olympiads", response_model=OlympiadOut, status_code=201)
def create_olympiad(body: OlympiadIn, _: User = Depends(admin), db: Session = Depends(get_db)):
    if body.lead_user_id and (not db.get(User, body.lead_user_id) or db.get(User, body.lead_user_id).role != Role.OLYMPIAD_LEAD): raise HTTPException(422, "Lead must be an Olympiad Lead user")
    item = Olympiad(**body.model_dump()); db.add(item); safe_commit(db); db.refresh(item); return item


@app.get("/olympiads/{olympiad_id}", response_model=OlympiadOut)
def get_olympiad(olympiad_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_olympiad_access(db, user, olympiad_id); item = db.get(Olympiad, olympiad_id)
    if not item: raise HTTPException(404, "Olympiad not found")
    return item


@app.put("/olympiads/{olympiad_id}", response_model=OlympiadOut)
def update_olympiad(olympiad_id: int, body: OlympiadIn, _: User = Depends(admin), db: Session = Depends(get_db)):
    item = db.get(Olympiad, olympiad_id)
    if not item: raise HTTPException(404, "Olympiad not found")
    if body.lead_user_id and (not db.get(User, body.lead_user_id) or db.get(User, body.lead_user_id).role != Role.OLYMPIAD_LEAD): raise HTTPException(422, "Lead must be an Olympiad Lead user")
    for key, val in body.model_dump().items(): setattr(item, key, val)
    safe_commit(db); db.refresh(item); return item


@app.delete("/olympiads/{olympiad_id}", status_code=204)
def delete_olympiad(olympiad_id: int, _: User = Depends(admin), db: Session = Depends(get_db)):
    item = db.get(Olympiad, olympiad_id)
    if not item: raise HTTPException(404, "Olympiad not found")
    if db.scalar(select(func.count(Student.id)).where(Student.olympiad_id == olympiad_id)): raise HTTPException(409, "Move or deactivate students before deleting this olympiad")
    db.delete(item); safe_commit(db)


@app.get("/students", response_model=list[StudentOut])
def students(q: str | None = None, olympiad_id: int | None = None, active: bool | None = True, user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(Student)
    if user.role == Role.OLYMPIAD_LEAD:
        own = lead_olympiad(db, user)
        if not own: return []
        stmt = stmt.where(Student.olympiad_id == own.id)
    if olympiad_id: stmt = stmt.where(Student.olympiad_id == olympiad_id)
    if active is not None: stmt = stmt.where(Student.active == active)
    if q: stmt = stmt.where(Student.full_name.ilike(f"%{q}%"))
    return db.scalars(stmt.order_by(Student.full_name)).all()


@app.post("/students", response_model=StudentOut, status_code=201)
def create_student(body: StudentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_olympiad_access(db, user, body.olympiad_id)
    if not db.get(Olympiad, body.olympiad_id): raise HTTPException(404, "Olympiad not found")
    item = Student(**body.model_dump()); db.add(item); safe_commit(db); db.refresh(item); return item


@app.get("/students/{student_id}", response_model=StudentOut)
def get_student(student_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.get(Student, student_id)
    if not item: raise HTTPException(404, "Student not found")
    ensure_olympiad_access(db, user, item.olympiad_id); return item


@app.put("/students/{student_id}", response_model=StudentOut)
def update_student(student_id: int, body: StudentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.get(Student, student_id)
    if not item: raise HTTPException(404, "Student not found")
    ensure_olympiad_access(db, user, item.olympiad_id); ensure_olympiad_access(db, user, body.olympiad_id)
    for key, val in body.model_dump().items(): setattr(item, key, val)
    safe_commit(db); db.refresh(item); return item


@app.delete("/students/{student_id}", status_code=204)
def deactivate_student(student_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.get(Student, student_id)
    if not item: raise HTTPException(404, "Student not found")
    ensure_olympiad_access(db, user, item.olympiad_id); item.active = False; safe_commit(db)


@app.get("/attendance/date/{attendance_date}")
def attendance_for_date(attendance_date: date, olympiad_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role == Role.OLYMPIAD_LEAD:
        own = lead_olympiad(db, user)
        if not own: return []
        olympiad_id = own.id
    stmt = select(Student).where(Student.active.is_(True))
    if olympiad_id: stmt = stmt.where(Student.olympiad_id == olympiad_id); ensure_olympiad_access(db, user, olympiad_id)
    students = db.scalars(stmt.order_by(Student.full_name)).all()
    result = []
    for student in students:
        record = db.scalar(select(Attendance).where(Attendance.student_id == student.id, Attendance.date == attendance_date))
        result.append({"student": StudentOut.model_validate(student), "attendance": AttendanceOut.model_validate(record) if record else None})
    return result


@app.post("/attendance", response_model=list[AttendanceOut])
def save_attendance(body: AttendanceBatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ids = {e.student_id for e in body.entries}
    if len(ids) != len(body.entries): raise HTTPException(422, "Duplicate student in attendance submission")
    students = {s.id: s for s in db.scalars(select(Student).where(Student.id.in_(ids))).all()} if ids else {}
    if len(students) != len(ids): raise HTTPException(404, "Student not found")
    for student in students.values(): ensure_olympiad_access(db, user, student.olympiad_id)
    output = []
    for entry in body.entries:
        row = db.scalar(select(Attendance).where(Attendance.student_id == entry.student_id, Attendance.date == body.date))
        if row is None:
            row = Attendance(student_id=entry.student_id, date=body.date, status=entry.status, marked_by_user_id=user.id); db.add(row)
        else: row.status = entry.status; row.marked_by_user_id = user.id
        output.append(row)
    safe_commit(db)
    for row in output: db.refresh(row)
    return output


@app.put("/attendance/{attendance_id}", response_model=AttendanceOut)
def update_attendance(attendance_id: int, body: AttendanceUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(Attendance, attendance_id)
    if not row: raise HTTPException(404, "Attendance record not found")
    student = db.get(Student, row.student_id)
    ensure_olympiad_access(db, user, student.olympiad_id)
    row.status = body.status; row.marked_by_user_id = user.id
    safe_commit(db); db.refresh(row); return row


@app.get("/attendance")
def attendance_history(student_id: int | None = None, olympiad_id: int | None = None, start: date | None = None, end: date | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(Attendance).join(Student)
    if student_id: stmt = stmt.where(Attendance.student_id == student_id)
    if olympiad_id: stmt = stmt.where(Student.olympiad_id == olympiad_id)
    if start: stmt = stmt.where(Attendance.date >= start)
    if end: stmt = stmt.where(Attendance.date <= end)
    if user.role == Role.OLYMPIAD_LEAD:
        own = lead_olympiad(db, user)
        if not own: return []
        stmt = stmt.where(Student.olympiad_id == own.id)
    elif olympiad_id: ensure_olympiad_access(db, user, olympiad_id)
    return db.scalars(stmt.order_by(Attendance.date.desc(), Attendance.id)).all()


@app.get("/students/{student_id}/attendance")
def student_attendance(student_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.get(Student, student_id)
    if not item: raise HTTPException(404, "Student not found")
    ensure_olympiad_access(db, user, item.olympiad_id)
    return db.scalars(select(Attendance).where(Attendance.student_id == student_id).order_by(Attendance.date.desc())).all()


@app.get("/statistics/students/{student_id}")
def statistics_student(student_id: int, start: date | None = None, end: date | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if not student: raise HTTPException(404, "Student not found")
    ensure_olympiad_access(db, user, student.olympiad_id); return student_stats(db, student_id, start, end)


@app.get("/statistics/olympiads/{olympiad_id}")
def statistics_olympiad(olympiad_id: int, start: date | None = None, end: date | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_olympiad_access(db, user, olympiad_id)
    if not db.get(Olympiad, olympiad_id): raise HTTPException(404, "Olympiad not found")
    return olympiad_stats(db, olympiad_id, start, end)


@app.get("/statistics/overview")
def statistics_overview(user: User = Depends(current_user), db: Session = Depends(get_db)):
    oids = [o.id for o in db.scalars(select(Olympiad)).all()] if user.role == Role.GLOBAL_ADMIN else [o.id for o in db.scalars(select(Olympiad).where(Olympiad.lead_user_id == user.id)).all()]
    today = datetime.now(ZoneInfo(settings.app_timezone)).date()
    total_students = db.scalar(select(func.count(Student.id)).where(Student.active.is_(True), Student.olympiad_id.in_(oids))) if oids else 0
    todays = db.execute(select(Attendance.status, func.count(Attendance.id)).join(Student).where(Attendance.date == today, Student.olympiad_id.in_(oids)).group_by(Attendance.status)).all() if oids else []
    stats = [olympiad_stats(db, oid) for oid in oids]
    events = db.scalars(select(CalendarEvent).where(func.coalesce(CalendarEvent.end_date, CalendarEvent.date) >= today).order_by(CalendarEvent.date).limit(5)).all()
    return {"directions": len(oids), "total_students": total_students or 0, "today_present": sum(c for s,c in todays if s == AttendanceStatus.PRESENT), "today_absent": sum(c for s,c in todays if s == AttendanceStatus.ABSENT), "olympiads": stats, "upcoming_events": [EventOut.model_validate(e) for e in events]}


@app.get("/calendar/events", response_model=list[EventOut])
def calendar_events(start: date | None = None, end: date | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(CalendarEvent)
    if start: stmt = stmt.where(func.coalesce(CalendarEvent.end_date, CalendarEvent.date) >= start)
    if end: stmt = stmt.where(CalendarEvent.date <= end)
    return db.scalars(stmt.order_by(CalendarEvent.date)).all()


@app.post("/calendar/events", response_model=EventOut, status_code=201)
def create_event(body: EventIn, user: User = Depends(admin), db: Session = Depends(get_db)):
    event = CalendarEvent(**body.model_dump(), created_by_user_id=user.id); db.add(event); safe_commit(db); db.refresh(event); return event


@app.put("/calendar/events/{event_id}", response_model=EventOut)
def update_event(event_id: int, body: EventIn, _: User = Depends(admin), db: Session = Depends(get_db)):
    item = db.get(CalendarEvent, event_id)
    if not item: raise HTTPException(404, "Event not found")
    item.date, item.end_date, item.title = body.date, body.end_date, body.title; safe_commit(db); db.refresh(item); return item


@app.delete("/calendar/events/{event_id}", status_code=204)
def delete_event(event_id: int, _: User = Depends(admin), db: Session = Depends(get_db)):
    item = db.get(CalendarEvent, event_id)
    if not item: raise HTTPException(404, "Event not found")
    db.delete(item); safe_commit(db)
