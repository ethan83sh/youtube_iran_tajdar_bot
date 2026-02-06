import re
from telegram import Update
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from bot import menus
from bot.conversations.common import admin_only, go_main
from shared import db as dbmod

S_WAIT_TITLE = 1
S_WAIT_DESC = 2
S_WAIT_THUMB = 3

def _parse_id(prefix: str, data: str) -> int | None:
    m = re.match(rf"^{re.escape(prefix)}(\d+)$", data or "")
    return int(m.group(1)) if m else None

async def entry_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END
    q = update.callback_query
    await q.answer()
    item_id = _parse_id(menus.CB_QUEUE_ITEM_EDIT_TITLE, q.data)
    if not item_id:
        await go_main(update, context)
        return ConversationHandler.END
    context.user_data["edit_item_id"] = item_id
    await q.edit_message_text("تیتر جدید را بفرست:", reply_markup=menus.cancel_kb())
    return S_WAIT_TITLE

async def got_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END
    item_id = context.user_data.get("edit_item_id")
    title = (update.effective_message.text or "").strip()
    if not item_id or len(title) < 3:
        await update.effective_message.reply_text("❌ تیتر نامعتبر است. دوباره بفرست.", reply_markup=menus.cancel_kb())
        return S_WAIT_TITLE
    con = context.application.bot_data["db"]
    dbmod.update_queue_title(con, int(item_id), title)
    await go_main(update, context, f"✅ تیتر آپدیت شد برای #{item_id}")
    return ConversationHandler.END

async def entry_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END
    q = update.callback_query
    await q.answer()
    item_id = _parse_id(menus.CB_QUEUE_ITEM_EDIT_DESC, q.data)
    if not item_id:
        await go_main(update, context)
        return ConversationHandler.END
    context.user_data["edit_item_id"] = item_id
    await q.edit_message_text("دیسکریپشن جدید را بفرست:", reply_markup=menus.cancel_kb())
    return S_WAIT_DESC

async def got_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END
    item_id = context.user_data.get("edit_item_id")
    if not item_id:
        return ConversationHandler.END
    desc = (update.effective_message.text or "").strip()
    con = context.application.bot_data["db"]
    dbmod.update_queue_desc(con, int(item_id), desc)
    await go_main(update, context, f"✅ دیسکریپشن آپدیت شد برای #{item_id}")
    return ConversationHandler.END

async def entry_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END
    q = update.callback_query
    await q.answer()
    item_id = _parse_id(menus.CB_QUEUE_ITEM_EDIT_THUMB, q.data)
    if not item_id:
        await go_main(update, context)
        return ConversationHandler.END
    context.user_data["edit_item_id"] = item_id
    await q.edit_message_text("تصویر پوستر را بفرست (عکس).", reply_markup=menus.cancel_kb())
    return S_WAIT_THUMB

async def got_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END
    item_id = context.user_data.get("edit_item_id")
    if not item_id:
        return ConversationHandler.END
    if not update.effective_message.photo:
        await update.effective_message.reply_text("❌ باید عکس بفرستی.", reply_markup=menus.cancel_kb())
        return S_WAIT_THUMB
    file_id = update.effective_message.photo[-1].file_id
    con = context.application.bot_data["db"]
    dbmod.update_queue_thumb_file_id(con, int(item_id), file_id)
    await go_main(update, context, f"✅ پوستر آپدیت شد برای #{item_id}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await go_main(update, context, "کنسل شد. منوی اصلی:")
    return ConversationHandler.END

def handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(entry_title, pattern=r"^QUEUE_ITEM_EDIT_TITLE:\d+$"),
            CallbackQueryHandler(entry_desc, pattern=r"^QUEUE_ITEM_EDIT_DESC:\d+$"),
            CallbackQueryHandler(entry_thumb, pattern=r"^QUEUE_ITEM_EDIT_THUMB:\d+$"),
        ],
        states={
            S_WAIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_title)],
            S_WAIT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_desc)],
            S_WAIT_THUMB: [MessageHandler(filters.PHOTO, got_thumb)],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern=f"^{menus.CB_CANCEL}$")],
        name="edit_item_conv",
    )
