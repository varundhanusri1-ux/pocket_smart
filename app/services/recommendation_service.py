"""Recommendation engine — orchestrates prompts, Gemini, validation, fallback.

Flow per plan:
  1. Build a planner-specific prompt.
  2. Ask Gemini for structured JSON (optionally with an outfit image).
  3. Validate/normalize the output with Pydantic; top up incomplete parts.
  4. If Gemini is unavailable/fails/malformed, build a clearly-labelled
     fallback plan from the simulated platform catalog (never presented as AI).
  5. Persist the plan and return it.
"""
import logging
import random

from sqlalchemy.orm import Session

from app.models import RecommendationPlan, User
from app.schemas.recommendation import AllocationItem, PlanResult, RecommendationItem
from app.services import budget_service, platform_service, prompts
from app.services.gemini_service import GeminiError, gemini_service

logger = logging.getLogger("pocketsmart.recommendations")

FALLBACK_NOTE = (
    "AI recommendations are temporarily unavailable, so this is a demo plan built "
    "from PocketSmart's simulated catalog. It is NOT live Gemini output or live "
    "platform data."
)


# --------------------------------------------------------------------------- #
# Output normalization
# --------------------------------------------------------------------------- #

def _coerce_recommendation(raw: dict, source: str) -> RecommendationItem | None:
    try:
        price = max(0.0, float(raw.get("estimated_price") or 0))
        quantity = max(1, int(float(raw.get("quantity") or 1)))
        name = str(raw.get("name") or "").strip()
        category = str(raw.get("category") or "General").strip()[:80]
        if not name or price <= 0:
            return None
        platform = platform_service.known_platform(str(raw.get("platform") or ""))
        link = str(raw.get("link") or "").strip() or platform_service.platform_homepage(platform)
        return RecommendationItem(
            name=name[:160],
            category=category,
            estimated_price=price,
            quantity=quantity,
            total_price=round(price * quantity, 2),
            platform=platform,
            reason=(str(raw.get("reason") or "").strip()[:500]) or None,
            link=link or None,
            source=source,
        )
    except (TypeError, ValueError):
        return None


def normalize_ai_result(raw: dict, budget: float, planner_type: str) -> PlanResult:
    """Validate Gemini output; raise GeminiError when it's unusable."""
    if not isinstance(raw, dict):
        raise GeminiError("AI response had an unexpected structure.")

    recommendations: list[RecommendationItem] = []
    for item in (raw.get("recommendations") or [])[:40]:
        if isinstance(item, dict):
            coerced = _coerce_recommendation(item, "ai")
            if coerced:
                recommendations.append(coerced)

    allocation: list[AllocationItem] = []
    for entry in (raw.get("allocation") or [])[:15]:
        if not isinstance(entry, dict):
            continue
        try:
            allocation.append(AllocationItem(
                category=str(entry.get("category") or "General")[:80],
                amount=max(0.0, float(entry.get("amount") or 0)),
                percentage=max(0.0, min(100.0, float(entry.get("percentage") or 0))),
                note=(str(entry.get("note") or "").strip()[:300]) or None,
            ))
        except (TypeError, ValueError):
            continue

    tips = [str(t).strip()[:300] for t in (raw.get("tips") or [])[:10] if str(t).strip()]
    summary = str(raw.get("summary") or "").strip()

    if not recommendations:
        # AI produced no usable recommendations -> not displayable as-is.
        raise GeminiError(
            "The AI response didn't include usable recommendations.",
            log_detail=f"No recommendations in output for {planner_type}",
        )
    if not summary:
        summary = (
            f"Here's a {planner_type} plan curated within your budget of "
            f"{budget_service.format_inr(budget)}."
        )

    result = PlanResult(
        summary=summary[:2000],
        budget=budget,
        allocation=allocation,
        recommendations=recommendations,
        tips=tips,
    )
    _rebalance_allocation(result, planner_type)
    return result


