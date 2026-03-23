"""
database.py — работа с JSON-хранилищем.

Все файловые операции централизованы здесь.
Структура user_data.json:
  { "user_id": { "plans": {...}, "bundles": {...} } }
"""

import json
import os
import logging
from datetime import datetime
from config import DATA_FILE, PRODUCTS_FILE, REMINDERS_FILE, DATA_DIR


# ──────────────────────────────────────────────
# БАЗОВЫЕ ОПЕРАЦИИ
# ──────────────────────────────────────────────

def _load(path: str) -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(path: str, data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
# ПОЛЬЗОВАТЕЛИ / ПЛАНЫ / СВЯЗКИ
# ──────────────────────────────────────────────

def load_data() -> dict:
    return _load(DATA_FILE)


def save_data(data: dict):
    _save(DATA_FILE, data)


def get_user(user_id: int) -> dict:
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"plans": {}, "bundles": {}}
        save_data(data)
    return data[uid]


# ── Планы ──

def save_plan(user_id: int, name: str, plan: dict):
    data = load_data()
    uid = str(user_id)
    data.setdefault(uid, {"plans": {}, "bundles": {}})
    data[uid].setdefault("plans", {})
    plan["created"] = datetime.now().strftime("%d.%m.%Y")
    data[uid]["plans"][name] = plan
    save_data(data)


def get_plans(user_id: int) -> dict:
    return get_user(user_id).get("plans", {})


def delete_plan(user_id: int, name: str) -> bool:
    data = load_data()
    uid = str(user_id)
    if uid in data and "plans" in data[uid] and name in data[uid]["plans"]:
        del data[uid]["plans"][name]
        save_data(data)
        return True
    return False


def save_plan_campaigns(user_id: int, plan_name: str, campaigns: list) -> bool:
    data = load_data()
    uid = str(user_id)
    try:
        data[uid]["plans"][plan_name]["linked_campaigns"] = campaigns
        save_data(data)
        return True
    except (KeyError, TypeError):
        return False


def get_plan_campaigns(user_id: int, plan_name: str) -> list:
    plans = get_plans(user_id)
    return plans.get(plan_name, {}).get("linked_campaigns", [])


# ── Связки ──

def save_bundle(user_id: int, name: str, bundle: dict):
    data = load_data()
    uid = str(user_id)
    data.setdefault(uid, {"plans": {}, "bundles": {}})
    data[uid].setdefault("bundles", {})

    bundle["date"] = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Сохраняем историю
    if name in data[uid]["bundles"]:
        old = data[uid]["bundles"][name]
        history = old.get("history", [])
        snapshot = {k: old.get(k) for k in [
            "date", "spend", "impressions", "clicks", "leads",
            "confirmed", "frequency", "ctr", "cpm", "cpc",
            "cr", "cpl", "verdict_emoji",
        ]}
        history.append(snapshot)
        if len(history) > 20:
            history = history[-20:]
        bundle["history"] = history
    else:
        bundle["history"] = []

    data[uid]["bundles"][name] = bundle
    save_data(data)


def get_bundles(user_id: int) -> dict:
    return get_user(user_id).get("bundles", {})


def delete_bundle(user_id: int, name: str) -> bool:
    data = load_data()
    uid = str(user_id)
    if uid in data and "bundles" in data[uid] and name in data[uid]["bundles"]:
        del data[uid]["bundles"][name]
        save_data(data)
        return True
    return False


# ──────────────────────────────────────────────
# ТОВАРЫ
# ──────────────────────────────────────────────

def load_products() -> dict:
    return _load(PRODUCTS_FILE)


def save_products(data: dict):
    _save(PRODUCTS_FILE, data)


def save_product(user_id: int, name: str, product_data: dict):
    data = load_products()
    uid = str(user_id)
    data.setdefault(uid, {})
    product_data["updated"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    data[uid][name] = product_data
    save_products(data)


def get_products(user_id: int) -> dict:
    return load_products().get(str(user_id), {})


def delete_product(user_id: int, name: str) -> bool:
    data = load_products()
    uid = str(user_id)
    if uid in data and name in data[uid]:
        del data[uid][name]
        save_products(data)
        return True
    return False


def update_product_field(user_id: int, name: str, field: str, value) -> bool:
    data = load_products()
    uid = str(user_id)
    if uid in data and name in data[uid]:
        data[uid][name][field] = value
        data[uid][name]["updated"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        save_products(data)
        return True
    return False


# ──────────────────────────────────────────────
# НАПОМИНАНИЯ
# ──────────────────────────────────────────────

def save_reminder(user_id: int, reminder_data: dict):
    data = _load(REMINDERS_FILE)
    data[str(user_id)] = reminder_data
    _save(REMINDERS_FILE, data)


def get_reminders() -> dict:
    return _load(REMINDERS_FILE)


def delete_reminder(user_id: int):
    data = _load(REMINDERS_FILE)
    data.pop(str(user_id), None)
    _save(REMINDERS_FILE, data)
