from PIL import Image, ImageDraw
import os

S = 1024
OUT = "docs/release/store/icon/layered"
os.makedirs(OUT, exist_ok=True)

# --- geometry measured from the approved master icon (gen-appicon-1024.png) ---
BAR_H = 105
RADIUS = BAR_H // 2
# (y_top, x_left, x_right) -- bar 2 is slightly wider, as in the master
BARS = [
    (246, 212, 812),
    (468, 188, 836),
    (690, 212, 812),
]
HL = (688, 786)          # highlight x-range measured on the third bar
HL_COLOR = (122, 176, 245, 255)

# --- background: same vertical gradient as the master ---
top = (30, 79, 191)
bot = (42, 111, 220)
bg = Image.new("RGB", (S, S))
d = ImageDraw.Draw(bg)
for y in range(S):
    t = y / (S - 1)
    d.line([(0, y), (S, y)], fill=tuple(
        round(a + (b - a) * t) for a, b in zip(top, bot)))
bg.save(f"{OUT}/background-1024.png")

# --- foreground: the three key caps, transparent elsewhere ---
fg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(fg)
for y, x0, x1 in BARS:
    d.rounded_rectangle([x0, y, x1, y + BAR_H - 1], radius=RADIUS, fill=(255, 255, 255, 255))

hl_h = 53
hl_y = 716
d.rounded_rectangle([HL[0], hl_y, HL[1], hl_y + hl_h], radius=hl_h // 2, fill=HL_COLOR)
fg.save(f"{OUT}/foreground-1024.png")

# --- previews ---
comp = Image.alpha_composite(bg.convert("RGBA"), fg)
comp.save(f"{OUT}/preview-square-1024.png")

mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=255)
masked = Image.new("RGBA", (S, S), (0, 0, 0, 0))
masked.paste(comp, (0, 0), mask)
masked.save(f"{OUT}/preview-launcher-1024.png")

comp.resize((216, 216), Image.LANCZOS).save(f"{OUT}/preview-216.png")

# --- self-check: geometry must match the master ---
master = Image.open("docs/release/store/icon/gen-appicon-1024.png").convert("RGB")
def bars_of(im):
    rows = []
    for y in range(S):
        xs = [x for x in range(S) if im.getpixel((x, y))[0] > 240 and im.getpixel((x, y))[1] > 240]
        if len(xs) > 100:
            rows.append((y, min(xs), max(xs)))
    groups = []
    for y, a, b in rows:
        if groups and y - groups[-1][-1][0] <= 2:
            groups[-1].append((y, a, b))
        else:
            groups.append([(y, a, b)])
    return [(g[0][0], g[-1][0], min(r[1] for r in g), max(r[2] for r in g)) for g in groups]

mb = bars_of(master)
ob = bars_of(comp.convert("RGB"))
print("master bars:", mb)
print("ours   bars:", ob)
ok = len(mb) == len(ob) == 3 and all(
    abs(m[0] - o[0]) <= 2 and abs(m[1] - o[1]) <= 2 and abs(m[2] - o[2]) <= 2 and abs(m[3] - o[3]) <= 2
    for m, o in zip(mb, ob))
print("GEOMETRY MATCH:", ok)
assert ok, "geometry drift vs master"

for n in ("background-1024.png", "foreground-1024.png", "preview-square-1024.png",
          "preview-launcher-1024.png", "preview-216.png"):
    print("  ", n, os.path.getsize(f"{OUT}/{n}"), "B")
