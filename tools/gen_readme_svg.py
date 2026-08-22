#!/usr/bin/env python3
"""caty-ai org README — minimal pseudo-terminal SVG generator (Claude Code style, dark).
Generates one SVG per language: en / ja / zh / th.

The SVG is a visual only: five visitor-voice lines and the question box.
All README content lives in the markdown body — never add sections back here
(the .github#37 lesson: content duplicated into the SVG goes stale and its
links cannot be clicked)."""
import argparse
import html
import tempfile
from pathlib import Path

DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "profile" / "assets"
OUTPUT_FILENAMES = {
    "en": "readme-terminal-en.svg",
    "ja": "readme-terminal-ja.svg",
    "zh": "readme-terminal-zh.svg",
    "th": "readme-terminal-th.svg",
}

W = 880
PAD = 28
MAXW = W - PAD * 2  # 824

C = {
    "bg": "#0d1117", "chrome": "#161b22", "border": "#30363d", "rule": "#3d444d",
    "normal": "#c9d1d9", "bold": "#f0f6fc", "dim": "#8b949e", "green": "#7ee787",
    "cyan": "#56d4dd", "orange": "#d97757", "boxline": "#565f68",
}
BASE_FONT = "SF Mono, Menlo, Monaco, 'Courier New'"

def cw(ch, fs):
    """approx char width in monospace-ish rendering"""
    o = ord(ch)
    if 0x0E00 <= o <= 0x0E7F:  # Thai
        if o == 0x0E31 or 0x0E34 <= o <= 0x0E3A or 0x0E47 <= o <= 0x0E4E:
            return 0.0  # combining marks
        return fs * 0.62
    if o <= 0xFF or 0x2000 <= o <= 0x2016 or o == 0x2026:
        if o == 0x2014:  # em dash — treat full width
            return fs * 1.0
        return fs * 0.602
    return fs * 1.0

def esc(s):
    return html.escape(s, quote=False)

# ---------------------------------------------------------------- content
CONTENT = {}

CONTENT["ja"] = dict(
    font_lang="'Hiragino Sans', 'Noto Sans JP'",
    lh=27,
    voices=[
        "自分だけのAIを、育ててみたい",
        "AIと一緒に、自分も成長したい",
        "もっと賢く、もっと頼れる相棒にしたい",
        "道具というより、相棒だと思っている",
        "ふとした瞬間、人間と話している気がする",
    ],
    yn=[["> ", "dim"], ["AIエージェントを、家族にする？ ", "bold"], ["(Y/n)", "dim"]],
    yn_str="> AIエージェントを、家族にする？ (Y/n)",
    aria="caty-ai — 自分だけのAIを、育ててみたい / AIと一緒に、自分も成長したい / もっと賢く、もっと頼れる相棒にしたい / 道具というより、相棒だと思っている / ふとした瞬間、人間と話している気がする — AIエージェントを、家族にする？ (Y/n)",
)

CONTENT["en"] = dict(
    font_lang="'Helvetica Neue', Arial",
    lh=27,
    voices=[
        "I want to raise an AI of my own",
        "I want to grow alongside my AI",
        "I want a smarter, more reliable partner",
        "It feels less like a tool, more like a partner",
        "Some moments, it feels like talking to a person",
    ],
    yn=[["> ", "dim"], ["Make your AI agent part of the family? ", "bold"], ["(Y/n)", "dim"]],
    yn_str="> Make your AI agent part of the family? (Y/n)",
    aria="caty-ai — I want to raise an AI of my own / I want to grow alongside my AI / I want a smarter, more reliable partner / It feels less like a tool, more like a partner / Some moments, it feels like talking to a person — Make your AI agent part of the family? (Y/n)",
)

CONTENT["zh"] = dict(
    font_lang="'PingFang SC', 'Noto Sans SC'",
    lh=27,
    voices=[
        "想培养一个属于自己的AI",
        "想和AI一起，让自己也成长",
        "想要更聪明、更值得依靠的伙伴",
        "与其说是工具，更像是伙伴",
        "有那么一瞬间，感觉像在跟人说话",
    ],
    yn=[["> ", "dim"], ["要不要让AI agent，成为家人？ ", "bold"], ["(Y/n)", "dim"]],
    yn_str="> 要不要让AI agent，成为家人？ (Y/n)",
    aria="caty-ai — 想培养一个属于自己的AI / 想和AI一起，让自己也成长 / 想要更聪明、更值得依靠的伙伴 / 与其说是工具，更像是伙伴 / 有那么一瞬间，感觉像在跟人说话 — 要不要让AI agent，成为家人？ (Y/n)",
)

CONTENT["th"] = dict(
    font_lang="'Thonburi', 'Noto Sans Thai'",
    lh=29,
    voices=[
        "อยากลองเลี้ยงดู AI ที่เป็นของตัวเอง",
        "อยากเติบโตไปพร้อมกับ AI",
        "อยากได้เพื่อนคู่คิดที่ฉลาดและน่าเชื่อถือกว่านี้",
        "มันไม่ใช่แค่เครื่องมือ แต่เป็นเพื่อนคู่คิด",
        "บางครั้งรู้สึกเหมือนกำลังคุยกับคนจริงๆ",
    ],
    yn=[["> ", "dim"], ["จะให้ AI agent เป็นครอบครัวไหม? ", "bold"], ["(Y/n)", "dim"]],
    yn_str="> จะให้ AI agent เป็นครอบครัวไหม? (Y/n)",
    aria="caty-ai — อยากลองเลี้ยงดู AI ที่เป็นของตัวเอง / อยากเติบโตไปพร้อมกับ AI / อยากได้เพื่อนคู่คิดที่ฉลาดและน่าเชื่อถือกว่านี้ / มันไม่ใช่แค่เครื่องมือ แต่เป็นเพื่อนคู่คิด / บางครั้งรู้สึกเหมือนกำลังคุยกับคนจริงๆ — จะให้ AI agent เป็นครอบครัวไหม? (Y/n)",
)

