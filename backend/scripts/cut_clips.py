"""Cuts one short clip (plus a poster frame) per card-player event out of the full-game
recording named in content/videos.json -> recording. Only the seconds around each event
are decoded, so this takes a few minutes, not hours. Existing clips are skipped; pass
--force to cut them again (e.g. after changing the offset or the windows).

Run from the backend folder:  python -m scripts.cut_clips
Needs ffmpeg: either on PATH or via `pip install imageio-ffmpeg`.
"""

import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from app.content import CLIPS_DIR, ROOT, get_content
from app.events import clip_window_kind


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        exe = shutil.which("ffmpeg")
        if not exe:
            sys.exit("ffmpeg not found: pip install imageio-ffmpeg, or put ffmpeg on PATH")
        return exe


def main():
    force = "--force" in sys.argv
    content = get_content()
    rec = content.recording
    source = ROOT / rec["file"]
    if not source.exists():
        sys.exit(f"Recording not found: {source}")
    ffmpeg = ffmpeg_exe()
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)

    # One clip per event; goal, assist and goal-against moments share the Goal event.
    events = {}
    for card in content.cards.values():
        for m in card["moments"]:
            kind = clip_window_kind(m["kind"])
            before, after = rec['windows'][kind]
            previous = events.get(m['timestamp'], (before, after))
            events[m['timestamp']] = (min(previous[0], before), max(previous[1], after))

    def cut(item):
        ts, window = item
        out, poster = CLIPS_DIR / f"{ts}.mp4", CLIPS_DIR / f"{ts}.jpg"
        if out.exists() and poster.exists() and not force:
            return "skipped"
        at = int(ts) / 1000 - rec["timestamp_offset"]
        before, after = window
        base = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
        subprocess.run(
            base + ["-ss", f"{at + before:.2f}", "-i", str(source), "-t", f"{after - before:.2f}",
                    "-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
                    "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)],
            check=True,
        )
        subprocess.run(
            base + ["-ss", f"{at:.2f}", "-i", str(source), "-frames:v", "1", "-vf", "scale=-2:360", "-q:v", "4", str(poster)],
            check=True,
        )
        return "cut"

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(cut, sorted(events.items())))
    print(f"{results.count('cut')} clips cut, {results.count('skipped')} already there -> {CLIPS_DIR}")


if __name__ == "__main__":
    main()
