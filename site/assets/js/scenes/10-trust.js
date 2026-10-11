// Scene "trust" of the methodology deck: how far the model can be trusted, in seven pictures. Every number is read
// from site/data/trust.json (scripts/site/trust.py writes it, its docstring documents every field); only the four
// retrain candidates of the last step come from docs/adr/0013-retrain-cadence.md, and the notes name it there.
import { h, s, canvas, put, stagger, reduced } from '../how.js'

const DATA = new URL('../../../data/trust.json', import.meta.url)
const T = await fetch(DATA).then((r) => (r.ok ? r.json() : null)).catch(() => null)

const SPLIT = {
  title: 'Правило поділу, записане до моделей',
  source: 'docs/adr/0008-time-split.md',
  text: `Тест: усі години з 2026-08-29 12:00 за Києвом (09:00Z) до кінця міток, тобто останні 6 повних тижнів ...
Тест відкриваємо один раз, для фінальної оцінки, і модель на ньому перенавчається щотижня на всьому, що відомо до початку тижня.
Розробка: години, чия мітка відома до межі ... Ознаки, модель, поріг і розмір вікна навчання обираємо на 8 тижневих фолдах walk-forward з 2026-07-04 12:00 за Києвом.`,
}
const MEASURES = {
  title: 'Мірила простими словами',
  source: 'README.md',
  text: `BSS: наскільки ймовірності точніші за сталу частку подій, відому на початок тижня; 0 той самий рівень, більше 0 краще.
ROC AUC: шанс, що година з атакою отримає вищий прогноз за тиху; 0.5 це монетка.
Інтервали в дужках: 95%, bootstrap по добах (для ночей по ночах), 1000 повторів.`,
}
const RULE = {
  title: 'Правило межі, записане до тесту',
  source: 'src/airalerts/quiet/forecast.py',
  text: `... Its scale was set on the development
folds only (quiet-now hours) by written rules, never on the test:
- busy from BUSY_AT: the highest threshold that still catches 80% of the busy windows (docs/METHODOLOGY.md 4.4);
- high risk from HIGH_AT: the upper third of the development predictions.
rules() recomputes both; tests/test_quiet_forecast.py checks they still hold.`,
}
const CHOICE = {
  title: 'Правило вибору, записане до чисел',
  source: 'docs/adr/0013-retrain-cadence.md',
  text: `Вибір: найрідше перенавчання, чий BSS на розробці не нижчий за найкращий BSS на розробці мінус 0.01
(правило простоти проєкту: рідше означає менше запусків і менше місць для збою).`,
}
const examplesCard = (D) => ({ title: 'Як обрано приклади', source: 'scripts/site/trust.py', text: D.examples.rule })

// docs/adr/0013-retrain-cadence.md, «Наслідки», the development rows: retrains in the 8 weeks and BSS on quiet-now hours
const CANDIDATES = [
  { label: 'щогодини', retrains: 1342, bss: 0.0982 },
  { label: 'кожні 6 год', retrains: 224, bss: 0.0978 },
  { label: 'щодня о 04:00', retrains: 57, bss: 0.0973 },
  { label: 'щотижня', retrains: 8, bss: 0.0943 },
]
const MARGIN = 0.01   // docs/adr/0013-retrain-cadence.md, «Вибір»
const RECALL = 0.8    // src/airalerts/quiet/forecast.py RECALL

const pct = (x) => `${Math.round(x * 100)}%`
const f3 = (x) => Number(x).toFixed(3)
const ci = (a) => `[${f3(a[0])}, ${f3(a[1])}]`
const num = (v) => `<span class="num">${v}</span>`
const dm = (t) => `${t.slice(8, 10)}.${t.slice(5, 7)}`   // "2026-07-04 12:00" -> "04.07"
const hour = (t) => Date.UTC(+t.slice(0, 4), +t.slice(5, 7) - 1, +t.slice(8, 10), +t.slice(11, 13)) / 36e5
const times = (n) => (n % 10 === 1 && n % 100 !== 11 ? 'раз'
  : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? 'рази' : 'разів')
const outcome = (it) => (!it.busy ? 'було тихо' : it.drones && it.missiles ? 'дрони і ракети'
  : it.drones ? 'прилетіли дрони' : it.missiles ? 'прилетіли ракети' : 'неспокійно')
const real = (bins) => bins.filter((b) => b.n > 0 && b.p_mean != null && b.busy_share != null)
function cadence() {
  const best = CANDIDATES.reduce((a, c) => (c.bss > a.bss ? c : a))
  const limit = best.bss - MARGIN
  const pass = CANDIDATES.filter((c) => c.bss >= limit)
  return { best, limit, pass, chosen: pass.reduce((a, c) => (c.retrains < a.retrains ? c : a)) }
}

function text(x, y, str, { anchor = 'start', size = 22, fill = 'var(--ink)', display = false } = {}) {
  const style = { fill }
  if (display) style.fontFamily = 'var(--font-display)'
  return s('text', { x, y, 'text-anchor': anchor, 'dominant-baseline': 'central', 'font-size': size, style, text: str })
}

// One move of a mark: its start state, its end state, when and around which point. A step plays its moves forward
// or jumps to their end states.
const mv = (el, from, to = {}, delay = 0, origin = 'center', dur = 320) => ({ el, from, to, delay, origin, dur })
function stepper(g, moves, zones) {
  const at = (m, st, o) => put(m.el, st, { origin: m.origin, ...o })
  return {
    g, zones,
    start() { for (const m of moves) at(m, m.from, { instant: true }) },
    play() { for (const m of moves) at(m, m.to, { delay: m.delay, dur: m.dur }) },
    end() { for (const m of moves) at(m, m.to, { instant: true }) },
  }
}

