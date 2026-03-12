"""
Admin uchun maxsus handlerlar:
  - Foydalanuvchilar ro'yxati
  - Qo'lda hisobot yuborish
"""
import io
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS, REGION_MAP
from database import get_all_users, get_today_clients, get_user
from keyboards import admin_main_menu_kb
from handlers.export import build_daily_excel


def _is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def _admin_guard(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not _is_admin(user.id):
            if update.callback_query:
                await update.callback_query.answer("❌ Bu funksiya faqat adminlar uchun!", show_alert=True)
            else:
                await update.message.reply_text("❌ Bu funksiya faqat adminlar uchun!")
            return
        return await func(update, ctx)
    return wrapper

# ─── FOYDALANUVCHILAR RO'YXATI ────────────────────────────────────────────────

@_admin_guard
async def admin_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    users = await get_all_users()
    if not users:
        await update.effective_message.reply_text(
            "👤 Hozircha foydalanuvchilar yo'q.",
            reply_markup=admin_main_menu_kb(),
        )
        return

    lines = []
    for u in users:
        role_icon = "👑" if u["role"] == "admin" else "👤"
        region    = REGION_MAP.get(u["region_id"], "—") if u["region_id"] else "—"
        full_name = (u['full_name'] or '—').replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        username  = (u['username'] or '—').replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(
            f"{role_icon} <b>{full_name}</b> (@{username})\n"
            f"   🏙 {region} | ID: <code>{u['telegram_id']}</code>\n"
            f"   🕐 {u['created_at'] or '—'}"
        )

    text = f"👥 <b>Foydalanuvchilar ro'yxati</b> ({len(users)} ta):\n\n" + "\n\n".join(lines)
    await update.effective_message.reply_text(
        text, parse_mode="HTML",
        reply_markup=admin_main_menu_kb(),
    )

# ─── QO'LDA HISOBOT YUBORISH ──────────────────────────────────────────────────

@_admin_guard
async def admin_send_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    loading = await update.effective_message.reply_text("⏳ Hisobot tayyorlanmoqda...")

    db_user   = await get_user(update.effective_user.id)
    region_id = db_user["region_id"] if db_user else None
    clients   = [dict(c) for c in await get_today_clients(region_id)]
    today     = date.today().strftime("%Y-%m-%d")

    if not clients:
        await loading.edit_text(
            f"📊 *{today}* — bugun hech qanday mijoz qo'shilmagan.",
            parse_mode="Markdown",
        )
        return

    wb     = build_daily_excel(clients, today)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    region_name = REGION_MAP.get(region_id, "Umumiy") if region_id else "Umumiy"
    await update.effective_chat.send_document(
        document=buffer,
        filename=f"Hisobot_{region_name}_{today}.xlsx",
        caption=(
            f"📊 *Kunlik hisobot — {today}*\n"
            f"🗺 {region_name}\n"
            f"👥 Bugun qo'shildi: *{len(clients)}* ta mijoz"
        ),
        parse_mode="Markdown",
    )
    await loading.edit_text("✅ Hisobot yuborildi!")
