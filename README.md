# AirPods melek ve şeytan

Kulaklık sapına geçen melek (sağ kulaklık) ve şeytan (sol kulaklık) figürleri. Dört kulaklık grubu için basılabilir STL dosyaları **[out/](out/OKU_BENI.md)** klasöründedir: AirPods 4/5, AirPods Pro 3, AirPods Pro 2 ve AirPods 2/1.

![Tüm modeller](out/onizleme_tum_modeller.png)

Baskı, geçme testi ve kullanım uyarıları [out/OKU_BENI.md](out/OKU_BENI.md) dosyasındadır.

## Site ilanı

Ürün sayfası için görseller ve Türkçe metin **[out/ilan/](out/ilan/ILAN_METNI.md)** klasöründedir: `gorseller/` altında 11 JPG (melek beyaz, şeytan kırmızı), `ILAN_METNI.md` içinde ürün adı, açıklamalar, SSS, SEO alanları ve alt metinler.

Görseller satışa hazır STL'lerden Cycles ile çizilen render'lardır, fotoğraf değildir. Yeniden üretmek için:

1. `blender -b --factory-startup --python scripts/ilan_render.py` (ham render'lar `work/ilan/` altına; `--preview` hızlı ve küçük, `--shots ana,melek` tek tek çizer)
2. `.venv/bin/python scripts/ilan_etiket.py` (yazıları ve ölçü çizgilerini ekler, `out/ilan/gorseller/` altına JPG yazar)

Renkler `ilan_render.py` başındaki `MELEK_COL` ve `SEYTAN_COL` değerleridir.

## Kaynaklar

- `references/`: kullanıcının verdiği konsept görselleri. Figürler `kaynak_figurler.png` görselinden kırpılan `melek.png` ve `seytan.png` ile üretildi.
- Figürler Meshy image-to-3d ile üretildi (meshy-7.1, 4k geometri, doku yok). İki üretim toplam 50 kredi harcadı; kalan bakiye 2385. API anahtarı hiçbir dosyaya yazılmadı, yalnızca `MESHY_API_KEY` ortam değişkeninden okunur.
- Kulaklık geometrisi:
  - AirPods 5 (4 ile aynı gövde) ve Pro 3: apple.com ürün sayfalarındaki AR (USDZ) modeller.
  - Pro 2 ve AirPods 2: developer.apple.com/accessories/dimensional-drawings çizimleri.
  
  Ham dosyalar `raw/` altında yerelde tutulur.

## Yeniden üretim

Kurulum: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`. Blender 5.2 kullanıldı.

1. `python scripts/crop_refs.py`: kaynak görselden figürleri kırpar.
2. `MESHY_API_KEY=... python scripts/meshy.py submit melek seytan` ve `... wait melek seytan`: üretir ve `raw/<figür>/` altına indirir.
3. `blender -b --python scripts/solidify_figure.py -- raw/<figür>/stl.stl work/<figür>_solid.stl`, ardından `python scripts/decimate.py work/<figür>_solid.stl work/<figür>_600k.stl 600000`: figürü 30 mm, kapalı katı yapar.
4. Kulaklıkları hazırlar:
   - `blender -b --python scripts/extract_earbud.py -- raw/airpods5.usdz earbuds/airpods45` (aynısı `airpodspro3.usdz` için de), ardından `decimate.py ... earbuds/<ad>_{L,R}_dec.stl 250000`.
   - `python scripts/make_proxy.py`: Pro 2 ve AirPods 2'yi çizimlerden kurar. Sonra `scripts/voxel_clean.py` ve `decimate.py` çalıştırılır.
5. `scripts/run_all.sh`: dört modeli üretir (`build.py`), kuponları çıkarır (`coupons.py`), et kalınlığını ölçer (`check_thickness.py`), paketi ve önizlemeleri hazırlar (`package.py`).

## Geçme tasarımı (`scripts/build.py`)

- Kişi -Y yönüne bakar, +Z yukarıdır. Sağ kulaklık -X tarafındadır.
- Figür sapın arkasına (+Y) yerleşir, dizleri sapa 2,5 mm gömülür, 1,5 mm dışa kaydırılır.
- Figürden, kulaklığın önden arkaya takılırken süpürdüğü hacim çıkarılır; bu yüzden takmayı engelleyen alttan kesik kalmaz.
- Kulaklık ile figür arasında yan başına 0,12 mm boşluk vardır.
- Diz ve ayak hizasında 1,8 mm yüksek, 1,1 mm kalın iki C kelepçe vardır. Ağızları sapın X genişliğinin %84'üdür.
- Sapın arkasındaki 1,0 mm şerit kelepçeleri figüre bağlar.
- Ellerin altında, kulaklık başına 1,0 mm oturan avuç yastığı vardır. Bu yastık ellerin dışbükey zarfıyla sınırlıdır.
- Başa bakan kanat kesilir.
- Dışa aktarmada aynı konumdaki köşeler birleştirilir ve 0,002 mm altı kıymıklar temizlenir (`fitlib.clean_export`).
