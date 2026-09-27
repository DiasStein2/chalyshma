from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Olympiad, Role, User
from app.security import hash_password


def seed():
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin"))
        if not admin:
            admin = User(username="admin", password_hash=hash_password(settings.seed_admin_password), full_name="Program Administrator", role=Role.GLOBAL_ADMIN)
            db.add(admin); db.flush()
        leads = {}
        for username, full_name in [
            ("dias", "Dias Sadykov"),
            ("kali", "Kali Omarova"),
            ("arman", "Arman Bek"),
        ]:
            lead = db.scalar(select(User).where(User.username == username))
            if not lead:
                lead = User(
                    username=username,
                    password_hash=hash_password(settings.seed_lead_password),
                    full_name=full_name,
                    role=Role.OLYMPIAD_LEAD,
                )
                db.add(lead)
                db.flush()
            leads[username] = lead

        directions = [
            ("Mathematics", "arman"),
            ("Physics", "dias"),
            ("Chemistry", "kali"),
            ("Biology", None),
            ("English", None),
        ]
        for name, lead_username in directions:
            olympiad = db.scalar(select(Olympiad).where(Olympiad.name == name))
            if not olympiad:
                olympiad = Olympiad(
                    name=name,
                    lead_user_id=leads[lead_username].id if lead_username else None,
                )
                db.add(olympiad)
            elif lead_username and olympiad.lead_user_id is None:
                olympiad.lead_user_id = leads[lead_username].id
        db.commit()
    finally: db.close()


if __name__ == "__main__": seed()
