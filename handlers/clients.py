import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_IDS, REGION_MAP, SAVDO_TURLARI, SAVDO_SUBTURLARI
from database import (
    get_user, add_client, get_clients, search_clients,
    get_client_by_id, update_client, delete_client, count_clients,
    get_my_clients, count_my_clients,
)


async def _get_display_name(user_id: int, fallback: str) -> str:
    """Ishchining tanlagan ismi (worker_name) yoki Telegram ismi."""
    db_user = await get_user(user_id)
    if db_user and db_user["worker_name"]:
        return db_user["worker_name"]
    return fallback
from keyboards import (
    clients_menu_kb, client_detail_kb, edit_fields_kb,
    savdo_turi_kb, savdo_subturi_kb,
    savdo_turi_reply_kb, savdo_subturi_reply_kb,
    kasb_turi_reply_kb,
    location_kb, cancel_kb,
    BTN_LOCATION_MANUAL,
    confirm_delete_kb, pagination_kb,
    admin_main_menu_kb, user_main_menu_kb,
)

# ─── HOLATLAR ─────────────────────────────────────────────────────────────────
(
    ADD_ISM, ADD_TELEFON, ADD_TELEFON2, ADD_LOCATION, ADD_KASB,
    ADD_SAVDO_TURI, ADD_SAVDO_SUBTURI,
    SEARCH_QUERY, EDIT_VALUE, DELETE_CONFIRM,
) = range(10)

ADD_MANZIL = ADD_LOCATION

PAGE_SIZE = 8

def _esc(text) -> str:
    """Markdown v1 maxsus belgilarini ekranlaydi."""
    for ch in ['_', '*', '`', '[']:
        text = str(text).replace(ch, f'\\{ch}')
    return text

def _is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def _main_kb(is_admin: bool):
    return admin_main_menu_kb() if is_admin else user_main_menu_kb()

def _progress(step: int, total: int = 7) -> str:
    filled = "▓" * step
    empty  = "░" * (total - step)
    return f"[{filled}{empty}] {step}/{total}"

async def _get_region(telegram_id: int):
    user = await get_user(telegram_id)
    return user["region_id"] if user else None

# ─── MIJOZLAR BO'LIM MENYUSI ──────────────────────────────────────────────────

async def clients_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    await update.effective_message.reply_text(
        "👥 *Mijozlar bo'limi*\n\nQuyidagi amallardan birini tanlang:",
        parse_mode="Markdown",
        reply_markup=clients_menu_kb(),
    )

# ═══════════════════════════════════════════════════════════════════════════════
# MIJOZ QO'SHISH — 7 BOSQICH
# ═══════════════════════════════════════════════════════════════════════════════

async def client_add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    ctx.user_data.clear()
    ctx.user_data["adding"] = True

    await update.effective_message.reply_text(
        f"➕ *Yangi mijoz qo'shish*\n"
        f"{_progress(1)}\n\n"
        f"1️⃣ *Ism va familiya* kiriting:",
        parse_mode="Markdown",
        reply_markup=cancel_kb(),
    )
    return ADD_ISM