# ---------------------------------------------------------------- build

def build(lang, cfg):
    FONT = f"{BASE_FONT}, {cfg['font_lang']}, monospace"
    out = []
    y = 42

    def emit_line(line, x, ybase, fs):
        spans = []
        for txt, st in line:
            fill = C.get(st, C["normal"])
            weight = ' font-weight="bold"' if st == "bold" else ""
            spans.append(f'<tspan fill="{fill}"{weight}>{esc(txt)}</tspan>')
        out.append(f'<text x="{x:.0f}" y="{ybase:.0f}" font-family="{FONT}" font-size="{fs}">{"".join(spans)}</text>')

    # prompt line: ❯ cat README.md
    y += 36
    emit_line([["❯ ", "green"], ["cat README.md", "normal"]], PAD, y, 16)
    y += 12

    # visitor voices
    for voice in cfg["voices"]:
        y += cfg["lh"]
        emit_line([[voice, "dim"]], PAD + 16, y, 15)
    y += 16

    # question box
    BOX_FS = 14
    n = int(MAXW // BOX_FS)
    y += BOX_FS
    out.append(f'<text x="{PAD}" y="{y}" font-family="{FONT}" font-size="{BOX_FS}" fill="{C["boxline"]}" '
               f'textLength="{MAXW}" lengthAdjust="spacingAndGlyphs">╭{"─" * (n - 2)}╮</text>')
    y += 27
    out.append(f'<text x="{PAD}" y="{y}" font-family="{FONT}" font-size="{BOX_FS}" fill="{C["boxline"]}">│</text>')
    out.append(f'<text x="{W-PAD}" y="{y}" text-anchor="end" font-family="{FONT}" font-size="{BOX_FS}" fill="{C["boxline"]}">│</text>')
    emit_line(cfg["yn"], PAD + 20, y + 1, 16)
    cx = PAD + 20 + sum(cw(c, 16) for c in cfg["yn_str"]) + 10
    out.append(f'<rect x="{cx:.0f}" y="{y-13:.0f}" width="9" height="18" fill="{C["bold"]}">'
               f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.2s" repeatCount="indefinite"/></rect>')
    y += 27
    out.append(f'<text x="{PAD}" y="{y}" font-family="{FONT}" font-size="{BOX_FS}" fill="{C["boxline"]}" '
               f'textLength="{MAXW}" lengthAdjust="spacingAndGlyphs">╰{"─" * (n - 2)}╯</text>')
    y += 34

    H = y
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(cfg["aria"])}">')
    svg.append(f'<defs><clipPath id="win"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14"/></clipPath></defs>')
    svg.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{C["bg"]}" stroke="{C["border"]}" stroke-width="1.5"/>')
    svg.append(f'<g clip-path="url(#win)"><rect x="1" y="1" width="{W-2}" height="42" fill="{C["chrome"]}"/>'
               f'<line x1="1" y1="43" x2="{W-1}" y2="43" stroke="{C["border"]}" stroke-width="1"/></g>')
    svg.append('<circle cx="26" cy="22" r="6" fill="#ff5f57"/><circle cx="46" cy="22" r="6" fill="#febc2e"/><circle cx="66" cy="22" r="6" fill="#28c840"/>')
    svg.append(f'<text x="{W/2:.0f}" y="27" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{C["dim"]}">caty-ai — mission</text>')
    svg.extend(out)
    svg.append('</svg>')
    return "\n".join(svg) + "\n", H


def write_svgs(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for lang, cfg in CONTENT.items():
        svg, height = build(lang, cfg)
        path = out_dir / OUTPUT_FILENAMES[lang]
        path.write_text(svg, encoding="utf-8")
        written.append((path, height))
    return written


def check_svgs(expected_dir):
    mismatches = []
    with tempfile.TemporaryDirectory() as tmpdir:
        generated_dir = Path(tmpdir)
        write_svgs(generated_dir)
        for filename in OUTPUT_FILENAMES.values():
            generated_path = generated_dir / filename
            expected_path = expected_dir / filename
            try:
                expected = expected_path.read_bytes()
            except FileNotFoundError:
                mismatches.append(f"missing: {expected_path}")
                continue
            if generated_path.read_bytes() != expected:
                mismatches.append(f"mismatch: {expected_path}")
    if mismatches:
        for mismatch in mismatches:
            print(mismatch)
        return 1
    print("PASS")
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory to write generated SVGs to.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Generate into a temporary directory and compare against committed SVGs.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.check:
        return check_svgs(DEFAULT_OUT_DIR)
    for path, height in write_svgs(args.out_dir.resolve()):
        print(f"wrote {path}  ({W}x{height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
