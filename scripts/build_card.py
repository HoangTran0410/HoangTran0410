#!/usr/bin/env python3
"""Vẽ thẻ kiểu `neofetch` cho README (assets/card-dark.svg + card-light.svg).

Chạy trong GitHub Action mỗi ngày với GITHUB_TOKEN để cập nhật số liệu.
Không có mạng / không có token thì dùng số trong assets/stats.json (cache lần trước),
nên chạy tay ở máy nào cũng ra được ảnh.

Chỉ dùng thư viện chuẩn.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import pathlib
import urllib.request

USER = "HoangTran0410"
ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "assets" / "stats.json"
CODING_SINCE = 2018

# ── Nội dung tĩnh: sửa ở đây ────────────────────────────────────────────────
ASCII = r"""
        ▄▄████████████▄▄
     ▄██▀▀            ▀▀██▄
   ▄█▀    ██              ▀█▄
  ██    ██████     ●   ●    ██
  █       ██     ●       ●   █
  █              ●   ●       █
  ██      ▄▄▄▄▄▄▄▄▄▄▄▄      ██
   ▀█▄  ▄█▀          ▀█▄  ▄█▀
     ▀███▀              ▀███▀

     ┌─────────────────────┐
     │  PRESS  ▶  START    │
     └─────────────────────┘
