#!/bin/sh
# GitHub Actions 里重建：不跑引擎导出（data/routes 已经导好）
set -e
OUT=${1:-out}
mkdir -p build
python3 tools/build_routes_js.py build/routes.js | head -1
python3 tools/compile_itineraries.py build/routes.js
python3 tools/estimate_prices.py
python3 tools/build_routes_js.py build/routes.js | head -1
python3 tools/compile_itineraries.py build/routes.js
python3 tools/build_quality.py | head -1
python3 tools/build_catalog.py build/catalog.js
python3 tools/validate_catalog.py build/routes.js > build/validate.txt; head -1 build/validate.txt
python3 tools/gen_posters.py site_src/posters | tail -1
python3 tools/build_site.py "$OUT"
python3 - "$OUT" <<'EOF'
import os, re, sys
R = sys.argv[1]; bad = []
for d, _, fs in os.walk(R):
    for f in fs:
        if f.endswith('.html'):
            for h in re.findall(r'href="(/[^"#?]*)', open(os.path.join(d, f), encoding='utf-8').read()):
                p = os.path.join(R, h.lstrip('/'), 'index.html') if h.endswith('/') else os.path.join(R, h.lstrip('/'))
                if not os.path.exists(p): bad.append(h)
print('断链', len(set(bad)))
sys.exit(1 if bad else 0)
EOF
