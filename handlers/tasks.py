from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_IDS, REGION_MAP
from database import get_user, add_task, get_tasks, complete_task, delete_task, get_client_by_id
from keyboards import tasks_menu_kb, task_action_kb, cancel_kb, confirm_delete_kb, admin_main_menu_kb, user_main_menu_kb

# ─── HOLATLAR ─────────────────────────────────────────────────────────────────
TASK_TITLE, TASK_CLIENT, TASK_DEADLINE, TASK_DESC = range(10, 14)

# ─── MENYU ────────────────────────────────────────────────────────────────────

async def tasks_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✅ *Vazifalar bo'limi*\n\nEslatmalar va vazifalarni boshqaring:",
        parse_mode="Markdown",
        reply_markup=tasks_menu_kb()
    )

# ─── VAZIFA QO'SHISH ──────────────────────────────────────────────────────────

async def task_add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """task_add yoki task_for_<client_id> callback"""
    query = update.callback_query
    await query.answer()
    ctx.user_data.clear()
    ctx.user_data["adding_task"] = True

    # Mijoz uchun vazifa
    if query.data.startswith("task_for_"):
        client_id = int(query.data.split("_")[-1])
        ctx.user_data["task_client_id"] = client_id
        c = await get_client_by_id(client_id)
        client_name = c["ism"] if c else f"ID:{client_id}"
        await query.edit_message_text(
            f"✅ *{client_name}* uchun vazifa qo'shish\n\n"
            "📝 Vazifa sarlavhasini kiriting:",
            parse_mode="Markdown",
            reply_markup=cancel_kb()
        )
    else:
        await query.edit_message_text(
            "✅ *Yangi vazifa qo'shish*\n\n"
            "📝 Vazifa sarlavhasini kiriting:",
            parse_mode="Markdown",
            reply_markup=cancel_kb()
        )
    return TASK_TITLE

async def task_title(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["task_title"] = update.message.text.strip()

    if ctx.user_data.get("task_client_id"):
        # Mijoz allaqachon tanlangan, muddatga o'tish
        await update.message.reply_text(
            "🗓 Muddat kiriting _(masalan: 2024-12-31 14:00)_\n"
            "_(o'tkazib yuborish uchun ➖ yozing)_:",
            parse_mode="Markdown",
            reply_markup=cancel_kb()
        )
        return TASK_DEADLINE

    await update.message.reply_text(
        "🔗 Mijoz ID sini kiriting _(ixtiyoriy, o'tkazish uchun 0 yozing)_:",
        reply_markup=cancel_kb()
    )
    return TASK_CLIENT

async def task_client(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "0":
        ctx.user_data["task_client_id"] = None
    else:
        try:
            ctx.user_data["task_client_id"] = int(text)
        except ValueError:
            ctx.user_data["task_client_id"] = None

    await update.message.reply_text(
        "🗓 Muddat kiriting _(masalan: 2024-12-31 14:00)_\n"
        "_(o'tkazish uchun ➖ yozing)_:",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
    return TASK_DEADLINE

async def task_deadline(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text in ("-", "—", "o'tkazish", "skip"):
        ctx.user_data["task_deadline"] = None
    else:
        ctx.user_data["task_deadline"] = text

    await update.message.reply_text(
        "📝 Tavsif yozing _(ixtiyoriy, ➖ yozing o'tkazish uchun)_:",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )
    return TASK_DESC

async def task_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    ctx.user_data["task_desc"] = "" if text in ("-", "—") else text

    user = update.effective_user
    db_user = await get_user(user.id)
    region_id = db_user["region_id"] if db_user else None

    if not region_id:
        await update.message.reply_text("❌ Avval viloyat tanlang! /start")
        ctx.user_data.clear()
        return ConversationHandler.END

    client_id = ctx.user_data.get("task_client_id")
    # Mijoz mavjudligini tekshirish
    if client_id:
        c = await get_client_by_id(client_id)
        if not c:
            client_id = None

    task_id = await add_task({
        "sarlavha":   ctx.user_data["task_title"],
        "tavsif":     ctx.user_data.get("task_desc", ""),
        "client_id":  client_id,
        "region_id":  region_id,
        "muddat":     ctx.user_data.get("task_deadline"),
        "qoshgan_id": user.id,
    })
    is_admin = user.id in ADMIN_IDS

    text = (
        f"✅ *Vazifa qo'shildi!*\n\n"
        f"📝 *{ctx.user_data['task_title']}*\n"
        f"🗓 Muddat: {ctx.user_data.get('task_deadline') or '—'}\n"
        f"📄 Tavsif: {ctx.user_data.get('task_desc') or '—'}\n"
        f"ID: `{task_id}`"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=admin_main_menu_kb() if is_admin else user_main_menu_kb()
    )
    ctx.user_data.clear()
    return ConversationHandler.END

# ─── VAZIFALAR RO'YXATI ───────────────────────────────────────────────────────

async def task_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    only_active = "done_list" not in query.data

    user = update.effective_user
    db_user = await get_user(user.id)
    region_id = db_user["region_id"] if db_user else None

    tasks = await get_tasks(region_id, only_active=only_active)

    if not tasks:
        status = "Faol" if only_active else "Bajarilgan"
        await query.edit_message_text(
            f"📋 {status} vazifalar yo'q.",
            reply_markup=tasks_menu_kb()
        )
        return

    lines = []
    for t in tasks:
        status = "✅" if t["bajarilgan"] else "🔔"
        client_info = f" → *{t['client_ism']}*" if t["client_ism"] else ""
        deadline = f"\n   🗓 {t['muddat']}" if t["muddat"] else ""
        lines.append(
            f"{status} *{t['sarlavha']}*{client_info}{deadline}\n"
            f"   🗺 {REGION_MAP.get(t['region_id'], '?')} | ID: `{t['id']}`"
        )

    title = "📋 *Faol vazifalar*" if only_active else "✅ *Bajarilgan vazifalar*"
    text = f"{title} ({len(tasks)} ta):\n\n" + "\n\n".join(lines)
    text += "\n\n_Amal uchun: /vazifa <ID>_"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=tasks_menu_kb())

async def task_detail_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Foydalanish: /vazifa <ID>")
        return
    # Vazifalar ro'yxatidan amal qilish
    try:
        task_id = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri ID!")
        return
    await update.message.reply_text(
        f"Vazifa `{task_id}` uchun amal tanlang:",
        parse_mode="Markdown",
        reply_markup=task_action_kb(task_id)
    )

async def task_complete_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.replace("task_complete_", ""))
    await complete_task(task_id)
    await query.edit_message_text(
        f"✅ Vazifa `{task_id}` bajarildi deb belgilandi!",
        parse_mode="Markdown",
        reply_markup=tasks_menu_kb()
    )

async def task_delete_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.replace("task_del_", ""))
    await query.edit_message_text(
        f"🗑 Vazifa `{task_id}` ni o'chirishni tasdiqlaysizmi?",
        parse_mode="Markdown",
        reply_markup=confirm_delete_kb("deltask", task_id)
    )

async def task_delete_confirm_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("_")[-1])
    await delete_task(task_id)
    await query.edit_message_text("✅ Vazifa o'chirildi.", reply_markup=tasks_menu_kb())
