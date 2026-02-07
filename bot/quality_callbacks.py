from telegram.error import BadRequest

from bot.conversations.common import admin_only


async def on_pick_quality_callback(update, context):
    """
    callback_data format: qpick:<item_id>:<height>

    pending_quality structure in bot_data:
      bot_data["pending_quality"][item_id] = {"chosen_height": int|None, ...}
    """
    if not await admin_only(update, context):
        return

    q = update.callback_query
    if not q:
        return

    data = q.data or ""
    if not data.startswith("qpick:"):
        return

    # جواب دادن سریع برای اینکه کلاینت تلگرام لودینگ نخوابونه
    try:
        await q.answer()
    except BadRequest as e:
        if "Query is too old" in str(e):
            return
        raise

    try:
        _, item_id_str, height_str = data.split(":", 2)
        item_id = int(item_id_str)
        height = int(height_str)
    except Exception:
        try:
            await q.edit_message_text("خطا: داده دکمه نامعتبر است.")
        except BadRequest:
            pass
        return

    pending = context.application.bot_data.get("pending_quality")
    if not isinstance(pending, dict):
        pending = {}
        context.application.bot_data["pending_quality"] = pending

    rec = pending.get(item_id)
    if not isinstance(rec, dict):
        try:
            await q.edit_message_text("این درخواست انتخاب کیفیت منقضی شده. دوباره /publish_now بزن.")
        except BadRequest:
            pass
        return

    rec["chosen_height"] = height

    # اگر می‌خوای بعد از انتخاب، pending پاک بشه تا انتخاب قدیمی اثر نذاره:
    # pending.pop(item_id, None)

    msg = (
        f"✅ انتخاب شد: {height}p برای آیتم #{item_id}.\n"
        f"حالا دوباره /publish_now بزن تا با همین کیفیت دانلود شود."
    )

    try:
        await q.edit_message_text(msg)
    except BadRequest as e:
        # رایج: Message is not modified
        if "Message is not modified" in str(e) or "Query is too old" in str(e):
            return
        raise
