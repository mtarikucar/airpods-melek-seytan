"""Figür + kulaklık geçme geometrisi için ortak yardımcılar.

Koordinatlar mm. Giyilmiş konum: kişi -Y'ye bakar, +Z yukarı. Sağ kulaklık -X tarafındadır.
Takma yönü: figür kulaklığa arkadan (+Y tarafından) ileri doğru bastırılır. Yani kulaklık figüre
göre önden (-Y) gelir; figürde kulaklığın önden arkaya süpürdüğü hacim boşaltılır.
"""
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union
from shapely import affinity


def to_manifold(mesh):
    m = mf.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32),
                tri_verts=np.asarray(mesh.faces, np.uint32))
    man = mf.Manifold(m)
    if man.status() != mf.Error.NoError:
        raise RuntimeError(f'manifold değil: {man.status()}')
    return man


def to_trimesh(man):
    m = man.to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts), process=False)


def clean_export(man, path, tol=0.002, tries=4):
    """STL'ye temiz yazar: aynı konumdaki köşeleri birleştirir, `tol` altı kıymık/dejenere üçgenleri
    Manifold.simplify ile siler, dosyayı geri okuyup döndürür. (Dilim basamakları, ayrı indeksli ama
    aynı konumlu köşeler bırakıyor; STL'de birleşince ağ bozuluyordu.) Geri okunan dosya su geçirmez
    değilse diskteki hâlinden, toleransı artırarak tekrar dener."""
    cur = man
    for k in range(tries):
        tm = to_trimesh(cur)
        tm.merge_vertices()
        m2 = mf.Manifold(mf.Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                                 tri_verts=np.asarray(tm.faces, np.uint32)))
        if m2.status() != mf.Error.NoError:
            m2 = cur
        m2 = m2.simplify(tol * (1 + k))
        parts = m2.decompose()
        if len(parts) > 1:
            vols = [q.volume() for q in parts]
            m2 = mf.Manifold.batch_boolean([q for q, v in zip(parts, vols) if v > 0.05 * max(vols)], mf.OpType.Add)
        to_trimesh(m2).export(path)
        out = trimesh.load(path)
        if out.is_watertight:
            return out
        cur = mf.Manifold(mf.Mesh(vert_properties=np.asarray(out.vertices, np.float32),
                                  tri_verts=np.asarray(out.faces, np.uint32)))
        if cur.status() != mf.Error.NoError:
            cur = m2
    return out


def polys_of(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return [g for g in getattr(geom, 'geoms', []) if isinstance(g, Polygon)]


def cross_section(geom):
    contours = []
    for p in polys_of(geom):
        p = p.buffer(0)
        for q in polys_of(p):
            ext = np.asarray(q.exterior.coords)[:-1]
            if Polygon(ext).exterior.is_ccw is False:
                ext = ext[::-1]
            contours.append(ext)
            for hole in q.interiors:
                h = np.asarray(hole.coords)[:-1]
                if Polygon(h).exterior.is_ccw:
                    h = h[::-1]
                contours.append(h)
    return mf.CrossSection(contours, mf.FillRule.Positive) if contours else None


def sections(mesh, z_levels):
    """Her z için kesit (shapely geometri)."""
    out = []
    paths = mesh.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=list(z_levels))
    for p in paths:
        if p is None:
            out.append(Polygon())
            continue
        out.append(unary_union(p.polygons_full))
    return out


def sweep_neg_y(poly, length):
    """2B çokgeni -Y yönünde `length` boyunca süpürür (Minkowski ⊕ doğru parçası)."""
    parts = [poly, affinity.translate(poly, 0, -length)]
    for q in polys_of(poly):
        for ring in [q.exterior, *q.interiors]:
            c = np.asarray(ring.coords)
            for a, b in zip(c[:-1], c[1:]):
                quad = Polygon([a, b, b - [0, length], a - [0, length]])
                if quad.area > 1e-9:
                    parts.append(quad)
    return unary_union(parts)


