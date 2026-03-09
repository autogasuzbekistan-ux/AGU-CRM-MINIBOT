"""
Admin uchun maxsus handlerlar:
  - Foydalanuvchilar ro'yxati
  - Qo'lda hisobot yuborish
  - Viloyat o'zgartirish
"""
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS, REGION_MAP
from database import get_all_users, get_today_clients, get_user
from keyboards import admin_main_menu_kb, back_kb, export_menu_kb
from handlers.export import build_daily_excel


def _is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def _admin_guard(func):
    """Dekorator: admin emaslar uchun bloklaydi"""
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not _is_admin(user.id):
            if update.callback_query:
                await update.callback_query.answer(
                    "❌ Bu funksiya faqat adminlar uchun!", show_alert=True
                )
            else:
                await update.message.reply_text("❌ Bu funksiya faqat adminlar uchun!")
            return
        return await func(update, ctx)
    return wrapper

# ─── FOYDALANUVCHILAR RO'YXATI ────────────────────────────────────────────────

@_admin_guard
async def admin_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    users = await get_all_users()
    if not users:
        await query.edit_message_text(
            "👤 Hozircha foydalanuvchilar yo'q.",
            reply_markup=back_kb("back_main"),
        )
        return

    lines = []
    for u in users:
        role_icon = "👑" if u["role"] == "admin" else "👤"
        region = REGION_MAP.get(u["region_id"], "—") if u["region_id"] else "—"
        lines.append(
            f"{role_icon} *{u['full_name']}* (@{u['username'] or '—'})\n"
            f"   🗺 {region} | ID: `{u['telegram_id']}`\n"
            f"   🕐 {u['created_at'] or '—'}"
        )

    text = (
        f"👥 *Foydalanuvchilar ro'yxati* ({len(users)} ta):\n\n"
        + "\n\n".join(lines)
    )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=back_kb("back_main"),
    )

# ─── QO'LDA HISOBOT YUBORISH ──────────────────────────────────────────────────

@_admin_guard
async def admin_send_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Adminning talabi bilan bugungi hisobotni darhol yuborish"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ Hisobot tayyorlanmoqda...")

    db_user   = await get_user(update.effective_user.id)
    region_id = db_user["region_id"] if db_user else None

    clients = await get_today_clients(region_id)
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")

    if not clients:
        await query.edit_message_text(
            f"📊 *{today}* — bugun hech qanday mijoz qo'shilmagan.",
            parse_mode="Markdown",
            reply_markup=back_kb("back_main"),
        )
        return

    import io
    wb = build_daily_excel(clients, today)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    region_name = REGION_MAP.get(region_id, "Umumiy") if region_id else "Umumiy"
    filename    = f"Hisobot_{region_name}_{today}.xlsx"

    await update.effective_chat.send_document(
        document=buffer,
        filename=filename,
        caption=(
            f"📊 *Kunlik hisobot — {today}*\n"
            f"🗺 {region_name}\n"
            f"👥 Bugun qo'shildi: *{len(clients)}* ta mijoz"
        ),
        parse_mode="Markdown",
    )
    await query.edit_message_text(
        "✅ Hisobot yuborildi!",
        reply_markup=back_kb("back_main"),
    )
