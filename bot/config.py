import os

def env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or str(v).strip() == "":
        raise RuntimeError(f"Missing env var: {name}")
    return v

BOT_TOKEN = env("BOT_TOKEN")
ADMIN_GROUP_ID = int(env("ADMIN_GROUP_ID"))
DB_PATH = env("DB_PATH", "/mnt/data/app.db")
DEFAULT_PUBLISH_TIME_IR = env("DEFAULT_PUBLISH_TIME_IR", "17:00")
DEFAULT_PRIVACY = env("DEFAULT_PRIVACY", "public")
