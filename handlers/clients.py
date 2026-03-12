from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_IDS, REGION_MAP
from database import (
    get_user, add_client, get_clients, search_clients,
    get_client_by_id, update_client, delete_client, count_clients,
    get_my_clients, count_my_clients,
)
from keyboards import (
    clients_menu_kb, client_detail_kb, edit_fields_kb,
    savdo_turi_kb, savdo_subturi_kb,
    cancel_kb, skip_cancel_kb,
    confirm_delete_kb, pagination_kb,
    admin_main_menu_kb, user_main_menu_kb,
)

# ─── HOLATLAR ─────────────────────────────────────────────────────────────────
(
    ADD_ISM, ADD_TELEFON, ADD_MANZIL, ADD_KASB,
    ADD_SAVDO_TURI, ADD_SAVDO_SUBTURI, ADD_IZOH,
    SEARCH_QUERY, EDIT_VALUE, DELETE_CONFIRM,
) = range(10)

PAGE_SIZE = 8

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
        f"3️⃣ *Manzil* kiriting:\n_(shahar, tuman, ko'cha)_",
        parse_mode="Markdown",
        reply_markup=cancel_kb(),
    )
    return ADD_MANZIL

async def add_manzil(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["manzil"] = update.message.text.strip()
    await update.message.reply_text(
        f"➕ *Yangi mijoz qo'shish*\n"
        f"{_progress(4)}\n\n"
        f"4️⃣ *Kasb turi* kiriting:\n_(masalan: Tadbirkor, Fermer, Shifokor...)_",
        parse_mode="Markdown",
        reply_markup=cancel_kb(),
    )
    return ADD_KASB

async def add_kasb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["kasb_turi"] = update.message.text.strip()
    await update.message.reply_text(
        f"➕ *Yangi mijoz qo'shish*\n"
        f"{_progress(5)}\n\n"
        f"5️⃣ *Savdo turini* tanlang:",
        parse_mode="Markdown",
        reply_markup=savdo_turi_kb(),
    )
    return ADD_SAVDO_TURI

async def add_savdo_turi_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    turi = query.data.replace("turi_", "")
    ctx.user_data["savdo_turi"] = turi

    await query.message.reply_text(
        f"➕ *Yangi mijoz qo'shish*\n"
        f"{_progress(6)}\n\n"
        f"6️⃣ *{turi}* — kichik turni tanlang:",
        parse_mode="Markdown",
        reply_markup=savdo_subturi_kb(turi),
    )
    return ADD_SAVDO_SUBTURI

async def add_savdo_subturi_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subturi = query.data.replace("subturi_", "")
    ctx.user_data["savdo_subturi"] = subturi

    await query.message.reply_text(
        f"➕ *Yangi mijoz qo'shish*\n"
        f"{_progress(7)}\n\n"
        f"7️⃣ *Izoh* yozing _(ixtiyoriy)_:",
        parse_mode="Markdown",
        reply_markup=skip_cancel_kb(),
    )
    return ADD_IZOH

async def add_izoh(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["izoh"] = update.message.text.strip()
    return await _save_client(update, ctx)

async def add_izoh_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    ctx.user_data["izoh"] = ""
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

    data = {
        **ctx.user_data,
        "region_id":    region_id,
        "qoshgan_id":   user.id,
        "qoshgan_user": user.username or "",
        "qoshgan_nomi": user.full_name,
    }
    client_id = await add_client(data)
    is_admin  = _is_admin(user.id)

    text = (
        f"✅ *Mijoz muvaffaqiyatli saqlandi!*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *{data['ism']}*\n"
        f"📞 {data.get('telefon') or '—'}\n"
        f"📍 {data.get('manzil') or '—'}\n"
        f"💼 {data.get('kasb_turi') or '—'}\n"
        f"🏷 {data.get('savdo_turi') or '—'}\n"
        f"   ↳ {data.get('savdo_subturi') or '—'}\n"
        f"📝 {data.get('izoh') or '—'}\n"
        f"🗺 {REGION_MAP.get(region_id, '?')}"
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
        lines.append(
            f"{i}. *{c['ism']}* — {c['telefon'] or '—'}\n"
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
        turi = c['savdo_turi'] or '—'
        lines.append(
            f"{i}. *{c['ism']}* — {c['telefon'] or '—'}\n"
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
        lines.append(
            f"{i}. *{c['ism']}* — {c['telefon'] or '—'}\n"
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

    text = (
        f"👤 *{c['ism']}*  `(ID: {c['id']})`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📞 Telefon:       {c['telefon'] or '—'}\n"
        f"📍 Manzil:        {c['manzil'] or '—'}\n"
        f"💼 Kasb turi:     {c['kasb_turi'] or '—'}\n"
        f"🏷 Savdo turi:    {c['savdo_turi'] or '—'}\n"
        f"   ↳ Kichik tur:  {c['savdo_subturi'] or '—'}\n"
        f"📝 Izoh:          {c['izoh'] or '—'}\n"
        f"🗺 Viloyat:       {REGION_MAP.get(c['region_id'], '?')}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Qo'shgan:      {c['qoshgan_nomi']} (@{c['qoshgan_user']})\n"
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
    await query.message.reply_text(
        f"✏️ *{c['ism']}* ni tahrirlash\n\nQaysi maydonni o'zgartirmoqchisiz?",
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

    label_map = {
        "ism": "Ism-Familya", "telefon": "Telefon", "manzil": "Manzil",
        "kasb_turi": "Kasb turi", "izoh": "Izoh",
    }
    await query.message.reply_text(
        f"✏️ *{label_map.get(field, field)}* uchun yangi qiymat kiriting:",
        parse_mode="Markdown",
        reply_markup=cancel_kb(),
    )
    return EDIT_VALUE

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
        await update.message.reply_text(
            f"✏️ *{c['ism']}* ni tahrirlash\n\nQaysi maydonni o'zgartirmoqchisiz?",
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
    await query.message.reply_text(
        f"🗑 *{c['ism']}* ni o'chirishni tasdiqlaysizmi?\n"
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
    await update.message.reply_text(
        f"🗑 *{c['ism']}* ni o'chirishni tasdiqlaysizmi?",
        parse_mode="Markdown",
        reply_markup=confirm_delete_kb("delclient", client_id),
    )
    ctx.user_data.clear()
    return ConversationHandler.END
