import re
import asyncio
import logging
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
    handle_worker_selection, change_region_menu, noop_callback,
)
from handlers.clients import (
    clients_menu, client_add_start,
    add_ism, add_telefon, add_telefon2, add_location_geo, add_location_text,
    add_savdo_turi_msg, add_savdo_subturi_msg,
    client_list, my_client_list, client_search_start, client_search_query,
    client_detail_command, client_detail_callback,
    edit_start_callback, edit_field_callback,
    edit_turi_cb, edit_subturi_cb, edit_value_received, edit_start_ask_id,
    edit_location_geo,
    delete_callback, delete_confirm_callback, delete_ask_id, delete_id_received,
    confirm_client_callback,
    ADD_ISM, ADD_TELEFON, ADD_TELEFON2, ADD_LOCATION,
    ADD_SAVDO_TURI, ADD_SAVDO_SUBTURI,
    SEARCH_QUERY, EDIT_VALUE, DELETE_CONFIRM,
)
from handlers.tasks import (
    tasks_menu, task_add_start, task_title, task_client, task_deadline,
    task_desc, task_list, task_done_list, task_detail_command,
    task_complete_callback, task_delete_callback, task_delete_confirm_callback,
    TASK_TITLE, TASK_CLIENT, TASK_DEADLINE, TASK_DESC,
)
from handlers.stats import (
    stats_menu, stats_general, stats_by_region, stats_by_type, stats_by_grade,
)
from handlers.export import (
    export_menu, export_my_region, export_all,
    export_choose_region, export_region_selected, send_daily_report,
    get_overdue_tasks_and_notify,
)
from handlers.admin import admin_users, admin_send_report
from keyboards import (
    BTN_CLIENTS, BTN_STATS, BTN_TASKS, BTN_EXPORT, BTN_REGION,
    BTN_USERS, BTN_REPORT,
    BTN_ADD_CLIENT, BTN_SEARCH_CLIENT, BTN_CLIENT_LIST, BTN_MY_CLIENTS,
    BTN_EDIT_CLIENT, BTN_DELETE_CLIENT,
    BTN_ADD_TASK, BTN_ACTIVE_TASKS, BTN_DONE_TASKS,
    BTN_STATS_GENERAL, BTN_STATS_REGION, BTN_STATS_TYPE, BTN_STATS_SUB,
    BTN_EXPORT_MY, BTN_EXPORT_ALL, BTN_EXPORT_CHOOSE,
    BTN_BACK, BTN_CANCEL,
    BTN_LOCATION_MANUAL,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── CONVERSATION HANDLERLAR ──────────────────────────────────────────────────

def _txt(btn: str):
    return filters.Regex(f"^{re.escape(btn)}$")

def _fallbacks():
    return [
        MessageHandler(_txt(BTN_CANCEL), handle_cancel),
        MessageHandler(_txt(BTN_BACK),   handle_cancel),
    ]

def build_add_client_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(_txt(BTN_ADD_CLIENT), client_add_start),
            CallbackQueryHandler(client_add_start, pattern="^client_add$"),
        ],
        states={
            ADD_ISM:      [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ism)],
            ADD_TELEFON:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_telefon)],
            ADD_TELEFON2: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_telefon2)],
            ADD_LOCATION: [
                MessageHandler(filters.LOCATION, add_location_geo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_location_text),
            ],
            ADD_SAVDO_TURI:    [MessageHandler(filters.TEXT & ~filters.COMMAND, add_savdo_turi_msg)],
            ADD_SAVDO_SUBTURI: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_savdo_subturi_msg)],
        },
        fallbacks=_fallbacks(),
        allow_reentry=True,
        per_message=False,
        block=False,
    )

def build_search_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(_txt(BTN_SEARCH_CLIENT), client_search_start)],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, client_search_query)],
        },
        fallbacks=_fallbacks(),
        allow_reentry=True,
        per_message=False,
        block=False,
    )

def build_edit_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(edit_start_callback, pattern=r"^edit_\d+$"),
            MessageHandler(_txt(BTN_EDIT_CLIENT), edit_start_ask_id),
        ],
        states={
            EDIT_VALUE: [
                CallbackQueryHandler(edit_field_callback, pattern=r"^editfield_\d+_\w+$"),
                CallbackQueryHandler(edit_turi_cb,        pattern=r"^turi_"),
                CallbackQueryHandler(edit_subturi_cb,     pattern=r"^subturi_"),
                MessageHandler(filters.LOCATION,                      edit_location_geo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value_received),
            ],
        },
        fallbacks=_fallbacks(),
        allow_reentry=True,
        per_message=False,
        block=False,
    )

def build_delete_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(_txt(BTN_DELETE_CLIENT), delete_ask_id)],
        states={
            DELETE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_id_received),
            ],
        },
        fallbacks=_fallbacks(),
        allow_reentry=True,
        per_message=False,
        block=False,
    )

