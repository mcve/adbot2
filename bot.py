import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)

BOT_TOKEN = "8206698499:AAGmnFhnd3GPxTO3nO6DwkXk2IcW0UaEakE"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


async def get_exchange_rates() -> dict:
    rates = {"usd": None, "rub": None}
    try:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    "https://api.nbrb.by/exrates/rates/431",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        rates["usd"] = data.get("Cur_OfficialRate")
            except:
                pass
            try:
                async with session.get(
                    "https://api.nbrb.by/exrates/rates/456",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        r100 = data.get("Cur_OfficialRate")
                        if r100:
                            rates["rub"] = r100 / 100
            except:
                pass
    except Exception as e:
        logging.error(f"Ошибка курсов: {e}")
    return rates


class CS(StatesGroup):
    purchase_price_rub = State()
    confirm_rates = State()
    has_import_vat = State()
    has_ad_tax = State()
    has_profit_tax = State()
    landing_price = State()
    cross_sell_pct = State()
    upsell_pct = State()
    upsell_amount = State()
    buyout_pct = State()
    lead_cost_usd = State()
    agent_commission_pct = State()
    approval_pct = State()
    works_alone = State()
    call_center_cost = State()
    warehouse_cost = State()
    targetolog_cost = State()


def ynkb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]],
        resize_keyboard=True
    )

def startkb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📊 Рассчитать юнит-экономику")]],
        resize_keyboard=True
    )

def alonekb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Сам обрабатываю")],
            [KeyboardButton(text="📞 Есть колл-центр/менеджер")]
        ],
        resize_keyboard=True
    )

def pn(text):
    try:
        return float(text.strip().replace(",", ".").replace("%", "").replace("$", "").replace(" ", ""))
    except:
        return None

def pyn(text):
    t = text.strip().lower()
    if any(x in t for x in ["да", "yes", "✅"]):
        return True
    if any(x in t for x in ["нет", "no", "❌"]):
        return False
    return None


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 <b>Калькулятор юнит-экономики товарки</b>\n\n"
        "Бот рассчитает:\n"
        "• 💵 Чистую прибыль с 1 заказа\n"
        "• 📈 Рентабельность\n"
        "• 🎯 Макс. цену лида\n"
        "• 💡 Где сэкономить\n\n"
        "Курсы валют — автоматически с НБРБ.\n\n"
        "👇 Нажми кнопку",
        parse_mode="HTML",
        reply_markup=startkb()
    )


