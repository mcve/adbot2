"""
services/facebook_api.py — Facebook Ads API.
"""

import json
import logging
import aiohttp
from config import FB_API_VERSION


def _get_creds(user_id: int) -> dict:
    from sessions import get_fb_creds
    return get_fb_creds(user_id)


def _base_url(ad_account_id: str) -> str:
    return f"https://graph.facebook.com/{FB_API_VERSION}/{ad_account_id}"


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def extract_leads(actions: list) -> int:
    if not actions:
        return 0
    for action in actions:
        if action.get("action_type") in (
            "lead",
            "onsite_conversion.lead_grouped",
            "offsite_conversion.fb_pixel_lead",
        ):
            return int(action.get("value", 0))
    return 0


def extract_purchases(actions: list) -> int:
    if not actions:
        return 0
    for action in actions:
        if action.get("action_type") in ("purchase", "offsite_conversion.fb_pixel_purchase"):
            return int(action.get("value", 0))
    return 0


# ──────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────

async def get_insights(
    user_id: int,
    date_preset: str = None,
    since: str = None,
    until: str = None,
    level: str = "account",
) -> dict:
    creds = _get_creds(user_id)
    params = {
        "access_token": creds["access_token"],
        "fields": "spend,impressions,clicks,cpc,ctr,cpm,actions,cost_per_action_type,campaign_name,frequency",
        "level": level,
    }
    if date_preset:
        params["date_preset"] = date_preset
    elif since and until:
        params["time_range"] = json.dumps({"since": since, "until": until})

    url = f"{_base_url(creds['ad_account_id'])}/insights"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params,
                                   timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"ok": True, "data": data.get("data", [])}
                error = await resp.text()
                logging.error(f"FB API error {resp.status}: {error}")
                return {"ok": False, "error": f"HTTP {resp.status}"}
    except Exception as e:
        logging.error(f"FB API exception: {e}")
        return {"ok": False, "error": str(e)}


async def get_campaigns(user_id: int, date_preset: str = "today") -> dict:
    return await get_insights(user_id, date_preset=date_preset, level="campaign")


async def get_active_campaigns(user_id: int) -> dict:
    creds = _get_creds(user_id)
    url = f"{_base_url(creds['ad_account_id'])}/campaigns"
    params = {
        "access_token": creds["access_token"],
        "fields": "name,status,objective,daily_budget,lifetime_budget",
        "filtering": json.dumps([{
            "field": "effective_status",
            "operator": "IN",
            "value": ["ACTIVE", "PAUSED"],
        }]),
        "limit": 50,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params,
                                   timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"ok": True, "data": data.get("data", [])}
                return {"ok": False, "error": f"HTTP {resp.status}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def get_campaign_insights(user_id: int, campaign_id: str, date_preset: str = "last_7d") -> dict:
    creds = _get_creds(user_id)
    url = f"https://graph.facebook.com/{FB_API_VERSION}/{campaign_id}/insights"
    params = {
        "access_token": creds["access_token"],
        "fields": "spend,impressions,clicks,cpc,ctr,cpm,actions,cost_per_action_type,frequency",
        "date_preset": date_preset,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params,
                                   timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"ok": True, "data": data.get("data", [])}
                return {"ok": False, "error": f"HTTP {resp.status}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ──────────────────────────────────────────────
# ФОРМАТИРОВАНИЕ
# ──────────────────────────────────────────────

def build_report(data_list: list, title: str = "📊 Facebook Ads") -> str:
    if not data_list:
        return f"{title}\n\n😐 Нет данных за этот период."

    total_spend = sum(float(r.get("spend", 0)) for r in data_list)
    total_imp   = sum(int(r.get("impressions", 0)) for r in data_list)
    total_clicks = sum(int(r.get("clicks", 0)) for r in data_list)
    total_leads  = sum(extract_leads(r.get("actions")) for r in data_list)
    total_purchases = sum(extract_purchases(r.get("actions")) for r in data_list)

    ctr = (total_clicks / total_imp * 100) if total_imp > 0 else 0
    cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
    cpm = (total_spend / total_imp * 1000) if total_imp > 0 else 0
    cpl = (total_spend / total_leads) if total_leads > 0 else 0

    ctr_e = "🟢" if ctr >= 1.5 else ("🟡" if ctr >= 0.8 else "🔴")
    cpc_e = "🟢" if cpc <= 0.15 else ("🟡" if cpc <= 0.5 else "🔴")
    cpm_e = "🟢" if cpm <= 3 else ("🟡" if cpm <= 8 else "🔴")

    report = (
        f"📘 <b>{title}</b>\n\n"
        f"━━━ 💰 РАСХОДЫ ━━━\n"
        f"💵 Потрачено: <b>${total_spend:.2f}</b>\n\n"
        f"━━━ 📊 ПОКАЗАТЕЛИ ━━━\n"
        f"👁 Показы: <b>{total_imp:,}</b>\n"
        f"🖱 Клики: <b>{total_clicks:,}</b>\n"
        f"{ctr_e} CTR: <b>{ctr:.2f}%</b>\n"
        f"{cpc_e} CPC: <b>${cpc:.2f}</b>\n"
        f"{cpm_e} CPM: <b>${cpm:.2f}</b>"
    )
    if total_leads > 0:
        report += f"\n\n━━━ 📝 КОНВЕРСИИ ━━━\n📝 Лиды: <b>{total_leads}</b>\n💰 CPL: <b>${cpl:.2f}</b>"
    if total_purchases > 0:
        cpp = total_spend / total_purchases
        report += f"\n🛒 Покупки: <b>{total_purchases}</b>\n💰 CPA: <b>${cpp:.2f}</b>"

    if data_list:
        d_start = data_list[0].get("date_start", "")
        d_stop  = data_list[0].get("date_stop", "")
        if d_start and d_stop:
            report += f"\n\n📅 {d_start} — {d_stop}"
    return report
