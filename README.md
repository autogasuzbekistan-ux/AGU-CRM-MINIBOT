# AGU CRM Minibot 🤖

Uzbekiston viloyatlari uchun Telegram CRM boti.

## Imkoniyatlar

| Funksiya | Tavsif |
|---|---|
| 👥 Mijoz qo'shish | Ism, telefon, savdo turi, shahar, hajm, izoh |
| 🔍 Mijoz qidirish | Ism, telefon yoki shahar bo'yicha qidiruv |
| ✏️ Tahrirlash | Barcha maydonlarni alohida tahrirlash |
| 🗑 O'chirish | Mijoz va unga tegishli vazifalarni o'chirish |
| ⭐ Daraja tizimi | Savdo hajmiga qarab avtomatik daraja |
| 📊 Statistika | Viloyat, savdo turi, daraja bo'yicha hisobot |
| ✅ Vazifalar | Eslatmalar, muddatlar, mijozga bog'lash |
| ⏰ Eslatmalar | Har 30 daqiqada muddati o'tgan vazifalarni tekshirish |
| 📤 Excel eksport | Viloyat yoki umumiy bazani .xlsx formatda yuklash |
| 🗺 14 viloyat | Har bir viloyat alohida CRM + umumiy ko'rinish |

## Daraja tizimi

| Daraja | Savdo hajmi |
|---|---|
| 🆕 Yangi | $1,000 dan kam |
| 🥉 1-daraja | $1,000 – $10,000 |
| 🥈 2-daraja | $10,001 – $30,000 |
| 🥇 3-daraja | $30,001 – $50,000 |
| 💎 VIP | $50,000 dan yuqori |

## O'rnatish

### 1. Repozitoriyni klonlash
```bash
git clone <repo-url>
cd AGU-CRM-MINIBOT
```

### 2. Virtual muhit va paketlar
```bash
python -m venv venv
source venv/bin/activate       # Linux/Mac
# yoki
venv\Scripts\activate          # Windows

pip install -r requirements.txt
```

### 3. .env fayl yaratish
```bash
cp .env.example .env
```
`.env` faylni tahrirlang:
```
BOT_TOKEN=your_bot_token_from_BotFather
ADMIN_IDS=123456789,987654321
DB_PATH=crm_bot.db
```

### 4. Botni ishga tushirish
```bash
python main.py
```

## Serverda ishlatish (systemd)

```ini
[Unit]
Description=AGU CRM Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/AGU-CRM-MINIBOT
ExecStart=/home/ubuntu/AGU-CRM-MINIBOT/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Heroku deployment

```bash
heroku create agu-crm-bot
heroku config:set BOT_TOKEN=your_token ADMIN_IDS=123456789
git push heroku main
```

## Bot komandalar

| Komanda | Tavsif |
|---|---|
| `/start` | Botni ishga tushirish / viloyat tanlash |
| `/mijoz <ID>` | Mijoz tafsilotlarini ko'rish |
| `/vazifa <ID>` | Vazifa ustida amal bajarish |

## Fayl tuzilmasi

```
AGU-CRM-MINIBOT/
├── main.py              # Asosiy entry point
├── config.py            # Konfiguratsiya, viloyatlar, daraja hisob
├── database.py          # SQLite async operatsiyalar
├── keyboards.py         # Barcha Telegram klaviaturalar
├── handlers/
│   ├── start.py         # /start, viloyat tanlash
│   ├── clients.py       # Mijozlar CRUD
│   ├── tasks.py         # Vazifalar
│   ├── stats.py         # Statistika
│   └── export.py        # Excel eksport
├── requirements.txt
├── .env.example
└── README.md
```

## Texnologiyalar

- **python-telegram-bot 20.x** — Async Telegram bot framework
- **aiosqlite** — Async SQLite database
- **openpyxl** — Excel (.xlsx) yaratish
- **APScheduler** — Vazifa eslatmalari uchun scheduler
- **python-dotenv** — Konfiguratsiya boshqaruvi
