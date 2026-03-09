import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN, ADMIN_IDS
from database import init_db, get_overdue_tasks

# ─── HANDLERLARNI IMPORT QILISH ───────────────────────────────────────────────
from handlers.start import (
    start, back_to_main, handle_cancel, handle_region_selection
)
from handlers.clients import (
    clients_menu, client_add_start, add_ism, add_telefon, add_turi_callback,
    add_shahar, add_savdo, add_izoh, add_izoh_skip, client_list,
    client_search_start, client_search_query, client_detail_command,
    client_detail_callback, edit_start_callback, edit_field_callback,
    edit_turi_callback, edit_value_received, delete_callback,
    delete_confirm_callback, edit_start_ask_id, delete_ask_id,
    delete_id_received,
    ADD_ISM, ADD_TELEFON, ADD_TURI, ADD_SHAHAR, ADD_SAVDO, ADD_IZOH,
    SEARCH_QUERY, EDIT_VALUE, DELETE_CONFIRM,
)
from handlers.tasks import (
    tasks_menu, task_add_start, task_title, task_client, task_deadline,
    task_desc, task_list, task_detail_command, task_complete_callback,
    task_delete_callback, task_delete_confirm_callback,
    TASK_TITLE, TASK_CLIENT, TASK_DEADLINE, TASK_DESC,
)
from handlers.stats import (
    stats_menu, stats_general, stats_by_region, stats_by_type, stats_by_grade
)
from handlers.export import (
    export_menu, export_my_region, export_all, export_choose_region,
    export_region_selected,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── ESLATMA YUBORUVCHI ───────────────────────────────────────────────────────

async def send_overdue_reminders(app: Application):
    tasks = await get_overdue_tasks()
    if not tasks:
        return
    for t in tasks:
        # Barcha adminlarga xabar yuborish
        for admin_id in ADMIN_IDS:
            try:
                client_info = f"\n🔗 Mijoz: *{t['client_ism']}*" if t["client_ism"] else ""
                await app.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"⏰ *Muddati o'tgan vazifa!*\n\n"
                        f"📝 *{t['sarlavha']}*{client_info}\n"
                        f"📄 {t['tavsif'] or '—'}\n"
                        f"🗓 Muddat: {t['muddat']}\n"
                        f"ID: `{t['id']}`\n\n"
                        f"_/vazifa {t['id']} — bajarish uchun_"
                    ),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Eslatma yuborishda xato (admin {admin_id}): {e}")

# ─── CONVERSATION HANDLER: MIJOZ QO'SHISH ────────────────────────────────────

def build_add_client_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(client_add_start, pattern="^client_add$")],
        states={
            ADD_ISM:    [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ism)],
            ADD_TELEFON:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_telefon)],
            ADD_TURI:   [CallbackQueryHandler(add_turi_callback, pattern="^turi_")],
            ADD_SHAHAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_shahar)],
            ADD_SAVDO:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_savdo)],
            ADD_IZOH:   [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_izoh),
                CallbackQueryHandler(add_izoh_skip, pattern="^cancel$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(handle_cancel, pattern="^cancel$")],
        allow_reentry=True,
    )

# ─── CONVERSATION HANDLER: MIJOZ QIDIRISH ────────────────────────────────────

def build_search_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(client_search_start, pattern="^client_search$")],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, client_search_query)],
        },
        fallbacks=[CallbackQueryHandler(handle_cancel, pattern="^cancel$")],
        allow_reentry=True,
    )

# ─── CONVERSATION HANDLER: MIJOZ TAHRIRLASH ──────────────────────────────────

def build_edit_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(edit_start_callback, pattern=r"^edit_\d+$"),
            CallbackQueryHandler(edit_start_ask_id,   pattern="^client_edit_start$"),
        ],
        states={
            EDIT_VALUE: [
                CallbackQueryHandler(edit_field_callback,  pattern=r"^editfield_\d+_\w+$"),
                CallbackQueryHandler(edit_turi_callback,   pattern="^turi_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value_received),
            ],
        },
        fallbacks=[CallbackQueryHandler(handle_cancel, pattern="^cancel$")],
        allow_reentry=True,
    )

# ─── CONVERSATION HANDLER: MIJOZ O'CHIRISH ───────────────────────────────────

