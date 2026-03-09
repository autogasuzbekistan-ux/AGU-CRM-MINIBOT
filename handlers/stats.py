from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS, REGION_MAP, SAVDO_TURLARI
from database import get_user, get_stats
from keyboards import stats_menu_kb, back_kb

async def stats_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📊 *Statistika*\n\nQaysi ko'rsatkichni ko'rmoqchisiz?",
        parse_mode="Markdown",
        reply_markup=stats_menu_kb(),
    )

async def stats_general(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await query.answer()
    db_user   = await get_user(update.effective_user.id)
    region_id = db_user["region_id"] if db_user else None
    stats     = await get_stats(region_id)
    region_name = REGION_MAP.get(region_id, "Barcha viloyatlar 🌍") if region_id else "Barcha viloyatlar 🌍"

    total = stats["total_clients"]
    text  = (
        f"📊 *Umumiy statistika*\n"
        f"🗺 {region_name}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Jami mijozlar: *{total}* ta\n"
    )
    # Savdo turlar bo'yicha qisqacha
    if stats["by_type"]:
        text += "\n📈 *Savdo turlari:*\n"
        for t in stats["by_type"]:
            name = t.get("savdo_turi") or "Noma'lum"
            text += f"  • {name}: *{t['cnt']}* ta\n"

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=back_kb("menu_stats"),
    )

async def stats_by_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stats     = await get_stats(region_id=None)
    by_region = stats["by_region"]

    if not by_region:
        await query.edit_message_text(
            "📊 Hozircha ma'lumot yo'q.", reply_markup=back_kb("menu_stats")
        )
        return

    lines = []
    for i, r in enumerate(by_region, 1):
        lines.append(
            f"{i}. 🗺 *{r['name']}*\n"
            f"   👥 {r['cnt']} ta mijoz"
        )

    text = "🗺 *Viloyatlar bo'yicha statistika:*\n\n" + "\n\n".join(lines)
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=back_kb("menu_stats"),
    )

async def stats_by_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await query.answer()
    db_user   = await get_user(update.effective_user.id)
    region_id = db_user["region_id"] if db_user else None
    stats     = await get_stats(region_id)
    by_type   = stats["by_type"]

    if not by_type:
        await query.edit_message_text(
            "📊 Hozircha ma'lumot yo'q.", reply_markup=back_kb("menu_stats")
        )
        return

    total = stats["total_clients"] or 1
    # Rang belgisi
    _icons = {"Ulgurji savdo": "🟢", "Chakana savdo": "🟡", "Servis": "🔵"}

    lines = []
    for t in by_type:
        name = t.get("savdo_turi") or "Noma'lum"
        pct  = (t["cnt"] / total) * 100
        bar  = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        icon = _icons.get(name, "🏷")
        lines.append(
            f"{icon} *{name}*: {t['cnt']} ta ({pct:.1f}%)\n"
            f"   `{bar}`"
        )

    text = "🏷 *Savdo turlari bo'yicha:*\n\n" + "\n\n".join(lines)
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=back_kb("menu_stats"),
    )

async def stats_by_grade(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kichik turlar bo'yicha statistika"""
    query     = update.callback_query
    await query.answer()
    db_user   = await get_user(update.effective_user.id)
    region_id = db_user["region_id"] if db_user else None
    stats     = await get_stats(region_id)
    by_sub    = stats["by_sub"]

    if not by_sub:
        await query.edit_message_text(
            "📊 Hozircha ma'lumot yo'q.", reply_markup=back_kb("menu_stats")
        )
        return

    total = stats["total_clients"] or 1
    lines = []
    for s in by_sub:
        name = s.get("savdo_subturi") or "Noma'lum"
        pct  = (s["cnt"] / total) * 100
        lines.append(f"  ↳ *{name}*: {s['cnt']} ta ({pct:.1f}%)")

    text = "🔍 *Kichik turlar bo'yicha:*\n\n" + "\n".join(lines)
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=back_kb("menu_stats"),
    )
