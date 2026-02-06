import os
import tempfile
from pathlib import Path
import yt_dlp


def download_youtube_temp(url: str, basename: str):
    """
    Downloads a single YouTube URL into a temp dir.
    Returns: (info_dict, mp4_path, tmp_dir)
    """
    tmpdir = tempfile.mkdtemp(prefix="yt_")
    outtmpl = os.path.join(tmpdir, f"{basename}.%(ext)s")

    ydl_opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        # best video+audio, prefer mp4+m4a, then fallback
        "format": "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b",
        "merge_output_format": "mp4",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)

    p = Path(path)
    if p.suffix.lower() != ".mp4":
        mp4 = p.with_suffix(".mp4")
        if mp4.exists():
            p = mp4

    return info, str(p), tmpdir
