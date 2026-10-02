"""work/ilan/ altındaki ham render'lardan site görsellerini hazırlar: out/ilan/gorseller/*.jpg

.venv/bin/python scripts/ilan_etiket.py
Düz ürün görselleri olduğu gibi kopyalanır; ölçü, uyumluluk ve takma görsellerine yazı ve çizgi eklenir.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
src = root / 'work' / 'ilan'
dst = root / 'out' / 'ilan' / 'gorseller'
dst.mkdir(parents=True, exist_ok=True)

FONT = '/usr/share/fonts/opentype/inter/Inter-{}.otf'
INK = (38, 36, 34)
SOFT = (92, 88, 84)
RED = (176, 24, 30)


def font(size, weight='SemiBold'):
    return ImageFont.truetype(FONT.format(weight), size)


def save(im, name):
    im.convert('RGB').save(dst / name, quality=93, subsampling=0, optimize=True)
    print(name, im.size)


def text(d, xy, s, f, fill=INK, anchor='la'):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def badge(d, xy, n, r=44):
    x, y = xy
    d.ellipse((x - r, y - r, x + r, y + r), fill=INK)
    d.text((x, y), str(n), font=font(48, 'Bold'), fill=(255, 255, 255), anchor='mm')


def arrow(d, a, b, w=9, head=30, fill=RED):
    (x0, y0), (x1, y1) = a, b
    d.line((x0, y0, x1 - head * 0.7, y1), fill=fill, width=w)
    d.polygon([(x1, y1), (x1 - head, y1 - head * 0.6), (x1 - head, y1 + head * 0.6)], fill=fill)


def dim_h(d, x0, x1, y, label, f):
    d.line((x0, y, x1, y), fill=INK, width=4)
    for x in (x0, x1):
        d.line((x, y - 18, x, y + 18), fill=INK, width=4)
    text(d, ((x0 + x1) / 2, y + 26), label, f, anchor='ma')


def dim_v(d, x, y0, y1, label, f):
    d.line((x, y0, x, y1), fill=INK, width=4)
    for y in (y0, y1):
        d.line((x - 18, y, x + 18, y), fill=INK, width=4)
    text(d, (x - 28, (y0 + y1) / 2), label, f, anchor='rm')


# ---- düz ürün görselleri
plain = [('ana', '01_ana_gorsel.jpg'), ('melek', '02_melek_sag_kulaklik.jpg'), ('seytan', '03_seytan_sol_kulaklik.jpg'),
         ('arka', '04_arkadan_gorunum.jpg'), ('detay_melek', '05_detay_melek.jpg'), ('detay_seytan', '06_detay_seytan.jpg'),
         ('figurler', '07_figurler_kulakliksiz.jpg'), ('banner', '11_banner_koyu.jpg')]
for a, b in plain:
    save(Image.open(src / f'{a}.png'), b)



def backdrop(render, size):
    """Render'ın boş sol kenar sütununu yayarak aynı zemin geçişine sahip boş bir fon üretir."""
    im = Image.open(src / f'{render}.png').convert('RGB')
    return im.crop((4, 0, 5, im.height)).resize(size, Image.BILINEAR)


# ---- 08 ölçüler: aynı ölçekte yan ve arka ortografik görünüş
meta = json.loads((src / 'olcu.json').read_text())
im = backdrop('ana', (2000, 2000))
d = ImageDraw.Draw(im)
f_dim, top = font(54), 330
ox = {'olcu_yan': 170, 'olcu_arka': 1060}
for key in ('olcu_yan', 'olcu_arka'):
    r = Image.open(src / f'{key}.png').convert('RGBA')
    im.paste(r, (ox[key], top), r)
