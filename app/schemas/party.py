"""Party planner input schema."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

EVENT_TYPES = ("birthday", "wedding", "corporate", "other")


class PartyPlanRequest(BaseModel):
    total_budget: float = Field(gt=0, le=1_000_000_000, description="Total budget in INR")
    guest_count: int = Field(ge=1, le=5000)
    event_type: Literal["birthday", "wedding", "corporate", "other"]
    venue_required: bool = True
    food_catering: bool = True
    decoration: bool = True
    entertainment: bool = False
    accommodation_required: bool = False
    additional_preferences: str | None = Field(default=None, max_length=1000)

    @field_validator("additional_preferences")
    @classmethod
    def clean_optional(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            return v or None
        return v

    @model_validator(mode="after")
    def at_least_one_need(self) -> "PartyPlanRequest":
        if not (self.venue_required or self.food_catering or self.decoration
                or self.entertainment or self.accommodation_required):
            raise ValueError(
                "Select at least one arrangement — venue, food, decoration, "
                "entertainment or accommodation."
            )
        return self

    @property
    def event_title(self) -> str:
        return self.event_type.capitalize() if self.event_type != "other" else "Special event"

    def to_input_summary(self) -> dict:
        services = []
        if self.venue_required:
            services.append("Venue")
        if self.food_catering:
            services.append("Food & catering")
        if self.decoration:
            services.append("Decoration")
        if self.entertainment:
            services.append("Entertainment")
        if self.accommodation_required:
            services.append("Accommodation")
        return {
            "guests": self.guest_count,
            "event_type": self.event_title,
            "services": ", ".join(services) or "General planning",
            "additional": self.additional_preferences or "",
        }
