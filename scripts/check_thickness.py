"""Kulaklığa yakın bölgede (oyuk, kelepçe, sırt şeridi) et kalınlığı kontrolü.

Figür yüzeyinden örnek noktalar alınır; kulaklığa 0,6 mm'den yakın olanlardan içe doğru ışın atılır,
karşı yüzeye mesafe (yerel et kalınlığı) ölçülür.
python scripts/check_thickness.py   -> out/<model>/kontrol/kalinlik.json
"""
import json, sys
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
sys.path.insert(0, str(Path(__file__).parent))
from build import MODELS, FIGS

root = Path(__file__).resolve().parents[1]
N = 120000
NEAR = 0.6
THIN = 0.5


def check(model, fig):
    side = FIGS[fig]
    m = trimesh.load(root / f'out/{model}/montaj/{fig}_{"sag" if side == "R" else "sol"}.stl')
    ear = trimesh.load(root / MODELS[model]['earbud'].format(side=side))
    pts, fi = trimesh.sample.sample_surface_even(m, N, seed=1)
    nrm = m.face_normals[fi]
    # kulaklığa yakınlık: kulaklık yüzeyinden yoğun örneklenmiş noktalara en yakın mesafe
    ev, _ = trimesh.sample.sample_surface_even(ear, 400000, seed=2)
    d, _ = cKDTree(ev).query(pts)
    near = d < NEAR
    o = pts[near] - nrm[near] * 1e-4
    r = m.ray.intersects_location(o, -nrm[near], multiple_hits=False)
    loc, idx = r[0], r[1]
    th = np.full(near.sum(), np.inf)
    th[idx] = np.linalg.norm(loc - o[idx], axis=1)
    thin = th < THIN
    res = dict(model=model, figur=fig, ornek=int(near.sum()), min_mm=round(float(th.min()), 3),
               yuzde1_mm=round(float(np.percentile(th[np.isfinite(th)], 1)), 3),
               ince_nokta_orani=round(float(thin.mean()), 4),
               ince_noktalar_z=np.round(np.percentile(pts[near][thin][:, 2], [0, 50, 100]), 2).tolist() if thin.any() else [])
    return res


if __name__ == '__main__':
    for model in (sys.argv[1:] or MODELS):
        out = []
        for fig in FIGS:
            r = check(model, fig)
            print(json.dumps(r, ensure_ascii=False))
            out.append(r)
        (root / f'out/{model}/kontrol/kalinlik.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
