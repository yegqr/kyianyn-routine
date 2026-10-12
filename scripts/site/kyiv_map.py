#!/usr/bin/env python3
"""Light vector map of Kyiv for the site, built from OpenStreetMap data. Stdlib only.

Usage:
  .venv/bin/python -I scripts/site/kyiv_map.py --fetch   download the raw OSM data (Overpass API, one request
                                                          at a time) into data/bronze/osm/, add one line to
                                                          data/bronze/MANIFEST.md, then build the map
  .venv/bin/python -I scripts/site/kyiv_map.py           rebuild offline from the saved raw files

Writes site/data/kyiv_map.json in SVG coordinates (viewBox width 1000): the city boundary, the Dnipro water
with islands, the river centreline, the 'west' (right bank) and 'east' (left bank) clip regions, the bridges
over the Dnipro from north to south (each one line from the right bank to the left bank across the islands,
with the name BRIDGES gives it), the M1 and M3 river crossings, the metro lines M1, M2 and M3 along their
routes, landmark points and label anchors.
Projection: equirectangular, x = (lon - lon_min) * cos_lat * scale, y = (lat_max - lat) * scale.
Paths are simplified with Douglas-Peucker (the tolerance grows until the file is under 160 KB) and rounded
to 1 decimal; fill them with fill-rule nonzero. Data: (c) OpenStreetMap contributors, ODbL.
"""
import argparse
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data' / 'bronze' / 'osm'
OUT = ROOT / 'site' / 'data' / 'kyiv_map.json'
MANIFEST = ROOT / 'data' / 'bronze' / 'MANIFEST.md'
ENDPOINTS = ('https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
             'https://overpass.private.coffee/api/interpreter')  # the third one when the first two are down
UA = 'airalers-kyianyn-routine/1.0 (https://kyianyn-routine.isakov.fyi; student project, map of Kyiv)'
QBOX = '50.17,30.19,50.63,30.87'  # south,west,north,east: a little wider than the city
WIDTH = 1000.0
MAX_BYTES = 160_000
ATTRIBUTION = '© OpenStreetMap contributors, ODbL'
ROADS = '^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|construction)(_link)?$'

QUERIES = {
    'boundary': '[out:json][timeout:90][maxsize:268435456];(rel["boundary"="administrative"]["wikidata"="Q1899"];'
                'rel["boundary"="administrative"]["admin_level"="4"]["name"="Київ"];);out geom;',
    # river relations print only their member lists; their member ways come with geometry, cut to the query box
    'water': f'[out:json][timeout:90][maxsize:268435456][bbox:{QBOX}];'
             '(rel["natural"="water"]["water"~"^(river|canal|oxbow)$"];rel["waterway"="riverbank"];)->.r;.r out body;'
             f'(way(r.r)({QBOX});way["natural"="water"]["water"~"^(river|canal|oxbow)$"];way["waterway"="riverbank"];'
             'nwr["place"~"^(island|islet)$"];);out geom;',
    'river': f'[out:json][timeout:90][maxsize:268435456][bbox:{QBOX}];(way["waterway"="river"]["name"="Дніпро"];'
             f'way["bridge"]["bridge"!="no"]["highway"~"{ROADS}"];'
             'way["bridge"]["bridge"!="no"]["railway"~"^(rail|subway|light_rail)$"];'
             'nwr["man_made"="bridge"];way["railway"="subway"];rel["route"="subway"];);out geom;',
    'landmarks': f'[out:json][timeout:90][maxsize:268435456][bbox:{QBOX}];(nwr["name"~"Батьківщина"];nwr["name"~"[Дд]звіниц"];'
                 'nwr["name"~"Києво-Печерськ"];nwr["name"~"Андріївськ"];nwr["name"~"Софі"];'
                 'nwr["name"="Золоті ворота"];nwr["name"~"[Тт]елевеж"];'
                 'nwr["man_made"="tower"]["tower:type"="communication"]["name"];'
                 'nwr["name"~"Арка [Сс]вободи|Арка [Дд]ружби"];nwr["name"~"Михайлівськ"];'
                 'nwr["addr:street"~"Миколи Шпака"];'
                 'nwr["name"~"Kyiv School of Economics|Київська школа економіки|^KSE"];);out center tags;',
}


# ---------- fetch ----------

def overpass(query):
    body = urllib.parse.urlencode({'data': query}).encode()
    last = None
    for attempt in range(2):
        for url in ENDPOINTS:
            req = urllib.request.Request(url, data=body, headers={'User-Agent': UA})
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    raw = r.read()
                data = json.loads(raw)
                if data.get('remark') and not data.get('elements'):
                    raise RuntimeError(data['remark'])
                return url, raw, data
            except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError) as e:
                last = e
                print(f'  {url}: {e}', file=sys.stderr)
                time.sleep(10)
    raise SystemExit(f'Overpass failed: {last}')


