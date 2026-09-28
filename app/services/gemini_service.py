"""Gemini API client — the ONLY module that talks to Google's Gemini API.

Uses the REST generateContent endpoint over httpx so no heavyweight SDK is
required. Supports text + optional inline image (multimodal, Jewelry Planner).
"""
import base64
import json
import logging
import re

import httpx

from app.core.config import settings

logger = logging.getLogger("pocketsmart.gemini")

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiError(Exception):
    """Raised for any Gemini failure. `user_message` is always safe to show."""

    def __init__(self, user_message: str, log_detail: str | None = None):
        super().__init__(user_message)
        self.user_message = user_message
        self.log_detail = log_detail


class GeminiService:
    def __init__(self, api_key: str | None = None, model: str | None = None,
                 timeout: int | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.timeout = timeout or settings.GEMINI_TIMEOUT_SECONDS

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    # ------------------------------------------------------------------ #
    def generate_plan(self, prompt: str, image: tuple[bytes, str] | None = None) -> dict:
        """Call Gemini and return the parsed JSON plan.

        `image` is an optional (bytes, mime_type) tuple for multimodal input.
        Raises GeminiError with a user-safe message on ANY failure.
        """
        if not self.configured:
            raise GeminiError(
                "AI recommendations are temporarily unavailable — the Gemini API key "
                "is not configured. Showing demo recommendations instead."
            )

        parts: list[dict] = [{"text": prompt}]
        if image is not None:
            image_bytes, mime_type = image
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                }
            })

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.8,
                "maxOutputTokens": 4096,
            },
        }

        url = f"{API_BASE}/{self.model}:generateContent"
        try:
            response = httpx.post(
                url,
                json=payload,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                timeout=httpx.Timeout(self.timeout, connect=10.0),
            )
        except httpx.TimeoutException:
            logger.warning("Gemini request timed out after %ss", self.timeout)
            raise GeminiError(
                "The AI service took too long to respond. Please try again in a moment."
            )
        except httpx.HTTPError as exc:
            logger.warning("Gemini network error: %s", exc)
            raise GeminiError(
                "We couldn't reach the AI service right now. Showing a demo plan instead."
            )

        if response.status_code in (401, 403):
            raise GeminiError(
                "The AI service rejected the configured API key. "
                "Please check the GEMINI_API_KEY setting.",
                log_detail=f"HTTP {response.status_code}: {response.text[:300]}",
            )
        if response.status_code == 404:
            raise GeminiError(
                "The configured Gemini model is not available. "
                "Please check the GEMINI_MODEL setting.",
                log_detail=f"HTTP 404 for model {self.model}",
            )
        if response.status_code == 429:
            raise GeminiError(
                "The AI service is receiving too many requests right now. "
                "Please try again in a minute."
            )
        if response.status_code >= 400:
            logger.warning("Gemini HTTP %s: %s", response.status_code, response.text[:300])
            raise GeminiError(
                "The AI service couldn't process this plan. Please try again in a moment."
            )

        return self._parse_response(response.json())

    # ------------------------------------------------------------------ #
    def _parse_response(self, body: dict) -> dict:
        feedback = body.get("promptFeedback") or {}
        if feedback.get("blockReason"):
            raise GeminiError(
                "The AI declined to process this request, possibly because of the "
                "uploaded image. Try a different image or remove it and describe "
                "your outfit in words instead.",
                log_detail=f"Blocked: {feedback.get('blockReason')}",
            )

        candidates = body.get("candidates") or []
        if not candidates:
            raise GeminiError("The AI returned an empty response. Please try again.")

        text = "".join(
            part.get("text", "")
            for part in (candidates[0].get("content") or {}).get("parts", [])
        ).strip()
        if not text:
            raise GeminiError("The AI returned an empty response. Please try again.")

        return self._extract_json(text)

    def _extract_json(self, text: str) -> dict:
        """Parse model output as JSON, tolerating stray code fences / prose."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except json.JSONDecodeError:
                pass

        # Last resort: outermost { ... } block.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise GeminiError(
            "The AI returned an unreadable response. Please try again.",
            log_detail=f"Unparseable output: {text[:200]}",
        )


# Shared instance (stateless; safe to reuse across requests).
gemini_service = GeminiService()