// 1. All hours on one time bar: development with its 8 weekly checks, the closed test
function stepSplit(D) {
  const sp = D.split
  const P = Object.fromEntries(sp.parts.map((p) => [p.key, p]))
  const F = sp.dev_folds
  const h0 = hour(sp.first)
  const BX = 16, BW = 608, BY = 96, BH = 48
  const X = (t) => BX + (BW * (hour(t) - h0)) / sp.hours
  const W = (n) => (BW * n) / sp.hours
  const g = s('g', {})
  const seg = (p, fill) => (p ? s('rect', { x: X(p.from), y: BY, width: Math.max(0, X(p.to) - X(p.from)), height: BH, style: { fill } }) : null)
  const over = s('rect', { x: BX, y: BY, width: BW, height: BH, style: { fill: 'var(--ink)', fillOpacity: 0.3 } })
  const weeks = sp.test_folds.filter((f) => f.rows === 7 * 24).slice(1)
    .map((f) => s('line', { x1: X(f.origin), x2: X(f.origin), y1: BY, y2: BY + BH, style: { stroke: 'var(--card)', strokeWidth: 2 } }))
  const bar = s('g', { 'clip-path': 'url(#how-trust-bar)' }, seg(P.history, 'var(--line)'), seg(P.development, 'var(--pink-soft)'),
    seg(P.purged, 'var(--line)'), seg(P.test, 'var(--ink)'), seg(P.unlabelled, 'var(--line)'), ...weeks, over)
  const tA = X(P.test.from), tB = X(P.test.to), cut = X(sp.test_start)
  const lx = (tA + tB) / 2, ly = BY + BH / 2
  const lock = s('g', {}, s('rect', { x: lx - 15, y: BY + 5, width: 30, height: BH - 10, rx: 4, style: { fill: 'var(--ink)' } }),
    s('g', { style: { fill: 'none', stroke: 'var(--card)', strokeWidth: 2.5, strokeLinecap: 'round' } },
      s('rect', { x: lx - 10, y: ly - 3, width: 20, height: 14, rx: 3 }), s('path', { d: `M${lx - 6},${ly - 3}v-5a6,6 0 0 1 12,0v5` })))
  const cells = F.map((f) => s('rect', { x: X(f.origin) + 1.5, y: BY + 8, width: Math.max(1, W(f.rows) - 3), height: BH - 16, rx: 3,
    style: { fill: 'var(--pink)' } }))
  const x0 = X(F[0].origin)
  const win = s('rect', { x: x0 - 1, y: BY - 7, width: W(7 * 24) + 2, height: BH + 14, rx: 5,
    style: { fill: 'none', stroke: 'var(--pink)', strokeWidth: 3 } })
  const brk = (a, b, label) => s('g', {},
    s('path', { d: `M${a},${BY - 8}V${BY - 16}H${b}V${BY - 8}`, style: { fill: 'none', stroke: 'var(--soft)', strokeWidth: 1.5 } }),
    text((a + b) / 2, BY - 34, label, { anchor: 'middle' }))
  const soft = { fill: 'var(--soft)' }
  const devMid = (X(P.development.from) + X(P.development.to)) / 2
  const nums = [
    text(BX, 262, 'годин «зараз тихо»', soft),
    text(devMid, 262, String(P.development.quiet_now), { anchor: 'middle', display: true }),
    text(lx, 262, String(P.test.quiet_now), { anchor: 'middle', display: true }),
    text(BX, 304, 'після них прилетіло', soft),
    text(devMid, 304, pct(P.development.busy_share), { anchor: 'middle', display: true, fill: 'var(--pink)' }),
    text(lx, 304, pct(P.test.busy_share), { anchor: 'middle', display: true, fill: 'var(--pink)' }),
  ]
  const cap = text(BX, 210, '')
  g.append(s('defs', {}, s('clipPath', { id: 'how-trust-bar' }, s('rect', { x: BX, y: BY, width: BW, height: BH, rx: 10 }))),
    text(BX, 26, `${sp.hours} годин: з ${dm(sp.first)} до ${dm(sp.last)}`),
    brk(BX + 2, cut - 4, 'розробка'), brk(cut + 4, BX + BW - 2, 'тест'), bar, ...cells, lock, win,
    text(BX, 168, dm(sp.first), soft), text(X(sp.folds_from), 168, dm(sp.folds_from), { ...soft, anchor: 'middle' }),
    text(cut, 168, dm(sp.test_start), { ...soft, anchor: 'middle' }), text(BX + BW, 168, dm(sp.last), { ...soft, anchor: 'end' }),
    cap, ...nums,
    s('rect', { x: BX, y: 344, width: 22, height: 22, rx: 5, style: { fill: 'none', stroke: 'var(--pink)', strokeWidth: 3 } }),
    text(BX + 34, 355, 'тиждень прогнозу'),
    s('rect', { x: 290, y: 344, width: 22, height: 22, rx: 5, style: { fill: 'var(--ink)', fillOpacity: 0.3 } }),
    text(324, 355, 'на чому вчиться'))
  const zones = [
    { x: (BX + X(P.history.to)) / 2, y: BY + BH / 2, t: `${dm(P.history.from)} - ${dm(P.history.to)}: лише навчання, ${P.history.rows} годин` },
    ...F.map((f, i) => ({ x: X(f.origin) + W(f.rows) / 2, y: BY + BH / 2,
      t: `тиждень ${i + 1} з ${dm(f.origin)}: вчилась на ${f.fit_rows} годинах; «зараз тихо» ${f.quiet_now}, після них прилетіло ${pct(f.busy_share)}` })),
    { x: lx, y: BY + BH / 2, t: `тест ${dm(P.test.from)} - ${dm(P.test.to)}: ${P.test.rows} годин, відкрили один раз` },
    { x: devMid, y: 283, t: `розробка: ${P.development.quiet_now} годин «зараз тихо», після ${P.development.busy} з них прилетіло` },
    { x: lx, y: 283, t: `тест: ${P.test.quiet_now} годин «зараз тихо», після ${P.test.busy} з них прилетіло` },
  ]
  const capAt = (i) => `тиждень ${i + 1} з ${F.length}: вчиться на ${F[i].fit_rows} год`
  const END = `${F.length} ${times(F.length)}: вчиться на минулому, прогноз на тиждень`
  const goTo = (i, o) => {
    put(win, { x: X(F[i].origin) - x0, o: 1 }, o)
    put(over, { kx: (X(F[i].origin) - BX) / BW }, { ...o, origin: 'left center' })
  }
  return {
    g, zones,
    start() {
      put(win, { o: 0 }, { instant: true })
      put(over, { kx: 0.001 }, { instant: true, origin: 'left center' })
      for (const el of [...cells, ...nums]) put(el, { o: 0 }, { instant: true })
      cap.textContent = ''
    },
    play(later) {   // the window slides week by week, the learning part grows behind it
      F.forEach((_, i) => later(200 + i * 420, () => {
        goTo(i, { dur: 320 })
        if (i) put(cells[i - 1], { o: 1 }, { dur: 240 })
        cap.textContent = capAt(i)
      }))
      later(200 + F.length * 420, () => {
        put(cells[F.length - 1], { o: 1 }, { dur: 240 })
        cap.textContent = END
        nums.forEach((el, j) => put(el, { o: 1 }, { delay: stagger(j, 80), dur: 300 }))
      })
    },
    end() {
      goTo(F.length - 1, { instant: true })
      for (const el of [...cells, ...nums]) put(el, { o: 1 }, { instant: true })
      cap.textContent = END
    },
  }
}

