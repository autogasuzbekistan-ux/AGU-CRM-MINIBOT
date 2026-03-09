import io
from datetime import datetime
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from config import ADMIN_IDS, REGION_MAP, REGIONS
from database import get_user, get_clients
from keyboards import export_menu_kb, regions_kb, back_kb, main_menu_kb

# ─── MENYU ────────────────────────────────────────────────────────────────────

async def export_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    is_admin = update.effective_user.id in ADMIN_IDS
    await query.edit_message_text(
        "📤 *Excel eksport*\n\nQaysi ma'lumotlarni eksport qilmoqchisiz?",
        parse_mode="Markdown",
        reply_markup=export_menu_kb(is_admin=is_admin)
    )

async def export_my_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    db_user = await get_user(user.id)
    region_id = db_user["region_id"] if db_user else None
    await _do_export(update, ctx, region_id)

async def export_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("Bu funksiya faqat adminlar uchun!", show_alert=True)
        return
    await _do_export(update, ctx, region_id=None)

async def export_choose_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("Bu funksiya faqat adminlar uchun!", show_alert=True)
        return
    await query.edit_message_text(
        "🗺 Eksport uchun viloyat tanlang:",
        reply_markup=regions_kb(include_all=True)
    )
    ctx.user_data["export_choosing"] = True

async def export_region_selected(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """region_<id> callback — export oqimida"""
    if not ctx.user_data.get("export_choosing"):
        return  # Boshqa handler boshqaradi
    query = update.callback_query
    await query.answer()
    ctx.user_data.pop("export_choosing", None)
    data = query.data
    if data == "region_all":
        region_id = None
    else:
        region_id = int(data.split("_")[1])
    await _do_export(update, ctx, region_id)

# ─── EXCEL YARATISH ───────────────────────────────────────────────────────────

async def _do_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE, region_id: int = None):
    query = update.callback_query

    await query.edit_message_text("⏳ Excel fayl tayyorlanmoqda...")

    clients = await get_clients(region_id, limit=5000)
    if not clients:
        is_admin = update.effective_user.id in ADMIN_IDS
        await query.edit_message_text(
            "❌ Eksport qilish uchun mijozlar yo'q.",
            reply_markup=export_menu_kb(is_admin=is_admin)
        )
        return

    wb = _create_workbook(clients, region_id)

    # Xotiraga yozish
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    region_name = REGION_MAP.get(region_id, "Umumiy") if region_id else "Umumiy"
    filename = f"CRM_{region_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    await update.effective_chat.send_document(
        document=InputFile(buffer, filename=filename),
        caption=(
            f"📊 *{region_name} CRM bazasi*\n"
            f"👥 Jami: {len(clients)} ta mijoz\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ),
        parse_mode="Markdown"
    )

    is_admin = update.effective_user.id in ADMIN_IDS
    await query.edit_message_text(
        "✅ Excel fayl yuborildi!",
        reply_markup=export_menu_kb(is_admin=is_admin)
    )

def _create_workbook(clients, region_id: int = None) -> Workbook:
    wb = Workbook()

    if region_id:
        # Bitta viloyat — bitta varaq
        ws = wb.active
        ws.title = REGION_MAP.get(region_id, "Viloyat")[:31]
        _fill_sheet(ws, clients)
    else:
        # Har bir viloyat uchun alohida varaq + umumiy varaq
        wb.remove(wb.active)  # bo'sh varaqni o'chirish

        # Umumiy varaq
        ws_all = wb.create_sheet("Umumiy")
        _fill_sheet(ws_all, clients)

        # Viloyat bo'yicha
        from collections import defaultdict
        by_region = defaultdict(list)
        for c in clients:
            by_region[c["region_id"]].append(c)

        for region in REGIONS:
            rid = region["id"]
            if rid in by_region:
                ws = wb.create_sheet(region["name"][:31])
                _fill_sheet(ws, by_region[rid])

    return wb

def _fill_sheet(ws, clients):
    # ─ SARLAVHA ─
    headers = [
        "№", "Ism", "Telefon", "Turi", "Shahar", "Viloyat",
        "Savdo ($)", "Daraja", "Izoh",
        "Qo'shgan", "Username", "Qo'shilgan vaqt", "Yangilangan"
    ]
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    ws.row_dimensions[1].height = 30

    # ─ MA'LUMOTLAR ─
    alt_fill = PatternFill("solid", fgColor="DDEEFF")
    for i, c in enumerate(clients, 1):
        row = i + 1
        fill = alt_fill if i % 2 == 0 else PatternFill()
        values = [
            i,
            c["ism"],
            c["telefon"] or "",
            c["turi"] or "",
            c["shahar"] or "",
            REGION_MAP.get(c["region_id"], ""),
            c["savdo_hajmi"] or 0,
            c["daraja"] or "",
            c["izoh"] or "",
            c["qoshgan_nomi"] or "",
            f"@{c['qoshgan_user']}" if c["qoshgan_user"] else "",
            c["qoshilgan_vaqt"] or "",
            c["yangilangan_vaqt"] or "",
        ]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.fill = fill
            cell.border = border
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if col == 7:  # Savdo
                cell.number_format = "#,##0.00"
                cell.alignment = Alignment(horizontal="right", vertical="center")

    # ─ USTUN KENGLIKLARI ─
    col_widths = [5, 25, 18, 12, 15, 20, 14, 14, 30, 20, 16, 20, 20]
    for col, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width

    # ─ FREEZE HEADER ─
    ws.freeze_panes = "A2"

    # ─ UMUMIY JAMI ─
    total_row = len(clients) + 2
    ws.cell(row=total_row, column=1, value="JAMI:")
    ws.cell(row=total_row, column=1).font = Font(bold=True)
    total_cell = ws.cell(row=total_row, column=7, value=sum(c["savdo_hajmi"] or 0 for c in clients))
    total_cell.font = Font(bold=True, color="1F4E79")
    total_cell.number_format = "#,##0.00"
    count_cell = ws.cell(row=total_row, column=2, value=f"{len(clients)} ta mijoz")
    count_cell.font = Font(bold=True)
