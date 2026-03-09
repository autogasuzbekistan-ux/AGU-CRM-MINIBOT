from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_IDS, REGION_MAP, calculate_daraja
from database import (
    get_user, add_client, get_clients, search_clients,
    get_client_by_id, update_client, delete_client, count_clients
)
from keyboards import (
    clients_menu_kb, client_detail_kb, edit_fields_kb,
    savdo_turi_kb, cancel_kb, back_kb, confirm_delete_kb,
    pagination_kb, main_menu_kb
)

# ─── HOLATLAR ─────────────────────────────────────────────────────────────────
(
    ADD_ISM, ADD_TELEFON, ADD_TURI, ADD_SHAHAR,
    ADD_SAVDO, ADD_IZOH,
    SEARCH_QUERY,
    EDIT_VALUE,
    DELETE_CONFIRM,
) = range(9)

PAGE_SIZE = 8

# ─── YORDAMCHI ────────────────────────────────────────────────────────────────

def format_client(c, index: int = None) -> str:
    prefix = f"*{index}.* " if index else ""
    return (
        f"{prefix}👤 *{c['ism']}*\n"
        f"📞 {c['telefon'] or '—'}\n"
        f"🏷 {c['turi'] or '—'} | 🌆 {c['shahar'] or '—'}\n"
        f"💰 {c['savdo_hajmi'] or 0:,.0f}$ | {c['daraja']}\n"
        f"🗺 {REGION_MAP.get(c['region_id'], '?')}\n"
        f"🕐 {c['qoshilgan_vaqt']}"
    )

async def get_user_region(telegram_id: int):
    user = await get_user(telegram_id)
    return user["region_id"] if user else None

# ─── MIJOZLAR MENYUSI ─────────────────────────────────────────────────────────

async def clients_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👥 *Mijozlar bo'limi*\n\nQuyidagi amallardan birini tanlang:",
        parse_mode="Markdown",
        reply_markup=clients_menu_kb()
    )

# ─── MIJOZ QO'SHISH ───────────────────────────────────────────────────────────