// 2. The formal score: BSS and ROC AUC with their 95% intervals, the model against the 7-day share
function stepScore(D) {
  const M = D.evaluation.models
  const fin = M.find((m) => m.role === 'finalist'), ref = M.find((m) => m.role === 'reference')
  const g = s('g', {}), zones = [], moves = []
  const A0 = 170, A1 = 530
  const PANELS = [
    { key: 'bss', name: 'BSS', title: 'BSS, більше 0 краще', lo: -0.2, hi: 0.6, mid: 0, ticks: [-0.2, 0, 0.2, 0.4, 0.6], y: 30, rows: [86, 132], tick: 168 },
    { key: 'roc_auc', name: 'ROC AUC', title: 'ROC AUC, 0.5 це монетка', lo: 0.3, hi: 0.9, mid: 0.5, ticks: [0.3, 0.5, 0.7, 0.9], y: 214, rows: [266, 312], tick: 348 },
  ]
  g.append(s('circle', { cx: 330, cy: 30, r: 7, style: { fill: 'var(--pink)' } }), text(344, 30, 'модель'),
    s('circle', { cx: 440, cy: 30, r: 7, style: { fill: 'var(--soft)' } }), text(454, 30, 'частка 7 днів'))
  PANELS.forEach((P, pi) => {
    const xs = (v) => A0 + ((A1 - A0) * (Math.max(P.lo, Math.min(P.hi, v)) - P.lo)) / (P.hi - P.lo)
    g.append(text(16, P.y, P.title),
      s('line', { x1: xs(P.mid), x2: xs(P.mid), y1: P.y + 24, y2: P.tick - 18, style: { stroke: 'var(--soft)', strokeWidth: 1.5, strokeDasharray: '5 5' } }),
      ...P.ticks.map((t) => text(xs(t), P.tick, String(t), { anchor: 'middle', fill: 'var(--soft)' })))
    ;['development', 'test'].forEach((part, ri) => {
      const y = P.rows[ri], name = part === 'test' ? 'тест' : 'розробка'
      g.append(text(16, y, name))
      ;[[fin, 'var(--pink)', -11], [ref, 'var(--soft)', 11]].forEach(([m, color, dy], mi) => {
        const r = m[part], v = r[P.key], c = r[`${P.key}_ci`]
        const line = s('rect', { x: xs(c[0]), y: y + dy - 2, width: Math.max(1, xs(c[1]) - xs(c[0])), height: 4, rx: 2, style: { fill: color } })
        const dot = s('circle', { cx: xs(v), cy: y + dy, r: 7, style: { fill: color, stroke: 'var(--card)', strokeWidth: 2 } })
        g.append(line, dot)
        const d = pi * 800 + ri * 220 + mi * 90
        moves.push(mv(line, { kx: 0.001, o: 0 }, {}, d, 'center', 360), mv(dot, { x: xs(P.mid) - xs(v), o: 0 }, {}, d, 'center', 360))
        if (mi === 0) {
          const val = text(624, y + dy, f3(v), { anchor: 'end', display: true, fill: 'var(--pink)' })
          g.append(val)
          moves.push(mv(val, { o: 0 }, {}, d + 300))
        }
        zones.push({ x: xs(v), y: y + dy, t: `${name}, ${m.label}: ${P.name} ${f3(v)}, 95% інтервал ${ci(c)}` })
      })
    })
  })
  return stepper(g, moves, zones)
}

