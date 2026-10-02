"""Apple AR (USDZ) sahnesinden iki kulaklığı ayırır, kapalı katı yapar, mm cinsinden STL yazar.

blender -b --factory-startup --python scripts/extract_earbud.py -- raw/airpods5.usdz earbuds/airpods45
Çıktı: <out>_L.stl, <out>_R.stl. Sahnede kişi -Y yönüne bakar; +X kulaklık SOL, -X kulaklık SAĞ kulaktır.
"""
import bpy, bmesh, sys
from mathutils import Vector

src, out = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath=src)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']


def bbox(o):
    pts = [o.matrix_world @ v.co for v in o.data.vertices] or [o.matrix_world.translation]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


boxes = {o.name: bbox(o) for o in meshes}
# Kabuk adayı: kulaklık boyutunda (her yönde 12-35 mm, yükseklik > 24 mm) sınır kutusu en büyük parça
cands = []
for o in meshes:
    mn, mx = boxes[o.name]
    s = (mx - mn) * 1000
    if all(12 < v < 35 for v in s) and s.z > 24:
        cands.append(((s.x * s.y * s.z), o))
for side, sign in (('L', 1), ('R', -1)):
    shell = max((c for c in cands if sign * (boxes[c[1].name][0].x + boxes[c[1].name][1].x) > 0), key=lambda c: c[0])[1]
    smn, smx = boxes[shell.name]
    pad = 0.006  # silikon uç kabuk kutusunun ~5 mm dışına taşar
    parts = []
    for o in meshes:
        mn, mx = boxes[o.name]
        if all(mn[i] >= smn[i] - pad and mx[i] <= smx[i] + pad for i in range(3)):
            parts.append(o)
    print(side, 'shell', shell.name, 'parts', len(parts), [round(v * 1000, 2) for v in smn], [round(v * 1000, 2) for v in smx])
    bpy.ops.object.select_all(action='DESELECT')
    dups = []
    for o in parts:
        d = o.copy(); d.data = o.data.copy(); d.parent = None
        d.matrix_world = o.matrix_world.copy()
        bpy.context.scene.collection.objects.link(d)
        dups.append(d)
    for d in dups:
        d.select_set(True)
    bpy.context.view_layer.objects.active = dups[0]
    bpy.ops.object.make_single_user(object=True, obdata=True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    j = bpy.context.active_object
    j.scale = (1000, 1000, 1000)
    bpy.ops.object.transform_apply(scale=True)
    # Kapalı katı: voksel yeniden örnekleme (0,05 mm)
    m = j.modifiers.new('vox', 'REMESH')
    m.mode = 'VOXEL'; m.voxel_size = 0.05; m.adaptivity = 0.0
    bpy.ops.object.modifier_apply(modifier='vox')
    bpy.ops.object.select_all(action='DESELECT'); j.select_set(True)
    bpy.ops.wm.stl_export(filepath=f'{out}_{side}.stl', export_selected_objects=True, apply_modifiers=True)
    print(side, 'verts', len(j.data.vertices))
    bpy.data.objects.remove(j)
