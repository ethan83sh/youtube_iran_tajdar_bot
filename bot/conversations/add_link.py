import logging

from telegram import Update
from telegram.error import BadRequest
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
S_THUMB_CHOICE = 2
S_WAIT_THUMB = 3
S_TITLE_CHOICE = 4
S_WAIT_TITLE = 5
S_DESC_CHOICE = 6
S_WAIT_DESC = 7


def _dict_get(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else default


async def _safe_edit_or_reply(q, text: str, reply_markup=None):
    """اول تلاش می‌کند پیام دکمه را ادیت کند، اگر نشد پیام جدید می‌فرستد."""
    try:
        await q.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as e:
        logger.warning("edit_message_text failed: %s", e)
        if q.message:
            await q.message.reply_text(text, reply_markup=reply_markup)


async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    q = update.callback_query
    if not q:
        return ConversationHandler.END

    logger.warning(
        "ADD_LINK entry reached: chat=%s user=%s data=%s",
        update.effective_chat.id if update.effective_chat else None,
        update.effective_user.id if update.effective_user else None,
        q.data,
    )

    try:
        await q.answer()
    except BadRequest as e:
        if "Query is too old" not in str(e):
            raise

    for k in (
        "url", "video_id", "yt_title", "yt_desc",
        "thumb_mode", "manual_thumb_file_id",
        "title_mode", "manual_title",
        "desc_mode", "manual_desc",
    ):
        context.user_data.pop(k, None)

    await _safe_edit_or_reply(q, "لینک ویدیو یوتوب را بفرست:", reply_markup=menus.cancel_kb())
    return S_WAIT_URL


async def got_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    try:
        raw = (update.effective_message.text or "")
        url = raw.strip()
        logger.warning("ADD_LINK got_url received: %r", raw)

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
            logger.warning("ADD_LINK get_video invalid response: type=%s value=%r", type(item), item)
            await update.effective_message.reply_text(
                "❌ ویدیو پیدا نشد یا پاسخ API نامعتبر بود.",
                reply_markup=menus.cancel_kb(),
            )
            return S_WAIT_URL

        sn = _dict_get(item, "snippet", {}) or {}
        cd = _dict_get(item, "contentDetails", {}) or {}
        duration_raw = _dict_get(cd, "duration", "") or ""
        dur_s = parse_iso8601_duration_to_seconds(duration_raw)

        logger.warning("ADD_LINK duration raw=%r dur_s=%s", duration_raw, dur_s)

        if dur_s <= 180:
            await update.effective_message.reply_text(
                f"⛔️ این ویدیو {dur_s} ثانیه است و زیر ۳ دقیقه محسوب می‌شود. وارد صف نشد."
            )
            await go_main(update, context)
            return ConversationHandler.END

        context.user_data["url"] = url
        context.user_data["video_id"] = vid
        context.user_data["yt_title"] = (_dict_get(sn, "title", "") or "").strip()
        context.user_data["yt_desc"] = (_dict_get(sn, "description", "") or "").strip()

        await update.effective_message.reply_text(
            "تامبنیل را چطور می‌خوای؟",
            reply_markup=menus.link_thumb_choice_kb(),
        )
        return S_THUMB_CHOICE

    except Exception as e:
        logger.exception("ADD_LINK got_url crashed", exc_info=e)
        await update.effective_message.reply_text(
            "❌ خطای غیرمنتظره رخ داد. دوباره از اول شروع کن (/start).",
            reply_markup=menus.cancel_kb(),
        )
        return ConversationHandler.END


async def thumb_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    if q.data == menus.CB_LINK_THUMB_YT:
        context.user_data["thumb_mode"] = "yt"
        await _safe_edit_or_reply(q, "تیتر را چطور می‌خوای؟", reply_markup=menus.link_title_choice_kb())
        return S_TITLE_CHOICE

    if q.data == menus.CB_LINK_THUMB_MANUAL:
        context.user_data["thumb_mode"] = "custom"
        await _safe_edit_or_reply(q, "لطفاً تصویر تامبنیل را ارسال کن (عکس).", reply_markup=menus.cancel_kb())
        return S_WAIT_THUMB

    await go_main(update, context)
    return ConversationHandler.END


async def got_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    if not update.effective_message.photo:
        await update.effective_message.reply_text("❌ باید عکس بفرستی.", reply_markup=menus.cancel_kb())
        return S_WAIT_THUMB

    file_id = update.effective_message.photo[-1].file_id
    context.user_data["manual_thumb_file_id"] = file_id

    await update.effective_message.reply_text("تیتر را چطور می‌خوای؟", reply_markup=menus.link_title_choice_kb())
    return S_TITLE_CHOICE


async def title_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    if q.data == menus.CB_LINK_TITLE_YT:
        context.user_data["title_mode"] = "yt"
        await _safe_edit_or_reply(q, "دیسکریپشن را چطور می‌خوای؟", reply_markup=menus.link_desc_choice_kb())
        return S_DESC_CHOICE

    if q.data == menus.CB_LINK_TITLE_MANUAL:
        context.user_data["title_mode"] = "manual"
        await _safe_edit_or_reply(q, "تیتر جدید را بفرست:", reply_markup=menus.cancel_kb())
        return S_WAIT_TITLE

    await go_main(update, context)
    return ConversationHandler.END


async def got_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    t = (update.effective_message.text or "").strip()
    if len(t) < 3:
        await update.effective_message.reply_text("❌ تیتر خیلی کوتاهه. دوباره بفرست.", reply_markup=menus.cancel_kb())
        return S_WAIT_TITLE

    context.user_data["manual_title"] = t
    await update.effective_message.reply_text("دیسکریپشن را چطور می‌خوای؟", reply_markup=menus.link_desc_choice_kb())
    return S_DESC_CHOICE


async def desc_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    if q.data == menus.CB_LINK_DESC_YT:
        context.user_data["desc_mode"] = "yt"
        return await _finalize(update, context)

    if q.data == menus.CB_LINK_DESC_MANUAL:
        context.user_data["desc_mode"] = "manual"
        await _safe_edit_or_reply(q, "دیسکریپشن جدید را بفرست:", reply_markup=menus.cancel_kb())
        return S_WAIT_DESC

    await go_main(update, context)
    return ConversationHandler.END


async def got_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return ConversationHandler.END

    d = (update.effective_message.text or "").strip()
    context.user_data["manual_desc"] = d
    return await _finalize(update, context)


async def _finalize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        con = context.application.bot_data["db"]
        url = context.user_data.get("url")
        if not url:
            await go_main(update, context, "❌ خطا: لینک از حافظه پاک شده. دوباره از اول شروع کن.")
            return ConversationHandler.END

        final_title = (
            context.user_data.get("manual_title")
            if context.user_data.get("title_mode") == "manual"
            else context.user_data.get("yt_title")
        )
        final_desc = (
            context.user_data.get("manual_desc")
            if context.user_data.get("desc_mode") == "manual"
            else context.user_data.get("yt_desc")
        )

        item_id = dbmod.add_queue_item_link(
            con,
            url=url,
            title=final_title,
            description=final_desc,
            thumb_mode=context.user_data.get("thumb_mode", "yt"),
        )

        con.execute(
            """
            UPDATE queue_items
            SET title_mode=?, desc_mode=?, manual_title=?, manual_desc=?, manual_thumb_file_id=?
            WHERE id=?
            """,
            (
                context.user_data.get("title_mode"),
                context.user_data.get("desc_mode"),
                context.user_data.get("manual_title"),
                context.user_data.get("manual_desc"),
                context.user_data.get("manual_thumb_file_id"),
                item_id,
            ),
        )
        con.commit()

        await go_main(update, context, f"✅ به صف اضافه شد: #{item_id}")
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

            S_THUMB_CHOICE: [
                CallbackQueryHandler(
                    thumb_choice,
                    pattern=f"^({menus.CB_LINK_THUMB_YT}|{menus.CB_LINK_THUMB_MANUAL})$",
                )
            ],
            S_WAIT_THUMB: [MessageHandler(filters.PHOTO, got_thumb)],

            S_TITLE_CHOICE: [
                CallbackQueryHandler(
                    title_choice,
                    pattern=f"^({menus.CB_LINK_TITLE_YT}|{menus.CB_LINK_TITLE_MANUAL})$",
                )
            ],
            S_WAIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_title)],

            S_DESC_CHOICE: [
                CallbackQueryHandler(
                    desc_choice,
                    pattern=f"^({menus.CB_LINK_DESC_YT}|{menus.CB_LINK_DESC_MANUAL})$",
                )
            ],
            S_WAIT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_desc)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern=f"^{menus.CB_CANCEL}$"),
            CommandHandler("cancel", cancel),
        ],
        name="add_link_conv",
    )
