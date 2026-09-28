"""AUTH tests: register, duplicate, login, wrong password, protected routes, logout."""
from tests.conftest import VALID_HOME


class TestRegister:
    def test_register_success(self, client):
        r = client.post("/register", json={
            "email": "new@example.com", "full_name": "New User", "password": "password123",
        })
        assert r.status_code == 201
        body = r.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["user"]["email"] == "new@example.com"
        assert "password" not in body["user"]
        # Auth cookie set for browser flows
        assert "ps_access_token" in r.cookies

    def test_duplicate_email_rejected(self, client, user_a):
        r = client.post("/register", json={
            "email": "alice@example.com", "full_name": "Someone Else", "password": "password123",
        })
        assert r.status_code == 409
        assert "already exists" in r.json()["detail"]

    def test_weak_password_rejected(self, client):
        r = client.post("/register", json={
            "email": "weak@example.com", "full_name": "Weak Pass", "password": "short",
        })
        assert r.status_code == 422

    def test_password_without_number_rejected(self, client):
        r = client.post("/register", json={
            "email": "nonum@example.com", "full_name": "No Number", "password": "onlyletters",
        })
        assert r.status_code == 422

    def test_invalid_email_rejected(self, client):
        r = client.post("/register", json={
            "email": "not-an-email", "full_name": "Bad Email", "password": "password123",
        })
        assert r.status_code == 422

    def test_password_never_stored_plain(self, client):
        from app.core.database import SessionLocal
        from app.models import User

        client.post("/register", json={
            "email": "hash@example.com", "full_name": "Hash Check", "password": "password123",
        })
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(email="hash@example.com").one()
            assert user.hashed_password != "password123"
            assert user.hashed_password.startswith("pbkdf2_sha256$")
        finally:
            db.close()


class TestLogin:
    def test_login_success(self, client, user_a):
        r = client.post("/login", json={
            "email": "alice@example.com", "password": "password123",
        })
        assert r.status_code == 200
        assert r.json()["user"]["full_name"] == "Alice Alpha"

    def test_wrong_password(self, client, user_a):
        r = client.post("/login", json={
            "email": "alice@example.com", "password": "totally-wrong1",
        })
        assert r.status_code == 401
        # Generic message — never reveals whether the email exists
        assert "Incorrect email or password" in r.json()["detail"]

    def test_unknown_email(self, client, user_a):
        r = client.post("/login", json={
            "email": "ghost@example.com", "password": "password123",
        })
        assert r.status_code == 401

    def test_oauth2_token_endpoint(self, client, user_a):
        r = client.post("/token", data={"username": "alice@example.com", "password": "password123"})
        assert r.status_code == 200
        token = r.json()["access_token"]
        # Token actually authenticates
        r2 = client.get("/session-info", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200

    def test_expired_token_rejected(self, client, user_a):
        import jwt as pyjwt

        from app.core.config import settings
        from app.core.security import create_access_token

        _, expires = create_access_token(user_a["id"])
        payload = {**pyjwt.decode(
            create_access_token(user_a["id"])[0],
            settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
        )}
        payload["exp"] = payload["iat"] - 10  # already expired
        expired = pyjwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        r = client.get("/session-info", headers={"Authorization": f"Bearer {expired}"})
        assert r.status_code == 401
        assert "expired" in r.json()["detail"].lower()

    def test_garbage_token_rejected(self, client):
        r = client.get("/session-info", headers={"Authorization": "Bearer not-a-jwt"})
        assert r.status_code == 401


class TestProtectedRoutes:
    def test_planner_requires_auth(self, client):
        r = client.post("/generate-home", json=VALID_HOME)
        assert r.status_code == 401

    def test_session_info_requires_auth(self, client):
        assert client.get("/session-info").status_code == 401

    def test_session_data_requires_auth(self, client):
        assert client.get("/session-data").status_code == 401

    def test_dashboard_page_redirects(self, client):
        r = client.get("/dashboard", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/login"

    def test_history_page_redirects(self, client):
        r = client.get("/history", follow_redirects=False)
        assert r.status_code == 302


class TestLogout:
    def test_logout_clears_session(self, client, user_a):
        assert client.get("/session-info").status_code == 200
        r = client.get("/logout")
        assert r.status_code == 200
        # Cookie cleared -> endpoints now unauthenticated
        assert client.get("/session-info").status_code == 401


class TestSessionEndpoints:
    def test_session_info(self, client, user_a):
        r = client.get("/session-info")
        assert r.status_code == 200
        body = r.json()
        assert body["authenticated"] is True
        assert body["email"] == "alice@example.com"
        assert body["expires_at"]

    def test_session_data(self, client, user_a):
        r = client.get("/session-data")
        assert r.status_code == 200
        body = r.json()
        assert body["user"]["id"] == user_a["id"]
        assert "plan_stats" in body
        assert body["plan_stats"]["total_plans"] >= 0
