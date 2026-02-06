from datetime import datetime
from zoneinfo import ZoneInfo

from bot.config import ADMIN_GROUP_ID
from shared import db as dbmod

TZ_IR = ZoneInfo("Asia/Tehran")


def _now_hhmm_ir() -> str:
    return datetime.now(TZ_IR).strftime("%H:%M")


def _today_ir() -> str:
    return datetime.now(TZ_IR).strftime("%Y-%m-%d")


async def daily_publisher(context):
    """
    Scheduled job entrypoint.
    - Prevents double-run in same Iran day via last_publish_day
    - Picks next item for today
    - Marks it ready
    - Sends a Telegram report to ADMIN_GROUP_ID for visibility
    """
    con = context.application.bot_data["db"]

    now_hhmm = _now_hhmm_ir()
    today = _today_ir()

    # 0) همیشه لاگ/پیام بده بفهمیم job اجرا شده
    await context.bot.send_message(
        ADMIN_GROUP_ID,
        f"⏰ daily_publisher اجرا شد — {today} {now_hhmm} (Asia/Tehran)",
    )

    # 1) اگر امروز قبلاً انجام شده، گزارش بده و خارج شو
    last = dbmod.get_last_publish_day(con)
    if last == today:
        await context.bot.send_message(
            ADMIN_GROUP_ID,
            f"ℹ️ امروز قبلاً اجرا شده بود (last_publish_day={last}).",
        )
        return

    # 2) آیتم امروز را انتخاب کن
    item_id = dbmod.pick_next_for_today(con)
    if not item_id:
        # اگر صف خالی بود هم امروز را انجام‌شده حساب کن (همان منطق قبلی خودت)
        dbmod.set_last_publish_day(con, today)
        await context.bot.send_message(
            ADMIN_GROUP_ID,
            f"📭 امروز صف خالی بود. چیزی برای انتشار نداریم. (ثبت شد: {today})",
        )
        return

    # 3) فعلاً فقط ببر حالت ready و روز را ثبت کن
    dbmod.mark_ready(con, item_id)
    dbmod.set_last_publish_day(con, today)

    await context.bot.send_message(
        ADMIN_GROUP_ID,
        f"✅ آیتم امروز انتخاب شد و ready شد: #{item_id} — ساعت {now_hhmm}",
    )
