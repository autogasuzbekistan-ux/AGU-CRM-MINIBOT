from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config import REGIONS, SAVDO_TURLARI, SAVDO_SUBTURLARI

# ─── TUGMA MATNLARI (konstanta) ───────────────────────────────────────────────
BTN_CLIENTS        = "👥 Mijozlar"
BTN_STATS          = "📊 Statistika"
BTN_TASKS          = "✅ Vazifalar"
BTN_EXPORT         = "📤 Excel Export"
BTN_REGION         = "🗺 Viloyat"
BTN_USERS          = "👤 Foydalanuvchilar"
BTN_REPORT         = "📨 Hisobot yuborish"

BTN_ADD_CLIENT     = "➕ Mijoz qo'shish"
BTN_SEARCH_CLIENT  = "🔍 Qidirish"
BTN_CLIENT_LIST    = "📋 Mijozlar ro'yxati"
BTN_MY_CLIENTS     = "📋 Mijozlarim"
BTN_EDIT_CLIENT    = "✏️ Tahrirlash"
BTN_DELETE_CLIENT  = "🗑 O'chirish"

BTN_ADD_TASK       = "➕ Vazifa qo'shish"
BTN_ACTIVE_TASKS   = "📋 Faol vazifalar"
BTN_DONE_TASKS     = "☑️ Bajarilganlar"

BTN_STATS_GENERAL  = "📈 Umumiy statistika"
BTN_STATS_REGION   = "🗺 Viloyat bo'yicha"
BTN_STATS_TYPE     = "🏷 Savdo turlari"
BTN_STATS_SUB      = "🔍 Kichik turlar"

BTN_EXPORT_MY      = "📤 Mening viloyatim"
BTN_EXPORT_ALL     = "🌍 Barcha viloyatlar"
BTN_EXPORT_CHOOSE  = "🗺 Viloyat tanlash"

BTN_BACK           = "🏠 Asosiy menyu"
BTN_CANCEL         = "❌ Bekor qilish"
BTN_SKIP           = "➡️ O'tkazib yuborish"

# ═══════════════════════════════════════════════════════════════════════════════
# ASOSIY MENYULAR (ReplyKeyboard)
# ═══════════════════════════════════════════════════════════════════════════════

def admin_main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [BTN_CLIENTS,     BTN_STATS],
        [BTN_TASKS,       BTN_EXPORT],
        [BTN_REGION,      BTN_USERS],
        [BTN_REPORT],
    ], resize_keyboard=True)

def user_main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [BTN_ADD_CLIENT],
        [BTN_MY_CLIENTS,  BTN_SEARCH_CLIENT],
        [BTN_TASKS,       BTN_REGION],
    ], resize_keyboard=True)

def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    return admin_main_menu_kb() if is_admin else user_main_menu_kb()

# ═══════════════════════════════════════════════════════════════════════════════
# BO'LIM MENYULARI (ReplyKeyboard)
# ═══════════════════════════════════════════════════════════════════════════════

def clients_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [BTN_ADD_CLIENT,   BTN_SEARCH_CLIENT],
        [BTN_CLIENT_LIST,  BTN_EDIT_CLIENT],
        [BTN_DELETE_CLIENT],
        [BTN_BACK],
    ], resize_keyboard=True)

def tasks_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [BTN_ADD_TASK,    BTN_ACTIVE_TASKS],
        [BTN_DONE_TASKS],
        [BTN_BACK],
    ], resize_keyboard=True)

def stats_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [BTN_STATS_GENERAL],
        [BTN_STATS_REGION, BTN_STATS_TYPE],
        [BTN_STATS_SUB],
        [BTN_BACK],
    ], resize_keyboard=True)

def export_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [[BTN_EXPORT_MY]]
    if is_admin:
        buttons.append([BTN_EXPORT_ALL, BTN_EXPORT_CHOOSE])
    buttons.append([BTN_BACK])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SUHBAT DAVOMIDAGI KLAVIATURALAR (ReplyKeyboard)
# ═══════════════════════════════════════════════════════════════════════════════

def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[BTN_CANCEL]], resize_keyboard=True)

def skip_cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[BTN_SKIP], [BTN_CANCEL]], resize_keyboard=True)

# ═══════════════════════════════════════════════════════════════════════════════
# VILOYAT TANLASH (InlineKeyboard — bir martalik amal)
# ═══════════════════════════════════════════════════════════════════════════════

