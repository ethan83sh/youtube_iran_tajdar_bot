from telegram.ext import Application, CallbackQueryHandler, CommandHandler
from bot import menus
from bot.config import BOT_TOKEN
from shared import db as dbmod
from bot.conversations.common import admin_only, go_main


def build_app(db_path: str):
    app = Application.builder().token(BOT_TOKEN).build()

    con = dbmod.connect(db_path)
    dbmod.migrate(con)
    app.bot_data["db"] = con

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

    async def on_click(update, context):
        if not await admin_only(update, context):
            return

        q = update.callback_query
        await q.answer()
        data = q.data

        if data in (menus.CB_CANCEL, menus.CB_BACK):
            await go_main(update, context)
            return

        if data == menus.CB_ADD_LINK:
            await q.edit_message_text(
                "مرحله «اضافه کردن با لینک» در گام بعد فعال می‌شود.",
                reply_markup=menus.back_main_kb(),
            )
            return

        if data == menus.CB_ADD_VIDEO:
            await q.edit_message_text(
                "مرحله «اضافه کردن ویدیو» در گام بعد فعال می‌شود.",
                reply_markup=menus.back_main_kb(),
            )
            return

        if data == menus.CB_QUEUE:
            await q.edit_message_text(
                "مرحله «صف انتشار» در گام بعد فعال می‌شود.",
                reply_markup=menus.back_main_kb(),
            )
            return

        if data == menus.CB_TIME:
            await q.edit_message_text(
                "مرحله «زمان انتشار» در گام بعد فعال می‌شود.",
                reply_markup=menus.back_main_kb(),
            )
            return

        await go_main(update, context)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CallbackQueryHandler(on_click))

    return app
