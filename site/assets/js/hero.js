// The crossing picture of tab 1 "Відповідь" (#hero-map): a live line map of the part of Kyiv where people cross the
// Dnipro, from Північний міст to Південний. Geometry: site/data/kyiv_map.json (OpenStreetMap, scripts/site/kyiv_map.py);
// line symbols: assets/img/sprites.svg. The right bank and the left bank are two soft tints with the river and its
// islands between them; the 7 bridges take the status colour of the road traffic on them now (crossing.js: green open,
// amber limited, red closed); the metro lines M1, M2, M3 run in their own colours, and a line that cannot cross now
// dims over the river and gets a stop mark. Quiet extras: a few landmarks (names on hover or tap), the sun or the moon
// by Kyiv time, drones toward Kyiv when the risk is high, a ballistic streak at the red level, a cloud when it is calm.
// The trick: the M1 train crosses the Metro bridge on a click or the key T; in an alert it rolls to the bank, stops and
// goes back, like the real red line. dashboard.js calls mountHero(el, data), then update(data) on new data and train()
// on the key T. If the map file does not load, mountHero gives null and the small picture of index.html stays.
// Motion: transform and opacity only, set each frame; with prefers-reduced-motion nothing flies or loops and every
// effect shows its end state at once.

import { crossingsFor } from './crossing.js'

const NS = 'http://www.w3.org/2000/svg'
const SPRITES = 'assets/img/sprites.svg'
const MAP_URL = 'data/kyiv_map.json'
const RM = window.matchMedia('(prefers-reduced-motion: reduce)')

// The viewBox of each symbol in sprites.svg: x, y, width, height.
const SYM = {
  motherland: [4.5, -1.5, 41, 103], lavra: [0.5, -0.5, 39, 102], andriivska: [-0.5, 0.5, 81, 72],
  sophia: [-1.5, -0.5, 103, 74], 'golden-gate': [-0.5, -3.5, 81, 68], 'tv-tower': [-4, 0, 48, 163],
  'freedom-arch': [0.5, 5.5, 79, 42.5], shahed: [5.5, 11, 58.5, 42], 'ballistic-missile': [1, 0, 96, 28],
  'interceptor-burst': [5, 5, 54, 54], chestnut: [12.5, 12.5, 44.5, 46.5], 'metro-train': [-2.5, 2.5, 105, 32.5],
  cloud: [10.5, 6.5, 47.5, 29], moon: [10.5, 7.5, 48, 44], sun: [7.5, 7.5, 49, 49],
}
// Landmarks of kyiv_map.json: symbol and height in px, by priority. A mark that would touch an earlier one, a label
// or the edge is left out, so a phone shows fewer.
const MARKS = [
  ['motherland', 'motherland', 34], ['lavra', 'lavra', 26], ['tv_tower', 'tv-tower', 32], ['andriivska', 'andriivska', 17],
  ['arch', 'freedom-arch', 12], ['sofia', 'sophia', 15], ['golden_gate', 'golden-gate', 14],
]
// What sets the colour of each bridge (the road entry of crossing.js) and which rail line runs on it.
const ROAD = { pivnichnyi: 'bridges', podilskyi: 'podilskyi', metro: 'bridges', patona: 'bridges', darnytskyi: 'bridges', pivdennyi: 'pivdennyi' }
const ON = { metro: 'm1', pivdennyi: 'm3', darnytskyi: 'rail' }
const RIDE = { m1: 'червона M1', m3: 'зелена M3', rail: 'електричка' }
const CAR = { open: 'авто їдуть', limited: 'авто з обмеженнями', closed: 'авто стоять', unknown: 'авто: невідомо' }
const GOES = { open: 'їде', limited: 'їде з обмеженнями', closed: 'не їде' }
const PX = { label: 11.5, train: 26, drone: 22, missile: 30, cloud: 44, sun: 22, chestnut: 16, burst: 30 }
const KONAMI = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'KeyB', 'KeyA']
const HOUR = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Kyiv', hour: '2-digit', hourCycle: 'h23' })

const f = (v, d = 1) => +Number(v).toFixed(d)
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2)
const rnd = (i) => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x) }
// Still poses to try along a path: from a to b by step, the ones nearest mid first.
const span = (a, b, step, mid) => Array.from({ length: Math.round((b - a) / step) + 1 }, (_, i) => a + i * step).sort((x, y) => Math.abs(x - mid) - Math.abs(y - mid))
const upper = (t) => (t ? t[0].toUpperCase() + t.slice(1) : '')
const ride = (name, st) => (GOES[st] ? `${name} ${GOES[st]}` : `${name}: невідомо`)
const isNight = () => { const h = Number(HOUR.format(new Date())); return h >= 21 || h < 6 }

function svg(tag, attrs = {}, ...kids) {
  const n = document.createElementNS(NS, tag)
  for (const [k, v] of Object.entries(attrs)) if (v != null && v !== false) n.setAttribute(k, v)
  for (const kid of kids.flat()) if (kid != null && kid !== false) n.append(kid)
  return n
}

function html(tag, attrs = {}, text = '') {
  const n = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v)
  if (text) n.textContent = text
  return n
}

const use = (id, x, y, w, h) => svg('use', { href: `${SPRITES}#${id}`, x: f(x, 2), y: f(y, 2), width: f(w, 2), height: f(h, 2) })

// "M1,2L3,4M5,6L7,8" -> [[[1,2],[3,4]], [[5,6],[7,8]]]
function polylines(d) {
  return String(d || '').split('M').filter(Boolean)
    .map((part) => part.replace(/Z/g, '').split('L').map((p) => p.split(',').map(Number)))
    .filter((l) => l.length > 1 && l.every((p) => p.length === 2 && p.every(Number.isFinite)))
}