// 3. Every quiet-now test hour as a dot, sorted into what the model said and what happened
function stepGrid(D) {
  const tb = D.replay.test.table
  const g = s('g', {}), zones = [], moves = []
  const L = 16, R = 324, BW = 300, C = 11
  const A = { top: 64, h: 80 }, B = { top: 184, h: 208 }
  const Q = [
    { n: tb.quiet_quiet, x: L, band: A, fill: 'var(--go)', soft: 'var(--go-soft)', ink: 'var(--go)', word: 'влучила', said: 'тихо', was: 'було тихо' },
    { n: tb.quiet_busy, x: R, band: A, fill: 'var(--stop)', soft: 'var(--stop-soft)', ink: 'var(--stop)', word: 'пропуск', said: 'тихо', was: 'прилетіло' },
    { n: tb.busy_quiet, x: L, band: B, fill: 'var(--risk-fill)', soft: 'var(--risk-soft)', ink: 'var(--risk)', word: 'зайва тривога', said: 'неспокійно', was: 'було тихо' },
    { n: tb.busy_busy, x: R, band: B, fill: 'var(--go)', soft: 'var(--go-soft)', ink: 'var(--go)', word: 'влучила', said: 'неспокійно', was: 'прилетіло' },
  ]
  const total = Q.reduce((a, q) => a + q.n, 0)
  g.append(text(L + BW / 2, 22, 'було тихо', { anchor: 'middle', fill: 'var(--soft)' }),
    text(R + BW / 2, 22, 'прилетіло', { anchor: 'middle', fill: 'var(--soft)' }),
    text(L, 47, 'казала «тихо»'), text(L, 167, 'казала «неспокійно»'))
  const labels = []
  for (const q of Q) {
    const b = q.band
    g.append(s('rect', { x: q.x, y: b.top, width: BW, height: b.h, rx: 14, style: { fill: q.soft } }))
    labels.push(text(q.x + BW - 14, b.top + 28, String(q.n), { anchor: 'end', display: true, size: 26, fill: q.ink }),
      text(q.x + BW - 14, b.top + 60, q.word, { anchor: 'end' }))
    zones.push({ x: q.x + BW / 2, y: b.top + b.h / 2, t: `казала «${q.said}», ${q.was}: ${q.n} з ${total} годин тесту, ${q.word}` })
  }
  // a fixed shuffle, so the pile at the start mixes the four kinds
  const kinds = Q.flatMap((q, qi) => Array.from({ length: q.n }, (_, j) => [qi, j]))
  const order = kinds.map((_, i) => i)
  let seed = 11
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1))
    ;[order[i], order[j]] = [order[j], order[i]]
  }
  const COLS = 32, gx = 320 - ((COLS - 1) * C) / 2, gy = 200
  const dots = s('g', {})
  order.forEach((ki, i) => {
    const [qi, j] = kinds[ki]
    const q = Q[qi], b = q.band, top = b === A
    const cols = top ? Math.max(10, Math.ceil(q.n / 5)) : 25
    const tx = q.x + 18 + (j % cols) * C
    const ty = top ? b.top + 18 + Math.floor(j / cols) * C : b.top + b.h - 16 - Math.floor(j / cols) * C
    const plain = s('circle', { cx: tx, cy: ty, r: 4, style: { fill: 'var(--soft)' } })
    const lit = s('circle', { cx: tx, cy: ty, r: 4, style: { fill: q.fill } })
    const dot = s('g', {}, plain, lit)
    dots.append(dot)
    const d = 450 + i * 2.5
    moves.push(mv(dot, { x: gx + (i % COLS) * C - tx, y: gy + Math.floor(i / COLS) * C - ty }, {}, d, 'center', 360),
      mv(lit, { o: 0 }, {}, d + 160), mv(plain, { o: 0.6 }, { o: 0 }, d + 160))
  })
  g.append(dots, ...labels)
  labels.forEach((el, i) => moves.push(mv(el, { o: 0 }, {}, 1700 + stagger(i, 70))))
  return stepper(g, moves, zones)
}

// 4. Plain accuracy against two lazy rules, and what each of them catches
function stepAccuracy(D) {
  const R = D.replay
  const g = s('g', {}), zones = [], moves = []
  const X0 = 262, S = 200
  g.append(text(X0, 26, 'точність', { fill: 'var(--soft)' }), text(624, 26, 'ловить атаки', { anchor: 'end', fill: 'var(--soft)' }))
  ;[[R.development, 'розробка', 26], [R.test, 'тест', 180]].forEach(([d, name, y0], gi) => {
    g.append(text(16, y0, name, { display: true }))
    const rows = [
      ['наша модель', d.accuracy, pct(d.busy_recall), 'var(--pink)', 'var(--go)'],
      ['завжди «неспокійно»', d.always_busy_accuracy, 'усі', 'var(--soft)', 'var(--ink)'],
      ['завжди «тихо»', d.always_quiet_accuracy, 'жодної', 'var(--soft)', 'var(--stop)'],
    ]
    rows.forEach(([label, v, caught, color, cc], i) => {
      const y = y0 + 34 * (i + 1), dl = gi * 500 + stagger(i, 110)
      const bar = s('rect', { x: X0, y: y - 11, width: Math.max(1, S * v), height: 22, rx: 6, style: { fill: color } })
      const val = text(X0 + S * v + 8, y, pct(v), { display: true, fill: i === 0 ? 'var(--pink)' : 'var(--ink)' })
      const got = text(624, y, caught, { anchor: 'end', fill: cc })
      g.append(text(16, y, label), bar, val, got)
      moves.push(mv(bar, { kx: 0.001 }, {}, dl, 'left center', 360), mv(val, { o: 0 }, {}, dl + 260),
        mv(got, { o: 0 }, {}, 1300 + gi * 300 + stagger(i, 110)))
      zones.push({ x: X0 + 100, y, t: `${name}, ${label}: точність ${pct(v)}; ловить ${i === 0 ? `${caught} неспокійних вікон`
        : i === 1 ? 'усі, бо попереджає завжди' : 'жодної, бо ніколи не попереджає'}` })
    })
  })
  const r1 = text(16, 338, `межа ${R.busy_at}: ловити ${pct(RECALL)} атак розробки`)
  const r2 = text(16, 372, 'бо пропустити атаку гірше за зайву тривогу', { fill: 'var(--soft)' })
  g.append(r1, r2)
  moves.push(mv(r1, { o: 0 }, {}, 2100), mv(r2, { o: 0 }, {}, 2250))
  zones.push({ x: 200, y: 355, t: `межа ${R.busy_at} з правила в src/airalerts/quiet/forecast.py: найвищий поріг, що ловить ${pct(RECALL)} неспокійних вікон розробки` })
  return stepper(g, moves, zones)
}

