"""
services/ai_service.py — Мульти-провайдерный AI.

Порядок: DeepSeek → Groq → Gemini.
Поддерживает пользовательские ключи через sessions.py.
"""

import re
import json
import logging
import aiohttp
from config import AI_SYSTEM_PROMPT


def _clean_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = text.replace("##", "").replace("# ", "")
    text = text.replace("```", "").replace("`", "")
    text = re.sub(r'<[^>]+>', '', text)
    return text


async def _ask_deepseek(message: str, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "error": "no_key"}
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        "max_tokens": 2000,
        "temperature": 0.7,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload,
                                    timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status == 200:
                    data = json.loads(await resp.text())
                    text = _clean_markdown(data["choices"][0]["message"]["content"])
                    return {"ok": True, "text": text, "provider": "DeepSeek"}
                body = await resp.text()
                logging.error(f"DeepSeek {resp.status}: {body[:100]}")
                return {"ok": False, "error": f"http_{resp.status}"}
    except Exception as e:
        logging.error(f"DeepSeek exception: {e}")
        return {"ok": False, "error": str(e)}


async def _ask_groq(message: str, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "error": "no_key"}
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        "max_tokens": 2000,
        "temperature": 0.7,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload,
                                    timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = _clean_markdown(data["choices"][0]["message"]["content"])
                    return {"ok": True, "text": text, "provider": "Groq"}
                return {"ok": False, "error": f"http_{resp.status}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _ask_gemini(message: str, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "error": "no_key"}
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-2.0-flash:generateContent?key={api_key}")
    payload = {
        "contents": [{"parts": [{"text": AI_SYSTEM_PROMPT + "\n\n" + message}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000},
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload,
                                    timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            text = _clean_markdown(parts[0].get("text", ""))
                            return {"ok": True, "text": text, "provider": "Gemini"}
                    return {"ok": False, "error": "empty_response"}
                return {"ok": False, "error": f"http_{resp.status}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ──────────────────────────────────────────────
# PUBLIC
# ──────────────────────────────────────────────

async def ai_ask(
    user_message: str,
    context: str = "",
    history: list = None,
    user_id: int = None,
) -> str:
    """
    Задаёт вопрос AI. Пробует DeepSeek → Groq → Gemini.
    Если передан user_id — использует его ключи (через sessions).
    """
    # Получаем ключи
    if user_id:
        from sessions import get_ai_keys
        keys = get_ai_keys(user_id)
    else:
        from config import DEEPSEEK_API_KEY, GROQ_API_KEY, GEMINI_API_KEY
        keys = {"deepseek": DEEPSEEK_API_KEY, "groq": GROQ_API_KEY, "gemini": GEMINI_API_KEY}

    # Формируем полное сообщение
    analysis_keywords = [
        "анализ", "отчёт", "отчет", "как дела", "как идёт", "как идет",
        "статистик", "связк", "кампани", "расход", "cpl", "ctr", "лиды",
        "лидов", "масштаб", "оптимиз",
    ]
    is_analysis = any(kw in user_message.lower() for kw in analysis_keywords)

    history_text = ""
    if history:
        for h in history[-6:]:
            role = "Пользователь" if h["role"] == "user" else "Ассистент"
            history_text += f"{role}: {h['text']}\n"

    if is_analysis and context:
        full_message = f"КОНТЕКСТ ДАННЫХ:\n{context}"
        if history_text:
            full_message += f"\n\nИСТОРИЯ ДИАЛОГА:\n{history_text}"
        full_message += f"\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_message}"
    elif context:
        clean_context = context.split("\n\nLIVE ДАННЫЕ РЕКЛАМЫ")[0]
        full_message = f"КОНТЕКСТ (справочно):\n{clean_context}"
        if history_text:
            full_message += f"\n\nИСТОРИЯ ДИАЛОГА:\n{history_text}"
        full_message += f"\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ (ответь ТОЛЬКО на этот вопрос):\n{user_message}"
    else:
        full_message = ""
        if history_text:
            full_message += f"ИСТОРИЯ ДИАЛОГА:\n{history_text}\n\n"
        full_message += user_message

    providers = [
        ("DeepSeek", _ask_deepseek, keys["deepseek"]),
        ("Groq",     _ask_groq,     keys["groq"]),
        ("Gemini",   _ask_gemini,   keys["gemini"]),
    ]

    errors = []
    for name, func, key in providers:
        result = await func(full_message, key)
        if result["ok"]:
            logging.info(f"AI response from {result['provider']}")
            return result["text"]
        if result["error"] != "no_key":
            errors.append(f"{name}: {result['error']}")
            logging.warning(f"AI {name} failed: {result['error']}")

    if errors:
        return "❌ AI недоступен:\n" + "\n".join(errors) + "\n\nПопробуй через минуту"
    return "❌ Нет API ключей. Заполни хотя бы один в настройках."
