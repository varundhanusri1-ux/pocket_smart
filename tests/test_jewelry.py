"""JEWELRY planner tests: text-only, image, invalid/oversized image, fallback."""
from tests.conftest import PNG_1PX


def post_jewelry(client, *, image=None, budget=5000, occasion="Wedding reception", **extra):
    data = {"total_budget": str(budget), "occasion": occasion, **{
        k: str(v) for k, v in extra.items() if v is not None
    }}
    files = {"outfit_image": image} if image else None
    return client.post("/generate-jewelry", data=data, files=files)


class TestJewelryPlanner:
    def test_text_only_request(self, client, user_a):
        r = post_jewelry(client, occasion="Engagement", style_preference="Traditional")
        assert r.status_code == 200
        body = r.json()
        assert body["planner_type"] == "jewelry"
        assert body["source"] == "fallback"  # tests run without an API key
        result = body["result"]
        assert result["recommendations"]
        assert result["budget"] == 5000
        summary = result["summary"]
        assert "input_summary" in body

    def test_image_request(self, client, user_a):
        r = post_jewelry(
            client,
            image=("outfit.png", PNG_1PX, "image/png"),
            outfit_description="Green silk saree with gold border",
        )
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "fallback"
        assert body["input_summary"]["image_analyzed"] in ("Yes", "No")

    def test_invalid_image_content(self, client, user_a):
        r = post_jewelry(client, image=("fake.png", b"definitely not a png", "image/png"))
        assert r.status_code == 400
        assert "valid image" in r.json()["detail"]

    def test_oversized_image_rejected(self, client, user_a, monkeypatch):
        from app.core.config import settings

        # Patch the source field (the byte limit is a derived read-only property).
        monkeypatch.setattr(settings, "MAX_IMAGE_SIZE_MB", 0, raising=False)
        r = post_jewelry(client, image=("big.png", PNG_1PX, "image/png"))
        monkeypatch.undo()
        assert r.status_code == 400
        assert "too large" in r.json()["detail"].lower()

    def test_unsupported_image_type_rejected(self, client, user_a):
        # GIF magic bytes with a png content-type -> sniffing fails
        gif = b"GIF89a" + b"\x00" * 50
        r = post_jewelry(client, image=("pic.gif", gif, "image/gif"))
        assert r.status_code == 400

    def test_missing_occasion_rejected(self, client, user_a):
        r = client.post("/generate-jewelry", data={"total_budget": "5000"})
        assert r.status_code == 422

    def test_invalid_budget_rejected(self, client, user_a):
        r = post_jewelry(client, budget=0)
        assert r.status_code == 422

    def test_requires_auth(self, client):
        r = client.post("/generate-jewelry", data={"total_budget": "5000", "occasion": "Wedding"})
        assert r.status_code == 401


class TestJewelryFallback:
    def test_gemini_failure_with_image_yields_fallback(self, client, user_a, monkeypatch):
        from app.services import recommendation_service
        from app.services.gemini_service import GeminiError

        def boom(prompt, image=None):
            raise GeminiError("simulated multimodal outage")

        monkeypatch.setattr(recommendation_service.gemini_service, "generate_plan", boom)
        r = post_jewelry(client, image=("outfit.png", PNG_1PX, "image/png"))
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "fallback"
        assert body["result"]["recommendations"]
