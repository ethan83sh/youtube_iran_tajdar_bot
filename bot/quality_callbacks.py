from telegram.error import BadRequest

from bot.conversations.common import admin_only


async def on_pick_quality_callback(update, context):
    """
    callback_data format: qpick:<item_id>:<height>
    chosen_height در bot_data ذخیره می‌شود تا job دفعه بعد از همان کیفیت دانلود کند.
    """
    if not await admin_only(update, context):
        return

    q = update.callback_query
    data = q.data or ""

    try:
        await q.answer()
    except BadRequest as e:
        # اگر query قدیمی شد، بی‌خیال
        if "Query is too old" in str(e):
            return
        raise

    try:
        _, item_id_str, height_str = data.split(":")
        item_id = int(item_id_str)
        height = int(height_str)
    except Exception:
        try:
            await q.edit_message_text("خطا: داده دکمه نامعتبر است.")
        except Exception:
            pass
        return

    pending = context.application.bot_data.get("pending_quality") or {}
    rec = pending.get(item_id)
    if not rec:
        try:
            await q.edit_message_text("این درخواست انتخاب کیفیت منقضی شده. دوباره /publish_now بزن.")
        except Exception:
            pass
        return

    rec["chosen_height"] = height

    try:
        await q.edit_message_text(
            f"✅ انتخاب شد: {height}p برای آیتم #{item_id}.\nحالا دوباره /publish_now بزن تا با همین کیفیت دانلود شود."
        )
    except Exception:
        pass
