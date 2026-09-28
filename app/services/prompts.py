"""Prompt templates for the three planners.

Each prompt returns STRICT JSON (see the schema block) so responses can be
validated with Pydantic before they ever reach the UI.
"""

PLANNER_RULES = """
RULES you MUST follow:
- All prices must be realistic Indian market prices in INR (rupees), as plain numbers without currency symbols or commas.
- The sum of all recommendation totals (price x quantity) must stay within the given total budget. Prefer using 85-98% of it.
- `platform` must be one of: Amazon, Flipkart, IKEA, Swiggy, Zomato, OYO, Urban Company, Local Vendor, Local Retailer.
- `link` must be either an empty string or the platform's official homepage (for example https://www.amazon.in, https://www.flipkart.com, https://www.ikea.com/in/en/, https://www.swiggy.com, https://www.zomato.com, https://www.oyorooms.com). NEVER invent deep product URLs or fake listing pages.
- Every recommendation needs a concrete, specific product or service name (no placeholders like "Item 1").
- `reason` should explain in one sentence why this fits the user's needs and budget.
- Do NOT claim the items are verified live listings. Phrase `summary` as advisory guidance.
- Respond with ONLY the JSON object. No markdown, no code fences, no commentary.
"""

JSON_SCHEMA = """
Return JSON with EXACTLY this shape:
{
  "summary": "2-3 sentence plan overview",
  "allocation": [
    {"category": "string", "amount": 0, "percentage": 0, "note": "short rationale"}
  ],
  "recommendations": [
    {"name": "string", "category": "string", "estimated_price": 0, "quantity": 1,
     "platform": "string", "reason": "string", "link": ""}
  ],
  "tips": ["short actionable budgeting tip", "..."]
}
"""


def home_prompt(data) -> str:
    room_lines = "\n".join(
        f"- {r.room_type} (quantity: {r.quantity})" for r in data.rooms
    )
    needs = []
    if data.furniture:
        needs.append("Furniture")
    if data.lighting:
        needs.append("Lighting (lamps, ceiling lights, LED strips)")
    if data.ceiling_fans:
        needs.append(f"Ceiling fans: {data.ceiling_fans}")
    if data.dining_table:
        needs.append("Dining table")
    if data.decor:
        needs.append("Decor (art, plants, rugs, cushions)")
    needs_text = "\n".join(f"- {n}" for n in needs) or "- General setup"
    style = data.style or "no specific style"
    extra = data.additional_requirements or "none"

    return f"""You are PocketSmart AI, an expert home interior budget planner.
Plan an Indian home interior setup within a strict budget.

TOTAL BUDGET: INR {data.total_budget:,.0f}
ROOMS TO FURNISH:
{room_lines}

REQUIREMENTS:
{needs_text}
STYLE PREFERENCE: {style}
ADDITIONAL REQUIREMENTS: {extra}

Allocate the budget across meaningful categories (furniture, lighting, fans, dining, decor, contingency)
respecting the selected requirements, then recommend specific cost-effective products per category
with platform labels (IKEA and Amazon are especially relevant for interiors).

{PLANNER_RULES}
{JSON_SCHEMA}"""


def party_prompt(data) -> str:
    services = []
    if data.venue_required:
        services.append("Venue / hall booking")
    if data.food_catering:
        services.append("Food & catering")
    if data.decoration:
        services.append("Decoration")
    if data.entertainment:
        services.append("Entertainment (music, games, performers)")
    if data.accommodation_required:
        services.append("Accommodation for guests")
    services_text = "\n".join(f"- {s}" for s in services) or "- General planning"
    extra = data.additional_preferences or "none"
    per_guest = data.total_budget / data.guest_count

    return f"""You are PocketSmart AI, an expert event budget planner for Indian events.
Plan a {data.event_type} event within a strict budget.

TOTAL BUDGET: INR {data.total_budget:,.0f}
GUEST COUNT: {data.guest_count} (approx. INR {per_guest:,.0f} per guest available)
EVENT TYPE: {data.event_type}
SERVICES NEEDED:
{services_text}
ADDITIONAL PREFERENCES: {extra}

Allocate the budget proportionally across the requested services (food usually deserves the largest
share). Recommend specific vendors/services per category: catering via Swiggy/Zomato where sensible,
venue and rooms via OYO for accommodation, decor and entertainment items via Amazon/Flipkart.
Keep quantities realistic for {data.guest_count} guests.

{PLANNER_RULES}
{JSON_SCHEMA}"""


def jewelry_prompt(data, image_context: str | None) -> str:
    image_block = f"""
OUTFIT IMAGE ANALYSIS: {image_context}
Use the described visual cues (colors, style, formality) to pick jewelry that coordinates well.
""" if image_context else """
No outfit image was provided. Base your picks on the written outfit description and occasion.
"""
    return f"""You are PocketSmart AI, an expert jewelry stylist for Indian occasions.
Recommend jewelry within a strict budget.

TOTAL BUDGET: INR {data.total_budget:,.0f}
OCCASION: {data.occasion}
STYLE PREFERENCE: {data.style_preference or "no specific style"}
JEWELRY TYPE PREFERENCE: {data.jewelry_type or "open to suggestions"}
OUTFIT DESCRIPTION: {data.outfit_description or "not described"}
{image_block}
Allocate the budget across a main piece plus optional matching accessories. Recommend specific
jewelry items (e.g., "Gold-plated jhumka earrings", "Kundan choker necklace set") with realistic
INR prices for imitation/fine jewelry as appropriate to the budget. Source platforms are usually
Amazon and Flipkart.

IMPORTANT: Describe only the outfit's visual characteristics (colors, style, formality).
Never make assumptions about the person wearing it or any personal characteristics.

{PLANNER_RULES}
{JSON_SCHEMA}"""