async def add_ism(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["ism"] = update.message.text.strip()
    await update.message.reply_text(
        f"➕ *Yangi mijoz qo'shish*\n"
        f"{_progress(2)}\n\n"
        f"2️⃣ *Telefon raqam* kiriting:\n_(masalan: +998901234567)_",
        parse_mode="Markdown",
        reply_markup=cancel_kb(),
    )
    return ADD_TELEFON

async def add_telefon(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["telefon"] = update.message.text.strip()
    await update.message.reply_text(
        f"➕ *Yangi mijoz qo'shish*\n"
        f"{_progress(3)}\n\n"
        f"3️⃣ *Qo'shimcha telefon raqam* kiriting:\n_(yo'q bo'lsa — deb yozing)_",
        parse_mode="Markdown",
        reply_markup=cancel_kb(),
    )
    return ADD_TELEFON2

async def add_telefon2(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    ctx.user_data["telefon2"] = "" if val in ("—", "-", "yo'q", "yoq") else val
    await update.message.reply_text(
        f"➕ *Yangi mijoz qo'shish*\n"
        f"{_progress(4)}\n\n"
        f"4️⃣ *Lokatsiya* yuboring yoki manzilni qo'lda kiriting:",
        parse_mode="Markdown",
        reply_markup=location_kb(),
    )
    return ADD_LOCATION


async def _coords_to_address(lat: float, lon: float) -> str:
    """Koordinatalarni aniq manzilga aylantiradi (Nominatim reverse geocoding).
    Qaytaradigan format: Ko'cha, Mahalla, Tuman, Shahar
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lon, "format": "json", "addressdetails": 1, "accept-language": "uz,ru,en"}
    headers = {"User-Agent": "AGU-CRM-MINIBOT/1.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    addr = data.get("address", {})
                    parts = []
                    # Ko'cha / yo'l
                    road = (addr.get("road") or addr.get("pedestrian")
                            or addr.get("footway") or addr.get("path")
                            or addr.get("street"))
                    if road:
                        parts.append(road)
                    # Mahalla / qo'shni
                    neighbourhood = (addr.get("neighbourhood") or addr.get("quarter")
                                     or addr.get("suburb") or addr.get("residential"))
                    if neighbourhood:
                        parts.append(neighbourhood)
                    # Tuman / shahar tumani
                    district = (addr.get("city_district") or addr.get("district")
                                or addr.get("county") or addr.get("state_district"))
                    if district:
                        parts.append(district)
                    # Shahar / qishloq
                    city = (addr.get("city") or addr.get("town")
                            or addr.get("village") or addr.get("municipality"))
                    if city:
                        parts.append(city)
                    if parts:
                        return ", ".join(parts)
                    # Zaxira: display_name
                    return data.get("display_name") or f"{lat:.5f}, {lon:.5f}"
    except Exception:
        pass
    return f"{lat:.5f}, {lon:.5f}"


async def add_location_geo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Telegram lokatsiya xabari."""
    loc = update.message.location
    ctx.user_data["manzil"] = await _coords_to_address(loc.latitude, loc.longitude)
    await update.message.reply_text(
        f"➕ *Yangi mijoz qo'shish*\n"
        f"{_progress(5)}\n\n"
        f"5️⃣ *Kasb turini* tanlang:",
        parse_mode="Markdown",
        reply_markup=kasb_turi_reply_kb(),
    )
    return ADD_KASB

async def add_location_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Matn orqali manzil: '✍️ Qo'lda kiritish' tugmasi yoki to'g'ridan-to'g'ri matn."""
    text = update.message.text.strip()
    if text == BTN_LOCATION_MANUAL:
        await update.message.reply_text(
            f"➕ *Yangi mijoz qo'shish*\n"
            f"{_progress(4)}\n\n"
            f"4️⃣ *Manzil* kiriting:\n_(shahar, tuman, ko'cha)_",
            parse_mode="Markdown",
            reply_markup=cancel_kb(),
        )
        return ADD_LOCATION
    ctx.user_data["manzil"] = text
    await update.message.reply_text(
        f"➕ *Yangi mijoz qo'shish*\n"
        f"{_progress(5)}\n\n"
        f"5️⃣ *Kasb turini* tanlang:",
        parse_mode="Markdown",
        reply_markup=kasb_turi_reply_kb(),
    )
    return ADD_KASB

async def add_kasb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["kasb_turi"] = update.message.text.strip()
    await update.message.reply_text(
        f"➕ *Yangi mijoz qo'shish*\n"
        f"{_progress(6)}\n\n"
        f"6️⃣ *Savdo turini* tanlang:",
        parse_mode="Markdown",
        reply_markup=savdo_turi_reply_kb(),
    )
    return ADD_SAVDO_TURI

async def add_savdo_turi_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    turi = update.message.text.strip()
    if turi not in SAVDO_TURLARI:
        await update.message.reply_text(
            "❌ Ro'yxatdan tanlang:",
            reply_markup=savdo_turi_reply_kb(),
        )
        return ADD_SAVDO_TURI
    ctx.user_data["savdo_turi"] = turi
    await update.message.reply_text(
        f"➕ *Yangi mijoz qo'shish*\n"
        f"{_progress(7)}\n\n"
        f"7️⃣ *{turi}* — kichik turni tanlang:",
        parse_mode="Markdown",
        reply_markup=savdo_subturi_reply_kb(turi),
    )
    return ADD_SAVDO_SUBTURI

async def add_savdo_subturi_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    subturi = update.message.text.strip()
    turi    = ctx.user_data.get("savdo_turi", "")
    valid   = SAVDO_SUBTURLARI.get(turi, [])
    if subturi not in valid:
        await update.message.reply_text(
            "❌ Ro'yxatdan tanlang:",
            reply_markup=savdo_subturi_reply_kb(turi),
        )
        return ADD_SAVDO_SUBTURI
    ctx.user_data["savdo_subturi"] = subturi
    return await _save_client(update, ctx)


async def confirm_client_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Tasdiqlandi!")
    is_admin = _is_admin(update.effective_user.id)
    await query.message.reply_text(
        "✅ Mijoz muvaffaqiyatli tasdiqlandi!",
        reply_markup=_main_kb(is_admin),
    )

async def _save_client(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    region_id = await _get_region(user.id)
    if not region_id:
        await update.effective_message.reply_text("❌ Avval viloyat tanlang! /start")
        ctx.user_data.clear()
        return ConversationHandler.END

    display_name = await _get_display_name(user.id, user.full_name)
    data = {
        **ctx.user_data,
        "region_id":    region_id,
        "qoshgan_id":   user.id,
        "qoshgan_user": user.username or "",
        "qoshgan_nomi": display_name,
    }
    client_id = await add_client(data)
    is_admin  = _is_admin(user.id)

    # Google Sheets sync (background — xato bot'ni to'xtatmaydi)
    from sheets import sync_client_to_sheet, update_stats_sheet
    from database import get_all_user_stats
    region_name = REGION_MAP.get(region_id, "Noma'lum")
    asyncio.ensure_future(sync_client_to_sheet(dict(data), region_name))
    stats = await get_all_user_stats()
    asyncio.ensure_future(update_stats_sheet(stats))

    username_display = f"@{user.username}" if user.username else f"ID:{user.id}"
    telefon2_line = f"📞 Qo'shimcha: {_esc(data['telefon2'])}\n" if data.get("telefon2") else ""
    text = (
        f"✅ *Mijoz muvaffaqiyatli saqlandi!*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *{_esc(data.get('ism') or '—')}*\n"
        f"📞 {_esc(data.get('telefon') or '—')}\n"
        f"{telefon2_line}"
        f"📍 {_esc(data.get('manzil') or '—')}\n"
        f"💼 {_esc(data.get('kasb_turi') or '—')}\n"
        f"🏷 {_esc(data.get('savdo_turi') or '—')}\n"
        f"   ↳ {_esc(data.get('savdo_subturi') or '—')}\n"
        f"🏙 {_esc(REGION_MAP.get(region_id, '?'))}\n"
        f"👤 Qo'shgan: {_esc(display_name)} ({_esc(username_display)})"
    )
    await update.effective_message.reply_text(
        text, parse_mode="Markdown", reply_markup=client_detail_kb(client_id)
    )

    ctx.user_data.clear()
    return ConversationHandler.END

# ═══════════════════════════════════════════════════════════════════════════════
# MENING MIJOZLARIM (faqat o'zi qo'shganlar)
# ═══════════════════════════════════════════════════════════════════════════════

async def my_client_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    page = 0
    if update.callback_query:
        await update.callback_query.answer()
        if "_page_" in update.callback_query.data:
            page = int(update.callback_query.data.split("_page_")[-1])

    uid   = update.effective_user.id
    total = await count_my_clients(uid)

    if total == 0:
        await update.effective_message.reply_text(
            "📋 Siz hali hech qanday mijoz qo'shmagansiz.",
            reply_markup=user_main_menu_kb(),
        )
        return

    clients = await get_my_clients(uid, limit=PAGE_SIZE, offset=page * PAGE_SIZE)
    lines   = []
    for i, c in enumerate(clients, start=page * PAGE_SIZE + 1):
        turi = c["savdo_turi"] or "—"
        label = c['ism'] if c['ism'] else (c['telefon'] or f"Mijoz #{c['id']}")
        lines.append(
            f"{i}. *{label}* — {c['telefon'] or '—'}\n"
            f"   🏷 {turi} | 📍 {c['manzil'] or '—'} | `/mijoz {c['id']}`"
        )

    text = (
        f"📋 *Mening mijozlarim* (jami: {total} ta)\n"
        f"Sahifa {page + 1}\n\n" + "\n\n".join(lines)
    )
    pag_kb = pagination_kb(page, total, PAGE_SIZE, "myclients")
    await update.effective_message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=pag_kb if pag_kb else user_main_menu_kb(),
    )

# ═══════════════════════════════════════════════════════════════════════════════
# MIJOZLAR RO'YXATI
# ═══════════════════════════════════════════════════════════════════════════════

async def client_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    page = 0
    if update.callback_query:
        await update.callback_query.answer()
        if "_page_" in update.callback_query.data:
            page = int(update.callback_query.data.split("_page_")[-1])

    region_id = await _get_region(update.effective_user.id)
    total     = await count_clients(region_id)

    if total == 0:
        await update.effective_message.reply_text(
            "📋 Bazada hech qanday mijoz yo'q.",
            reply_markup=clients_menu_kb(),
        )
        return

    clients = await get_clients(region_id, limit=PAGE_SIZE, offset=page * PAGE_SIZE)
    lines = []
    for i, c in enumerate(clients, start=page * PAGE_SIZE + 1):
        turi  = c['savdo_turi'] or '—'
        label = c['ism'] if c['ism'] else (c['telefon'] or f"Mijoz #{c['id']}")
        lines.append(
            f"{i}. *{label}* — {c['telefon'] or '—'}\n"
            f"   🏷 {turi} | 🗺 {REGION_MAP.get(c['region_id'], '?')} | `/mijoz {c['id']}`"
        )

    text = (
        f"📋 *Mijozlar ro'yxati* (jami: {total} ta)\n"
        f"Sahifa {page + 1}\n\n" +
        "\n\n".join(lines)
    )
    pag_kb = pagination_kb(page, total, PAGE_SIZE, "clist")
    await update.effective_message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=pag_kb if pag_kb else clients_menu_kb(),
    )

# ═══════════════════════════════════════════════════════════════════════════════
# MIJOZ QIDIRISH
# ═══════════════════════════════════════════════════════════════════════════════

async def client_search_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    await update.effective_message.reply_text(
        "🔍 *Mijoz qidirish*\n\n"
        "Ism, telefon, manzil yoki kasb turi bo'yicha qidiring:",
        parse_mode="Markdown",
        reply_markup=cancel_kb(),
    )
    return SEARCH_QUERY

async def client_search_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q         = update.message.text.strip()
    user      = update.effective_user
    region_id = await _get_region(user.id)
    results   = await search_clients(q, region_id)
    is_admin  = _is_admin(user.id)

    if not results:
        await update.message.reply_text(
            f"❌ *'{q}'* bo'yicha hech narsa topilmadi.",
            parse_mode="Markdown",
            reply_markup=_main_kb(is_admin),
        )
        return ConversationHandler.END

    lines = []
    for i, c in enumerate(results, 1):
        label = c['ism'] if c['ism'] else (c['telefon'] or f"Mijoz #{c['id']}")
        lines.append(
            f"{i}. *{label}* — {c['telefon'] or '—'}\n"
            f"   📍 {c['manzil'] or '—'} | 💼 {c['kasb_turi'] or '—'}\n"
            f"   🏷 {c['savdo_turi'] or '—'} → {c['savdo_subturi'] or '—'}\n"
            f"   🗺 {REGION_MAP.get(c['region_id'], '?')} | `/mijoz {c['id']}`"
        )

    text = f"🔍 *'{q}'* bo'yicha {len(results)} ta natija:\n\n" + "\n\n".join(lines)
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=_main_kb(is_admin),
    )
    return ConversationHandler.END

# ═══════════════════════════════════════════════════════════════════════════════
# MIJOZ TAFSILOTI
# ═══════════════════════════════════════════════════════════════════════════════

async def client_detail_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Foydalanish: /mijoz <ID>")
        return
    try:
        client_id = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri ID!")
        return
    await _show_client(update, ctx, client_id)

async def client_detail_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.replace("client_detail_", ""))
    await _show_client(update, ctx, client_id)

