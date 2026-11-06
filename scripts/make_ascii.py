#!/usr/bin/env python3
"""Đổi một ảnh thành ASCII art CÓ MÀU cho card (assets/avatar.json).

Chạy tay mỗi khi đổi avatar:
    pip install pillow
    python scripts/make_ascii.py path/to/avatar.jpg            # mặc định 49x22
    python scripts/make_ascii.py avatar.jpg --cols 49 --rows 22

Mỗi ô lưu [ký tự, màu hex]. build_card.py đọc file này; không cần Pillow lúc build.
"""
from __future__ import annotations

import argparse
import json
import pathlib

from PIL import Image, ImageEnhance, ImageOps

# từ thưa tới dày — chỗ sáng dùng ký tự dày (nền card tối)
RAMP = "  .,:;i1tfLCG08@"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--cols", type=int, default=49)
    ap.add_argument("--rows", type=int, default=22)
    ap.add_argument("--out", default=str(ROOT / "assets" / "avatar.json"))
    a = ap.parse_args()

    img = Image.open(a.image).convert("RGB")
    img = ImageOps.fit(img, (img.width, int(img.width * a.rows / a.cols * 2.24)))
    img = ImageEnhance.Contrast(img).enhance(1.35)
    img = ImageEnhance.Color(img).enhance(1.25)
    img = img.resize((a.cols, a.rows), Image.LANCZOS)
    gray = ImageOps.autocontrast(img.convert("L"), cutoff=2)

    rows = []
    for y in range(a.rows):
        row = []
        for x in range(a.cols):
            lum = gray.getpixel((x, y)) / 255
            ch = RAMP[min(int(lum * len(RAMP)), len(RAMP) - 1)]
            r, g, b = img.getpixel((x, y))
            # lượng tử hoá nhẹ để gộp được nhiều ký tự liền nhau cùng màu
            r, g, b = (min(255, (v // 12) * 12 + 6) for v in (r, g, b))
            row.append([ch, f"#{r:02x}{g:02x}{b:02x}"])
        rows.append(row)
    pathlib.Path(a.out).write_text(json.dumps(rows, separators=(",", ":")) + "\n")
    print(f"wrote {a.out} ({a.cols}x{a.rows})")


if __name__ == "__main__":
    main()