def _rebalance_allocation(result: PlanResult, planner_type: str) -> None:
    """Keep allocation figures consistent with the actual itemized plan."""
    if result.allocation:
        total_pct = sum(a.percentage for a in result.allocation)
        if total_pct <= 0:
            for a in result.allocation:
                a.percentage = round(a.amount / result.total_estimated_cost * 100, 1) \
                    if result.total_estimated_cost else 0.0
        elif abs(total_pct - 100) > 2:
            for a in result.allocation:
                a.percentage = round(a.percentage / total_pct * 100, 1)
        alloc_total = sum(a.amount for a in result.allocation)
        if result.total_estimated_cost and abs(alloc_total - result.total_estimated_cost) > result.budget * 0.15:
            scale = result.total_estimated_cost / alloc_total
            for a in result.allocation:
                a.amount = round(a.amount * scale, 2)
    elif result.recommendations:
        result.allocation = _derive_allocation(result, planner_type)


def _derive_allocation(result: PlanResult, planner_type: str) -> list[AllocationItem]:
    """Derive category allocation from actual recommended items."""
    by_category: dict[str, float] = {}
    for rec in result.recommendations:
        by_category[rec.category] = by_category.get(rec.category, 0.0) + rec.total_price
    items: list[AllocationItem] = []
    for category, amount in by_category.items():
        items.append(AllocationItem(
            category=category[:80],
            amount=round(amount, 2),
            percentage=round(amount / result.total_estimated_cost * 100, 1) if result.total_estimated_cost else 0,
            note=budget_service._ALLOCATION_NOTES.get(category, ""),
        ))
    return sorted(items, key=lambda a: a.amount, reverse=True)


# --------------------------------------------------------------------------- #
# Fallback plan builder (Phase 19)
# --------------------------------------------------------------------------- #

def build_fallback_plan(budget: float, planner_type: str, categories: list[str],
                        note: str = FALLBACK_NOTE) -> PlanResult:
    """Structured demo plan from the simulated catalog. Clearly labelled."""
    allocation = budget_service.build_allocation(planner_type, budget, categories)
    recommendations: list[RecommendationItem] = []

    for entry in allocation:
        category = entry.category
        if category == "Contingency":
            continue
        demo_items = platform_service.demo_items_for_category(
            planner_type, category, entry.amount, count=2
        )
        if not demo_items:
            continue
        picked = demo_items[0]
        price = picked["estimated_price"]
        # Fit the pick to the category envelope (roughly 40-90% of it).
        price = max(min(price, entry.amount * 0.9), min(entry.amount * 0.4, price))
        price = round(price, 2)
        recommendations.append(RecommendationItem(
            name=picked["name"],
            category=category,
            estimated_price=price,
            quantity=1,
            total_price=price,
            platform=picked["platform"],
            reason=f"Demo pick for the {category.lower()} portion of your budget.",
            link=picked.get("link") or None,
            source="fallback",
        ))
        if len(demo_items) > 1 and entry.amount - price > demo_items[1]["estimated_price"]:
            second = demo_items[1]
            second_price = round(second["estimated_price"], 2)
            recommendations.append(RecommendationItem(
                name=second["name"],
                category=category,
                estimated_price=second_price,
                quantity=1,
                total_price=second_price,
                platform=second["platform"],
                reason=f"Optional add-on within the {category.lower()} budget.",
                link=second.get("link") or None,
                source="fallback",
            ))

    if not recommendations:
        raise RuntimeError("Fallback catalog produced no items")

    fallback_tips = [
        "This is demo data — reconnect the AI service for personalized plans.",
        "Prices are estimates; confirm current prices on the platform before buying.",
    ]
    if planner_type == "party":
        fallback_tips.insert(1, "Lock the venue and caterer first — they move fastest in price.")
    elif planner_type == "home":
        fallback_tips.insert(1, "Buy large furniture first, then layer lighting and decor.")
    else:
        fallback_tips.insert(1, "Match metals across pieces for a cohesive look.")

    return PlanResult(
        summary=FALLBACK_NOTE,
        budget=budget,
        allocation=allocation,
        recommendations=recommendations,
        tips=fallback_tips,
        # signals demo mode in the UI
    )