""".strip("\n").splitlines()

INFO = [
    ("title", f"hoang@github"),
    ("rule", None),
    ("OS", "Linux · macOS · Android · the Browser"),
    ("Host", "MoMo · Software Engineer"),
    ("Uptime", "{uptime}"),
    ("Kernel", "Game · Frontend · Mobile · Tools"),
    ("IDE", "VS Code + Claude Code"),
    ("blank", None),
    ("Lang.Daily", "TypeScript, Kotlin, JavaScript"),
    ("Lang.Games", "Canvas 2D, p5.js, Phaser, Three.js"),
    ("Lang.Other", "Java, C#, Python, PHP"),
    ("Hobbies", "building engines, killing annoyances"),
    ("blank", None),
    ("section", "Contact"),
    ("Email", "99.hoangtran@gmail.com"),
    ("Web", "hoangtran99.is-a.dev"),
    ("Tools", "fbaio.org"),
    ("blank", None),
    ("section", "GitHub Stats"),
    ("stats1", None),
    ("stats2", None),
]

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", fg="#c9d1d9", key="#ffa657",
                 val="#a5d6ff", dim="#6e7681", acc="#d2a8ff", ok="#7ee787",
                 art="#d2a8ff", art2="#79c0ff"),
    "light": dict(bg="#ffffff", border="#d0d7de", fg="#24292f", key="#953800",
                  val="#0a3069", dim="#8c959f", acc="#8250df", ok="#1a7f37",
                  art="#8250df", art2="#0969da"),
}


# ── Số liệu ────────────────────────────────────────────────────────────────
def gh(path: str):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-card-builder")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def fetch_stats() -> dict:
    user = gh(f"/users/{USER}")
    repos, page = [], 1
    while True:
        batch = gh(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    own = [r for r in repos if not r.get("fork")]
    return {
        "repos": user["public_repos"],
        "own_repos": len(own),
        "stars": sum(r["stargazers_count"] for r in own),
        "forks": sum(r["forks_count"] for r in own),
        "followers": user["followers"],
    }


def load_stats() -> dict:
    try:
        stats = fetch_stats()
        CACHE.write_text(json.dumps(stats, indent=2) + "\n")
        print("stats: live", stats)
        return stats
    except Exception as e:  # noqa: BLE001 — offline thì dùng cache
        stats = json.loads(CACHE.read_text())
        print(f"stats: cache ({e.__class__.__name__}: {e})", stats)
        return stats


def uptime(today: dt.date) -> str:
    years = today.year - CODING_SINCE
    months = today.month - 1
    return f"{years} years, {months} months (since {CODING_SINCE})"


# ── Vẽ ─────────────────────────────────────────────────────────────────────
W, H = 930, 470
FS, LH = 14.5, 19.5
ART_X, INFO_X, TOP = 30, 390, 40
INFO_COLS = 58  # số ký tự của mọi dòng bên phải (để các giá trị thẳng mép phải)


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def kv(key: str, value: str) -> str:
    """`. Key: .......... value` — chấm dẫn để các giá trị thẳng hàng bên phải."""
    dots = INFO_COLS - len(key) - len(value) - 5
    return (f'<tspan class="dim">. </tspan><tspan class="key">{esc(key)}</tspan>'
            f'<tspan class="dim">:{" " + "." * max(dots, 1) + " "}</tspan>'
            f'<tspan class="val">{esc(value)}</tspan>')


def pair(a: tuple[str, str], b: tuple[str, str]) -> str:
    left = (INFO_COLS - 5) // 2
    right = INFO_COLS - 5 - left
    def one(k, v, width):
        dots = width - len(k) - len(v) - 3
        return (f'<tspan class="key">{esc(k)}</tspan>'
                f'<tspan class="dim">:{" " + "." * max(dots, 1) + " "}</tspan>'
                f'<tspan class="val">{esc(v)}</tspan>')
    return (f'<tspan class="dim">. </tspan>{one(*a, left)}'
            f'<tspan class="dim"> | </tspan>{one(*b, right)}')


def render(theme: str, stats: dict, today: dt.date) -> str:
    c = THEMES[theme]
    lines: list[str] = []
    for kind, val in INFO:
        if kind == "title":
            lines.append(f'<tspan class="acc">{esc(val)}</tspan>'
                         f'<tspan class="dim"> ─{"─" * (INFO_COLS - len(val) - 2)}</tspan>')
        elif kind == "rule":
            continue
        elif kind == "blank":
            lines.append("")
        elif kind == "section":
            lines.append(f'<tspan class="dim">- </tspan><tspan class="acc">{esc(val)}</tspan>'
                         f'<tspan class="dim"> {"─" * (INFO_COLS - len(val) - 3)}</tspan>')
        elif kind == "stats1":
            lines.append(pair(("Repos", f"{stats['repos']}"),
                              ("Stars", f"{stats['stars']:,}")))
        elif kind == "stats2":
            lines.append(pair(("Followers", f"{stats['followers']:,}"),
                              ("Forks", f"{stats['forks']:,}")))
        else:
            lines.append(kv(kind, val.format(uptime=uptime(today))))

    info = []
    for i, ln in enumerate(lines):
        y = TOP + i * LH
        info.append(f'<text x="{INFO_X}" y="{y:.1f}" class="ln" '
                    f'style="animation-delay:{0.25 + i * 0.06:.2f}s">{ln}</text>')

    art = []
    art_top = TOP + (len(lines) * LH - len(ASCII) * LH) / 2 - 8
    for i, ln in enumerate(ASCII):
        cls = "art2" if i >= len(ASCII) - 3 else "art"
        art.append(f'<text x="{ART_X}" y="{art_top + i * LH:.1f}" class="{cls}" '
                   f'xml:space="preserve">{esc(ln)}</text>')

    # con trỏ nhấp nháy ở cuối
    cur_y = TOP + len(lines) * LH + 6
    stamp = today.isoformat()

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Hoang Tran — neofetch-style profile card">
<style>
  text {{ font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', Consolas, 'Liberation Mono', Menlo, monospace; font-size: {FS}px; fill: {c['fg']}; white-space: pre; }}
  .key {{ fill: {c['key']}; }} .val {{ fill: {c['val']}; }} .dim {{ fill: {c['dim']}; }}
  .acc {{ fill: {c['acc']}; font-weight: 700; }} .ok {{ fill: {c['ok']}; }}
  .art {{ fill: {c['art']}; }} .art2 {{ fill: {c['art2']}; animation: blink 1.6s steps(1) infinite; }}
  .ln {{ opacity: 0; animation: in .35s ease-out forwards; }}
  .cur {{ fill: {c['ok']}; animation: blink 1s steps(1) infinite; }}
  .foot {{ font-size: 11px; fill: {c['dim']}; }}
  @keyframes in {{ from {{ opacity: 0; transform: translateX(-6px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes blink {{ 70% {{ opacity: 0; }} }}
  @media (prefers-reduced-motion: reduce) {{ .ln {{ animation: none; opacity: 1; }} .cur, .art2 {{ animation: none; }} }}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{c['bg']}" stroke="{c['border']}"/>
{chr(10).join(art)}
{chr(10).join(info)}
<text x="{INFO_X}" y="{cur_y:.1f}"><tspan class="ok">hoang@github</tspan><tspan class="dim">:</tspan><tspan class="val">~</tspan><tspan class="dim">$ </tspan><tspan class="cur">█</tspan></text>
<text x="{W - 20}" y="{H - 14}" text-anchor="end" class="foot">auto-updated {stamp}</text>
</svg>
"""


def main() -> None:
    stats = load_stats()
    today = dt.date.today()
    for theme in THEMES:
        out = ROOT / "assets" / f"card-{theme}.svg"
        out.write_text(render(theme, stats, today))
        print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
