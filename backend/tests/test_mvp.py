def test_login_and_me(client, tokens):
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['admin']}"})
    assert response.status_code == 200
    assert response.json()["role"] == "GLOBAL_ADMIN"
    assert client.post("/auth/login", json={"username": "admin", "password": "wrong-pass"}).status_code == 401


def test_role_authorization_and_scoped_students(client, tokens):
    auth = {"Authorization": f"Bearer {tokens['lead1']}"}
    assert client.get("/users", headers=auth).status_code == 403
    assert [o["name"] for o in client.get("/olympiads", headers=auth).json()] == ["Physics"]
    chem = client.post("/students", headers=auth, json={"full_name":"Nope Student", "class_name":"10A", "olympiad_id":2})
    assert chem.status_code == 403


def test_olympiad_and_student_crud(client, tokens):
    admin = {"Authorization": f"Bearer {tokens['admin']}"}
    lead = {"Authorization": f"Bearer {tokens['lead1']}"}
    created = client.post("/olympiads", headers=admin, json={"name":"Informatics", "lead_user_id":2})
    assert created.status_code == 201
    assert created.json()["lead"]["username"] == "lead1"
    kid = client.post("/students", headers=lead, json={"full_name":"Aida Example", "class_name":"11A", "olympiad_id":1})
    assert kid.status_code == 201
    assert client.get("/students", headers=lead).json()[0]["full_name"] == "Aida Example"


def test_attendance_upsert_duplicate_and_stats(client, tokens):
    admin = {"Authorization": f"Bearer {tokens['admin']}"}
    lead = {"Authorization": f"Bearer {tokens['lead1']}"}
    student = client.post("/students", headers=lead, json={"full_name":"Aida Example", "class_name":"11A", "olympiad_id":1}).json()
    body = {"date":"2026-09-24", "entries":[{"student_id":student["id"], "status":"PRESENT"}]}
    assert client.post("/attendance", headers=lead, json=body).status_code == 200
    body["entries"][0]["status"] = "ABSENT"
    assert client.post("/attendance", headers=lead, json=body).status_code == 200
    history = client.get(f"/students/{student['id']}/attendance", headers=lead).json()
    assert len(history) == 1 and history[0]["status"] == "ABSENT"
    stats = client.get("/statistics/olympiads/1", headers=lead).json()
    assert stats["most_absences"][0]["absent"] == 1
    dup = {"date":"2026-09-25", "entries":[{"student_id":student["id"],"status":"PRESENT"},{"student_id":student["id"],"status":"ABSENT"}]}
    assert client.post("/attendance", headers=lead, json=dup).status_code == 422


def test_calendar_permissions(client, tokens):
    admin = {"Authorization": f"Bearer {tokens['admin']}"}
    lead = {"Authorization": f"Bearer {tokens['lead1']}"}
    assert client.post("/calendar/events", headers=lead, json={"date":"2026-10-12","title":"Test event"}).status_code == 403
    created = client.post("/calendar/events", headers=admin, json={"date":"2026-10-12","title":"Test event"})
    assert created.status_code == 201
    assert len(client.get("/calendar/events", headers=lead).json()) == 1
