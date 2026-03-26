# CLAUDE.md — AI Assistant Guide for adbot2

This document provides context for AI assistants working in this repository.

## Project Overview

**adbot2** ("Товарный Бро") is a Telegram bot for e-commerce advertising optimization, written in Python. It helps marketers manage and analyze ad campaigns on Facebook, TikTok, and Google Ads, compute unit economics, and get AI-powered recommendations.

The project is mid-refactor: the original monolithic `ad_bot_legacy.py` is being split into modular service and handler files. Both the legacy file and new modules coexist.

## Repository Structure

```
adbot2/
├── main.py                  # Entry point — starts the bot
├── ad_bot_legacy.py         # Monolithic bot (~11,500 lines) — all Telegram handlers
├── bot.py                   # Standalone unit economics calculator bot
│
├── config.py                # Central config: API keys, platform benchmarks, AI prompt
├── database.py              # JSON-based persistence layer
├── sessions.py              # Per-user API credential isolation
├── ai_service.py            # Multi-provider AI (DeepSeek → Groq → Gemini fallback)
├── tiktok_api.py            # TikTok Ads API client (per-user token management)
├── facebook_api.py          # Facebook Ads API client
├── helpers.py               # Utility functions, keyboards, formatters, rating helpers
├── settings.py              # Telegram FSM handlers for ⚙️ API Settings menu
│
├── user_data.json           # User plans and ad bundle snapshots
├── sessions.json            # Per-user API tokens and keys
├── reminders.json           # Notification preferences per user
│
├── bot.log / ecom.log       # Log files (do not commit)
├── migrate.sh               # Migration script (monolith → modular)
└── .env                     # Environment variables (do not commit)
```

## Running the Bot

```bash
# Install dependencies
pip install aiogram aiohttp pytrends

# Configure environment
cp .env .env.local  # edit with actual keys

# Start
python3 main.py
```

There is no `requirements.txt`. Dependencies: `aiogram` (v3.x), `aiohttp`, `pytrends`.

There is no test suite. Testing is manual via logs.

**View logs:**
```bash
tail -f bot.log
```

## Key Conventions

### Language
- User-facing messages and comments are in **Russian**.
- Code identifiers use English.

### Code Style
- **Python** snake_case for functions/variables, CamelCase for classes.
- All external I/O (API calls, file reads) is **async** using `asyncio` + `aiohttp`.
- HTTP timeouts are ~30 seconds.
- Error handling: `try/except` with `logging`, graceful fallbacks.
- Logging via Python's `logging` module at `INFO` level.

### No linting or formatting tools are configured. Follow existing style in each file.

### UI Conventions
- Telegram messages use **HTML parse mode** (not Markdown).
- Escape user content with `safe_html()` from `helpers.py`.
- Use emoji heavily for user-friendly output (e.g., `🎵` TikTok, `📘` Facebook, `🟢🟡🔴` traffic-light ratings).
- Keyboards are defined via `helpers.py` utilities: `main_kb()`, `platform_kb()`, `period_kb()`, etc.

### Traffic Light Rating
Metrics are rated using emoji based on platform-specific benchmarks defined in `config.py`:
- `🟢` good, `🟡` medium, `🔴` bad, `⏳` pending/unknown
- Use `rate_higher_better()` / `rate_lower_better()` from `helpers.py`.

## Architecture Patterns

### Session Isolation (Multi-Tenancy)
Each user can provide their own API credentials. `sessions.py` stores these in `sessions.json`. Functions like `get_tt_creds(user_id)` and `get_fb_creds(user_id)` fall back to the owner's keys from `config.py` if the user has none.

### AI Multi-Provider Fallback
`ai_service.py` tries providers in order: **DeepSeek → Groq → Gemini**. It detects context type (report analysis, copywriting, or Q&A) and adjusts behavior. User-specific AI keys are supported.

### Token Refresh
TikTok tokens are stored in a memory `_token_store` keyed by `user_id`. The client auto-refreshes on HTTP 401. See `tiktok_api.py`.

### FSM Flows
Complex multi-step user interactions use aiogram's **Finite State Machine** (`StatesGroup`). Each flow (unit economics, analysis, product check, AI chat, etc.) has its own `StatesGroup` class. All are currently in `ad_bot_legacy.py`.

### Data Persistence
JSON files in `DATA_DIR` (default: `/root/bot/data/`). `database.py` provides typed helpers. Bundles keep the last 20 historical snapshots automatically.

## Data Schemas

### `user_data.json`
```json
{
  "<user_id>": {
    "plans": {
      "<plan_name>": {
        "landing_price": 0.0,
        "net_profit": 0.0,
        "max_cpl": 0.0,
        "linked_campaigns": [{"id": "", "name": "", "source": "tt|fb|goog|uni"}]
        // ... full unit economics fields
      }
    },
    "bundles": {
      "<bundle_name>": {
        "spend": 0.0, "impressions": 0, "clicks": 0, "leads": 0,
        "ctr": 0.0, "cpm": 0.0, "cpc": 0.0, "cpl": 0.0,
        "verdict_emoji": "🟢",
        "history": []  // last 20 snapshots
      }
    }
  }
}
```

### `sessions.json`
```json
{
  "<user_id>": {
    "tt_advertiser_id": "", "tt_access_token": "", "tt_app_id": "", "tt_app_secret": "",
    "fb_access_token": "", "fb_ad_account_id": "",
    "deepseek_api_key": "", "groq_api_key": "", "gemini_api_key": ""
  }
}
```

### `reminders.json`
```json
{
  "<user_id>": {
    "report_times": ["HH:MM"],
    "reports_enabled": true,
    "enabled": true,
    "use_ai": false,
    "triggers_enabled": false,
    "alerts_enabled": false
  }
}
```

## Ongoing Refactoring

The project is splitting `ad_bot_legacy.py` into separate handler modules. The planned structure:

```
handlers/
├── start.py
├── unit_economics.py
├── analyze.py
├── campaigns.py
├── products.py
├── plans.py
├── ai_chat.py
├── dashboards.py
└── alerts.py
```

**When adding new features:**
- New service logic → create or extend a file in the root (e.g., `google_api.py`).
- New Telegram handlers → add to `ad_bot_legacy.py` for now, or create a new handler module and register it in `main.py`.
- Do not duplicate credential logic — always use `sessions.py`.
- Do not duplicate AI calls — always use `ai_service.py`.

## Security Notes

- **Never commit `.env`** or `sessions.json` — they contain API keys and user tokens.
- `config.py` contains hardcoded fallback keys for the owner account. Do not replace these with user credentials.
- User data files (`user_data.json`, `sessions.json`) contain personal and financial data. Do not log their contents.

## Environment Variables (`.env`)

| Variable | Purpose |
|---|---|
| `BOT_TOKEN` | Telegram bot token |
| `DEEPSEEK_API_KEY` | DeepSeek AI API key |
| `GROQ_API_KEY` | Groq AI API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `FB_ACCESS_TOKEN` | Facebook Ads API token (owner) |
| `FB_AD_ACCOUNT_ID` | Facebook ad account ID (owner) |
| `TT_APP_ID` | TikTok app ID (owner) |
| `TT_APP_SECRET` | TikTok app secret (owner) |
| `TT_ADVERTISER_ID` | TikTok advertiser ID (owner) |
| `TT_ACCESS_TOKEN` | TikTok access token (owner) |
| `DATA_DIR` | Path for JSON data files (default: `/root/bot/data`) |
