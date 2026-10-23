#!/usr/bin/env python3
"""Reproducibly generate Flind's *temporary* first-party app identity assets.

Run with Pillow installed: python3 tools/flind/generate_brand_assets.py.
This replaces imported artwork; it is not the final approved design identity.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "frontend/public"
ICONS = PUBLIC / "icons"

INK = "#202936"
PAPER = "#FAFBFE"
ACCENT = "#FF7259"

ICON_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Flind">
<rect width="64" height="64" rx="15" fill="{INK}"/>
<path d="M19 16H46V25H28V31H41V39H28V49H19Z" fill="{PAPER}"/>
<circle cx="46" cy="44" r="4" fill="{ACCENT}"/>
</svg>
"""

WORDMARK_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 64" role="img" aria-label="Flind">
<rect x="0" y="4" width="56" height="56" rx="13" fill="{INK}"/>
<path d="M17 18H42V26H25V32H37V39H25V49H17Z" fill="{PAPER}"/>
<circle cx="42" cy="44" r="4" fill="{ACCENT}"/>
<text x="76" y="48" fill="{INK}" font-family="Arial, Helvetica, sans-serif" font-weight="700" font-size="48">Flind</text>
</svg>
"""

SAFARI_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<path d="M16 8H53V20H28V28H46V40H28V56H16Z" fill="#000"/>
</svg>
"""


def render_icon(size: int) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    sf = size / 64
    box = lambda a: tuple(round(v * sf) for v in a)
    draw.rounded_rectangle(box((0, 0, 64, 64)), radius=round(15 * sf), fill=INK)
    draw.polygon([box((19, 16)), box((46, 16)), box((46, 25)), box((28, 25)), box((28, 31)),
                  box((41, 31)), box((41, 39)), box((28, 39)), box((28, 49)), box((19, 49))], fill=PAPER)
    draw.ellipse(box((42, 40, 50, 48)), fill=ACCENT)
    return im


def render_wordmark() -> Image.Image:
    width, height = 320, 56
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((0, 2, 52, 54), radius=12, fill=INK)
    draw.polygon([(16, 14), (40, 14), (40, 22), (24, 22), (24, 29),
                  (35, 29), (35, 36), (24, 36), (24, 47), (16, 47)], fill=PAPER)
    draw.ellipse((39, 38, 47, 46), fill=ACCENT)
    font_candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ]
    font_path = next((font for font in font_candidates if font.is_file()), None)
    if font_path is None:
        raise RuntimeError("A supported system bold font is required to render the Flind wordmark")
    font = ImageFont.truetype(str(font_path), 44)
    draw.text((70, 3), "Flind", fill=INK, font=font)
    return im


def main() -> None:
    ICONS.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "flind-icon.svg").write_text(ICON_SVG)
    (PUBLIC / "flind-logo.svg").write_text(WORDMARK_SVG)
    (ICONS / "safari-pinned-tab.svg").write_text(SAFARI_SVG)

    sizes = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "apple-touch-icon.png": 180,
        "android-chrome-192x192.png": 192,
        "android-chrome-512x512.png": 512,
    }
    for filename, size in sizes.items():
        render_icon(size).save(ICONS / filename, optimize=True)
    multi = [render_icon(n) for n in (16, 32, 48)]
    multi[-1].save(ICONS / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    multi[-1].save(ICONS / "favicon-dev.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])

    render_wordmark().save(PUBLIC / "flind-logo.png", optimize=True)

    # Temporary compatibility aliases: existing bundled consumers of static
    # URLs must never show the inherited image while references are migrated.
    (PUBLIC / "posthog-icon.svg").write_text(ICON_SVG)
    (PUBLIC / "posthog-logo.svg").write_text(WORDMARK_SVG)
    render_wordmark().save(PUBLIC / "posthog-logo.png", optimize=True)
    print("Generated Flind SVG, PNG, ICO and Safari icons (temporary identity).")


if __name__ == "__main__":
    main()
