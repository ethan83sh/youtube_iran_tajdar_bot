from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from bot import menus
from bot.config import BOT_TOKEN
from shared import db as dbmod

def build_app(db_path: str):
    app = Application.builder().token(BOT_TOKEN).build()

    con = dbmod.connect(db_path)
    dbmod.migrate(con)
    app.bot_data["db"] = con

    async def start(update, context):
        await update.effective_message.reply_text("منوی اصلی:", reply_markup=menus.main_menu())

    async def on_menu_click(update, context):
        q = update.callback_query
        await q.answer()
        if q.data == menus.CB_BACK:
            await q.edit_message_text("منوی اصلی:", reply_markup=menus.main_menu())
            return
        await q.edit_message_text("این بخش در مرحله بعد فعال می‌شود.", reply_markup=menus.back_main_kb())

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_menu_click))

    return app
