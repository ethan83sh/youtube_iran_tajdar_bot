from __future__ import annotations

from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.config import ADMIN_GROUP_ID
from bot import menus


def is_admin_group(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id == ADMIN_GROUP_ID)


async def admin_only(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # فقط در گروه مدیریت
    if not is_admin_group(update):
        if update.effective_message:
            await update.effective_message.reply_text("این بات فقط در گروه مدیریت فعال است.")
        return False

    user = update.effective_user
    if not user:
        return False

    try:
        member = await context.bot.get_chat_member(ADMIN_GROUP_ID, user.id)
    except (BadRequest, Forbidden):
        # اگر دسترسی/اطلاعات عضو قابل دریافت نبود
        if update.effective_message:
            await update.effective_message.reply_text("خطا در بررسی دسترسی ادمین. بعداً دوباره تلاش کن.")
        return False

    if member.status not in ("creator", "administrator"):
        if update.effective_message:
            await update.effective_message.reply_text("فقط ادمین‌های گروه اجازه استفاده دارند.")
        return False

    return True


async def go_main(update: Update, context: ContextTypes.DEFAULT_TYPE, notice: str | None = None):
    text = notice or "منو اصلی:"
    q = update.callback_query

    if q:
        # همیشه سعی کن answer کنی تا لودینگ کلاینت نخوابه
        try:
            await q.answer()
        except BadRequest:
            pass

        # اگر پیام قابل ادیت بود، ادیت کن؛ اگر نبود، پیام جدید بفرست
        try:
            await q.edit_message_text(text, reply_markup=menus.main_menu())
            return
        except BadRequest as e:
            msg = str(e)
            # این‌ها را بی‌سروصدا هندل کن
            if "Message is not modified" in msg or "Query is too old" in msg:
                return
            if "message can't be edited" in msg or "Message can't be edited" in msg:
                # fall back به ارسال پیام جدید
                pass
            else:
                # بقیه خطاها مهم‌اند
                raise

    # اگر callback نبود یا ادیت ممکن نبود
    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=menus.main_menu())