async def _show_client(update: Update, ctx: ContextTypes.DEFAULT_TYPE, client_id: int):
    c = await get_client_by_id(client_id)
    if not c:
        await update.effective_message.reply_text("❌ Mijoz topilmadi!")
        return

    label = c['ism'] if c['ism'] else (c['telefon'] or f"Mijoz #{c['id']}")
    qoshgan_user = f"@{c['qoshgan_user']}" if c['qoshgan_user'] else f"ID:{c['qoshgan_id']}"
    telefon2_line = f"📞 Qo'shimcha:    {_esc(c['telefon2'])}\n" if c.get('telefon2') else ""
    text = (
        f"👤 *{_esc(label)}*  `(ID: {c['id']})`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📞 Telefon:       {_esc(c['telefon'] or '—')}\n"
        f"{telefon2_line}"
        f"📍 Manzil:        {_esc(c['manzil'] or '—')}\n"
        f"💼 Kasb turi:     {_esc(c['kasb_turi'] or '—')}\n"
        f"🏷 Savdo turi:    {_esc(c['savdo_turi'] or '—')}\n"
        f"   ↳ Kichik tur:  {_esc(c['savdo_subturi'] or '—')}\n"
        f"📝 Izoh:          {_esc(c['izoh'] or '—')}\n"
        f"🗺 Viloyat:       {_esc(REGION_MAP.get(c['region_id'], '?'))}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Qo'shgan:      {_esc(c['qoshgan_nomi'])} ({_esc(qoshgan_user)})\n"
        f"🕐 Qo'shilgan:    {c['qoshilgan_vaqt']}\n"
        f"🔄 Yangilangan:   {c['yangilangan_vaqt']}"
    )
    await update.effective_message.reply_text(
        text, parse_mode="Markdown", reply_markup=client_detail_kb(client_id)
    )

