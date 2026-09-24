"""Draw packaging/icon.ico (the app and installer icon), matching static/icon.svg.

Only needed when the icon design changes:  python packaging/make_icon.py  (needs Pillow)
"""

from pathlib import Path

from PIL import Image, ImageDraw

S = 1024  # draw large, then scale down for each icon size
k = S / 64  # static/icon.svg uses a 64x64 grid

# Diagonal indigo -> violet gradient.
top, bottom = (0x63, 0x66, 0xF1), (0xA8, 0x55, 0xF7)
grad = Image.new("RGBA", (S, S))
px = grad.load()
for y in range(S):
    for x in range(S):
        t = (x + y) / (2 * S - 2)
        px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,)

mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=round(16 * k), fill=255)
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
img.paste(grad, mask=mask)

d = ImageDraw.Draw(img)
# Play triangle with rounded corners: an inset triangle outlined with a thick, round-jointed line.
r = 2 * k
corners = [(21 * k, 22 * k), (21 * k, 42 * k), (39.5 * k, 32 * k)]
d.polygon(corners, fill="white")
d.line(corners + corners[:1], fill="white", width=round(2 * r), joint="curve")
for cx, cy in corners:
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill="white")

# Two sound waves: (center x, radius, half-angle, opacity) of the arcs in icon.svg.
for cx, radius, angle, alpha in ((39.8, 9, 46, 217), (40.6, 15.5, 45, 140)):
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cx, cy, rr = cx * k, 32 * k, radius * k
    ImageDraw.Draw(layer).arc(
        (cx - rr, cy - rr, cx + rr, cy + rr), start=-angle, end=angle, fill=(255, 255, 255, alpha), width=round(3.6 * k)
    )
    img = Image.alpha_composite(img, layer)

out = Path(__file__).with_name("icon.ico")
img.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Wrote {out}")
