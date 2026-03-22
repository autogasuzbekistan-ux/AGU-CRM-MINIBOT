"""
Google Sheets integratsiyasi:
  - Yangi mijoz qo'shilganda avtomatik Google Sheetsga qo'shiladi
  - Chiroyli formatlanadi: sarlavha rangi, savdo turi bo'yicha rang, filter, muzlatilgan sarlavha
"""
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_HEADERS = [
    "No", "Ism-Familya", "Telefon Raqam", "Manzil",
    "Kasb turi", "Savdo Turi", "Savdo Subturi",
    "Viloyat", "Qo'shgan", "Sana", "Izoh",
]

# Savdo turi bo'yicha qator ranglari (RGB 0-1)
_ROW_COLORS = {
    "Ulgurji savdo": {"red": 0.573, "green": 0.816, "blue": 0.314},  # yashil
    "Chakana savdo": {"red": 1.0,   "green": 0.753, "blue": 0.0},    # sariq
    "Servis":        {"red": 0.0,   "green": 0.690, "blue": 0.941},  # moviy
}


def _build_creds():
    from google.oauth2.service_account import Credentials
    from config import GOOGLE_SERVICE_ACCOUNT_EMAIL, GOOGLE_PRIVATE_KEY

    pk = GOOGLE_PRIVATE_KEY.strip()
    if pk and not pk.startswith("-----"):
        pk = f"-----BEGIN PRIVATE KEY-----\n{pk}\n-----END PRIVATE KEY-----\n"

    return Credentials.from_service_account_info(
        {
            "type": "service_account",
            "client_email": GOOGLE_SERVICE_ACCOUNT_EMAIL,
            "private_key": pk,
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "client_id": "",
        },
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )


def _apply_sheet_format(spreadsheet, ws):
    """Sarlavha formati, muzlatish, filter, ustun kengliklari."""
    sid = ws.id
    ncols = len(_HEADERS)
    spreadsheet.batch_update({"requests": [
        # Sarlavha — ko'k fon, oq qalin matn, markazlashgan
        {
            "repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1,
                           "startColumnIndex": 0, "endColumnIndex": ncols},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 0.259, "green": 0.522, "blue": 0.957},
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                        "fontSize": 11,
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                    "wrapStrategy": "CLIP",
                }},
                "fields": "userEnteredFormat",
            }
        },
        # Sarlavha qatori balandligi
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sid, "dimension": "ROWS",
                          "startIndex": 0, "endIndex": 1},
                "properties": {"pixelSize": 36},
                "fields": "pixelSize",
            }
        },
        # Muzlatilgan sarlavha
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sid,
                               "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        },
        # Filter
        {
            "setBasicFilter": {
                "filter": {"range": {"sheetId": sid, "startRowIndex": 0,
                                     "startColumnIndex": 0, "endColumnIndex": ncols}}
            }
        },
        # Barcha ustunlar kengligi 150px
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sid, "dimension": "COLUMNS",
                          "startIndex": 0, "endIndex": ncols},
                "properties": {"pixelSize": 150},
                "fields": "pixelSize",
            }
        },
        # "No" ustuni — tor (50px)
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sid, "dimension": "COLUMNS",
                          "startIndex": 0, "endIndex": 1},
                "properties": {"pixelSize": 50},
                "fields": "pixelSize",
            }
        },
        # "Izoh" ustuni (oxirgi) — keng (280px)
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sid, "dimension": "COLUMNS",
                          "startIndex": ncols - 1, "endIndex": ncols},
                "properties": {"pixelSize": 280},
                "fields": "pixelSize",
            }
        },
        # "Manzil" ustuni — keng (200px), index=3
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sid, "dimension": "COLUMNS",
                          "startIndex": 3, "endIndex": 4},
                "properties": {"pixelSize": 200},
                "fields": "pixelSize",
            }
        },
    ]})


def _color_row(spreadsheet, ws, row_index: int, savdo_turi: str):
    """Qatorni savdo turi bo'yicha ranglaydi."""
    color = _ROW_COLORS.get(savdo_turi)
    if not color:
        return
    sid = ws.id
    spreadsheet.batch_update({"requests": [{
        "repeatCell": {
            "range": {"sheetId": sid,
                      "startRowIndex": row_index - 1, "endRowIndex": row_index,
                      "startColumnIndex": 0, "endColumnIndex": len(_HEADERS)},
            "cell": {"userEnteredFormat": {"backgroundColor": color}},
            "fields": "userEnteredFormat.backgroundColor",
        }
    }]})


def _get_or_create_worksheet(spreadsheet, name: str = "Mijozlar"):
    import gspread
    try:
        ws = spreadsheet.worksheet(name)
        # Sarlavha to'g'rimi tekshir, eski formatda bo'lsa qayta yarat
        existing = ws.row_values(1)
        if existing != _HEADERS:
            spreadsheet.del_worksheet(ws)
            raise gspread.WorksheetNotFound
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=5000, cols=len(_HEADERS))
        ws.append_row(_HEADERS)
        _apply_sheet_format(spreadsheet, ws)
    return ws


def _sync_append(client: dict, region_name: str):
    from config import SPREADSHEET_ID

    gc = __import__("gspread").authorize(_build_creds())
    sp = gc.open_by_key(SPREADSHEET_ID)
    ws = _get_or_create_worksheet(sp, "Mijozlar")

    row_count = len(ws.get_all_values())
    savdo_turi = client.get("savdo_turi", "")

    ws.append_row([
        row_count,
        client.get("ism", ""),
        client.get("telefon", ""),
        client.get("manzil", ""),
        client.get("kasb_turi", ""),
        savdo_turi,
        client.get("savdo_subturi", ""),
        region_name,
        client.get("qoshgan_nomi", ""),
        client.get("qoshilgan_vaqt") or datetime.now().strftime("%Y-%m-%d %H:%M"),
        client.get("izoh", ""),
    ])

    # Yangi qatorn rangini belgilash
    new_row = len(ws.get_all_values())
    _color_row(sp, ws, new_row, savdo_turi)


async def sync_client_to_sheet(client: dict, region_name: str):
    """Yangi mijozni Google Sheetsga qo'shadi (background, xato bot'ni to'xtatmaydi)."""
    from config import GOOGLE_SERVICE_ACCOUNT_EMAIL, GOOGLE_PRIVATE_KEY, SPREADSHEET_ID

    if not all([GOOGLE_SERVICE_ACCOUNT_EMAIL, GOOGLE_PRIVATE_KEY, SPREADSHEET_ID]):
        logger.warning(
            f"Google Sheets sozlanmagan! "
            f"EMAIL={'✓' if GOOGLE_SERVICE_ACCOUNT_EMAIL else '✗'} "
            f"PRIVATE_KEY={'✓' if GOOGLE_PRIVATE_KEY else '✗'} "
            f"SPREADSHEET_ID={'✓' if SPREADSHEET_ID else '✗'}"
        )
        return

    try:
        await asyncio.to_thread(_sync_append, client, region_name)
        logger.info(f"Google Sheets: '{client.get('ism')}' qo'shildi ✓")
    except Exception as e:
        logger.warning(f"Google Sheets sync xato: {e}")
