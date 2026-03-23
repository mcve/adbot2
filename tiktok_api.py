"""
services/tiktok_api.py — TikTok Ads API.

Все функции принимают user_id и берут credentials через sessions.py.
"""

import json
import logging
import aiohttp
from datetime import datetime, timedelta, timezone

MINSK_TZ = timezone(timedelta(hours=3))


def _today_minsk():
    return datetime.now(MINSK_TZ).date()


def _date_range(preset: str):
    today = _today_minsk()
    p = preset.lower()
    if p in ("today", "сегодня"):
        return today.isoformat(), today.isoformat()
    if p in ("yesterday", "вчера"):
        d = (today - timedelta(days=1)).isoformat()
        return d, d
    if p in ("last_7d", "7 дней"):
        return (today - timedelta(days=6)).isoformat(), today.isoformat()
    if p in ("last_30d", "30 дней"):
        return (today - timedelta(days=29)).isoformat(), today.isoformat()
    return today.isoformat(), today.isoformat()


def _get_creds(user_id: int) -> dict:
    from sessions import get_tt_creds
    return get_tt_creds(user_id)


# ──────────────────────────────────────────────
# TOKEN REFRESH (per-user token store in memory)
# ──────────────────────────────────────────────

# Хранилище токенов в памяти (ключ = user_id или "owner")
_token_store: dict = {}


def _token_key(user_id) -> str:
    return str(user_id) if user_id else "owner"


def get_access_token(user_id) -> str:
    key = _token_key(user_id)
    if key in _token_store:
        return _token_store[key]["access_token"]
    creds = _get_creds(user_id)
    _token_store[key] = {
        "access_token": creds["access_token"],
        "refresh_token": creds.get("refresh_token", ""),
    }
    return _token_store[key]["access_token"]


