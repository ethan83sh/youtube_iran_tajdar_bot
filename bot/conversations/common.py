from telegram import Update
from telegram.ext import ContextTypes
from bot.config import ADMIN_GROUP_ID
from bot.menus import main_menu

def is_admin_group(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id == ADMIN_GROUP_ID)

async def admin_only(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not is_admin_group(update):
        if update.effective_message:
            await update.effective_message.reply_text("این بات فقط در گروه مدیریت فعال است.")
        return False
    user = update.effective_user
    if not user:
        return False
    member = await context.bot.get_chat_member(ADMIN_GROUP_ID, user.id)
    if member.status not in ("creator", "administrator"):
        if update.effective_message:
            await update.effective_message.reply_text("فقط ادمین‌های گروه اجازه استفاده دارند.")
        return False
    return True

from telegram.error import BadRequest

async def go_main(update, context, notice: str | None = None):
    q = update.callback_query

    if q:
        try:
            await q.answer()
        except BadRequest:
            pass  # Query is too old / invalid -> ignore

        # اگر پیام دکمه‌ای داریم، ادیت کن
        text = notice or "منو اصلی:"
        await q.edit_message_text(text, reply_markup=menus.main_kb())
        return

    # اگر با Command آمده (callback_query ندارد)
    text = notice or "منو اصلی:"
    await update.effective_message.reply_text(text, reply_markup=menus.main_kb())

