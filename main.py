import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN
from database import init_db

# ─── HANDLER IMPORTLAR ────────────────────────────────────────────────────────
from handlers.start import (
    start, back_to_main, handle_cancel, handle_region_selection,
    change_region_menu, noop_callback,
)
from handlers.clients import (
    clients_menu, client_add_start,
    add_ism, add_telefon, add_manzil, add_kasb,
    add_savdo_turi_cb, add_savdo_subturi_cb, add_izoh, add_izoh_skip,
    client_list, client_search_start, client_search_query,
    client_detail_command, client_detail_callback,
    edit_start_callback, edit_field_callback,
    edit_turi_cb, edit_subturi_cb, edit_value_received, edit_start_ask_id,
    delete_callback, delete_confirm_callback, delete_ask_id, delete_id_received,
    ADD_ISM, ADD_TELEFON, ADD_MANZIL, ADD_KASB,
    ADD_SAVDO_TURI, ADD_SAVDO_SUBTURI, ADD_IZOH,
    SEARCH_QUERY, EDIT_VALUE, DELETE_CONFIRM,
)
from handlers.tasks import (
    tasks_menu, task_add_start, task_title, task_client, task_deadline,
    task_desc, task_list, task_detail_command,
    task_complete_callback, task_delete_callback, task_delete_confirm_callback,
    TASK_TITLE, TASK_CLIENT, TASK_DEADLINE, TASK_DESC,
)
from handlers.stats import (
    stats_menu, stats_general, stats_by_region, stats_by_type, stats_by_grade,
)
from handlers.export import (
    export_menu, export_my_region, export_all,
    export_choose_region, export_region_selected, send_daily_report,
)
from handlers.admin import admin_users, admin_send_report
from handlers.export import get_overdue_tasks_and_notify

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── CONVERSATION HANDLERLAR ──────────────────────────────────────────────────

def build_add_client_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(client_add_start, pattern="^client_add$"),
        ],
        states={
            ADD_ISM:          [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ism)],
            ADD_TELEFON:      [MessageHandler(filters.TEXT & ~filters.COMMAND, add_telefon)],
            ADD_MANZIL:       [MessageHandler(filters.TEXT & ~filters.COMMAND, add_manzil)],
            ADD_KASB:         [MessageHandler(filters.TEXT & ~filters.COMMAND, add_kasb)],
            ADD_SAVDO_TURI:   [CallbackQueryHandler(add_savdo_turi_cb, pattern=r"^turi_")],
            ADD_SAVDO_SUBTURI:[CallbackQueryHandler(add_savdo_subturi_cb, pattern=r"^subturi_")],
            ADD_IZOH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_izoh),
                CallbackQueryHandler(add_izoh_skip, pattern="^skip_izoh$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(handle_cancel, pattern="^cancel$")],
        allow_reentry=True,
    )

def build_search_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(client_search_start, pattern="^client_search$")],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, client_search_query)],
        },
        fallbacks=[CallbackQueryHandler(handle_cancel, pattern="^cancel$")],
        allow_reentry=True,
    )

