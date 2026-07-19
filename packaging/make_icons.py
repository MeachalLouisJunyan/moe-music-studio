#!/usr/bin/env python3
"""Generate the app icon: pink rounded square + white musical note.

Outputs (into packaging/assets/):
  icon.png  — 1024x1024 master, used by the macOS build to make icon.icns
  icon.ico  — multi-size Windows icon, referenced by the PyInstaller spec

Requires Pillow:  pip install pillow
"""

from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).parent / "assets"
SIZE = 1024

PINK = (255, 107, 157)       # theme accent #ff6b9d
PINK_DARK = (214, 69, 120)
WHITE = (255, 255, 255)


def draw_icon():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # rounded-square background with a subtle vertical gradient
    pad = SIZE // 16
    radius = SIZE // 5
    d.rounded_rectangle((pad, pad, SIZE - pad, SIZE - pad),
                        radius=radius, fill=PINK)
    grad = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(pad, SIZE - pad):
        t = (y - pad) / (SIZE - 2 * pad)
        alpha = int(70 * t)
        gd.line([(pad, y), (SIZE - pad, y)],
                fill=(PINK_DARK[0], PINK_DARK[1], PINK_DARK[2], alpha))
    img = Image.alpha_composite(img, grad)
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (pad, pad, SIZE - pad, SIZE - pad), radius=radius, fill=255)
    img.putalpha(mask)
    d = ImageDraw.Draw(img)

    # beamed eighth notes ♫
    u = SIZE // 100
    stem_w = 5 * u
    # note heads (ellipses), stems, beam
    lx, rx = 33 * u, 62 * u          # stem x positions
    head_ry, head_rx = 6 * u, 8 * u  # head radii
    l_bottom, r_bottom = 72 * u, 68 * u
    beam_top = 28 * u

    d.ellipse((lx - head_rx * 2 + stem_w, l_bottom - head_ry,
               lx + stem_w, l_bottom + head_ry), fill=WHITE)
    d.ellipse((rx - head_rx * 2 + stem_w, r_bottom - head_ry,
               rx + stem_w, r_bottom + head_ry), fill=WHITE)
    d.rectangle((lx, beam_top + 2 * u, lx + stem_w, l_bottom), fill=WHITE)
    d.rectangle((rx, beam_top, rx + stem_w, r_bottom), fill=WHITE)
    d.polygon([(lx, beam_top + 2 * u), (rx + stem_w, beam_top - 2 * u),
               (rx + stem_w, beam_top + 6 * u), (lx, beam_top + 10 * u)],
              fill=WHITE)

    return img


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    img = draw_icon()
    img.save(ASSETS / "icon.png")
    img.save(ASSETS / "icon.ico",
             sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                    (64, 64), (128, 128), (256, 256)])
    print(f"wrote {ASSETS / 'icon.png'} and {ASSETS / 'icon.ico'}")


if __name__ == "__main__":
    main()
