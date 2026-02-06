import re
from telegram import Update
from telegram.ext import ConversationHandler, CallbackQueryHandler, ContextTypes

from bot import menus
from bot.conversations.common import admin_only, go_main
from shared import db as dbmod

states = {
    S_PICK_POS: [CallbackQueryHandler(pick_pos, pattern=r"^QUEUE_POS:\d+$")],
}


async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    q = update.callback_query
    await q.answer()

    m = re.match(r"^QUEUE_REORDER:(\d+)$", q.data or "")
    if not m:
        await go_main(update, context)
        return ConversationHandler.END

    item_id = int(m.group(1))
    con = context.application.bot_data["db"]

    ids = dbmod.list_queued_ids(con, limit=200)
    if item_id not in ids:
        await q.edit_message_text("این آیتم در صف نیست یا حذف شده.", reply_markup=menus.back_main_kb())
        return ConversationHandler.END

    context.user_data["reorder_item_id"] = item_id
    context.user_data["queued_ids"] = ids

    await q.edit_message_text(
        f"جایگاه جدید برای آیتم #{item_id} را انتخاب کن (جابجایی با آیتمِ آن جایگاه انجام می‌شود):",
        reply_markup=menus.queue_pick_position_kb(len(ids)),
    )
    return S_PICK_POS

async def pick_pos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    q = update.callback_query
    await q.answer()

    m = re.match(r"^QUEUE_POS:(\d+)$", q.data or "")
    if not m:
        await go_main(update, context)
        return ConversationHandler.END

    pos = int(m.group(1))  # 1..N
    item_id = int(context.user_data.get("reorder_item_id"))
    ids = context.user_data.get("queued_ids") or []

    if pos < 1 or pos > len(ids):
        await q.edit_message_text("جایگاه نامعتبر است.", reply_markup=menus.back_main_kb())
        return ConversationHandler.END

    target_id = int(ids[pos - 1])
    con = context.application.bot_data["db"]

    if target_id != item_id:
        dbmod.swap_queue_order(con, item_id, target_id)

    # نمایش صف بعد از تغییر
    rows = dbmod.list_queued(con, limit=30)
    if not rows:
        await q.edit_message_text("صف خالی است.", reply_markup=menus.back_main_kb())
        return ConversationHandler.END

    await q.edit_message_text("✅ ترتیب صف تغییر کرد. صف فعلی:", reply_markup=menus.queue_list_kb(rows))
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await go_main(update, context, "کنسل شد. منوی اصلی:")
    return ConversationHandler.END

def handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(entry, pattern=r"^QUEUE_REORDER:\d+$")],
        states={S_PICK_POS: [CallbackQueryHandler(pick_pos, pattern=r"^QUEUE_POS:\d+$")]},
        fallbacks=[CallbackQueryHandler(cancel, pattern=f"^{menus.CB_CANCEL}$")],
        name="reorder_queue_conv",
        per_chat=True,
        per_user=True,
        per_message=True,
    )
