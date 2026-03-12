import asyncio
import aiosqlite
from datetime import datetime, date
from config import DB_PATH, REGIONS

# ─── YORDAMCHI ────────────────────────────────────────────────────────────────

def _connect():
    """Har bir operatsiya uchun yangi ulanish — event loop konflikti yo'q."""
    return aiosqlite.connect(DB_PATH)

# ─── JADVALLARNI YARATISH ────────────────────────────────────────────────────

async def init_db():
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS regions (
                id   INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                code TEXT NOT NULL
            )
        """)
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                ism              TEXT NOT NULL,
                telefon          TEXT,
                manzil           TEXT,
                kasb_turi        TEXT,
                savdo_turi       TEXT,
                savdo_subturi    TEXT,
                izoh             TEXT,
                region_id        INTEGER NOT NULL,
                qoshgan_id       INTEGER,
                qoshgan_user     TEXT,
                qoshgan_nomi     TEXT,
                qoshilgan_vaqt   TEXT,
                yangilangan_vaqt TEXT,
                FOREIGN KEY(region_id) REFERENCES regions(id)
            )
        """)
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

        # Migration: eski jadvallarga ustunlar qo'shish
        for col_sql in [
            "ALTER TABLE clients ADD COLUMN manzil TEXT",
            "ALTER TABLE clients ADD COLUMN kasb_turi TEXT",
            "ALTER TABLE clients ADD COLUMN savdo_turi TEXT",
            "ALTER TABLE clients ADD COLUMN savdo_subturi TEXT",
            "ALTER TABLE tasks ADD COLUMN notified INTEGER DEFAULT 0",
        ]:
            try:
                await db.execute(col_sql)
            except Exception:
                pass

        for r in REGIONS:
            await db.execute(
                "INSERT OR IGNORE INTO regions (id, name, code) VALUES (?, ?, ?)",
                (r["id"], r["name"], r["code"])
            )
        await db.commit()


# ─── FOYDALANUVCHI ────────────────────────────────────────────────────────────

async def get_user(telegram_id: int):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            return await cur.fetchone()


