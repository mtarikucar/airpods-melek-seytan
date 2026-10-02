"""Melek (sağ kulaklık) ve şeytan (sol kulaklık) figürlerini kulaklığa geçmeli hale getirir.

python scripts/build.py airpods45 [melek|seytan]
Çıktılar: out/<model>/montaj/<figür>_<taraf>.stl (giyilmiş konumda, kulaklık koordinatlarında)
          out/<model>/kontrol/<figür>.json
Baskı kopyaları (tablaya oturtulmuş) scripts/package.py ile out/<model>/baski/ altına çıkarılır.
"""
import json, sys, time
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import box
sys.path.insert(0, str(Path(__file__).parent))
from fitlib import to_manifold, to_trimesh, slab_solid, band, spine, sections, keep_main, clean_export

root = Path(__file__).resolve().parents[1]

# Kulaklık modelleri. Yükseklikler sapın alt ucundan (z_rel) ölçülür.
MODELS = {
    'airpods45': dict(name='AirPods 4 / AirPods 5', earbud='earbuds/airpods45_{side}_dec.stl',
                      fig_h=30.0, hands_z=24.0, knee_depth=2.5, lateral=1.5,
                      bands=[(4.6, 1.8), (10.4, 1.8)], stem_z=(3.0, 12.5)),
    'airpodspro3': dict(name='AirPods Pro 3', earbud='earbuds/airpodspro3_{side}_dec.stl',
                        fig_h=30.0, hands_z=24.5, knee_depth=2.5, lateral=1.5,
                        bands=[(4.6, 1.8), (10.6, 1.8)], stem_z=(3.0, 13.0)),
    # Aşağıdaki ikisi Apple ölçü çizimlerinden kurulan vekil kulaklıklarla yapılır (scripts/make_proxy.py)
    'airpodspro2': dict(name='AirPods Pro 2', earbud='earbuds/airpodspro2_{side}_dec.stl',
                        fig_h=30.0, hands_z=24.5, knee_depth=2.5, lateral=1.5,
                        bands=[(4.6, 1.8), (10.4, 1.8)], stem_z=(3.0, 12.6)),
    'airpods2': dict(name='AirPods 2 / AirPods 1', earbud='earbuds/airpods2_{side}_dec.stl',
                     fig_h=32.0, hands_z=34.7, knee_depth=2.5, lateral=1.5,
                     bands=[(14.5, 1.8), (20.7, 1.8)], stem_z=(14.0, 23.4)),
}
FIGS = {'melek': 'R', 'seytan': 'L'}

CLEAR = 0.12      # kulaklık ile figür arası boşluk (yan başına, mm)
BAND_T = 1.1      # kelepçe et kalınlığı
GAP_FRAC = 0.84   # kelepçe ağzı / sapın X genişliği
SPINE_T = 1.0     # sapın arkasındaki bağlantı şeridi kalınlığı
SPINE_BACK = 1.2  # şerit, sap merkezinin bu kadar arkasından başlar
PAD_T = 1.0       # avuç yastığı kalınlığı
PAD_W, PAD_H = 6.0, 6.0  # ellerin arandığı kutu (X, Z)
SLAB_H = 0.05     # dilim kalınlığı
SWEEP = 40.0      # önden giriş süpürme boyu


def landmarks(fig):
    v = fig.vertices
    up = v[(v[:, 2] > 3) & (v[:, 2] < 10)]
    lo = v[(v[:, 2] > -8) & (v[:, 2] < -2)]
    return up[up[:, 1].argmin()], lo[lo[:, 1].argmin()]


def cut_medial_wing(fig_m, medial_sign):
    """İç taraftaki (başa bakan) kanadı keser; dıştan görünen profil değişmez."""
    x0 = 4.8
    b = mf.Manifold.cube((20, 30, 14.5)).translate((x0 if medial_sign > 0 else -x0 - 20, -1.0, -3.8))
    return fig_m - b


