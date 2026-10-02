"""Meshy image-to-3d istemcisi. Anahtar yalnızca MESHY_API_KEY ortam değişkeninden okunur, dosyaya yazılmaz.

Kullanım:
  python scripts/meshy.py balance
  python scripts/meshy.py submit melek seytan
  python scripts/meshy.py wait melek seytan      # bitene kadar bekler, GLB/STL indirir
"""
import base64, json, os, sys, time, urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
API = 'https://api.meshy.ai/openapi'
KEY = os.environ['MESHY_API_KEY']


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def request_body(name):
    img = (root / 'references' / f'{name}.png').read_bytes()
    return {
        'image_url': 'data:image/png;base64,' + base64.b64encode(img).decode(),
        'ai_model': 'meshy-7.1',
        'geometry_resolution': '4k',
        'should_texture': False,
        'should_remesh': True,
        'topology': 'triangle',
        'target_polycount': 300000,
        'save_pre_remeshed_model': True,
        'image_enhancement': False,
        'target_formats': ['glb', 'stl'],
        'multi_view_thumbnails': True,
    }


def download(url, target):
    tmp = target.with_suffix(target.suffix + '.part')
    with urllib.request.urlopen(url, timeout=300) as r, tmp.open('wb') as out:
        while chunk := r.read(1 << 20):
            out.write(chunk)
    tmp.rename(target)


def main():
    cmd, names = sys.argv[1], sys.argv[2:]
    (root / 'raw').mkdir(exist_ok=True)
    if cmd == 'balance':
        print(call('GET', '/v1/balance'))
    elif cmd == 'submit':
        for name in names:
            res = call('POST', '/v1/image-to-3d', request_body(name))
            (root / 'raw' / f'{name}_id.txt').write_text(res['result'])
            print(name, res)
    elif cmd == 'wait':
        pending = set(names)
        while pending:
            for name in sorted(pending):
                tid = (root / 'raw' / f'{name}_id.txt').read_text().strip()
                task = call('GET', f'/v1/image-to-3d/{tid}')
                print(name, task['status'], task.get('progress'), flush=True)
                if task['status'] in ('SUCCEEDED', 'FAILED', 'CANCELED', 'EXPIRED'):
                    (root / 'raw' / f'{name}_task.json').write_text(json.dumps(task, indent=1))
                    if task['status'] == 'SUCCEEDED':
                        dest = root / 'raw' / name
                        dest.mkdir(exist_ok=True)
                        for fmt, url in task.get('model_urls', {}).items():
                            target = dest / f'{fmt}.{fmt.split("_")[-1]}'
                            if fmt in ('glb', 'stl', 'pre_remeshed_glb') and url and not target.exists():
                                download(url, target)
                        thumbs = task.get('thumbnail_urls') or {}
                        if isinstance(thumbs, list):
                            thumbs = dict(enumerate(thumbs))
                        for view, url in thumbs.items():
                            download(url, dest / f'thumb_{view}.png')
                        if task.get('thumbnail_url'):
                            download(task['thumbnail_url'], dest / 'thumb.png')
                    pending.discard(name)
            if pending:
                time.sleep(20)


main()
