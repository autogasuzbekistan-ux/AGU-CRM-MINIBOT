import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH   = os.getenv("DB_PATH", "crm_bot.db")

_admin_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS  = [int(x.strip()) for x in _admin_raw.split(",") if x.strip().isdigit()]

# ─── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
GOOGLE_SERVICE_ACCOUNT_EMAIL = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL", "")
_pk_encoded = os.getenv("SHEETS_PK_ENCODED", "")
if _pk_encoded:
    import base64
    GOOGLE_PRIVATE_KEY = base64.b64decode(_pk_encoded).decode("utf-8")
else:
    GOOGLE_PRIVATE_KEY = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")

# ─── AGU SHAHARLARI ───────────────────────────────────────────────────────────
REGIONS = [
    {"id": 1,  "name": "AGU Andijon",   "code": "AND"},
    {"id": 2,  "name": "AGU Namangan",  "code": "NAM"},
    {"id": 3,  "name": "AGU Qo'qon",   "code": "QOQ"},
    {"id": 4,  "name": "AGU Toshkent", "code": "TOS"},
    {"id": 5,  "name": "AGU Guliston", "code": "GUL"},
    {"id": 6,  "name": "AGU Samarqand","code": "SAM"},
    {"id": 7,  "name": "AGU Buxoro",   "code": "BUX"},
    {"id": 8,  "name": "AGU Qarshi",   "code": "QAR"},
    {"id": 9,  "name": "AGU Denov",    "code": "DEN"},
    {"id": 10, "name": "AGU Xorazm",   "code": "XOR"},
    {"id": 11, "name": "AGU Nukus",    "code": "NUK"},
]
REGION_MAP      = {r["id"]: r["name"] for r in REGIONS}
REGION_CODE_MAP = {r["id"]: r["code"] for r in REGIONS}

# ─── HAR BIR SHAHARDAGI ISHCHILAR ─────────────────────────────────────────────
# region_id → ishchilar ro'yxati (Qo'qon va Toshkentda bir nechta)
REGION_WORKERS = {
    1:  ["Xayotjon"],                           # Andijon
    2:  ["Baxromjon"],                          # Namangan
    3:  ["Rashidjon", "Xurshidjon", "Asrorxon"],# Qo'qon  (3 do'kon)
    4:  ["Sherxon", "Maqsudjon"],               # Toshkent (2 do'kon)
    5:  ["Rustamjon"],                          # Guliston
    6:  ["Rustamxon"],                          # Samarqand
    7:  ["Oybekjon"],                           # Buxoro
    8:  ["Javohir"],                            # Qarshi
    9:  ["Jahongir"],                           # Denov
    10: ["Dilshodjon"],                         # Xorazm
    11: ["Nizomjon"],                           # Nukus
}

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
