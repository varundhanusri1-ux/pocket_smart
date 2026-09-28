"""HISTORY tests: privacy, per-user isolation, details endpoint."""
import uuid

from tests.conftest import VALID_HOME, VALID_PARTY


def _fresh_user(client) -> dict:
    """Register a brand-new isolated user (owns zero plans) and log in as them."""
    email = f"hist-{uuid.uuid4().hex[:12]}@example.com"
    r = client.post("/register", json={
        "email": email, "full_name": "History Test", "password": "password123",
    })
    assert r.status_code == 201, r.text
    return r.json()["user"]


def _login(client, email: str, password: str = "password123") -> None:
    r = client.post("/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


class TestHistory:
    def test_own_history_accessible(self, client, user_a):
        client.post("/generate-home", json=VALID_HOME)
        client.post("/generate-party", json=VALID_PARTY)
        r = client.get("/history")
        assert r.status_code == 200
        assert "Home interior plan" in r.text
        assert "party plan" in r.text

    def test_details_of_own_plan(self, client, user_a):
        created = client.post("/generate-home", json=VALID_HOME).json()
        r = client.get(f"/recommendations-details?plan_id={created['plan_id']}")
        assert r.status_code == 200
        assert r.json()["plan_id"] == created["plan_id"]
        assert r.json()["planner_type"] == "home"

    def test_cannot_access_another_users_plan(self, client, user_a, user_b):
        """Plans created as one user must be invisible to another user."""
        owner = _fresh_user(client)
        created = client.post("/generate-home", json=VALID_HOME).json()
        other = _fresh_user(client)  # cookie now belongs to `other`
        assert other["id"] != owner["id"]
        r = client.get(f"/recommendations-details?plan_id={created['plan_id']}")
        assert r.status_code == 404

    def test_history_page_shows_only_own_plans(self, client, user_a, user_b):
        owner = _fresh_user(client)
        client.post("/generate-home", json={
            **VALID_HOME,
            "rooms": [{"room_type": "Balcony", "quantity": 1}],
        })
        _fresh_user(client)  # switch to a user with zero plans
        r = client.get("/history")
        assert r.status_code == 200
        assert "Home interior plan" not in r.text

    def test_latest_plan_per_planner(self, client, user_a):
        client.post("/generate-party", json=VALID_PARTY)
        client.post("/generate-home", json=VALID_HOME)
        r = client.get("/recommendations-details?planner_type=party")
        assert r.status_code == 200
        assert r.json()["planner_type"] == "party"

    def test_details_404_when_no_plans(self, client):
        _fresh_user(client)  # isolated user with zero plans
        r = client.get("/recommendations-details")
        assert r.status_code == 404
        assert "haven't generated" in r.json()["detail"].lower()

    def test_input_summary_stored(self, client, user_a):
        created = client.post("/generate-home", json={
            **VALID_HOME,
            "rooms": [{"room_type": "Bedroom", "quantity": 2}],
        }).json()
        assert created["input_summary"]["rooms"] == "Bedroom x2"

    def test_timestamp_stored(self, client, user_a):
        created = client.post("/generate-home", json=VALID_HOME).json()
        assert created["created_at"]

    def test_plan_stats_in_session_data(self, client):
        _fresh_user(client)  # isolated user with zero plans
        before = client.get("/session-data").json()["plan_stats"]["total_plans"]
        client.post("/generate-home", json=VALID_HOME)
        stats = client.get("/session-data").json()["plan_stats"]
        assert stats["total_plans"] == before + 1
        assert stats["by_type"]["home"]["count"] >= 1
