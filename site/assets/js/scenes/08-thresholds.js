// Scene "thresholds" of the methodology deck: where the two lines of the forecast scale come from, drawn from the real
// development predictions (site/data/dev_predictions.json, written by scripts/site/dev_predictions.py).
import { h, s, canvas, put, reduced } from '../how.js'

const RULE = {
  title: 'Правило меж, записане до тесту',
  source: 'src/airalerts/quiet/forecast.py',
  text: `... Its scale was set on the development
folds only (quiet-now hours) by written rules, never on the test:
- busy from BUSY_AT: the highest threshold that still catches 80% of the busy windows (docs/METHODOLOGY.md 4.4);
- high risk from HIGH_AT: the upper third of the development predictions.
rules() recomputes both; tests/test_quiet_forecast.py checks they still hold.`,
}

const DATA = new URL('../../../data/dev_predictions.json', import.meta.url)
const RECALL = 0.8                                                  // src/airalerts/quiet/forecast.py RECALL
const TIERS = ['швидше тихо', 'середній ризик', 'високий ризик']    // src/airalerts/quiet/forecast.py level()
const ROWS = 22
const GB = 306                                                      // the bottom of the dot grid
const pct = (x) => `${Math.round(x * 100)}%`
const num = (v, d) => (Number.isFinite(v) ? v : d)
const label = (x, y, str, { anchor = 'start', size = 22, fill = 'var(--ink)', display = false } = {}) => {
  const style = { fill }
  if (display) style.fontFamily = 'var(--font-display)'
  return s('text', { x, y, 'text-anchor': anchor, 'font-size': size, style, text: str })
}

