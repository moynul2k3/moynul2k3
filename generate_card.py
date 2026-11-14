#!/usr/bin/env python3
"""
Generate animated, terminal-style GitHub profile cards (dark + light).

  python generate_card.py                 # ASCII-art portrait (default)
  MODE=photo python generate_card.py      # round photo avatar with animated ring

Needs:  pip install pillow requests
Input:  assets/photo.jpg  (a clear, front-facing portrait works best)
Output: assets/dark_mode.svg, assets/light_mode.svg
"""
import base64
import io
import os
import sys
from html import escape

import requests
from PIL import Image, ImageEnhance, ImageOps

# ----------------------------------------------------------------------------
# CONFIG - edit this part
# ----------------------------------------------------------------------------
USER = os.environ.get("GH_USER", "moynul2k3")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
PHOTO = os.environ.get("PHOTO", "assets/photo.jpg")
MODE = os.environ.get("MODE", "ascii")  # "ascii" or "photo"
OUTDIR = "assets"

NAME = "Md. Moynul Islam"
HANDLE = f"{USER}@github"

# ("head", title) | ("kv", key, value) | ("gap",)
# {repos} {stars} {followers} {commits} are filled from the GitHub API.
INFO = [
    ("head", "About"),
    ("kv", "Role", "Full-Stack Web Developer"),
    ("kv", "Focus", "Next.js · Django · FastAPI"),
    ("kv", "Strengths", "Scalable APIs, Secure Auth"),
    ("kv", "Website", "moynul.com"),
    ("head", "Stack"),
    ("kv", "Frontend", "TypeScript, React, Next.js"),
    ("kv", "Backend", "Django, DRF, FastAPI, Celery"),
    ("kv", "Database", "PostgreSQL, SQLite, Redis"),
    ("kv", "DevOps", "Docker, Nginx, Linux, Git"),
    ("head", "Contact"),
    ("kv", "Email", "moynul2k3@gmail.com"),
    ("kv", "LinkedIn", "in/moynul2k3"),
    ("head", "GitHub"),
    ("kv", "Repos", "{repos}"),
    ("kv", "Stars", "{stars}"),
    ("kv", "Followers", "{followers}"),
    ("kv", "Commits (1y)", "{commits}"),
]

THEMES = {
    "dark": dict(bg="#0d1117", bar="#161b22", b1="#58a6ff", b2="#bc8cff",
                 text="#c9d1d9", muted="#6e7681", key="#7ee787",
                 accent="#58a6ff", title="#d2a8ff", dots="#484f58",
                 a1="#79c0ff", a2="#d2a8ff"),
    "light": dict(bg="#ffffff", bar="#f6f8fa", b1="#0969da", b2="#8250df",
                  text="#24292f", muted="#6e7781", key="#1a7f37",
                  accent="#0969da", title="#8250df", dots="#afb8c1",
                  a1="#0969da", a2="#8250df"),
}

# ----------------------------------------------------------------------------
# Layout constants
# ----------------------------------------------------------------------------
W = 985
PAD = 30
BAR_H = 38
LEFT_W = 310
RIGHT_X = PAD + LEFT_W + 24
FONT = "'JetBrains Mono','Fira Code',ui-monospace,SFMono-Regular,Menlo,Consolas,'Courier New',monospace"
CW = 7.8            # width of one 13px monospace character
RAMP = " .'`^,:;~-+=*#%@"
ASCII_FS, ASCII_LH, ASCII_CW, CHAR_ASPECT = 9, 10.5, 5.4, 10.5 / 5.4
ASCII_COLS, ASCII_MAX_ROWS = 50, 40


