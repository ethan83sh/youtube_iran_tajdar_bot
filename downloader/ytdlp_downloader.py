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


def probe_youtube_formats(url: str) -> dict:
    """
    فقط متادیتا/فرمت‌ها را می‌گیرد (بدون دانلود).
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def _extract_final_filepath(info: dict) -> str | None:
    """
    تلاش می‌کند مسیر فایل نهایی بعد از دانلود/مرج را از info دربیارد.
    """
    if not isinstance(info, dict):
        return None

    # yt-dlp معمولاً این را دارد
    fp = info.get("filepath")
    if fp:
        return fp

    # خیلی وقت‌ها _filename مسیر خروجی نهایی است
    fp = info.get("_filename")
    if fp:
        return fp

    # بعضی وقت‌ها در requested_downloads می‌آید
    reqs = info.get("requested_downloads")
    if isinstance(reqs, list) and reqs:
        for r in reversed(reqs):
            if isinstance(r, dict) and r.get("filepath"):
                return r["filepath"]
            if isinstance(r, dict) and r.get("_filename"):
                return r["_filename"]

    return None


def download_youtube_temp(
    url: str,
    name: str,
    *,
    progress_cb=None,
    format_selector: str | None = None,
    merge_container: str = "mkv",   # پیش‌فرض پایدارتر از mp4 برای مرج [web:1016]
    debug: bool = False,
):
    """
    خروجی: (info, file_path, tmpdir)

    progress_cb: تابع sync که dict پیشرفت را می‌گیرد.
    format_selector: مثل 'bv*[height<=1080]+ba/b[height<=1080]' و ...
    merge_container: 'mkv' یا 'mp4'
    debug: اگر True باشد لاگ کامل yt-dlp/ffmpeg را می‌دهد.
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
        if status == "downloading" and (now - last["t"] < 7):
            return
        last["t"] = now

        downloaded = d.get("downloaded_bytes") or 0
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        speed = d.get("speed")
        eta = d.get("eta")

        percent = (downloaded / total * 100) if total else None

        info_dict = d.get("info_dict") or {}
        progress_cb(
            {
                "status": status,
                "downloaded": downloaded,
                "total": total,
                "percent": percent,
                "speed": speed,
                "eta": eta,
                "filename": info_dict.get("_filename"),
            }
        )

    ydl_opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "progress_hooks": [hook],

        # اگر debug روشن شد، خروجی کامل می‌گیری (برای دیدن خطای دقیق ffmpeg) [web:1004]
        "quiet": (not debug),
        "no_warnings": (not debug),
        "verbose": bool(debug),

        # مرج/ریمکس:
        # mkv برای مرج پایدارتره و faststart mp4 را دور می‌زند [web:1016]
        "merge_output_format": merge_container,
    }

    if format_selector:
        ydl_opts["format"] = format_selector

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            file_path = _extract_final_filepath(info)
            if not file_path:
                # fallback: prepare_filename (گاهی دقیق نیست، ولی بهتر از هیچ) [web:646]
                file_path = ydl.prepare_filename(info)

            return info, file_path, tmpdir

    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