async def client_add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data.clear()
    ctx.user_data["adding"] = True
    await query.edit_message_text(
        "➕ *Yangi mijoz qo'shish*\n\n"
        "1️⃣ Mijozning ism va familiyasini kiriting:",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
    return ADD_ISM

async def add_ism(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["ism"] = update.message.text.strip()
    await update.message.reply_text(
        "2️⃣ Telefon raqamini kiriting:\n_(masalan: +998901234567)_",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
    return ADD_TELEFON

async def add_telefon(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["telefon"] = update.message.text.strip()
    await update.message.reply_text(
        "3️⃣ Savdo turini tanlang:",
        reply_markup=savdo_turi_kb()
    )
    return ADD_TURI

async def add_turi_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["turi"] = query.data.replace("turi_", "")
    await query.edit_message_text(
        "4️⃣ Shahar yoki tumanni kiriting:",
        reply_markup=cancel_kb()
    )
    return ADD_SHAHAR

async def add_shahar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["shahar"] = update.message.text.strip()
    await update.message.reply_text(
        "5️⃣ Savdo hajmini kiriting _(dollar, son)_:\n_(masalan: 5000)_",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
    return ADD_SAVDO

async def add_savdo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", "").replace(" ", "")
    try:
        savdo = float(text)
    except ValueError:
        await update.message.reply_text(
            "❌ Raqam kiriting (masalan: 5000):",
            reply_markup=cancel_kb()
        )
        return ADD_SAVDO
    ctx.user_data["savdo_hajmi"] = savdo
    ctx.user_data["daraja"] = calculate_daraja(savdo)
    await update.message.reply_text(
        "6️⃣ Izoh yozing _(ixtiyoriy, o'tkazib yuborish uchun ➡️ bosing)_:",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
    return ADD_IZOH

async def add_izoh(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["izoh"] = update.message.text.strip()
    return await _save_client(update, ctx)

async def add_izoh_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["izoh"] = ""
    return await _save_client(update, ctx, from_callback=True)

async def _save_client(update: Update, ctx: ContextTypes.DEFAULT_TYPE, from_callback: bool = False):
    user = update.effective_user
    region_id = await get_user_region(user.id)
    if not region_id:
        msg = "❌ Avval viloyat tanlang! /start"
        if from_callback:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
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
    is_admin = user.id in ADMIN_IDS

    text = (
        f"✅ *Mijoz saqlandi!*\n\n"
        f"👤 *{data['ism']}*\n"
        f"📞 {data['telefon']}\n"
        f"🏷 {data['turi']} | 🌆 {data['shahar']}\n"
        f"💰 {data['savdo_hajmi']:,.0f}$ | {data['daraja']}\n"
        f"📝 {data.get('izoh') or '—'}\n"
        f"🗺 {REGION_MAP.get(region_id, '?')}"
    )
    kb = client_detail_kb(client_id)
    if from_callback:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

    ctx.user_data.clear()
    return ConversationHandler.END

# ─── MIJOZLAR RO'YXATI ────────────────────────────────────────────────────────

async def client_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data  # "client_list" yoki "clist_page_2"
    page = 0
    if "_page_" in data:
        page = int(data.split("_page_")[-1])

    user = update.effective_user
    region_id = await get_user_region(user.id)
    total = await count_clients(region_id)

    if total == 0:
        await query.edit_message_text(
            "📋 Bazada hech qanday mijoz yo'q.",
            reply_markup=clients_menu_kb()
        )
        return

    clients = await get_clients(region_id, limit=PAGE_SIZE, offset=page * PAGE_SIZE)
    lines = []
    for i, c in enumerate(clients, start=page * PAGE_SIZE + 1):
        lines.append(f"{i}. [{c['ism']}](tg://user?id=0) — {c['telefon'] or '—'} | {c['daraja']}")

    text = (
        f"📋 *Mijozlar ro'yxati* ({total} ta)\n"
        f"_(sahifa {page + 1})_\n\n" +
        "\n".join(lines) +
        "\n\n_Mijoz tafsilotlari uchun ID raqamini /mijoz <ID> yuboring_"
    )
    kb = pagination_kb(page, total, PAGE_SIZE, "clist")
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

# ─── MIJOZ QIDIRISH ───────────────────────────────────────────────────────────

async def client_search_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔍 *Mijoz qidirish*\n\n"
        "Ism, telefon yoki shahar bo'yicha qidiring:",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
    return SEARCH_QUERY

async def client_search_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.message.text.strip()
    user = update.effective_user
    region_id = await get_user_region(user.id)
    results = await search_clients(q, region_id)
    is_admin = user.id in ADMIN_IDS

    if not results:
        await update.message.reply_text(
            f"❌ *'{q}'* bo'yicha hech narsa topilmadi.",
            parse_mode="Markdown",
            reply_markup=main_menu_kb(is_admin=is_admin)
        )
        return ConversationHandler.END

    lines = []
    for i, c in enumerate(results, 1):
        lines.append(
            f"{i}. *{c['ism']}* — {c['telefon'] or '—'}\n"
            f"   🏷 {c['turi'] or '—'} | 🌆 {c['shahar'] or '—'} | {c['daraja']}\n"
            f"   🗺 {REGION_MAP.get(c['region_id'], '?')} | ID: `{c['id']}`"
        )

    text = f"🔍 *'{q}'* bo'yicha natijalar ({len(results)} ta):\n\n" + "\n\n".join(lines)
    text += "\n\n_Tafsilot uchun: /mijoz ID_"
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=main_menu_kb(is_admin=is_admin)
    )
    return ConversationHandler.END

# ─── MIJOZ TAFSILOTI (/mijoz <id>) ───────────────────────────────────────────

async def client_detail_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Foydalanish: /mijoz <ID>")
        return
    try:
        client_id = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri ID!")
        return
    await _show_client_detail(update, ctx, client_id, via_message=True)

async def client_detail_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.replace("client_detail_", ""))
    await _show_client_detail(update, ctx, client_id)

async def _show_client_detail(update: Update, ctx: ContextTypes.DEFAULT_TYPE,
                               client_id: int, via_message: bool = False):
    c = await get_client_by_id(client_id)
    if not c:
        txt = "❌ Mijoz topilmadi!"
        if via_message:
            await update.message.reply_text(txt)
        else:
            await update.callback_query.edit_message_text(txt)
        return

    text = (
        f"👤 *{c['ism']}*  `(ID: {c['id']})`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📞 Telefon:    {c['telefon'] or '—'}\n"
        f"🏷 Turi:       {c['turi'] or '—'}\n"
        f"🌆 Shahar:     {c['shahar'] or '—'}\n"
        f"🗺 Viloyat:    {REGION_MAP.get(c['region_id'], '?')}\n"
        f"💰 Savdo:      {c['savdo_hajmi'] or 0:,.0f}$\n"
        f"⭐ Daraja:     {c['daraja']}\n"
        f"📝 Izoh:       {c['izoh'] or '—'}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Qo'shgan:   {c['qoshgan_nomi']} (@{c['qoshgan_user']})\n"
        f"🕐 Qo'shilgan: {c['qoshilgan_vaqt']}\n"
        f"🔄 Yangilangan: {c['yangilangan_vaqt']}"
    )
    kb = client_detail_kb(client_id)
    if via_message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

# ─── MIJOZ TAHRIRLASH ─────────────────────────────────────────────────────────

async def edit_start_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """edit_<client_id>"""
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[1])
    c = await get_client_by_id(client_id)
    if not c:
        await query.edit_message_text("❌ Mijoz topilmadi!")
        return

    ctx.user_data["edit_client_id"] = client_id
    await query.edit_message_text(
        f"✏️ *{c['ism']}* ni tahrirlash\n\nQaysi maydonni o'zgartirmoqchisiz?",
        parse_mode="Markdown",
        reply_markup=edit_fields_kb(client_id)
    )

async def edit_field_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """editfield_<client_id>_<field>"""
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    client_id = int(parts[1])
    field = parts[2]

    field_names = {
        "ism": "Ism", "telefon": "Telefon", "turi": "Savdo turi",
        "shahar": "Shahar", "savdo_hajmi": "Savdo hajmi ($)", "izoh": "Izoh"
    }

    if field == "turi":
        ctx.user_data["edit_client_id"] = client_id
        ctx.user_data["edit_field"] = field
        await query.edit_message_text(
            "🏷 Yangi savdo turini tanlang:",
            reply_markup=savdo_turi_kb()
        )
    else:
        ctx.user_data["edit_client_id"] = client_id
        ctx.user_data["edit_field"] = field
        await query.edit_message_text(
            f"✏️ *{field_names.get(field, field)}* uchun yangi qiymat kiriting:",
            parse_mode="Markdown",
            reply_markup=cancel_kb()
        )
    return EDIT_VALUE

async def edit_turi_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """turi_<value> — tahrirlash oqimida"""
    query = update.callback_query
    await query.answer()
    client_id = ctx.user_data.get("edit_client_id")
    if not client_id:
        await query.edit_message_text("❌ Xato. Qaytadan urinib ko'ring.")
        return ConversationHandler.END
    value = query.data.replace("turi_", "")
    await update_client(client_id, "turi", value)
    ctx.user_data.clear()
    await query.edit_message_text(f"✅ Savdo turi yangilandi: *{value}*", parse_mode="Markdown",
                                   reply_markup=client_detail_kb(client_id))
    return ConversationHandler.END

async def edit_value_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    client_id = ctx.user_data.get("edit_client_id")
    field = ctx.user_data.get("edit_field")
    if not client_id or not field:
        await update.message.reply_text("❌ Xato. /start bosing.")
        return ConversationHandler.END

    value = update.message.text.strip()

    if field == "savdo_hajmi":
        try:
            value = str(float(value.replace(",", "").replace(" ", "")))
            # Darajani yangilash
            new_daraja = calculate_daraja(float(value))
            await update_client(client_id, "daraja", new_daraja)
        except ValueError:
            await update.message.reply_text(
                "❌ Raqam kiriting:", reply_markup=cancel_kb()
            )
            return EDIT_VALUE

    await update_client(client_id, field, value)
    ctx.user_data.clear()
    await update.message.reply_text(
        "✅ *Muvaffaqiyatli yangilandi!*",
        parse_mode="Markdown",
        reply_markup=client_detail_kb(client_id)
    )
    return ConversationHandler.END

# ─── MIJOZ O'CHIRISH ──────────────────────────────────────────────────────────

async def delete_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """del_<client_id>"""
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[1])
    c = await get_client_by_id(client_id)
    if not c:
        await query.edit_message_text("❌ Mijoz topilmadi!")
        return

    await query.edit_message_text(
        f"🗑 *{c['ism']}* ni o'chirishni tasdiqlaysizmi?\n"
        "_(Barcha bog'liq vazifalar ham o'chadi)_",
        parse_mode="Markdown",
        reply_markup=confirm_delete_kb("delclient", client_id)
    )

async def delete_confirm_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """delclient_confirm_<client_id>"""
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[-1])
    await delete_client(client_id)
    is_admin = update.effective_user.id in ADMIN_IDS
    await query.edit_message_text(
        "✅ Mijoz o'chirildi.",
        reply_markup=main_menu_kb(is_admin=is_admin)
    )

# ─── INLINE QIDIRUV (ConversationHandler uchun) ───────────────────────────────

async def edit_start_ask_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Inline tahrirlash: foydalanuvchi ID kiritadi"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✏️ Tahrirlash uchun mijoz ID sini kiriting:\n_(ID ni ro'yxatdan topishingiz mumkin)_",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
    ctx.user_data["awaiting_edit_id"] = True
    return EDIT_VALUE

async def delete_ask_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Inline o'chirish: foydalanuvchi ID kiritadi"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🗑 O'chirish uchun mijoz ID sini kiriting:",
        reply_markup=cancel_kb()
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
        await update.message.reply_text("❌ Mijoz topilmadi. Boshqa ID kiriting:", reply_markup=cancel_kb())
        return DELETE_CONFIRM
    await update.message.reply_text(
        f"🗑 *{c['ism']}* ni o'chirishni tasdiqlaysizmi?",
        parse_mode="Markdown",
        reply_markup=confirm_delete_kb("delclient", client_id)
    )
    ctx.user_data.clear()
    return ConversationHandler.END
