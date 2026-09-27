from datetime import date
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Attendance, AttendanceStatus, Olympiad, Student, User, Role


def lead_olympiad(db: Session, user: User) -> Olympiad | None:
    return db.scalar(select(Olympiad).where(Olympiad.lead_user_id == user.id))


def can_access_olympiad(db: Session, user: User, olympiad_id: int) -> bool:
    return user.role == Role.GLOBAL_ADMIN or db.scalar(select(Olympiad.id).where(Olympiad.id == olympiad_id, Olympiad.lead_user_id == user.id)) is not None


def ensure_olympiad_access(db: Session, user: User, olympiad_id: int):
    from fastapi import HTTPException
    if not can_access_olympiad(db, user, olympiad_id):
        raise HTTPException(403, "You do not have access to this olympiad")


def student_stats(db: Session, student_id: int, start: date | None = None, end: date | None = None):
    q = select(Attendance.status, func.count(Attendance.id)).where(Attendance.student_id == student_id)
    if start:
        q = q.where(Attendance.date >= start)
    if end:
        q = q.where(Attendance.date <= end)
    rows = db.execute(q.group_by(Attendance.status)).all()
    counts = {status.value: count for status, count in rows}
    present, absent = counts.get("PRESENT", 0), counts.get("ABSENT", 0)
    total = present + absent
    return {"student_id": student_id, "sessions": total, "present": present, "absent": absent, "percentage": round(present * 100 / total, 1) if total else 0}


def olympiad_stats(db: Session, olympiad_id: int, start: date | None = None, end: date | None = None):
    students = db.scalars(select(Student).where(Student.olympiad_id == olympiad_id, Student.active.is_(True))).all()
    ids = [s.id for s in students]
    query = select(Attendance.student_id, Attendance.status, func.count(Attendance.id)).where(Attendance.student_id.in_(ids)) if ids else None
    if query is not None:
        if start: query = query.where(Attendance.date >= start)
        if end: query = query.where(Attendance.date <= end)
        rows = db.execute(query.group_by(Attendance.student_id, Attendance.status)).all()
    else: rows = []
    per = {sid: {"PRESENT": 0, "ABSENT": 0} for sid in ids}
    for sid, status, count in rows: per[sid][status.value] = count
    total_present = sum(c["PRESENT"] for c in per.values())
    total_sessions = sum(c["PRESENT"] + c["ABSENT"] for c in per.values())
    ranked = [{"student_id": s.id, "full_name": s.full_name, "present": per[s.id]["PRESENT"], "absent": per[s.id]["ABSENT"], "percentage": round(100*per[s.id]["PRESENT"] / max(1, per[s.id]["PRESENT"]+per[s.id]["ABSENT"]), 1)} for s in students]
    return {"olympiad_id": olympiad_id, "total_students": len(students), "sessions_recorded": max((v["PRESENT"]+v["ABSENT"] for v in per.values()), default=0), "attendance_records": total_sessions, "average_attendance_percentage": round(total_present * 100 / total_sessions, 1) if total_sessions else 0, "students": ranked, "top_attenders": sorted(ranked, key=lambda x: (-x["percentage"], -x["present"]))[:5], "most_absences": sorted(ranked, key=lambda x: (-x["absent"], x["full_name"]))[:5]}
