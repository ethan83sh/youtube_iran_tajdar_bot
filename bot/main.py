from bot.app_factory import build_app
from bot.config import DB_PATH

def main():
    app = build_app(DB_PATH)
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
