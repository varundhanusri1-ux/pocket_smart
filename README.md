# PocketSmart AI — Smart Budget & Recommendation Assistant

GenAI-powered, budget-aware recommendations for **home interiors**, **party planning**, and **jewelry styling**, built with **FastAPI** + **Google Gemini** + Jinja2/HTML/CSS/JS.

Enter a budget (plus rooms, guests, occasion — optionally an outfit photo) and get a category-wise allocation, curated product/service picks with estimated INR prices, and practical tips. Every plan is saved to your private history.

## Features

- **3 planners**: Home Interior (`/planners/home`), Party (`/planners/party`), Jewelry with optional outfit-image upload (`/planners/jewelry`)
- **Gemini multimodal AI** (`gemini-2.5-flash` default) with strict-JSON prompts, validation, and clearly-labelled **fallback demo plans** when the AI is unavailable
- **Auth**: register / login (JSON) / OAuth2 `/token` / logout (GET + POST), JWT in `Authorization` header or HttpOnly cookie, PBKDF2-hashed passwords
- **Session**: `/session-info`, `/session-data` (plan stats for dashboard insights)
- **Recommendations**: `/recommendations-details?plan_id=…` or `?planner_type=home|party|jewelry` (owner-only)
- **History**: `/history` renders HTML; send `Accept: application/json` for a JSON API
- **UX**: landing page, dashboard with insights, testimonials, responsive design, loading/error/empty states
- **Security**: per-user history isolation, magic-byte image validation, size limits, CORS allowlist, no secrets in responses, sanitized 500s

## Quickstart

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then edit .env (see below)
python run.py          # http://127.0.0.1:8000
```

### Environment (`.env`)

| Key | Required | Notes |
|---|---|---|
| `GEMINI_API_KEY` | For live AI | From [Google AI Studio](https://aistudio.google.com/apikey). App runs in labelled fallback/demo mode without it. |
| `GEMINI_MODEL` | No | Default `gemini-2.5-flash`. Any `generateContent` model works. |
| `SECRET_KEY` | Yes | Long random string: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | No | Default `sqlite:///./pocketsmart.db` |
| `CORS_ORIGINS` | No | Frontend origins only |
| `MAX_IMAGE_SIZE_MB` / `ALLOWED_IMAGE_TYPES` | No | Jewelry upload guardrails (default 5 MB, PNG/JPEG/WebP) |

Never commit `.env` (already in `.gitignore`). Commit `.env.example` only.

## API overview

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | — | Create account, returns JWT + sets cookie |
| POST | `/login` | — | JSON email/password login |
| POST | `/token` | — | OAuth2 password flow (API clients) |
| GET/POST | `/logout` | — | Clear session cookie |
| GET | `/session-info` | ✅ | Identity + token expiry |
| GET | `/session-data` | ✅ | User + per-planner plan stats |
| POST | `/generate-home` | ✅ | JSON: `total_budget`, `rooms[]`, furniture/lighting/fans/dining/decor/style |
| POST | `/generate-party` | ✅ | JSON: `total_budget`, `guest_count`, `event_type`, service toggles |
| POST | `/generate-jewelry` | ✅ | Multipart: `total_budget`, `occasion`, optional style/type/description + `outfit_image` |
| GET | `/recommendations-details` | ✅ | `?plan_id=` or `?planner_type=` (owner-only) |
| GET | `/history` | ✅ | HTML page; JSON with `Accept: application/json` |
| GET | `/startup` | — | Health/config probe (no secrets) |

Interactive docs: `/docs`.

## Project structure

```
app/
  main.py            # app factory, CORS, error handlers, /startup
  core/              # config, database, security (PBKDF2+JWT), deps (cookie/bearer auth)
  routes/            # auth, session, home, party, jewelry, recommendations, history, pages
  services/          # gemini_service, prompts, recommendation_service, budget_service, platform_service
  schemas/           # pydantic input/output validation
  models/            # User, RecommendationPlan (+ history queries)
  templates/         # Jinja2 pages (planners, recommendations, dashboard, history, …)
static/              # css/, js/ (planner forms, recommendations rendering), images/
tests/               # pytest: auth, home, party, jewelry, history, system
```

## Platform sources — honest abstraction

There are **no live marketplace integrations**. `platform_service.py` defines a `PlatformSource` adapter registry backed by a **simulated demo catalog**; the UI labels fallback plans as demo and prompts forbid inventing deep product URLs (homepage links only). Real affiliate/API adapters can be added later behind the same interface. Do not claim demo data is live, and do not add scraping.

## Testing

```bash
python -m pytest tests/ -q
```

Tests run in fallback mode (`GEMINI_API_KEY=""`) against an isolated temp SQLite DB and cover auth/session, all three planners (valid/invalid/fallback), image upload validation, history isolation, and system endpoints.

## Security notes

- Passwords: PBKDF2-HMAC-SHA256, per-user salt, constant-time compare
- JWT: signed with `SECRET_KEY`, expiry enforced, wrong-type tokens rejected
- History/details queries are scoped by `user_id` at the data-access layer
- Uploads: declared-type allowlist + magic-byte sniffing (PNG/JPEG/WebP), size cap, empty-file rejection
- `GET /history` redirects browsers to `/login` but returns JSON 401 to API clients
- Error handlers return human-readable messages; stack traces stay server-side
