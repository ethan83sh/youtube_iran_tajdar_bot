import os
import shutil
import tempfile
import time
from pathlib import Path

import yt_dlp


def _fmt_bytes(n):
    if not n:
        return "?"
    n = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def download_youtube_temp(url, name, *, progress_cb=None, format_selector: str | None = None):
    """
    خروجی: (info, file_path, tmpdir)
    progress_cb: تابع sync که dict پیشرفت را می‌گیرد (درصد/حجم/ETA/سرعت...)
    """
    tmpdir = tempfile.mkdtemp(prefix="ytdlp_")
    outtmpl = str(Path(tmpdir) / f"{name}.%(ext)s")

    last = {"t": 0.0}

    def hook(d):
        if progress_cb is None:
            return

        status = d.get("status")
        if status not in ("downloading", "finished"):
            return

        now = time.time()
        # هر ۵-۷ ثانیه یک آپدیت (برای اسپم نشدن)
        if status == "downloading" and (now - last["t"] < 7):
            return
        last["t"] = now

        downloaded = d.get("downloaded_bytes") or 0
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        speed = d.get("speed")
        eta = d.get("eta")

        percent = None
        if total:
            percent = downloaded / total * 100

        info_dict = d.get("info_dict") or {}
        progress_cb(
            {
                "status": status,
                "downloaded": downloaded,
                "total": total,
                "percent": percent,
                "speed": speed,
                "eta": eta,
                "filename": info_dict.get("_filename"),  # گاهی اینجا پر می‌شود
            }
        )

    ydl_opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }
    if format_selector:
        ydl_opts["format"] = format_selector  # انتخاب کیفیت با selector [web:610]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # مسیر نهایی فایل دانلودشده
            file_path = info.get("filepath")  # در بعضی موارد yt-dlp این را می‌گذارد [web:646]
            if not file_path:
                file_path = ydl.prepare_filename(info)  # روش رایج برای گرفتن اسم فایل [web:649]

            return info, file_path, tmpdir

    except Exception:
        # اگر شکست خورد، فولدر موقت را پاک کن
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
