# Re-render tree.blend with symmetric margin so the foliage no longer touches
# the frame edge. Camera position untouched; only the vertical FOV is widened
# and the resolution scaled by the same factor, so the tree keeps EXACTLY the
# same pixel scale and only gains transparent margin on all four sides.
import bpy, time
M = 1.34
sc = bpy.context.scene
cam = sc.camera.data
old_lens = cam.lens
cam.lens = old_lens / M
sc.render.resolution_x = int(round(1280 * M / 4) * 4)   # 1716
sc.render.resolution_y = int(round(1600 * M / 4) * 4)   # 2144
sc.render.film_transparent = True
sc.eevee.taa_render_samples = 320
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.compression = 15
sc.render.filepath = "/private/tmp/claude-501/-Users-iliaskalalou/1bd10a43-69c5-476d-82d4-b393f02194ee/scratchpad/hero_css/tree_margin.png"
print("RENDER lens %.2f -> %.2f  res %dx%d" % (old_lens, cam.lens, sc.render.resolution_x, sc.render.resolution_y), flush=True)
t0 = time.time()
bpy.ops.render.render(write_still=True)
print("RENDER DONE in %.1fs" % (time.time() - t0), flush=True)
