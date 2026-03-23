"""
sessions.py — Сессионность пользователей.

Каждый пользователь может подключить СВОИ API ключи:
  - TikTok Ads (advertiser_id + access_token)
  - Facebook Ads (ad_account_id + access_token)
  - AI провайдеры (deepseek / groq / gemini)

Если пользовательских ключей нет — используются owner-ключи из config.py.
Данные каждого юзера изолированы — никто не видит чужого.
"""

import json
import os
import logging
from config import SESSIONS_FILE, DATA_DIR


def _load() -> dict:
    if not os.path.exists(SESSIONS_FILE):
        return {}
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────

def get_session(user_id: int) -> dict:
    """Возвращает сессию пользователя (или пустой dict)."""
    return _load().get(str(user_id), {})


def save_session(user_id: int, session: dict):
    """Сохраняет/обновляет сессию пользователя."""
    data = _load()
    data[str(user_id)] = session
    _save(data)


def delete_session(user_id: int):
    """Удаляет сессию (сброс к owner-ключам)."""
    data = _load()
    data.pop(str(user_id), None)
    _save(data)


def set_session_field(user_id: int, field: str, value):
    """Устанавливает одно поле сессии."""
    session = get_session(user_id)
    session[field] = value
    save_session(user_id, session)


# ──────────────────────────────────────────────
# HELPERS — возвращают актуальный ключ (user или owner)
# ──────────────────────────────────────────────

def get_tt_creds(user_id: int) -> dict:
    """Возвращает TikTok credentials для пользователя."""
    from config import TT_ADVERTISER_ID, TT_ACCESS_TOKEN, TT_APP_ID, TT_APP_SECRET
    s = get_session(user_id)
    return {
        "advertiser_id": s.get("tt_advertiser_id") or TT_ADVERTISER_ID,
        "access_token":  s.get("tt_access_token")  or TT_ACCESS_TOKEN,
        "app_id":        s.get("tt_app_id")         or TT_APP_ID,
        "app_secret":    s.get("tt_app_secret")     or TT_APP_SECRET,
    }


def get_fb_creds(user_id: int) -> dict:
    """Возвращает Facebook credentials для пользователя."""
    from config import FB_ACCESS_TOKEN, FB_AD_ACCOUNT_ID
    s = get_session(user_id)
    return {
        "access_token":   s.get("fb_access_token")   or FB_ACCESS_TOKEN,
        "ad_account_id":  s.get("fb_ad_account_id")  or FB_AD_ACCOUNT_ID,
    }


def get_ai_keys(user_id: int) -> dict:
    """Возвращает AI ключи для пользователя."""
    from config import DEEPSEEK_API_KEY, GROQ_API_KEY, GEMINI_API_KEY
    s = get_session(user_id)
    return {
        "deepseek": s.get("deepseek_api_key") or DEEPSEEK_API_KEY,
        "groq":     s.get("groq_api_key")     or GROQ_API_KEY,
        "gemini":   s.get("gemini_api_key")   or GEMINI_API_KEY,
    }


def has_custom_tt(user_id: int) -> bool:
    s = get_session(user_id)
    return bool(s.get("tt_access_token") and s.get("tt_advertiser_id"))


def has_custom_fb(user_id: int) -> bool:
    s = get_session(user_id)
    return bool(s.get("fb_access_token") and s.get("fb_ad_account_id"))
