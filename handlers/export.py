"""
Excel eksport:
  - Rasm kabi format: No | Ism-Familya | Telefon Raqam | Manzil | Kasb turi | Savdo Turi | Izoh
  - Savdo Turi katakchalari rangli (Ulgurji=yashil, Chakana=sariq, Servis=moviy)
  - Kechki 22:00 da avtomatik kunlik hisobot
  - Qo'lda eksport: mening viloyatim / barcha viloyatlar
"""
import io
from datetime import datetime, date
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, GradientFill
)
from openpyxl.utils import get_column_letter

from telegram import Update, InputFile
from telegram.ext import ContextTypes

from config import ADMIN_IDS, REGION_MAP, REGIONS, SAVDO_COLORS
from database import get_user, get_clients, get_today_clients
from keyboards import export_menu_kb, regions_kb, back_kb

# ─── RANGLAR VA USLUBLAR ──────────────────────────────────────────────────────

_HEADER_FILL  = PatternFill("solid", fgColor="BDD7EE")   # och ko'k (rasmdagi kabi)
_HEADER_FONT  = Font(bold=True, size=11, color="1F3864")
_ALT_FILL     = PatternFill("solid", fgColor="F2F2F2")   # kulrang qator
_TOTAL_FILL   = PatternFill("solid", fgColor="1F3864")
_TOTAL_FONT   = Font(bold=True, color="FFFFFF", size=11)

_THIN = Side(style="thin", color="9DC3E6")
_CELL_BORDER = Border(
    left=_THIN, right=_THIN, top=_THIN, bottom=_THIN
)

# Savdo turi bo'yicha katakcha rangi
_SAVDO_FILL = {
    k: PatternFill("solid", fgColor=v) for k, v in SAVDO_COLORS.items()
}
_DEFAULT_FILL = PatternFill()

# Ustun kengliklar: No | Ism-Familya | Telefon | Manzil | Kasb turi | Savdo Turi | Izoh
_COL_WIDTHS = [5, 28, 18, 24, 20, 22, 35]
_HEADERS    = [
    "No", "Ism - Familya", "Telefon Raqam",
    "Manzil", "Kasb turi", "Savdo Turi", "Izoh"
]

# ─── ASOSIY EXCEL YARATUVCHI ──────────────────────────────────────────────────

def _apply_header(ws):
    """Sarlavha qatorini bezatish"""
    for col, h in enumerate(_HEADERS, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill      = _HEADER_FILL
        cell.font      = _HEADER_FONT
        cell.border    = _CELL_BORDER
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
    ws.row_dimensions[1].height = 28
    ws.freeze_panes = "A2"

def _apply_col_widths(ws):
    for col, width in enumerate(_COL_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(col)].width = width

def _write_client_row(ws, row: int, idx: int, c: dict, alt: bool):
    """Bitta mijoz qatorini yozish"""
    turi   = c.get("savdo_turi") or ""
    values = [
        idx,
        c.get("ism") or "",
        c.get("telefon") or "",
        c.get("manzil") or "",
        c.get("kasb_turi") or "",
        turi,
        c.get("izoh") or "",
    ]
    row_fill = _ALT_FILL if alt else _DEFAULT_FILL

    for col, val in enumerate(values, 1):
        cell = ws.cell(row=row, column=col, value=val)
        cell.border    = _CELL_BORDER
        cell.alignment = Alignment(vertical="center", wrap_text=True)

        if col == 6 and turi:
            # Savdo Turi katakchasi — rangli
            cell.fill = _SAVDO_FILL.get(turi, row_fill)
            cell.font = Font(bold=True, color="FFFFFF" if turi == "Servis" else "1F3864")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        elif col == 1:
            cell.fill      = row_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.fill = row_fill

def _write_legend(ws, start_row: int):
    """O'ng tomonga Savdo turi legenda"""
    legend_col = len(_HEADERS) + 2   # H ustuni (qo'shimcha)
    ws.cell(row=start_row, column=legend_col, value="Savdo turi ranglari:").font = Font(bold=True)
    for i, (name, color) in enumerate(SAVDO_COLORS.items(), 1):
        cell = ws.cell(row=start_row + i, column=legend_col, value=name)
        cell.fill = PatternFill("solid", fgColor=color)
        cell.font = Font(bold=True, color="FFFFFF" if name == "Servis" else "1F3864")
        cell.border = _CELL_BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(legend_col)].width = 22

