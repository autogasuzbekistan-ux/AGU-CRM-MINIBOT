"""
Google Sheets integratsiyasi:
  - Yangi mijoz qo'shilganda avtomatik Google Sheetsga qo'shiladi
  - Background task sifatida ishlaydi (bot sekinlamaydi)
"""
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_HEADERS = [
    "No", "Ism-Familya", "Telefon Raqam", "Manzil",
    "Kasb turi", "Savdo Turi", "Savdo Subturi", "Izoh",
    "Viloyat", "Qo'shgan", "Sana",
]


def _build_creds():
    from google.oauth2.service_account import Credentials
    from config import GOOGLE_SERVICE_ACCOUNT_EMAIL, GOOGLE_PRIVATE_KEY

    # PEM sarlavhalari yo'q bo'lsa qo'shamiz
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


def _get_or_create_worksheet(spreadsheet, name: str = "Mijozlar"):
    import gspread
    try:
        ws = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=5000, cols=len(_HEADERS))
        ws.append_row(_HEADERS)
    return ws


def _sync_append(client: dict, region_name: str):
    import gspread
    from config import SPREADSHEET_ID

    gc = gspread.authorize(_build_creds())
    sp = gc.open_by_key(SPREADSHEET_ID)
    ws = _get_or_create_worksheet(sp, "Mijozlar")

    row_count = len(ws.get_all_values())  # sarlavha + mavjud qatorlar

    ws.append_row([
        row_count,  # No (avtomatik)
        client.get("ism", ""),
        client.get("telefon", ""),
        client.get("manzil", ""),
        client.get("kasb_turi", ""),
        client.get("savdo_turi", ""),
        client.get("savdo_subturi", ""),
        client.get("izoh", ""),
        region_name,
        client.get("qoshgan_nomi", ""),
        client.get("qoshilgan_vaqt") or datetime.now().strftime("%Y-%m-%d %H:%M"),
    ])


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
