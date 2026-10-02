"""Apple ölçü çizimlerinden (Pro 2, AirPods 2) kulaklık vekil katısı üretir.

Sap: ölçülen genişliklerle süper-elips kesit (gerçeğe yakın).
Baş: her yükseklikte ön ve yan siluetin sınır kutusuna oturan süper-elips (n=3,5), sap eksenine göre
simetrik. Yuvarlak gerçek baş kesitini kapsar; figürün elleri başa değmeden biraz boşlukla oturur.

python scripts/make_proxy.py
Çıktı: earbuds/airpodspro2_{R,L}_dec.stl, earbuds/airpods2_{R,L}_dec.stl
"""
import sys
from pathlib import Path
import numpy as np
from scipy.ndimage import median_filter
import trimesh
import manifold3d as mf
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, str(Path(__file__).parent))
from drawing_silhouette import silhouette
from fitlib import cross_section, to_trimesh

root = Path(__file__).resolve().parents[1]
D = root / 'raw/apple_drawings'

PROXIES = {
    # ön görünüm (sapın arka yüzüne bakan), yan görünüm (baş sağa uzanır), px/mm, sap z aralığı (ölçüm), süper-elips üssü,
    # baş yönü açısı (AR modeldeki benzer kulaklıktan), sap merkezi
    'airpods2': dict(png='hi_airpods-2nd-generation-2.png', front=(980, 375, 1165, 815, True), front_open=31, side_open=31, side=(690, 375, 900, 815, False),
                     ppm=38.36, stem_meas=(3, 23), n=2.3, head_dir=-70.7, stem_c=(-15.0, 1.2)),
    'airpodspro2': dict(png='hi_airpods-pro-2nd-generation-2.png', front=(970, 215, 1230, 660, False), side=(1340, 215, 1630, 660, False),
                        ppm=50.6, stem_meas=(4, 11), n=3.0, head_dir=-63.8, stem_c=(-18.2, 1.0)),
}
DZ = 0.05
HEAD_N = 3.5


def profile(sil, ppm, flip):
    if flip:
        sil = sil[:, ::-1]
    ys, xs = np.nonzero(sil)
    ybot = ys.max()
    rows = {}
    for r in range(ys.min(), ybot + 1):
        c = np.nonzero(sil[r])[0]
        if len(c):
            rows[(ybot - r) / ppm] = ((c.min() - xs.min()) / ppm, (c.max() + 1 - xs.min()) / ppm)
    zs = np.array(sorted(rows))
    lo = np.array([rows[z][0] for z in zs]); hi = np.array([rows[z][1] for z in zs])
    # ölçü/kılavuz çizgilerinden kalan çıkıntıları at: 2,5 mm pencereli medyan
    # (medyan tekdüze artan/azalan profili bozmaz, ~1 mm'lik sıçramaları siler)
    w = int(2.5 * ppm) | 1
    lo, hi = median_filter(lo, size=w, mode='nearest'), median_filter(hi, size=w, mode='nearest')
    return zs, lo, hi


def superellipse(a, b, n, cx=0, cy=0, k=180):
    t = np.linspace(0, 2 * np.pi, k, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    x = a * np.sign(c) * np.abs(c) ** (2 / n)
    y = b * np.sign(s) * np.abs(s) ** (2 / n)
    return Polygon(np.c_[x + cx, y + cy])


def build(key):
    cfg = PROXIES[key]
    png = D / cfg['png']
    # AirPods 2 çiziminde 0,5 ve 1,0 mm ölçülerinin uzatma çizgileri başın yanında kapalı şerit oluşturuyor;
    # büyük morfolojik açma ile atılır
    fz, flo, fhi = profile(silhouette(png, cfg['front'][:4], open_px=cfg.get('front_open', 7))[0], cfg['ppm'], cfg['front'][4])
    sz, slo, shi = profile(silhouette(png, cfg['side'][:4], open_px=cfg.get('side_open', 7))[0], cfg['ppm'], cfg['side'][4])
    H = min(fz.max(), sz.max())
    m0, m1 = cfg['stem_meas']
    fm = (fz > m0) & (fz < m1); sm = (sz > m0) & (sz < m1)
    su = (np.median(fhi[fm]) + np.median(flo[fm])) / 2           # sap merkezi (ön görünüm)
    sw_u = np.median(fhi[fm] - flo[fm]); sw_v = np.median(shi[sm] - slo[sm])
    sv = (np.median(shi[sm]) + np.median(slo[sm])) / 2
    stem = superellipse(sw_u / 2, sw_v / 2, cfg['n'])
    # baş, yan siluet genişliği sapınkini 1 mm aştığı ilk yükseklikte başlar
    z_head = min(z for z, a, b in zip(sz, slo, shi) if z > m1 and (b - a) > sw_v + 1.0)
    slabs = []
    for z0 in np.arange(0, H, DZ):
        z = z0 + DZ / 2
        fi = np.argmin(abs(fz - z)); si = np.argmin(abs(sz - z))
        u0, u1 = flo[fi] - su, fhi[fi] - su
        v0, v1 = slo[si] - sv, shi[si] - sv
        if z < z_head:
            # sap: sabit süper-elips; yalnızca alt uçtaki yuvarlatmada siluete göre küçülür
            # (çizimdeki ölçü/kılavuz çizgileri genişliği büyütemez)
            ku = min(1.0, (u1 - u0) / sw_u) if u1 > u0 else 0
            kv = min(1.0, (v1 - v0) / sw_v) if v1 > v0 else 0
            if ku <= 0.05 or kv <= 0.05:
                continue
            g = affinity.scale(stem, ku, kv)
        else:
            if u1 <= u0 or v1 <= v0:
                continue
            umax = max(abs(u0), abs(u1), sw_u / 2)   # simetrik; X yönünde gerçeği kapsar
            # yuvarlak baş kesitini kapsayan, köşeleri kırpılmış süper-elips (n=3,5)
            g = superellipse(umax, (v1 - v0) / 2, HEAD_N, 0, (v0 + v1) / 2)
            if z < z_head + 2.0:
                g = unary_union([g, stem])
        slabs.append(mf.Manifold.extrude(cross_section(g), DZ + 0.004).translate((0, 0, z0 - 0.002)))
    solid = mf.Manifold.batch_boolean(slabs, mf.OpType.Add)
    # kendi çerçevesi (u, v=baş yönü, z) -> giyilmiş çerçeve: v, head_dir açısına döner
    phi = np.radians(cfg['head_dir'])
    # v ekseni (0,1) -> (cos phi, sin phi): z etrafında (phi - 90°) döndür
    solid = solid.rotate((0, 0, np.degrees(phi) - 90)).translate((*cfg['stem_c'], 20.0))
    mesh = to_trimesh(solid)
    print(key, 'yükseklik', round(H, 2), 'baş başlangıcı', round(z_head, 2), 'sap', round(sw_u, 2), 'x', round(sw_v, 2), 'hacim', round(mesh.volume, 1),
          'boyut', np.round(mesh.extents, 2).tolist(), 'su geçirmez', mesh.is_watertight)
    mesh.export(root / f'earbuds/{key}_R_dec.stl')
    mir = mesh.copy(); mir.apply_transform(np.diag([-1, 1, 1, 1]))
    mir.export(root / f'earbuds/{key}_L_dec.stl')


if __name__ == '__main__':
    for k in (sys.argv[1:] or PROXIES):
        build(k)
