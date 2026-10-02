"""STL'leri Workbench ile birden çok açıdan çizer, tek PNG'de birleştirir.

blender -b --factory-startup --python scripts/render_views.py -- out.png "a.stl:#e8e4dc" "b.stl:#7a8a99" [--views front,right,back,left,top,iso]
Görünüm adları kişinin bakış yönüne göredir: kişi -Y'ye bakar, +Z yukarı.
"""
import bpy, sys, math
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
out = args[0]
views = 'front,right,back,left,top,iso'.split(',')
items = []
i = 1
while i < len(args):
    if args[i] == '--views':
        views = args[i + 1].split(','); i += 2; continue
    items.append(args[i]); i += 1

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
for eng in ('BLENDER_WORKBENCH', 'BLENDER_WORKBENCH_NEXT'):
    try:
        scene.render.engine = eng; break
    except TypeError:
        pass
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_cavity = True; sh.cavity_type = 'BOTH'
sh.show_object_outline = False
scene.display.render_aa = '8'
scene.world = bpy.data.worlds.new('w'); scene.world.color = (0.16, 0.16, 0.17)
scene.render.resolution_x = scene.render.resolution_y = 700
scene.render.film_transparent = False
objs = []
for it in items:
    path, col = it.rsplit(':', 1)
    bpy.ops.wm.stl_import(filepath=path)
    o = bpy.context.selected_objects[0]
    mat = bpy.data.materials.new(path)
    h = col.lstrip('#'); rgb = [int(h[k:k + 2], 16) / 255 for k in (0, 2, 4)]
    mat.diffuse_color = (*rgb, 1)
    o.data.materials.append(mat)
    objs.append(o)
pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
mn = Vector([min(p[k] for p in pts) for k in range(3)]); mx = Vector([max(p[k] for p in pts) for k in range(3)])
ctr = (mn + mx) / 2; rad = (mx - mn).length / 2
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
scene.collection.objects.link(cam); scene.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = rad * 2.15
cam.data.clip_end = rad * 50
dirs = {'front': (0, -1, 0), 'back': (0, 1, 0), 'right': (-1, 0, 0), 'left': (1, 0, 0), 'top': (0, 0.0001, 1),
        'bottom': (0, 0.0001, -1), 'iso': (-0.8, -1, 0.6), 'iso2': (0.8, -1, 0.6), 'isoback': (-0.8, 1, 0.5), 'isoback2': (0.8, 1, 0.5)}
files = []
for v in views:
    d = Vector(dirs[v]).normalized()
    cam.location = ctr + d * rad * 10
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    f = f'{out}.{v}.png'; scene.render.filepath = f
    bpy.ops.render.render(write_still=True)
    files.append((v, f))
# birleştir
import numpy as np
imgs = []
for v, f in files:
    im = bpy.data.images.load(f); a = np.array(im.pixels[:]).reshape(im.size[1], im.size[0], 4)[::-1]
    imgs.append(a)
row = np.concatenate(imgs, axis=1)
h, w = row.shape[:2]
res = bpy.data.images.new('sheet', w, h)
res.pixels = row[::-1].ravel().tolist()
res.filepath_raw = out; res.file_format = 'PNG'; res.save()
import os
for v, f in files:
    os.remove(f)
print('wrote', out)
