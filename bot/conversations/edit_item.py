import logging
import re

from telegram import Update
from telegram.ext import (
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from bot import menus
from bot.conversations.common import admin_only, go_main
from shared import db as dbmod

logger = logging.getLogger(__name__)

S_WAIT_TITLE = 1
S_WAIT_DESC = 2
S_WAIT_THUMB = 3


def _parse_id(prefix: str, data: str) -> int | None:
    """
    prefix مثل: "QUEUE_ITEM_EDIT_TITLE:"
    data مثل:   "QUEUE_ITEM_EDIT_TITLE:12"
    """
    m = re.match(rf"^{re.escape(prefix)}(\d+)$", data or "")
    return int(m.group(1)) if m else None


async def _start_prompt(update: Update, text: str):
    """همیشه پیام جدید بفرست؛ edit نکن تا Conversation با BadRequest نپره."""
    chat = update.effective_chat
    if chat:
        await chat.send_message(text, reply_markup=menus.cancel_kb())


async def entry_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    q = update.callback_query
    if not q:
        return ConversationHandler.END

    try:
        await q.answer()
    except Exception:
        pass

    item_id = _parse_id(menus.CB_QUEUE_ITEM_EDIT_TITLE, q.data)
    logger.warning("EDIT_ITEM entry_title data=%s item_id=%s", q.data, item_id)

    if not item_id:
        await go_main(update, context)
        return ConversationHandler.END

    context.user_data["edit_item_id"] = item_id
    await _start_prompt(update, f"تیتر جدید را برای آیتم #{item_id} بفرست:")
    return S_WAIT_TITLE


async def got_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    item_id = context.user_data.get("edit_item_id")
    title = (update.effective_message.text or "").strip()

    if not item_id:
        await go_main(update, context, "❌ خطا: آیتم انتخاب نشده. دوباره از صف وارد شو.")
        return ConversationHandler.END

    if len(title) < 3:
        await update.effective_message.reply_text("❌ تیتر نامعتبر است. دوباره بفرست.", reply_markup=menus.cancel_kb())
        return S_WAIT_TITLE

    con = context.application.bot_data["db"]
    dbmod.update_queue_title(con, int(item_id), title)

    context.user_data.pop("edit_item_id", None)
    await go_main(update, context, f"✅ تیتر آپدیت شد برای #{item_id}")
    return ConversationHandler.END


async def entry_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    q = update.callback_query
    if not q:
        return ConversationHandler.END

    try:
        await q.answer()
    except Exception:
        pass

    item_id = _parse_id(menus.CB_QUEUE_ITEM_EDIT_DESC, q.data)
    logger.warning("EDIT_ITEM entry_desc data=%s item_id=%s", q.data, item_id)

    if not item_id:
        await go_main(update, context)
        return ConversationHandler.END

    context.user_data["edit_item_id"] = item_id
    await _start_prompt(update, f"دیسکریپشن جدید را برای آیتم #{item_id} بفرست:")
    return S_WAIT_DESC


async def got_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    item_id = context.user_data.get("edit_item_id")
    if not item_id:
        await go_main(update, context, "❌ خطا: آیتم انتخاب نشده. دوباره از صف وارد شو.")
        return ConversationHandler.END

    desc = (update.effective_message.text or "").strip()

    con = context.application.bot_data["db"]
    dbmod.update_queue_desc(con, int(item_id), desc)

    context.user_data.pop("edit_item_id", None)
    await go_main(update, context, f"✅ دیسکریپشن آپدیت شد برای #{item_id}")
    return ConversationHandler.END


async def entry_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    q = update.callback_query
    if not q:
        return ConversationHandler.END

    try:
        await q.answer()
    except Exception:
        pass

    item_id = _parse_id(menus.CB_QUEUE_ITEM_EDIT_THUMB, q.data)
    logger.warning("EDIT_ITEM entry_thumb data=%s item_id=%s", q.data, item_id)

    if not item_id:
        await go_main(update, context)
        return ConversationHandler.END

    context.user_data["edit_item_id"] = item_id
    await _start_prompt(update, f"تصویر پوستر را برای آیتم #{item_id} بفرست (Photo یا File).")
    return S_WAIT_THUMB


async def got_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    item_id = context.user_data.get("edit_item_id")
    if not item_id:
        await go_main(update, context, "❌ خطا: آیتم انتخاب نشده. دوباره از صف وارد شو.")
        return ConversationHandler.END

    msg = update.effective_message
    file_id = None

    if msg.photo:
        file_id = msg.photo[-1].file_id
    elif msg.document and (msg.document.mime_type or "").startswith("image/"):
        file_id = msg.document.file_id

    if not file_id:
        await msg.reply_text("❌ باید عکس بفرستی (Photo یا File).", reply_markup=menus.cancel_kb())
        return S_WAIT_THUMB

    con = context.application.bot_data["db"]
    dbmod.update_queue_thumb_file_id(con, int(item_id), file_id)

    context.user_data.pop("edit_item_id", None)
    await go_main(update, context, f"✅ پوستر آپدیت شد برای #{item_id}")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("edit_item_id", None)
    await go_main(update, context, "کنسل شد. منوی اصلی:")
    return ConversationHandler.END


def handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(entry_title, pattern=rf"^{re.escape(menus.CB_QUEUE_ITEM_EDIT_TITLE)}\d+$"),
            CallbackQueryHandler(entry_desc, pattern=rf"^{re.escape(menus.CB_QUEUE_ITEM_EDIT_DESC)}\d+$"),
            CallbackQueryHandler(entry_thumb, pattern=rf"^{re.escape(menus.CB_QUEUE_ITEM_EDIT_THUMB)}\d+$"),
        ],
        states={
            S_WAIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_title)],
            S_WAIT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_desc)],
            S_WAIT_THUMB: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, got_thumb)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern=f"^{menus.CB_CANCEL}$"),
            CommandHandler("cancel", cancel),
        ],
        name="edit_item_conv",
    )