def fetch(names=None):
    """Download the named queries (all by default), one at a time, then add one line to the MANIFEST."""
    RAW.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    mpath = RAW / 'meta.json'
    meta = json.loads(mpath.read_text()) if names and mpath.exists() else {'queries': {}}
    meta.update(fetched=started, user_agent=UA)
    for i, name in enumerate(names or QUERIES):
        if i:
            time.sleep(8)
        url, raw, data = overpass(QUERIES[name])
        (RAW / f'{name}.json').write_bytes(raw)
        meta['queries'][name] = {'endpoint': url, 'query': QUERIES[name], 'elements': len(data.get('elements', [])),
                                 'bytes': len(raw), 'osm_base': data.get('osm3s', {}).get('timestamp_osm_base')}
        print(f"fetched {name}: {meta['queries'][name]['elements']} elements, {len(raw)} bytes, {url}")
        mpath.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    for name in QUERIES:  # a file saved by an earlier, interrupted run
        if name not in meta['queries'] and (RAW / f'{name}.json').exists():
            raw = (RAW / f'{name}.json').read_bytes()
            data = json.loads(raw)
            meta['queries'][name] = {'endpoint': None, 'query': QUERIES[name], 'elements': len(data['elements']),
                                     'bytes': len(raw), 'osm_base': data.get('osm3s', {}).get('timestamp_osm_base')}
    mpath.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    total = sum(q['elements'] for q in meta['queries'].values())
    base = max(q['osm_base'] or '' for q in meta['queries'].values())
    row = (f'| `osm/` (OpenStreetMap, Overpass API, `scripts/site/kyiv_map.py`: межа Києва, вода Дніпра з островами, '
           f'осьова річки, мости, лінії метро, пам\'ятки; {len(meta["queries"])} запити; © OpenStreetMap contributors, ODbL) '
           f'| {started} | {total} | знімок OSM {base} | знімок OSM {base} |')
    lines = MANIFEST.read_text().splitlines()
    last_row = max(i for i, line in enumerate(lines) if line.startswith('|'))
    lines.insert(last_row + 1, row)
    MANIFEST.write_text('\n'.join(lines) + '\n')


# ---------- geometry ----------

class Proj:
    def __init__(self, s, w, n, e):
        self.lon_min, self.lat_max, self.lat_mean = w, n, (s + n) / 2
        self.cos = math.cos(math.radians(self.lat_mean))
        self.scale = WIDTH / ((e - w) * self.cos)
        self.height = (n - s) * self.scale

    def __call__(self, lat, lon):
        return ((lon - self.lon_min) * self.cos * self.scale, (self.lat_max - lat) * self.scale)

    def lat(self, y):
        return self.lat_max - y / self.scale


def dp(pts, tol):
    """Douglas-Peucker for an open polyline."""
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack, t2 = [(0, len(pts) - 1)], tol * tol
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = pts[a], pts[b]
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        best, idx = -1.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
            d = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
            if d > best:
                best, idx = d, i
        if best > t2:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def dp_ring(ring, tol):
    """Douglas-Peucker for a closed ring (no repeated closing point)."""
    if len(ring) < 4:
        return list(ring)
    x0, y0 = ring[0]
    far = max(range(len(ring)), key=lambda i: (ring[i][0] - x0) ** 2 + (ring[i][1] - y0) ** 2)
    return dp(ring[:far + 1], tol)[:-1] + dp(ring[far:] + [ring[0]], tol)[:-1]


def area(r):
    return sum(r[i - 1][0] * r[i][1] - r[i][0] * r[i - 1][1] for i in range(len(r))) / 2


def centroid(r):
    a = area(r)
    if abs(a) < 1e-9:
        return (sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r))
    cx = sum((r[i - 1][0] + r[i][0]) * (r[i - 1][0] * r[i][1] - r[i][0] * r[i - 1][1]) for i in range(len(r)))
    cy = sum((r[i - 1][1] + r[i][1]) * (r[i - 1][0] * r[i][1] - r[i][0] * r[i - 1][1]) for i in range(len(r)))
    return (cx / (6 * a), cy / (6 * a))


def inside(pt, rings):
    """Even-odd point in polygon over all rings."""
    x, y = pt
    c = False
    for r in rings:
        j = len(r) - 1
        for i in range(len(r)):
            (xi, yi), (xj, yj) = r[i], r[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                c = not c
            j = i
    return c


def winding(pt, rings):
    """Nonzero winding number of a point over all rings, as SVG fills them with fill-rule nonzero."""
    x, y = pt
    w = 0
    for r in rings:
        for (ax, ay), (bx, by) in zip(r[-1:] + r[:-1], r):
            side = (bx - ax) * (y - ay) - (x - ax) * (by - ay)
            if ay <= y < by and side > 0:
                w += 1
            elif by <= y < ay and side < 0:
                w -= 1
    return w


def clip_ring(ring, w, h):
    """Sutherland-Hodgman clip of a ring to the frame [0, w] x [0, h]."""
    def ix(a, b, x):
        return (x, a[1] + (x - a[0]) / (b[0] - a[0]) * (b[1] - a[1]))

    def iy(a, b, y):
        return (a[0] + (y - a[1]) / (b[1] - a[1]) * (b[0] - a[0]), y)

    edges = ((lambda p: p[0] >= 0, lambda a, b: ix(a, b, 0)), (lambda p: p[0] <= w, lambda a, b: ix(a, b, w)),
             (lambda p: p[1] >= 0, lambda a, b: iy(a, b, 0)), (lambda p: p[1] <= h, lambda a, b: iy(a, b, h)))
    pts = list(ring)
    for ok, cut in edges:
        out = []
        for i in range(len(pts)):
            cur, prev = pts[i], pts[i - 1]
            if ok(cur):
                if not ok(prev):
                    out.append(cut(prev, cur))
                out.append(cur)
            elif ok(prev):
                out.append(cut(prev, cur))
        pts = out
        if not pts:
            break
    return pts


def clip_seg(a, b, w, h):
    """Liang-Barsky: the part of segment a-b inside the frame, or None."""
    x0, y0 = a
    dx, dy = b[0] - x0, b[1] - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0), (dx, w - x0), (-dy, y0), (dy, h - y0)):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            if t > t1:
                return None
            t0 = max(t0, t)
        else:
            if t < t0:
                return None
            t1 = min(t1, t)
    return (x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy)


