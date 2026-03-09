import aiosqlite
from datetime import datetime
from config import DB_PATH, REGIONS

# ─── JADVALLARNI YARATISH ────────────────────────────────────────────────────

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Viloyatlar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS regions (
                id   INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                code TEXT NOT NULL
            )
        """)

        # Foydalanuvchilar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id  INTEGER PRIMARY KEY,
                username     TEXT,
                full_name    TEXT,
                region_id    INTEGER,
                role         TEXT DEFAULT 'manager',
                created_at   TEXT,
                FOREIGN KEY(region_id) REFERENCES regions(id)
            )
        """)

        # Mijozlar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                ism            TEXT NOT NULL,
                telefon        TEXT,
                turi           TEXT,
                shahar         TEXT,
                region_id      INTEGER NOT NULL,
                savdo_hajmi    REAL DEFAULT 0,
                daraja         TEXT DEFAULT '🆕 Yangi',
                izoh           TEXT,
                qoshgan_id     INTEGER,
                qoshgan_user   TEXT,
                qoshgan_nomi   TEXT,
                qoshilgan_vaqt TEXT,
                yangilangan_vaqt TEXT,
                FOREIGN KEY(region_id) REFERENCES regions(id)
            )
        """)

        # Vazifalar (eslatmalar) jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                sarlavha       TEXT NOT NULL,
                tavsif         TEXT,
                client_id      INTEGER,
                region_id      INTEGER NOT NULL,
                muddat         TEXT,
                bajarilgan     INTEGER DEFAULT 0,
                qoshgan_id     INTEGER,
                qoshilgan_vaqt TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id),
                FOREIGN KEY(region_id) REFERENCES regions(id)
            )
        """)

        # Viloyatlarni seed qilish
        for r in REGIONS:
            await db.execute(
                "INSERT OR IGNORE INTO regions (id, name, code) VALUES (?, ?, ?)",
                (r["id"], r["name"], r["code"])
            )

        await db.commit()

# ─── FOYDALANUVCHI OPERATSIYALARI ────────────────────────────────────────────

async def get_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            return await cur.fetchone()

