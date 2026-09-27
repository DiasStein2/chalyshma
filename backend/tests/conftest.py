import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models import Olympiad, Role, User
from app.security import hash_password


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    db = TestingSession()
    admin = User(username="admin", password_hash=hash_password("admin123"), full_name="Admin User", role=Role.GLOBAL_ADMIN)
    lead1 = User(username="lead1", password_hash=hash_password("leadpass1"), full_name="Lead One", role=Role.OLYMPIAD_LEAD)
    lead2 = User(username="lead2", password_hash=hash_password("leadpass2"), full_name="Lead Two", role=Role.OLYMPIAD_LEAD)
    db.add_all([admin, lead1, lead2]); db.flush()
    p = Olympiad(name="Physics", lead_user_id=lead1.id)
    c = Olympiad(name="Chemistry", lead_user_id=lead2.id)
    db.add_all([p, c]); db.commit(); db.close()
    def override_db():
        session = TestingSession()
        try: yield session
        finally: session.close()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def tokens(client):
    def token(username, password):
        response = client.post("/auth/login", json={"username": username, "password": password})
        assert response.status_code == 200
        return response.json()["access_token"]
    return {"admin": token("admin", "admin123"), "lead1": token("lead1", "leadpass1"), "lead2": token("lead2", "leadpass2")}