def clip_line(pts, w, h):
    """The longest run of a polyline inside the frame."""
    runs, cur = [], []
    for a, b in zip(pts, pts[1:]):
        seg = clip_seg(a, b, w, h)
        if seg is None:
            if cur:
                runs.append(cur)
                cur = []
            continue
        p, q = seg
        if not cur:
            cur = [p]
        cur.append(q)
        if q != b:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return max(runs, key=len) if runs else []


def seg_x(p, q, a, b):
    """Intersection point of segments p-q and a-b, or None."""
    d = (q[0] - p[0]) * (b[1] - a[1]) - (q[1] - p[1]) * (b[0] - a[0])
    if d == 0:
        return None
    t = ((a[0] - p[0]) * (b[1] - a[1]) - (a[1] - p[1]) * (b[0] - a[0])) / d
    u = ((a[0] - p[0]) * (q[1] - p[1]) - (a[1] - p[1]) * (q[0] - p[0])) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))
    return None


def trim(pts, mid, limit):
    """The part of a polyline within `limit` path length of its vertex nearest to mid."""
    i = min(range(len(pts)), key=lambda k: math.dist(pts[k], mid))

    def walk(seq):
        out, acc = [seq[0]], 0.0
        for a, b in zip(seq, seq[1:]):
            d = math.dist(a, b)
            if acc + d >= limit:
                t = (limit - acc) / d if d else 0.0
                return out + [(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))]
            out.append(b)
            acc += d
        return out
    return walk(pts[i::-1])[::-1] + walk(pts[i:])[1:]


def length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def along(pts, step):
    """(path length, point) about every `step` along a polyline."""
    out, acc = [], 0.0
    for p, q in zip(pts, pts[1:]):
        d = math.dist(p, q)
        n = max(1, int(d / step))
        out += [(acc + d * k / n, (p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n)) for k in range(n)]
        acc += d
    return out + [(acc, pts[-1])]


def cut(pts, a, b):
    """The part of a polyline between path lengths a and b."""
    out, acc = [], 0.0
    for p, q in zip(pts, pts[1:]):
        d = math.dist(p, q)
        if d and acc + d > a and acc < b:
            ta, tb = max(0.0, (a - acc) / d), min(1.0, (b - acc) / d)
            if not out:
                out.append((p[0] + ta * (q[0] - p[0]), p[1] + ta * (q[1] - p[1])))
            out.append((p[0] + tb * (q[0] - p[0]), p[1] + tb * (q[1] - p[1])))
        acc += d
    return out


def join_lines(lines):
    """Join open polylines that share an end point, so a metro line draws as few strokes as possible."""
    key = lambda p: (round(p[0], 1), round(p[1], 1))
    rest, out = [list(x) for x in lines if len(x) >= 2], []
    while rest:
        cur, grew = rest.pop(0), True
        while grew:
            grew = False
            for i, x in enumerate(rest):
                if key(x[0]) == key(cur[-1]):
                    cur += x[1:]
                elif key(x[-1]) == key(cur[-1]):
                    cur += x[::-1][1:]
                elif key(x[-1]) == key(cur[0]):
                    cur = x + cur[1:]
                elif key(x[0]) == key(cur[0]):
                    cur = x[::-1] + cur[1:]
                else:
                    continue
                rest.pop(i)
                grew = True
                break
        out.append(cur)
    return out


def assemble(lines):
    """Join open member lines (lists of (lat, lon)) into rings by matching end points."""
    rings, rest = [], []
    for line in lines:
        line = [p for p in line if p]
        if len(line) >= 2:
            (rings if line[0] == line[-1] else rest).append(line)
    while rest:
        cur, changed = rest.pop(), True
        while cur[0] != cur[-1] and changed:
            changed = False
            for i, line in enumerate(rest):
                if line[0] == cur[-1]:
                    cur = cur + line[1:]
                elif line[-1] == cur[-1]:
                    cur = cur + line[::-1][1:]
                elif line[-1] == cur[0]:
                    cur = line + cur[1:]
                elif line[0] == cur[0]:
                    cur = line[::-1] + cur[1:]
                else:
                    continue
                rest.pop(i)
                changed = True
                break
        rings.append(cur)
    # rings cut by the query box stay open: join the pieces by their nearest ends, which lie outside the frame
    done, cut = [r for r in rings if r[0] == r[-1]], [r for r in rings if r[0] != r[-1]]
    d2 = lambda a, b: (a[0] - b[0]) ** 2 + ((a[1] - b[1]) * 0.64) ** 2
    while cut:
        cur = cut.pop(0)
        while cut:
            i = min(range(len(cut)), key=lambda k: min(d2(cur[-1], cut[k][0]), d2(cur[-1], cut[k][-1])))
            o = cut[i]
            if d2(cur[-1], cur[0]) < min(d2(cur[-1], o[0]), d2(cur[-1], o[-1])):
                break
            cut.pop(i)
            cur = cur + (o if d2(cur[-1], o[0]) <= d2(cur[-1], o[-1]) else o[::-1])
        done.append(cur + [cur[0]])
    return [r[:-1] for r in done if len(r) >= 5]


def latlon(geom):
    return [(round(g['lat'], 7), round(g['lon'], 7)) if g else None for g in geom or []]


