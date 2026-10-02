"""Apple ölçü çiziminden (400 dpi raster) bir görünümün dış siluetini çıkarır.
Kullanım (modül): silhouette(png, kutu_110dpi) -> bool maske (satır=aşağı, sütun=sağa), piksel ölçeği ayrı kalibre edilir."""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

K = 400 / 110


def silhouette(png, box110, open_px=7):
    im = np.array(Image.open(png).convert('L'))
    x0, y0, x1, y1 = [int(round(v * K)) for v in box110]
    crop = im[y0:y1, x0:x1] < 160            # çizgiler
    crop = ndi.binary_dilation(crop, iterations=1)
    free = ~crop
    lab, n = ndi.label(free)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    sil = ~bg
    sil = ndi.binary_opening(sil, structure=np.ones((open_px, open_px)))   # ince ölçü çizgilerini at
    lab, n = ndi.label(sil)
    if n > 1:
        sizes = ndi.sum(sil, lab, range(1, n + 1))
        sil = lab == (np.argmax(sizes) + 1)
    return sil, (x0, y0)
