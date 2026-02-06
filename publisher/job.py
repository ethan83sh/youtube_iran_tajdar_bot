import asyncio
import shutil
import time
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


def _fmt_bytes(n):
    if not n:
        return "?"
    n = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


async def _safe_send(context, text: str):
    try:
        await context.bot.send_message(ADMIN_GROUP_ID, text)
    except BadRequest:
        return
    except Exception:
        return


async def _safe_edit(context, message_id: int, text: str):
    try:
        await context.bot.edit_message_text(chat_id=ADMIN_GROUP_ID, message_id=message_id, text=text)
    except Exception:
        return


def _row_to_dict(it):
    if it is None:
        return {}
    if isinstance(it, dict):
        return it
    if hasattr(it, "keys"):
        return dict(it)
    return {}


def _pick_url(it: dict) -> str:
    return (it.get("source_url") or it.get("url") or it.get("link") or "").strip()


async def _process_item(context, con, item_id: int, *, set_today_done: bool):
    now_str = _now_str_ir()
    today = _today_ir()

    it = _row_to_dict(dbmod.get_queue_item(con, item_id))
    title = (it.get("title") or "").strip()
    url = _pick_url(it)
    desc = (it.get("description") or "").strip()

    if not url:
        await _safe_send(context, f"❌ آیتم #{item_id} لینک ندارد (source_url/url/link خالی است).")
        if set_today_done:
            dbmod.set_last_publish_day(con, today)
        # اگر آیتم picking شده بود، برگردان به صف
        try:
            dbmod.mark_back_to_queue(con, item_id)
        except Exception:
            pass
        return

    tmpdir = None
    progress_msg_id = None

    try:
        # پیام ثابت برای progress
        msg = await context.bot.send_message(ADMIN_GROUP_ID, f"⬇️ شروع دانلود: #{item_id}\n🔗 {url}")
        progress_msg_id = msg.message_id

        loop = asyncio.get_running_loop()
        last_edit = {"t": 0.0}

        def progress_cb(p: dict):
            """
            این callback داخل thread دانلود اجرا می‌شود، پس باید thread-safe به loop پاس داده شود. [web:642]
            """
            now = time.time()
            if now - last_edit["t"] < 7:
                return
            last_edit["t"] = now

            downloaded = p.get("downloaded") or 0
            total = p.get("total") or 0
            percent = p.get("percent")
            speed = p.get("speed")
            eta = p.get("eta")

            percent_str = f"{percent:.1f}%" if percent is not None else "?"
            total_str = _fmt_bytes(total) if total else "?"

            text = (
                f"⬇️ دانلود: #{item_id}\n"
                f"{percent_str}  ({_fmt_bytes(downloaded)} / {total_str})\n"
                f"⚡️ speed={_fmt_bytes(speed)}/s  ⏳ eta={eta}s"
            )

            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(_safe_edit(context, progress_msg_id, text))
            )

        # دانلود را در thread جدا انجام بده تا event loop تلگرام قفل نشود
        info, file_path, tmpdir = await asyncio.to_thread(
            download_youtube_temp,
            url,
            f"item_{item_id}",
            progress_cb=progress_cb,
        )

        await _safe_send(context, f"✅ دانلود تمام شد: #{item_id}")

        up_title = title or (info.get("title") or f"item {item_id}")
        up_desc = desc

        await _safe_send(context, f"⬆️ شروع آپلود یوتیوب (public): #{item_id}\n📌 {up_title}")
        resp = await asyncio.to_thread(
            upload_video,
            file_path,
            up_title,
            up_desc,
            "public",
        ) if False else upload_video(
            file_path=file_path,
            title=up_title,
            description=up_desc,
            privacy_status="public",
        )
        yt_id = (resp or {}).get("id")

        # موفقیت: حذف از صف + ثبت امروز (فقط در daily)
        try:
            dbmod.delete_queue_item(con, item_id)
        except Exception:
            pass

        if set_today_done:
            dbmod.set_last_publish_day(con, today)

        await _safe_send(context, f"🎬 ✅ آپلود انجام شد: #{item_id}\nvideo_id={yt_id}\n⏱ {now_str}")

    except Exception as e:
        # اگر شکست خورد، آیتم را برگردان به queued تا گیر نکند
        try:
            dbmod.mark_back_to_queue(con, item_id)
        except Exception:
            pass

        await _safe_send(context, f"❌ خطا در پردازش آیتم #{item_id}: {type(e).__name__}: {e}")
        raise

    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
            await _safe_send(context, f"🧹 فایل‌های موقت پاک شد: #{item_id}")


async def daily_publisher(context):
    con = context.application.bot_data["db"]
    now_str = _now_str_ir()
    today = _today_ir()

    await _safe_send(context, f"⏰ daily_publisher اجرا شد — {now_str} (Asia/Tehran)")

    last = dbmod.get_last_publish_day(con)
    if last == today:
        await _safe_send(context, f"ℹ️ امروز قبلاً انجام شده بود (last_publish_day={last}).")
        return

    item_id = dbmod.pick_next_for_today(con)
    if not item_id:
        dbmod.set_last_publish_day(con, today)
        await _safe_send(context, f"📭 صف خالی بود؛ امروز را انجام‌شده ثبت کردم. ({today})")
        return

    await _process_item(context, con, item_id, set_today_done=True)


async def publish_one_item_now(context, item_id: int | None = None):
    """
    اجرای دستی:
    - شرط last_publish_day را نادیده می‌گیرد
    - اگر item_id ندادی، یکی از صف برمی‌دارد
    """
    con = context.application.bot_data["db"]

    if item_id is None:
        item_id = dbmod.pick_next_for_today(con)

    if not item_id:
        await _safe_send(context, "📭 آیتمی برای اجرای دستی پیدا نشد.")
        return

    await _safe_send(context, f"🧪 اجرای دستی publish_one_item_now برای آیتم #{item_id}")
    await _process_item(context, con, item_id, set_today_done=False)
