"""Composite an RGBA render over the page background #0c0c0c and report
the luminance distribution, so the pagoda can be judged as it will be seen."""
import sys, numpy as np
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGBA")
bg = Image.new("RGBA", im.size, (12, 12, 12, 255))
out = Image.alpha_composite(bg, im).convert("RGB")
out.save(dst)

a = np.asarray(im).astype(np.float32) / 255.0
rgb, alpha = a[..., :3], a[..., 3]
m = alpha > 0.5
if m.sum():
    lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])[m]
    px = rgb[m]
    print(f"coverage        {m.mean()*100:5.1f}% of frame")
    print(f"luminance  mean {lum.mean():.3f}   p50 {np.percentile(lum,50):.3f}"
          f"   p90 {np.percentile(lum,90):.3f}   p99 {np.percentile(lum,99):.3f}")
    print(f"mean sRGB       #{''.join(f'{int(round(c*255)):02X}' for c in px.mean(0))}")
    hi = px[lum > np.percentile(lum, 97)]
    print(f"brightest 3%    #{''.join(f'{int(round(c*255)):02X}' for c in hi.mean(0))}")
# vertical / horizontal extent of the silhouette
ys, xs = np.where(alpha > 0.06)
if len(ys):
    print(f"bbox  x {xs.min()}..{xs.max()} / {im.size[0]}   "
          f"y {ys.min()}..{ys.max()} / {im.size[1]}")