def build_delete_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(delete_ask_id, pattern="^client_delete_start$")],
        states={
            DELETE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_id_received),
            ],
        },
        fallbacks=[CallbackQueryHandler(handle_cancel, pattern="^cancel$")],
        allow_reentry=True,
    )

# ─── CONVERSATION HANDLER: VAZIFA QO'SHISH ───────────────────────────────────

def build_task_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(task_add_start, pattern="^task_add$"),
            CallbackQueryHandler(task_add_start, pattern=r"^task_for_\d+$"),
        ],
        states={
            TASK_TITLE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, task_title)],
            TASK_CLIENT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, task_client)],
            TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_deadline)],
            TASK_DESC:     [MessageHandler(filters.TEXT & ~filters.COMMAND, task_desc)],
        },
        fallbacks=[CallbackQueryHandler(handle_cancel, pattern="^cancel$")],
        allow_reentry=True,
    )

# ─── ASOSIY ───────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN .env faylida yo'q!")

    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handlerlar (tartib muhim)
    app.add_handler(build_add_client_conv())
    app.add_handler(build_search_conv())
    app.add_handler(build_edit_conv())
    app.add_handler(build_delete_conv())
    app.add_handler(build_task_conv())

    # Oddiy command handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mijoz", client_detail_command))
    app.add_handler(CommandHandler("vazifa", task_detail_command))

    # Callback query handlerlar — menyular
    app.add_handler(CallbackQueryHandler(back_to_main,        pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(handle_cancel,       pattern="^cancel$"))

    # Viloyat tanlash
    app.add_handler(CallbackQueryHandler(handle_region_selection, pattern=r"^region_"))

    # Mijozlar
    app.add_handler(CallbackQueryHandler(clients_menu,        pattern="^menu_clients$"))
    app.add_handler(CallbackQueryHandler(client_list,         pattern=r"^client_list$|^clist_page_\d+$"))
    app.add_handler(CallbackQueryHandler(delete_callback,     pattern=r"^del_\d+$"))
    app.add_handler(CallbackQueryHandler(delete_confirm_callback, pattern=r"^delclient_confirm_\d+$"))
    app.add_handler(CallbackQueryHandler(client_detail_callback,  pattern=r"^client_detail_\d+$"))

    # Vazifalar
    app.add_handler(CallbackQueryHandler(tasks_menu,          pattern="^menu_tasks$"))
    app.add_handler(CallbackQueryHandler(task_list,           pattern=r"^task_list$|^task_done_list$"))
    app.add_handler(CallbackQueryHandler(task_complete_callback,    pattern=r"^task_complete_\d+$"))
    app.add_handler(CallbackQueryHandler(task_delete_callback,      pattern=r"^task_del_\d+$"))
    app.add_handler(CallbackQueryHandler(task_delete_confirm_callback, pattern=r"^deltask_confirm_\d+$"))

    # Statistika
    app.add_handler(CallbackQueryHandler(stats_menu,          pattern="^menu_stats$"))
    app.add_handler(CallbackQueryHandler(stats_general,       pattern="^stats_general$"))
    app.add_handler(CallbackQueryHandler(stats_by_region,     pattern="^stats_by_region$"))
    app.add_handler(CallbackQueryHandler(stats_by_type,       pattern="^stats_by_type$"))
    app.add_handler(CallbackQueryHandler(stats_by_grade,      pattern="^stats_by_grade$"))

    # Eksport
    app.add_handler(CallbackQueryHandler(export_menu,         pattern="^menu_export$"))
    app.add_handler(CallbackQueryHandler(export_my_region,    pattern="^export_my_region$"))
    app.add_handler(CallbackQueryHandler(export_all,          pattern="^export_all$"))
    app.add_handler(CallbackQueryHandler(export_choose_region,pattern="^export_choose$"))
    app.add_handler(CallbackQueryHandler(export_region_selected, pattern=r"^region_"))

    # Viloyat o'zgartirish
    app.add_handler(CallbackQueryHandler(
        lambda u, c: handle_region_selection(u, c),
        pattern="^menu_change_region$"
    ))

    # ─── Eslatma scheduler ───
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_overdue_reminders,
        trigger="interval",
        minutes=30,
        args=[app],
    )
    scheduler.start()

    logger.info("✅ CRM Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import asyncio

    async def setup():
        await init_db()

    asyncio.run(setup())
    main()
