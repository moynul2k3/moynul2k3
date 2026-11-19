#!/usr/bin/env python3
"""
Generate terminal-style neofetch GitHub profile cards (dark + light).
Outputs: assets/dark_mode.svg, assets/light_mode.svg
"""
import utils.session
import base64
import os
import shutil
import subprocess
import sys
from html import escape

import requests
from PIL import Image, ImageEnhance, ImageOps

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
USER = os.environ.get("GH_USER", "moynul2k3")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not TOKEN:
    try:
        if shutil.which("gh"):
            TOKEN = subprocess.check_output(
                ["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL
            ).strip()
    except Exception:
        pass

PHOTO = os.environ.get("PHOTO", "assets/photo.jpg")
OUTDIR = "assets"

NAME = "Md. Moynul Islam"
COMPANY = "Quanta Plus Plus"
HANDLE = "moynul@quanta-plus-plus"

THEMES = {
    "dark": {
        "bg": "#0f141c",
        "border": "#1e293b",
        "ascii": "#94a3b8",
        "user": "#58a6ff",
        "dashes": "#334155",
        "dot_prefix": "#64748b",
        "key": "#f59e0b",
        "dots": "#334155",
        "val": "#e2e8f0",
        "stats_val": "#38bdf8",
        "pipe": "#475569",
        "sec_title": "#cbd5e1",
    },
    "light": {
        "bg": "#f8fafc",
        "border": "#e2e8f0",
        "ascii": "#475569",
        "user": "#0969da",
        "dashes": "#cbd5e1",
        "dot_prefix": "#94a3b8",
        "key": "#d97706",
        "dots": "#cbd5e1",
        "val": "#0f172a",
        "stats_val": "#0284c7",
        "pipe": "#94a3b8",
        "sec_title": "#334155",
    },
}

# ----------------------------------------------------------------------------
# GitHub Stats Fetcher
# ----------------------------------------------------------------------------
def _headers():
    h = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def fetch_stats():
    s = {"repos": "56", "stars": "1", "followers": "5", "commits": "536"}
    try:
        u = requests.get(
            f"https://api.github.com/users/{USER}",
            headers=_headers(),
            timeout=15,
        ).json()
        if "public_repos" in u:
            s["repos"] = str(u["public_repos"])
        if "followers" in u:
            s["followers"] = str(u["followers"])

        stars, page = 0, 1
        while True:
            r = requests.get(
                f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}",
                headers=_headers(),
                timeout=15,
            ).json()
            if not r or not isinstance(r, list):
                break
            stars += sum(x.get("stargazers_count", 0) for x in r)
            page += 1
        s["stars"] = str(stars)
    except Exception as e:
        print(f"[warn] REST stats failed: {e}", file=sys.stderr)

    if TOKEN:
        try:
            q = (
                "query($l:String!){user(login:$l){contributionsCollection"
                "{totalCommitContributions}}}"
            )
            r = requests.post(
                "https://api.github.com/graphql",
                json={"query": q, "variables": {"l": USER}},
                headers=_headers(),
                timeout=15,
            ).json()
            commits = r.get("data", {}).get("user", {}).get("contributionsCollection", {}).get("totalCommitContributions")
            if commits is not None:
                s["commits"] = f"{commits:,}"
        except Exception as e:
            print(f"[warn] GraphQL stats failed: {e}", file=sys.stderr)

    return s