def polygon(el, wgeo=None):
    """(outer rings, inner rings) in (lat, lon) for a closed way or a multipolygon relation."""
    if el['type'] == 'way':
        g = latlon(el.get('geometry'))
        if len(g) >= 4 and (g[0] == g[-1] or None in g):
            return assemble([g]), []
        return [], []
    if el['type'] != 'relation':
        return [], []
    ways = [(m, m.get('geometry') or (wgeo or {}).get(m['ref'])) for m in el.get('members', []) if m['type'] == 'way']
    outer = [latlon(g) for m, g in ways if g and m.get('role') in ('outer', '')]
    inner = [latlon(g) for m, g in ways if g and m.get('role') == 'inner']
    return assemble(outer), assemble(inner)


# ---------- build ----------

# a part of the OSM name, the id and the name the site shows. One rule: the name КМВА uses in its bridge rules
# (t.me/VA_Kyiv/21404, 03.10.2026: Північний, Подільсько-Воскресенський, Метро, Патона, Дарницький, Південний), the
# same as crossing.js; a bridge КМВА does not name keeps its official name. OSM calls two of them Подільський
# мостовий перехід and Дарницький залізнично-автомобільний міст. The one-track rail bridge from Рибальський острів
# over the Dnipro and the Desenka (freight and the city electric train) is Рибальський залізничний міст since
# 18 January 2024, before that Петрівський (uk.wikipedia.org).
BRIDGES = (('Північн', 'pivnichnyi', 'Північний міст'), ('Рибальськ', 'rybalskyi', 'Рибальський залізничний міст'),
           ('Петрівськ', 'rybalskyi', 'Рибальський залізничний міст'),
           ('Подільськ', 'podilskyi', 'Подільсько-Воскресенський міст'), ('Метро', 'metro', 'міст Метро'),
           ('Патона', 'patona', 'міст Патона'), ('Дарницьк', 'darnytskyi', 'Дарницький міст'),
           ('Південн', 'pivdennyi', 'Південний міст'))
LANDMARKS = (
    ('motherland', 'Батьківщина-мати', r'Батьківщина-[Мм]ати'),
    ('lavra', 'Києво-Печерська лавра', r'Велика [Лл]аврська дзвіниця|Києво-Печерська лавра'),
    ('andriivska', 'Андріївська церква', r'Андріївська церква'),
    ('sofia', 'Софійський собор', r'Софійський собор|Собор Святої Софії|Свято-Софійський собор'),
    ('golden_gate', 'Золоті ворота', r'^Золоті ворота$'),
    ('tv_tower', 'Київська телевежа', r'[Тт]елевежа'),
    ('arch', 'Арка Свободи', r'Арка [Сс]вободи'),
    ('mykhailivskyi', 'Михайлівський золотоверхий собор', r'Михайлівський [Зз]олотоверхий'),
)


def load(name):
    return json.loads((RAW / f'{name}.json').read_text())['elements']


def fmt(v):
    s = f'{v:.1f}'
    s = s[:-2] if s.endswith('.0') else s
    return '0' if s == '-0' else s


def path_pts(pts, close):
    out = []
    for x, y in pts:
        p = f'{fmt(x)},{fmt(y)}'
        if not out or p != out[-1]:
            out.append(p)
    if close and len(out) < 3:
        return ''
    return 'M' + 'L'.join(out) + ('Z' if close else '')


def path_rings(rings):
    return ''.join(path_pts(r, True) for r in rings)


def orient(r, positive):
    return r if (area(r) > 0) == positive else r[::-1]


def tag_score(t):
    s = 3 * ('historic' in t) + 2 * (t.get('tourism') in ('attraction', 'museum', 'artwork', 'viewpoint'))
    s += 2 * ('building' in t or t.get('amenity') == 'place_of_worship' or t.get('man_made') in ('tower', 'mast'))
    s += 2 * ('wikidata' in t) + ('wikipedia' in t) + 5 * ('дзвіниц' in t.get('name', '').lower())
    bad = ('railway', 'public_transport', 'highway', 'shop', 'office', 'station', 'route')
    if any(k in t for k in bad) or t.get('amenity') not in (None, 'place_of_worship'):
        s -= 8
    return s


def where(e):
    c = e.get('center') or e
    return (c['lat'], c['lon']) if 'lat' in c else None


def landmarks(P):
    els = [e for e in load('landmarks') if where(e)]
    out, missing = [], []

    def add(lid, title, e):
        lat, lon = where(e)
        x, y = P(lat, lon)
        out.append({'id': lid, 'name': title, 'x': round(x, 1), 'y': round(y, 1), 'lat': round(lat, 5),
                    'lon': round(lon, 5), 'osm': f"{e['type']}/{e['id']}", 'osm_name': e['tags'].get('name', '')})

    for lid, title, pat in LANDMARKS:
        cand = [e for e in els if re.search(pat, e.get('tags', {}).get('name', ''))]
        if cand:
            add(lid, title, max(cand, key=lambda e: (tag_score(e['tags']), e['type'] != 'node')))
        else:
            missing.append(title)
    kse = [e for e in els if 'Миколи Шпака' in e.get('tags', {}).get('addr:street', '')
           and e['tags'].get('addr:housenumber') == '3']
    kse = kse or [e for e in els if re.search(r'Kyiv School of Economics|Київська школа економіки|^KSE',
                                              e.get('tags', {}).get('name', ''))]
    if kse:
        add('kse', 'KSE', max(kse, key=lambda e: ('name' in e['tags'], 'building' in e['tags'], e['type'] != 'node')))
    else:
        missing.append('KSE, вул. Миколи Шпака, 3')
    return out, missing


