from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from config import REGIONS, SAVDO_TURLARI

# ─── ASOSIY MENYU ─────────────────────────────────────────────────────────────

def main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("👥 Mijozlar",    callback_data="menu_clients"),
         InlineKeyboardButton("📊 Statistika",  callback_data="menu_stats")],
        [InlineKeyboardButton("✅ Vazifalar",   callback_data="menu_tasks"),
         InlineKeyboardButton("📤 Excel Export",callback_data="menu_export")],
    ]
    if is_admin:
        buttons.append([
            InlineKeyboardButton("🗺 Viloyat tanlash", callback_data="menu_change_region"),
            InlineKeyboardButton("👑 Umumiy CRM",      callback_data="region_all"),
        ])
    return InlineKeyboardMarkup(buttons)

# ─── VILOYAT TANLASH ──────────────────────────────────────────────────────────

def regions_kb(include_all: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, r in enumerate(REGIONS):
        row.append(InlineKeyboardButton(r["name"], callback_data=f"region_{r['id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if include_all:
        buttons.append([InlineKeyboardButton("🌍 Barcha viloyatlar", callback_data="region_all")])
    return InlineKeyboardMarkup(buttons)

# ─── MIJOZLAR MENYUSI ─────────────────────────────────────────────────────────

def clients_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Mijoz qo'shish",  callback_data="client_add"),
         InlineKeyboardButton("🔍 Mijoz qidirish",  callback_data="client_search")],
        [InlineKeyboardButton("📋 Ro'yxat ko'rish", callback_data="client_list"),
         InlineKeyboardButton("✏️ Tahrirlash",      callback_data="client_edit_start")],
        [InlineKeyboardButton("🗑 O'chirish",        callback_data="client_delete_start")],
        [InlineKeyboardButton("🔙 Orqaga",           callback_data="back_main")],
    ])

# ─── MIJOZ TAFSILOTLARI ───────────────────────────────────────────────────────

def client_detail_kb(client_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Tahrirlash",       callback_data=f"edit_{client_id}"),
         InlineKeyboardButton("🗑 O'chirish",         callback_data=f"del_{client_id}")],
        [InlineKeyboardButton("✅ Vazifa qo'shish",  callback_data=f"task_for_{client_id}")],
        [InlineKeyboardButton("🔙 Ro'yxatga qaytish", callback_data="client_list")],
    ])

# ─── TAHRIRLASH MAYDONLARI ────────────────────────────────────────────────────

def edit_fields_kb(client_id: int) -> InlineKeyboardMarkup:
    fields = [
        ("Ism", "ism"), ("Telefon", "telefon"), ("Turi", "turi"),
        ("Shahar", "shahar"), ("Savdo hajmi", "savdo_hajmi"), ("Izoh", "izoh"),
    ]
    buttons = []
    row = []
    for label, field in fields:
        row.append(InlineKeyboardButton(label, callback_data=f"editfield_{client_id}_{field}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"client_detail_{client_id}")])
    return InlineKeyboardMarkup(buttons)

# ─── SAVDO TURI ───────────────────────────────────────────────────────────────

def savdo_turi_kb() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, t in enumerate(SAVDO_TURLARI):
        row.append(InlineKeyboardButton(t, callback_data=f"turi_{t}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Bekor qilish", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)

# ─── VAZIFALAR MENYUSI ────────────────────────────────────────────────────────

def tasks_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Vazifa qo'shish",  callback_data="task_add"),
         InlineKeyboardButton("📋 Faol vazifalar",   callback_data="task_list")],
        [InlineKeyboardButton("✅ Bajarilganlar",    callback_data="task_done_list")],
        [InlineKeyboardButton("🔙 Orqaga",           callback_data="back_main")],
    ])

def task_action_kb(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Bajarildi",   callback_data=f"task_complete_{task_id}"),
         InlineKeyboardButton("🗑 O'chirish",   callback_data=f"task_del_{task_id}")],
        [InlineKeyboardButton("🔙 Orqaga",      callback_data="task_list")],
    ])

# ─── STATISTIKA MENYUSI ───────────────────────────────────────────────────────

def stats_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📊 Umumiy statistika", callback_data="stats_general")],
        [InlineKeyboardButton("🗺 Viloyat bo'yicha",  callback_data="stats_by_region")],
        [InlineKeyboardButton("📈 Savdo turlari",      callback_data="stats_by_type")],
        [InlineKeyboardButton("⭐ Darajalar",           callback_data="stats_by_grade")],
        [InlineKeyboardButton("🔙 Orqaga",             callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(buttons)

# ─── EXPORT MENYUSI ───────────────────────────────────────────────────────────

def export_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📤 Mening viloyatim",  callback_data="export_my_region")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton("🌍 Barcha viloyatlar", callback_data="export_all")])
        buttons.append([InlineKeyboardButton("🗺 Viloyat tanlash",   callback_data="export_choose")])
    buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)

# ─── UMUMIY TUGMALAR ──────────────────────────────────────────────────────────

def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")]])

def back_kb(target: str = "back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data=target)]])

def confirm_delete_kb(prefix: str, item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ha, o'chirish",  callback_data=f"{prefix}_confirm_{item_id}"),
         InlineKeyboardButton("❌ Yo'q",           callback_data="cancel")],
    ])

# ─── SAHIFALASH ───────────────────────────────────────────────────────────────

def pagination_kb(page: int, total: int, page_size: int,
                  prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton("◀️ Oldingi", callback_data=f"{prefix}_page_{page-1}"))
    if (page + 1) * page_size < total:
        row.append(InlineKeyboardButton("Keyingi ▶️", callback_data=f"{prefix}_page_{page+1}"))
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="menu_clients")])
    return InlineKeyboardMarkup(buttons)
