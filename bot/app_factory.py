import re
from datetime import time
from zoneinfo import ZoneInfo

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from bot import menus
from bot.config import BOT_TOKEN, DEFAULT_PUBLISH_TIME_IR, DEFAULT_PRIVACY
from bot.conversations.common import admin_only, go_main
from bot.conversations import add_link, edit_item, reorder_queue
from publisher.job import daily_publisher
from shared import db as dbmod


TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def build_app(db_path: str):
    app = Application.builder().token(BOT_TOKEN).build()

    con = dbmod.connect(db_path)
    dbmod.migrate(con)
    dbmod.init_defaults(con, DEFAULT_PUBLISH_TIME_IR, DEFAULT_PRIVACY)
    app.bot_data["db"] = con

    # Daily publisher 
    app.bot_data["db"] = con


    # Conversations
    app.add_handler(add_link.handler())
    app.add_handler(edit_item.handler())
    app.add_handler(reorder_queue.handler())

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
        await go_main(update, context, f"✅ زمان انتشار ذخیره شد: {hhmm} (ایران)")

    async def add(update, context):
        # اختیاری: افزودن سریع با دستور
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
        # اختیاری: حذف سریع با دستور
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
            await update.effective_message.reply_text("JobQueue فعال نیست (job-queue extra نصب نشده).")
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

    def _parse_hhmm(hhmm: str):
    hh, mm = hhmm.split(":")
    return int(hh), int(mm)

    def ensure_daily_job(app):
        # اگر JobQueue فعال نبود، هیچ کاری نکن
        if app.job_queue is None:
            return False
    
        # هر Job قبلی با همین نام را پاک کن
        for j in app.job_queue.get_jobs_by_name("daily_publisher"):
            j.schedule_removal()
    
        # زمان را از DB بخوان
        con = app.bot_data["db"]
        hhmm = dbmod.get_publish_time_ir(con)  # مثل "17:00"
        h, m = _parse_hhmm(hhmm)
    
        tz = ZoneInfo("Asia/Tehran")
        app.job_queue.run_daily(
            daily_publisher,
            time=time(hour=h, minute=m, tzinfo=tz),
            name="daily_publisher",
        )
        return True


    
    async def on_click(update, context):
        if not await admin_only(update, context):
            return

        q = update.callback_query
        data = q.data or ""

        try:
            await q.answer()
        except Exception:
            pass

        # Cancel / Back
        if data in (menus.CB_CANCEL, menus.CB_BACK):
            await go_main(update, context)
            return

        # Add video (later)
        if data == menus.CB_ADD_VIDEO:
            await q.edit_message_text(
                "مرحله «اضافه کردن ویدیو» در گام بعد فعال می‌شود.",
                reply_markup=menus.back_main_kb(),
            )
            return

        # Queue list
        if data == menus.CB_QUEUE or data == menus.CB_QUEUE_REFRESH:
            con2 = context.application.bot_data["db"]
            rows = dbmod.list_queued(con2, limit=30)
            if not rows:
                await q.edit_message_text("صف خالی است.", reply_markup=menus.back_main_kb())
                return
            await q.edit_message_text("📥 صف انتشار (روی هر آیتم بزن):", reply_markup=menus.queue_list_kb(rows))
            return

        # Full view
        m = re.match(r"^QUEUE_ITEM_VIEW:(\d+)$", data)
        if m:
            item_id = int(m.group(1))
            con2 = context.application.bot_data["db"]
            it = dbmod.get_queue_item(con2, item_id)
            if not it:
                await q.edit_message_text("این آیتم پیدا نشد یا از صف حذف شده.", reply_markup=menus.back_main_kb())
                return

            title = (it["title"] or "").strip()
            desc = (it["description"] or "").strip()
            url = (it["source_url"] or "").strip()

            text = (
                f"👁 مشاهده کامل — آیتم #{item_id}\n\n"
                f"📌 تیتر:\n{title}\n\n"
                f"📝 دیسکریپشن:\n{desc[:1500]}\n\n"
                f"🔗 لینک:\n{url}"
            )
            await q.edit_message_text(text, reply_markup=menus.queue_item_kb(item_id))
            return

        # Select item
        m = re.match(r"^QUEUE_ITEM:(\d+)$", data)
        if m:
            item_id = int(m.group(1))
            await q.edit_message_text(f"آیتم انتخاب شد: #{item_id}", reply_markup=menus.queue_item_kb(item_id))
            return

        # Delete item
        m = re.match(r"^QUEUE_ITEM_DEL:(\d+)$", data)
        if m:
            item_id = int(m.group(1))
            con2 = context.application.bot_data["db"]
            dbmod.delete_queue_item(con2, item_id)

            rows = dbmod.list_queued(con2, limit=30)
            if not rows:
                await q.edit_message_text("✅ حذف شد. صف خالی است.", reply_markup=menus.back_main_kb())
                return
            await q.edit_message_text("✅ حذف شد. صف فعلی:", reply_markup=menus.queue_list_kb(rows))
            return

        # Publish time menu
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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("settime", settime))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("delq", delq))
    app.add_handler(CallbackQueryHandler(on_click))
    app.add_handler(CommandHandler("testjob", testjob))
    app.add_handler(CommandHandler("daily_in", daily_in))
    app.add_handler(CommandHandler("jobs", jobs))

    return app