def regions_kb(include_all: bool = False) -> InlineKeyboardMarkup:
    buttons, row = [], []
    for r in REGIONS:
        row.append(InlineKeyboardButton(r["name"], callback_data=f"region_{r['id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if include_all:
        buttons.append([InlineKeyboardButton("🌍 Barcha viloyatlar", callback_data="region_all")])
    return InlineKeyboardMarkup(buttons)

# ═══════════════════════════════════════════════════════════════════════════════
# MIJOZ AMALLARI (InlineKeyboard — kontekstli)
# ═══════════════════════════════════════════════════════════════════════════════

def client_detail_kb(client_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Tahrirlash",       callback_data=f"edit_{client_id}"),
         InlineKeyboardButton("🗑 O'chirish",         callback_data=f"del_{client_id}")],
        [InlineKeyboardButton("✅ Vazifa qo'shish",  callback_data=f"task_for_{client_id}"),
         InlineKeyboardButton("✔️ Tasdiqlash",        callback_data=f"confirm_{client_id}")],
    ])

def edit_fields_kb(client_id: int) -> InlineKeyboardMarkup:
    fields = [
        ("Ism-Familya", "ism"),      ("Telefon",    "telefon"),
        ("Manzil",      "manzil"),   ("Kasb turi",  "kasb_turi"),
        ("Savdo turi",  "savdo_turi"), ("Kichik tur", "savdo_subturi"),
        ("Izoh",        "izoh"),
    ]
    buttons, row = [], []
    for label, field in fields:
        row.append(InlineKeyboardButton(label, callback_data=f"editfield_{client_id}_{field}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

# ═══════════════════════════════════════════════════════════════════════════════
# SAVDO TURI (InlineKeyboard — suhbat ichida)
# ═══════════════════════════════════════════════════════════════════════════════

_TURI_EMOJI = {"Ulgurji savdo": "🟢", "Chakana savdo": "🟡", "Servis": "🔵"}

def savdo_turi_kb() -> InlineKeyboardMarkup:
    buttons = []
    for t in SAVDO_TURLARI:
        emoji = _TURI_EMOJI.get(t, "")
        buttons.append([InlineKeyboardButton(f"{emoji} {t}", callback_data=f"turi_{t}")])
    return InlineKeyboardMarkup(buttons)

def savdo_subturi_kb(turi: str) -> InlineKeyboardMarkup:
    subtypes = SAVDO_SUBTURLARI.get(turi, [])
    buttons = [[InlineKeyboardButton(sub, callback_data=f"subturi_{sub}")] for sub in subtypes]
    return InlineKeyboardMarkup(buttons)

# ═══════════════════════════════════════════════════════════════════════════════
# VAZIFA AMALLARI (InlineKeyboard — kontekstli)
# ═══════════════════════════════════════════════════════════════════════════════

def task_action_kb(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Bajarildi",  callback_data=f"task_complete_{task_id}"),
         InlineKeyboardButton("🗑 O'chirish",  callback_data=f"task_del_{task_id}")],
    ])

def task_list_kb(tasks: list) -> InlineKeyboardMarkup:
    """Vazifalar ro'yxati — har bir vazifa uchun ✅ va 🗑 tugmalar."""
    buttons = []
    for t in tasks[:20]:
        title = t["sarlavha"]
        short = (title[:20] + "…") if len(title) > 20 else title
        buttons.append([
            InlineKeyboardButton(f"✅ {short}", callback_data=f"task_complete_{t['id']}"),
            InlineKeyboardButton("🗑",           callback_data=f"task_del_{t['id']}"),
        ])
    return InlineKeyboardMarkup(buttons) if buttons else None

# ═══════════════════════════════════════════════════════════════════════════════
# UMUMIY YORDAMCHI (InlineKeyboard)
# ═══════════════════════════════════════════════════════════════════════════════

def confirm_delete_kb(prefix: str, item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"{prefix}_confirm_{item_id}"),
         InlineKeyboardButton("❌ Yo'q",          callback_data="noop")],
    ])

def pagination_kb(page: int, total: int, page_size: int, prefix: str) -> InlineKeyboardMarkup | None:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton("◀️ Oldingi", callback_data=f"{prefix}_page_{page - 1}"))
    if (page + 1) * page_size < total:
        row.append(InlineKeyboardButton("Keyingi ▶️", callback_data=f"{prefix}_page_{page + 1}"))
    return InlineKeyboardMarkup([row]) if row else None