// 5. Calibration: what the model said against how often it really came, the diagonal is the ideal
function stepCalibration(D) {
  const g = s('g', {}), zones = [], moves = []
  const PX = (p) => 80 + 260 * p, PY = (q) => 350 - 260 * q
  const soft = { fill: 'var(--soft)' }
  const clip = s('rect', { x: 76, y: 86, width: 268, height: 268 })
  g.append(s('defs', {}, s('clipPath', { id: 'how-trust-diag' }, clip)),
    s('path', { d: 'M80,220H340M210,90V350', style: { fill: 'none', stroke: 'var(--line)', strokeWidth: 1.5, strokeDasharray: '4 6' } }),
    s('path', { d: 'M80,90V350H340', style: { fill: 'none', stroke: 'var(--soft)', strokeWidth: 1.5 } }),
    s('line', { x1: PX(0), y1: PY(0), x2: PX(1), y2: PY(1), 'clip-path': 'url(#how-trust-diag)',
      style: { stroke: 'var(--ink)', strokeWidth: 2, strokeDasharray: '7 6' } }),
    text(80, 56, 'сталося насправді', soft), text(352, 350, 'модель казала', soft),
    ...[[0, '0%'], [0.5, '50%'], [1, '100%']].flatMap(([v, t]) => [
      text(PX(v), 378, t, { ...soft, anchor: 'middle' }), text(70, PY(v), t, { ...soft, anchor: 'end' })]))
  const test = real(D.replay.test.calibration)
  const above = test.filter((b) => b.busy_share > b.p_mean).length * 2 > test.length
  ;[[real(D.replay.development.calibration), 'розробка', 'var(--soft)', 400], [test, 'тест', 'var(--pink)', 1150]].forEach(([bins, name, color, t0]) => {
    bins.forEach((b, i) => {
      const c = s('circle', { cx: PX(b.p_mean), cy: PY(b.busy_share), r: (3 + 0.55 * Math.sqrt(b.n)).toFixed(1),
        style: { fill: color, stroke: 'var(--card)', strokeWidth: 1.5 } })
      g.append(c)
      moves.push(mv(c, { k: 0.001, o: 0 }, {}, t0 + stagger(i, 60), 'center', 300))
      zones.push({ x: PX(b.p_mean), y: PY(b.busy_share), t: `${name}: модель казала в середньому ${pct(b.p_mean)}, прилетіло після ${pct(b.busy_share)} з ${b.n} годин` })
    })
  })
  const n1 = text(380, 250, `тест ${above ? 'вище' : 'нижче'} лінії:`), n2 = text(380, 280, `прилітало ${above ? 'частіше' : 'рідше'}`, { fill: 'var(--pink)' })
  g.append(s('circle', { cx: 392, cy: 110, r: 8, style: { fill: 'var(--pink)' } }), text(408, 110, 'тест'),
    s('circle', { cx: 392, cy: 146, r: 8, style: { fill: 'var(--soft)' } }), text(408, 146, 'розробка'),
    s('line', { x1: 380, x2: 402, y1: 182, y2: 182, style: { stroke: 'var(--ink)', strokeWidth: 2, strokeDasharray: '7 6' } }), text(408, 182, 'ідеал'),
    n1, n2)
  moves.push(mv(clip, { kx: 0.001 }, {}, 0, 'left center', 400), mv(n1, { o: 0 }, {}, 1900), mv(n2, { o: 0 }, {}, 2000))
  return stepper(g, moves, zones)
}

