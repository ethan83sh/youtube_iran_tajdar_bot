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

async def go_main(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = "منوی اصلی:"):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())
    else:
        await update.effective_message.reply_text(text, reply_markup=main_menu())