function draw(svg, rows, busyAt, highAt) {
  const pts = rows.filter((r) => r && Number.isFinite(r.p)).map((r, t) => ({ p: r.p, busy: r.busy ? 1 : 0, t }))
  const order = [...pts].sort((a, b) => a.p - b.p || a.t - b.t)
  order.forEach((d, r) => { d.rank = r })
  const N = order.length
  const B = pts.reduce((a, d) => a + d.busy, 0)
  const caughtFrom = (k) => order.slice(k).reduce((a, d) => a + d.busy, 0)
  // forecast.rules(): the highest threshold whose alarms (p >= it) still catch 80% of the busy windows ...
  let k80 = 0
  for (let r = N - 1, got = 0; r >= 0; r--) {
    got += order[r].busy
    if ((r === 0 || order[r - 1].p < order[r].p) && got >= RECALL * B) { k80 = r; break }
  }
  // ... and the upper third: the prediction two thirds up the sorted list
  const v33 = order[Math.floor((2 * N) / 3)].p
  const k33 = order.findIndex((d) => d.p >= v33)
  // the tiers as forecast.level() reads the scale
  const zones = [[], [], []]
  for (const d of order) zones[d.p < busyAt ? 0 : d.p < highAt ? 1 : 2].push(d)

  const cols = Math.ceil(N / ROWS)
  const zc = zones.map((z) => Math.max(1, Math.ceil(z.length / ROWS)))
  const c = Math.min(11, 560 / Math.max(cols, zc[0] + zc[1] + zc[2] + 2))
  const gx = 320 - (cols * c) / 2
  const right = gx + cols * c
  const gTop = GB - ROWS * c
  const colX = (k) => gx + Math.floor(k / ROWS) * c
  const cell = (i) => [colX(i) + c / 2, GB - (i % ROWS) * c - c / 2]

  // the last step: each tier its own block, busy dots first, filled row by row from the bottom
  let zx = 320 - ((zc[0] + zc[1] + zc[2] + 2) * c) / 2
  const blocks = zones.map((z, i) => {
    const left = zx
    zx += (zc[i] + 1) * c
    ;[...z].sort((a, b) => b.busy - a.busy || a.p - b.p).forEach((d, j) => {
      d.zx = left + (j % zc[i]) * c + c / 2
      d.zy = GB - Math.floor(j / zc[i]) * c - c / 2
    })
    const busy = z.reduce((a, d) => a + d.busy, 0)
    return { mid: left + (zc[i] * c) / 2, n: z.length, busy }
  })

  const third = s('rect', { x: colX(k33), y: gTop - 6, width: right - colX(k33) + 6, height: GB - gTop + 12, rx: 8,
    style: { fill: 'var(--pink-soft)' } })
  const dots = s('g', {})
  for (const d of pts) {
    const [x, y] = cell(d.rank)
    const [tx, ty] = cell(d.t)
    d.cx = x
    d.cy = y
    d.el = s('circle', { cx: x, cy: y, r: (c * 0.36).toFixed(2), style: { fill: d.busy ? 'var(--pink)' : 'var(--soft)' } })
    dots.append(d.el)
    put(d.el, { x: tx - x, y: ty - y, o: d.busy ? 1 : 0.4 }, { instant: true })   // first in time order
  }
  const stair = (k) => {
    const x = colX(k), row = k % ROWS
    return row ? `M${x},${gTop - 8}V${GB - row * c}H${x + c}V${GB + 8}` : `M${x},${gTop - 8}V${GB + 8}`
  }
  const line = (k, v) => {
    const lab = label(colX(k), gTop - 16, v.toFixed(3), { anchor: 'middle', display: true })
    const g = s('g', {}, s('path', { d: stair(k), style: { fill: 'none', stroke: 'var(--ink)', strokeWidth: 2.5 } }), lab)
    return { g, lab, x: colX(k) }
  }
  const L80 = line(k80, order[k80].p)
  const L33 = line(k33, v33)
  const head = label(gx, 26, '')
  const lx = right - 214
  const legend = s('g', {},
    s('circle', { cx: lx + 7, cy: 19, r: 6, style: { fill: 'var(--pink)' } }), label(lx + 20, 26, 'неспокійно'),
    s('circle', { cx: lx + 157, cy: 19, r: 6, style: { fill: 'var(--soft)', opacity: 0.4 } }), label(lx + 170, 26, 'тихо'))
  const bottom = s('g', {},
    label(gx, GB + 34, `p ${order[0].p.toFixed(2)}`, { fill: 'var(--soft)' }),
    label(320, GB + 34, 'від низької p до високої', { anchor: 'middle', fill: 'var(--soft)' }),
    label(right, GB + 34, `p ${order[N - 1].p.toFixed(2)}`, { anchor: 'end', fill: 'var(--soft)' }))
  const tiers = s('g', {}, ...blocks.flatMap((b, i) => [
    label(b.mid, gTop - 14, TIERS[i], { anchor: 'middle' }),
    label(b.mid, GB + 34, b.n ? pct((i === 0 ? b.n - b.busy : b.busy) / b.n) : '-', { anchor: 'middle', size: 24, display: true }),
    label(b.mid, GB + 64, i === 0 ? 'тихо' : 'неспокійно', { anchor: 'middle', fill: 'var(--soft)' }),
  ]))
  svg.append(third, dots, L80.g, L33.g, head, legend, bottom, tiers)
  for (const el of [third, L33.g, tiers]) put(el, { o: 0 }, { instant: true })
  put(L80.g, { x: right - L80.x, o: 0 }, { instant: true })
  put(L33.g, { x: right - L33.x, o: 0 }, { instant: true })

  const HEAD = [
    `${N} годин, ${pct(B / N)} неспокійні`,
    `спіймано ${pct(caughtFrom(k80) / B)} неспокійних`,
    `вище ${v33.toFixed(3)}: ${pct((N - k33) / N)} годин`,
    '',
  ]
  const lit = (d) => (d.busy ? 1 : 0.4)
  const OP = (d, k) => {
    if (k === 0 || k === 3) return lit(d)
    const dim = d.busy ? 0.3 : 0.12
    if (k === 1) return d.rank >= k80 ? lit(d) : dim
    return d.rank >= k33 ? lit(d) : d.rank >= k80 ? (d.busy ? 0.6 : 0.24) : dim
  }

  function end(k, o, intro = false) {
    const opt = (delay = 0) => ({ instant: o.instant, delay: o.instant ? 0 : delay })
    for (const d of pts) {
      const at = k === 3 ? { x: d.zx - d.cx, y: d.zy - d.cy } : { x: 0, y: 0 }
      put(d.el, { ...at, o: OP(d, k) }, opt(intro ? Math.floor(d.rank / ROWS) * 6 : k === 3 ? (d.rank % ROWS) * 8 : 0))
    }
    L80.lab.textContent = order[k80].p.toFixed(3)
    put(L80.g, { x: k === 0 ? right - L80.x : 0, o: k === 1 || k === 2 ? 1 : 0 }, opt())
    put(L33.g, { x: k < 2 ? right - L33.x : 0, o: k === 2 ? 1 : 0 }, opt())
    put(third, { o: k === 2 ? 1 : 0 }, opt(k === 2 ? 200 : 0))
    head.textContent = HEAD[k]
    for (const el of [head, legend, bottom]) put(el, { o: k < 3 ? 1 : 0 }, opt())
    put(tiers, { o: k === 3 ? 1 : 0 }, opt(k === 3 ? 500 : 0))
  }

  // step 2 told forward: the line sweeps down from the top prediction, the counter of caught busy windows runs
  function sweep(later) {
    const n = 6, gap = 330, t0 = 350, span = Math.max(1, N - k80)
    for (const d of pts) put(d.el, { o: d.busy ? 0.3 : 0.12 })
    put(L80.g, { x: right - L80.x, o: 1 })
    L80.lab.textContent = order[N - 1].p.toFixed(3)
    head.textContent = `спіймано ${pct(0)} неспокійних`
    put(head, { o: 1 })
    for (let i = 1; i <= n; i++) {
      const r = i === n ? k80 : Math.round(N - (span * i) / n)
      later(t0 + (i - 1) * gap, () => put(L80.g, { x: colX(r) - L80.x, o: 1 }, { dur: 320 }))
      later(t0 + (i - 1) * gap + 300, () => {
        L80.lab.textContent = order[r].p.toFixed(3)
        head.textContent = `спіймано ${pct(caughtFrom(r) / B)} неспокійних`
      })
    }
    later(t0, () => {
      for (const d of pts) if (d.rank >= k80) put(d.el, { o: lit(d) }, { delay: ((N - d.rank) / span) * n * gap, dur: 300 })
    })
    later(t0 + n * gap + 100, () => end(1, {}))
  }

  return {
    near(ux, uy, k) {
      if (!pts.length) return ''
      let best = pts[0], bd = Infinity
      for (const d of pts) {
        const dd = ((k === 3 ? d.zx : d.cx) - ux) ** 2 + ((k === 3 ? d.zy : d.cy) - uy) ** 2
        if (dd < bd) { bd = dd; best = d }
      }
      const tier = TIERS[best.p < busyAt ? 0 : best.p < highAt ? 1 : 2]
      return `p ${best.p.toFixed(4)}: наступні 3 години ${best.busy ? 'стали неспокійними' : 'були тихі'}, рівень «${tier}»`
    },
    play(k, fwd, anim, later) {
      if (fwd && k === 1) return sweep(later)
      end(k, { instant: !anim }, fwd && k === 0)
    },
  }
}

