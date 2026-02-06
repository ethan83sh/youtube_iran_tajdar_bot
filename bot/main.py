import os
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import Application

from bot.app_factory import build_app
from bot.config import DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _write_file_if_env_set(env_name: str, path: str) -> bool:
    val = os.environ.get(env_name)
    if not val:
        return Path(path).exists()

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if not p.exists():
        p.write_text(val, encoding="utf-8")

    return p.exists()


def ensure_google_oauth_files():
    client_path = os.environ.get("YT_CLIENT_SECRET_PATH", "/tmp/client_secret.json")
    if _write_file_if_env_set("YT_CLIENT_SECRET_JSON", client_path):
        os.environ["YT_CLIENT_SECRET_PATH"] = client_path

    token_path = os.environ.get("YT_TOKEN_PATH", "/tmp/token.json")
    if _write_file_if_env_set("YT_TOKEN_JSON", token_path):
        os.environ["YT_TOKEN_PATH"] = token_path


def main():
    ensure_google_oauth_files()

    app = build_app(DB_PATH)
    if app is None:
        raise RuntimeError("build_app returned None. Check bot/app_factory.py return app.")

    # لاگ کن مطمئن شیم همین باته
    me = app.bot.get_me()
    logger.info("Bot started: @%s (id=%s)", me.username, me.id)

    # webhook را حتماً پاک کن و بعد polling
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
