from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_IDS, REGION_MAP
from database import get_user, upsert_user, set_user_region
from keyboards import (
    admin_main_menu_kb, user_main_menu_kb, regions_kb,
    BTN_CANCEL,
)

def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ─── /start ───────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    is_admin = _is_admin(user.id)

    await upsert_user(
        telegram_id=user.id,
        username=user.username or "",
        full_name=user.full_name,
        role="admin" if is_admin else "manager",
    )

    db_user = await get_user(user.id)

    if not db_user or not db_user["region_id"]:
        await update.effective_message.reply_text(
            f"👋 Xush kelibsiz, *{user.full_name}*!\n\n"
            "🗺 Iltimos, o'z viloyatingizni tanlang:",
            parse_mode="Markdown",
            reply_markup=regions_kb(include_all=is_admin),
        )
        return

    region_name = REGION_MAP.get(db_user["region_id"], "Barcha viloyatlar 🌍")

    if is_admin:
        text = (
            f"👑 *ADMIN PANEL*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {user.full_name}\n"
            f"🗺 Viloyat: *{region_name}*\n\n"
            f"Quyidagi amallardan birini tanlang:"
        )
    else:
        text = (
            f"📋 *Mening menyum*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {user.full_name}\n"
            f"🗺 {region_name}\n\n"
            f"Nima qilmoqchisiz?"
        )

    kb = admin_main_menu_kb() if is_admin else user_main_menu_kb()
    await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

# ─── VILOYAT TANLASH ──────────────────────────────────────────────────────────

async def handle_region_selection(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    user     = update.effective_user
    is_admin = _is_admin(user.id)
    data     = query.data

    if data == "region_all":
        if not is_admin:
            await query.answer("Bu funksiya faqat adminlar uchun!", show_alert=True)
            return
        await set_user_region(user.id, None)
        region_name = "Barcha viloyatlar 🌍"
    else:
        region_id = int(data.split("_")[1])
        await set_user_region(user.id, region_id)
        region_name = REGION_MAP.get(region_id, "Noma'lum")

    await upsert_user(
        telegram_id=user.id,
        username=user.username or "",
        full_name=user.full_name,
        role="admin" if is_admin else "manager",
    )

    if is_admin:
        text = (
            f"👑 *ADMIN PANEL*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Viloyat: *{region_name}*\n\n"
            f"Quyidagi amallardan birini tanlang:"
        )
    else:
        text = (
            f"✅ Viloyat tanlandi: *{region_name}*\n\n"
            f"Nima qilmoqchisiz?"
        )

    kb = admin_main_menu_kb() if is_admin else user_main_menu_kb()
    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

# ─── VILOYAT O'ZGARTIRISH ─────────────────────────────────────────────────────

async def change_region_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    is_admin = _is_admin(update.effective_user.id)
    if update.callback_query:
        await update.callback_query.answer()
    await update.effective_message.reply_text(
        "🗺 Viloyat tanlang:",
        reply_markup=regions_kb(include_all=is_admin),
    )

# ─── ORQAGA / BEKOR QILISH ───────────────────────────────────────────────────

async def back_to_main(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    ctx.user_data.clear()
    await start(update, ctx)

async def handle_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    ctx.user_data.clear()
    user     = update.effective_user
    is_admin = _is_admin(user.id)
    kb = admin_main_menu_kb() if is_admin else user_main_menu_kb()
    await update.effective_message.reply_text(
        "❌ Bekor qilindi. Asosiy menyu:",
        reply_markup=kb,
    )
    return ConversationHandler.END

async def noop_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
