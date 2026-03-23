# 🤖 Товарный Бро — Рефакторинг

## Структура проекта

```
/root/bot/
├── main.py                  # Точка входа (запуск бота)
├── config.py                # Все настройки, константы, AI prompt
├── database.py              # Работа с JSON-хранилищем
├── sessions.py              # Сессионность (API ключи per-user)
├── migrate.sh               # Скрипт миграции
├── .env                     # Переменные окружения (не коммитить!)
│
├── services/
│   ├── __init__.py
│   ├── ai_service.py        # Мульти-провайдерный AI (DeepSeek/Groq/Gemini)
│   ├── tiktok_api.py        # TikTok Ads API (с авто-refresh токена)
│   └── facebook_api.py      # Facebook Ads API
│
├── handlers/
│   ├── __init__.py
│   ├── settings.py          # ⚙️ Настройки API ключей per-user (НОВОЕ)
│   └── ... (остальные хендлеры переносятся сюда постепенно)
│
├── utils/
│   ├── __init__.py
│   └── helpers.py           # Парсинг, форматирование, клавиатуры, светофор
│
├── data/
│   ├── user_data.json       # Планы и связки
│   ├── products.json        # Товары
│   ├── reminders.json       # Напоминания
│   └── sessions.json        # API ключи пользователей (изолированно)
│
└── ad_bot_legacy.py         # Оригинальный файл (переименованный ad_bot.py)
```

## Что изменилось

### 1. Сессионность (главная новинка)
Каждый пользователь может подключить **свои** API ключи:
- TikTok Ads (advertiser_id + access_token)
- Facebook Ads (ad_account_id + access_token)
- AI провайдеры (deepseek / groq / gemini)

Кнопка **⚙️ Настройки API** в главном меню.  
Если ключей нет — используются owner-ключи из config.py.  
Данные каждого юзера изолированы в `data/sessions.json`.

### 2. Безопасность
- Все API ключи вынесены в `config.py` (единое место)
- `.env` шаблон для хранения ключей вне кода
- Данные пользователей разнесены в `data/` директорию

### 3. Модульность
- `services/` — вся бизнес-логика (API, AI) без зависимости от Telegram
- `handlers/` — только Telegram хендлеры
- `utils/helpers.py` — утилиты без побочных эффектов
- Легко тестировать каждый модуль отдельно

### 4. TikTok API — user-aware
Все функции принимают `user_id` и автоматически используют нужные credentials.  
Авто-refresh токена работает отдельно для каждого пользователя.

## Запуск

```bash
# Установка зависимостей
pip install aiogram aiohttp pytrends

# Настройка переменных (опционально)
cp .env.example .env
nano .env

# Запуск
pkill -f ad_bot_legacy.py 2>/dev/null || true
nohup python3 main.py > bot.log 2>&1 &
tail -f bot.log
```

## Миграция шаг за шагом

1. Загрузи новые файлы на сервер в `/root/bot/`
2. Запусти `bash migrate.sh`
3. Переименуй: `mv ad_bot.py ad_bot_legacy.py`
4. Запусти `python3 main.py`
5. Постепенно переноси хендлеры из `ad_bot_legacy.py` в `handlers/*.py`

## Дальнейший рефакторинг (следующие этапы)

После проверки что всё работает:

```
handlers/
  start.py           — /start, отмена, главное меню
  unit_economics.py  — 📊 Юнит-экономика (FSM UnitEcon)
  analyze.py         — 📈 Анализ связки (FSM Analyze)
  campaigns.py       — 🔗 Привязка кампаний
  products.py        — Отбор товаров (FSM ProductCheck, DemandCheck)
  plans.py           — 📋 Мои планы / связки
  ai_chat.py         — 🤖 AI чат (FSM AIChat)
  dashboards.py      — 🎵 TikTok / 📘 Facebook дашборды
  alerts.py          — ⏰ Уведомления + alert_loop
```
