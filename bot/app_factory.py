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

    async def on_click(update, context):
        if not await admin_only(update, context):
            return
        q = update.callback_query
        data = q.data

        if data == menus.CB_CANCEL or data == menus.CB_BACK:
            await go_main(update, context)
            return

        if data == menus.CB_ADD_LINK:
            await q.answer()
            await q.edit_message_text("مرحله «اضافه کردن با لینک» در گام بعد فعال می‌شود.", reply_markup=menus.back_main_kb())
            return

        if data == menus.CB_ADD_VIDEO:
            await q.answer()
            await q.edit_message_text("مرحله «اضافه کردن ویدیو» در گام بعد فعال می‌شود.", reply_markup=menus.back_main_kb())
            return

        if data == menus.CB_QUEUE:
            await q.answer()
            await q.edit_message_text("مرحله «صف انتشار» در گام بعد فعال می‌شود.", reply_markup=menus.back_main_kb())
            return

        if data == menus.CB_TIME:
            await q.answer()
            await q.edit_message_text("مرحله «زمان انتشار» در گام بعد فعال می‌شود.", reply_markup=menus.back_main_kb())
            return

        await q.answer()
        await go_main(update, context, "منوی اصلی:")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_click))

    return app