// Walks a polyline by the share of its length: at(t) gives the point and the heading in degrees.
function walker(pts) {
  const acc = [0]
  for (let i = 1; i < pts.length; i++) acc.push(acc[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
  const total = acc[acc.length - 1] || 1
  return {
    total,
    at(t) {
      const d = Math.max(0, Math.min(1, t)) * total
      let i = 1
      while (i < acc.length - 1 && acc[i] < d) i++
      const [ax, ay] = pts[i - 1]
      const [bx, by] = pts[i]
      const u = (d - acc[i - 1]) / ((acc[i] - acc[i - 1]) || 1)
      return { x: ax + (bx - ax) * u, y: ay + (by - ay) * u, a: (Math.atan2(by - ay, bx - ax) * 180) / Math.PI }
    },
  }
}

// Turns a symbol that points right to the heading `ang` without putting it upside down (it mirrors instead).
function pose(ang) {
  const a = ((((ang + 180) % 360) + 360) % 360) - 180
  return Math.abs(a) > 90 ? `rotate(${f(a - 180 * Math.sign(a))}) scale(-1 1)` : `rotate(${f(a)})`
}

// The part of the map to show: every bridge and both metro crossings with a margin, widened to the box's shape.
function cropOf(map, w, h) {
  const pts = []
  for (const b of map.bridges) for (const l of polylines(b.path)) pts.push(...l)
  for (const m of Object.values(map.metro || {})) for (const l of polylines(m.path)) pts.push(...l)
  const xs = pts.map((p) => p[0])
  const ys = pts.map((p) => p[1])
  const span = Math.max(...ys) - Math.min(...ys)
  let x = Math.min(...xs) - 12
  let y = Math.min(...ys) - span * 0.13
  let cw = Math.max(...xs) + 12 - x
  let ch = span * 1.22
  const ar = w / h
  if (cw / ch < ar) { x -= (ch * ar - cw) / 2; cw = ch * ar } else { y -= (cw / ar - ch) / 2; ch = cw / ar }
  return { x, y, w: cw, h: ch }
}

function stateOf(data) {
  const now = data?.now
  const alert = Boolean(now?.now?.alert)
  const level = alert ? now.now.level || 'alert' : null
  const tier = now?.forecast?.tier || null
  const kyiv = (Array.isArray(now?.waves) ? now.waves : []).filter((w) => w?.kyiv).length
  return {
    alert, level, tier, red: level === 'red',
    drones: Math.min(5, Math.max(kyiv, tier === 'high' ? 2 : 0)),
    st: Object.fromEntries(crossingsFor(level).map((c) => [c.id, c])),
  }
}

// One sentence for screen readers: what crosses the river now.
function sentence(s) {
  const st = s.st
  const long = { m1: 'червона лінія M1 мостом Метро', m3: 'зелена лінія M3 Південним мостом' }
  const go = ['m1', 'm3'].filter((id) => st[id]?.status === 'open')
  const stop = ['m1', 'm3'].filter((id) => st[id]?.status === 'closed').map((id) => RIDE[id])
  const unsure = ['m1', 'm3'].filter((id) => !['open', 'closed'].includes(st[id]?.status)).map((id) => RIDE[id])
  const metro = go.length === 2 ? 'їдуть обидві лінії метро, червона M1 і зелена M3'
    : go.length ? `їде ${long[go[0]]}`
      : stop.length && unsure.length ? `${stop.join(' і ')} не їде` : stop.length ? 'метро не їде' : 'чи їде метро, невідомо'
  const lim = ['pivdennyi', 'podilskyi'].filter((id) => st[id]?.status === 'limited').map((id) => (id === 'pivdennyi' ? 'Південному' : 'Подільському'))
  return `${[`Зараз через Дніпро ${metro}`,
    go.length && stop.length ? `${stop.join(' і ')} стоїть` : '',
    stop.length && unsure.length ? `чи їде ${unsure.join(' і ')}, невідомо` : '',
    `авто їдуть мостами${lim.length ? `, на ${lim.join(' і ')} ${lim.length > 1 ? 'мостах' : 'мосту'} обмеження` : ' без обмежень'}`,
  ].filter(Boolean).join(', ')}.`
}

function bridgeText(b, st) {
  const road = st[ROAD[b.id]]
  const line = st[ON[b.id]]
  const parts = []
  if (road) parts.push(`${CAR[road.status] || CAR.unknown}${road.status === 'limited' ? ` (${road.note})` : ''}`)
  if (line) parts.push(ride(RIDE[ON[b.id]], line.status))
  return `${upper(b.name)}: ${parts.length ? parts.join(', ') : 'лише поїзди'}`
}

let mapLoad = null
function loadMap() {
  mapLoad ??= fetch(MAP_URL).then((r) => (r.ok ? r.json() : null))
    .then((m) => (m?.paths?.water && Array.isArray(m.bridges) && m.bridges.length ? m : null), () => null)
  return mapLoad.then((m) => { if (!m) mapLoad = null; return m })
}

const mounts = new WeakMap()

export function mountHero(el, data) {
  if (!el) return null
  if (!mounts.has(el)) {
    const p = loadMap().then((map) => (map ? createHero(el, map) : null))
    mounts.set(el, p)
    p.then((h) => { if (!h) mounts.delete(el) })
  }
  return mounts.get(el).then((h) => { h?.update(data); return h })
}

function createHero(el, map) {
  let state = stateOf(null)
  let vb = null
  let k = 1
  let size = ''
  let base = null
  let fly = null
  let fx = null
  let trainG = null
  let track = null
  let T = null
  let trainAt = null
  let cross = {}
  let placed = {}
  let flyers = []
  let tweens = []
  let raf = 0
  let inView = true
  let side = 0
  let facing = 1
  let busy = false
  let tipTimer = 0
  let kseq = 0
  const s = (px) => px * k
  const city = (() => {
    const pts = (map.landmarks || []).filter((m) => ['motherland', 'lavra', 'sofia', 'andriivska', 'golden_gate', 'arch'].includes(m.id))
    return pts.length ? [pts.reduce((a, m) => a + m.x, 0) / pts.length, pts.reduce((a, m) => a + m.y, 0) / pts.length] : map.metro?.M1?.mid || [500, 400]
  })()

  const tip = html('p', { class: 'hm-tip', role: 'tooltip' })
  tip.hidden = true
  const live = html('p', { class: 'sr-only', 'aria-live': 'polite' })
  const btn = html('button', { type: 'button', class: 'hm-go' })
  const osm = html('a', { class: 'hm-osm', href: 'https://www.openstreetmap.org/copyright', target: '_blank', rel: 'noopener' }, '© OpenStreetMap')
  el.classList.add('hm')
  el.replaceChildren(btn, tip, osm, live)

  // ---------- drawing ----------

  function build() {
    const W = el.clientWidth
    const H = el.clientHeight
    if (W < 60 || H < 40 || (`${W}x${H}` === size && base)) return false
    size = `${W}x${H}`
    vb = cropOf(map, W, H)
    k = vb.w / W
    const box = `${f(vb.x, 2)} ${f(vb.y, 2)} ${f(vb.w, 2)} ${f(vb.h, 2)}`
    const defs = svg('defs', {},
      svg('linearGradient', { id: 'hm-sky', x1: 0, y1: 0, x2: 0, y2: 1 }, svg('stop', { offset: 0, class: 'hm-sky-a' }), svg('stop', { offset: 1, class: 'hm-sky-b' })))
    const label = (text, x, y, anchor) => svg('text', { class: 'hm-label', x: f(x, 2), y: f(y, 2), 'text-anchor': anchor, 'font-size': f(s(PX.label), 2) }, text)

    const bridges = svg('g', { class: 'hm-bridges' })
    for (const b of map.bridges) {
      const hit = svg('path', { class: 'hm-hit', d: b.path })
      bridges.append(svg('g', { class: 'hm-bridge', 'data-id': b.id }, svg('path', { class: 'hm-deck-case', d: b.path }), svg('path', { class: 'hm-deck', d: b.path }), hit))
      hint(hit, () => bridgeText(b, state.st), () => ({ x: b.mid[0], y: b.mid[1] - s(5) }))
    }
    const lines = svg('g', { class: 'hm-lines' })
    for (const id of ['M2', 'M3', 'M1']) {
      const d = map.lines?.[id] || map.metro?.[id]?.path
      if (!d) continue
      lines.append(svg('g', { class: `hm-route hm-${id}` },
        svg('g', { class: 'hm-full' }, svg('path', { class: 'hm-line-case', d }), svg('path', { class: 'hm-line', d })),
        id === 'M2' ? null : svg('g', { class: 'hm-cut', 'clip-path': `url(#hm-in-${id})`, style: 'display:none' }, svg('path', { class: 'hm-line', d }))))
    }

    // The bank labels go to the spot with the fewest metro line points and bridges under them (boxes in px).
    const dots = map.bridges.map((b) => [(b.mid[0] - vb.x) / k, (b.mid[1] - vb.y) / k])
    for (const id of ['M1', 'M2', 'M3']) {
      for (const l of polylines(map.lines?.[id] || map.metro?.[id]?.path)) {
        for (let i = 1; i < l.length; i++) {
          const n = Math.ceil(Math.hypot(l[i][0] - l[i - 1][0], l[i][1] - l[i - 1][1]) / 2)
          for (let j = 0; j < n; j++) dots.push([(l[i - 1][0] + ((l[i][0] - l[i - 1][0]) * j) / n - vb.x) / k, (l[i - 1][1] + ((l[i][1] - l[i - 1][1]) * j) / n - vb.y) / k])
        }
      }
    }
    const under = (bx) => dots.filter(([x, y]) => x > bx[0] - 3 && x < bx[2] + 3 && y > bx[1] - 3 && y < bx[3] + 3).length
    const spot = (text, west, fys) => {
      const tw = text.length * PX.label * 0.56
      return fys.map((fy) => (west ? [12, H * fy - 10, 12 + tw, H * fy + 3] : [W - 12 - tw, H * fy - 10, W - 12, H * fy + 3]))
        .reduce((a, b) => (under(b) < under(a) ? b : a))
    }
    const wb = spot('правий берег', true, [0.95, 0.5, 0.62, 0.74, 0.86, 0.4])
    const eb = spot('лівий берег', false, [0.34, 0.26, 0.44, 0.56, 0.66])
    const labels = svg('g', { class: 'hm-labels' },
      label('правий берег', vb.x + s(wb[0]), vb.y + s(wb[3] - 3), 'start'),
      label('лівий берег', vb.x + s(eb[2]), vb.y + s(eb[3] - 3), 'end'))
    const taken = [[0, 0, PX.sun + 20, PX.sun + 16], wb, eb, [W - 112, H - 24, W, H]]
    const rl = riverLabel()
    if (rl) {
      const t = svg('text', { class: 'hm-label hm-river', x: f(rl.x, 2), y: f(rl.y, 2), 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': f(s(PX.label - 1), 2), transform: `rotate(${f(rl.a)} ${f(rl.x, 2)} ${f(rl.y, 2)})` }, 'Дніпро')
      t.addEventListener('click', boat)
      labels.append(t)
      const px = (rl.x - vb.x) / k
      const py = (rl.y - vb.y) / k
      const rad = (rl.a * Math.PI) / 180
      const hw = Math.abs(Math.cos(rad)) * 21 + Math.abs(Math.sin(rad)) * 7
      const hh = Math.abs(Math.sin(rad)) * 21 + Math.abs(Math.cos(rad)) * 7
      taken.push([px - hw, py - hh, px + hw, py + hh])
    }

    const marks = svg('g', { class: 'hm-marks' })

    const sz = s(PX.sun)
    const stars = [[0.2, 0.05], [0.31, 0.11], [0.45, 0.035], [0.62, 0.075], [0.79, 0.03], [0.9, 0.1]]
    const sky = svg('g', { class: 'hm-sky' },
      svg('g', { class: 'hm-sun' }, use('sun', vb.x + s(10), vb.y + s(8), sz, sz)),
      svg('g', { class: 'hm-moon' }, use('moon', vb.x + s(10), vb.y + s(8), sz, (sz * 44) / 48),
        stars.map(([x, y]) => svg('circle', { class: 'hm-star', cx: f(vb.x + vb.w * x, 2), cy: f(vb.y + vb.h * y, 2), r: f(s(1), 2) }))))
    const stops = svg('g', { class: 'hm-stops' })
    const nb = svg('svg', { class: 'hm-svg hm-base', viewBox: box, role: 'img', 'aria-label': sentence(state), focusable: 'false' },
      defs,
      svg('g', { class: 'hm-land' },
        svg('path', { class: 'hm-west', d: map.paths.west }), svg('path', { class: 'hm-east', d: map.paths.east }),
        svg('path', { class: 'hm-water', d: map.paths.water }), svg('path', { class: 'hm-isle', d: map.paths.islands })),
      svg('rect', { class: 'hm-sky-band', x: f(vb.x, 2), y: f(vb.y, 2), width: f(vb.w, 2), height: f(vb.h * 0.17, 2), fill: 'url(#hm-sky)' }),
      bridges, lines, stops, marks, labels, sky)

    fly = svg('g', { class: 'hm-fly' })
    fx = svg('g', { class: 'hm-fx' })
    const tw = PX.train
    trainG = svg('g', { class: 'hm-train' },
      svg('rect', { class: 'hm-train-bg', x: -tw / 2 - 0.5, y: -4.6, width: tw + 1, height: 9.2, rx: 3.2 }),
      use('metro-train', -tw / 2, (-tw * 32.5) / 105 / 2, tw, (tw * 32.5) / 105))
    const no = svg('svg', { class: 'hm-svg hm-over', viewBox: box, 'aria-hidden': 'true', focusable: 'false' },
      svg('defs', {},
        svg('linearGradient', { id: 'hm-trail', x1: 0, y1: 0, x2: 1, y2: 0 }, svg('stop', { offset: 0, class: 'hm-trail-a' }), svg('stop', { offset: 1, class: 'hm-trail-b' })),
        svg('filter', { id: 'hm-blur', x: '-100%', y: '-100%', width: '300%', height: '300%' }, svg('feGaussianBlur', { stdDeviation: 2.4 }))),
      fly, trainG, fx)
    for (const old of el.querySelectorAll(':scope > .hm-svg')) old.remove()
    base = nb
    el.prepend(base, no)

    // The river segment of M1 and M3: the part of the line over the water near its bridge, found on the drawn water.
    cross = {}
    for (const id of ['M1', 'M3']) {
      const c = crossing(id)
      if (!c) continue
      cross[id] = c
      const big = `M${f(vb.x - 60)},${f(vb.y - 60)}h${f(vb.w + 120)}v${f(vb.h + 120)}h${f(-vb.w - 120)}Z`
      const r = f(c.r, 2)
      const ring = `M${f(c.cx - c.r, 2)},${f(c.cy, 2)}a${r},${r} 0 1 0 ${f(2 * c.r, 2)},0a${r},${r} 0 1 0 ${f(-2 * c.r, 2)},0Z`
      defs.append(svg('clipPath', { id: `hm-out-${id}` }, svg('path', { d: big + ring, 'clip-rule': 'evenodd' })),
        svg('clipPath', { id: `hm-in-${id}` }, svg('circle', { cx: f(c.cx, 2), cy: f(c.cy, 2), r })))
      stops.append(svg('g', { class: 'hm-stop', 'data-line': id, transform: `translate(${f(c.cx, 2)} ${f(c.cy, 2)}) scale(${f(k, 4)})`, style: 'display:none' },
        svg('circle', { r: 5.5 }), svg('rect', { x: -3.3, y: -1, width: 6.6, height: 2, rx: 0.7 })))
    }
    // The train waits on M1 a little before the water on either bank.
    T = null
    track = cross.M1?.walk || null
    if (track) {
      const c = cross.M1
      const dir = c.A.x <= c.B.x ? 1 : -1 // 1 when the share t grows toward the east
      const back = s(30) / track.total
      const half = s(PX.train / 2 + 2) / track.total
      const [tw0, te0] = dir > 0 ? [c.ta, c.tb] : [c.tb, c.ta]
      const clamp = (t) => Math.max(0.005, Math.min(0.995, t))
      T = { w: clamp(tw0 - dir * back), e: clamp(te0 + dir * back), ew: tw0 - dir * half, ee: te0 + dir * half, dir }
    }
    placeMarks(marks, taken, W, H)
    btn.hidden = !T
    return true
  }

  function crossing(id) {
    const mid = map.metro?.[id]?.mid
    const all = polylines(map.lines?.[id] || map.metro?.[id]?.path)
    if (!mid || !all.length) return null
    const near = (l) => Math.min(...l.map((p) => Math.hypot(p[0] - mid[0], p[1] - mid[1])))
    const walk = walker(all.reduce((a, b) => (near(b) < near(a) ? b : a)))
    const water = base.querySelector('.hm-water')
    const n = Math.max(60, Math.ceil(walk.total))
    let ta = null
    let tb = null
    let tm = 0
    let dm = Infinity
    for (let i = 0; i <= n; i++) {
      const t = i / n
      const p = walk.at(t)
      const d = Math.hypot(p.x - mid[0], p.y - mid[1])
      if (d < dm) { dm = d; tm = t }
      if (d > 45) continue
      let wet = false
      try { wet = water.isPointInFill(new DOMPoint(p.x, p.y)) } catch { wet = false }
      if (wet) { if (ta == null) ta = t; tb = t }
    }
    if (ta == null) { ta = tm - 14 / walk.total; tb = tm + 14 / walk.total }
    const A = walk.at(ta)
    const B = walk.at(tb)
    return { walk, ta, tb, A, B, cx: (A.x + B.x) / 2, cy: (A.y + B.y) / 2, r: Math.hypot(B.x - A.x, B.y - A.y) / 2 + s(3) }
  }

  // Landmarks stand next to their real spot on its own bank, never on a metro line, a bridge, the water, a stop mark or
  // the stretch of M1 where the train rides: each takes the free place closest to its point within 30 px, or is left out.
  function placeMarks(marks, taken, W, H) {
    placed = {}
    const keep = [] // points to keep clear, in px: x, y and the clearance
    const at = (x, y, r) => keep.push([(x - vb.x) / k, (y - vb.y) / k, r])
    const trace = (d, r) => {
      for (const l of polylines(d)) {
        for (let i = 1; i < l.length; i++) {
          const [x0, y0] = l[i - 1]
          const [x1, y1] = l[i]
          const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / s(2)))
          for (let j = 0; j <= n; j++) at(x0 + ((x1 - x0) * j) / n, y0 + ((y1 - y0) * j) / n, r)
        }
      }
    }
    for (const id of ['M1', 'M2', 'M3']) trace(map.lines?.[id] || map.metro?.[id]?.path, 6)
    for (const b of map.bridges) trace(b.path, 10)
    for (const c of Object.values(cross)) at(c.cx, c.cy, 10)
    if (T) {
      const pad = s(PX.train / 2 + 4) / track.total
      const lo = Math.min(T.w, T.e) - pad
      const hi = Math.max(T.w, T.e) + pad
      const n = Math.ceil(((hi - lo) * track.total) / s(2))
      for (let i = 0; i <= n; i++) { const p = track.at(lo + ((hi - lo) * i) / n); at(p.x, p.y, 13) }
      for (const t of [T.w, T.e]) { const p = track.at(t); at(p.x, p.y, 18) } // the train button
    }
    const inside = (sel) => {
      const n = base.querySelector(sel)
      return (x, y) => { try { return Boolean(n?.isPointInFill(new DOMPoint(vb.x + x * k, vb.y + y * k))) } catch { return false } }
    }
    const wet = inside('.hm-water')
    const isle = inside('.hm-isle')
    const west = inside('.hm-west')
    const clear = (c, pts) => !pts.some(([x, y, r]) => {
      const dx = Math.max(c[0] - x, 0, x - c[2])
      const dy = Math.max(c[1] - y, 0, y - c[3])
      return dx * dx + dy * dy < r * r
    })
    const offs = []
    for (let dx = -30; dx <= 30; dx += 2) for (let dy = -30; dy <= 30; dy += 2) if (dx * dx + dy * dy <= 900) offs.push([dx, dy])
    offs.sort((a, b) => a[0] ** 2 + a[1] ** 2 - b[0] ** 2 - b[1] ** 2)
    for (const [id, sym, hp] of MARKS) {
      if (Object.keys(placed).length >= (W < 420 ? 4 : MARKS.length)) break // a phone keeps it quiet
      const m = (map.landmarks || []).find((x) => x.id === id)
      if (!m) continue
      const [, , sw, sh] = SYM[sym]
      const wp = (hp * sw) / sh
      const mx = (m.x - vb.x) / k
      const my = (m.y - vb.y) / k
      const bank = west(mx, my)
      const near = keep.filter(([x, y, r]) => Math.abs(x - mx) < 32 + wp / 2 + r && y > my - 32 - hp - r && y < my + 32 + r)
      let spot = null
      for (const [dx, dy] of offs) {
        const px = mx + dx
        const py = my + dy
        const c = [px - wp / 2 + 1, py - hp + 1, px + wp / 2 - 1, py - 1] // line art: the outer pixel may touch
        if (c[0] < 4 || c[1] < 4 || c[2] > W - 4 || c[3] > H - 4) continue
        if (taken.some((t) => c[0] - 5 < t[2] && c[2] + 5 > t[0] && c[1] - 5 < t[3] && c[3] + 5 > t[1])) continue // 3 px apart
        if (!clear(c, near) || west(px, py - 1) !== bank || isle(px, py - 1)) continue
        if (wet(px, py - 1) || wet(c[0], py - 1) || wet(c[2], py - 1) || wet(px, py - hp / 2)) continue
        spot = { px, py, c }
        break
      }
      if (!spot) continue
      taken.push(spot.c)
      const wu = s(wp)
      const hu = s(hp)
      const x = vb.x + spot.px * k
      const y = vb.y + spot.py * k
      placed[id] = { x, y, wu, hu }
      const g = svg('g', { class: 'hm-mark', 'data-id': id, transform: `translate(${f(x, 2)} ${f(y, 2)})` },
        use(sym, -wu / 2, -hu, wu, hu),
        svg('rect', { class: 'hm-mark-hit', x: f(-wu / 2 - s(3), 2), y: f(-hu - s(3), 2), width: f(wu + s(6), 2), height: f(hu + s(6), 2) }))
      hint(g, () => m.name, () => ({ x, y: y - hu }), () => (id === 'motherland' ? glow() : id === 'arch' ? rainbow() : null))
      marks.append(g)
    }
  }

  // "Дніпро" along the river, in a wide gap between two bridges away from the landmarks.
  function riverLabel() {
    const line = polylines(map.paths.centreline)[0]
    if (!line) return null
    const onLine = (at) => {
      for (let i = 1; i < line.length; i++) {
        const [x0, y0] = line[i - 1]
        const [x1, y1] = line[i]
        if ((y0 - at) * (y1 - at) > 0 || y0 === y1) continue
        const a = line[Math.max(0, i - 3)]
        const b = line[Math.min(line.length - 1, i + 2)]
        let ang = (Math.atan2(b[1] - a[1], b[0] - a[0]) * 180) / Math.PI
        if (ang > 90) ang -= 180
        if (ang < -90) ang += 180
        return { x: x0 + ((x1 - x0) * (at - y0)) / (y1 - y0), y: at, a: ang }
      }
      return null
    }
    const ys = map.bridges.map((b) => b.mid[1]).sort((a, b) => a - b)
    let best = null
    for (let i = 1; i < ys.length; i++) {
      const gap = ys[i] - ys[i - 1]
      const p = gap >= 36 ? onLine((ys[i] + ys[i - 1]) / 2) : null
      if (!p) continue
      const score = gap / 2 + Math.min(60, ...(map.landmarks || []).map((m) => Math.hypot(m.x - p.x, m.y - p.y)))
      if (!best || score > best.score) best = { ...p, score }
    }
    return best
  }

  function paint() {
    if (!base) return
    base.setAttribute('aria-label', sentence(state))
    base.classList.toggle('is-night', isNight())
    for (const g of base.querySelectorAll('.hm-bridge')) {
      const road = state.st[ROAD[g.dataset.id]]
      g.setAttribute('class', `hm-bridge is-${road ? road.status : 'rail'}`)
    }
    for (const id of ['M1', 'M3']) {
      const closed = state.st[id.toLowerCase()]?.status === 'closed' && Boolean(cross[id])
      const route = base.querySelector(`.hm-route.hm-${id}`)
      const full = route?.querySelector('.hm-full')
      if (full && closed) full.setAttribute('clip-path', `url(#hm-out-${id})`)
      else if (full) full.removeAttribute('clip-path')
      const cut = route?.querySelector('.hm-cut')
      if (cut) cut.style.display = closed ? '' : 'none'
      const mark = base.querySelector(`.hm-stop[data-line="${id}"]`)
      if (mark) mark.style.display = closed ? '' : 'none'
    }
    btn.setAttribute('aria-label', trainText())
    if (T && !busy) { placeTrain(side ? T.e : T.w, 0); moveBtn() }
    setFlyers()
  }

  // ---------- tooltips ----------

  function hint(node, text, at, act) {
    node.addEventListener('pointerenter', () => showTip(text(), at()))
    node.addEventListener('pointerleave', hideTip)
    node.addEventListener('click', () => { showTip(text(), at(), 2600); act?.() })
  }

  function showTip(text, p, ms = 0) {
    if (!vb || !p) return
    tip.textContent = text
    tip.hidden = false
    const W = el.clientWidth
    const H = el.clientHeight
    const px = (p.x - vb.x) / k
    const py = (p.y - vb.y) / k
    const tw = tip.offsetWidth
    const th = tip.offsetHeight
    const top = py - th - 10 >= 6 ? py - th - 10 : Math.min(H - th - 6, py + 14)
    tip.style.left = `${Math.round(Math.max(6, Math.min(W - tw - 6, px - tw / 2)))}px`
    tip.style.top = `${Math.round(Math.max(6, top))}px`
    clearTimeout(tipTimer)
    if (ms) tipTimer = setTimeout(hideTip, ms)
  }

  function hideTip() {
    clearTimeout(tipTimer)
    tip.hidden = true
  }

  // ---------- motion ----------

  function loop(now) {
    raf = 0
    if (!RM.matches) for (const fl of flyers) fl.frame(now)
    for (const fn of tweens.slice()) fn(now)
    kick()
  }

  function kick() {
    if (raf || document.hidden || !inView) return
    if (tweens.length || (flyers.length && !RM.matches)) raf = requestAnimationFrame(loop)
  }

  function tween(ms, step, done) {
    const t0 = performance.now()
    const fn = (now) => {
      const p = Math.min(1, Math.max(0, (now - t0) / ms))
      step(p)
      if (p >= 1) { tweens = tweens.filter((x) => x !== fn); done?.() }
    }
    tweens.push(fn)
    kick()
  }

  function fade(g) {
    if (RM.matches || !g.animate) { g.remove(); return }
    g.animate([{ opacity: g.style.opacity || 1 }, { opacity: 0 }], { duration: 320, easing: 'ease-out' }).onfinish = () => g.remove()
  }

  function pulse(g, ms) {
    fx.append(g)
    if (RM.matches || !g.animate) { setTimeout(() => g.remove(), ms); return }
    g.animate([{ opacity: 0 }, { opacity: 1, offset: 0.2 }, { opacity: 1, offset: 0.75 }, { opacity: 0 }], { duration: ms, easing: 'ease-in-out', fill: 'both' })
      .onfinish = () => g.remove()
  }

  // ---------- what flies ----------

  function setFlyers() {
    if (!fly) return
    fly.replaceChildren()
    flyers = []
    for (let i = 0; i < state.drones; i++) flyers.push(drone(i, state.drones))
    if (state.red) flyers.push(missile())
    if (!state.drones && !state.alert) flyers.push(cloud())
    if (RM.matches) hold(flyers)
    else for (const fl of flyers) fl.frame(performance.now())
    kick()
  }

  // Reduced motion: each flyer stands still at the first spot of its path that covers no label, landmark, sun or moon,
  // the train, the link or an earlier flyer (screen boxes with 2 px of air). A missile with no such spot drops its
  // trail; a flyer that still finds none is left out.
  function hold(list) {
    // A use counts by its own x, y, width and height, so it has its box before the sprite file is in.
    const box = (n) => {
      const m = n.tagName === 'use' && n.getScreenCTM()
      if (!m) return n.getBoundingClientRect()
      const [x, y, w, h] = ['x', 'y', 'width', 'height'].map((k) => n[k].baseVal.value)
      const p = [[x, y], [x + w, y], [x, y + h], [x + w, y + h]].map(([u, v]) => new DOMPoint(u, v).matrixTransform(m))
      const r = { left: Math.min(...p.map((q) => q.x)), top: Math.min(...p.map((q) => q.y)), right: Math.max(...p.map((q) => q.x)), bottom: Math.max(...p.map((q) => q.y)) }
      return { ...r, width: r.right - r.left, height: r.bottom - r.top }
    }
    const air = (a, b) => Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left) + 2) * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) + 2)
    const taken = [...base.querySelectorAll('.hm-labels text, .hm-mark use, .hm-sky use'), trainG, ...el.querySelectorAll('a')]
      .filter(Boolean).map(box).filter((r) => r.width && r.height)
    const shown = (fl) => fl.parts.filter((n) => n.style.display !== 'none').map(box).filter((r) => r.width)
    const clear = (fl) => fl.times.find((t) => { fl.frame(t); return shown(fl).every((a) => taken.every((b) => !air(a, b))) })
    for (const fl of list) {
      let t = clear(fl)
      if (t == null && fl.parts.length > 1) { fl.parts[0].style.display = 'none'; t = clear(fl) }
      if (t == null) { fl.g.style.display = 'none'; continue }
      fl.frame(t)
      taken.push(...shown(fl))
    }
  }

  // A shahed drifts from the north or the east edge toward the centre and fades before it gets there; tap it.
  function drone(i, n) {
    const r1 = rnd(i + 1)
    const r2 = rnd(i + 11)
    const from = i % 2 ? [vb.x + vb.w * (0.45 + 0.4 * r1), vb.y + s(16)] : [vb.x + vb.w - s(16), vb.y + vb.h * (0.44 + 0.3 * r1)]
    const goal = [city[0] + (r2 - 0.5) * s(70), city[1] + (r1 - 0.5) * s(50)]
    const to = [from[0] + (goal[0] - from[0]) * 0.7, from[1] + (goal[1] - from[1]) * 0.7]
    const ang = (Math.atan2(to[1] - from[1], to[0] - from[0]) * 180) / Math.PI
    const dur = 17000 + 2300 * i
    const off = (dur * i) / n + 2500
    const w = PX.drone
    const h = (w * 42) / 58.5
    const inner = svg('g', { class: 'hm-drone-in' }, svg('circle', { class: 'hm-drone-hit', r: 16 }), use('shahed', -w / 2, -h / 2, w, h))
    const g = svg('g', { class: 'hm-drone' }, inner)
    fly.append(g)
    let down = -1
    const self = {
      g, at: null, cyc: 0, o: 0,
      frame(now) {
        const q = now + off
        const p = (q % dur) / dur
        self.cyc = Math.floor(q / dur)
        self.at = { x: from[0] + (to[0] - from[0]) * p, y: from[1] + (to[1] - from[1]) * p }
        self.o = self.cyc === down ? 0 : p < 0.12 ? p / 0.12 : p > 0.84 ? (1 - p) / 0.16 : 1
        g.setAttribute('transform', `translate(${f(self.at.x, 2)} ${f(self.at.y, 2)}) ${pose(ang)} scale(${f(k, 4)})`)
        inner.style.opacity = f(self.o, 3)
      },
      parts: [inner.querySelector('use')],
      times: [0.35 + 0.3 * rnd(i + 5), ...span(0.15, 0.81, 0.03, 0.5)].map((x) => dur * (10 + x) - off),
    }
    g.addEventListener('click', () => {
      if (self.o < 0.2 || !self.at) return
      burst(self.at)
      down = self.cyc
      if (RM.matches) inner.style.opacity = 0
    })
    return self
  }

  // The red level: a ballistic missile streaks in from the north-east every few seconds.
  function missile() {
    const from = [vb.x + vb.w - s(24), vb.y + s(18)]
    const to = [vb.x + vb.w * 0.6, vb.y + vb.h * 0.62]
    const ang = (Math.atan2(to[1] - from[1], to[0] - from[0]) * 180) / Math.PI
    const dur = 7000
    const go = 1400
    const off = 2200
    const w = PX.missile
    const h = (w * 28) / 96
    const tl = RM.matches ? 30 : 58
    const inner = svg('g', {},
      svg('rect', { class: 'hm-trail', x: -w / 2 - tl + 2, y: -1, width: tl, height: 2, rx: 1, fill: 'url(#hm-trail)' }),
      use('ballistic-missile', -w / 2, -h / 2, w, h))
    const g = svg('g', { class: 'hm-missile' }, inner)
    fly.append(g)
    const self = {
      frame(now) {
        const q = (now + off) % dur
        const p = Math.min(1, q / go)
        const e = p ** 1.6
        g.setAttribute('transform', `translate(${f(from[0] + (to[0] - from[0]) * e, 2)} ${f(from[1] + (to[1] - from[1]) * e, 2)}) ${pose(ang)} scale(${f(k, 4)})`)
        inner.style.opacity = f(q > go ? 0 : p < 0.15 ? p / 0.15 : p > 0.75 ? (1 - p) / 0.25 : 1, 3)
      },
      g,
      parts: [...inner.children],
      times: span(0.16, 0.74, 0.02, 0.55).map((p) => go * p - off + dur * 10),
    }
    return self
  }

  // Calm: one cloud drifts across, slowly.
  function cloud() {
    const w = PX.cloud
    const h = (w * 29) / 47.5
    const y = vb.y + vb.h * 0.1
    const x0 = vb.x + s(36)
    const x1 = vb.x + vb.w - s(36 + w)
    const dur = 60000
    const off = 21000
    const inner = svg('g', {}, use('cloud', 0, -h / 2, w, h))
    const g = svg('g', { class: 'hm-cloud' }, inner)
    fly.append(g)
    const self = {
      frame(now) {
        const p = ((now + off) % dur) / dur
        g.setAttribute('transform', `translate(${f(x0 + (x1 - x0) * p, 2)} ${f(y, 2)}) scale(${f(k, 4)})`)
        inner.style.opacity = f(p < 0.1 ? p / 0.1 : p > 0.9 ? (1 - p) / 0.1 : 1, 3)
      },
      g,
      parts: [...inner.children],
      times: span(0.1, 0.9, 0.05, 0.3).map((p) => dur * (10 + p) - off),
    }
    return self
  }

  // ---------- the train trick ----------

  function placeTrain(t, toward) {
    if (!track || !trainG) return
    const p = track.at(t)
    if (toward) facing = toward
    const east = T.dir > 0 ? p.a : p.a + 180
    trainG.setAttribute('transform', `translate(${f(p.x, 2)} ${f(p.y, 2)}) ${pose(facing > 0 ? east : east + 180)} scale(${f(k, 4)})`)
    trainAt = p
  }

  function moveBtn() {
    if (!T || !vb) return
    const p = track.at(side ? T.e : T.w)
    btn.style.left = `${f((p.x - vb.x) / k)}px`
    btn.style.top = `${f((p.y - vb.y) / k)}px`
  }

  function trainText() {
    const m1 = state.st.m1
    if (!m1) return 'Потяг червоної лінії: натисни або T.'
    const open = m1.status === 'open'
    return `${m1.name}, ${m1.via}: ${open ? 'їде' : m1.status === 'closed' ? 'не їде' : 'невідомо'}. Натисни або T: ${open ? 'потяг перетне Дніпро.' : 'подивись, що робить потяг.'}`
  }

  function say(text) {
    live.textContent = text
    if (trainAt) showTip(text, { x: trainAt.x, y: trainAt.y - s(8) }, 2600)
  }

  function train() {
    if (!T || busy) return
    if (state.st.m1?.status !== 'open') {
      say('Тривога: червона лінія не виходить на міст і повертається під землю.')
      if (RM.matches) return
      busy = true
      const home = side ? T.e : T.w
      const edge = side ? T.ee : T.ew
      const out = side ? -1 : 1
      tween(1000, (p) => placeTrain(home + (edge - home) * ease(p), out), () =>
        setTimeout(() => tween(1000, (p) => placeTrain(edge + (home - edge) * ease(p), 0), () => { busy = false }), 700))
      return
    }
    side = 1 - side
    say(side ? 'Потяг на лівому березі. Ще раз, і він повернеться.' : 'Потяг знову на правому березі.')
    const a = side ? T.w : T.e
    const b = side ? T.e : T.w
    const to = side ? 1 : -1
    if (RM.matches) { placeTrain(b, to); moveBtn(); return }
    busy = true
    tween(2400, (p) => placeTrain(a + (b - a) * ease(p), to), () => { busy = false; moveBtn() })
  }

  btn.addEventListener('click', () => train())
  btn.addEventListener('pointerenter', () => trainAt && showTip(trainText(), { x: trainAt.x, y: trainAt.y - s(8) }))
  btn.addEventListener('pointerleave', () => { if (document.activeElement !== btn) hideTip() })
  btn.addEventListener('focus', () => trainAt && showTip(trainText(), { x: trainAt.x, y: trainAt.y - s(8) }))
  btn.addEventListener('blur', hideTip)

  // ---------- easter eggs ----------

  function burst(p) {
    const n = PX.burst
    const inner = svg('g', {}, use('interceptor-burst', -n / 2, -n / 2, n, n))
    const g = svg('g', { class: 'hm-burst', transform: `translate(${f(p.x, 2)} ${f(p.y, 2)}) scale(${f(k, 4)})` }, inner)
    fx.append(g)
    showTip('Мінус один. Дякуємо ППО.', { x: p.x, y: p.y - s(14) }, 1800)
    if (RM.matches || !inner.animate) { setTimeout(() => g.remove(), 900); return }
    inner.animate([{ transform: 'scale(.3)', opacity: 1 }, { transform: 'scale(1.25)', opacity: 0 }], { duration: 700, easing: 'cubic-bezier(.22,.75,.28,1)' })
      .onfinish = () => g.remove()
  }

  function glow() {
    const m = placed.motherland
    if (!m) return
    const [sx, sy, , sh] = SYM.motherland
    const sc = m.hu / sh
    pulse(svg('g', { class: 'hm-glow', transform: `translate(${f(m.x - m.wu / 2 + (31.2 - sx) * sc, 2)} ${f(m.y - m.hu + (45 - sy) * sc, 2)}) scale(${f(k, 4)})` },
      svg('ellipse', { class: 'hm-glow-soft', rx: 6, ry: 8, filter: 'url(#hm-blur)' }),
      svg('ellipse', { class: 'hm-glow-core', rx: 2.2, ry: 3 })), 2000)
  }

  function rainbow() {
    const m = placed.arch
    if (!m) return
    const [sx, sy, , sh] = SYM['freedom-arch']
    const sc = m.hu / sh
    pulse(svg('g', { class: 'hm-rainbow', transform: `translate(${f(m.x - m.wu / 2 + (40 - sx) * sc, 2)} ${f(m.y - m.hu + (42 - sy) * sc, 2)}) scale(${f(k, 4)})` },
      ['m1', 'risk', 'm3', 'm2'].map((c, i) => { const r = f(21 - 3.2 * i, 2); return svg('path', { class: `hm-rb-${c}`, d: `M${-r} 0A${r} ${r} 0 0 1 ${r} 0` }) })), 2600)
  }

  function boat() {
    const pts = (polylines(map.paths.centreline)[0] || []).filter((p) => p[1] > vb.y - s(30) && p[1] < vb.y + vb.h + s(30))
    if (pts.length < 2 || fx.querySelector('.hm-boat')) return
    const w = walker(pts)
    const g = svg('g', { class: 'hm-boat' },
      svg('path', { class: 'hm-boat-body', d: 'M-11 .5H6.5Q10.5 .5 12-2.5H-8.5Z' }),
      svg('path', { class: 'hm-boat-cabin', d: 'M-6-2.5L-4.5-5.5H4L6.5-2.5' }),
      svg('path', { class: 'hm-boat-foil', d: 'M-7 .5V3.2M5 .5V3.2M-9.5 3.2H7.5' }))
    const place = (t) => { const p = w.at(t); g.setAttribute('transform', `translate(${f(p.x, 2)} ${f(p.y, 2)}) ${pose(p.a)} scale(${f(k, 4)})`); return p }
    fx.append(g)
    const p = place(RM.matches ? 0.5 : 0.03)
    showTip('Ракета на підводних крилах: єдина, яку тут чекають.', { x: p.x, y: p.y - s(10) }, 2600)
    if (RM.matches) { setTimeout(() => g.remove(), 2600); return }
    tween(7000, (q) => { place(0.03 + 0.94 * q); g.style.opacity = f(Math.min(1, q * 12, (1 - q) * 12), 3) }, () => g.remove())
  }

  function chestnuts() {
    if (!fx) return
    el.scrollIntoView({ block: 'nearest', behavior: RM.matches ? 'auto' : 'smooth' })
    const n = PX.chestnut
    const h = (n * 46.5) / 44.5
    showTip('Київські каштани', { x: vb.x + vb.w / 2, y: vb.y + s(40) }, 2200)
    for (let i = 0; i < 7; i++) {
      const x = vb.x + vb.w * (0.1 + 0.8 * rnd(i + 31))
      const y0 = vb.y + s(8)
      const y1 = vb.y + vb.h * (0.5 + 0.42 * rnd(i + 41))
      const spin = 160 + 200 * rnd(i + 51)
      const g = svg('g', { class: 'hm-chestnut' }, use('chestnut', -n / 2, -h / 2, n, h))
      const at = (p) => g.setAttribute('transform', `translate(${f(x, 2)} ${f(y0 + (y1 - y0) * p, 2)}) rotate(${f(spin * p)}) scale(${f(k, 4)})`)
      fx.append(g)
      if (RM.matches) { at(1); setTimeout(() => g.remove(), 2600); continue }
      at(0)
      g.style.opacity = 0
      setTimeout(() => tween(1000 + 300 * rnd(i + 61), (p) => { at(p * p); g.style.opacity = f(Math.min(1, p * 5), 3) },
        () => setTimeout(() => fade(g), 2200)), i * 140)
    }
  }

  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return
    const code = e.key?.startsWith('Arrow') ? e.key : e.code
    if (code === KONAMI[kseq]) kseq += 1
    else if (!(kseq === 2 && code === 'ArrowUp')) kseq = code === KONAMI[0] ? 1 : 0
    if (kseq === KONAMI.length) { kseq = 0; chestnuts() }
  })

  // ---------- life cycle ----------

  new ResizeObserver(() => { if (build()) paint() }).observe(el)
  new IntersectionObserver((es) => { inView = es.some((e) => e.isIntersecting); kick() }).observe(el)
  document.addEventListener('visibilitychange', kick)
  RM.addEventListener?.('change', () => setFlyers())
  document.fonts?.ready.then(() => { if (RM.matches) setFlyers() })
  setInterval(() => base?.classList.toggle('is-night', isNight()), 60000)

  return {
    update(data) {
      state = stateOf(data)
      if (!base) build()
      paint()
    },
    train,
  }
}