def slab_solid(earbud, z0, z1, h, clearance, sweep_len=None, simplify=0.004):
    """Kulaklığı z0..z1 aralığında h kalınlıklı dilimlerle katıya çevirir.
    Her dilim, alt ve üst sınırdaki kesitlerin birleşimidir (kulaklığı tam kapsar).
    clearance: 2B ofset (mm). sweep_len verilirse dilimler -Y yönünde süpürülür."""
    edges = np.arange(z0, z1 + h, h)
    secs = sections(earbud, edges)
    solids = []
    for i in range(len(edges) - 1):
        g = unary_union([secs[i], secs[i + 1]])
        if g.is_empty:
            continue
        g = g.buffer(clearance, join_style='round', quad_segs=8).simplify(simplify)
        if sweep_len:
            g = sweep_neg_y(g, sweep_len).simplify(simplify)
        cs = cross_section(g)
        if cs is None:
            continue
        # komşu dilimler 0,004 mm bindirilir; tam temas eden yüzeyler birleşmez
        solids.append(mf.Manifold.extrude(cs, edges[i + 1] - edges[i] + 0.004).translate((0, 0, edges[i] - 0.002)))
    return mf.Manifold.batch_boolean(solids, mf.OpType.Add)


def band(stem_section, z0, height, clearance, thickness, gap, chamfer=0.25):
    """Sapı saran C kelepçe. Ağız önde (-Y), genişliği `gap` (iç yüzeyler arası, X yönünde)."""
    inner = stem_section.buffer(clearance, join_style='round', quad_segs=16)
    outer = stem_section.buffer(clearance + thickness, join_style='round', quad_segs=16)
    ring = outer.difference(inner)
    cx, cy = stem_section.centroid.x, stem_section.centroid.y
    ring = ring.difference(box(cx - gap / 2, cy - 100, cx + gap / 2, cy))
    # uçları yuvarlat: içe-dışa ofset
    ring = ring.buffer(-0.2, join_style='round').buffer(0.2, join_style='round')
    layers = []
    # alt/üst kenarlara pah: ring'i katmanlarla daralt
    steps = 3
    for k in range(steps):
        t = chamfer * (1 - (k + 0.5) / steps)
        g = outer.buffer(-t, join_style='round').difference(inner.buffer(t, join_style='round'))
        g = g.difference(box(cx - gap / 2 - t, cy - 100, cx + gap / 2 + t, cy))
        layers.append(g)
    hs = chamfer / steps
    solids = []
    for k, g in enumerate(layers):
        for zz in (z0 + k * hs, z0 + height - (k + 1) * hs):
            cs = cross_section(g)
            if cs is not None:
                solids.append(mf.Manifold.extrude(cs, hs).translate((0, 0, zz)))
    core = cross_section(ring)
    solids.append(mf.Manifold.extrude(core, height - 2 * chamfer).translate((0, 0, z0 + chamfer)))
    return mf.Manifold.batch_boolean(solids, mf.OpType.Add)


def spine(stem_section, z0, z1, clearance, thickness, back_from):
    """Sapın arka yüzünü (figüre bakan yüz) kaplayan şerit; kelepçeleri figüre bağlar.
    back_from: sap merkezinden arkaya (+Y) bu kadar ötesi kaplanır."""
    inner = stem_section.buffer(clearance, join_style='round', quad_segs=16)
    outer = stem_section.buffer(clearance + thickness, join_style='round', quad_segs=16)
    cx, cy = stem_section.centroid.x, stem_section.centroid.y
    g = outer.difference(inner).intersection(box(cx - 100, cy + back_from, cx + 100, cy + 100))
    g = g.buffer(-0.2, join_style='round').buffer(0.2, join_style='round')
    return mf.Manifold.extrude(cross_section(g), z1 - z0).translate((0, 0, z0))


def keep_main(man, min_frac=0.01):
    parts = man.decompose()
    vols = [p.volume() for p in parts]
    vmax = max(vols)
    kept = [p for p, v in zip(parts, vols) if v >= min_frac * vmax]
    dropped = [round(v, 3) for v in vols if v < min_frac * vmax]
    return mf.Manifold.batch_boolean(kept, mf.OpType.Add) if len(kept) > 1 else kept[0], dropped, len(kept)
