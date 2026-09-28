"""Page routes (Jinja2): landing, auth pages, planners, dashboard, misc."""
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import __version__
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_optional_user
from app.models import User
from app.models.history import get_plan_stats, get_user_plans
from app.services import budget_service

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["APP_NAME"] = settings.APP_NAME
templates.env.globals["APP_VERSION"] = __version__

router = APIRouter(tags=["pages"])


def _ctx(request: Request, user: User | None = None, **extra) -> dict:
    ctx = {
        "request": request,
        "user": user,
        "current_year": datetime.now(timezone.utc).year,
        **extra,
    }
    return ctx


def _require_user(user: User | None) -> RedirectResponse | None:
    if user is None:
        return RedirectResponse(url="/login", status_code=302)
    return None


# ----------------------------- public pages ----------------------------- #

@router.get("/")
def landing(request: Request, user: User | None = Depends(get_optional_user)):
    return templates.TemplateResponse(request, "home.html", _ctx(request, user))


@router.get("/login")
def login_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", _ctx(request, user))


@router.get("/register")
def register_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request, "register.html", _ctx(request, user))


@router.get("/testimonials")
def testimonials_page(request: Request, user: User | None = Depends(get_optional_user)):
    return templates.TemplateResponse(request, "testimonials.html", _ctx(request, user))


# ---------------------------- planner pages ----------------------------- #

def _planner_page(request: Request, user: User | None, template: str, planner: str, **extra):
    redirect = _require_user(user)
    if redirect:
        return redirect
    next_target = f"/planners/{planner}"
    return templates.TemplateResponse(
        request, template, _ctx(request, user, next_target=quote(next_target, safe=""), **extra)
    )


@router.get("/planners/home")
def home_planner_page(request: Request, user: User | None = Depends(get_optional_user)):
    return _planner_page(request, user, "home_planner.html", "home")


@router.get("/planners/home/recommendations")
def home_recommendations_page(request: Request, user: User | None = Depends(get_optional_user)):
    return _planner_page(request, user, "home_recommendations.html", "home")


@router.get("/planners/party")
def party_planner_page(request: Request, user: User | None = Depends(get_optional_user)):
    return _planner_page(request, user, "party_planner.html", "party")


@router.get("/planners/party/recommendations")
def party_recommendations_page(request: Request, user: User | None = Depends(get_optional_user)):
    return _planner_page(request, user, "party_recommendations.html", "party")


@router.get("/planners/jewelry")
def jewelry_planner_page(request: Request, user: User | None = Depends(get_optional_user)):
    return _planner_page(request, user, "jewelry_planner.html", "jewelry")


@router.get("/planners/jewelry/recommendations")
def jewelry_recommendations_page(request: Request, user: User | None = Depends(get_optional_user)):
    return _planner_page(request, user, "jewelry_recommendations.html", "jewelry")


# ---------------------------- user pages -------------------------------- #

@router.get("/dashboard")
def dashboard_page(request: Request, user: User | None = Depends(get_optional_user),
                   db: Session = Depends(get_db)):
    redirect = _require_user(user)
    if redirect:
        return redirect

    stats = get_plan_stats(db, user.id)
    recent = get_user_plans(db, user.id, limit=5)
    insights = build_insights(stats)
    return templates.TemplateResponse(request, "dashboard.html", _ctx(
        request, user, stats=stats, recent=recent, insights=insights,
    ))


def build_insights(stats: dict) -> list[dict]:
    """Personalized dashboard insights derived from the user's plan stats."""
    insights: list[dict] = []
    by_type = stats["by_type"]
    total = stats["total_plans"]

    favorite = max(by_type.items(), key=lambda kv: kv[1]["count"])
    if favorite[1]["count"] > 0:
        label = {"home": "home interiors", "party": "parties", "jewelry": "jewelry"}[favorite[0]]
        insights.append({
            "icon": "star",
            "title": "Your favourite planner",
            "text": f"You've planned {favorite[1]['count']} {label}"
                    + (" so far — keep the streak going!" if favorite[1]["count"] == 1 else "!"),
        })
    if total >= 2:
        total_budget = sum(v["total_budget"] for v in by_type.values())
        insights.append({
            "icon": "wallet",
            "title": "Total budget planned",
            "text": f"Across {total} plans you've organized {budget_service.format_inr(total_budget)}.",
        })
    if by_type["party"]["count"] >= 1 and by_type["jewelry"]["count"] == 0:
        insights.append({
            "icon": "sparkle",
            "title": "Try the Jewelry Planner",
            "text": "Planning a party? Get occasion-matched jewelry ideas that fit the same budget.",
        })
    if by_type["home"]["count"] >= 1 and by_type["party"]["count"] == 0:
        insights.append({
            "icon": "party",
            "title": "Try the Party Planner",
            "text": "Your home is ready — let PocketSmart AI plan your next celebration too.",
        })
    if not insights:
        insights.append({
            "icon": "rocket",
            "title": "Welcome to PocketSmart AI",
            "text": "Generate your first plan and your insights will appear here.",
        })
    return insights[:3]
