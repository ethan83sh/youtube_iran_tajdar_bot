import re
import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ConversationHandler, CallbackQueryHandler, ContextTypes, CommandHandler

from bot import menus
from bot.conversations.common import admin_only, go_main
from shared import db as dbmod

logger = logging.getLogger(__name__)

S_PICK_POS = 1


async def _safe_edit_or_reply(q, text: str, reply_markup=None):
    try:
        await q.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as e:
        logger.warning("reorder edit_message_text failed: %s", e)
        if q.message:
            await q.message.reply_text(text, reply_markup=reply_markup)


async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    q = update.callback_query
    if not q:
        return ConversationHandler.END

    try:
        await q.answer()
    except BadRequest as e:
        if "Query is too old" not in str(e):
            raise

    # FIX: raw string باید \d+ باشد نه \\d+
    m = re.match(r"^QUEUE_REORDER:(\d+)$", q.data or "")
    if not m:
        await go_main(update, context)
        return ConversationHandler.END

    item_id = int(m.group(1))
    con = context.application.bot_data["db"]

    ids = dbmod.list_queued_ids(con, limit=200)
    if item_id not in ids:
        await _safe_edit_or_reply(q, "این آیتم در صف نیست یا حذف شده.", reply_markup=menus.back_main_kb())
        return ConversationHandler.END

    context.user_data["reorder_item_id"] = item_id

    await _safe_edit_or_reply(
        q,
        f"جایگاه جدید برای آیتم #{item_id} را انتخاب کن (با آیتم آن جایگاه جابجا می‌شود):",
        reply_markup=menus.queue_pick_position_kb(len(ids)),
    )
    return S_PICK_POS


async def pick_pos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    q = update.callback_query
    if not q:
        return ConversationHandler.END

    try:
        await q.answer()
    except BadRequest as e:
        if "Query is too old" not in str(e):
            raise

    # FIX: raw string باید \d+ باشد نه \\d+
    m = re.match(r"^QUEUE_POS:(\d+)$", q.data or "")
    if not m:
        await go_main(update, context)
        return ConversationHandler.END

    pos = int(m.group(1))  # 1..N
    item_id = int(context.user_data.get("reorder_item_id") or 0)
    if not item_id:
        await go_main(update, context)
        return ConversationHandler.END

    con = context.application.bot_data["db"]
    ids = dbmod.list_queued_ids(con, limit=200)

    if pos < 1 or pos > len(ids):
        await _safe_edit_or_reply(q, "جایگاه نامعتبر است.", reply_markup=menus.back_main_kb())
        context.user_data.pop("reorder_item_id", None)
        return ConversationHandler.END

    target_id = int(ids[pos - 1])

    if target_id != item_id:
        dbmod.swap_queue_order(con, item_id, target_id)

    context.user_data.pop("reorder_item_id", None)

    rows = dbmod.list_queued(con, limit=30)
    if not rows:
        await _safe_edit_or_reply(q, "صف خالی است.", reply_markup=menus.back_main_kb())
        return ConversationHandler.END

    await _safe_edit_or_reply(q, "✅ ترتیب صف تغییر کرد. صف فعلی:", reply_markup=menus.queue_list_kb(rows))
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("reorder_item_id", None)
    await go_main(update, context, "کنسل شد. منوی اصلی:")
    return ConversationHandler.END


def handler():
    return ConversationHandler(
        entry_points=[
            # FIX: pattern باید \d+ باشد نه \\d+
            CallbackQueryHandler(entry, pattern=r"^QUEUE_REORDER:\d+$"),
        ],
        states={
            S_PICK_POS: [
                CallbackQueryHandler(pick_pos, pattern=r"^QUEUE_POS:\d+$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern=f"^{menus.CB_CANCEL}$"),
            CommandHandler("cancel", cancel),
        ],
        name="reorder_queue_conv",
        per_chat=True,
        per_user=True,
    )