# ═══════════════════════════════════════════════════════════════════════════════
# MIJOZ TAHRIRLASH
# ═══════════════════════════════════════════════════════════════════════════════

async def edit_start_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[1])
    c = await get_client_by_id(client_id)
    if not c:
        await query.message.reply_text("❌ Mijoz topilmadi!")
        return

    ctx.user_data["edit_client_id"] = client_id
    label = c['ism'] if c['ism'] else (c['telefon'] or f"Mijoz #{c['id']}")
    await query.message.reply_text(
        f"✏️ *{label}* ni tahrirlash\n\nQaysi maydonni o'zgartirmoqchisiz?",
        parse_mode="Markdown",
        reply_markup=edit_fields_kb(client_id),
    )

async def edit_field_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts     = query.data.split("_")
    client_id = int(parts[1])
    field     = parts[2]

    ctx.user_data["edit_client_id"] = client_id
    ctx.user_data["edit_field"]     = field

    if field == "savdo_turi":
        await query.message.reply_text("🏷 Yangi savdo turini tanlang:", reply_markup=savdo_turi_kb())
        return EDIT_VALUE
    if field == "savdo_subturi":
        c = await get_client_by_id(client_id)
        turi = c["savdo_turi"] if c else "Ulgurji savdo"
        await query.message.reply_text(
            f"🏷 *{turi}* — yangi kichik turni tanlang:",
            parse_mode="Markdown",
            reply_markup=savdo_subturi_kb(turi),
        )
        return EDIT_VALUE

    if field == "manzil":
        await query.message.reply_text(
            "✏️ *Yangi manzil* kiriting yoki lokatsiya yuboring:\n"
            "_(mahalla, ko'cha, tuman darajasida aniqlanadi)_",
            parse_mode="Markdown",
            reply_markup=location_kb(),
        )
        return EDIT_VALUE

    label_map = {
        "ism": "Ism-Familya", "telefon": "Telefon",
        "kasb_turi": "Kasb turi", "izoh": "Izoh",
    }
    await query.message.reply_text(
        f"✏️ *{label_map.get(field, field)}* uchun yangi qiymat kiriting:",
        parse_mode="Markdown",
        reply_markup=cancel_kb(),
    )
    return EDIT_VALUE