def build_edit_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(edit_start_callback, pattern=r"^edit_\d+$"),
            CallbackQueryHandler(edit_start_ask_id,   pattern="^client_edit_start$"),
        ],
        states={
            EDIT_VALUE: [
                CallbackQueryHandler(edit_field_callback, pattern=r"^editfield_\d+_\w+$"),
                CallbackQueryHandler(edit_turi_cb,        pattern=r"^turi_"),
                CallbackQueryHandler(edit_subturi_cb,     pattern=r"^subturi_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value_received),
            ],
        },
        fallbacks=[CallbackQueryHandler(handle_cancel, pattern="^cancel$")],
        allow_reentry=True,
    )

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
        raise ValueError("BOT_TOKEN .env faylida topilmadi!")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )

    # ConversationHandlerlar (AVVAL ro'yxatga olinishi shart)
    app.add_handler(build_add_client_conv())
    app.add_handler(build_search_conv())
    app.add_handler(build_edit_conv())
    app.add_handler(build_delete_conv())
    app.add_handler(build_task_conv())

    # Oddiy komandalar
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("mijoz",  client_detail_command))
    app.add_handler(CommandHandler("vazifa", task_detail_command))

    # ─── Callback handlerlar ───────────────────────────────────────────────────

    # Umumiy
    app.add_handler(CallbackQueryHandler(back_to_main,       pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(handle_cancel,      pattern="^cancel$"))
    app.add_handler(CallbackQueryHandler(noop_callback,      pattern="^noop$"))

    # Viloyat — bitta dispatcher: export_choosing flagini tekshiradi
    app.add_handler(CallbackQueryHandler(change_region_menu, pattern="^menu_change_region$"))

    async def region_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if ctx.user_data.get("export_choosing"):
            return await export_region_selected(update, ctx)
        return await handle_region_selection(update, ctx)

    app.add_handler(CallbackQueryHandler(region_router, pattern=r"^region_"))

    # Mijozlar
    app.add_handler(CallbackQueryHandler(clients_menu,          pattern="^menu_clients$"))
    app.add_handler(CallbackQueryHandler(client_list,           pattern=r"^client_list$|^clist_page_\d+$"))
    app.add_handler(CallbackQueryHandler(client_detail_callback,pattern=r"^client_detail_\d+$"))
    app.add_handler(CallbackQueryHandler(delete_callback,       pattern=r"^del_\d+$"))
    app.add_handler(CallbackQueryHandler(delete_confirm_callback, pattern=r"^delclient_confirm_\d+$"))

    # Vazifalar
    app.add_handler(CallbackQueryHandler(tasks_menu,             pattern="^menu_tasks$"))
    app.add_handler(CallbackQueryHandler(task_list,              pattern=r"^task_list$|^task_done_list$"))
    app.add_handler(CallbackQueryHandler(task_complete_callback, pattern=r"^task_complete_\d+$"))
    app.add_handler(CallbackQueryHandler(task_delete_callback,   pattern=r"^task_del_\d+$"))
    app.add_handler(CallbackQueryHandler(task_delete_confirm_callback, pattern=r"^deltask_confirm_\d+$"))

    # Statistika
    app.add_handler(CallbackQueryHandler(stats_menu,             pattern="^menu_stats$"))
    app.add_handler(CallbackQueryHandler(stats_general,          pattern="^stats_general$"))
    app.add_handler(CallbackQueryHandler(stats_by_region,        pattern="^stats_by_region$"))
    app.add_handler(CallbackQueryHandler(stats_by_type,          pattern="^stats_by_type$"))
    app.add_handler(CallbackQueryHandler(stats_by_grade,         pattern="^stats_by_grade$|^stats_by_sub$"))

    # Eksport
    app.add_handler(CallbackQueryHandler(export_menu,            pattern="^menu_export$"))
    app.add_handler(CallbackQueryHandler(export_my_region,       pattern="^export_my_region$"))
    app.add_handler(CallbackQueryHandler(export_all,             pattern="^export_all$"))
    app.add_handler(CallbackQueryHandler(export_choose_region,   pattern="^export_choose$"))
    # region_ uchun bitta dispatcher — ichida export_choosing flagini tekshiradi

    # Admin
    app.add_handler(CallbackQueryHandler(admin_users,            pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin_send_report,      pattern="^admin_send_report$"))

    # ─── Schedulerlar ─────────────────────────────────────────────────────────
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

    # Har kecha soat 22:00 da kunlik hisobot
    scheduler.add_job(
        send_daily_report,
        trigger="cron",
        hour=22,
        minute=0,
        args=[app],
        id="daily_report_2200",
    )
    # Har 30 daqiqada muddati o'tgan vazifalarni tekshirish
    scheduler.add_job(
        get_overdue_tasks_and_notify,
        trigger="interval",
        minutes=30,
        args=[app],
        id="overdue_tasks",
    )

    logger.info("✅ AGU CRM Bot ishga tushdi! Har kecha 22:00 da hisobot yuboriladi.")

    async def post_init(application):
        scheduler.start()

    app.post_init = post_init
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def setup():
        await init_db()

    loop.run_until_complete(setup())
    main()