const scene = {
  id: 'thresholds',
  title: 'Звідки дві межі',
  lead: 'Межі шкали не обирали руками: їх дали прогнози розробки за правилом, записаним до тесту.',
  steps: [
    { note: '<p>Кожна точка це година розробки, коли було тихо: <span class="num">1067</span> годин за 8 тижнів з 2026-07-04. ' +
        'Модель щотижня вчилась лише на минулому і ставила кожній годині ймовірність p; тут точки впорядковані від низької p до високої. ' +
        'Рожеві: наступні 3 години стали неспокійними (<span class="num">31%</span>, docs/quiet/model.md розділ 7). ' +
        'Дані: <b>site/data/dev_predictions.json</b>, їх перераховує scripts/site/dev_predictions.py.</p>' },
    { note: '<p>Лінія порогу їде вниз по p: усе праворуч модель назвала б неспокійним, а лічильник рахує спіймані рожеві точки. ' +
        'Правило записали наперед: пропустити атаку гірше за зайве попередження, тож беремо найвищий поріг, який ще ловить 80% неспокійних вікон ' +
        '(docs/METHODOLOGY.md 4.4). Лінія зупиняється на <span class="num">0.197</span>.</p>' },
    { note: '<p>Друга межа простіша: верхня третина прогнозів розробки, вона починається з <span class="num">0.300</span>. ' +
        'Праворуч від неї «високий ризик», між лініями «середній ризик». ' +
        'Обидві межі перераховує rules() у <b>src/airalerts/quiet/forecast.py</b>, руками їх ніхто не обирав.</p>' },
    { note: '<p>Що означали рівні на цих годинах: «швидше тихо» модель казала у 37% з них, і справді було тихо у <span class="num">83%</span>. ' +
        'Після «високого ризику» неспокійно ставало у <span class="num">49%</span> (174 з 354); обидва числа під блоками, з site/data/dev_predictions.json. ' +
        'На тесті, де модель вчилась наново щогодини, ці частки 83% і 80% (docs/quiet/forecast.md). ' +
        'Тиша не гарантована: навіть «швидше тихо» це приблизно 1 шанс з 6 (розділ 10 docs/quiet/model.md).</p>' },
  ],
  prompts: [RULE],
  mount(stage, data) {
    const root = h('div', { class: 'scene-thresholds' }, h('style', { text: '.scene-thresholds { position: absolute; inset: 0; } .scene-thresholds .tip { position: absolute; z-index: 2; max-width: 260px; '
      + 'padding: 6px 10px; border-radius: var(--r-small); background: var(--card); border: 1px solid var(--line); color: var(--ink); font-size: 14px; '
      + 'line-height: 1.35; pointer-events: none; } .scene-thresholds .tip[hidden] { display: none; }' }))
    stage.append(root)
    const svg = canvas(root, 'Години розробки як точки від низької ймовірності до високої і дві межі шкали')
    const tip = h('div', { class: 'tip', role: 'tooltip', hidden: true })
    root.append(tip)
    const showTip = (e) => {
      if (!view) return
      const b = root.getBoundingClientRect()
      tip.textContent = view.near(((e.clientX - b.left) * 640) / b.width, ((e.clientY - b.top) * 400) / b.height, cur)
      tip.hidden = false
      tip.style.left = `${Math.max(4, Math.min(e.clientX - b.left + 14, b.width - tip.offsetWidth - 4))}px`
      tip.style.top = `${Math.max(4, Math.min(e.clientY - b.top + 14, b.height - tip.offsetHeight - 4))}px`
    }
    svg.addEventListener('pointermove', showTip)
    svg.addEventListener('pointerdown', showTip)
    svg.addEventListener('pointerleave', () => { tip.hidden = true })
    const busyAt = num(data?.model?.busy_at, 0.197)   // fallback: docs/quiet/model.md section 7
    const highAt = num(data?.model?.high_at, 0.3)
    const status = label(320, 200, 'Завантажую години розробки', { anchor: 'middle', fill: 'var(--soft)' })
    svg.append(status)
    let view = null
    let cur = -1
    let want = { k: 0, instant: true }
    let timers = []
    let alive = true
    const later = (ms, f) => timers.push(setTimeout(f, ms))
    const clear = () => { timers.forEach(clearTimeout); timers = [] }

    function show(k, { instant } = {}) {
      want = { k, instant }
      clear()
      tip.hidden = true
      if (!view) return
      const anim = !instant && !reduced()
      const fwd = anim && k === cur + 1
      cur = k
      view.play(k, fwd, anim, later)
    }

    fetch(DATA)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then((rows) => {
        if (!alive) return
        view = draw(svg, rows, busyAt, highAt)
        status.remove()
        svg.getBoundingClientRect()   // the dots are rendered in time order before they sort themselves
        show(want.k, { instant: want.instant && want.k !== 0 })
      })
      .catch(() => { if (alive) status.textContent = 'Не вдалось завантажити години розробки' })

    return { show, destroy() { alive = false; clear() } }
  },
}

export default scene
