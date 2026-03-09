import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "crm_bot.db")

_admin_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in _admin_raw.split(",") if x.strip().isdigit()]

# Uzbekiston viloyatlari
REGIONS = [
    {"id": 1,  "name": "Andijon",           "code": "AND"},
    {"id": 2,  "name": "Buxoro",            "code": "BUX"},
    {"id": 3,  "name": "Farg'ona",          "code": "FAR"},
    {"id": 4,  "name": "Jizzax",            "code": "JIZ"},
    {"id": 5,  "name": "Xorazm",            "code": "XOR"},
    {"id": 6,  "name": "Namangan",          "code": "NAM"},
    {"id": 7,  "name": "Navoiy",            "code": "NAV"},
    {"id": 8,  "name": "Qashqadaryo",       "code": "QAS"},
    {"id": 9,  "name": "Qoraqalpog'iston",  "code": "QQP"},
    {"id": 10, "name": "Samarqand",         "code": "SAM"},
    {"id": 11, "name": "Sirdaryo",          "code": "SIR"},
    {"id": 12, "name": "Surxondaryo",       "code": "SUR"},
    {"id": 13, "name": "Toshkent viloyati", "code": "TOS"},
    {"id": 14, "name": "Toshkent shahri",   "code": "TSH"},
]

REGION_MAP = {r["id"]: r["name"] for r in REGIONS}
REGION_CODE_MAP = {r["id"]: r["code"] for r in REGIONS}

# Savdo turlari
SAVDO_TURLARI = ["Chakana", "Ulgurji", "Online", "B2B", "Service", "Boshqa"]

# Daraja hisobi ($)
def calculate_daraja(savdo: float) -> str:
    if 1_000 <= savdo <= 10_000:
        return "🥉 1-daraja"
    elif 10_001 <= savdo <= 30_000:
        return "🥈 2-daraja"
    elif 30_001 <= savdo <= 50_000:
        return "🥇 3-daraja"
    elif savdo > 50_000:
        return "💎 VIP"
    return "🆕 Yangi"
