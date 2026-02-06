import os
import yt_dlp


def download_youtube(url: str, out_dir: str, basename: str):
    os.makedirs(out_dir, exist_ok=True)
    outtmpl = os.path.join(out_dir, f"{basename}.%(ext)s")

    # اولویت: mp4 با بهترین کیفیت (ترجیحاً 2160/1080) + ادغام صدا
    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        # اگر merge انجام شده باشد، پسوند ممکن است mp4 شود
        if not path.endswith(".mp4"):
            base, _ = os.path.splitext(path)
            mp4 = base + ".mp4"
            if os.path.exists(mp4):
                path = mp4
        return info, path