def build(model_key, fig_name):
    cfg = MODELS[model_key]
    side = FIGS[fig_name]
    medial = 1 if side == 'R' else -1  # sağ kulaklık -X tarafında, başa doğru +X
    t0 = time.time()
    ear = trimesh.load(root / cfg['earbud'].format(side=side))
    zb = ear.bounds[0, 2]
    he = ear.bounds[1, 2] - zb
    stem_mid = sections(ear, [zb + np.mean(cfg['stem_z'])])[0]
    cx, cy = stem_mid.centroid.x, stem_mid.centroid.y
    sx0, sy0, sx1, sy1 = stem_mid.bounds
    stem_w = sx1 - sx0

    fig = trimesh.load(root / f'work/{fig_name}_600k.stl')
    k = cfg['fig_h'] / (fig.bounds[1, 2] - fig.bounds[0, 2])
    hands, knee = landmarks(fig)
    fig_m = cut_medial_wing(to_manifold(fig), medial)
    off = np.array([cx - medial * cfg['lateral'] - hands[0] * k,
                    sy1 - cfg['knee_depth'] - knee[1] * k,
                    zb + cfg['hands_z'] - hands[2] * k])
    fig_m = fig_m.scale((k, k, k)).translate(tuple(off))
    hands_w, knee_w = hands * k + off, knee * k + off

    fb = fig_m.bounding_box()
    z0, z1 = max(zb, fb[2] - 0.5), min(ear.bounds[1, 2], fb[5] + 0.5)
    cavity = slab_solid(ear, z0, z1, SLAB_H, CLEAR, sweep_len=SWEEP)
    # avuç yastığı: ellerin altında kulaklık başının yüzünü PAD_T kalınlıkta saran kabuk.
    # Oyulunca incelen parmakları birleştirir, figürün başa oturup aşağı kaymamasını sağlar.
    hz0, hz1 = hands_w[2] - PAD_H / 2, hands_w[2] + PAD_H / 2
    shell = slab_solid(ear, hz0, hz1, SLAB_H, CLEAR + PAD_T) - slab_solid(ear, hz0 - 0.1, hz1 + 0.1, SLAB_H, CLEAR)
    # yastık yalnızca ellerin dışbükey zarfı içinde kalır (yandan bakınca avuçların altında gizli)
    hbox = mf.Manifold.cube((PAD_W, 5.0, PAD_H)).translate((hands_w[0] - PAD_W / 2, hands_w[1] - 1.0, hz0))
    hands_hull = (fig_m ^ hbox).hull()
    fig_m = fig_m + (shell ^ hands_hull)
    carved = fig_m - cavity

    gap = GAP_FRAC * stem_w
    bands = []
    for bz, bh in cfg['bands']:
        sec = sections(ear, [zb + bz + bh / 2])[0]
        bands.append(band(sec, zb + bz, bh, CLEAR, BAND_T, gap))
    lo = min(b[0] for b in cfg['bands'])
    bands.append(spine(stem_mid, zb + lo, zb + cfg['stem_z'][1], CLEAR, SPINE_T, SPINE_BACK))
    part = mf.Manifold.batch_boolean([carved, *bands], mf.OpType.Add)
    # kelepçenin kulaklığa taşan kısmı olmasın (süpürmesiz sıkı boşluk)
    tight = slab_solid(ear, zb + lo - 0.2, zb + cfg['stem_z'][1] + 0.2, SLAB_H, CLEAR)
    part = part - tight
    part, dropped, nparts = keep_main(part)

    ear_m = to_manifold(ear)
    overlap = (part ^ ear_m).volume()
    out = root / 'out' / model_key
    (out / 'kontrol').mkdir(parents=True, exist_ok=True)
    (out / 'montaj').mkdir(exist_ok=True)
    stl = out / 'montaj' / f'{fig_name}_{"sag" if side == "R" else "sol"}.stl'
    mesh = clean_export(part, stl)  # kontroller diskteki dosya üzerinden
    info = dict(model=cfg['name'], figur=fig_name, kulak='sağ' if side == 'R' else 'sol',
                stl=str(stl.relative_to(root)), ucgen=len(mesh.faces), su_gecirmez=bool(mesh.is_watertight), stl_parca=len(mesh.split(only_watertight=False)), dejenere_ucgen=int((mesh.area_faces < 1e-10).sum()),
                hacim_mm3=round(mesh.volume, 1), agirlik_g_1_15=round(mesh.volume * 1.15e-3, 2),
                boyut_mm=np.round(mesh.extents, 2).tolist(), parca_sayisi=nparts, atilan_kirintilar=dropped,
                olcek=round(k, 4), oteleme=np.round(off, 3).tolist(),
                kulaklik_ile_cakisma_mm3=round(overlap, 4), sap_genislik_x=round(stem_w, 2), kelepce_agzi=round(gap, 2), bosluk=CLEAR,
                eller=np.round(hands_w, 2).tolist(), diz=np.round(knee_w, 2).tolist(), sure_s=round(time.time() - t0, 1))
    (out / 'kontrol' / f'{fig_name}.json').write_text(json.dumps(info, indent=1, ensure_ascii=False))
    print(json.dumps(info, ensure_ascii=False))


if __name__ == '__main__':
    model = sys.argv[1]
    for f in (sys.argv[2:] or FIGS):
        build(model, f)
