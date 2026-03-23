"""
utils/helpers.py — утилиты парсинга, форматирования, клавиатуры, светофор.
"""

import re
import html
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import NORMS


# ──────────────────────────────────────────────
# ПАРСИНГ
# ──────────────────────────────────────────────

def pn(text: str):
    """Парсит число (float). Возвращает None при ошибке."""
    try:
        return float(
            text.strip()
            .replace(",", ".").replace("%", "")
            .replace("$", "").replace(" ", "")
        )
    except Exception:
        return None


def pn_int(text: str):
    try:
        return int(float(text.strip().replace(",", "").replace(" ", "")))
    except Exception:
        return None


def pyn(text: str):
    """Парсит да/нет → True/False/None."""
    t = text.strip().lower()
    if any(x in t for x in ("да", "yes", "✅")):
        return True
    if any(x in t for x in ("нет", "no", "❌")):
        return False
    return None


def parse_views(text: str):
    text = text.strip().lower().replace(" ", "").replace(",", ".")
    multiplier = 1
    if text.endswith(("m", "м")):
        text, multiplier = text[:-1], 1_000_000
    elif text.endswith(("k", "к")):
        text, multiplier = text[:-1], 1_000
    v = pn(text)
    if v is None or v < 0:
        return None
    return v * multiplier


def parse_platform(text: str):
    t = text.lower()
    if any(x in t for x in ("facebook", "fb", "instagram", "📘")):
        return "fb"
    if any(x in t for x in ("tiktok", "тикток", "tt", "🎵")):
        return "tt"
    if any(x in t for x in ("google", "гугл", "🔍")):
        return "goog"
    if any(x in t for x in ("друг", "📢")):
        return "uni"
    return None


# ──────────────────────────────────────────────
# ФОРМАТИРОВАНИЕ
# ──────────────────────────────────────────────

def format_number_short(n: float) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(int(n))


def build_sparkline(values: list, width: int = 20) -> str:
    if not values:
        return ""
    if len(values) > width:
        step = len(values) / width
        values = [values[min(int(i * step), len(values) - 1)] for i in range(width)]
    max_v = max(values) or 1
    blocks = " ▁▂▃▄▅▆▇█"
    return "".join(blocks[int(v / max_v * (len(blocks) - 1))] for v in values)


def safe_html(text: str) -> str:
    return html.escape(str(text))


def smart_split(text: str, max_len: int = 4000) -> list:
    """Разбивает текст на части, не разрывая слова."""
    parts = []
    while len(text) > max_len:
        cut = text.rfind("\n", 0, max_len)
        if cut == -1:
            cut = max_len
        parts.append(text[:cut])
        text = text[cut:]
    if text:
        parts.append(text)
    return parts


# ──────────────────────────────────────────────
# КЛАВИАТУРЫ
# ──────────────────────────────────────────────

def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🎵 Дашборд TikTok"),  KeyboardButton(text="📘 Дашборд Facebook")],
        [KeyboardButton(text="🤖 AI ТОВАРНЫЙ БРО")],
        [KeyboardButton(text="📊 Юнит-экономика"), KeyboardButton(text="📈 Анализ связки")],
        [KeyboardButton(text="🔗 Привязать кампании"), KeyboardButton(text="🔓 Отвязать кампании")],
        [KeyboardButton(text="📋 Мои планы"),       KeyboardButton(text="📎 Мои связки")],
        [KeyboardButton(text="⚙️ Настройки API"),  KeyboardButton(text="⏰ Уведомления")],
    ], resize_keyboard=True)


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True)


def yes_no_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]
    ], resize_keyboard=True)


def platform_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📘 Facebook/Instagram"), KeyboardButton(text="🎵 TikTok")],
        [KeyboardButton(text="🔍 Google Ads"),         KeyboardButton(text="📢 Другая")],
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True)


def period_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📅 Сегодня"),   KeyboardButton(text="📅 Вчера")],
        [KeyboardButton(text="📅 7 дней"),    KeyboardButton(text="📅 За всё время")],
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True)


# ──────────────────────────────────────────────
# ОЦЕНКИ (СВЕТОФОР)
# ──────────────────────────────────────────────

def rate_higher_better(value: float, metric: str, platform: str = "uni"):
    n = NORMS.get(platform, NORMS["uni"])
    if metric not in n:
        return "⏳", "мало данных"
    low, high = n[metric]
    if value >= high:
        return "🟢", "отлично"
    if value >= low:
        return "🟡", "нормально"
    return "🔴", "низкий"


def rate_lower_better(value: float, metric: str, platform: str = "uni"):
    n = NORMS.get(platform, NORMS["uni"])
    if metric not in n:
        return "⏳", "мало данных"
    low, high = n[metric]
    if value <= low:
        return "🟢", "отлично"
    if value <= high:
        return "🟡", "нормально"
    return "🔴", "дорого"


def rate_freq(freq: float):
    if freq <= 2.0:
        return "🟢", "норм"
    if freq <= 3.0:
        return "🟡", "аудитория выгорает"
    return "🔴", "аудитория выгорела"