async def refresh_token(user_id) -> bool:
    key = _token_key(user_id)
    creds = _get_creds(user_id)
    store = _token_store.get(key, {})
    refresh_tok = store.get("refresh_token", "")
    if not refresh_tok or refresh_tok == "ТВОЙ_REFRESH_TOKEN":
        return False

    url = "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/"
    data = {
        "app_id":        creds["app_id"],
        "secret":        creds["app_secret"],
        "grant_type":    "refresh_token",
        "refresh_token": refresh_tok,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as resp:
                res = await resp.json()
                if res.get("code") == 0:
                    new_data = res["data"]
                    _token_store[key] = {
                        "access_token": new_data["access_token"],
                        "refresh_token": new_data.get("refresh_token", refresh_tok),
                    }
                    logging.info(f"✅ TikTok token refreshed for {key}")
                    return True
                logging.error(f"TT refresh error: {res}")
                return False
    except Exception as e:
        logging.error(f"TT refresh exception: {e}")
        return False


async def _get(user_id, url: str, params: dict) -> dict:
    """Выполняет GET с авто-refresh при 401."""
    token = get_access_token(user_id)
    headers = {"Access-Token": token}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params,
                                   timeout=aiohttp.ClientTimeout(total=30)) as resp:
                text = await resp.text()
                try:
                    res = json.loads(text)
                except Exception:
                    return {"ok": False, "error": text[:200]}

                if res.get("code") in (40100, 40104, 40105):
                    refreshed = await refresh_token(user_id)
                    if refreshed:
                        headers["Access-Token"] = get_access_token(user_id)
                        async with session.get(url, headers=headers, params=params) as resp2:
                            res = json.loads(await resp2.text())
                    else:
                        return {"ok": False, "error": "token_expired"}

                if res.get("code") == 0:
                    return {"ok": True, "data": res.get("data", {})}
                return {"ok": False, "error": res.get("message", "unknown")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ──────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────

async def get_campaigns(user_id) -> dict:
    creds = _get_creds(user_id)
    url = "https://business-api.tiktok.com/open_api/v1.3/campaign/get/"
    params = {
        "advertiser_id": creds["advertiser_id"],
        "page": 1,
        "page_size": 50,
    }
    result = await _get(user_id, url, params)
    if result["ok"]:
        return {"ok": True, "data": result["data"].get("list", [])}
    return result


async def get_campaign_insights(user_id, campaign_id, preset="today") -> dict:
    creds = _get_creds(user_id)
    start_date, end_date = _date_range(preset)
    logging.info(f"TT campaign insights: camp={campaign_id}, {start_date}..{end_date}")

    url = "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"
    base_params = {
        "advertiser_id": creds["advertiser_id"],
        "service_type": "AUCTION",
        "report_type": "BASIC",
        "data_level": "AUCTION_CAMPAIGN",
        "dimensions": json.dumps(["campaign_id"]),
        "start_date": start_date,
        "end_date": end_date,
        "filtering": json.dumps([{
            "field_name": "campaign_ids",
            "filter_type": "IN",
            "filter_value": json.dumps([str(campaign_id)]),
        }]),
        "page": 1,
        "page_size": 10,
    }

    result_metrics = {}
    try:
        async with aiohttp.ClientSession() as session:
            token = get_access_token(user_id)
            headers = {"Access-Token": token}

            p1 = {**base_params, "metrics": json.dumps(["spend", "impressions", "clicks", "cpc", "ctr", "cpm"])}
            async with session.get(url, headers=headers, params=p1) as r:
                res1 = await r.json()
                if res1.get("code") == 0:
                    lst = res1.get("data", {}).get("list", [])
                    if lst:
                        result_metrics = lst[0].get("metrics", {})

            p2 = {**base_params, "metrics": json.dumps(["real_time_conversion", "real_time_cost_per_conversion"])}
            async with session.get(url, headers=headers, params=p2) as r:
                res2 = await r.json()
                if res2.get("code") == 0:
                    lst2 = res2.get("data", {}).get("list", [])
                    if lst2:
                        m = lst2[0].get("metrics", {})
                        result_metrics["conversion"] = m.get("real_time_conversion", "0")
                        result_metrics["cost_per_conversion"] = m.get("real_time_cost_per_conversion", "0")

        result_metrics.setdefault("conversion", "0")
        if result_metrics:
            return {"ok": True, "data": result_metrics}
        return {"ok": False, "data": {}}
    except Exception as e:
        logging.error(f"TT campaign insights error: {e}")
        return {"ok": False, "error": str(e)}


async def get_adgroup_insights(user_id, campaign_id, preset="today") -> list:
    """Возвращает список adgroup-статистик для кампании."""
    creds = _get_creds(user_id)
    start_date, end_date = _date_range(preset)

    url = "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"
    base_params = {
        "advertiser_id": creds["advertiser_id"],
        "service_type": "AUCTION",
        "report_type": "BASIC",
        "data_level": "AUCTION_ADGROUP",
        "dimensions": json.dumps(["adgroup_id"]),
        "start_date": start_date,
        "end_date": end_date,
        "filtering": json.dumps([{
            "field_name": "campaign_ids",
            "filter_type": "IN",
            "filter_value": json.dumps([str(campaign_id)]),
        }]),
        "page": 1,
        "page_size": 50,
    }

    try:
        token = get_access_token(user_id)
        headers = {"Access-Token": token}

        async with aiohttp.ClientSession() as session:
            # Метрики
            p1 = {**base_params, "metrics": json.dumps([
                "spend", "impressions", "clicks", "cpc", "ctr", "cpm",
                "real_time_conversion", "real_time_cost_per_conversion",
            ])}
            async with session.get(url, headers=headers, params=p1,
                                   timeout=aiohttp.ClientTimeout(total=30)) as resp:
                res = await resp.json()

            if res.get("code") != 0:
                logging.error(f"TT adgroup insights error: {res.get('message')}")
                return []

            metrics_list = res.get("data", {}).get("list", [])
            adgroup_ids = [row["dimensions"]["adgroup_id"] for row in metrics_list]
            if not adgroup_ids:
                return []

            # Имена и статусы
            names_url = "https://business-api.tiktok.com/open_api/v1.3/adgroup/get/"
            names_params = {
                "advertiser_id": creds["advertiser_id"],
                "filtering": json.dumps({"campaign_ids": [str(campaign_id)]}),
                "fields": json.dumps(["adgroup_id", "adgroup_name", "status", "budget"]),
                "page_size": 50,
            }
            async with session.get(names_url, headers=headers, params=names_params,
                                   timeout=aiohttp.ClientTimeout(total=15)) as resp2:
                names_res = await resp2.json()

            name_map = {}
            budget_map = {}
            status_map = {}
            if names_res.get("code") == 0:
                for ag in names_res.get("data", {}).get("list", []):
                    aid = ag.get("adgroup_id")
                    name_map[aid]   = ag.get("adgroup_name", f"adgroup_{aid}")
                    budget_map[aid] = float(ag.get("budget", 0))
                    status_map[aid] = ag.get("status", "ENABLE")

        result = []
        for row in metrics_list:
            aid = row["dimensions"]["adgroup_id"]
            m = row.get("metrics", {})
            spend = float(m.get("spend", 0))
            imp   = int(m.get("impressions", 0))
            clicks = int(m.get("clicks", 0))
            ctr   = float(m.get("ctr", 0))
            cpc   = float(m.get("cpc", 0))
            leads = int(float(m.get("real_time_conversion", 0)))
            cpl   = float(m.get("real_time_cost_per_conversion", 0))
            status = status_map.get(aid, "ENABLE")
            result.append({
                "id":        aid,
                "name":      name_map.get(aid, f"adgroup_{aid}"),
                "spend":     spend,
                "impressions": imp,
                "clicks":    clicks,
                "ctr":       ctr,
                "cpc":       cpc,
                "leads":     leads,
                "cpl":       cpl,
                "budget":    budget_map.get(aid, 0),
                "is_active": status in ("ENABLE", "ACTIVE"),
            })
        return result

    except Exception as e:
        logging.error(f"TT adgroup insights exception: {e}")
        return []


async def get_report(user_id, date_range="LAST_7_DAYS") -> dict:
    creds = _get_creds(user_id)
    today = _today_minsk()
    if date_range == "TODAY":
        start_date = end_date = today.isoformat()
    else:
        start_date = (today - timedelta(days=6)).isoformat()
        end_date   = today.isoformat()

    url = "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"
    params = {
        "advertiser_id": creds["advertiser_id"],
        "service_type": "AUCTION",
        "report_type": "BASIC",
        "data_level": "AUCTION_CAMPAIGN",
        "dimensions": json.dumps(["campaign_id"]),
        "metrics": json.dumps(["spend", "impressions", "clicks", "cpc", "ctr", "cpm"]),
        "start_date": start_date,
        "end_date": end_date,
        "page": 1,
        "page_size": 20,
    }
    result = await _get(user_id, url, params)
    if result["ok"]:
        return {"ok": True, "data": result["data"].get("list", [])}
    return result