def _fill_sheet(ws, clients: list, title: str = ""):
    """Bir varaqni to'ldirish"""
    if title:
        ws.cell(row=1, column=1)  # keyingi qadamda sarlavha qo'yiladi

    _apply_header(ws)
    _apply_col_widths(ws)

    for i, c in enumerate(clients, 1):
        _write_client_row(ws, row=i + 1, idx=i, c=c, alt=(i % 2 == 0))

    # Jami qatori
    total_row = len(clients) + 2
    ws.cell(row=total_row, column=1, value="Jami:").fill = _TOTAL_FILL
    ws.cell(row=total_row, column=1).font = _TOTAL_FONT
    ws.cell(row=total_row, column=1).alignment = Alignment(horizontal="center")
    cnt_cell = ws.cell(row=total_row, column=2, value=f"{len(clients)} ta mijoz")
    cnt_cell.fill = _TOTAL_FILL
    cnt_cell.font = _TOTAL_FONT
    for col in range(3, len(_HEADERS) + 1):
        ws.cell(row=total_row, column=col).fill = _TOTAL_FILL

    _write_legend(ws, start_row=2)

# ─── KUNLIK HISOBOT (22:00 + qo'lda) ─────────────────────────────────────────

def build_daily_excel(clients: list, report_date: str) -> Workbook:
    """
    Bugungi hisobot: har bir viloyat uchun alohida varaq + Umumiy varaq.
    Format rasmdagi kabi: No | Ism-Familya | Telefon | Manzil | Kasb turi | Savdo Turi | Izoh
    """
    wb = Workbook()
    wb.remove(wb.active)

    # Umumiy varaq
    ws_all = wb.create_sheet("Umumiy")
    ws_all.sheet_properties.tabColor = "1F3864"
    ws_all.cell(row=1, column=1)   # placeholder before header
    _fill_sheet(ws_all, clients)

    # Viloyat bo'yicha
    by_region: dict[int, list] = defaultdict(list)
    for c in clients:
        by_region[c["region_id"]].append(c)

    for region in REGIONS:
        rid = region["id"]
        if rid in by_region:
            ws = wb.create_sheet(region["name"][:31])
            _fill_sheet(ws, by_region[rid])

    return wb


def build_full_excel(clients: list, region_id: int = None) -> Workbook:
    """To'liq eksport (barcha vaqtlar)"""
    wb = Workbook()
    wb.remove(wb.active)

    if region_id:
        ws = wb.create_sheet(REGION_MAP.get(region_id, "Viloyat")[:31])
        _fill_sheet(ws, clients)
    else:
        ws_all = wb.create_sheet("Umumiy")
        _fill_sheet(ws_all, clients)

        by_region: dict[int, list] = defaultdict(list)
        for c in clients:
            by_region[c["region_id"]].append(c)

        for region in REGIONS:
            rid = region["id"]
            if rid in by_region:
                ws = wb.create_sheet(region["name"][:31])
                _fill_sheet(ws, by_region[rid])

    return wb

# ─── TELEGRAM HANDLERLARI ─────────────────────────────────────────────────────

async def export_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    is_admin = update.effective_user.id in ADMIN_IDS
    await query.edit_message_text(
        "📤 *Excel eksport*\n\nQaysi ma'lumotlarni eksport qilmoqchisiz?",
        parse_mode="Markdown",
        reply_markup=export_menu_kb(is_admin=is_admin),
    )

async def export_my_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db_user   = await get_user(update.effective_user.id)
    region_id = db_user["region_id"] if db_user else None
    await _do_export(update, ctx, region_id)

async def export_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("Faqat adminlar uchun!", show_alert=True)
        return
    await _do_export(update, ctx, region_id=None)

async def export_choose_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("Faqat adminlar uchun!", show_alert=True)
        return
    ctx.user_data["export_choosing"] = True
    await query.edit_message_text(
        "🗺 Eksport uchun viloyat tanlang:",
        reply_markup=regions_kb(include_all=True),
    )

