"""Teslim paketini hazırlar.

- out/<model>/baski/: figürlerin tablaya oturtulmuş kopyaları (XY ortalı, en alt nokta Z=0, giyilmiş duruşta dik)
- out/<model>/montaj/kulaklik_{sag,sol}_referans.stl: önizleme/kontrol için kulaklık (baskı için değil)
- out/<model>/onizleme.png ve out/onizleme_tum_modeller.png
- out/ozet.json
"""
import json, shutil, subprocess, sys
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).parent))
from build import MODELS, FIGS

root = Path(__file__).resolve().parents[1]
out = root / 'out'
FIG_COL, EAR_COL = '#efe9df', '#8796a8'


def render(png, items, views):
    args = ['blender', '-b', '--factory-startup', '--python', str(root / 'scripts/render_views.py'), '--', str(png),
            *[f'{p}:{c}' for p, c in items], '--views', ','.join(views)]
    subprocess.run(args, check=True, capture_output=True)


def label(img_path, text):
    im = Image.open(img_path).convert('RGB')
    bar = Image.new('RGB', (im.width, 70), (32, 32, 34))
    d = ImageDraw.Draw(bar)
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 38)
    except OSError:
        f = ImageFont.load_default()
    d.text((24, 14), text, fill=(235, 235, 235), font=f)
    c = Image.new('RGB', (im.width, im.height + 70)); c.paste(bar, (0, 0)); c.paste(im, (0, 70))
    c.save(img_path)
    return c


summary = []
sheets = []
for key, cfg in MODELS.items():
    d = out / key
    (d / 'baski').mkdir(parents=True, exist_ok=True)
    for side, name in (('R', 'sag'), ('L', 'sol')):
        shutil.copy(root / cfg['earbud'].format(side=side), d / 'montaj' / f'kulaklik_{name}_referans.stl')
    for fig, side in FIGS.items():
        name = f'{fig}_{"sag" if side == "R" else "sol"}'
        m = trimesh.load(d / 'montaj' / f'{name}.stl')
        b = m.bounds
        m.apply_translation([-(b[0, 0] + b[1, 0]) / 2, -(b[0, 1] + b[1, 1]) / 2, -b[0, 2]])
        m.export(d / 'baski' / f'{name}.stl')
        info = json.loads((d / 'kontrol' / f'{fig}.json').read_text())
        summary.append({k: info[k] for k in ('model', 'figur', 'kulak', 'hacim_mm3', 'agirlik_g_1_15', 'boyut_mm',
                                              'su_gecirmez', 'kulaklik_ile_cakisma_mm3', 'sap_genislik_x', 'kelepce_agzi', 'bosluk')}
                       | {'baski_stl': f'out/{key}/baski/{name}.stl'})
    png = d / 'onizleme.png'
    ang = [(d / 'montaj/melek_sag.stl', FIG_COL), (d / 'montaj/kulaklik_sag_referans.stl', EAR_COL)]
    dev = [(d / 'montaj/seytan_sol.stl', FIG_COL), (d / 'montaj/kulaklik_sol_referans.stl', EAR_COL)]
    parts = [(d / '_a.png', ang, ['right', 'isoback']), (d / '_b.png', dev, ['left', 'isoback2']), (d / '_c.png', ang + dev, ['iso'])]
    for f, items, views in parts:
        render(f, items, views)
    ims = [Image.open(f) for f, _, _ in parts]
    row = Image.new('RGB', (sum(i.width for i in ims), max(i.height for i in ims))); x = 0
    for i in ims:
        row.paste(i, (x, 0)); x += i.width
    row.save(png)
    for f, _, _ in parts:
        f.unlink()
    src = 'Apple AR modeli' if key in ('airpods45', 'airpodspro3') else 'Apple ölçü çizimi (vekil kulaklık)'
    sheets.append(label(png, f"{cfg['name']}  —  kulaklık kaynağı: {src}"))
    print(key, 'tamam')

W = max(s.width for s in sheets)
H = sum(s.height for s in sheets)
allimg = Image.new('RGB', (W, H), (40, 40, 42)); y = 0
for s in sheets:
    allimg.paste(s, (0, y)); y += s.height
allimg = allimg.resize((W * 2 // 5, H * 2 // 5), Image.LANCZOS)
allimg.save(out / 'onizleme_tum_modeller.png')
(out / 'ozet.json').write_text(json.dumps(summary, indent=1, ensure_ascii=False))
print('özet', len(summary))
