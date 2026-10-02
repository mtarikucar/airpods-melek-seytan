"""Kaynak görselden melek ve şeytanı ayrı, kare görsellere ayırır."""
from pathlib import Path
from PIL import Image
root = Path(__file__).resolve().parents[1]
src = Image.open(root / 'references/kaynak_figurler.png').convert('RGB')
bg = src.getpixel((5, 5))
boxes = {'melek': (10, 30, 700, 900), 'seytan': (860, 30, 1500, 900)}
for name, (x0, y0, x1, y1) in boxes.items():
    crop = src.crop((x0, y0, x1, y1))
    side = int(max(crop.size) * 1.12)
    canvas = Image.new('RGB', (side, side), bg)
    canvas.paste(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
    canvas = canvas.resize((1024, 1024), Image.LANCZOS)
    canvas.save(root / f'references/{name}.png')
    print(name, canvas.size)
