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
        # پیام تلگرام ممکن است به دلایل مختلف fail شود؛ فعلاً کرش نکن
        return
    except Exception:
        return


async def daily_publisher(context):
    """
    Daily job:
    - Report that job fired (for visibility)
    - Skip if already executed today (Iran date)
    - Pick next item, mark_ready, persist last_publish_day
    - Report chosen item details

    Next step (later):
    - Download from YouTube (temp)
    - Upload to destination YouTube channel
    - Cleanup temp files
    - Mark published / remove from queue
    """
    con = context.application.bot_data["db"]

    now_str = _now_str_ir()
    today = _today_ir()

    await _safe_send(context, f"⏰ daily_publisher اجرا شد — {now_str} (Asia/Tehran)")

    try:
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

        # 3) گرفتن جزئیات آیتم
        it = None
        try:
            it = dbmod.get_queue_item(con, item_id)
        except Exception:
            it = None

        title = ""
        url = ""
        desc = ""
        if isinstance(it, dict):
            title = (it.get("title") or "").strip()
            url = (it.get("source_url") or "").strip()
            desc = (it.get("description") or "").strip()

        # 4) آماده‌سازی (فعلاً انتشار واقعی نداریم)
        dbmod.mark_ready(con, item_id)
        dbmod.set_last_publish_day(con, today)

        # 5) گزارش نتیجه
        msg = f"✅ آیتم امروز ready شد: #{item_id} — {now_str}"
        if title:
            msg += f"\n📌 {title}"
        if url:
            msg += f"\n🔗 {url}"
        if desc:
            msg += f"\n📝 {desc[:300]}"

        await _safe_send(context, msg)

        # ----------------------------
        # مرحله بعد (فعلاً کامنت)
        # ----------------------------
        # from downloader.ytdlp_downloader import download_youtube_temp
        # from uploader.youtube_uploader import upload_video
        # import shutil
        #
        # tmpdir = None
        # file_path = None
        # try:
        #     info, file_path, tmpdir = download_youtube_temp(url, f"item_{item_id}")
        #     await _safe_send(context, f"⬇️ دانلود انجام شد: #{item_id}")
        #
        #     resp = upload_video(
        #         file_path=file_path,
        #         title=title or info.get("title") or f"item {item_id}",
        #         description=desc or "",
        #         privacy_status="public",
        #     )
        #     yt_id = resp.get("id")
        #     await _safe_send(context, f"🎬 آپلود یوتیوب انجام شد: #{item_id} — video_id={yt_id} — {now_str}")
        #
        #     # TODO: dbmod.mark_published(con, item_id) یا dbmod.delete_queue_item(con, item_id)
        # finally:
        #     if tmpdir:
        #         shutil.rmtree(tmpdir, ignore_errors=True)

    except Exception as e:
        await _safe_send(context, f"❌ خطا در daily_publisher — {type(e).__name__}: {e}")
        raise