// 6. Four real test hours: two right, a miss, a false alarm
function stepExamples(D) {
  const g = s('g', {}), zones = [], moves = []
  D.examples.items.slice(0, 4).forEach((it, i) => {
    const top = 8 + i * 98, cy = top + 44
    const ok = (it.tier === 'low') === !it.busy
    const card = s('g', {},
      s('rect', { x: 16, y: top, width: 608, height: 88, rx: 14, style: { fill: 'var(--card)', stroke: 'var(--line)', strokeWidth: 1.5 } }),
      text(88, cy - 16, `${dm(it.t)}, ${it.window}`),
      text(88, cy + 18, `казала «${it.said}»`, { fill: 'var(--soft)' }),
      text(604, cy - 16, `шанс ${pct(it.p)}`, { anchor: 'end', display: true }),
      text(604, cy + 18, outcome(it), { anchor: 'end' }))
    const mark = s('g', {}, s('circle', { cx: 52, cy, r: 20, style: { fill: ok ? 'var(--go)' : 'var(--stop)' } }),
      s('path', { d: ok ? `M42,${cy + 1}l7,7l13,-15` : `M45,${cy - 7}l14,14M59,${cy - 7}l-14,14`,
        style: { fill: 'none', stroke: 'var(--card)', strokeWidth: 3.5, strokeLinecap: 'round', strokeLinejoin: 'round' } }))
    g.append(card, mark)
    moves.push(mv(card, { x: 36, o: 0 }, {}, stagger(i, 140), 'center', 340), mv(mark, { k: 0.001, o: 0 }, {}, stagger(i, 140, 300), 'center', 300))
    zones.push({ x: 320, y: cy, t: `${it.label}: ${dm(it.t)} ${it.window}, p ${it.p.toFixed(4)}, сталося: ${it.happened}` })
  })
  return stepper(g, moves, zones)
}

// 7. How often the live model retrains: four candidates, the written rule, the choice
function stepCadence(D) {
  const g = s('g', {}), zones = [], moves = []
  const { best, limit, chosen } = cadence()
  const X0 = 236, S = 2500
  const xl = X0 + S * limit
  const weeks = D.split.dev_folds.length
  g.append(text(X0, 22, 'BSS на розробці', { fill: 'var(--soft)' }))
  CANDIDATES.forEach((c, i) => {
    const y = 92 + i * 72, dl = stagger(i, 120)
    const bar = s('rect', { x: X0, y: y - 13, width: S * c.bss, height: 26, rx: 6, style: { fill: 'var(--soft)' } })
    const val = text(X0 + S * c.bss + 8, y, c.bss.toFixed(4), { display: true })
    g.append(text(16, y - 13, c.label), text(16, y + 15, `${c.retrains} ${times(c.retrains)}`, { fill: 'var(--soft)' }), bar, val)
    moves.push(mv(bar, { kx: 0.001 }, {}, dl, 'left center', 360), mv(val, { o: 0 }, {}, dl + 260))
    if (c === chosen) {
      const pick = s('rect', { x: X0, y: y - 13, width: S * c.bss, height: 26, rx: 6, style: { fill: 'var(--pink)' } })
      g.append(pick)
      moves.push(mv(pick, { o: 0 }, {}, 1600, 'center', 360))
    }
    zones.push({ x: X0 + 120, y, t: `${c.label}: ${c.retrains} ${times(c.retrains)} за ${weeks} тижнів розробки, BSS ${c.bss.toFixed(4)}`
      + `${c === chosen ? ', обрано' : ''} (docs/adr/0013-retrain-cadence.md)` })
  })
  const rule = s('g', {},
    s('line', { x1: xl, x2: xl, y1: 62, y2: 340, style: { stroke: 'var(--pink)', strokeWidth: 2, strokeDasharray: '6 5' } }),
    text(xl, 48, `межа ${limit.toFixed(4)}`, { anchor: 'middle', fill: 'var(--pink)' }))
  const pickText = s('text', { x: 16, y: 372, 'dominant-baseline': 'central', 'font-size': 22, style: { fill: 'var(--ink)' } },
    s('tspan', { style: { fill: 'var(--pink)' }, text: 'вибір: ' }), s('tspan', { text: D.replay.cadence.words }))
  g.append(rule, pickText)
  moves.push(mv(rule, { x: S * MARGIN, o: 0 }, {}, 800, 'center', 400), mv(pickText, { o: 0 }, {}, 2000))
  zones.push({ x: xl, y: 200, t: `найкращий BSS ${best.bss.toFixed(4)} (${best.label}) мінус ${MARGIN} = ${limit.toFixed(4)}` })
  return stepper(g, moves, zones)
}

