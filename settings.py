"""
handlers/settings.py — настройка API ключей пользователя.

Позволяет каждому пользователю подключить свои:
  - TikTok Ads API
  - Facebook Ads API
  - AI провайдеры
Без настройки используются owner-ключи из config.py.
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from sessions import (
    get_session, set_session_field, delete_session,
    has_custom_tt, has_custom_fb,
)
from utils.helpers import main_kb, cancel_kb

router = Router()


class SettingsState(StatesGroup):
    menu         = State()
    tt_token     = State()
    tt_adv_id    = State()
    fb_token     = State()
    fb_account   = State()
    ai_provider  = State()
    ai_key_input = State()


def settings_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🎵 Настроить TikTok API")],
        [KeyboardButton(text="📘 Настроить Facebook API")],
        [KeyboardButton(text="🤖 Настроить AI ключ")],
        [KeyboardButton(text="🗑 Сбросить мои ключи")],
        [KeyboardButton(text="📋 Показать статус")],
        [KeyboardButton(text="❌ Отмена")],
    ], resize_keyboard=True)


@router.message(F.text == "⚙️ Настройки API")
async def settings_start(message: types.Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    tt_ok = "✅" if has_custom_tt(uid) else "⬜"
    fb_ok = "✅" if has_custom_fb(uid) else "⬜"
    s = get_session(uid)
    ai_ok = "✅" if (s.get("deepseek_api_key") or s.get("groq_api_key") or s.get("gemini_api_key")) else "⬜"

    await message.answer(
        f"⚙️ <b>Настройки API</b>\n\n"
        f"Подключи свои API ключи чтобы бот работал с твоими кабинетами.\n"
        f"Без настройки используются owner-ключи.\n\n"
        f"{tt_ok} TikTok Ads API\n"
        f"{fb_ok} Facebook Ads API\n"
        f"{ai_ok} AI провайдер\n\n"
        f"Выбери что настроить:",
        parse_mode="HTML",
        reply_markup=settings_kb(),
    )
    await state.set_state(SettingsState.menu)


@router.message(F.text == "📋 Показать статус")
async def settings_status(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    s = get_session(uid)

    lines = ["⚙️ <b>Текущие настройки:</b>\n"]

    # TikTok
    if s.get("tt_access_token"):
        lines.append(f"🎵 TikTok: ✅ подключён")
        lines.append(f"   Advertiser ID: <code>{s.get('tt_advertiser_id', '—')}</code>")
        tok = s['tt_access_token']
        lines.append(f"   Token: <code>{tok[:8]}...{tok[-4:]}</code>")
    else:
        lines.append("🎵 TikTok: owner-ключи")

    lines.append("")

    # Facebook
    if s.get("fb_access_token"):
        lines.append(f"📘 Facebook: ✅ подключён")
        lines.append(f"   Account ID: <code>{s.get('fb_ad_account_id', '—')}</code>")
        tok = s['fb_access_token']
        lines.append(f"   Token: <code>{tok[:8]}...{tok[-4:]}</code>")
    else:
        lines.append("📘 Facebook: owner-ключи")

    lines.append("")

    # AI
    for provider, field in [("DeepSeek", "deepseek_api_key"), ("Groq", "groq_api_key"), ("Gemini", "gemini_api_key")]:
        if s.get(field):
            key = s[field]
            lines.append(f"🤖 {provider}: ✅ <code>{key[:8]}...{key[-4:]}</code>")

    if not any(s.get(f) for f in ("deepseek_api_key", "groq_api_key", "gemini_api_key")):
        lines.append("🤖 AI: owner-ключи")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=settings_kb())


# ── TikTok ──

@router.message(F.text == "🎵 Настроить TikTok API")
async def settings_tt_start(message: types.Message, state: FSMContext):
    await message.answer(
        "🎵 <b>TikTok Ads API</b>\n\n"
        "Введи <b>Access Token</b> из TikTok Business Center:\n"
        "<i>Business Center → Assets → API ключи → сгенерировать токен</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await state.set_state(SettingsState.tt_token)


@router.message(SettingsState.tt_token)
async def settings_tt_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    if len(token) < 20:
        await message.answer("❌ Слишком короткий токен. Проверь и попробуй снова:")
        return
    await state.update_data(tt_access_token=token)
    await message.answer(
        "✅ Токен сохранён.\n\n"
        "Теперь введи <b>Advertiser ID</b>:\n"
        "<i>Business Center → Account → Advertiser ID</i>",
        parse_mode="HTML",
    )
    await state.set_state(SettingsState.tt_adv_id)


@router.message(SettingsState.tt_adv_id)
async def settings_tt_adv(message: types.Message, state: FSMContext):
    adv_id = message.text.strip()
    if not adv_id.isdigit():
        await message.answer("❌ Advertiser ID — только цифры:")
        return
    d = await state.get_data()
    uid = message.from_user.id
    set_session_field(uid, "tt_access_token", d["tt_access_token"])
    set_session_field(uid, "tt_advertiser_id", adv_id)
    await message.answer(
        "✅ <b>TikTok API подключён!</b>\n\n"
        "Теперь дашборд TikTok будет работать с твоим кабинетом.",
        parse_mode="HTML",
        reply_markup=settings_kb(),
    )
    await state.set_state(SettingsState.menu)


# ── Facebook ──

@router.message(F.text == "📘 Настроить Facebook API")
async def settings_fb_start(message: types.Message, state: FSMContext):
    await message.answer(
        "📘 <b>Facebook Ads API</b>\n\n"
        "Введи <b>Access Token</b>:\n"
        "<i>developers.facebook.com → Tools → Graph API Explorer → Generate Token</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await state.set_state(SettingsState.fb_token)


@router.message(SettingsState.fb_token)
async def settings_fb_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    if len(token) < 20:
        await message.answer("❌ Слишком короткий токен:")
        return
    await state.update_data(fb_access_token=token)
    await message.answer(
        "✅ Токен сохранён.\n\n"
        "Введи <b>Ad Account ID</b>:\n"
        "<i>Формат: act_123456789 (или просто цифры)</i>",
        parse_mode="HTML",
    )
    await state.set_state(SettingsState.fb_account)


@router.message(SettingsState.fb_account)
async def settings_fb_account(message: types.Message, state: FSMContext):
    account = message.text.strip()
    if not account.startswith("act_"):
        account = f"act_{account.lstrip('act_')}"
    d = await state.get_data()
    uid = message.from_user.id
    set_session_field(uid, "fb_access_token", d["fb_access_token"])
    set_session_field(uid, "fb_ad_account_id", account)
    await message.answer(
        "✅ <b>Facebook API подключён!</b>\n\n"
        f"Account ID: <code>{account}</code>",
        parse_mode="HTML",
        reply_markup=settings_kb(),
    )
    await state.set_state(SettingsState.menu)


# ── AI ──

@router.message(F.text == "🤖 Настроить AI ключ")
async def settings_ai_start(message: types.Message, state: FSMContext):
    await message.answer(
        "🤖 <b>AI провайдер</b>\n\nВыбери провайдер:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="DeepSeek"), KeyboardButton(text="Groq")],
            [KeyboardButton(text="Gemini")],
            [KeyboardButton(text="❌ Отмена")],
        ], resize_keyboard=True),
    )
    await state.set_state(SettingsState.ai_provider)


@router.message(SettingsState.ai_provider)
async def settings_ai_provider(message: types.Message, state: FSMContext):
    t = message.text.strip().lower()
    if "deepseek" in t:
        provider, field = "DeepSeek", "deepseek_api_key"
        url = "platform.deepseek.com → API Keys"
    elif "groq" in t:
        provider, field = "Groq", "groq_api_key"
        url = "console.groq.com → API Keys"
    elif "gemini" in t:
        provider, field = "Gemini", "gemini_api_key"
        url = "aistudio.google.com/apikey"
    else:
        await message.answer("❌ Выбери провайдер кнопкой:")
        return

    await state.update_data(ai_provider=provider, ai_field=field)
    await message.answer(
        f"🤖 <b>{provider}</b>\n\n"
        f"Введи API ключ:\n<i>{url}</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await state.set_state(SettingsState.ai_key_input)


@router.message(SettingsState.ai_key_input)
async def settings_ai_key(message: types.Message, state: FSMContext):
    key = message.text.strip()
    if len(key) < 10:
        await message.answer("❌ Ключ слишком короткий:")
        return
    d = await state.get_data()
    set_session_field(message.from_user.id, d["ai_field"], key)
    await message.answer(
        f"✅ <b>{d['ai_provider']} подключён!</b>",
        parse_mode="HTML",
        reply_markup=settings_kb(),
    )
    await state.set_state(SettingsState.menu)


# ── Сброс ──

@router.message(F.text == "🗑 Сбросить мои ключи")
async def settings_reset(message: types.Message, state: FSMContext):
    delete_session(message.from_user.id)
    await state.clear()
    await message.answer(
        "✅ Все твои API ключи удалены.\n"
        "Бот вернулся к owner-ключам.",
        reply_markup=main_kb(),
    )
