import re
from urllib.parse import urlparse, parse_qs

ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

def extract_video_id(url: str) -> str | None:
    url = (url or "").strip()

    # اگر کاربر خود ID را داد
    if ID_RE.match(url):
        return url

    try:
        p = urlparse(url)
    except Exception:
        return None

    host = (p.netloc or "").lower()
    path = (p.path or "").strip("/")

    # youtu.be/<id>
    if "youtu.be" in host:
        vid = path.split("/")[0] if path else ""
        return vid if ID_RE.match(vid) else None

    # youtube.com/watch?v=<id>
    if "youtube.com" in host or "m.youtube.com" in host:
        qs = parse_qs(p.query or "")
        v = (qs.get("v") or [""])[0]
        if ID_RE.match(v):
            return v

        # youtube.com/shorts/<id>  یا  /live/<id>  یا /embed/<id>
        parts = path.split("/")
        if len(parts) >= 2 and parts[0] in ("shorts", "live", "embed"):
            vid = parts[1]
            return vid if ID_RE.match(vid) else None

    return None