@dp.message(F.text == "📊 Рассчитать юнит-экономику")
async def start_calc(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("⏳ Загружаю курсы НБРБ...", reply_markup=ReplyKeyboardRemove())
    rates = await get_exchange_rates()
    if rates["usd"] and rates["rub"]:
        await state.update_data(usd_rate=rates["usd"], rub_rate=rates["rub"])
        await message.answer(
            f"✅ <b>Курсы НБРБ:</b>\n\n"
            f"💵 $1 = <b>{rates['usd']:.4f} BYN</b>\n"
            f"🪙 ₽1 = <b>{rates['rub']:.4f} BYN</b>\n\n"
            f"Актуальные?",
            parse_mode="HTML", reply_markup=ynkb()
        )
        await state.set_state(CS.confirm_rates)
    else:
        await state.update_data(step="waiting_rub")
        await message.answer(
            "⚠️ Не загрузились. Введи курс ₽ к BYN\n\nНапример: <code>0.037</code>",
            parse_mode="HTML"
        )
        await state.set_state(CS.confirm_rates)


@dp.message(CS.confirm_rates)
async def confirm_rates(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get("step") == "waiting_usd":
        v = pn(message.text)
        if not v or v <= 0:
            await message.answer("❌ Число. Например: <code>3.2</code>", parse_mode="HTML")
            return
        await state.update_data(usd_rate=v, step=None)
        await ask_purchase(message)
        await state.set_state(CS.purchase_price_rub)
        return
    if data.get("step") == "waiting_rub":
        v = pn(message.text)
        if not v or v <= 0:
            await message.answer("❌ Число. Например: <code>0.037</code>", parse_mode="HTML")
            return
        await state.update_data(rub_rate=v, step="waiting_usd")
        await message.answer("Теперь курс $ к BYN\n\nНапример: <code>3.2</code>", parse_mode="HTML")
        return
    yn = pyn(message.text)
    if yn is None:
        await message.answer("Нажми ✅ Да или ❌ Нет")
        return
    if yn:
        await ask_purchase(message)
        await state.set_state(CS.purchase_price_rub)
    else:
        await state.update_data(step="waiting_rub")
        await message.answer(
            "Введи курс ₽ к BYN\n\nНапример: <code>0.037</code>",
            parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
        )


async def ask_purchase(msg):
    await msg.answer(
        "━━━ 📦 ЗАКУПКА ━━━\n\n"
        "💰 <b>Цена закупки 1 ед. товара</b> в рос. рублях\n\n"
        "<i>Цена у поставщика (Садовод, Южные Ворота и т.д.)</i>\n\n"
        "Например: <code>650</code>",
        parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
    )


@dp.message(CS.purchase_price_rub)
async def get_purchase(message: types.Message, state: FSMContext):
    v = pn(message.text)
    if not v or v <= 0:
        await message.answer("❌ Число. Например: <code>650</code>", parse_mode="HTML")
        return
    await state.update_data(purchase_price_rub=v)
    d = await state.get_data()
    byn = v * d["rub_rate"]
    await message.answer(
        f"📦 Закупка: {v:.0f} ₽ = <b>{byn:.2f} BYN</b>\n\n"
        "━━━ 🏛 НАЛОГИ ━━━\n\n"
        "🏛 Платишь <b>ввозной НДС 20%</b>?\n\n"
        "<i>Если ввозишь официально через ИП/юрлицо — да.\n"
        "Серый ввоз — нет.</i>",
        parse_mode="HTML", reply_markup=ynkb()
    )
    await state.set_state(CS.has_import_vat)


@dp.message(CS.has_import_vat)
async def get_vat(message: types.Message, state: FSMContext):
    v = pyn(message.text)
    if v is None:
        await message.answer("✅ Да или ❌ Нет")
        return
    await state.update_data(has_import_vat=v)
    await message.answer(
        "📢 Платишь <b>налог на рекламу 20%</b>?\n\n"
        "<i>Через агента официально (напр, АйКонтекст) — да.\n"
        "Через крипту (напр, Бусты) — нет.</i>",
        parse_mode="HTML", reply_markup=ynkb()
    )
    await state.set_state(CS.has_ad_tax)


@dp.message(CS.has_ad_tax)
async def get_ad_tax(message: types.Message, state: FSMContext):
    v = pyn(message.text)
    if v is None:
        await message.answer("✅ Да или ❌ Нет")
        return
    await state.update_data(has_ad_tax=v)
    await message.answer(
        "💼 Платишь <b>налог на прибыль 20%</b>?\n\n"
        "<i>Если ИП/юрлицо на ОСН — да.\n"
        "Если без регистрации — нет.</i>",
        parse_mode="HTML", reply_markup=ynkb()
    )
    await state.set_state(CS.has_profit_tax)


@dp.message(CS.has_profit_tax)
async def get_ptax(message: types.Message, state: FSMContext):
    v = pyn(message.text)
    if v is None:
        await message.answer("✅ Да или ❌ Нет")
        return
    await state.update_data(has_profit_tax=v)
    await message.answer(
        "━━━ 🏷 ПРОДАЖИ ━━━\n\n"
        "🏷 <b>Цена на лендинге</b> (BYN)\n\n"
        "<i>Цена которую видит клиент. Без апсейлов/кроссейлов.</i>\n\n"
        "Например: <code>59.9</code>",
        parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(CS.landing_price)


@dp.message(CS.landing_price)
async def get_land(message: types.Message, state: FSMContext):
    v = pn(message.text)
    if not v or v <= 0:
        await message.answer("❌ Число", parse_mode="HTML")
        return
    await state.update_data(landing_price=v)
    await message.answer(
        "🔄 <b>% кроссейлов</b>\n\n"
        "<i>Кроссейл — клиент берёт доп. товар.\n"
        "33% = каждый 3-й берёт ещё один.\n"
        "Норма: 10-25%, топ: 50%+\n"
        "Если не делаешь — ставь 0.</i>\n\n"
        "Например: <code>33</code> или <code>0</code>",
        parse_mode="HTML"
    )
    await state.set_state(CS.cross_sell_pct)


@dp.message(CS.cross_sell_pct)
async def get_cross(message: types.Message, state: FSMContext):
    v = pn(message.text)
    if v is None or v < 0 or v > 100:
        await message.answer("❌ Число 0-100")
        return
    await state.update_data(cross_sell_pct=v / 100)
    await message.answer(
        "⬆️ <b>% апсейлов</b>\n\n"
        "<i>Апсейл — клиент берёт дороже (набор вместо 1 шт).\n"
        "Норма: 30-80%\n"
        "Если не делаешь — ставь 0.</i>\n\n"
        "Например: <code>40</code> или <code>0</code>",
        parse_mode="HTML"
    )
    await state.set_state(CS.upsell_pct)


@dp.message(CS.upsell_pct)
async def get_upct(message: types.Message, state: FSMContext):
    v = pn(message.text)
    if v is None or v < 0 or v > 100:
        await message.answer("❌ Число 0-100")
        return
    await state.update_data(upsell_pct=v / 100)
    if v > 0:
        await message.answer(
            "💵 <b>Сумма апсейла</b> (BYN)\n\n"
            "<i>На сколько BYN дороже платит клиент.\n"
            "Основной 59.9, набор 79.9 → разница = 20.\n"
            "Лучше кратно 5-10.</i>\n\n"
            "Например: <code>20</code>",
            parse_mode="HTML"
        )
        await state.set_state(CS.upsell_amount)
    else:
        await state.update_data(upsell_amount=0)
        await ask_buyout(message)
        await state.set_state(CS.buyout_pct)


@dp.message(CS.upsell_amount)
async def get_uamt(message: types.Message, state: FSMContext):
    v = pn(message.text)
    if v is None or v < 0:
        await message.answer("❌ Число", parse_mode="HTML")
        return
    await state.update_data(upsell_amount=v)
    await ask_buyout(message)
    await state.set_state(CS.buyout_pct)


async def ask_buyout(msg):
    await msg.answer(
        "📬 <b>% выкупа</b>\n\n"
        "<i>Сколько % забирают товар с почты.\n"
        "• 92%+ отлично\n"
        "• 85-92% нормально\n"
        "• ниже 80% проблема</i>\n\n"
        "Например: <code>90</code>",
        parse_mode="HTML"
    )


@dp.message(CS.buyout_pct)
async def get_buyout(message: types.Message, state: FSMContext):
    v = pn(message.text)
    if not v or v <= 0 or v > 100:
        await message.answer("❌ Число 1-100")
        return
    await state.update_data(buyout_pct=v / 100)
    await message.answer(
        "━━━ 📢 РЕКЛАМА ━━━\n\n"
        "📢 <b>Стоимость 1 лида</b> ($)\n\n"
        "<i>Лид = заявка на сайте (НЕ покупатель).\n"
        "Ориентиры:\n"
        "• до 30 BYN → ~$1.5\n"
        "• 30-50 BYN → ~$1.8\n"
        "• 60-80 BYN → ~$2.0\n"
        "• 80+ BYN → ~$2.3</i>\n\n"
        "Например: <code>2</code>",
        parse_mode="HTML"
    )
    await state.set_state(CS.lead_cost_usd)


@dp.message(CS.lead_cost_usd)
async def get_lead(message: types.Message, state: FSMContext):
    v = pn(message.text)
    if not v or v <= 0:
        await message.answer("❌ Число", parse_mode="HTML")
        return
    await state.update_data(lead_cost_usd=v)
    await message.answer(
        "🏢 <b>Комиссия рекл. агента</b> (%)\n\n"
        "Например: <code>10</code> или <code>7</code>",
        parse_mode="HTML"
    )
    await state.set_state(CS.agent_commission_pct)


@dp.message(CS.agent_commission_pct)
async def get_agent(message: types.Message, state: FSMContext):
    v = pn(message.text)
    if v is None or v < 0 or v > 100:
        await message.answer("❌ Число 0-100")
        return
    await state.update_data(agent_commission_pct=v / 100)
    await message.answer(
        "📞 <b>Аппрув</b> (%)\n\n"
        "<i>% лидов, подтвердивших заказ.\n"
        "• 75%+ отлично\n"
        "• 60-75% нормально\n"
        "• ниже 60% — нужен КЦ</i>\n\n"
        "Например: <code>70</code>",
        parse_mode="HTML"
    )
    await state.set_state(CS.approval_pct)


@dp.message(CS.approval_pct)
async def get_appr(message: types.Message, state: FSMContext):
    v = pn(message.text)
    if not v or v <= 0 or v > 100:
        await message.answer("❌ Число 1-100")
        return
    await state.update_data(approval_pct=v / 100)
    await message.answer(
        "━━━ 👤 ОБРАБОТКА ЗАКАЗОВ ━━━\n\n"
        "<i>Сам = затраты на КЦ 0, почта 0.08 BYN\n"
        "КЦ = укажешь стоимость</i>",
        parse_mode="HTML", reply_markup=alonekb()
    )
    await state.set_state(CS.works_alone)


@dp.message(CS.works_alone)
async def get_alone(message: types.Message, state: FSMContext):
    t = message.text.strip()
    if "Сам" in t or "сам" in t:
        await state.update_data(
            call_center_cost=0, warehouse_cost=0.08, targetolog_cost=0
        )
        await do_calc(message, state)
    elif "колл" in t.lower() or "менеджер" in t.lower() or "📞" in t:
        await message.answer(
            "📞 <b>Затраты на КЦ</b> за 1 заказ (BYN)\n\n"
            "<i>Обычно: 1 BYN за заявку + 10% от суммы кросс/апсейла.\n"
            "Или фикс 2-5 BYN.</i>\n\n"
            "Например: <code>3.38</code>",
            parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(CS.call_center_cost)
    else:
        await message.answer("Выбери кнопкой 👇", reply_markup=alonekb())


@dp.message(CS.call_center_cost)
async def get_cc(message: types.Message, state: FSMContext):
    v = pn(message.text)
    if v is None or v < 0:
        await message.answer("❌ Число", parse_mode="HTML")
        return
    await state.update_data(call_center_cost=v)
    await message.answer(
        "📮 <b>Затраты на почту/склад</b> за 1 заказ (BYN)\n\n"
        "<i>Сам упаковываешь → 0.08 BYN\n"
        "Кладовщик → обычно 1 BYN</i>\n\n"
        "Например: <code>0.08</code> или <code>1</code>",
        parse_mode="HTML"
    )
    await state.set_state(CS.warehouse_cost)


@dp.message(CS.warehouse_cost)
async def get_wh(message: types.Message, state: FSMContext):
    v = pn(message.text)
    if v is None or v < 0:
        await message.answer("❌ Число. Например: <code>0.08</code>", parse_mode="HTML")
        return
    await state.update_data(warehouse_cost=v)
    await message.answer(
        "🎯 <b>Затраты на таргетолога</b> за 1 заказ (BYN)\n\n"
        "<i>Обычно ~0.70 BYN за заказ.\n"
        "Если сам ведёшь рекламу — ставь 0.</i>\n\n"
        "Например: <code>0.7</code> или <code>0</code>",
        parse_mode="HTML"
    )
    await state.set_state(CS.targetolog_cost)


@dp.message(CS.targetolog_cost)
async def get_tgt(message: types.Message, state: FSMContext):
    v = pn(message.text)
    if v is None or v < 0:
        await message.answer("❌ Число", parse_mode="HTML")
        return
    await state.update_data(targetolog_cost=v)
    await do_calc(message, state)


async def do_calc(message, state):
    try:
        data = await state.get_data()
        result = calculate(data)
        if len(result) <= 4096:
            await message.answer(result, parse_mode="HTML", reply_markup=startkb())
        else:
            parts = smart_split(result)
            for i, p in enumerate(parts):
                kb = startkb() if i == len(parts) - 1 else None
                await message.answer(p, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        await message.answer(f"❌ Ошибка:\n<code>{e}</code>", parse_mode="HTML", reply_markup=startkb())
    await state.clear()


def smart_split(text, limit=4096):
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:]
    parts.append(text)
    return parts


# ==============================================
#            РАСЧЁТ (как в таблице)
# ==============================================
def calculate(d: dict) -> str:

    delivery = 0.5
    parcel_cost = 5.0

    # --- ЗАКУПКА ---
    purchase_byn = d["purchase_price_rub"] * d["rub_rate"]

    if d["has_import_vat"]:
        vat_amount = purchase_byn * 0.20
    else:
        vat_amount = 0

    purchase_with_vat = purchase_byn + vat_amount
    purchase_total = purchase_with_vat + delivery

    # --- КРОССЕЙЛЫ ---
    cross_pct = d["cross_sell_pct"]
    units_sold = 1 + cross_pct
    cross_revenue = d["landing_price"] * cross_pct
    purchase_with_cross = purchase_total * units_sold

    # --- АПСЕЙЛЫ ---
    upsell_revenue = d["upsell_pct"] * d["upsell_amount"]

    # --- ВЫРУЧКА ---
    revenue_gross = d["landing_price"] + cross_revenue + upsell_revenue

    # --- ВЫКУП ---
    buyout = d["buyout_pct"]
    non_buyout = 1 - buyout
    revenue_after_buyout = revenue_gross * buyout

    # Возврат товара на склад (как в таблице!)
    returned_goods = purchase_with_cross * non_buyout

    # ИТОГОВАЯ ВЫРУЧКА = после выкупа + вернувшийся товар
    effective_revenue = revenue_after_buyout + returned_goods

    # --- ПОКАТУШКИ (как в таблице: 5 × 1.5 × невыкуп%) ---
    return_shipping = parcel_cost * 1.5 * non_buyout

    # --- РЕКЛАМА ---
    lead_byn = d["lead_cost_usd"] * d["usd_rate"]
    lead_with_agent = lead_byn * (1 + d["agent_commission_pct"])

    if d["has_ad_tax"]:
        ad_tax = lead_with_agent * 0.20
        lead_final = lead_with_agent + ad_tax
    else:
        ad_tax = 0
        lead_final = lead_with_agent

    client_cost = lead_final / d["approval_pct"]

    # --- ВОЗВРАТ НЕКАЧ (как в таблице: закупка × выкуп% × 1.5%) ---
    defect_return = purchase_total * 0.015

    # --- ПРОЧИЕ ЗАТРАТЫ ---
    cc = d["call_center_cost"]
    wh = d["warehouse_cost"]
    tgt = d.get("targetolog_cost", 0)

    # --- ЗАТРАТЫ ДО НАЛОГА ---
    costs_before_tax = (
        purchase_with_cross +
        return_shipping +
        client_cost +
        tgt +
        cc +
        wh +
        defect_return
    )

    # --- ПРИБЫЛЬ И НАЛОГ ---
    profit_before_tax = effective_revenue - costs_before_tax

    if d["has_profit_tax"] and profit_before_tax > 0:
        profit_tax = profit_before_tax * 0.20
    else:
        profit_tax = 0

    net_profit = profit_before_tax - profit_tax
    total_costs = costs_before_tax + profit_tax

    profitability = net_profit / total_costs if total_costs > 0 else 0

    # --- ТОЧКИ БЕЗУБЫТОЧНОСТИ ---
    costs_no_ads = (
        purchase_with_cross + return_shipping +
        tgt + cc + wh + defect_return
    )

    # Безубыточность (0%)
    if d["has_profit_tax"]:
        max_costs_0 = effective_revenue  # прибыль=0, налог=0
    else:
        max_costs_0 = effective_revenue

    max_cc_0 = max_costs_0 - costs_no_ads
    max_lead_0 = _reverse_lead(max_cc_0, d)

        # Рент 20% = прибыль / затраты = 0.20
    # Значит затраты = выручка / 1.20
    # С налогом на прибыль:
    # net = (выр - costs_bt) × 0.8
    # total = costs_bt + (выр - costs_bt) × 0.2
    # net / total = 0.20
    # Решаем: costs_bt = выр × 0.76 / 0.96
    if d["has_profit_tax"]:
        max_costs_20 = effective_revenue * 0.76 / 0.96
    else:
        max_costs_20 = effective_revenue / 1.20

    max_cc_20 = max_costs_20 - costs_no_ads
    max_lead_20 = _reverse_lead(max_cc_20, d)

    # Запас
    if d["lead_cost_usd"] > 0 and max_lead_0 > 0:
        lead_margin = ((max_lead_0 / d["lead_cost_usd"]) - 1) * 100
    else:
        lead_margin = 0

    # --- БЕЗ ДОПОВ ---
    rev_no = d["landing_price"] * buyout + purchase_total * non_buyout
    cc_no = 1.0 if cc > 0 else 0
    costs_no = (
        purchase_total + return_shipping + client_cost +
        tgt + cc_no + wh + purchase_total * 0.015
    )
    pbt_no = rev_no - costs_no
    if d["has_profit_tax"] and pbt_no > 0:
        tax_no = pbt_no * 0.20
    else:
        tax_no = 0
    np_no = pbt_no - tax_no
    total_costs_no = costs_no + tax_no
    rent_no = np_no / total_costs_no if total_costs_no > 0 else 0

    # --- ГДЕ СЭКОНОМИТЬ ---
    savings = []

    if d["approval_pct"] < 0.80:
        s = client_cost - lead_final / 0.80
        if s > 0.01:
            savings.append(("Поднять аппрув до 80%", s, "быстрый перезвон, скрипт"))

    if buyout < 0.95:
        r95 = revenue_gross * 0.95 + purchase_with_cross * 0.05
        ret95 = parcel_cost * 1.5 * 0.05
        s = (r95 - ret95) - (effective_revenue - return_shipping)
        if s > 0.01:
            savings.append(("Поднять выкуп до 95%", s, "СМС-дожим, звонки"))

    if cross_pct == 0:
        er = d["landing_price"] * 0.20 * buyout
        ec = purchase_total * 0.20
        s = er - ec
        if s > 0.01:
            savings.append(("Добавить кроссейлы (20%)", s, "доп. товар при звонке"))

    if d["upsell_pct"] == 0:
        s = 0.30 * 15 * buyout
        if s > 0.01:
            savings.append(("Добавить апсейлы (30% × 15 BYN)", s, "набор подороже"))

    savings.sort(key=lambda x: x[1], reverse=True)

    # --- СТАТУС ---
    if profitability >= 0.25:
        se, st = "🟢", "ОТЛИЧНО"
    elif profitability >= 0.15:
        se, st = "🟡", "НОРМАЛЬНО"
    elif profitability > 0:
        se, st = "🟠", "НА ГРАНИ"
    else:
        se, st = "🔴", "УБЫТОК"

    tax_parts = []
    if d["has_import_vat"]:
        tax_parts.append("НДС 20%")
    if d["has_ad_tax"]:
        tax_parts.append("Нал.рекл. 20%")
    if d["has_profit_tax"]:
        tax_parts.append("Нал.приб. 20%")
    tax_mode = " + ".join(tax_parts) if tax_parts else "Без налогов"

    ag = d["agent_commission_pct"] * 100
    ap = d["approval_pct"] * 100

    # ===== ФОРМИРУЕМ ОТВЕТ =====
    r = f"""{se} <b>ЮНИТ-ЭКОНОМИКА — {st}</b>

━━━ ⚙️ ДАННЫЕ ━━━

🏷 Цена на ленде: <b>{d['landing_price']:.2f} BYN</b>
📦 Закупка: {d['purchase_price_rub']:.0f}₽ × {d['rub_rate']:.4f} = {purchase_byn:.2f} BYN"""

    if vat_amount > 0:
        r += f"\n🏛 + НДС 20%: +{vat_amount:.2f} = {purchase_with_vat:.2f} BYN"

    r += f"""
🚚 + Доставка: {delivery:.2f} BYN
📦 <b>Закупка 1 ед.: {purchase_total:.2f} BYN</b>
💵 $1 = {d['usd_rate']:.4f} | ₽1 = {d['rub_rate']:.4f}
🏛 {tax_mode}

━━━ 💰 ВЫРУЧКА ━━━

Базовая: {d['landing_price']:.2f} BYN"""

    if cross_pct > 0:
        r += f"""
+ Кроссейлы ({cross_pct*100:.0f}%): +{cross_revenue:.2f} BYN
  <i>{cross_pct*100:.0f}% клиентов берут ещё 1 товар</i>"""

    if d["upsell_pct"] > 0:
        r += f"""
+ Апсейлы ({d['upsell_pct']*100:.0f}% × {d['upsell_amount']:.0f}): +{upsell_revenue:.2f} BYN
  <i>{d['upsell_pct']*100:.0f}% платят на {d['upsell_amount']:.0f} BYN больше</i>"""

    r += f"""

Выручка до выкупа: {revenue_gross:.2f} BYN
× выкуп {buyout*100:.0f}% = {revenue_after_buyout:.2f} BYN
+ возврат товара на склад: +{returned_goods:.2f} BYN
  <i>(невыкупленный товар вернётся, его можно продать)</i>
<b>= ВЫРУЧКА: {effective_revenue:.2f} BYN</b>

━━━ 📊 ЗАТРАТЫ ━━━

📦 <b>Закупка: {purchase_with_cross:.2f} BYN</b>"""

    if cross_pct > 0:
        r += f"""
   {purchase_total:.2f} × {units_sold:.2f} ед."""

    r += f"""

📢 <b>Клиент: {client_cost:.2f} BYN</b>
   Лид ${d['lead_cost_usd']:.2f} × {d['usd_rate']:.4f} = {lead_byn:.2f} BYN"""
    if ag > 0:
        r += f"\n   + агент {ag:.0f}% = {lead_with_agent:.2f}"
    if ad_tax > 0:
        r += f"\n   + нал.рекл. 20% = {lead_final:.2f}"
    r += f"""
   ÷ аппрув {ap:.0f}% = <b>{client_cost:.2f} BYN</b>
   <i>Из 100 лидов {ap:.0f} покупают → за клиента платим больше</i>"""

    if tgt > 0:
        r += f"\n\n🎯 <b>Таргетолог: {tgt:.2f} BYN</b>"
    if cc > 0:
        r += f"\n\n📞 <b>Колл-центр: {cc:.2f} BYN</b>"

    r += f"""

📮 <b>Почта/склад: {wh:.2f} BYN</b>

🔄 <b>Покатушки: {return_shipping:.2f} BYN</b>
   <i>5 BYN × 1.5 × {non_buyout*100:.0f}% невыкупа</i>

🔧 <b>Возврат некач.: {defect_return:.2f} BYN</b>
   <i>1.5% от закупки выкупленного товара</i>"""

    if profit_tax > 0:
        r += f"""

📋 <b>Прибыль до налога: {profit_before_tax:.2f} BYN</b>
   <i>Выручка {effective_revenue:.2f} − Затраты {costs_before_tax:.2f}</i>
🏛 <b>Налог 20%: {profit_tax:.2f} BYN</b>
   <i>{profit_before_tax:.2f} × 20%</i>"""

    r += f"""

━━━━━━━━━━━━━━━━━━━━
📊 <b>ИТОГО ЗАТРАТ: {total_costs:.2f} BYN</b>

━━━ ✅ РЕЗУЛЬТАТ ━━━

💵 Выручка: {effective_revenue:.2f} BYN
📊 Затраты: {total_costs:.2f} BYN
━━━━━━━━━━━━━━━━━━━━
💰 <b>ПРИБЫЛЬ: {net_profit:.2f} BYN</b>
📈 <b>РЕНТАБЕЛЬНОСТЬ: {profitability*100:.1f}%</b>
━━━━━━━━━━━━━━━━━━━━

━━━ 🎯 КОНТРОЛЬНЫЕ ТОЧКИ ━━━

🔴 <b>Безубыточность (0%)</b>
   Макс. лид: <b>${max_lead_0:.2f}</b>"""

    if lead_margin > 0:
        r += f" (запас {lead_margin:.0f}%)"
        r += f"\n   <i>Пока лид дешевле ${max_lead_0:.2f} — в плюсе</i>"
    else:
        r += "\n   ⚠️ Уже в убытке!"

    r += f"""

🟢 <b>Рентабельность 20%</b>
   Макс. лид: <b>${max_lead_20:.2f}</b>"""
    if d["lead_cost_usd"] <= max_lead_20:
        r += f"\n   ✅ Лид ${d['lead_cost_usd']:.2f} — проходишь!"
    else:
        r += f"\n   ❌ Нужно снизить лид на ${d['lead_cost_usd'] - max_lead_20:.2f}"

    if cross_pct > 0 or d["upsell_pct"] > 0:
        r += f"""

━━━ 📉 БЕЗ ДОПОВ ━━━
Прибыль: <b>{np_no:.2f} BYN</b> | Рент.: <b>{rent_no*100:.1f}%</b>
<i>Без апсейлов и кроссейлов</i>"""

    if savings:
        r += "\n\n━━━ 💡 ГДЕ СЭКОНОМИТЬ ━━━\n"
        for i, (name, save, hint) in enumerate(savings, 1):
            r += f"\n{i}. <b>{name}</b>"
            r += f"\n   +{save:.2f} BYN/заказ"
            r += f"\n   <i>{hint}</i>\n"
        total_save = sum(s[1] for s in savings)
        new_p = net_profit + total_save
        new_r = new_p / effective_revenue if effective_revenue > 0 else 0
        r += f"\n📊 Потенциал: <b>{new_p:.2f} BYN</b> ({new_r*100:.1f}%)"

    # Рекомендации
    recs = []
    if profitability < 0:
        recs.append("🔴 Убыток — снижай лид или повышай цену")
    elif profitability < 0.15:
        recs.append("🟠 Маржа тонкая — попробуй +5-10 BYN к цене")
    if 0 < lead_margin < 30:
        recs.append("⚠️ Запас по лиду мал — любой скачок съест прибыль")

    if recs:
        r += "\n\n━━━ ⚠️ ВАЖНО ━━━\n\n" + "\n".join(recs)

    r += "\n\n<i>🔄 За месяц можно обернуть 2-3 раза</i>"
    return r


def _reverse_lead(max_client_cost, d):
    """Из макс. стоимости клиента → макс. цена лида в $"""
    if max_client_cost <= 0:
        return 0
    max_lead_byn = max_client_cost * d["approval_pct"]
    if d["has_ad_tax"]:
        max_lead_byn = max_lead_byn / 1.20
    max_lead_byn = max_lead_byn / (1 + d["agent_commission_pct"])
    return max_lead_byn / d["usd_rate"]


async def main():
    print("Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())