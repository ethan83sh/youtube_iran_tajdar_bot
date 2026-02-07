import logging
import re
from datetime import time
from zoneinfo import ZoneInfo

from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from bot import menus
from bot.config import BOT_TOKEN, DEFAULT_PUBLISH_TIME_IR, DEFAULT_PRIVACY
from bot.conversations.common import admin_only, go_main
from bot.conversations import add_link, edit_item, reorder_queue
from bot.quality_callbacks import on_pick_quality_callback
from publisher.job import daily_publisher, publish_one_item_now
from shared import db as dbmod

logger = logging.getLogger(__name__)

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _parse_hhmm(hhmm: str) -> tuple[int, int]:
    hh, mm = hhmm.split(":")
    return int(hh), int(mm)


def build_app(db_path: str):
    app = Application.builder().token(BOT_TOKEN).build()

    con = dbmod.connect(db_path)
    dbmod.migrate(con)
    dbmod.init_defaults(con, DEFAULT_PUBLISH_TIME_IR, DEFAULT_PRIVACY)
    app.bot_data["db"] = con

    def ensure_daily_job(_app: Application) -> bool:
        if _app.job_queue is None:
            return False

        for j in _app.job_queue.get_jobs_by_name("daily_publisher"):
            j.schedule_removal()

        con2 = _app.bot_data["db"]
        hhmm = dbmod.get_publish_time_ir(con2)
        h, m = _parse_hhmm(hhmm)

        tz = ZoneInfo("Asia/Tehran")
        _app.job_queue.run_daily(
            daily_publisher,
            time=time(hour=h, minute=m, tzinfo=tz),
            name="daily_publisher",
        )
        return True

    ensure_daily_job(app)

    # Conversations (اولویت بالاتر)
    app.add_handler(add_link.handler(), group=0)
    app.add_handler(edit_item.handler(), group=0)
    app.add_handler(reorder_queue.handler(), group=0)

    async def start(update, context):
        if not await admin_only(update, context):
            return
        await go_main(update, context)

    async def whoami(update, context):
        chat = update.effective_chat
        user = update.effective_user
        if not chat or not user:
            return
        m = await context.bot.get_chat_member(chat.id, user.id)
        await update.effective_message.reply_text(
            f"chat_id={chat.id}\nuser_id={user.id}\nstatus={m.status}"
        )

    async def settime(update, context):
        if not await admin_only(update, context):
            return

        if not context.args or len(context.args) != 1:
            await update.effective_message.reply_text("فرمت درست: /settime HH:MM  (مثلاً /settime 17:00)")
            return

        hhmm = context.args[0].strip()
        if not TIME_RE.match(hhmm):
            await update.effective_message.reply_text("زمان نامعتبر است. نمونه درست: 17:00")
            return

        con2 = context.application.bot_data["db"]
        dbmod.set_publish_time_ir(con2, hhmm)

        ok = ensure_daily_job(context.application)
        if ok:
            await go_main(update, context, f"✅ زمان انتشار ذخیره و اعمال شد: {hhmm} (ایران)")
        else:
            await go_main(update, context, f"✅ زمان انتشار ذخیره شد: {hhmm} (ایران) — JobQueue فعال نیست")

    async def add(update, context):
        if not await admin_only(update, context):
            return
        if not context.args:
            await update.effective_message.reply_text("فرمت درست: /add YOUTUBE_URL")
            return

        url = context.args[0].strip()
        con2 = context.application.bot_data["db"]
        item_id = dbmod.add_queue_item_link(con2, url=url, thumb_mode="yt")
        await go_main(update, context, f"✅ به صف اضافه شد: #{item_id}")

    async def delq(update, context):
        if not await admin_only(update, context):
            return
        if not context.args or len(context.args) != 1 or not context.args[0].isdigit():
            await update.effective_message.reply_text("فرمت درست: /delq ID  (مثلاً /delq 12)")
            return

        item_id = int(context.args[0])
        con2 = context.application.bot_data["db"]
        dbmod.delete_queue_item(con2, item_id)
        await go_main(update, context, f"✅ از صف حذف شد: {item_id}")

    async def testjob(update, context):
        if not await admin_only(update, context):
            return

        if context.application.job_queue is None:
            await update.effective_message.reply_text('JobQueue فعال نیست (PTB را با "python-telegram-bot[job-queue]" نصب کن).')
            return

        chat_id = update.effective_chat.id

        async def _ping(ctx):
            await ctx.bot.send_message(chat_id=chat_id, text="✅ JobQueue OK — این پیام از run_once آمد.")

        context.application.job_queue.run_once(_ping, when=10)
        await update.effective_message.reply_text("⏱ تست شروع شد: 10 ثانیه دیگه پیام میاد…")

    async def daily_in(update, context):
        if not await admin_only(update, context):
            return
        if context.application.job_queue is None:
            await update.effective_message.reply_text("JobQueue فعال نیست.")
            return

        chat_id = update.effective_chat.id
        seconds = 120
        if context.args and context.args[0].isdigit():
            seconds = int(context.args[0])

        async def _run(ctx):
            await ctx.bot.send_message(chat_id=chat_id, text=f"⏱ اجرای تست daily_publisher بعد از {seconds} ثانیه…")
            await daily_publisher(ctx)
            await ctx.bot.send_message(chat_id=chat_id, text="✅ daily_publisher اجرا شد (تست زمان‌بندی).")

        context.application.job_queue.run_once(_run, when=seconds, name="test_daily_once")
        await update.effective_message.reply_text(f"ثبت شد. {seconds} ثانیه دیگه اجرا میشه.")

    async def jobs(update, context):
        if not await admin_only(update, context):
            return
        jq = context.application.job_queue
        if jq is None:
            await update.effective_message.reply_text("JobQueue فعال نیست.")
            return

        daily = jq.get_jobs_by_name("daily_publisher")
        test = jq.get_jobs_by_name("test_daily_once")
        await update.effective_message.reply_text(
            f"daily_publisher jobs: {len(daily)}\n"
            f"test_daily_once jobs: {len(test)}"
        )

    async def publish_now(update, context):
        if not await admin_only(update, context):
            return
        await update.effective_message.reply_text("🚀 شروع تست دانلود/آپلود…")
        await publish_one_item_now(context)
        await update.effective_message.reply_text("✅ تست تمام شد (اگر خطا بود، در پیام‌های گزارش می‌بینی).")

    async def on_click(update, context):
        if not await admin_only(update, context):
            return

        q = update.callback_query
        if not q:
            return

        data = q.data or ""

        try:
            await q.answer()
        except BadRequest as e:
            if "Query is too old" not in str(e):
                raise

        # این نباید اینجا بیاد چون handler خودش جداست
        if data.startswith("qpick:"):
            return

        # FIX: CB_BACK وجود ندارد، باید CB_BACK_MAIN باشد
        if data in (menus.CB_CANCEL, menus.CB_BACK_MAIN):
            await go_main(update, context)
            return

        if data in (menus.CB_QUEUE, menus.CB_QUEUE_REFRESH):
            con2 = context.application.bot_data["db"]
            rows = dbmod.list_queued(con2, limit=30)
            try:
                if not rows:
                    await q.edit_message_text("صف خالی است.", reply_markup=menus.back_main_kb())
                else:
                    await q.edit_message_text("📥 صف انتشار (روی هر آیتم بزن):", reply_markup=menus.queue_list_kb(rows))
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    return
                raise
            return

        # FIX: کلیک روی آیتم‌های لیست صف -> QUEUE_ITEM:<id>
        m = re.match(r"^QUEUE_ITEM:(\d+)$", data)
        if m:
            item_id = int(m.group(1))
            con2 = context.application.bot_data["db"]
            it = dbmod.get_queue_item(con2, item_id)
            if not it:
                await q.edit_message_text("این آیتم پیدا نشد یا از صف حذف شده.", reply_markup=menus.back_main_kb())
                return

            title = ((it["title"] if "title" in it.keys() else "") or "").strip()
            desc = ((it["description"] if "description" in it.keys() else "") or "").strip()
            url = ((it["source_url"] if "source_url" in it.keys() else "") or "").strip()

            text = (
                f"📌 آیتم #{item_id}\n\n"
                f"📌 تیتر:\n{title}\n\n"
                f"📝 دیسکریپشن:\n{desc[:1500]}\n\n"
                f"🔗 لینک:\n{url}"
            )
            await q.edit_message_text(text, reply_markup=menus.queue_item_kb(item_id))
            return

        # FIX: regex ها باید \d+ باشند نه \\d+
        m = re.match(r"^QUEUE_ITEM_VIEW:(\d+)$", data)
        if m:
            item_id = int(m.group(1))
            con2 = context.application.bot_data["db"]
            it = dbmod.get_queue_item(con2, item_id)
            if not it:
                await q.edit_message_text("این آیتم پیدا نشد یا از صف حذف شده.", reply_markup=menus.back_main_kb())
                return

            title = ((it["title"] if "title" in it.keys() else "") or "").strip()
            desc = ((it["description"] if "description" in it.keys() else "") or "").strip()
            url = ((it["source_url"] if "source_url" in it.keys() else "") or "").strip()

            text = (
                f"👁 مشاهده کامل — آیتم #{item_id}\n\n"
                f"📌 تیتر:\n{title}\n\n"
                f"📝 دیسکریپشن:\n{desc[:1500]}\n\n"
                f"🔗 لینک:\n{url}"
            )
            await q.edit_message_text(text, reply_markup=menus.queue_item_kb(item_id))
            return

        m = re.match(r"^QUEUE_ITEM_DEL:(\d+)$", data)
        if m:
            item_id = int(m.group(1))
            con2 = context.application.bot_data["db"]
            dbmod.delete_queue_item(con2, item_id)
            rows = dbmod.list_queued(con2, limit=30)
            if not rows:
                await q.edit_message_text("✅ حذف شد. صف خالی است.", reply_markup=menus.back_main_kb())
            else:
                await q.edit_message_text("✅ حذف شد. صف فعلی:", reply_markup=menus.queue_list_kb(rows))
            return

        if data == menus.CB_TIME:
            await q.edit_message_text("زمان انتشار:", reply_markup=menus.time_menu())
            return

        if data == menus.CB_TIME_VIEW:
            con2 = context.application.bot_data["db"]
            t = dbmod.get_publish_time_ir(con2)
            await q.edit_message_text(f"زمان فعلی انتشار: {t} (به وقت ایران)", reply_markup=menus.time_menu())
            return

        if data == menus.CB_TIME_SET:
            await q.edit_message_text(
                "زمان جدید را با این دستور بفرست:\n/settime HH:MM\nمثلاً: /settime 17:00",
                reply_markup=menus.time_menu(),
            )
            return

        await go_main(update, context)

    async def error_handler(update, context):
        err = context.error
        if isinstance(err, BadRequest):
            msg = str(err)
            if "Query is too old" in msg or "Message is not modified" in msg:
                return
        logger.exception("Unhandled exception while processing update", exc_info=err)

    # Commands
    app.add_handler(CommandHandler("start", start), group=1)
    app.add_handler(CommandHandler("whoami", whoami), group=1)
    app.add_handler(CommandHandler("settime", settime), group=1)
    app.add_handler(CommandHandler("add", add), group=1)
    app.add_handler(CommandHandler("delq", delq), group=1)
    app.add_handler(CommandHandler("testjob", testjob), group=1)
    app.add_handler(CommandHandler("daily_in", daily_in), group=1)
    app.add_handler(CommandHandler("jobs", jobs), group=1)
    app.add_handler(CommandHandler("publish_now", publish_now), group=1)

    # Callback ها
    app.add_handler(CallbackQueryHandler(on_pick_quality_callback, pattern=r"^qpick:"), group=1)  # [web:714]
    app.add_handler(CallbackQueryHandler(on_click), group=1)

    app.add_error_handler(error_handler)

    return app