def near_cells(line, cell=25, reach=2):
    cells = set()
    for a, b in zip(line, line[1:]):
        n = max(1, int(math.dist(a, b) / (cell / 2)))
        for k in range(n + 1):
            cx = int((a[0] + (b[0] - a[0]) * k / n) // cell)
            cy = int((a[1] + (b[1] - a[1]) * k / n) // cell)
            cells.update((cx + i, cy + j) for i in range(-reach, reach + 1) for j in range(-reach, reach + 1))
    return lambda p: (int(p[0] // cell), int(p[1] // cell)) in cells


def mode(t):
    if t.get('railway') == 'subway':
        return 'metro'
    if t.get('railway') in ('rail', 'light_rail'):
        return 'rail'
    return 'road' if t.get('highway') else None


def line_id(t):
    ref, name = re.sub(r'\D', '', t.get('ref', '')), t.get('name', '')
    if ref == '1' or 'Святошинсько' in name:
        return 'M1'
    if ref == '3' or 'Сирецько' in name:
        return 'M3'
    return 'M2' if ref == '2' or 'Оболонсько' in name else None


def build():
    meta = json.loads((RAW / 'meta.json').read_text())
    rels = [e for e in load('boundary') if e['type'] == 'relation']
    rel = (next((e for e in rels if e['tags'].get('name') == 'Київ' and e['tags'].get('admin_level') == '4'), None)
           or next((e for e in rels if e['tags'].get('wikidata') == 'Q1899'), None))
    if not rel:
        raise SystemExit('the Kyiv boundary relation is not in the raw data')
    c_out, c_in = polygon(rel)
    lats, lons = [p[0] for r in c_out for p in r], [p[1] for r in c_out for p in r]
    s, n, w, e = min(lats), max(lats), min(lons), max(lons)
    P = Proj(s - (n - s) * 0.025, w - (e - w) * 0.025, n + (n - s) * 0.025, e + (e - w) * 0.025)
    W, H = WIDTH, P.height
    city_outer = [[P(*p) for p in r] for r in c_out]
    city = [orient(r, True) for r in city_outer] + [orient([P(*p) for p in r], False) for r in c_in]

    # the Dnipro centreline, north to south, cut to the frame and run out to its edges
    river = load('river')
    ways = [x for x in river if x['type'] == 'way' and x.get('tags', {}).get('waterway') == 'river'
            and x['tags'].get('name') == 'Дніпро' and x.get('geometry')]
    by_start, ends = defaultdict(list), {x['nodes'][-1] for x in ways}
    for x in ways:
        by_start[x['nodes'][0]].append(x)
    heads = [x for x in ways if x['nodes'][0] not in ends] or ways
    best = []
    for x in heads:
        chain, seen, cur = [], set(), x
        while cur and cur['id'] not in seen:
            seen.add(cur['id'])
            g = [(p['lat'], p['lon']) for p in cur['geometry'] if p]
            chain += g if not chain else g[1:]
            nxt = [y for y in by_start.get(cur['nodes'][-1], []) if y['id'] not in seen]
            cur = nxt[0] if nxt else None
        if len(chain) > len(best):
            best = chain
    line = clip_line([P(*p) for p in best], W, H)
    if line[0][1] > line[-1][1]:
        line.reverse()

    def on_edge(p):
        return p[0] <= 0.05 or p[0] >= W - 0.05 or p[1] <= 0.05 or p[1] >= H - 0.05
    if not on_edge(line[0]):
        line.insert(0, (line[0][0], 0.0))
    if not on_edge(line[-1]):
        line.append((line[-1][0], H))

    def regions(c):
        def t_of(p):
            x, y = p
            if y <= 0.05:
                return x
            if x >= W - 0.05:
                return W + y
            if y >= H - 0.05:
                return W + H + (W - x)
            return 2 * W + H + (H - y)
        ts, te = t_of(c[0]), t_of(c[-1])
        corners = sorted([((W, 0.0), W), ((W, H), W + H), ((0.0, H), 2 * W + H), ((0.0, 0.0), 0.0)], key=lambda k: k[1])
        east = c + [p for p, t in reversed(corners) if ts < t < te]
        west = c + [p for p, t in corners if t > te] + [p for p, t in corners if t < ts]
        return west, east

    # water near the Dnipro, its holes and the island polygons
    near = near_cells(line)
    water, holes, place_islands = [], [], []
    wels = load('water')
    wgeo = {x['id']: x['geometry'] for x in wels if x['type'] == 'way' and x.get('geometry')}
    for el in wels:
        t = el.get('tags', {})
        if not (t.get('natural') == 'water' or t.get('waterway') == 'riverbank' or t.get('place') in ('island', 'islet')):
            continue
        outer, inner = polygon(el, wgeo)
        outer = [r for r in (clip_ring([P(*p) for p in r], W, H) for r in outer) if len(r) >= 3]
        inner = [r for r in (clip_ring([P(*p) for p in r], W, H) for r in inner) if len(r) >= 3]
        if t.get('place') in ('island', 'islet'):
            place_islands += [(t.get('name'), r) for r in outer if abs(area(r)) > 6 and near(centroid(r))]
            continue
        keep = [r for r in outer if abs(area(r)) > 3 and any(near(p) for p in r[::4])]
        if keep:
            water += [orient(r, True) for r in keep]
            hs = [r for r in inner if abs(area(r)) > 3]
            water += [orient(r, False) for r in hs]
            holes += [r for r in hs if abs(area(r)) > 6]

    def bbox(r):
        xs, ys = [p[0] for p in r], [p[1] for p in r]
        return min(xs), min(ys), max(xs), max(ys)
    hole_boxes = [(bbox(h), h) for h in holes]
    islands, island_labels = [orient(h, True) for h in holes], []
    for name, r in place_islands:
        c = centroid(r)
        if not any(b[0] <= c[0] <= b[2] and b[1] <= c[1] <= b[3] and inside(c, [h]) for b, h in hole_boxes):
            islands.append(orient(r, True))
        if name and abs(area(r)) > 300:
            if not inside(c, [r]):
                c = min(r, key=lambda p: math.dist(p, c))
            island_labels.append({'name': name, 'x': round(c[0], 1), 'y': round(c[1], 1)})

    # bridges: bridge ways that cross the centreline inside the city, grouped by place
    geo = {x['id']: [P(g['lat'], g['lon']) for g in x['geometry'] if g]
           for x in river if x['type'] == 'way' and x.get('geometry')}
    bways = [x for x in river if x['type'] == 'way' and x.get('tags', {}).get('bridge', 'no') != 'no'
             and mode(x['tags']) and x['id'] in geo]
    segs = list(zip(line, line[1:]))
    buckets = defaultdict(list)
    for i, (a, b) in enumerate(segs):
        for k in range(int(min(a[1], b[1]) // 10), int(max(a[1], b[1]) // 10) + 1):
            buckets[k].append(i)
    hits = []
    for x in bways:
        pts = geo[x['id']]
        for p, q in zip(pts, pts[1:]):
            cand = set()
            for k in range(int(min(p[1], q[1]) // 10), int(max(p[1], q[1]) // 10) + 1):
                cand.update(buckets.get(k, ()))
            for i in cand:
                pt = seg_x(p, q, *segs[i])
                if pt and inside(pt, city_outer):
                    hits.append((pt, x))
    hits.sort(key=lambda h: h[0][1])
    clusters = []
    for pt, x in hits:
        for c in clusters:
            if any(math.dist(pt, q) < 9 for q, _ in c):
                c.append((pt, x))
                break
        else:
            clusters.append([(pt, x)])
    areas = []
    for x in river:
        t = x.get('tags', {})
        if t.get('man_made') == 'bridge' and t.get('name'):
            areas += [(t['name'], bbox(r), r) for r in ([P(*p) for p in r] for r in polygon(x)[0])]
    pools = defaultdict(lambda: defaultdict(list))
    for x in bways:
        for nd in (x['nodes'][0], x['nodes'][-1]):
            pools[mode(x['tags'])][nd].append(x)
    subway = defaultdict(list)
    for x in river:
        if x['type'] == 'way' and x.get('tags', {}).get('railway') == 'subway' and x['id'] in geo:
            for nd in (x['nodes'][0], x['nodes'][-1]):
                subway[nd].append(x)
    route_of = {}
    for x in river:
        if x['type'] == 'relation' and x.get('tags', {}).get('route') == 'subway':
            for m in x.get('members', []):
                if m['type'] == 'way':
                    route_of.setdefault(m['ref'], x['tags'])

    # the metro lines along their routes: the track members (empty role) of the route relations of both directions
    tracks = defaultdict(dict)
    for x in river:
        if x['type'] == 'relation' and x.get('tags', {}).get('route') == 'subway' and line_id(x['tags']):
            for m in x.get('members', []):
                pts = [P(g['lat'], g['lon']) for g in m.get('geometry') or [] if g] or geo.get(m['ref'], [])
                if m['type'] == 'way' and not m.get('role') and len(pts) >= 2:
                    tracks[line_id(x['tags'])].setdefault(m['ref'], pts)
    routes = {lid: join_lines(list(ws.values())) for lid, ws in sorted(tracks.items())}

    def grow(w0, pool, limit):
        nodes, pts, used = list(w0['nodes']), list(geo[w0['id']]), {w0['id']}
        for _ in range(2):
            start = length(pts)
            while length(pts) - start < limit:
                nxt = [x for x in pool.get(nodes[-1], []) if x['id'] not in used]
                if not nxt or len(pts) < 2:
                    break
                h0 = math.atan2(pts[-1][1] - pts[-2][1], pts[-1][0] - pts[-2][0])

                def turn(x):
                    g = geo[x['id']] if x['nodes'][0] == nodes[-1] else geo[x['id']][::-1]
                    d = abs(math.atan2(g[1][1] - g[0][1], g[1][0] - g[0][0]) - h0) % (2 * math.pi)
                    return min(d, 2 * math.pi - d)
                x = min(nxt, key=turn)
                used.add(x['id'])
                fwd = x['nodes'][0] == nodes[-1]
                nodes += (x['nodes'] if fwd else x['nodes'][::-1])[1:]
                pts += (geo[x['id']] if fwd else geo[x['id']][::-1])[1:]
            nodes.reverse()
            pts.reverse()
        return pts

    # a point on a bank: outside the water and every island
    boxes = [[(bbox(r), r) for r in water], [(bbox(r), r) for r in islands]]

    def bank(p):
        return not any(winding(p, [r for b, r in rs if b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]]) for rs in boxes)

    def span(w0, pool, on_land):
        """Way w0 grown into the whole crossing: (length of its straight parts, points). It joins the way at its end
        with the least turn: any way of the pool off the bank (in the water or on an island), on a bank only if
        on_land (the road and rail pools hold bridge ways only, the subway pool whole lines). A road across an
        island is no bridge, so it is not in the data: where nothing joins off the bank, the line runs straight
        to the nearest way of the pool ahead."""
        ways = {x['id']: x for xs in pool.values() for x in xs}
        nodes, pts, used, straight = list(w0['nodes']), list(geo[w0['id']]), {w0['id']}, 0.0

        def turn(a, b, h):
            d = abs(math.atan2(b[1] - a[1], b[0] - a[0]) - h) % (2 * math.pi)
            return min(d, 2 * math.pi - d)
        for _ in range(2):
            start = length(pts)
            while length(pts) - start < 100:
                end, off = pts[-1], not bank(pts[-1])
                back = next((p for p in reversed(pts) if math.dist(p, end) >= 3), pts[0])
                h = math.atan2(end[1] - back[1], end[0] - back[0])
                joined = [((x['nodes'], geo[x['id']]) if x['nodes'][0] == nodes[-1] else
                           (x['nodes'][::-1], geo[x['id']][::-1]), x)
                          for x in pool.get(nodes[-1], []) if x['id'] not in used] if off or on_land else []
                if joined:
                    (ns, g), x = min(joined, key=lambda j: turn(j[0][1][0], j[0][1][1], h))
                    ns, g = ns[1:], g[1:]
                elif off:
                    ahead = [(math.dist(end, g[0]), ns, g, x) for x in ways.values() if x['id'] not in used
                             for ns, g in ((x['nodes'], geo[x['id']]), (x['nodes'][::-1], geo[x['id']][::-1]))
                             if math.dist(end, g[0]) < 40 and turn(g[0], g[-1], h) < 0.8
                             and (math.dist(end, g[0]) < 0.5 or turn(end, g[0], h) < 0.6)]
                    if not ahead:
                        break
                    d, ns, g, x = min(ahead, key=lambda a: a[0])
                    straight += d
                else:
                    break
                used.add(x['id'])
                nodes += ns
                pts += g
            nodes.reverse()
            pts.reverse()
        return straight, pts

    west0, east0 = regions(dp(line, 2))
    bridges, metro, used_ids = [], {}, set()
    for c in clusters:
        votes = defaultdict(int)
        named = [(pt, x) for pt, x in c if mode(x['tags']) == 'road'] or c  # a road and rail pair takes the road bridge name
        for pt, x in named:
            for name, b, r in areas:
                if b[0] - 1 <= pt[0] <= b[2] + 1 and b[1] - 1 <= pt[1] <= b[3] + 1:
                    votes[name] += 100 if inside(pt, [r]) else 30
            t = x['tags']
            if t.get('bridge:name'):
                votes[t['bridge:name']] += 10
            elif 'міст' in t.get('name', '').lower():
                votes[t['name']] += 1
        name = max(votes, key=votes.get) if votes else 'міст без назви'
        bid, name = next(((v, shown) for k, v, shown in BRIDGES if k in name), ('bridge', name))
        modes = {mode(x['tags']) for _, x in c}
        road = [x for _, x in c if mode(x['tags']) == 'road']
        kind = 'metro' if 'Метро' in name else 'rail' if modes == {'rail'} else 'road'
        mid = (sum(p[0] for p, _ in c) / len(c), sum(p[1] for p, _ in c) / len(c))
        while bid in used_ids:
            bid += '_2'
        used_ids.add(bid)
        # the whole crossing of each mode on it, then the one with the shortest straight parts, the road first
        # (the road across Hidropark is no bridge, the metro track of the Metro bridge runs on to the left bank)
        spans = []
        for m in sorted(modes, key=('road', 'rail', 'metro').index):
            w0 = max((x for _, x in c if mode(x['tags']) == m), key=lambda x: length(geo[x['id']]))
            straight, pts = span(w0, subway, False) if m == 'metro' else span(w0, pools[m], True)
            spans.append((straight, len(spans), pts))
        straight, _, pts = min(spans)
        if not inside(pts[0], [west0]):  # from the right bank to the left bank
            pts = pts[::-1]
        # the part over the river and its islands, landing 4 units (about 180 m) on each bank
        off = [k for k, p in along(pts, 1) if not bank(p)]
        pts = cut(pts, off[0] - 4, off[-1] + 4) if off else pts
        item = {'id': bid, 'name': name, 'kind': kind, 'carries': sorted(modes), 'pts': pts, 'straight': straight,
                'banks': bank(pts[0]) and bank(pts[-1]), 'mid': mid, 'lat': round(P.lat(mid[1]), 4)}
        if road and all(x['tags'].get('highway') == 'construction' for x in road):
            item['construction'] = True
        bridges.append(item)
        sub = [x for _, x in c if mode(x['tags']) == 'metro']
        if sub:
            lid = next((line_id(route_of[x['id']]) for x in sub if x['id'] in route_of), None)
            metro[len(metro)] = {'line': lid, 'bridge': name, 'pts': trim(grow(sub[0], subway, 200), mid, 55), 'mid': mid}
    bridges.sort(key=lambda b: b['mid'][1])
    by_order = sorted(metro.values(), key=lambda m: m['mid'][1])
    for i, m in enumerate(by_order):
        m['how'] = 'route relation' if m['line'] else 'order from north'
        m['line'] = m['line'] or ('M1', 'M3')[min(i, 1)]
    marks, missing = landmarks(P)

    # label anchors: the middle of each bank inside the city, and a spot on the river
    coarse_city = [dp_ring(r, 4) for r in city_outer]

    obstacles = [(m['x'], m['y']) for m in marks]  # city edge, river and landmarks, every 10 units
    for r, closed in [(r, True) for r in coarse_city] + [(dp(line, 2), False)]:
        for a, b in zip(r, r[1:] + r[:1] if closed else r[1:]):
            n = max(1, int(math.dist(a, b) // 10))
            obstacles += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]

    def anchor(region):
        # the spot of the bank inside the city farthest from its edge, the river and the landmarks
        grid = [(x + 7.5, y + 7.5) for x in range(0, int(W), 15) for y in range(0, int(H), 15)]
        pts = [p for p in grid if inside(p, [region]) and inside(p, coarse_city)]
        return max(pts, key=lambda p: min(math.dist(p, o) for o in obstacles))
    aw, ae = anchor(west0), anchor(east0)
    k = min(range(len(line)), key=lambda i: abs(line[i][1] - H * 0.66))
    a, b = line[max(0, k - 3)], line[min(len(line) - 1, k + 3)]
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    ang = ang - 180 if ang > 90 else ang + 180 if ang < -90 else ang

    def render(tol):
        cl = dp(line, tol)
        west, east = regions(cl)
        rnd = lambda p: [round(p[0], 1), round(p[1], 1)]
        return {
            'viewBox': [0, 0, int(W), round(H, 1)],
            'projection': {'type': 'equirectangular', 'lon_min': round(P.lon_min, 6), 'lat_max': round(P.lat_max, 6),
                           'lat_mean': round(P.lat_mean, 6), 'cos_lat': round(P.cos, 8), 'scale': round(P.scale, 4),
                           'x': '(lon - lon_min) * cos_lat * scale', 'y': '(lat_max - lat) * scale'},
            'fill_rule': 'nonzero',
            'paths': {'city': path_rings([dp_ring(r, tol) for r in city]),
                      'water': path_rings([dp_ring(r, tol) for r in water]),
                      'islands': path_rings([dp_ring(r, tol) for r in islands]),
                      'centreline': path_pts(cl, False),
                      'west': path_rings([west]), 'east': path_rings([east])},
            'bridges': [{'id': b['id'], 'name': b['name'], 'kind': b['kind'], 'carries': b['carries'],
                         'path': path_pts(dp(b['pts'], 0.3), False), 'mid': rnd(b['mid']), 'lat': b['lat'],
                         'order': i + 1, **({'construction': True} if b.get('construction') else {})}
                        for i, b in enumerate(bridges)],
            'metro': {m['line']: {'bridge': m['bridge'], 'path': path_pts(dp(m['pts'], 0.3), False),
                                  'mid': rnd(m['mid']), 'line_from': m['how']} for m in by_order},
            'lines': {lid: ''.join(path_pts(dp(r, max(tol, 0.5)), False) for r in rs) for lid, rs in routes.items()},
            'landmarks': marks,
            'labels': {'banks': [{'id': 'west', 'text': 'Правий берег', 'x': round(aw[0], 1), 'y': round(aw[1], 1)},
                                 {'id': 'east', 'text': 'Лівий берег', 'x': round(ae[0], 1), 'y': round(ae[1], 1)}],
                       'river': {'text': 'Дніпро', 'x': round(line[k][0], 1), 'y': round(line[k][1], 1),
                                 'angle': round(ang, 1)},
                       'islands': island_labels},
            'attribution': ATTRIBUTION,
            'fetched': meta['fetched'],
            'osm_base': meta['queries']['boundary'].get('osm_base'),
            'simplify_tolerance': tol,
            'source': 'OpenStreetMap via Overpass API, scripts/site/kyiv_map.py',
        }

    for tol in (0.35, 0.5, 0.7, 1.0, 1.4, 2.0, 3.0):
        doc = render(tol)
        text = json.dumps(doc, ensure_ascii=False, separators=(',', ':'))
        if len(text.encode()) < MAX_BYTES - 5000:
            break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text + '\n')
    pc = lambda s: s.count('M') + s.count('L')
    ps = doc['paths']
    print(f"{OUT.relative_to(ROOT)}: {len(text.encode())} bytes, tolerance {tol}, viewBox {doc['viewBox']}, "
          f"OSM data {doc['osm_base']}, fetched {doc['fetched']}")
    print(f"city: {ps['city'].count('M')} rings, {pc(ps['city'])} points; water: {ps['water'].count('M')} rings, "
          f"{pc(ps['water'])} points; islands: {ps['islands'].count('M')}; centreline: {pc(ps['centreline'])} points")
    print(f'bridges over the Dnipro from north to south: {len(bridges)}')
    for b, item in zip(doc['bridges'], bridges):
        print(f"  {b['order']}. {b['name']} ({b['id']}): {b['kind']}, carries {'+'.join(b['carries'])}, "
              f"lat {b['lat']}{', construction' if b.get('construction') else ''}, "
              f"{'from bank to bank' if item['banks'] else 'AN END OFF THE BANK'}, "
              f"straight parts {item['straight']:.1f}")
    for k2, m in doc['metro'].items():
        print(f"metro {k2}: crosses on {m['bridge']} (line from {m['line_from']})")
    print('metro lines: ' + ', '.join(f"{k2} {v.count('M')} strokes, {pc(v)} points" for k2, v in doc['lines'].items()))
    print(f"landmarks: {len(marks)}; " + '; '.join(f"{m['name']} {m['lat']},{m['lon']} ({m['osm']})" for m in marks))
    print('not found in OSM: ' + (', '.join(missing) if missing else 'none'))
    print(f"labels: banks {doc['labels']['banks']}; islands {[i['name'] for i in island_labels]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fetch', action='store_true', help='download the raw OSM data first (network)')
    args = ap.parse_args()
    if args.fetch:
        fetch()
    build()


if __name__ == '__main__':
    main()
