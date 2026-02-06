import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram.error import BadRequest

from bot.config import ADMIN_GROUP_ID
from shared import db as dbmod

from downloader.ytdlp_downloader import download_youtube_temp
from uploader.youtube_uploader import upload_video

TZ_IR = ZoneInfo("Asia/Tehran")


def _now_str_ir() -> str:
    return datetime.now(TZ_IR).strftime("%Y-%m-%d %H:%M")


def _today_ir() -> str:
    return datetime.now(TZ_IR).strftime("%Y-%m-%d")


async def _safe_send(context, text: str):
    try:
        await context.bot.send_message(ADMIN_GROUP_ID, text)
    except BadRequest:
        return
    except Exception:
        return


async def daily_publisher(context):
    """
    مرحله 3:
    - اجرا روزانه (یک‌بار در روز ایران)
    - برداشتن آیتم از صف
    - دانلود موقت از یوتیوب
    - آپلود public به یوتیوب مقصد (OAuth token)
    - پاکسازی فایل‌های موقت
    - حذف آیتم از صف (یا بعداً mark_published)
    - گزارش کامل در تلگرام مدیریت
    """
    con = context.application.bot_data["db"]

    now_str = _now_str_ir()
    today = _today_ir()

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

    # 3) جزئیات آیتم
    it = dbmod.get_queue_item(con, item_id) or {}
    title = (it.get("title") or "").strip()
    url = (it.get("source_url") or "").strip()
    desc = (it.get("description") or "").strip()

    if not url:
        dbmod.set_last_publish_day(con, today)
        await _safe_send(context, f"❌ آیتم #{item_id} لینک ندارد (source_url خالی است).")
        return

    tmpdir = None
    file_path = None

    try:
        # 4) دانلود
        await _safe_send(context, f"⬇️ شروع دانلود: #{item_id}\n🔗 {url}")
        info, file_path, tmpdir = download_youtube_temp(url, f"item_{item_id}")
        await _safe_send(context, f"✅ دانلود تمام شد: #{item_id}\n📁 {file_path}")

        # 5) آماده‌سازی متادیتا برای آپلود
        up_title = title or (info.get("title") or f"item {item_id}")
        up_desc = desc

        # 6) آپلود public
        await _safe_send(context, f"⬆️ شروع آپلود یوتیوب (public): #{item_id}\n📌 {up_title}")
        resp = upload_video(
            file_path=file_path,
            title=up_title,
            description=up_desc,
            privacy_status="public",
        )
        yt_id = (resp or {}).get("id")

        # 7) بعد از موفقیت: امروز را انجام‌شده ثبت کن + آیتم را از صف حذف کن
        dbmod.set_last_publish_day(con, today)

        # اگر تابع حذف داری، همین بهترینه
        dbmod.delete_queue_item(con, item_id)

        await _safe_send(
            context,
            f"🎬 ✅ آپلود انجام شد: #{item_id}\nvideo_id={yt_id}\n⏱ {now_str}",
        )

    except Exception as e:
        await _safe_send(context, f"❌ خطا برای آیتم #{item_id} — {type(e).__name__}: {e}")
        raise

    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
            await _safe_send(context, f"🧹 فایل‌های موقت پاک شد: #{item_id}")
