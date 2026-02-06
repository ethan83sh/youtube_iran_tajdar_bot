from datetime import datetime
from zoneinfo import ZoneInfo

from telegram.error import BadRequest

from bot.config import ADMIN_GROUP_ID
from shared import db as dbmod

TZ_IR = ZoneInfo("Asia/Tehran")


def _now_str_ir() -> str:
    return datetime.now(TZ_IR).strftime("%Y-%m-%d %H:%M")


def _today_ir() -> str:
    return datetime.now(TZ_IR).strftime("%Y-%m-%d")


async def _safe_send(context, text: str):
    try:
        await context.bot.send_message(ADMIN_GROUP_ID, text)
    except BadRequest:
        # اگر مثلاً پیام تکراری/یا محدودیت خاصی رخ داد، فعلاً کرش نکنیم
        return


async def daily_publisher(context):
    """
    مرحله 2:
    - گزارش اجرای job در تلگرام (برای دیباگ)
    - جلوگیری از دوباره‌اجرا شدن در همان روز ایران
    - انتخاب آیتم امروز، mark_ready، و گزارش جزئیات آیتم در تلگرام
    """
    con = context.application.bot_data["db"]

    now_str = _now_str_ir()
    today = _today_ir()

    # 0) گزارش شروع اجرا
    await _safe_send(context, f"⏰ daily_publisher اجرا شد — {now_str} (Asia/Tehran)")

    # 1) جلوگیری از اجرای دوباره در همان روز
    last = dbmod.get_last_publish_day(con)
    if last == today:
        await _safe_send(context, f"ℹ️ امروز قبلاً انجام شده بود (last_publish_day={last}).")
        return

    # 2) انتخاب آیتم
    item_id = dbmod.pick_next_for_today(con)
    if not item_id:
        dbmod.set_last_publish_day(con, today)
        await _safe_send(context, f"📭 صف خالی بود؛ امروز را انجام‌شده ثبت کردم. ({today})")
        return

    # 3) گرفتن جزئیات آیتم (برای گزارش دقیق)
    it = None
    try:
        it = dbmod.get_queue_item(con, item_id)
    except Exception:
        it = None

    title = ""
    url = ""
    if isinstance(it, dict):
        title = (it.get("title") or "").strip()
        url = (it.get("source_url") or "").strip()

    # 4) آماده‌سازی (فعلاً انتشار واقعی نداریم)
    dbmod.mark_ready(con, item_id)
    dbmod.set_last_publish_day(con, today)

    # 5) گزارش نتیجه (فعلاً "ready شد"؛ وقتی انتشار واقعی اضافه شد متن را می‌کنیم "منتشر شد")
    msg = f"✅ آیتم امروز آماده شد: #{item_id} — {now_str}"
    if title:
        msg += f"\n📌 {title}"
    if url:
        msg += f"\n🔗 {url}"

    await _safe_send(context, msg)
