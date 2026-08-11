import sys, numpy as np
from PIL import Image

src = sys.argv[1]; dst = sys.argv[2]
sky = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None
im = np.asarray(Image.open(src).convert('RGBA')).astype(np.float64) / 255.0
a = im[..., 3:4]; rgb = im[..., :3]
bg = np.zeros_like(rgb) + (12 / 255.0)
if sky:
    sk = np.asarray(Image.open(sky).convert('RGBA')).astype(np.float64) / 255.0
    bg = sk[..., :3] * sk[..., 3:4] + bg * (1 - sk[..., 3:4])
outp = rgb * a + bg * (1 - a)          # straight alpha
Image.fromarray((np.clip(outp, 0, 1) * 255).astype(np.uint8)).save(dst)

L = (0.2126 * outp[..., 0] + 0.7152 * outp[..., 1] + 0.0722 * outp[..., 2]) * 255
H, W = L.shape
print("%s  %dx%d" % (dst.split('/')[-1], W, H))
print("  luma  max %.1f  p99.9 %.1f  p99 %.1f  p90 %.1f  mean %.1f" %
      (L.max(), np.percentile(L, 99.9), np.percentile(L, 99), np.percentile(L, 90), L.mean()))
print("  alpha max %.2f  cover>0.02: %.1f%%   pixels brighter than 40: %.2f%%  >80: %.3f%%" %
      (a.max(), 100 * (a > 0.02).mean(), 100 * (L > 40).mean(), 100 * (L > 80).mean()))
ys, xs = np.where(L > np.percentile(L, 99.9))
if len(ys):
    print("  brightest region  x %d-%d (%.0f%%-%.0f%%)  y %d-%d (%.0f%%-%.0f%%)" %
          (xs.min(), xs.max(), 100 * xs.min() / W, 100 * xs.max() / W,
           ys.min(), ys.max(), 100 * ys.min() / H, 100 * ys.max() / H))
# vertical luma profile
prof = L.mean(axis=1)
print("  row luma:", " ".join("%d%%:%.0f" % (int(100 * i / H), prof[i]) for i in range(0, H, max(1, H // 12))))