async def upsert_user(telegram_id: int, username: str, full_name: str,
                      region_id=None, role: str = "manager"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with _connect() as db:
        await db.execute("""
            INSERT INTO users (telegram_id, username, full_name, region_id, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name,
                region_id = COALESCE(excluded.region_id, users.region_id),
                role      = excluded.role
        """, (telegram_id, username, full_name, region_id, role, now))
        await db.commit()


async def set_user_region(telegram_id: int, region_id):
    async with _connect() as db:
        await db.execute(
            "UPDATE users SET region_id = ? WHERE telegram_id = ?",
            (region_id, telegram_id)
        )
        await db.commit()


async def get_all_users():
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY created_at DESC") as cur:
            return await cur.fetchall()


# ─── MIJOZLAR ─────────────────────────────────────────────────────────────────

async def add_client(data: dict) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with _connect() as db:
        cur = await db.execute("""
            INSERT INTO clients
                (ism, telefon, manzil, kasb_turi, savdo_turi, savdo_subturi,
                 izoh, region_id, qoshgan_id, qoshgan_user, qoshgan_nomi,
                 qoshilgan_vaqt, yangilangan_vaqt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["ism"],
            data.get("telefon", ""),
            data.get("manzil", ""),
            data.get("kasb_turi", ""),
            data.get("savdo_turi", ""),
            data.get("savdo_subturi", ""),
            data.get("izoh", ""),
            data["region_id"],
            data["qoshgan_id"],
            data.get("qoshgan_user", ""),
            data.get("qoshgan_nomi", ""),
            now, now,
        ))
        await db.commit()
        return cur.lastrowid


async def get_clients(region_id=None, limit: int = 50, offset: int = 0):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        if region_id:
            sql    = "SELECT * FROM clients WHERE region_id = ? ORDER BY id DESC LIMIT ? OFFSET ?"
            params = (region_id, limit, offset)
        else:
            sql    = "SELECT * FROM clients ORDER BY id DESC LIMIT ? OFFSET ?"
            params = (limit, offset)
        async with db.execute(sql, params) as cur:
            return await cur.fetchall()


async def get_today_clients(region_id=None):
    today = date.today().strftime("%Y-%m-%d")
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        if region_id:
            sql    = ("SELECT * FROM clients "
                      "WHERE region_id = ? AND qoshilgan_vaqt LIKE ? ORDER BY id")
            params = (region_id, f"{today}%")
        else:
            sql    = ("SELECT * FROM clients "
                      "WHERE qoshilgan_vaqt LIKE ? ORDER BY region_id, id")
            params = (f"{today}%",)
        async with db.execute(sql, params) as cur:
            return await cur.fetchall()


async def search_clients(query: str, region_id=None):
    like = f"%{query}%"
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        if region_id:
            sql = """SELECT * FROM clients
                     WHERE region_id = ?
                       AND (ism LIKE ? OR telefon LIKE ? OR manzil LIKE ? OR kasb_turi LIKE ?)
                     ORDER BY id DESC LIMIT 20"""
            params = (region_id, like, like, like, like)
        else:
            sql = """SELECT * FROM clients
                     WHERE ism LIKE ? OR telefon LIKE ? OR manzil LIKE ? OR kasb_turi LIKE ?
                     ORDER BY id DESC LIMIT 20"""
            params = (like, like, like, like)
        async with db.execute(sql, params) as cur:
            return await cur.fetchall()


async def get_client_by_id(client_id: int):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)) as cur:
            return await cur.fetchone()


async def update_client(client_id: int, field: str, value: str):
    allowed = {"ism", "telefon", "manzil", "kasb_turi", "savdo_turi", "savdo_subturi", "izoh"}
    if field not in allowed:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with _connect() as db:
        await db.execute(
            f"UPDATE clients SET {field} = ?, yangilangan_vaqt = ? WHERE id = ?",
            (value, now, client_id)
        )
        await db.commit()


async def delete_client(client_id: int):
    async with _connect() as db:
        await db.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        await db.execute("DELETE FROM tasks WHERE client_id = ?", (client_id,))
        await db.commit()


async def get_my_clients(qoshgan_id: int, limit: int = 50, offset: int = 0):
    """Foydalanuvchi o'zi qo'shgan mijozlar."""
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM clients WHERE qoshgan_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (qoshgan_id, limit, offset),
        ) as cur:
            return await cur.fetchall()


async def count_my_clients(qoshgan_id: int) -> int:
    async with _connect() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM clients WHERE qoshgan_id = ?", (qoshgan_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def count_clients(region_id=None) -> int:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
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

async def get_stats(region_id=None) -> dict:
    where  = f"WHERE region_id = {int(region_id)}" if region_id else ""
    async with _connect() as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            f"SELECT COUNT(*) as cnt FROM clients {where}"
        ) as cur:
            general = await cur.fetchone()

        async with db.execute(
            f"SELECT savdo_turi, COUNT(*) as cnt FROM clients {where} GROUP BY savdo_turi"
        ) as cur:
            by_type = await cur.fetchall()

        async with db.execute(
            f"SELECT savdo_subturi, COUNT(*) as cnt FROM clients {where} GROUP BY savdo_subturi"
        ) as cur:
            by_sub = await cur.fetchall()

        async with db.execute(
            f"""SELECT r.name, COUNT(c.id) as cnt
                FROM clients c JOIN regions r ON c.region_id = r.id
                {where} GROUP BY c.region_id ORDER BY cnt DESC"""
        ) as cur:
            by_region = await cur.fetchall()

    return {
        "total_clients": general["cnt"] if general else 0,
        "by_type":       [dict(r) for r in by_type],
        "by_sub":        [dict(r) for r in by_sub],
        "by_region":     [dict(r) for r in by_region],
    }


# ─── VAZIFALAR ────────────────────────────────────────────────────────────────

async def add_task(data: dict) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with _connect() as db:
        cur = await db.execute("""
            INSERT INTO tasks
                (sarlavha, tavsif, client_id, region_id, muddat, qoshgan_id, qoshilgan_vaqt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data["sarlavha"], data.get("tavsif", ""), data.get("client_id"),
            data["region_id"], data.get("muddat"), data["qoshgan_id"], now
        ))
        await db.commit()
        return cur.lastrowid


async def get_tasks(region_id=None, only_active: bool = True):
    conditions, params = [], []
    if region_id:
        conditions.append("t.region_id = ?")
        params.append(region_id)
    if only_active:
        conditions.append("t.bajarilgan = 0")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT t.*, c.ism as client_ism
        FROM tasks t LEFT JOIN clients c ON t.client_id = c.id
        {where} ORDER BY t.muddat ASC, t.id DESC LIMIT 50
    """
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, params) as cur:
            return await cur.fetchall()


async def complete_task(task_id: int):
    async with _connect() as db:
        await db.execute("UPDATE tasks SET bajarilgan = 1 WHERE id = ?", (task_id,))
        await db.commit()


async def delete_task(task_id: int):
    async with _connect() as db:
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()


async def get_overdue_tasks():
    """Muddati o'tgan, hali bajarilmagan va xabar berilmagan vazifalar."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """
        SELECT t.*, c.ism as client_ism
        FROM tasks t LEFT JOIN clients c ON t.client_id = c.id
        WHERE t.bajarilgan = 0 AND t.muddat IS NOT NULL
          AND t.muddat <= ? AND COALESCE(t.notified, 0) = 0
    """
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, (now,)) as cur:
            return await cur.fetchall()


async def mark_task_notified(task_id: int):
    """Vazifani 'xabar berildi' deb belgilash."""
    async with _connect() as db:
        await db.execute("UPDATE tasks SET notified = 1 WHERE id = ?", (task_id,))
        await db.commit()
