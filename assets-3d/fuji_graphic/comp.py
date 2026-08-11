"""Composite the transparent render over #0c0c0c (and optionally over the sky layer)."""
import sys
from PIL import Image

fg = Image.open(sys.argv[1]).convert('RGBA')
out = sys.argv[2]
sky = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None

base = Image.new('RGBA', fg.size, (12, 12, 12, 255))
if sky:
    s = Image.open(sky).convert('RGBA').resize(fg.size)
    base = Image.alpha_composite(base, s)
Image.alpha_composite(base, fg).convert('RGB').save(out)
print('wrote', out, fg.size)
