"""Mock the real hero so the pagoda can be judged against the momiji, which is
   the whole point of the brief. Usage: python3 mock_hero.py pagoda.png out.png"""
import sys
from PIL import Image, ImageStat

CMP = "/private/tmp/claude-501/-Users-iliaskalalou/1bd10a43-69c5-476d-82d4-b393f02194ee/scratchpad/compare"
W, H = 1700, 950
BG = (12, 12, 12)

pag = Image.open(sys.argv[1]).convert("RGBA")
tree = Image.open(f"{CMP}/cards.png").convert("RGBA")
fuji = Image.open(f"{CMP}/fuji_minimal.png").convert("RGB")

canvas = Image.new("RGB", (W, H), BG)

# Fuji: far back, wide, low
fw = int(W * 1.05)
f = fuji.resize((fw, int(fuji.height * fw / fuji.width)))
canvas.paste(f, ((W - fw) // 2, int(H * 0.30)))

def fit_h(im, h):
    return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)

t = fit_h(tree, int(H * 1.02))
canvas.paste(t, (W - t.width - 40, int(H * 0.02)), t)

p = fit_h(pag, int(H * 0.98))
canvas.paste(p, (30, int(H * 0.02)), p)
canvas.save(sys.argv[2])


def stats(im, label):
    """Mean and 95th-percentile luminance of the non-transparent pixels."""
    rgb = im.convert("RGBA")
    px = list(rgb.getdata())
    lum = sorted(0.2126 * r + 0.7152 * g + 0.0722 * b
                 for (r, g, b, a) in px if a > 20 and (r + g + b) > 24)
    if not lum:
        print(f"{label}: empty"); return
    n = len(lum)
    print(f"{label:10s} mean={sum(lum)/n:6.1f}  median={lum[n//2]:6.1f}  "
          f"p95={lum[int(n*0.95)]:6.1f}  max={lum[-1]:6.1f}  lit_px={n}")

stats(pag, "pagoda")
stats(tree, "momiji")
