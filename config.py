import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH   = os.getenv("DB_PATH", "crm_bot.db")

_admin_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS  = [int(x.strip()) for x in _admin_raw.split(",") if x.strip().isdigit()]

# ─── UZBEKISTON VILOYATLARI ───────────────────────────────────────────────────
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
REGION_MAP      = {r["id"]: r["name"] for r in REGIONS}
REGION_CODE_MAP = {r["id"]: r["code"] for r in REGIONS}

# ─── SAVDO TURLARI ─────────────────────────────────────────────────────────────
# Asosiy 3 tur
SAVDO_TURLARI = ["Ulgurji savdo", "Chakana savdo", "Servis"]

# Har bir tur uchun kichik turlar
SAVDO_SUBTURLARI = {
    "Ulgurji savdo": [
        "5,000 – 10,000$",
        "10,001 – 30,000$",
        "30,001 – 50,000$",
    ],
    "Chakana savdo": [
        "Oylik xaridor",
        "Referral (mijoz olib keluvchi)",
    ],
    "Servis": [
        "Ehtiyot qism (boshqa servicedan)",
        "Servis uchun xaridor",
    ],
}

# Excel katakchalar rangi (RRGGBB hex)
SAVDO_COLORS = {
    "Ulgurji savdo": "92D050",   # yashil
    "Chakana savdo": "FFC000",   # to'q sariq
    "Servis":        "00B0F0",   # moviy
}
