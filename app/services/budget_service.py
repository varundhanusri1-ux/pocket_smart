"""Budget allocation helpers — default category weights and formatting."""
from typing import Sequence

from app.schemas.recommendation import AllocationItem


def format_inr(amount: float) -> str:
    """Format an INR amount the Indian way (lakhs/crores grouping)."""
    return f"₹{amount:,.0f}"


# Default category weights per planner. Only the requested categories receive
# weight; the remainder is redistributed proportionally.
_HOME_WEIGHTS = {
    "Furniture": 0.34,
    "Lighting": 0.14,
    "Fans & Cooling": 0.10,
    "Dining": 0.16,
    "Decor": 0.16,
    "Contingency": 0.10,
}

_PARTY_WEIGHTS = {
    "Food & Catering": 0.38,
    "Venue": 0.24,
    "Decoration": 0.16,
    "Entertainment": 0.12,
    "Accommodation": 0.10,
}

_JEWELRY_WEIGHTS = {
    "Primary Piece": 0.62,
    "Matching Accessories": 0.26,
    "Finishing Touches": 0.12,
}

_PLANNER_WEIGHTS = {"home": _HOME_WEIGHTS, "party": _PARTY_WEIGHTS, "jewelry": _JEWELRY_WEIGHTS}

_ALLOCATION_NOTES = {
    "Furniture": "Core seating, storage and beds",
    "Lighting": "Ambient and accent lighting",
    "Fans & Cooling": "Comfort appliances for the rooms",
    "Dining": "Eating area setup",
    "Decor": "Finishing touches and personality",
    "Contingency": "Buffer for delivery, setup and surprises",
    "Food & Catering": "Guest experience starts with the menu",
    "Venue": "Space rental for the guest count",
    "Decoration": "Theme and ambience",
    "Entertainment": "Keeps guests engaged",
    "Accommodation": "Stays for out-of-town guests",
    "Primary Piece": "The hero jewelry item for the occasion",
    "Matching Accessories": "Pieces that complete the look",
    "Finishing Touches": "Care, storage and presentation",
}


def required_categories(planner_type: str, requested: Sequence[str]) -> list[str]:
    """Category names activated for this plan, in canonical order."""
    weights = _PLANNER_WEIGHTS[planner_type]
    wanted = set(requested)
    return [c for c in weights if c in wanted]


def build_allocation(planner_type: str, budget: float, requested: Sequence[str]) -> list[AllocationItem]:
    """Distribute the budget across the requested categories.

    Weights of the selected categories are renormalized to 100%.
    """
    weights = _PLANNER_WEIGHTS[planner_type]
    active = required_categories(planner_type, requested)
    if not active:
        active = list(weights)[:2]
    total_weight = sum(weights[c] for c in active)
    items: list[AllocationItem] = []
    for category in active:
        share = weights[category] / total_weight
        amount = round(budget * share, 2)
        items.append(AllocationItem(
            category=category,
            amount=amount,
            percentage=round(share * 100, 1),
            note=_ALLOCATION_NOTES.get(category, ""),
        ))
    return items


def home_requested_categories(data) -> list[str]:
    cats: list[str] = []
    if data.furniture:
        cats.append("Furniture")
    if data.lighting:
        cats.append("Lighting")
    if data.ceiling_fans:
        cats.append("Fans & Cooling")
    if data.dining_table:
        cats.append("Dining")
    if data.decor:
        cats.append("Decor")
    cats.append("Contingency")
    return cats


def party_requested_categories(data) -> list[str]:
    cats: list[str] = []
    if data.food_catering:
        cats.append("Food & Catering")
    if data.venue_required:
        cats.append("Venue")
    if data.decoration:
        cats.append("Decoration")
    if data.entertainment:
        cats.append("Entertainment")
    if data.accommodation_required:
        cats.append("Accommodation")
    return cats


def jewelry_requested_categories() -> list[str]:
    return ["Primary Piece", "Matching Accessories", "Finishing Touches"]