# ----------------------------------------------------------------------------
# ASCII Portrait Generator
# ----------------------------------------------------------------------------
def generate_ascii(cols=46, rows=32):
    if not os.path.exists(PHOTO):
        return []
    img = Image.open(PHOTO).convert("L")
    enh = ImageEnhance.Contrast(img).enhance(1.45)
    inv = ImageOps.invert(enh)
    resized = inv.resize((cols, rows), Image.Resampling.LANCZOS)
    px = list(resized.tobytes())

    ramp = " .:-=+*#%@"
    out = []
    for y in range(rows):
        row = px[y * cols : (y + 1) * cols]
        line = "".join(ramp[v * (len(ramp) - 1) // 255] if v > 28 else " " for v in row)
        out.append(line.rstrip())
    return out


# ----------------------------------------------------------------------------
# SVG Builder
# ----------------------------------------------------------------------------
def build_card(theme_name, stats):
    t = THEMES[theme_name]
    ascii_lines = generate_ascii(cols=46, rows=32)

    CARD_W = 960
    CARD_H = 512
    PAD_X = 26
    PAD_Y = 26
    LINE_H = 19
    FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

    ASCII_CW = 5.75
    ASCII_LH = 14.2
    ASCII_FS = 10
    ascii_w = 46 * ASCII_CW + 18

    RIGHT_X = PAD_X + ascii_w + 14
    TOTAL_CHARS = 78
    VAL_COL = 30

    items = [
        ("header", HANDLE),
        ("kv", "OS", "Linux (Ubuntu), Windows"),
        ("kv", "Host", COMPANY),
        ("kv", "Kernel", "Full-Stack Web Developer"),
        ("kv", "Uptime", "4+ years active development"),
        ("kv", "IDE", "VS Code, PyCharm"),
        ("blank",),
        ("kv", "Languages.Programming", "TypeScript, Python, JavaScript"),
        ("kv", "Languages.Frameworks", "Next.js, Django, FastAPI, React"),
        ("kv", "Languages.Real", "Bengali (Native), English (Fluent)"),
        ("blank",),
        ("kv", "Stack.Databases", "PostgreSQL, SQLite, Redis"),
        ("kv", "Stack.DevOps", "Docker, Nginx, Linux, VPS"),
        ("blank",),
        ("section", "Contact"),
        ("kv", "Email.Personal", "moynul2k3@gmail.com"),
        ("kv", "Email.Work", "quantaplusplus@gmail.com"),
        ("kv", "Website", "moynul.com"),
        ("kv", "LinkedIn", "linkedin.com/in/moynul2k3"),
        ("kv", "GitHub", "github.com/moynul2k3"),
        ("blank",),
        ("section", "GitHub Stats"),
        ("stats2", ("Repos", stats["repos"]), ("Stars", stats["stars"])),
        ("stats2", ("Commits (1y)", stats["commits"]), ("Followers", stats["followers"])),
    ]

    ascii_svg = []
    ascii_start_y = PAD_Y + 14
    for i, line in enumerate(ascii_lines):
        y = ascii_start_y + i * ASCII_LH
        if line.strip():
            ascii_svg.append(
                f'<text class="ascii r" x="{PAD_X}" y="{y:.1f}" xml:space="preserve" '
                f'style="animation-delay:{0.05 + i * 0.015:.2f}s">{escape(line)}</text>'
            )

    right_svg = []
    cur_y = PAD_Y + 14
    anim_idx = 0

    for item in items:
        anim_delay = f"{0.12 + anim_idx * 0.02:.2f}s"
        anim_idx += 1

        if item[0] == "header":
            user_text = item[1]
            dashes_count = max(4, TOTAL_CHARS - len(user_text) - 1)
            dashes = "-" * dashes_count
            right_svg.append(
                f'<text class="r text" x="{RIGHT_X}" y="{cur_y}" xml:space="preserve" style="animation-delay:{anim_delay}">'
                f'<tspan fill="{t["user"]}" font-weight="600">{escape(user_text)}</tspan> '
                f'<tspan fill="{t["dashes"]}">{dashes}</tspan></text>'
            )
        elif item[0] == "section":
            sec_text = f"- {item[1]} "
            dashes_count = max(4, TOTAL_CHARS - len(sec_text))
            dashes = "-" * dashes_count
            right_svg.append(
                f'<text class="r text" x="{RIGHT_X}" y="{cur_y}" xml:space="preserve" style="animation-delay:{anim_delay}">'
                f'<tspan fill="{t["sec_title"]}" font-weight="600">{escape(sec_text)}</tspan>'
                f'<tspan fill="{t["dashes"]}">{dashes}</tspan></text>'
            )
        elif item[0] == "kv":
            k, v = item[1], item[2]
            k_part = f". {k}: "
            dots_count = max(2, VAL_COL - len(k_part))
            dots = "." * dots_count
            right_svg.append(
                f'<text class="r text" x="{RIGHT_X}" y="{cur_y}" xml:space="preserve" style="animation-delay:{anim_delay}">'
                f'<tspan fill="{t["dot_prefix"]}">. </tspan>'
                f'<tspan fill="{t["key"]}">{escape(k)}: </tspan>'
                f'<tspan fill="{t["dots"]}">{dots} </tspan>'
                f'<tspan fill="{t["val"]}">{escape(v)}</tspan></text>'
            )
        elif item[0] == "stats2":
            (k1, v1), (k2, v2) = item[1], item[2]
            COL1_W = 26
            k1_part = f". {k1}: "
            dots1_count = max(2, COL1_W - len(k1_part) - len(v1) - 2)
            dots1 = "." * dots1_count

            COL2_W = 21
            k2_part = f"{k2}: "
            dots2_count = max(2, COL2_W - len(k2_part) - len(v2) - 1)
            dots2 = "." * dots2_count

            right_svg.append(
                f'<text class="r text" x="{RIGHT_X}" y="{cur_y}" xml:space="preserve" style="animation-delay:{anim_delay}">'
                f'<tspan fill="{t["dot_prefix"]}">. </tspan>'
                f'<tspan fill="{t["key"]}">{escape(k1)}: </tspan>'
                f'<tspan fill="{t["dots"]}">{dots1} </tspan>'
                f'<tspan fill="{t["stats_val"]}" font-weight="600">{escape(v1)} </tspan>'
                f'<tspan fill="{t["pipe"]}">| </tspan>'
                f'<tspan fill="{t["key"]}">{escape(k2)}: </tspan>'
                f'<tspan fill="{t["dots"]}">{dots2} </tspan>'
                f'<tspan fill="{t["stats_val"]}" font-weight="600">{escape(v2)}</tspan></text>'
            )
        elif item[0] == "blank":
            pass

        cur_y += LINE_H

    css = f"""
.text {{ font: 12.5px {FONT}; }}
.ascii {{ font: {ASCII_FS}px {FONT}; fill: {t["ascii"]}; }}
.r {{ opacity: 0; animation: fadeIn 0.35s ease-out forwards; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(3px); }} to {{ opacity: 1; transform: translateY(0); }} }}
"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}" role="img" aria-label="{escape(NAME)} - GitHub profile card">
<title>{escape(NAME)} - GitHub profile card</title>
<defs>
  <style>{css}</style>
  <clipPath id="cardClip">
    <rect x="0" y="0" width="{CARD_W}" height="{CARD_H}" rx="14" />
  </clipPath>
</defs>

<rect x="0" y="0" width="{CARD_W}" height="{CARD_H}" rx="14" fill="{t['bg']}" stroke="{t['border']}" stroke-width="1.5" />

<g clip-path="url(#cardClip)">
{chr(10).join(ascii_svg)}
{chr(10).join(right_svg)}
</g>
</svg>
"""


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    stats = fetch_stats()
    for theme in THEMES:
        path = os.path.join(OUTDIR, f"{theme}_mode.svg")
        content = build_card(theme, stats)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