m, x0 = meta['olcu_yan'], ox['olcu_yan']
size = [m['max'][k] - m['min'][k] for k in range(3)]
tr = lambda v: f'{v:.0f} mm'
y_alt, y_ust = top + m['alt'][1], top + m['ust'][1]
xs = sorted((x0 + m['y_min'][0], x0 + m['y_max'][0]))
dim_v(d, xs[0] - 40, y_ust, y_alt, tr(size[2]), f_dim)
dim_h(d, xs[0], xs[1], y_alt + 70, tr(size[1]), f_dim)
m, x0 = meta['olcu_arka'], ox['olcu_arka']
xs = sorted((x0 + m['x_min'][0], x0 + m['x_max'][0]))
dim_h(d, xs[0], xs[1], top + m['alt'][1] + 70, tr(size[0]), f_dim)
text(d, (1000, 120), 'Ölçüler', font(96, 'Bold'), anchor='ma')
text(d, (1000, 240), 'Melek figürü · AirPods 4 / 5, Pro 3 ve Pro 2 modelleri', font(44, 'Medium'), SOFT, 'ma')
text(d, (1000, 1790), 'Ağırlık: melek yaklaşık 1,7 g · şeytan yaklaşık 1,9 g', font(50), anchor='ma')
text(d, (1000, 1870), 'AirPods 2 / 1 modeli 32 mm boyundadır. Şeytan figürü melekle aynı boydadır.', font(38, 'Medium'), SOFT, 'ma')
save(im, '08_olculer.jpg')

# ---- 09 uyumluluk: dört kulaklık grubu
tiles = [('airpods45', 'AirPods 4 · AirPods 5'), ('airpodspro3', 'AirPods Pro 3'),
         ('airpodspro2', 'AirPods Pro 2'), ('airpods2', 'AirPods 2 · AirPods 1')]
im = Image.new('RGB', (2000, 2000))
d = ImageDraw.Draw(im)
for i, (key, name) in enumerate(tiles):
    x, y = (i % 2) * 1000, (i // 2) * 1000
    im.paste(Image.open(src / f'uyum_{key}.png').convert('RGB'), (x, y))
    text(d, (x + 500, y + 70), name, font(58, 'Bold'), anchor='ma')
d.line((1000, 60, 1000, 1880), fill=SOFT, width=2)
d.line((60, 1000, 1940, 1000), fill=SOFT, width=2)
text(d, (1000, 1920), 'Kulaklıklar temsilidir ve ürüne dahil değildir.', font(34, 'Medium'), SOFT, 'ma')
save(im, '09_uyumluluk.jpg')

# ---- 10 nasıl takılır
steps = ['Figürü sapın arkasına hizalayın', 'Öne doğru bastırın', 'Yerine oturana kadar itin']
im = Image.new('RGB', (2000, 2000))
im.paste(backdrop('takma_3', (1000, 1000)), (1000, 1000))
d = ImageDraw.Draw(im)
for i, cap in enumerate(steps):
    x, y = (i % 2) * 1000, (i // 2) * 1000
    im.paste(Image.open(src / f'takma_{i + 1}.png').convert('RGB'), (x, y))
    badge(d, (x + 110, y + 110), i + 1)
    text(d, (x + 500, y + 880), cap, font(52), anchor='ma')
    if i < 2:
        m = json.loads((src / f'takma_{i + 1}.json').read_text())
        xa, xb = sorted((m['figur_arka'][0], m['figur_on'][0]))
        ya = max(m['figur_arka'][1], m['figur_on'][1]) + 70
        arrow(d, (x + xa + 20, y + ya), (x + xb + 40, y + ya))
x, y = 1000, 1000
text(d, (x + 110, y + 250), 'Melek sağ kulaklığa,', font(60, 'Bold'))
text(d, (x + 110, y + 330), 'şeytan sol kulaklığa takılır.', font(60, 'Bold'))
text(d, (x + 110, y + 480), 'Şarj kutusuna koymadan önce', font(46, 'Medium'), SOFT)
text(d, (x + 110, y + 545), 'figürü geriye doğru çekerek çıkarın.', font(46, 'Medium'), SOFT)
text(d, (x + 110, y + 650), 'Figür takılıyken kulaklık', font(46, 'Medium'), SOFT)
text(d, (x + 110, y + 715), 'kutuya girmez.', font(46, 'Medium'), SOFT)
d.line((1000, 60, 1000, 1940), fill=SOFT, width=2)
d.line((60, 1000, 1940, 1000), fill=SOFT, width=2)
save(im, '10_nasil_takilir.jpg')