async def edit_location_geo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Edit flow: GPS lokatsiyani aniq manzilga o'tkazib saqlaydi."""
    client_id = ctx.user_data.get("edit_client_id")
    if not client_id:
        await update.message.reply_text("❌ Xato. Qaytadan urinib ko'ring.")
        return ConversationHandler.END
    loc = update.message.location
    manzil = await _coords_to_address(loc.latitude, loc.longitude)
    await update_client(client_id, "manzil", manzil)
    ctx.user_data.clear()
    await update.message.reply_text(
        f"✅ *Manzil yangilandi!*\n📍 {manzil}",
        parse_mode="Markdown",
        reply_markup=client_detail_kb(client_id),
    )
    return ConversationHandler.END

async def edit_turi_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await query.answer()
    client_id = ctx.user_data.get("edit_client_id")
    if not client_id:
        await query.message.reply_text("❌ Xato. Qaytadan urinib ko'ring.")
        return ConversationHandler.END
    value = query.data.replace("turi_", "")
    await update_client(client_id, "savdo_turi", value)
    ctx.user_data["edit_field"] = "savdo_subturi"
    await query.message.reply_text(
        f"✅ Savdo turi yangilandi: *{value}*\n\nKichik turni ham yangilaysizmi?",
        parse_mode="Markdown",
        reply_markup=savdo_subturi_kb(value),
    )
    return EDIT_VALUE

