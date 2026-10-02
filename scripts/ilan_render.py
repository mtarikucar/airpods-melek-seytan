"""İlan (ürün sayfası) görsellerinin ham render'larını Cycles ile çizer.

blender -b --factory-startup --python scripts/ilan_render.py -- [--shots ana,melek,...] [--preview]

Her çekim work/ilan/<ad>.png olarak yazılır; yazı ve ölçü çizgileri scripts/ilan_etiket.py ile eklenir.
Yazı konacak noktaların piksel konumları work/ilan/<ad>.json dosyasına kaydedilir.
Koordinatlar build.py ile aynıdır: kişi -Y'ye bakar, +Z yukarı, sağ kulaklık -X tarafında. Birim mm.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

root = Path(__file__).resolve().parents[1]
out = root / 'work' / 'ilan'
out.mkdir(parents=True, exist_ok=True)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PREVIEW = '--preview' in argv
ONLY = argv[argv.index('--shots') + 1].split(',') if '--shots' in argv else None

MELEK_COL = (0.86, 0.85, 0.82)
SEYTAN_COL = (0.40, 0.010, 0.016)
KULAKLIK_COL = (0.90, 0.90, 0.91)
ACIK_ZEMIN = (0.70, 0.685, 0.665)
KOYU_ZEMIN = (0.012, 0.012, 0.014)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == 'OPTIX'
    sc.cycles.device = 'GPU'
    sc.cycles.samples = 48 if PREVIEW else 320
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.view_settings.view_transform = 'Khronos PBR Neutral'
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'PNG'
    sc.world = bpy.data.worlds.new('w')
    sc.world.use_nodes = True
    return sc


def principled(name, col, rough, sss=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (1.0, 0.6, 0.45)
        b.inputs['Subsurface Scale'].default_value = 0.6
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = 0.08
    return m


def materials():
    return {'melek': principled('melek', MELEK_COL, 0.42, sss=0.25),
            'seytan': principled('seytan', SEYTAN_COL, 0.36, sss=0.15),
            'kulaklik': principled('kulaklik', KULAKLIK_COL, 0.16, coat=0.6)}


def load(path, mat):
    bpy.ops.wm.stl_import(filepath=str(path))
    o = bpy.context.selected_objects[0]
    o.data.materials.append(mat)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    return o


def bounds(objs):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    mn = Vector([min(p[k] for p in pts) for k in range(3)])
    mx = Vector([max(p[k] for p in pts) for k in range(3)])
    return mn, mx


def group(objs, loc=(0, 0, 0), rot_z=0.0, pivot=None):
    """Nesneleri XY kutu merkezinden (ya da pivot'tan) tutup loc'a taşır, Z ekseninde döndürür. Z korunur."""
    mn, mx = bounds(objs)
    c = pivot if pivot is not None else Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0))
    e = bpy.data.objects.new('grp', None)
    bpy.context.scene.collection.objects.link(e)
    e.location = c
    bpy.context.view_layer.update()
    for o in objs:
        o.parent = e
        o.matrix_parent_inverse = e.matrix_world.inverted()
    e.location = Vector(loc) + Vector((0, 0, c.z))
    e.rotation_euler = (0, 0, math.radians(rot_z))
    bpy.context.view_layer.update()
    return e


def earbud(path, mat):
    """Referans kulaklık yalnızca dekordur; seyreltmeden kalan basamak izleri render için yumuşatılır."""
    o = load(path, mat)
    m = o.modifiers.new('yumusat', 'SMOOTH')
    m.factor = 0.5; m.iterations = 40
    return o


def pair(model, side, mats):
    d = root / 'out' / model / 'montaj'
    if side == 'R':
        return [load(d / 'melek_sag.stl', mats['melek']), earbud(d / 'kulaklik_sag_referans.stl', mats['kulaklik'])]
    return [load(d / 'seytan_sol.stl', mats['seytan']), earbud(d / 'kulaklik_sol_referans.stl', mats['kulaklik'])]


def floor(z, col, rough=0.55):
    bpy.ops.mesh.primitive_plane_add(size=40000, location=(0, 0, z))
    p = bpy.context.active_object
    p.data.materials.append(principled('zemin', col, rough))
    return p


def area(name, loc, target, size, power, col=(1, 1, 1)):
    l = bpy.data.lights.new(name, 'AREA')
    l.shape = 'DISK'; l.size = size; l.energy = power; l.color = col
    o = bpy.data.objects.new(name, l)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


def sun(direction, strength, angle=25):
    l = bpy.data.lights.new('sun', 'SUN')
    l.energy = strength; l.angle = math.radians(angle)
    o = bpy.data.objects.new('sun', l)
    bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = (-Vector(direction)).to_track_quat('-Z', 'Y').to_euler()
    return o


def world(strength, col=(1, 1, 1)):
    bg = next(n for n in bpy.context.scene.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (*col, 1)
    bg.inputs['Strength'].default_value = strength


def camera(objs, direction, res, focal=135, fill=0.80, ortho=False, shift=(0, 0), aim=None, width=None):
    """direction: nesneden kameraya doğru. fill: nesnenin kareyi doldurma oranı.
    aim/width verilirse o noktaya bakılır ve width mm genişliğindeki alan kareye sığdırılır."""
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = (res[0] * 2 // 5, res[1] * 2 // 5) if PREVIEW else res
    cd = bpy.data.cameras.new('cam')
    cam = bpy.data.objects.new('cam', cd)
    sc.collection.objects.link(cam); sc.camera = cam
    d = Vector(direction).normalized()
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    right = cam.matrix_world.to_3x3() @ Vector((1, 0, 0))
    up = cam.matrix_world.to_3x3() @ Vector((0, 1, 0))
    mn, mx = bounds(objs)
    corners = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
    us = [c.dot(right) for c in corners]; vs = [c.dot(up) for c in corners]
    if aim is None:
        ctr = (mn + mx) / 2
        ctr += right * ((min(us) + max(us)) / 2 - ctr.dot(right)) + up * ((min(vs) + max(vs)) / 2 - ctr.dot(up))
        w, h = (max(us) - min(us)) / fill, (max(vs) - min(vs)) / fill
    else:
        ctr = Vector(aim); w, h = width, 0
    asp = res[0] / res[1]
    span_w = max(w, h * asp)  # kareye sığması gereken yatay genişlik (mm)
    cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = span_w
        dist = 600
    else:
        cd.lens = focal
        dist = span_w / 2 / (18 / focal)
    cd.shift_x, cd.shift_y = shift
    cd.clip_start = 1; cd.clip_end = 100000
    cam.location = ctr + d * dist
    bpy.context.view_layer.update()
    return cam, span_w


def px(cam, p):
    sc = bpy.context.scene
    v = world_to_camera_view(sc, cam, Vector(p))
    return [round(v.x * sc.render.resolution_x, 1), round((1 - v.y) * sc.render.resolution_y, 1)]


def render(name, meta=None):
    sc = bpy.context.scene
    sc.render.filepath = str(out / f'{name}.png')
    bpy.ops.render.render(write_still=True)
    if meta is not None:
        meta['olcek'] = 0.4 if PREVIEW else 1.0
        (out / f'{name}.json').write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print('ILAN', name, 'tamam', flush=True)


def studio(objs, cam_dir, gap=7.0):
    """Açık zeminli stüdyo. Zemin nesnenin gap mm altındadır ve yalnızca güneş + ortam ışığı alır;
    alan ışıkları ürüne bağlıdır (light linking), böylece zemin düz ve tek gölgeli kalır."""
    mn, mx = bounds(objs)
    floor(mn.z - gap, ACIK_ZEMIN)
    d = Vector(cam_dir).normalized()
    side = d.cross(Vector((0, 0, 1))).normalized()  # kameranın solu
    world(0.26)
    sun(d * 0.35 + side * 0.35 + Vector((0, 0, 1.0)), 1.6, angle=30)
    c = (mn + mx) / 2
    urun = bpy.data.collections.new('urun')
    bpy.context.scene.collection.children.link(urun)
    for o in objs:
        urun.objects.link(o)
    for l in (area('ana', c + d * 200 + side * 160 + Vector((0, 0, 120)), c, 200, 0.75e6),
              area('kenar', c - d * 160 - side * 120 + Vector((0, 0, 140)), c, 120, 0.9e6),
              area('dolgu', c + d * 200 - side * 220 + Vector((0, 0, 40)), c, 220, 0.25e6)):
        l.light_linking.receiver_collection = urun


def dark(objs, cam_dir, gap=7.0):
    """Koyu zeminli sahne: iki yandan kenar ışığı, önden zayıf dolgu."""
    mn, mx = bounds(objs)
    floor(mn.z - gap, KOYU_ZEMIN, rough=0.28)
    d = Vector(cam_dir).normalized()
    side = d.cross(Vector((0, 0, 1))).normalized()
    world(0.015)
    c = (mn + mx) / 2
    area('sol', c - d * 110 + side * 170 + Vector((0, 0, 90)), c, 150, 2.0e6, (1.0, 0.97, 0.93))
    area('sag', c - d * 110 - side * 170 + Vector((0, 0, 90)), c, 150, 2.0e6, (1.0, 0.93, 0.90))
    area('ust', c + d * 60 + Vector((0, 0, 220)), c, 200, 0.9e6)
    area('on', c + d * 260 + side * 60 + Vector((0, 0, 30)), c, 260, 0.45e6)


def facing_pairs(model, mats, gap=5.0):
    """Melek + sağ kulaklık ve şeytan + sol kulaklık, dış yüzleri -X'e bakacak şekilde karşı karşıya."""
    a = pair(model, 'R', mats)
    b = pair(model, 'L', mats)
    amn, amx = bounds(a)
    bmn, bmx = bounds(b)
    ha, hb = (amx.y - amn.y) / 2, (bmx.y - bmn.y) / 2
    group(a, loc=(0, ha + gap / 2, 0))
    group(b, loc=(0, -hb - gap / 2, 0), rot_z=180)
    return a, b


# ---------------------------------------------------------------- çekimler

def shot_ana():
    reset(); mats = materials()
    a, b = facing_pairs('airpods45', mats)
    d = (-1, 0.0, 0.17)
    studio(a + b, d)
    camera(a + b, d, (2000, 2000), fill=0.84)
    render('ana')


def shot_melek():
    reset(); mats = materials()
    a = pair('airpods45', 'R', mats)
    d = (-1, -0.34, 0.22)
    studio(a, d)
    camera(a, d, (2000, 2000), fill=0.70)
    render('melek')


def shot_seytan():
    reset(); mats = materials()
    b = pair('airpods45', 'L', mats)
    d = (1, -0.34, 0.22)
    studio(b, d)
    camera(b, d, (2000, 2000), fill=0.70)
    render('seytan')


def shot_arka():
    reset(); mats = materials()
    a = pair('airpods45', 'R', mats)
    b = pair('airpods45', 'L', mats)
    group(a, loc=(-19, 0, 0)); group(b, loc=(19, 0, 0))
    d = (0.0, 1, 0.2)
    studio(a + b, d)
    camera(a + b, d, (2000, 2000), fill=0.74)
    render('arka')


def shot_detay(name, side):
    reset(); mats = materials()
    p = pair('airpods45', side, mats)
    sx = -1 if side == 'R' else 1
    d = (sx, 0.16, 0.12)
    studio(p, d)
    mn, mx = bounds([p[0]])
    aim = ((mn.x + mx.x) / 2, mn.y + (mx.y - mn.y) * 0.42, mx.z - 8.5)
    cam, _ = camera(p, d, (2000, 2000), focal=160, aim=aim, width=24)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = (cam.location - Vector(aim)).length
    cam.data.dof.aperture_fstop = 22
    render(name)


def shot_figurler():
    """Kulaklıksız figürler: ana görseldeki gibi karşı karşıya, kelepçeler görünsün diye kameraya hafif dönük."""
    reset(); mats = materials()
    d0 = root / 'out' / 'airpods45' / 'baski'
    m = load(d0 / 'melek_sag.stl', mats['melek'])
    s = load(d0 / 'seytan_sol.stl', mats['seytan'])
    group([m], loc=(0, 15, 0), rot_z=-32)
    group([s], loc=(0, -15, 0), rot_z=212)
    d = (-1, 0.0, 0.2)
    studio([m, s], d)
    camera([m, s], d, (2000, 2000), fill=0.74)
    render('figurler')


def shot_olcu():
    """Aynı ölçekte iki ortografik görünüş: yandan (boy, derinlik) ve arkadan (genişlik)."""
    meta = {}
    for name, d in (('olcu_yan', (-1, 0, 0)), ('olcu_arka', (0, 1, 0))):
        sc = reset(); mats = materials()
        m = load(root / 'out' / 'airpods45' / 'baski' / 'melek_sag.stl', mats['melek'])
        sc.render.film_transparent = True
        world(0.75)
        dv = Vector(d); side = dv.cross(Vector((0, 0, 1)))
        sun(dv * 0.9 + side * 0.7 + Vector((0, 0, 1.1)), 2.4, angle=30)
        mn, mx = bounds([m])
        cam, span = camera([m], d, (1000, 1400), ortho=True, aim=(0, 0, 15), width=30)
        meta[name] = {'mm_genislik': span, 'min': list(mn), 'max': list(mx),
                      'alt': px(cam, (0, 0, mn.z)), 'ust': px(cam, (0, 0, mx.z)),
                      'y_min': px(cam, (0, mn.y, 0)), 'y_max': px(cam, (0, mx.y, 0)),
                      'x_min': px(cam, (mn.x, 0, 0)), 'x_max': px(cam, (mx.x, 0, 0))}
        render(name)
    (out / 'olcu.json').write_text(json.dumps(meta, indent=1))


def shot_uyumluluk():
    for model in ('airpods45', 'airpodspro3', 'airpodspro2', 'airpods2'):
        reset(); mats = materials()
        a = pair(model, 'R', mats)
        mn, mx = bounds(a)
        d = (-1, 0.0, 0.17)
        studio(a, d)
        aim = ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, (mn.z + mx.z) / 2)
        camera(a, d, (1000, 1000), aim=aim, width=62)
        render(f'uyum_{model}')


