from types import SimpleNamespace

import pytest

from backend import app as app_module


class FakeCursor:
    def __init__(self):
        self.lastrowid = 101
        self.rowcount = 1

    def execute(self, query, params=()):
        self.query = query
        self.params = params

    def fetchone(self):
        return {"result": 1}

    def fetchall(self):
        return []


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self

    def __enter__(self):
        return self.cursor_obj

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=()):
        return self.cursor_obj.execute(query, params)

    def fetchone(self):
        return self.cursor_obj.fetchone()

    def fetchall(self):
        return self.cursor_obj.fetchall()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


@pytest.fixture()
def client():
    app_module.app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
    )
    with app_module.app.test_client() as client:
        yield client


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json()["status"] == "running"


def test_health(client, monkeypatch):
    monkeypatch.setattr(app_module, "get_connection", FakeConnection)
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "healthy"
    assert body["database"] == "connected"


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "student",
            "email": "student@example.com",
            "password": "123",
        },
    )

    assert response.status_code == 400
    assert "8 characters" in response.get_json()["error"]


def test_protected_endpoint_requires_login(client):
    response = client.get("/api/exams")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_admin_endpoint_requires_login(client):
    response = client.post(
        "/api/exams",
        json={
            "title": "Python Basics",
            "description": "Core Python",
            "duration_minutes": 30,
        },
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_exam_payload_validation():
    payload, error = app_module.validate_exam_payload(
        {
            "title": "DBMS",
            "description": "Database basics",
            "duration_minutes": 30,
        }
    )

    assert error is None
    assert payload["duration_minutes"] == 30


def test_question_payload_validation():
    payload, error = app_module.validate_question_payload(
        {
            "question_text": "Which keyword defines a function in Python?",
            "option_a": "func",
            "option_b": "def",
            "option_c": "function",
            "option_d": "define",
            "correct_option": "b",
            "marks": 2,
        }
    )

    assert error is None
    assert payload["correct_option"] == "b"
    assert payload["marks"] == 2
