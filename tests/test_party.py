"""PARTY planner tests: valid, invalid guests/budget, AI failure/fallback."""
from tests.conftest import VALID_PARTY


class TestPartyPlanner:
    def test_valid_request(self, client, user_a):
        r = client.post("/generate-party", json=VALID_PARTY)
        assert r.status_code == 200
        body = r.json()
        assert body["planner_type"] == "party"
        assert body["source"] == "fallback"  # no API key in tests
        result = body["result"]
        assert result["budget"] == 30000
        assert result["recommendations"]
        total = sum(x["total_price"] for x in result["recommendations"])
        assert total <= result["budget"] * 1.01

    def test_all_event_types_accepted(self, client, user_a):
        for event in ("birthday", "wedding", "corporate", "other"):
            payload = {**VALID_PARTY, "event_type": event}
            r = client.post("/generate-party", json=payload)
            assert r.status_code == 200, event

    def test_wedding_includes_accommodation(self, client, user_a):
        payload = {**VALID_PARTY, "event_type": "wedding", "accommodation_required": True}
        r = client.post("/generate-party", json=payload)
        assert r.status_code == 200
        cats = {x["category"] for x in r.json()["result"]["recommendations"]}
        assert "Accommodation" in cats or "Venue" in cats

    def test_invalid_guest_count_zero(self, client, user_a):
        payload = {**VALID_PARTY, "guest_count": 0}
        r = client.post("/generate-party", json=payload)
        assert r.status_code == 422
        assert "guest" in r.json()["detail"].lower()

    def test_invalid_guest_count_negative(self, client, user_a):
        payload = {**VALID_PARTY, "guest_count": -5}
        r = client.post("/generate-party", json=payload)
        assert r.status_code == 422

    def test_invalid_guest_count_huge(self, client, user_a):
        payload = {**VALID_PARTY, "guest_count": 999999}
        r = client.post("/generate-party", json=payload)
        assert r.status_code == 422

    def test_invalid_budget(self, client, user_a):
        payload = {**VALID_PARTY, "total_budget": -1}
        r = client.post("/generate-party", json=payload)
        assert r.status_code == 422

    def test_invalid_event_type_rejected(self, client, user_a):
        payload = {**VALID_PARTY, "event_type": "space-launch"}
        r = client.post("/generate-party", json=payload)
        assert r.status_code == 422

    def test_no_services_selected(self, client, user_a):
        payload = {
            "total_budget": 30000, "guest_count": 20, "event_type": "birthday",
            "venue_required": False, "food_catering": False, "decoration": False,
        }
        r = client.post("/generate-party", json=payload)
        assert r.status_code == 422


class TestPartyFallback:
    def test_gemini_failure_yields_fallback(self, client, user_a, monkeypatch):
        from app.services import recommendation_service
        from app.services.gemini_service import GeminiError

        monkeypatch.setattr(
            recommendation_service.gemini_service, "generate_plan",
            lambda prompt, image=None: (_ for _ in ()).throw(GeminiError("outage")),
        )
        r = client.post("/generate-party", json=VALID_PARTY)
        assert r.status_code == 200
        assert r.json()["source"] == "fallback"
        assert r.json()["result"]["recommendations"]