async def edit_subturi_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await query.answer()
    client_id = ctx.user_data.get("edit_client_id")
    if not client_id:
        await query.message.reply_text("❌ Xato.")
        return ConversationHandler.END
    value = query.data.replace("subturi_", "")
    await update_client(client_id, "savdo_subturi", value)
    ctx.user_data.clear()
    await query.message.reply_text(
        f"✅ Kichik tur yangilandi: *{value}*",
        parse_mode="Markdown",
        reply_markup=client_detail_kb(client_id),
    )
    return ConversationHandler.END

async def edit_value_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    client_id = ctx.user_data.get("edit_client_id")
    field     = ctx.user_data.get("edit_field")

    # Agar awaiting_edit_id bo'lsa — ID kutilmoqda
    if ctx.user_data.get("awaiting_edit_id"):
        try:
            client_id = int(update.message.text.strip())
        except ValueError:
            await update.message.reply_text("❌ Raqam kiriting:", reply_markup=cancel_kb())
            return EDIT_VALUE
        c = await get_client_by_id(client_id)
        if not c:
            await update.message.reply_text("❌ Topilmadi. Boshqa ID:", reply_markup=cancel_kb())
            return EDIT_VALUE
        ctx.user_data["edit_client_id"]    = client_id
        ctx.user_data["awaiting_edit_id"]  = False
        label = c['ism'] if c['ism'] else (c['telefon'] or f"Mijoz #{c['id']}")
        await update.message.reply_text(
            f"✏️ *{label}* ni tahrirlash\n\nQaysi maydonni o'zgartirmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=edit_fields_kb(client_id),
        )
        return EDIT_VALUE

    if not client_id or not field:
        await update.message.reply_text("❌ Xato. /start bosing.")
        return ConversationHandler.END

    value = update.message.text.strip()
    await update_client(client_id, field, value)
    ctx.user_data.clear()
    await update.message.reply_text(
        "✅ *Muvaffaqiyatli yangilandi!*",
        parse_mode="Markdown",
        reply_markup=client_detail_kb(client_id),
    )
    return ConversationHandler.END

async def edit_start_ask_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    await update.effective_message.reply_text(
        "✏️ Tahrirlash uchun mijoz *ID* sini kiriting:",
        parse_mode="Markdown",
        reply_markup=cancel_kb(),
    )
    ctx.user_data["awaiting_edit_id"] = True
    return EDIT_VALUE

# ═══════════════════════════════════════════════════════════════════════════════
# MIJOZ O'CHIRISH
# ═══════════════════════════════════════════════════════════════════════════════

async def delete_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[1])
    c = await get_client_by_id(client_id)
    if not c:
        await query.message.reply_text("❌ Mijoz topilmadi!")
        return
    label = c['ism'] if c['ism'] else (c['telefon'] or f"Mijoz #{c['id']}")
    await query.message.reply_text(
        f"🗑 *{label}* ni o'chirishni tasdiqlaysizmi?\n"
        "_(Barcha bog'liq vazifalar ham o'chadi)_",
        parse_mode="Markdown",
        reply_markup=confirm_delete_kb("delclient", client_id),
    )

async def delete_confirm_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[-1])
    await delete_client(client_id)
    is_admin = _is_admin(update.effective_user.id)
    await query.message.reply_text("✅ Mijoz o'chirildi.", reply_markup=_main_kb(is_admin))

async def delete_ask_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    await update.effective_message.reply_text(
        "🗑 O'chirish uchun mijoz *ID* sini kiriting:",
        parse_mode="Markdown",
        reply_markup=cancel_kb(),
    )
    ctx.user_data["awaiting_delete_id"] = True
    return DELETE_CONFIRM

async def delete_id_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        client_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Raqam kiriting:", reply_markup=cancel_kb())
        return DELETE_CONFIRM
    c = await get_client_by_id(client_id)
    if not c:
        await update.message.reply_text("❌ Topilmadi. Boshqa ID:", reply_markup=cancel_kb())
        return DELETE_CONFIRM
    label = c['ism'] if c['ism'] else (c['telefon'] or f"Mijoz #{c['id']}")
    await update.message.reply_text(
        f"🗑 *{label}* ni o'chirishni tasdiqlaysizmi?",
        parse_mode="Markdown",
        reply_markup=confirm_delete_kb("delclient", client_id),
    )
    ctx.user_data.clear()
    return ConversationHandler.END
