import logging

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
from bot.config import YOUTUBE_API_KEY
from shared import db as dbmod
from shared.youtube_public import extract_video_id, get_video, parse_iso8601_duration_to_seconds

logger = logging.getLogger(__name__)

S_WAIT_URL = 1
S_WAIT_THUMB = 2


async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع از دکمه ADD_LINK."""
    if not await admin_only(update, context):
        return ConversationHandler.END

    q = update.callback_query
    if q:
        # فقط برای اینکه تلگرام اسپینر را قطع کند
        try:
            await q.answer()
        except Exception:
            pass

    # پاکسازی داده‌های مربوط به این flow
    for k in ("url", "video_id", "yt_title", "yt_desc", "manual_thumb_file_id"):
        context.user_data.pop(k, None)

    # خیلی مهم: پیام جدید می‌فرستیم، ادیت نمی‌کنیم (برای جلوگیری از BadRequest)
    await update.effective_chat.send_message(
        "1) لینک ویدیو یوتوب را بفرست:",
        reply_markup=menus.cancel_kb(),
    )
    return S_WAIT_URL


async def got_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    try:
        url = (update.effective_message.text or "").strip()
        logger.warning("ADD_LINK got_url: %r", url)

        if "youtube.com" not in url and "youtu.be" not in url:
            await update.effective_message.reply_text(
                "❌ لینک معتبر نیست. یک لینک یوتوب بفرست.",
                reply_markup=menus.cancel_kb(),
            )
            return S_WAIT_URL

        vid = extract_video_id(url)
        logger.warning("ADD_LINK extracted video_id: %s", vid)

        if not vid:
            await update.effective_message.reply_text(
                "❌ نتونستم videoId رو از لینک دربیارم.",
                reply_markup=menus.cancel_kb(),
            )
            return S_WAIT_URL

        item = get_video(YOUTUBE_API_KEY, vid)
        if not item or not isinstance(item, dict):
            await update.effective_message.reply_text(
                "❌ ویدیو پیدا نشد یا پاسخ API نامعتبر بود.",
                reply_markup=menus.cancel_kb(),
            )
            return S_WAIT_URL

        sn = item.get("snippet", {}) or {}
        cd = item.get("contentDetails", {}) or {}

        duration_raw = (cd.get("duration") or "").strip()
        dur_s = parse_iso8601_duration_to_seconds(duration_raw)
        logger.warning("ADD_LINK duration raw=%r dur_s=%s", duration_raw, dur_s)

        # اگر خواستی شرط ۳ دقیقه را نگه داریم:
        if dur_s <= 180:
            await update.effective_message.reply_text(
                f"⛔️ این ویدیو {dur_s} ثانیه است و زیر ۳ دقیقه محسوب می‌شود. وارد صف نشد."
            )
            await go_main(update, context)
            return ConversationHandler.END

        # همیشه عنوان/دیسک یوتوب
        context.user_data["url"] = url
        context.user_data["video_id"] = vid
        context.user_data["yt_title"] = (sn.get("title") or "").strip()
        context.user_data["yt_desc"] = (sn.get("description") or "").strip()

        await update.effective_message.reply_text(
            "2) تامبنیل را ارسال کن (عکس).\n"
            "اگر نمی‌خوای تامبنیل بدی، دستور /skip را بفرست تا از تامبنیل پیش‌فرض یوتوب استفاده شود.",
            reply_markup=menus.cancel_kb(),
        )
        return S_WAIT_THUMB

    except Exception as e:
        logger.exception("ADD_LINK got_url crashed", exc_info=e)
        await update.effective_message.reply_text(
            "❌ خطای غیرمنتظره رخ داد. دوباره از اول شروع کن (/start).",
            reply_markup=menus.cancel_kb(),
        )
        return ConversationHandler.END


async def got_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    if not update.effective_message.photo:
        await update.effective_message.reply_text(
            "❌ باید عکس بفرستی، یا اگر تامبنیل نمی‌خوای /skip را بفرست.",
            reply_markup=menus.cancel_kb(),
        )
        return S_WAIT_THUMB

    file_id = update.effective_message.photo[-1].file_id
    context.user_data["manual_thumb_file_id"] = file_id

    return await _finalize(update, context, has_manual_thumb=True)


async def skip_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدون تامبنیل دستی => تامبنیل یوتوب."""
    if not await admin_only(update, context):
        return ConversationHandler.END

    context.user_data["manual_thumb_file_id"] = None
    return await _finalize(update, context, has_manual_thumb=False)


async def _finalize(update: Update, context: ContextTypes.DEFAULT_TYPE, has_manual_thumb: bool):
    try:
        con = context.application.bot_data["db"]

        url = context.user_data.get("url")
        if not url:
            await go_main(update, context, "❌ خطا: لینک موجود نیست. دوباره از اول شروع کن.")
            return ConversationHandler.END

        title = context.user_data.get("yt_title") or ""
        desc = context.user_data.get("yt_desc") or ""

        thumb_mode = "custom" if has_manual_thumb else "yt"

        item_id = dbmod.add_queue_item_link(
            con,
            url=url,
            title=title,
            description=desc,
            thumb_mode=thumb_mode,
        )

        # اگر ستون manual_thumb_file_id را داری، اینجا ذخیره می‌کنیم
        try:
            con.execute(
                "UPDATE queue_items SET manual_thumb_file_id=? WHERE id=?",
                (context.user_data.get("manual_thumb_file_id"), item_id),
            )
            con.commit()
        except Exception as e:
            # اگر این ستون/جدول هنوز migration نشده بود، کل flow را خراب نکن
            logger.warning("ADD_LINK manual_thumb_file_id update skipped: %s", e)

        await go_main(
            update,
            context,
            f"✅ به صف اضافه شد: #{item_id}\n"
            f"🖼 تامبنیل: {'دستی' if has_manual_thumb else 'پیش‌فرض یوتوب'}",
        )
        return ConversationHandler.END

    except Exception as e:
        logger.exception("ADD_LINK finalize crashed", exc_info=e)
        await go_main(update, context, "❌ خطا در ذخیره‌سازی آیتم. لاگ سرور را بفرست.")
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await go_main(update, context, "کنسل شد. منوی اصلی:")
    return ConversationHandler.END


def handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(entry, pattern=f"^{menus.CB_ADD_LINK}$")],
        states={
            S_WAIT_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_url)],
            S_WAIT_THUMB: [
                MessageHandler(filters.PHOTO, got_thumb),
                CommandHandler("skip", skip_thumb),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern=f"^{menus.CB_CANCEL}$"),
            CommandHandler("cancel", cancel),
        ],
        name="add_link_conv",
    )
