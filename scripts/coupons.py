"""Her kulaklık modeli için geçme test kuponları: ürünle aynı kelepçe + sırt şeridi, üç farklı boşluk.

python scripts/coupons.py [model ...]
Çıktı: out/<model>/baski/gecme_testi_sag.stl  (sağ kulaklığa takılır; çentik sayısı = sıra no)
Kupon 1: 0,08 mm, kupon 2: 0,12 mm (figürlerdeki değer), kupon 3: 0,16 mm boşluk.
"""
import sys
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import box
sys.path.insert(0, str(Path(__file__).parent))
from fitlib import band, spine, sections, slab_solid, clean_export
from build import MODELS, BAND_T, GAP_FRAC, SPINE_T, SPINE_BACK, SLAB_H

root = Path(__file__).resolve().parents[1]
CLEARS = [0.08, 0.12, 0.16]
H = 6.0          # kupon yüksekliği
BLOCK = 3.0      # arkadaki tutma bloğu derinliği


def coupon(ear, z_mid, clear, notches):
    sec = sections(ear, [z_mid])[0]
    cx, cy = sec.centroid.x, sec.centroid.y
    x0, y0, x1, y1 = sec.bounds
    gap = GAP_FRAC * (x1 - x0)
    z0 = z_mid - H / 2
    parts = [band(sec, z_mid - 0.9, 1.8, clear, BAND_T, gap),
             spine(sec, z0, z0 + H, clear, SPINE_T, SPINE_BACK)]
    # arkada tutma bloğu (figür gövdesinin yerine)
    blk = mf.Manifold.cube((x1 - x0, BLOCK, H)).translate((x0, y1 + clear + SPINE_T - 0.3, z0))
    parts.append(blk)
    c = mf.Manifold.batch_boolean(parts, mf.OpType.Add)
    # çentikler: bloğun arka üst kenarında
    for k in range(notches):
        nx = cx - (notches - 1) * 0.9 + k * 1.8
        c = c - mf.Manifold.cube((0.7, 1.2, 1.2)).translate((nx - 0.35, y1 + clear + SPINE_T - 0.3 + BLOCK - 0.6, z0 + H - 0.6))
    c = c - slab_solid(ear, z0 - 0.5, z0 + H + 0.5, SLAB_H, clear)
    return c


def main(models):
    for key in models:
        cfg = MODELS[key]
        ear = trimesh.load(root / cfg['earbud'].format(side='R'))
        zb = ear.bounds[0, 2]
        z_mid = zb + (cfg['stem_z'][0] + cfg['stem_z'][1]) / 2
        out = []
        for i, c in enumerate(CLEARS):
            m = coupon(ear, z_mid, c, i + 1)
            bb = m.bounding_box()
            # tablaya: arka blok aşağı değil, kesit yukarı bakacak şekilde (Z ekseni dik), yan yana diz
            m = m.translate((-bb[0] + i * 14.0, -bb[1], -bb[2]))
            out.append(m)
        allm = mf.Manifold.batch_boolean(out, mf.OpType.Add)
        path = root / 'out' / key / 'baski' / 'gecme_testi_sag.stl'
        path.parent.mkdir(parents=True, exist_ok=True)
        mesh = clean_export(allm, path)
        print(key, path.name, 'su geçirmez', mesh.is_watertight, 'parça', len(mesh.split(only_watertight=False)),
              'dejenere', int((mesh.area_faces < 1e-10).sum()), np.round(mesh.extents, 1).tolist())


if __name__ == '__main__':
    main(sys.argv[1:] or list(MODELS))
