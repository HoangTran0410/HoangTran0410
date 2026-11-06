#!/usr/bin/env python3
"""Vẽ thẻ kiểu `neofetch` cho README (assets/card-dark.svg + card-light.svg).

Chạy trong GitHub Action mỗi ngày với GITHUB_TOKEN để cập nhật số liệu.
Không có mạng / không có token thì dùng số trong assets/stats.json (cache lần trước),
nên chạy tay ở máy nào cũng ra được ảnh.

Avatar ASCII màu nằm ở assets/avatar.json — tạo bằng scripts/make_ascii.py.
Chỉ dùng thư viện chuẩn.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

USER = "HoangTran0410"
ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CACHE = ASSETS / "stats.json"
LOC_CACHE = ASSETS / "loc.json"
AVATAR = ASSETS / "avatar.json"
CODING_SINCE = 2018

# ── Nội dung tĩnh: sửa ở đây ────────────────────────────────────────────────
INFO = [
    ("title", "hoang@github"),
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
    ("loc", None),
]

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", fg="#c9d1d9", key="#ffa657",
                 val="#a5d6ff", dim="#6e7681", acc="#d2a8ff", ok="#3fb950",
                 add="#3fb950", rm="#f85149", art_dim=1.0),
    "light": dict(bg="#ffffff", border="#d0d7de", fg="#24292f", key="#953800",
                  val="#0a3069", dim="#8c959f", acc="#8250df", ok="#1a7f37",
                  add="#1a7f37", rm="#cf222e", art_dim=1.0, frame="#0d1117"),
}


# ── GitHub API ─────────────────────────────────────────────────────────────
def _req(method: str, url: str, body: dict | None = None):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-card-builder")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return r.status, (json.loads(raw) if raw else None)


def gh(path: str):
    return _req("GET", f"https://api.github.com{path}")[1]


def graphql(query: str, **variables):
    _, res = _req("POST", "https://api.github.com/graphql",
                  {"query": query, "variables": variables})
    if res.get("errors"):
        raise RuntimeError(res["errors"])
    return res["data"]


def own_repos() -> list[dict]:
    repos, page = [], 1
    while True:
        batch = gh(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    return repos


def contributed_repos() -> tuple[list[str], int]:
    """Repo của người khác/tổ chức mà mình đã đóng góp (GitHub chỉ nhớ ~1 năm gần nhất)."""
    q = """query($login:String!,$after:String){user(login:$login){
      repositoriesContributedTo(first:100,after:$after,includeUserRepositories:false,
        contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){
        totalCount pageInfo{hasNextPage endCursor} nodes{nameWithOwner}}}}"""
    names, after, total = [], None, 0
    while True:
        d = graphql(q, login=USER, after=after)["user"]["repositoriesContributedTo"]
        total = d["totalCount"]
        names += [n["nameWithOwner"] for n in d["nodes"]]
        if not d["pageInfo"]["hasNextPage"]:
            break
        after = d["pageInfo"]["endCursor"]
    return names, total


def loc_for(repos: list[str], cache: dict) -> dict:
    """Cộng additions/deletions/commits của USER trên từng repo.

    /stats/contributors trả 202 khi GitHub còn đang tính — gọi vòng lại vài lượt,
    repo nào vẫn chưa xong thì giữ số cũ trong cache thay vì tính là 0.
    """
    pending = list(repos)
    for attempt in range(5):
        still = []
        for name in pending:
            try:
                status, data = _req("GET", f"https://api.github.com/repos/{name}/stats/contributors")
            except urllib.error.HTTPError as e:
                print(f"  {name}: HTTP {e.code}")
                continue
            if status == 202 or not isinstance(data, list):
                still.append(name)
                continue
            me = next((c for c in data if c.get("author") and
                       c["author"]["login"].lower() == USER.lower()), None)
            if me:
                cache[name] = {
                    "add": sum(w["a"] for w in me["weeks"]),
                    "del": sum(w["d"] for w in me["weeks"]),
                    "commits": me["total"],
                }
            else:
                cache.pop(name, None)
        pending = still
        if not pending:
            break
        print(f"  waiting on {len(pending)} repos (pass {attempt + 1})")
        time.sleep(15)
    if pending:
        print(f"  kept cached numbers for {len(pending)} repos")
    return cache


def fetch_stats() -> dict:
    user = gh(f"/users/{USER}")
    repos = own_repos()
    own = [r for r in repos if not r.get("fork")]
    contributed, n_contrib = contributed_repos()

    names = sorted({r["full_name"] for r in own} | set(contributed))
    loc_cache = json.loads(LOC_CACHE.read_text()) if LOC_CACHE.exists() else {}
    loc_cache = loc_for(names, loc_cache)
    LOC_CACHE.write_text(json.dumps(dict(sorted(loc_cache.items())), indent=1) + "\n")

    return {
        "repos": user["public_repos"],
        "contributed": n_contrib,
        "stars": sum(r["stargazers_count"] for r in own),
        "followers": user["followers"],
        "commits": sum(v["commits"] for v in loc_cache.values()),
        "loc_add": sum(v["add"] for v in loc_cache.values()),
        "loc_del": sum(v["del"] for v in loc_cache.values()),
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
    return f"{today.year - CODING_SINCE} years, {today.month - 1} months (since {CODING_SINCE})"


# ── Vẽ ─────────────────────────────────────────────────────────────────────
FS, LH, CW = 14.5, 19.5, 8.7  # cỡ chữ, chiều cao dòng, bề rộng 1 ký tự (ước lượng)
TOP, PAD = 34, 26
INFO_COLS = 60  # mọi dòng bên phải dài đúng ngần này ký tự → giá trị thẳng mép phải


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def t(cls: str, s: str) -> str:
    return f'<tspan class="{cls}">{esc(s)}</tspan>'


def field(k: str, v, width: int) -> str:
    """`Key: ...... value` dài đúng `width` ký tự. v là str hoặc list[(class, text)]."""
    parts = [("val", v)] if isinstance(v, str) else v
    vlen = sum(len(s) for _, s in parts)
    dots = max(width - len(k) - vlen - 3, 1)
    return t("key", k) + t("dim", ": " + "." * dots + " ") + "".join(t(c, s) for c, s in parts)


def kv(k, v):
    return t("dim", ". ") + field(k, v, INFO_COLS - 2)


def pair(a, b):
    left = (INFO_COLS - 5) // 2
    return t("dim", ". ") + field(*a, left) + t("dim", " | ") + field(*b, INFO_COLS - 5 - left)


def info_lines(stats: dict, today: dt.date) -> list[str]:
    out = []
    for kind, val in INFO:
        if kind == "title":
            out.append(t("acc", val) + t("dim", " " + "─" * (INFO_COLS - len(val) - 1)))
        elif kind == "blank":
            out.append("")
        elif kind == "section":
            out.append(t("dim", "- ") + t("acc", val) + t("dim", " " + "─" * (INFO_COLS - len(val) - 3)))
        elif kind == "stats1":
            out.append(pair(("Repos", [("val", f"{stats['repos']}"), ("dim", " {"),
                                       ("key", "Contrib"), ("dim", ": "),
                                       ("val", f"{stats['contributed']}"), ("dim", "}")]),
                            ("Stars", f"{stats['stars']:,}")))
        elif kind == "stats2":
            out.append(pair(("Commits", f"{stats['commits']:,}"),
                            ("Followers", f"{stats['followers']:,}")))
        elif kind == "loc":
            total = stats["loc_add"] - stats["loc_del"]
            out.append(kv("Lines of Code", [
                ("val", f"{total:,}"), ("dim", " ( "),
                ("add", f"{stats['loc_add']:,}++"), ("dim", ", "),
                ("rm", f"{stats['loc_del']:,}--"), ("dim", " )")]))
        else:
            out.append(kv(kind, val.format(uptime=uptime(today))))
    return out


def shade(hex_color: str, k: float) -> str:
    if k == 1.0:
        return hex_color
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(int(v * k) for v in (r, g, b))


def avatar_svg(rows: list, x: float, top: float, k: float) -> str:
    out = []
    for i, row in enumerate(rows):
        spans, cur, buf = [], None, ""
        for ch, color in row:  # gộp ký tự liền nhau cùng màu cho file nhẹ
            color = shade(color, k)
            if color != cur and buf:
                spans.append(f'<tspan fill="{cur}">{esc(buf)}</tspan>')
                buf = ""
            cur = color
            buf += ch
        if buf:
            spans.append(f'<tspan fill="{cur}">{esc(buf)}</tspan>')
        out.append(f'<text x="{x}" y="{top + i * LH:.1f}" class="art" '
                   f'style="animation-delay:{i * 0.04:.2f}s">{"".join(spans)}</text>')
    return "\n".join(out)


def render(theme: str, stats: dict, today: dt.date) -> str:
    c = THEMES[theme]
    rows = json.loads(AVATAR.read_text())
    lines = info_lines(stats, today)
    info_x = PAD + len(rows[0]) * CW + 28
    W = int(info_x + INFO_COLS * CW + PAD)
    H = int(TOP + max(len(lines) + 1, len(rows)) * LH)

    info = [f'<text x="{info_x:.0f}" y="{TOP + i * LH:.1f}" class="ln" '
            f'style="animation-delay:{0.3 + i * 0.06:.2f}s">{ln}</text>' for i, ln in enumerate(lines)]
    cur_y = TOP + len(lines) * LH
    cur_delay = 0.3 + len(lines) * 0.06
    # nền sáng: ASCII ánh sáng (chỗ sáng = ký tự dày) sẽ bị ngược → đặt avatar trong khung tối
    frame = ""
    if c.get("frame"):
        fw, fh = len(rows[0]) * CW + 20, len(rows) * LH + 12
        frame = (f'<rect x="{PAD - 10}" y="{TOP - LH + 2:.1f}" width="{fw:.0f}" height="{fh:.0f}" '
                 f'rx="8" fill="{c['frame']}"/>\n')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Hoang Tran — neofetch-style profile card">
<style>
  text {{ font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', Consolas, 'Liberation Mono', Menlo, monospace; font-size: {FS}px; fill: {c['fg']}; white-space: pre; }}
  .key {{ fill: {c['key']}; }} .val {{ fill: {c['val']}; }} .dim {{ fill: {c['dim']}; }}
  .acc {{ fill: {c['acc']}; font-weight: 700; }} .ok {{ fill: {c['ok']}; }}
  .add {{ fill: {c['add']}; }} .rm {{ fill: {c['rm']}; }}
  .art {{ font-weight: 700; opacity: 0; animation: fade .5s ease-out forwards; }}
  .ln {{ opacity: 0; animation: in .35s ease-out forwards; }}
  .cur {{ fill: {c['ok']}; animation: blink 1s steps(1) infinite; }}
  @keyframes fade {{ to {{ opacity: 1; }} }}
  @keyframes in {{ from {{ opacity: 0; transform: translateX(-6px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  @media (prefers-reduced-motion: reduce) {{ .ln, .art {{ animation: none; opacity: 1; }} .cur {{ animation: none; }} }}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{c['bg']}" stroke="{c['border']}"/>
{frame}{avatar_svg(rows, PAD, TOP, c['art_dim'])}
{chr(10).join(info)}
<text x="{info_x:.0f}" y="{cur_y:.1f}" class="ln" style="animation-delay:{cur_delay:.2f}s"><tspan class="ok">hoang@github</tspan><tspan class="dim">:</tspan><tspan class="val">~</tspan><tspan class="dim">$ </tspan><tspan class="cur">█</tspan><tspan class="dim">   # updated {today.isoformat()}</tspan></text>
</svg>
"""


def main() -> None:
    stats = load_stats()
    today = dt.date.today()
    for theme in THEMES:
        out = ASSETS / f"card-{theme}.svg"
        out.write_text(render(theme, stats, today))
        print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
