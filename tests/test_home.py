"""HOME planner tests: valid, invalid budget, missing fields, AI failure/fallback."""
from tests.conftest import VALID_HOME


class TestHomePlanner:
    def test_valid_request(self, client, user_a):
        r = client.post("/generate-home", json=VALID_HOME)
        assert r.status_code == 200
        body = r.json()
        result = body["result"]
        assert body["planner_type"] == "home"
        # No API key configured in tests -> clearly-labelled fallback
        assert body["source"] == "fallback"
        assert body["ai_generated"] is False
        assert len(result["recommendations"]) >= 3
        assert result["budget"] == 50000
        # Derived figures consistent
        total = sum(x["total_price"] for x in result["recommendations"])
        assert abs(total - result["total_estimated_cost"]) < 1
        assert result["total_estimated_cost"] <= result["budget"] * 1.01
        assert result["allocation"], "allocation must be present"
        assert result["summary"]

    def test_recommendations_well_formed(self, client, user_a):
        r = client.post("/generate-home", json=VALID_HOME)
        for item in r.json()["result"]["recommendations"]:
            assert item["name"] and item["category"] and item["platform"]
            assert item["estimated_price"] > 0
            assert item["quantity"] >= 1
            assert abs(item["total_price"] - item["estimated_price"] * item["quantity"]) < 1
            if item["link"]:
                assert item["link"].startswith("http")

    def test_invalid_budget_negative(self, client, user_a):
        payload = {**VALID_HOME, "total_budget": -100}
        r = client.post("/generate-home", json=payload)
        assert r.status_code == 422
        assert "budget" in r.json()["detail"].lower()

    def test_invalid_budget_zero(self, client, user_a):
        payload = {**VALID_HOME, "total_budget": 0}
        r = client.post("/generate-home", json=payload)
        assert r.status_code == 422

    def test_missing_rooms(self, client, user_a):
        payload = {k: v for k, v in VALID_HOME.items() if k != "rooms"}
        r = client.post("/generate-home", json=payload)
        assert r.status_code == 422

    def test_no_requirements_selected(self, client, user_a):
        payload = {
            "total_budget": 50000,
            "rooms": [{"room_type": "Bedroom", "quantity": 2}],
        }
        r = client.post("/generate-home", json=payload)
        assert r.status_code == 422
        assert "at least one" in r.json()["detail"].lower()

    def test_multi_room_quantities(self, client, user_a):
        payload = {
            **VALID_HOME,
            "rooms": [
                {"room_type": "Bedroom", "quantity": 2},
                {"room_type": "Kitchen", "quantity": 1},
            ],
            "ceiling_fans": 3,
            "dining_table": True,
        }
        r = client.post("/generate-home", json=payload)
        assert r.status_code == 200


class TestHomeFallback:
    def test_gemini_failure_yields_fallback(self, client, user_a, monkeypatch):
        """Simulated Gemini outage -> labelled fallback, never a crash."""
        from app.services import recommendation_service
        from app.services.gemini_service import GeminiError

        def boom(prompt, image=None):
            raise GeminiError("simulated outage")

        monkeypatch.setattr(recommendation_service.gemini_service, "generate_plan", boom)
        r = client.post("/generate-home", json=VALID_HOME)
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "fallback"
        assert body["ai_generated"] is False
        assert body["result"]["summary"]  # honest fallback notice as summary
        # Fallback items are individually tagged
        assert all(x["source"] == "fallback" for x in body["result"]["recommendations"])

    def test_malformed_gemini_output_yields_fallback(self, client, user_a, monkeypatch):
        from app.services import recommendation_service

        def garbage(prompt, image=None):
            return {"summary": "no recommendations key at all", "tips": []}

        monkeypatch.setattr(recommendation_service.gemini_service, "generate_plan", garbage)
        r = client.post("/generate-home", json=VALID_HOME)
        assert r.status_code == 200
        assert r.json()["source"] == "fallback"
