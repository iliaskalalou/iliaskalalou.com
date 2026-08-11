"""Composite an RGBA render over the page background #0c0c0c, as it will be seen.
   Usage: python3 comp.py in.png out.png [--side ref.png]"""
import sys
from PIL import Image

BG = (12, 12, 12)

src = Image.open(sys.argv[1]).convert("RGBA")
dst = Image.new("RGB", src.size, BG)
dst.paste(src, (0, 0), src)
dst.save(sys.argv[2])

# alpha coverage report: how much of the frame the building occupies
a = src.split()[3]
hist = a.histogram()
tot = src.size[0] * src.size[1]
cov = sum(hist[8:]) / tot
bbox = a.getbbox()
print(f"size={src.size} coverage={cov:.3f} bbox={bbox}")
if bbox:
    print(f"  building spans x {bbox[0]}..{bbox[2]}  y {bbox[1]}..{bbox[3]}")
    print(f"  margins  L={bbox[0]} R={src.size[0]-bbox[2]} T={bbox[1]} B={src.size[1]-bbox[3]}")
