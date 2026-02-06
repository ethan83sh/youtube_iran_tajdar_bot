from datetime import datetime
from zoneinfo import ZoneInfo

from bot.config import ADMIN_GROUP_ID
from shared import db as dbmod

TZ_IR = ZoneInfo("Asia/Tehran")

def _today_ir() -> str:
    return datetime.now(TZ_IR).strftime("%Y-%m-%d")

async def daily_publisher(context):
    con = context.application.bot_data["db"]

    today = _today_ir()
    last = dbmod.get_last_publish_day(con)
    if last == today:
        return  # امروز انجام شده

    item_id = dbmod.pick_next_for_today(con)
    if not item_id:
        dbmod.set_last_publish_day(con, today)  # صف خالی بود هم امروز را انجام‌شده حساب کن
        await context.bot.send_message(ADMIN_GROUP_ID, "📭 امروز صف خالی بود. چیزی برای انتشار نداریم.")
        return

    # فعلاً فقط پیام بده و ببر حالت ready
    dbmod.mark_ready(con, item_id)
    dbmod.set_last_publish_day(con, today)
    await context.bot.send_message(ADMIN_GROUP_ID, f"✅ آیتم امروز انتخاب شد: #{item_id} (مرحله دانلود/آپلود در گام بعد)")
