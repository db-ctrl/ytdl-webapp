"""Generate an .icns app icon: rounded blue square with a white play + down-arrow."""
import math
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path("/private/tmp/vd_icon.iconset")
OUT.mkdir(parents=True, exist_ok=True)


def rounded_rect(draw, box, r, fill):
    draw.rounded_rectangle(box, radius=r, fill=fill)


def render(size):
    # Supersample for smooth edges.
    S = size * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Background: rounded square with a vertical blue gradient.
    pad = int(S * 0.06)
    box = [pad, pad, S - pad, S - pad]
    radius = int(S * 0.225)  # macOS "squircle"-ish
    top = (79, 140, 255)      # #4f8cff
    bot = (44, 90, 200)
    grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / S
        r = int(top[0] * (1 - t) + bot[0] * t)
        g = int(top[1] * (1 - t) + bot[1] * t)
        b = int(top[2] * (1 - t) + bot[2] * t)
        gd.line([(0, y), (S, y)], fill=(r, g, b, 255))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius, fill=255)
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    cx = S / 2
    white = (255, 255, 255, 255)

    # Play triangle (upper portion).
    tw = S * 0.20
    th = S * 0.24
    ty = S * 0.30
    d.polygon(
        [(cx - tw * 0.45, ty), (cx - tw * 0.45, ty + th), (cx + tw * 0.62, ty + th / 2)],
        fill=white,
    )

    # Down arrow (lower portion): shaft + arrowhead.
    shaft_w = S * 0.075
    shaft_top = S * 0.55
    shaft_bot = S * 0.70
    d.rounded_rectangle(
        [cx - shaft_w / 2, shaft_top, cx + shaft_w / 2, shaft_bot],
        radius=shaft_w / 2, fill=white,
    )
    head = S * 0.13
    d.polygon(
        [(cx - head, shaft_bot - head * 0.15), (cx + head, shaft_bot - head * 0.15),
         (cx, shaft_bot + head * 0.9)],
        fill=white,
    )
    # Base line (tray) under the arrow.
    base_y = S * 0.775
    bw = S * 0.30
    d.rounded_rectangle(
        [cx - bw / 2, base_y, cx + bw / 2, base_y + shaft_w],
        radius=shaft_w / 2, fill=white,
    )

    return img.resize((size, size), Image.LANCZOS)


sizes = [16, 32, 64, 128, 256, 512, 1024]
for s in sizes:
    render(s).save(OUT / f"icon_{s}x{s}.png")
    # @2x variants required by iconutil naming.
for base in [16, 32, 128, 256, 512]:
    render(base * 2).save(OUT / f"icon_{base}x{base}@2x.png")

print("iconset written to", OUT)