# --------------------------------------------------------------------------- #
# Public entry points per planner
# --------------------------------------------------------------------------- #

def _persist_plan(db: Session, user: User, planner_type: str, title: str,
                  input_summary: dict, budget: float, result: PlanResult,
                  source: str) -> RecommendationPlan:
    plan = RecommendationPlan(
        user_id=user.id,
        planner_type=planner_type,
        title=title[:200],
        input_summary=input_summary,
        budget=budget,
        result=result.model_dump(),
        source=source,
        ai_generated=(source == "gemini"),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _finalize(db: Session, user: User, planner_type: str, title: str,
              input_summary: dict, budget: float, categories: list[str],
              prompt: str, image: tuple[bytes, str] | None = None,
              fallback_note: str = "") -> tuple[RecommendationPlan, PlanResult]:
    try:
        raw = gemini_service.generate_plan(prompt, image=image)
        result = normalize_ai_result(raw, budget, planner_type)
        source = "gemini"
    except GeminiError as exc:
        logger.warning("Falling back for %s plan: %s", planner_type, exc.log_detail or exc.user_message)
        result = build_fallback_plan(budget, planner_type, categories)
        if fallback_note:
            result.tips.insert(0, fallback_note)
        source = "fallback"

    plan = _persist_plan(db, user, planner_type, title, input_summary, budget, result, source)
    return plan, result


def generate_home_plan(db: Session, user: User, data) -> RecommendationPlan:
    categories = budget_service.home_requested_categories(data)
    return _finalize(
        db, user, "home",
        f"Home interior plan — {budget_service.format_inr(data.total_budget)}",
        data.to_input_summary(), data.total_budget, categories,
        prompts.home_prompt(data),
    )[0]


def generate_party_plan(db: Session, user: User, data) -> RecommendationPlan:
    categories = budget_service.party_requested_categories(data)
    return _finalize(
        db, user, "party",
        f"{data.event_title} party plan — {budget_service.format_inr(data.total_budget)}",
        data.to_input_summary(), data.total_budget, categories,
        prompts.party_prompt(data),
    )[0]


def generate_jewelry_plan(db: Session, user: User, data,
                          image: tuple[bytes, str] | None = None) -> RecommendationPlan:
    image_context = None
    if image is not None:
        # Lightweight description of what the AI should extract; the real
        # analysis happens inside Gemini's multimodal pass.
        image_context = "provided — analyze colors, formality and visual style"
    fallback_note = ""
    if image is not None and not gemini_service.configured:
        fallback_note = (
            "Your image couldn't be analyzed because the AI service is unavailable. "
            "The demo plan below is based on your text description only."
        )
    return _finalize(
        db, user, "jewelry",
        f"{data.occasion.title()} jewelry plan — {budget_service.format_inr(data.total_budget)}",
        data.to_input_summary(image_used=image is not None),
        data.total_budget, budget_service.jewelry_requested_categories(),
        prompts.jewelry_prompt(data, image_context),
        image=image,
        fallback_note=fallback_note,
    )[0]


def plan_response(plan: RecommendationPlan) -> dict:
    """Serialize a stored plan into the API response shape."""
    from app.schemas.recommendation import PlanResponse

    return PlanResponse(
        plan_id=plan.id,
        planner_type=plan.planner_type,
        title=plan.title,
        input_summary=plan.input_summary or {},
        source=plan.source,
        ai_generated=plan.ai_generated,
        created_at=plan.created_at,
        result=PlanResult(**plan.result),
    ).model_dump(mode="json")
