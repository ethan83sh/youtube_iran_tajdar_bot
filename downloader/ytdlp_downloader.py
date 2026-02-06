import time
import yt_dlp

def _fmt_bytes(n):
    if not n:
        return "?"
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"

def download_youtube_temp(url, name, *, progress_cb=None):
    last = {"t": 0}

    def hook(d):
        if progress_cb is None:
            return
        if d.get("status") != "downloading":
            return

        now = time.time()
        if now - last["t"] < 7:   # هر ۷ ثانیه یک آپدیت
            return
        last["t"] = now

        downloaded = d.get("downloaded_bytes") or 0
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        speed = d.get("speed")
        eta = d.get("eta")

        percent = None
        if total:
            percent = downloaded / total * 100

        progress_cb({
            "downloaded": downloaded,
            "total": total,
            "percent": percent,
            "speed": speed,
            "eta": eta,
        })

    ydl_opts = {
        "progress_hooks": [hook],
        # سایر آپشن‌های خودت...
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # ...
        return info, file_path, tmpdir
