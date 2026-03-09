from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS, REGION_MAP, REGIONS
from database import get_user, get_stats
from keyboards import stats_menu_kb, regions_kb, back_kb, main_menu_kb

async def stats_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    is_admin = update.effective_user.id in ADMIN_IDS
    await query.edit_message_text(
        "📊 *Statistika*\n\nQaysi ko'rsatkichni ko'rmoqchisiz?",
        parse_mode="Markdown",
        reply_markup=stats_menu_kb(is_admin=is_admin)
    )

async def stats_general(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    db_user = await get_user(user.id)
    region_id = db_user["region_id"] if db_user else None
    is_admin = user.id in ADMIN_IDS

    stats = await get_stats(region_id)
    region_name = REGION_MAP.get(region_id, "Barcha viloyatlar") if region_id else "Barcha viloyatlar 🌍"

    text = (
        f"📊 *Umumiy statistika*\n"
        f"🗺 {region_name}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Jami mijozlar:  *{stats['total_clients']}* ta\n"
        f"💰 Jami savdo:     *{stats['total_sales']:,.0f}$*\n"
    )
    if stats["total_clients"] > 0:
        avg = stats["total_sales"] / stats["total_clients"]
        text += f"📈 O'rtacha savdo:  *{avg:,.0f}$*\n"

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=back_kb("menu_stats")
    )

async def stats_by_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    is_admin = user.id in ADMIN_IDS

    # Admin barcha viloyatlarni ko'radi
    stats = await get_stats(region_id=None)
    by_region = stats["by_region"]

    if not by_region:
        await query.edit_message_text("📊 Hozircha ma'lumot yo'q.", reply_markup=back_kb("menu_stats"))
        return

    lines = []
    for i, r in enumerate(by_region, 1):
        lines.append(
            f"{i}. 🗺 *{r['name']}*\n"
            f"   👥 {r['cnt']} ta | 💰 {(r['total'] or 0):,.0f}$"
        )

    text = "🗺 *Viloyatlar bo'yicha statistika:*\n\n" + "\n\n".join(lines)
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=back_kb("menu_stats")
    )

async def stats_by_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    db_user = await get_user(user.id)
    region_id = db_user["region_id"] if db_user else None

    stats = await get_stats(region_id)
    by_type = stats["by_type"]

    if not by_type:
        await query.edit_message_text("📊 Hozircha ma'lumot yo'q.", reply_markup=back_kb("menu_stats"))
        return

    total = stats["total_clients"] or 1
    lines = []
    for t in by_type:
        pct = (t["cnt"] / total) * 100
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        lines.append(f"🏷 *{t['turi'] or 'Noma\\'lum'}*: {t['cnt']} ta ({pct:.1f}%)\n   `{bar}`")

    text = "📈 *Savdo turlari bo'yicha:*\n\n" + "\n\n".join(lines)
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=back_kb("menu_stats")
    )

async def stats_by_grade(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    db_user = await get_user(user.id)
    region_id = db_user["region_id"] if db_user else None

    stats = await get_stats(region_id)
    by_grade = stats["by_grade"]

    if not by_grade:
        await query.edit_message_text("📊 Hozircha ma'lumot yo'q.", reply_markup=back_kb("menu_stats"))
        return

    grade_order = ["💎 VIP", "🥇 3-daraja", "🥈 2-daraja", "🥉 1-daraja", "🆕 Yangi"]
    grade_dict = {g["daraja"]: g["cnt"] for g in by_grade}

    lines = []
    for g in grade_order:
        cnt = grade_dict.get(g, 0)
        if cnt > 0:
            lines.append(f"{g}: *{cnt}* ta")

    text = "⭐ *Darajalar bo'yicha:*\n\n" + "\n".join(lines)
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=back_kb("menu_stats")
    )