function notes(D) {
  const sp = D.split, P = Object.fromEntries(sp.parts.map((p) => [p.key, p]))
  const M = D.evaluation.models, fin = M.find((m) => m.role === 'finalist'), ref = M.find((m) => m.role === 'reference')
  const R = D.replay, rd = R.development, rt = R.test, tb = rt.table
  const kind = Object.fromEntries(D.examples.items.map((it) => [it.kind, it]))
  const ex = (it) => `${dm(it.t)}, ${it.window}: шанс ${pct(it.p)}, «${it.said}», а сталося: ${it.happened}`
  const most = (b) => real(b).reduce((a, x) => (x.n > a.n ? x : a))
  const gap = (b) => real(b).filter((x) => x.n >= 30).reduce((a, x) => (x.busy_share - x.p_mean > a.busy_share - a.p_mean ? x : a))
  const dB = most(rd.calibration), dG = gap(rd.calibration), tG = gap(rt.calibration), tL = real(rt.calibration)[0]
  const tAll = real(rt.calibration), above = tAll.filter((b) => b.busy_share > b.p_mean).length * 2 > tAll.length
  const { best, limit, pass, chosen } = cadence()
  const lo = Math.min(...CANDIDATES.map((c) => c.bss))
  const saidQuiet = tb.quiet_quiet + tb.quiet_busy, folds = sp.dev_folds.length
  return [
    `<p>Усі дані: ${num(sp.hours)} годин з ${dm(sp.first)} до ${dm(sp.last)}, кожна година це рядок (<b>site/data/trust.json</b>). ` +
      `Розробка: тут модель вчили й обирали; з ${dm(sp.folds_from)} вона ${num(folds)} ${times(folds)} вчилась на всьому минулому і прогнозувала наступний тиждень. ` +
      `Тест: останні ${num(sp.test_weeks)} тижнів з ${dm(sp.test_start)}, їх відкрили один раз, коли все вже обрали (docs/adr/0008-time-split.md). ` +
      `Під частинами години «зараз тихо» (тривоги немає, і в минулу годину нічого не прилітало) і частка тих, після яких за 3 години прилетіли дрони чи ракети.</p>`,
    `<p>BSS показує, на скільки прогноз точніший за просту частку: щотижня казати кожній годині ту саму частку неспокійних годин, відому на початок тижня; 0 так само, більше 0 краще. ` +
      `У моделі ${num(f3(fin.development.bss))} на розробці і ${num(f3(fin.test.bss))} на тесті; лінія навколо точки це 95% інтервал: число ${D.evaluation.n_boot} разів перерахували на випадково вибраних добах, і 95% результатів лягли на цій лінії. ` +
      `ROC AUC: візьмемо годину, коли прилетіло, і тиху; у ${num(Math.round(fin.test.roc_auc * 100))} з 100 таких пар на тесті модель дала першій вищу ймовірність (на розробці у ${Math.round(fin.development.roc_auc * 100)}), монетка дала б 50. ` +
      `Сіру частку за 7 днів модель на розробці перемогла (різниця BSS ${f3(fin.development.d_bss)}, увесь інтервал ${ci(fin.development.d_bss_ci)} вище 0), а на тесті ні: частка там теж добра (BSS ${f3(ref.test.bss)}), і інтервал різниці ${ci(fin.test.d_bss_ci)} накриває 0 (reports/quiet_leaderboard.md).</p>`,
    `<p>Кожна точка це година тесту «зараз тихо», їх ${num(rt.hours)}; «казала тихо» тут означає рівень «швидше тихо», p нижче ${R.busy_at}, інакше «неспокійно». ` +
      `Зелені: слово збіглося з тим, що сталося (${num(tb.quiet_quiet)} і ${num(tb.busy_busy)}); червоні: пропуск, казала «тихо», а прилетіло (${num(tb.quiet_busy)}); жовті: зайва тривога (${num(tb.busy_quiet)}). ` +
      `Восени модель казала «тихо» рідко, ${saidQuiet} ${times(saidQuiet)} з ${rt.hours}, і тоді справді було тихо у ${num(pct(rt.quiet_truth))} (<b>site/data/trust.json</b>, replay.test).</p>`,
    `<p>Точність це частка годин, де слово моделі збіглося з тим, що сталося. ` +
      `На розробці ліниве правило «завжди кажи тихо» має ${num(pct(rd.always_quiet_accuracy))}, більше за модель (${num(pct(rd.accuracy))}), але воно жодного разу не попереджає; на тесті «завжди кажи неспокійно» має ${pct(rt.always_busy_accuracy)} проти ${pct(rt.accuracy)} у моделі, бо восени прилітало після ${pct(rt.busy_share)} тихих годин. ` +
      `Тому межу ${R.busy_at} обирали не за точністю: правило, записане до тесту, вимагало ловити ${pct(RECALL)} неспокійних вікон розробки, бо пропустити атаку гірше за зайве попередження. ` +
      `У цьому перерахунку вона ловить ${num(pct(rd.busy_recall))} на розробці і ${num(pct(rt.busy_recall))} на тесті.</p>`,
    `<p>Калібрування: коли модель каже «прилетить з імовірністю X%», чи прилітає справді у X% таких годин. Точка це години з близькою p (крок 0.1), більша точка більше годин, пунктир це ідеал. ` +
      `На розробці точки біля лінії: казала ${pct(dB.p_mean)}, прилетіло після ${pct(dB.busy_share)} (${dB.n} годин); найдалі там, де казала ${pct(dG.p_mean)}, а прилетіло після ${pct(dG.busy_share)}. ` +
      `На тесті, восени, точки ${above ? 'вище лінії, тобто модель недооцінювала ризик' : 'нижче лінії, тобто модель переоцінювала ризик'}: казала ${num(pct(tG.p_mean))}, а прилетіло після ${num(pct(tG.busy_share))}${above ? ', бо атак стало більше, ніж у навчанні' : ''}; внизу, де модель каже «швидше тихо», вона й восени влучна: ${pct(tL.p_mean)} проти ${pct(tL.busy_share)}.</p>`,
    `<p>Чотири справжні години тесту, найвпевненіші свого виду за правилом у картці; час київський, «шанс» це p, ймовірність, що за 3 години прилетять дрони чи ракети. ` +
      `Влучила: ${ex(kind.right_quiet)}; ${ex(kind.right_high)}. ` +
      `Помилилась: ${ex(kind.miss)}, це пропуск; ${ex(kind.false_alarm)}, це зайва тривога. ` +
      'Тож низький шанс не обіцяє тиші, а високий не обіцяє атаки.</p>',
    `<p>Модель на сайті час від часу вчиться заново на свіжих годинах; питання, як часто (<b>docs/adr/0013-retrain-cadence.md</b>). ` +
      `Чотири кандидати перевірили на тих самих ${folds} тижнях розробки: BSS майже однаковий, від ${lo.toFixed(4)} до ${best.bss.toFixed(4)}. ` +
      `Правило записали до чисел: найрідше перенавчання, чий BSS не нижчий за найкращий мінус ${MARGIN}, тобто ${num(limit.toFixed(4))}. ` +
      `Межу пройшли ${pass.length === CANDIDATES.length ? 'всі чотири' : pass.length}, тож сайт перенавчає модель ${num(R.cadence.words)}: ${chosen.retrains} ${times(chosen.retrains)} за розробку замість ${best.retrains}.</p>`,
  ]
}

