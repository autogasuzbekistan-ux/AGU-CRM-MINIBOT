"""
Admin uchun maxsus handlerlar:
  - Foydalanuvchilar ro'yxati + bloklash/ochish + viloyat o'zgartirish
  - Qo'lda hisobot yuborish
  - Menejerlar faolligi reytingi
"""
import io
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS, REGION_MAP
from database import (
    get_all_users, get_today_clients, get_user,
    block_user, unblock_user, set_user_region, get_all_user_stats,
)
from keyboards import admin_main_menu_kb, manager_actions_kb, regions_kb, stats_menu_kb
from handlers.export import build_daily_excel


def _is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def _esc(text) -> str:
    return (str(text) or "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

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

# ─── FOYDALANUVCHILAR RO'YXATI + BOSHQARUV ───────────────────────────────────

@_admin_guard
async def admin_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    users = await get_all_users()
    managers = [u for u in users if u["role"] != "admin"]
    if not managers:
        await update.effective_message.reply_text(
            "👤 Hozircha menejerlar yo'q.",
            reply_markup=admin_main_menu_kb(),
        )
        return

    await update.effective_message.reply_text(
        f"👥 <b>Menejerlar ro'yxati</b> ({len(managers)} ta):\n\n"
        "Kerakli menjerning tugmalaridan foydalaning 👇",
        parse_mode="HTML",
        reply_markup=admin_main_menu_kb(),
    )
    for u in managers:
        region    = _esc(REGION_MAP.get(u["region_id"], "—") if u["region_id"] else "—")
        full_name = _esc(u["full_name"] or "—")
        username  = _esc(u["username"] or "—")
        is_blocked = bool(u.get("is_blocked", 0))
        status_icon = "🔴" if is_blocked else "🟢"
        text = (
            f"{status_icon} <b>{full_name}</b> (@{username})\n"
            f"   🏙 {region} | ID: <code>{u['telegram_id']}</code>"
        )
        await update.effective_message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=manager_actions_kb(u["telegram_id"], is_blocked),
        )

# ─── BLOKLASH / OCHISH ────────────────────────────────────────────────────────

@_admin_guard
async def admin_block_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data  # mgr_block_<id> yoki mgr_unblock_<id>
    parts = data.split("_")
    action = parts[1]        # "block" yoki "unblock"
    tid    = int(parts[2])

    if action == "block":
        await block_user(tid)
        status_icon = "🔴"
        msg = "🚫 Menejer bloklandi"
    else:
        await unblock_user(tid)
        status_icon = "🟢"
        msg = "✅ Menejer blokdan chiqarildi"

    target = await get_user(tid)
    full_name = _esc(target["full_name"] if target else tid)
    region    = _esc(REGION_MAP.get(target["region_id"], "—") if target and target["region_id"] else "—")
    is_blocked = (action == "block")

    await query.edit_message_text(
        f"{status_icon} <b>{full_name}</b>\n   🏙 {region} | ID: <code>{tid}</code>\n\n{msg}",
        parse_mode="HTML",
        reply_markup=manager_actions_kb(tid, is_blocked),
    )

# ─── MENEJER VILOYATINI O'ZGARTIRISH ─────────────────────────────────────────

@_admin_guard
async def admin_change_manager_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Menejer uchun viloyat tanlash oynasini ko'rsatish."""
    query = update.callback_query
    await query.answer()
    tid = int(query.data.split("_")[2])  # mgr_region_<id>
    ctx.user_data["mgr_region_for"] = tid

    target = await get_user(tid)
    full_name = _esc(target["full_name"] if target else tid)
    await query.message.reply_text(
        f"🗺 <b>{full_name}</b> uchun yangi viloyatni tanlang:",
        parse_mode="HTML",
        reply_markup=regions_kb(include_all=False),
    )

@_admin_guard
async def admin_set_manager_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin viloyat tanlaganda — menejerga o'rnatish."""
    query     = update.callback_query
    await query.answer()
    tid       = ctx.user_data.pop("mgr_region_for", None)
    if not tid:
        return
    region_id = int(query.data.split("_")[1])
    await set_user_region(tid, region_id)
    region_name = REGION_MAP.get(region_id, "Noma'lum")
    target = await get_user(tid)
    full_name = _esc(target["full_name"] if target else tid)
    await query.message.reply_text(
        f"✅ <b>{full_name}</b> ning viloyati <b>{_esc(region_name)}</b> ga o'zgartirildi.",
        parse_mode="HTML",
        reply_markup=admin_main_menu_kb(),
    )
    ctx.user_data.pop("mgr_region_for", None)

# ─── MENEJERLAR FAOLLIGI REYTINGI ────────────────────────────────────────────

@_admin_guard
async def admin_manager_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    rows  = await get_all_user_stats()
    mgrs  = [r for r in rows if r.get("role") != "admin"]

    if not mgrs:
        await update.effective_message.reply_text(
            "📊 Hozircha ma'lumot yo'q.",
            reply_markup=stats_menu_kb(is_admin=True),
        )
        return

    medals = ["🥇", "🥈", "🥉"]
    lines  = []
    for i, m in enumerate(mgrs, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name  = _esc(m.get("worker_name") or m.get("full_name") or "—")
        reg   = _esc(m.get("region_name") or "—")
        cnt   = m.get("client_count") or 0
        lines.append(f"{medal} <b>{name}</b> — {cnt} ta mijoz\n   🏙 {reg}")

    text = "👥 <b>Menejerlar faolligi reytingi:</b>\n\n" + "\n\n".join(lines)
    await update.effective_message.reply_text(
        text, parse_mode="HTML",
        reply_markup=stats_menu_kb(is_admin=True),
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