def shot_takma():
    for i, off in enumerate((13.0, 5.0, 0.0), 1):
        reset(); mats = materials()
        a = pair('airpods45', 'R', mats)
        mn, mx = bounds(a)
        a[0].location.y += off
        d = (-1, 0.22, 0.2)
        studio(a, d)
        aim = ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2 + 5.5, (mn.z + mx.z) / 2)
        cam, _ = camera(a, d, (1000, 1000), aim=aim, width=64)
        fmn, fmx = bounds([a[0]])
        cx = (fmn.x + fmx.x) / 2
        meta = {'figur_arka': px(cam, (cx, fmx.y, fmn.z)), 'figur_on': px(cam, (cx, fmn.y, fmn.z))}
        render(f'takma_{i}', meta)


def shot_banner():
    reset(); mats = materials()
    a, b = facing_pairs('airpods45', mats, gap=9.0)
    d = (-1, 0.0, 0.14)
    dark(a + b, d, gap=9.0)
    camera(a + b, d, (2560, 1440), fill=0.60)
    render('banner')


SHOTS = {'ana': shot_ana, 'melek': shot_melek, 'seytan': shot_seytan, 'arka': shot_arka,
         'detay_melek': lambda: shot_detay('detay_melek', 'R'), 'detay_seytan': lambda: shot_detay('detay_seytan', 'L'),
         'figurler': shot_figurler, 'olcu': shot_olcu, 'uyumluluk': shot_uyumluluk, 'takma': shot_takma,
         'banner': shot_banner}

for key in (ONLY or SHOTS):
    SHOTS[key]()