const CSS = `
.scene-trust { position: absolute; inset: 0; }
.scene-trust .tip { position: absolute; z-index: 2; max-width: 280px; padding: 6px 10px; border-radius: var(--r-small); background: var(--card);
  border: 1px solid var(--line); color: var(--ink); font-size: 14px; line-height: 1.35; pointer-events: none; }
.scene-trust .tip[hidden] { display: none; }
`
// trust.json missing, not JSON, or JSON without the fields the steps read (an empty file, an older schema): every step
// then says so calmly, instead of an error that makes the deck swap the whole scene for its placeholder
const STEPS = [stepSplit, stepScore, stepGrid, stepAccuracy, stepCalibration, stepExamples, stepCadence]
const MISSING = 'Не вдалось прочитати site/data/trust.json'
const MISSING_NOTE = '<p>Не вдалось прочитати <b>site/data/trust.json</b>: файла немає або в ньому бракує потрібних полів. Його пише scripts/site/trust.py.</p>'
const broken = (str) => /undefined|NaN|Infinity/.test(str)
function prepare(data) {
  try {
    const list = notes(data)
    // a dry run of every picture and its hover texts, nothing is shown: a gap in the data fails here, not on the stage
    const drawn = STEPS.map((f) => { const st = f(data); return `${st.g.textContent} ${st.zones.map((z) => z.t).join(' ')}` }).join(' ')
    return list.length === STEPS.length && !list.some(broken) && !broken(drawn) && typeof data.examples.rule === 'string' ? list : null
  } catch {
    return null
  }
}
const NOTES = T ? prepare(T) : null
const D = NOTES ? T : null
const CARDS = [[SPLIT], [MEASURES], [RULE], [RULE], [], D ? [examplesCard(D)] : [], [CHOICE]]

const scene = {
  id: 'trust',
  title: 'Наскільки можна вірити моделі',
  lead: 'Перевірка на годинах, яких модель не бачила: мірила, влучання, помилки і як часто вона вчиться заново.',
  steps: CARDS.map((prompts, i) => ({ note: NOTES ? NOTES[i] : MISSING_NOTE, prompts })),
  prompts: [],
  mount(stage) {
    const root = h('div', { class: 'scene-trust' }, h('style', { text: CSS }))
    stage.append(root)
    const svg = canvas(root, 'Наскільки можна вірити моделі: поділ годин, мірила, влучання і помилки, калібрування, приклади, перенавчання')
    const calm = () => {
      svg.replaceChildren(text(320, 200, MISSING, { anchor: 'middle', fill: 'var(--soft)' }))
      return { show() {}, destroy() {} }
    }
    if (!D) return calm()
    let S
    try {
      S = STEPS.map((f, i) => {
        const st = f(D)
        st.g.setAttribute('data-step', String(i + 1))
        svg.append(st.g)
        st.end()
        put(st.g, { o: 0 }, { instant: true })
        st.g.style.display = 'none'
        return st
      })
    } catch {
      return calm()
    }
    // hover or tap: the exact numbers behind the nearest mark
    const tip = h('div', { class: 'tip', role: 'tooltip', hidden: true })
    root.append(tip)
    let cur = -1
    let timers = []
    const later = (ms, f) => timers.push(setTimeout(f, ms))
    const clear = () => { timers.forEach(clearTimeout); timers = [] }
    function showTip(e) {
      const st = S[cur]
      if (!st) return
      const b = root.getBoundingClientRect()
      const ux = ((e.clientX - b.left) * 640) / b.width, uy = ((e.clientY - b.top) * 400) / b.height
      let best = null, bd = Infinity
      for (const z of st.zones) {
        const d = (z.x - ux) ** 2 + (z.y - uy) ** 2
        if (d < bd) { bd = d; best = z }
      }
      if (!best) return
      tip.textContent = best.t
      tip.hidden = false
      tip.style.left = `${Math.max(4, Math.min(e.clientX - b.left + 14, b.width - tip.offsetWidth - 4))}px`
      tip.style.top = `${Math.max(4, Math.min(e.clientY - b.top + 14, b.height - tip.offsetHeight - 4))}px`
    }
    svg.addEventListener('pointermove', showTip)
    svg.addEventListener('pointerdown', showTip)
    svg.addEventListener('pointerleave', () => { tip.hidden = true })

    // one group per step: the others fade out and leave the page, this one jumps to its end state or plays forward
    function show(k, { instant } = {}) {
      clear()
      tip.hidden = true
      const anim = !instant && !reduced()
      const fwd = anim && k === cur + 1
      cur = k
      S.forEach((st, j) => {
        if (j === k || st.g.style.display === 'none') return
        put(st.g, { o: 0 }, { instant: !anim, dur: 240 })
        if (anim) later(260, () => { st.g.style.display = 'none' })
        else st.g.style.display = 'none'
      })
      const st = S[k]
      if (!st) return
      const hidden = st.g.style.display === 'none'
      st.g.style.display = ''
      if (fwd) st.start()
      else st.end()
      if (hidden || fwd) put(st.g, { o: 0 }, { instant: true })
      svg.getBoundingClientRect()   // the start state is rendered before the first move
      put(st.g, { o: 1 }, { instant: !anim, dur: 300 })
      if (fwd) st.play(later)
    }
    return { show, destroy() { clear() } }
  },
}

export default scene