def build_task_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(_txt(BTN_ADD_TASK), task_add_start),
            CallbackQueryHandler(task_add_start, pattern=r"^task_for_\d+$"),
        ],
        states={
            TASK_TITLE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, task_title)],
            TASK_CLIENT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, task_client)],
            TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_deadline)],
            TASK_DESC:     [MessageHandler(filters.TEXT & ~filters.COMMAND, task_desc)],
        },
        fallbacks=_fallbacks(),
        allow_reentry=True,
        per_message=False,
        block=False,
    )


# ─── XATO HANDLER ─────────────────────────────────────────────────────────────

async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error("Handler xatosi!", exc_info=ctx.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"⚠️ Xato: {type(ctx.error).__name__}: {ctx.error}"
            )
        except Exception:
            pass


# ─── ASOSIY (SYNC) ────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN .env faylida topilmadi!")

    # 1. DB ni oldin ishga tushirish (alohida, muammosiz)
    asyncio.run(init_db())
    logger.info("✅ DB tayyor")

    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

    # post_init: faqat scheduler uchun (DB shart emas)
    async def _post_init(application: Application) -> None:
        scheduler.add_job(
            send_daily_report, "cron", hour=22, minute=0, args=[application]
        )
        scheduler.add_job(
            get_overdue_tasks_and_notify, "interval", minutes=30, args=[application]
        )
        scheduler.start()
        logger.info("✅ Scheduler tayyor")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(_post_init)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )

    app.add_error_handler(error_handler)

    # ── ConversationHandlerlar (birinchi) ─────────────────────────────────────
    app.add_handler(build_add_client_conv())
    app.add_handler(build_search_conv())
    app.add_handler(build_edit_conv())
    app.add_handler(build_delete_conv())
    app.add_handler(build_task_conv())

    # ── Komandalar ────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("mijoz",  client_detail_command))
    app.add_handler(CommandHandler("vazifa", task_detail_command))

    # ── Inline callback handlerlar ────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(noop_callback, pattern="^noop$"))

    async def region_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if ctx.user_data.get("export_choosing"):
            return await export_region_selected(update, ctx)
        return await handle_region_selection(update, ctx)

    app.add_handler(CallbackQueryHandler(handle_worker_selection,    pattern=r"^worker_"))
    app.add_handler(CallbackQueryHandler(region_router,              pattern=r"^region_"))
    app.add_handler(CallbackQueryHandler(client_detail_callback,     pattern=r"^client_detail_\d+$"))
    app.add_handler(CallbackQueryHandler(delete_callback,            pattern=r"^del_\d+$"))
    app.add_handler(CallbackQueryHandler(delete_confirm_callback,    pattern=r"^delclient_confirm_\d+$"))
    app.add_handler(CallbackQueryHandler(client_list,                pattern=r"^clist_page_\d+$"))
    app.add_handler(CallbackQueryHandler(task_complete_callback,     pattern=r"^task_complete_\d+$"))
    app.add_handler(CallbackQueryHandler(task_delete_callback,       pattern=r"^task_del_\d+$"))
    app.add_handler(CallbackQueryHandler(task_delete_confirm_callback, pattern=r"^deltask_confirm_\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_client_callback,      pattern=r"^confirm_\d+$"))
    app.add_handler(CallbackQueryHandler(my_client_list,               pattern=r"^myclients_page_\d+$"))

    # ── ReplyKeyboard text handlerlar (group=1) ───────────────────────────────
    def add_txt(pattern: str, handler):
        app.add_handler(
            MessageHandler(filters.Regex(f"^{re.escape(pattern)}$"), handler),
            group=1,
        )

    add_txt(BTN_CLIENTS,       clients_menu)
    add_txt(BTN_STATS,         stats_menu)
    add_txt(BTN_TASKS,         tasks_menu)
    add_txt(BTN_EXPORT,        export_menu)
    add_txt(BTN_REGION,        change_region_menu)
    add_txt(BTN_USERS,         admin_users)
    add_txt(BTN_REPORT,        admin_send_report)
    add_txt(BTN_CLIENT_LIST,   client_list)
    add_txt(BTN_MY_CLIENTS,    my_client_list)
    add_txt(BTN_ACTIVE_TASKS,  task_list)
    add_txt(BTN_DONE_TASKS,    task_done_list)
    add_txt(BTN_STATS_GENERAL, stats_general)
    add_txt(BTN_STATS_REGION,  stats_by_region)
    add_txt(BTN_STATS_TYPE,    stats_by_type)
    add_txt(BTN_STATS_SUB,     stats_by_grade)
    add_txt(BTN_EXPORT_MY,     export_my_region)
    add_txt(BTN_EXPORT_ALL,    export_all)
    add_txt(BTN_EXPORT_CHOOSE, export_choose_region)
    add_txt(BTN_BACK,          back_to_main)
    add_txt(BTN_CANCEL,        handle_cancel)

    logger.info("✅ AGU CRM Bot ishga tushdi!")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