async def export_region_selected(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.user_data.get("export_choosing"):
        return
    query = update.callback_query
    await query.answer()
    ctx.user_data.pop("export_choosing", None)
    data      = query.data
    region_id = None if data == "region_all" else int(data.split("_")[1])
    await _do_export(update, ctx, region_id)

async def _do_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE, region_id: int = None):
    query = update.callback_query
    await query.edit_message_text("⏳ Excel fayl tayyorlanmoqda...")

    clients = await get_clients(region_id, limit=10_000)
    if not clients:
        is_admin = update.effective_user.id in ADMIN_IDS
        await query.edit_message_text(
            "❌ Eksport qilish uchun mijozlar yo'q.",
            reply_markup=export_menu_kb(is_admin=is_admin),
        )
        return

    wb       = build_full_excel(list(clients), region_id)
    buffer   = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    region_name = REGION_MAP.get(region_id, "Umumiy") if region_id else "Umumiy"
    today       = date.today().strftime("%Y-%m-%d")
    filename    = f"CRM_{region_name}_{today}.xlsx"

    await update.effective_chat.send_document(
        document=buffer,
        filename=filename,
        caption=(
            f"📊 *{region_name} — CRM bazasi*\n"
            f"👥 Jami: *{len(clients)}* ta mijoz\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ),
        parse_mode="Markdown",
    )
    is_admin = update.effective_user.id in ADMIN_IDS
    await query.edit_message_text(
        "✅ Excel fayl yuborildi!",
        reply_markup=export_menu_kb(is_admin=is_admin),
    )

# ─── 22:00 AVTOMATIK KUNLIK HISOBOT ──────────────────────────────────────────

async def send_daily_report(app):
    """
    Har kecha soat 22:00 da barcha adminlarga bugungi
    qo'shilgan mijozlarning Excel hisobotini yuboradi.
    """
    from config import ADMIN_IDS
    today   = date.today().strftime("%Y-%m-%d")
    clients = await get_today_clients(region_id=None)   # barcha viloyatlar

    for admin_id in ADMIN_IDS:
        try:
            db_user   = await get_user(admin_id)
            region_id = db_user["region_id"] if db_user else None

            # Admin o'z viloyatini tanlagan bo'lsa — faqat o'shani
            if region_id:
                day_clients = [c for c in clients if c["region_id"] == region_id]
                region_name = REGION_MAP.get(region_id, "Viloyat")
            else:
                day_clients = list(clients)
                region_name = "Barcha viloyatlar"

            if not day_clients:
                await app.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"📊 *Kunlik hisobot — {today}*\n"
                        f"🗺 {region_name}\n\n"
                        f"Bugun hech qanday mijoz qo'shilmadi."
                    ),
                    parse_mode="Markdown",
                )
                continue

            wb     = build_daily_excel(day_clients, today)
            buffer = io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)

            filename = f"Hisobot_{region_name}_{today}.xlsx"
            await app.bot.send_document(
                chat_id=admin_id,
                document=buffer,
                filename=filename,
                caption=(
                    f"📊 *Kunlik hisobot — {today}*\n"
                    f"🗺 {region_name}\n"
                    f"👥 Bugun qo'shildi: *{len(day_clients)}* ta mijoz\n"
                    f"⏰ Vaqt: 22:00"
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"22:00 hisobot yuborishda xato (admin {admin_id}): {e}"
            )

# ─── MUDDATI O'TGAN VAZIFALAR ESLATMASI ──────────────────────────────────────

async def get_overdue_tasks_and_notify(app):
    """Har 30 daqiqada muddati o'tgan vazifalarni adminlarga bildiradi"""
    from database import get_overdue_tasks
    from config import ADMIN_IDS, REGION_MAP
    import logging
    tasks = await get_overdue_tasks()
    if not tasks:
        return
    for t in tasks:
        for admin_id in ADMIN_IDS:
            try:
                client_info = f"\n🔗 Mijoz: *{t['client_ism']}*" if t["client_ism"] else ""
                await app.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"⏰ *Muddati o'tgan vazifa!*\n\n"
                        f"📝 *{t['sarlavha']}*{client_info}\n"
                        f"📄 {t['tavsif'] or '—'}\n"
                        f"🗓 Muddat: {t['muddat']}\n"
                        f"🗺 {REGION_MAP.get(t['region_id'], '?')}\n"
                        f"ID: `{t['id']}`\n\n"
                        f"_/vazifa {t['id']} — boshqarish uchun_"
                    ),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logging.getLogger(__name__).warning(
                    f"Eslatma yuborishda xato (admin {admin_id}): {e}"
                )
