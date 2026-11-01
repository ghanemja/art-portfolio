#!/usr/bin/env python3
"""Give every js/ module a new cache token in index.html (the import map and main.js's tag),
so browsers fetch the new files after a push instead of serving yesterday's from cache.
Run it after any change to js/:  python3 scripts/bump-cache.py"""
import glob, os, re
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
p = os.path.join(root, 'index.html'); s = open(p).read()
cb = max([int(x) for x in re.findall(r'\?cb=(\d+)', s)] or [0]) + 1
mods = sorted(os.path.basename(f) for f in glob.glob(os.path.join(root, 'js', '*.js')))
entries = ',\n'.join(f'  "./js/{m}": "./js/{m}?cb={cb}"' for m in mods)
s = re.sub(r'<script type="importmap">.*?</script>', '<script type="importmap">\n{ "imports": {\n'
           '  "three": "https://unpkg.com/three@0.160.0/build/three.module.min.js",\n'
           '  "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/",\n' + entries + '\n} }\n</script>', s, flags=re.S)
s = re.sub(r'js/main\.js\?cb=\d+', f'js/main.js?cb={cb}', s)
open(p, 'w').write(s); print('cache token', cb, '·', len(mods), 'modules')
