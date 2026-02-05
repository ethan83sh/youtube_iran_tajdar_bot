import re
from googleapiclient.discovery import build

_YT_ID_RE = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")

def extract_video_id(url: str) -> str | None:
    m = _YT_ID_RE.search(url)
    return m.group(1) if m else None

def get_video(api_key: str, video_id: str) -> dict | None:
    yt = build("youtube", "v3", developerKey=api_key)
    res = yt.videos().list(
        part="snippet,contentDetails",
        id=video_id
    ).execute()
    items = res.get("items", [])
    return items[0] if items else None

def parse_iso8601_duration_to_seconds(dur: str) -> int:
    # PT#H#M#S ساده
    m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", dur or "")
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h * 3600 + mi * 60 + s