# ----------------------------------------------------------------------------
# GitHub stats
# ----------------------------------------------------------------------------
def _headers():
    h = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def fetch_stats():
    s = {"repos": "-", "stars": "-", "followers": "-", "commits": "-"}
    try:
        u = requests.get(f"https://api.github.com/users/{USER}",
                         headers=_headers(), timeout=15).json()
        s["repos"], s["followers"] = u["public_repos"], u["followers"]
        stars, page = 0, 1
        while True:
            r = requests.get(
                f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}",
                headers=_headers(), timeout=15).json()
            if not r:
                break
            stars += sum(x.get("stargazers_count", 0) for x in r)
            page += 1
        s["stars"] = stars
    except Exception as e:  # noqa: BLE001
        print(f"[warn] REST stats failed: {e}", file=sys.stderr)
    if TOKEN:
        try:
            q = ("query($l:String!){user(login:$l){contributionsCollection"
                 "{totalCommitContributions}}}")
            r = requests.post("https://api.github.com/graphql",
                              json={"query": q, "variables": {"l": USER}},
                              headers=_headers(), timeout=15).json()
            s["commits"] = r["data"]["user"]["contributionsCollection"][
                "totalCommitContributions"]
        except Exception as e:  # noqa: BLE001
            print(f"[warn] GraphQL stats failed: {e}", file=sys.stderr)
    return s


