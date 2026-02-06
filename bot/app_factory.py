import re
from telegram.ext import Application, CallbackQueryHandler, CommandHandler
from bot.conversations import add_link
from bot import menus
from bot.config import BOT_TOKEN, DEFAULT_PUBLISH_TIME_IR, DEFAULT_PRIVACY
from shared import db as dbmod
from bot.conversations.common import admin_only, go_main


TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def build_app(db_path: str):
    app = Application.builder().token(BOT_TOKEN).build()

    con = dbmod.connect(db_path)
    dbmod.migrate(con)
    dbmod.init_defaults(con, DEFAULT_PUBLISH_TIME_IR, DEFAULT_PRIVACY)
    app.bot_data["db"] = con
    app.add_handler(add_link.handler())

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

        con = context.application.bot_data["db"]
        dbmod.set_publish_time_ir(con, hhmm)
        await go_main(update, context, f"✅ زمان انتشار ذخیره شد: {hhmm} (ایران)")

    async def add(update, context):
        if not await admin_only(update, context):
            return
        if not context.args:
            await update.effective_message.reply_text("فرمت درست: /add YOUTUBE_URL")
            return

        url = context.args[0].strip()
        con = context.application.bot_data["db"]
        item_id = dbmod.add_queue_item_link(con, url=url, thumb_mode="yt")
        await go_main(update, context, f"✅ به صف اضافه شد: #{item_id}")

    async def delq(update, context):
        if not await admin_only(update, context):
            return
        if not context.args or len(context.args) != 1 or not context.args[0].isdigit():
            await update.effective_message.reply_text("فرمت درست: /delq ID  (مثلاً /delq 12)")
            return

        item_id = int(context.args[0])
        con = context.application.bot_data["db"]
        dbmod.delete_queue_item(con, item_id)
        await go_main(update, context, f"✅ از صف حذف شد: {item_id}")

    async def on_click(update, context):
        if not await admin_only(update, context):
            return

        q = update.callback_query
        await q.answer()
        data = q.data or ""

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

        # Queue list (button-based)
        if data == menus.CB_QUEUE or data == menus.CB_QUEUE_REFRESH:
            con = context.application.bot_data["db"]
            rows = dbmod.list_queued(con, limit=30)
            if not rows:
                await q.edit_message_text("صف خالی است.", reply_markup=menus.back_main_kb())
                return
            await q.edit_message_text(
                "📥 صف انتشار (روی هر آیتم بزن):",
                reply_markup=menus.queue_list_kb(rows),
            )
            return

        m = re.match(r"^QUEUE_ITEM:(\d+)$", data)
        if m:
            item_id = int(m.group(1))
            await q.edit_message_text(
                f"آیتم انتخاب شد: #{item_id}",
                reply_markup=menus.queue_item_kb(item_id),
            )
            return

        m = re.match(r"^QUEUE_ITEM_DEL:(\d+)$", data)
        if m:
            item_id = int(m.group(1))
            con = context.application.bot_data["db"]
            dbmod.delete_queue_item(con, item_id)

            rows = dbmod.list_queued(con, limit=30)
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
            con = context.application.bot_data["db"]
            t = dbmod.get_publish_time_ir(con)
            await q.edit_message_text(
                f"زمان فعلی انتشار: {t} (به وقت ایران)",
                reply_markup=menus.time_menu(),
            )
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

    return app