async def upsert_user(telegram_id: int, username: str, full_name: str,
                      region_id: int = None, role: str = "manager"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (telegram_id, username, full_name, region_id, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username   = excluded.username,
                full_name  = excluded.full_name,
                region_id  = COALESCE(excluded.region_id, users.region_id),
                role       = excluded.role
        """, (telegram_id, username, full_name, region_id, role, now))
        await db.commit()

async def set_user_region(telegram_id: int, region_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET region_id = ? WHERE telegram_id = ?",
            (region_id, telegram_id)
        )
        await db.commit()

# ─── MIJOZ OPERATSIYALARI ─────────────────────────────────────────────────────

async def add_client(data: dict) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO clients
                (ism, telefon, turi, shahar, region_id, savdo_hajmi, daraja,
                 izoh, qoshgan_id, qoshgan_user, qoshgan_nomi, qoshilgan_vaqt, yangilangan_vaqt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["ism"], data["telefon"], data["turi"], data["shahar"],
            data["region_id"], data["savdo_hajmi"], data["daraja"],
            data.get("izoh", ""), data["qoshgan_id"], data["qoshgan_user"],
            data["qoshgan_nomi"], now, now
        ))
        await db.commit()
        return cur.lastrowid

async def get_clients(region_id: int = None, limit: int = 50, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if region_id:
            query = "SELECT * FROM clients WHERE region_id = ? ORDER BY id DESC LIMIT ? OFFSET ?"
            params = (region_id, limit, offset)
        else:
            query = "SELECT * FROM clients ORDER BY id DESC LIMIT ? OFFSET ?"
            params = (limit, offset)
        async with db.execute(query, params) as cur:
            return await cur.fetchall()

async def search_clients(query: str, region_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        like = f"%{query}%"
        if region_id:
            sql = """SELECT * FROM clients
                     WHERE region_id = ? AND (ism LIKE ? OR telefon LIKE ? OR shahar LIKE ?)
                     ORDER BY id DESC LIMIT 20"""
            params = (region_id, like, like, like)
        else:
            sql = """SELECT * FROM clients
                     WHERE ism LIKE ? OR telefon LIKE ? OR shahar LIKE ?
                     ORDER BY id DESC LIMIT 20"""
            params = (like, like, like)
        async with db.execute(sql, params) as cur:
            return await cur.fetchall()

async def get_client_by_id(client_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)) as cur:
            return await cur.fetchone()

async def update_client(client_id: int, field: str, value: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    allowed = {"ism", "telefon", "turi", "shahar", "savdo_hajmi", "daraja", "izoh"}
    if field not in allowed:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE clients SET {field} = ?, yangilangan_vaqt = ? WHERE id = ?",
            (value, now, client_id)
        )
        await db.commit()

async def delete_client(client_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        await db.execute("DELETE FROM tasks WHERE client_id = ?", (client_id,))
        await db.commit()

async def count_clients(region_id: int = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        if region_id:
            async with db.execute(
                "SELECT COUNT(*) FROM clients WHERE region_id = ?", (region_id,)
            ) as cur:
                row = await cur.fetchone()
        else:
            async with db.execute("SELECT COUNT(*) FROM clients") as cur:
                row = await cur.fetchone()
        return row[0] if row else 0

# ─── STATISTIKA ───────────────────────────────────────────────────────────────

async def get_stats(region_id: int = None) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        where = f"WHERE region_id = {region_id}" if region_id else ""

        async with db.execute(
            f"SELECT COUNT(*) as cnt, SUM(savdo_hajmi) as total FROM clients {where}"
        ) as cur:
            general = await cur.fetchone()

        async with db.execute(
            f"SELECT turi, COUNT(*) as cnt FROM clients {where} GROUP BY turi"
        ) as cur:
            by_type = await cur.fetchall()

        async with db.execute(
            f"SELECT daraja, COUNT(*) as cnt FROM clients {where} GROUP BY daraja"
        ) as cur:
            by_grade = await cur.fetchall()

        async with db.execute(
            f"""SELECT r.name, COUNT(c.id) as cnt, SUM(c.savdo_hajmi) as total
                FROM clients c JOIN regions r ON c.region_id = r.id
                {where} GROUP BY c.region_id ORDER BY cnt DESC"""
        ) as cur:
            by_region = await cur.fetchall()

        return {
            "total_clients": general["cnt"] if general else 0,
            "total_sales": general["total"] or 0 if general else 0,
            "by_type": [dict(r) for r in by_type],
            "by_grade": [dict(r) for r in by_grade],
            "by_region": [dict(r) for r in by_region],
        }

# ─── VAZIFALAR ────────────────────────────────────────────────────────────────

async def add_task(data: dict) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO tasks (sarlavha, tavsif, client_id, region_id, muddat, qoshgan_id, qoshilgan_vaqt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data["sarlavha"], data.get("tavsif", ""), data.get("client_id"),
            data["region_id"], data.get("muddat"), data["qoshgan_id"], now
        ))
        await db.commit()
        return cur.lastrowid

async def get_tasks(region_id: int = None, only_active: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        conditions = []
        params = []
        if region_id:
            conditions.append("t.region_id = ?")
            params.append(region_id)
        if only_active:
            conditions.append("t.bajarilgan = 0")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT t.*, c.ism as client_ism
            FROM tasks t
            LEFT JOIN clients c ON t.client_id = c.id
            {where}
            ORDER BY t.muddat ASC, t.id DESC
            LIMIT 50
        """
        async with db.execute(sql, params) as cur:
            return await cur.fetchall()

async def complete_task(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tasks SET bajarilgan = 1 WHERE id = ?", (task_id,)
        )
        await db.commit()

async def delete_task(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()

async def get_overdue_tasks():
    """Muddati o'tgan vazifalarni qaytaradi"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        sql = """
            SELECT t.*, c.ism as client_ism
            FROM tasks t
            LEFT JOIN clients c ON t.client_id = c.id
            WHERE t.bajarilgan = 0 AND t.muddat IS NOT NULL AND t.muddat <= ?
        """
        async with db.execute(sql, (now,)) as cur:
            return await cur.fetchall()
