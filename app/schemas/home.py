"""Home Interior planner input schema."""
from pydantic import BaseModel, Field, field_validator, model_validator

ROOM_SUGGESTIONS = ("Living Room", "Kitchen", "Bedroom", "Bathroom", "Dining Room",
                    "Study Room", "Kids Room", "Balcony", "Other")


class RoomSpec(BaseModel):
    room_type: str = Field(min_length=2, max_length=40)
    quantity: int = Field(default=1, ge=1, le=20)

    @field_validator("room_type")
    @classmethod
    def clean_room(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Room type cannot be empty")
        return v[:40]


class HomePlanRequest(BaseModel):
    total_budget: float = Field(gt=0, le=1_000_000_000, description="Total budget in INR")
    rooms: list[RoomSpec] = Field(min_length=1, max_length=12)
    furniture: bool = False
    lighting: bool = False
    ceiling_fans: int = Field(default=0, ge=0, le=50)
    dining_table: bool = False
    decor: bool = False
    style: str | None = Field(default=None, max_length=60)
    additional_requirements: str | None = Field(default=None, max_length=1000)

    @field_validator("style", "additional_requirements")
    @classmethod
    def clean_optional(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            return v or None
        return v

    @model_validator(mode="after")
    def at_least_one_need(self) -> "HomePlanRequest":
        if not (self.furniture or self.lighting or self.ceiling_fans > 0
                or self.dining_table or self.decor or self.style):
            raise ValueError(
                "Select at least one requirement — furniture, lighting, ceiling fans, "
                "dining table, decor or a style preference."
            )
        return self

    def to_input_summary(self) -> dict:
        rooms = ", ".join(
            f"{r.room_type} x{r.quantity}" if r.quantity > 1 else r.room_type for r in self.rooms
        )
        needs = []
        if self.furniture:
            needs.append("Furniture")
        if self.lighting:
            needs.append("Lighting")
        if self.ceiling_fans:
            needs.append(f"{self.ceiling_fans} ceiling fan(s)")
        if self.dining_table:
            needs.append("Dining table")
        if self.decor:
            needs.append("Decor")
        if self.style:
            needs.append(f"{self.style} style")
        return {
            "rooms": rooms,
            "requirements": ", ".join(needs) or "General setup",
            "additional": self.additional_requirements or "",
        }