# ----------------------------------------------------------------------------
# Left panel: ASCII portrait or round photo
# ----------------------------------------------------------------------------
def ascii_rows(theme):
    img = Image.open(PHOTO).convert("L")
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Contrast(img).enhance(1.25)
    w, h = img.size
    cols = ASCII_COLS
    rows = round(cols * h / w / CHAR_ASPECT)
    if rows > ASCII_MAX_ROWS:
        rows = ASCII_MAX_ROWS
        cols = round(rows * CHAR_ASPECT * w / h)
    img = img.resize((cols, rows), Image.LANCZOS)
    ramp = RAMP if theme == "dark" else RAMP[::-1]
    px = list(img.tobytes())
    out = []
    for y in range(rows):
        row = px[y * cols:(y + 1) * cols]
        out.append("".join(ramp[v * (len(ramp) - 1) // 255] for v in row).rstrip())
    return out, cols


def left_ascii(theme, top):
    lines, cols = ascii_rows(theme)
    height = len(lines) * ASCII_LH
    x = PAD + (LEFT_W - cols * ASCII_CW) / 2
    svg = [f'<g clip-path="url(#asciiClip)">']
    for i, ln in enumerate(lines):
        y = top + (i + 1) * ASCII_LH
        svg.append(
            f'<text class="a r" x="{x:.1f}" y="{y:.1f}" xml:space="preserve" '
            f'style="animation-delay:{0.2 + i * 0.035:.2f}s">{escape(ln)}</text>')
    svg.append(f'<rect class="scan" x="{PAD}" y="{top}" width="{LEFT_W}" '
               f'height="14" fill="url(#scanG)"/>')
    svg.append("</g>")
    clip = (f'<clipPath id="asciiClip"><rect x="{PAD}" y="{top}" '
            f'width="{LEFT_W}" height="{height:.1f}"/></clipPath>')
    return "\n".join(svg), clip, height


def left_photo(theme, top):
    size = 260
    cx, cy = PAD + LEFT_W / 2, top + size / 2 + 10
    img = Image.open(PHOTO).convert("RGB")
    img = ImageOps.fit(img, (360, 360), Image.LANCZOS, centering=(0.5, 0.35))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=84, optimize=True)
    uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    r = size / 2
    svg = f"""
<g class="r" style="animation-delay:.2s">
  <circle cx="{cx}" cy="{cy}" r="{r + 14}" fill="none" stroke="url(#bord)" stroke-width="1.5" stroke-dasharray="3 9" opacity=".9">
    <animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="26s" repeatCount="indefinite"/>
  </circle>
  <circle cx="{cx}" cy="{cy}" r="{r + 6}" fill="none" stroke="url(#bord)" stroke-width="2.5">
    <animate attributeName="opacity" values=".35;1;.35" dur="4s" repeatCount="indefinite"/>
  </circle>
  <image href="{uri}" x="{cx - r}" y="{cy - r}" width="{size}" height="{size}" clip-path="url(#avatarClip)" preserveAspectRatio="xMidYMid slice"/>
</g>"""
    clip = f'<clipPath id="avatarClip"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
    return svg, clip, size + 40


# ----------------------------------------------------------------------------
# Right panel
# ----------------------------------------------------------------------------
def right_panel(t, stats, y0):
    parts, y, n = [], y0, 0

    def d():
        return f"{1.3 + n * 0.11:.2f}s"

    # typed command
    cmd_user, cmd_rest = f"{HANDLE}:~$ ", "neofetch"
    total = len(cmd_user + cmd_rest)
    steps = ";".join(f"{k * CW:.1f}" for k in range(total + 1))
    parts.append(f'<clipPath id="typ"><rect x="{RIGHT_X}" y="{y - 14}" height="22" width="0">'
                 f'<animate attributeName="width" values="{steps}" dur="1.0s" begin="0.3s" '
                 f'calcMode="discrete" fill="freeze"/></rect></clipPath>')
    parts.append(f'<text class="t" x="{RIGHT_X}" y="{y}" clip-path="url(#typ)">'
                 f'<tspan fill="{t["key"]}">{escape(cmd_user)}</tspan>'
                 f'<tspan fill="{t["accent"]}">{cmd_rest}</tspan></text>')
    parts.append(f'<rect class="cur" x="{RIGHT_X + total * CW + 2:.1f}" y="{y - 11}" '
                 f'width="7" height="14" fill="{t["accent"]}"/>')
    y += 34

    # name + rule
    parts.append(f'<text class="t r" x="{RIGHT_X}" y="{y}" font-size="19" font-weight="700" '
                 f'fill="url(#bord)" style="animation-delay:{d()}">{escape(NAME)}</text>')
    n += 1
    y += 12
    parts.append(f'<line class="draw" x1="{RIGHT_X}" y1="{y}" x2="{W - PAD}" y2="{y}" '
                 f'stroke="url(#bord)" stroke-width="1.5" style="animation-delay:{d()}"/>')
    y += 10

    for item in INFO:
        n += 1
        if item[0] == "head":
            y += 30
            label = f"─ {item[1]} "
            label += "─" * max(2, int((W - PAD - RIGHT_X) / CW) - len(label))
            parts.append(f'<text class="t r" x="{RIGHT_X}" y="{y}" fill="{t["accent"]}" '
                         f'font-weight="700" xml:space="preserve" '
                         f'style="animation-delay:{d()}">{escape(label)}</text>')
        elif item[0] == "kv":
            y += 21
            key = item[1]
            val = item[2].format(**stats)
            kx = RIGHT_X + 4
            vx = RIGHT_X + 150
            lead_x1 = kx + len(key) * CW + 8
            parts.append(
                f'<g class="r" style="animation-delay:{d()}">'
                f'<text class="t" x="{kx}" y="{y}" fill="{t["key"]}" font-weight="600">{escape(key)}</text>'
                f'<line x1="{lead_x1:.1f}" y1="{y - 4}" x2="{vx - 10}" y2="{y - 4}" '
                f'stroke="{t["dots"]}" stroke-width="1.5" stroke-dasharray="1 5" stroke-linecap="round"/>'
                f'<text class="t" x="{vx}" y="{y}" fill="{t["text"]}">{escape(val)}</text></g>')
        else:
            y += 12
    return "\n".join(parts), y - y0 + 10


# ----------------------------------------------------------------------------
# Assemble
# ----------------------------------------------------------------------------
def build(theme, stats):
    t = THEMES[theme]
    content_top = BAR_H + 30
    right_svg, right_h = right_panel(t, stats, content_top + 14)
    if MODE == "photo":
        probe_h = 300
    else:
        probe_h = len(ascii_rows(theme)[0]) * ASCII_LH
    content_h = max(right_h + 20, probe_h)
    H = int(content_top + content_h + 34)
    left_top = content_top + (content_h - probe_h) / 2
    left_svg, left_clip, left_h = (left_photo if MODE == "photo" else left_ascii)(theme, left_top)
    scan_travel = int(left_h)

    css = """
.t{font:13px __FONT__}
.a{font:__AFS__px __FONT__;fill:url(#ag)}
.r{opacity:0;animation:in .55s ease-out forwards}
@keyframes in{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}
.draw{stroke-dasharray:__DW__;stroke-dashoffset:__DW__;animation:dr 1.1s ease-out forwards}
@keyframes dr{to{stroke-dashoffset:0}}
.cur{opacity:0;animation:bl 1.05s steps(1) 1.4s infinite}
@keyframes bl{0%,100%{opacity:1}50%{opacity:0}}
.scan{animation:sc 5s linear 1.6s infinite;opacity:0}
@keyframes sc{0%{transform:translateY(0);opacity:0}8%{opacity:.55}92%{opacity:.55}100%{transform:translateY(__ST__px);opacity:0}}
.dot{animation:pu 3s ease-in-out infinite}
@keyframes pu{0%,100%{opacity:1}50%{opacity:.55}}
""".replace("__FONT__", FONT).replace("__AFS__", str(ASCII_FS)) \
   .replace("__DW__", str(W)).replace("__ST__", str(scan_travel))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(NAME)} - GitHub profile card">
<title>{escape(NAME)} - GitHub profile card</title>
<defs>
<style>{css}</style>
<linearGradient id="bord" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="{t['b1']}"><animate attributeName="stop-color" values="{t['b1']};{t['b2']};{t['b1']}" dur="7s" repeatCount="indefinite"/></stop>
  <stop offset="1" stop-color="{t['b2']}"><animate attributeName="stop-color" values="{t['b2']};{t['b1']};{t['b2']}" dur="7s" repeatCount="indefinite"/></stop>
</linearGradient>
<linearGradient id="ag" gradientUnits="userSpaceOnUse" x1="0" y1="{left_top:.0f}" x2="0" y2="{left_top + left_h:.0f}">
  <stop offset="0" stop-color="{t['a1']}"/><stop offset="1" stop-color="{t['a2']}"/>
</linearGradient>
<linearGradient id="scanG" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{t['a1']}" stop-opacity="0"/>
  <stop offset=".5" stop-color="{t['a1']}" stop-opacity=".9"/>
  <stop offset="1" stop-color="{t['a1']}" stop-opacity="0"/>
</linearGradient>
<radialGradient id="glow1"><stop offset="0" stop-color="{t['b1']}" stop-opacity=".22"/><stop offset="1" stop-color="{t['b1']}" stop-opacity="0"/></radialGradient>
<radialGradient id="glow2"><stop offset="0" stop-color="{t['b2']}" stop-opacity=".2"/><stop offset="1" stop-color="{t['b2']}" stop-opacity="0"/></radialGradient>
<clipPath id="card"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16"/></clipPath>
{left_clip}
</defs>

<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" fill="{t['bg']}"/>
<g clip-path="url(#card)">
  <circle cx="120" cy="120" r="260" fill="url(#glow1)">
    <animate attributeName="cx" values="120;220;120" dur="14s" repeatCount="indefinite"/>
    <animate attributeName="cy" values="120;200;120" dur="14s" repeatCount="indefinite"/>
  </circle>
  <circle cx="{W - 120}" cy="{H - 80}" r="280" fill="url(#glow2)">
    <animate attributeName="cx" values="{W - 120};{W - 260};{W - 120}" dur="16s" repeatCount="indefinite"/>
  </circle>
  <rect x="0" y="0" width="{W}" height="{BAR_H}" fill="{t['bar']}"/>
  <line x1="0" y1="{BAR_H}" x2="{W}" y2="{BAR_H}" stroke="{t['dots']}" stroke-opacity=".5"/>
</g>
<circle class="dot" cx="24" cy="{BAR_H / 2}" r="6" fill="#ff5f56"/>
<circle class="dot" cx="46" cy="{BAR_H / 2}" r="6" fill="#ffbd2e" style="animation-delay:.4s"/>
<circle class="dot" cx="68" cy="{BAR_H / 2}" r="6" fill="#27c93f" style="animation-delay:.8s"/>
<text class="t" x="{W / 2}" y="{BAR_H / 2 + 4.5}" text-anchor="middle" fill="{t['muted']}" font-size="12">{escape(USER)} - zsh - {W}x{H}</text>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" fill="none" stroke="url(#bord)" stroke-width="1.6"/>

{left_svg}
{right_svg}
</svg>
"""


def main():
    if not os.path.exists(PHOTO):
        sys.exit(f"Missing {PHOTO}. Put your portrait there (or set PHOTO=path).")
    os.makedirs(OUTDIR, exist_ok=True)
    stats = fetch_stats()
    for theme in THEMES:
        path = os.path.join(OUTDIR, f"{theme}_mode.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build(theme, stats))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()