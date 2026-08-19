"""Per-post pastel marker CSS. Mirrors the marker generation in src/build.py (frozen),
but with an isolated random.Random(seed) so blog markers can never shift the resume's."""
import random
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
MARKER_TEMPLATE = (SRC / "markers.css").read_text()

COLORS = {
    "c1": "250, 223, 161",
    "c2": "242, 198, 223",
    "c3": "175, 211, 240",
    "c4": "218, 204, 239",
    "c5": "201, 228, 223",
}


def generate_css(marker_colors, seed):
    rnd = random.Random(seed)
    out = ""
    for i, color in enumerate(marker_colors):
        marker = MARKER_TEMPLATE.replace("$$id$$", f"marker{i}")
        marker = marker.replace("$$color$$", color)

        marker = marker.replace("$$a1$$", str(rnd.randint(1, 3) / 10))
        marker = marker.replace("$$a2$$", str(rnd.randint(5, 9) / 10))
        marker = marker.replace("$$a3$$", str(rnd.randint(1, 3) / 10))
        marker = marker.replace("$$a4$$", str(rnd.randint(5, 9) / 10))
        marker = marker.replace("$$a5$$", str(rnd.randint(3, 6) / 10))

        marker = marker.replace("$$p1$$", str(rnd.randint(1, 6)))
        marker = marker.replace("$$p2$$", str(rnd.randint(94, 100)))

        r1 = rnd.randint(2, 9) / 10
        marker = marker.replace("$$r1$$", str(r1))
        marker = marker.replace("$$r2$$", str(1 - r1 + rnd.randint(-1, 1) / 10))

        marker = marker.replace("$$time$$", str(rnd.randint(4, 7) / 10))

        out += marker
    return out
