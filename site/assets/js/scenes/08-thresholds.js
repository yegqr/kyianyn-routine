// Scene "thresholds" of the methodology deck: where the two lines of the risk scale come from. The bars are the
// forecasts the week-by-week check gave the training hours (site/data/dev_predictions.json, written by
// scripts/site/dev_predictions.py); the last step reads what each level meant on the test hours from
// site/data/trust.json (scripts/site/trust.py writes it).
import { h, s, canvas, put, reduced } from '../how.js'

const RULE = {
  title: 'Правило меж, записане наперед',
  source: 'коментар у коді прогнозу, переклад',
  text: `... Межі задали лише на навчальних даних (спокійні години) за записаними правилами, ніколи на тесті:
- попередження від BUSY_AT: найвища межа, яка ще ловить 80% вікон з атакою (docs/METHODOLOGY.md 4.4);
- високий ризик від HIGH_AT: верхня третина прогнозів на навчальних даних.
rules() рахує обидві межі заново; tests/test_quiet_forecast.py перевіряє, що вони досі такі.`,
}

const get = (name) => fetch(new URL(`../../../data/${name}`, import.meta.url))
  .then((r) => (r.ok ? r.json() : null)).catch(() => null)
const [ROWS, TRUST] = await Promise.all([get('dev_predictions.json'), get('trust.json')])

const RECALL = 0.8                                     // src/airalerts/quiet/forecast.py RECALL: 4 of 5 attacks
const LEVELS = [['low', 'низький'], ['medium', 'середній'], ['high', 'високий']]   // forecast.level()
const BANDS = 7                                        // 0-10%, 10-20% ... 50-60%, and 60-100% at the top
const X0 = 72, Y0 = 352, BH = 42, LEN = 210, P = 396   // the axis, its bottom, a band, the longest bar, the panel
const YT = Y0 - BANDS * BH                             // the top of the axis: 100%
const yOf = (p) => (p >= 0.6 ? Y0 - 6 * BH - ((p - 0.6) / 0.4) * BH : Y0 - p * 10 * BH)
// a line as the reader sees it: 0.197 is 19.7%, 0.3 is 30%
const pctx = (p) => { const t = (p * 100).toFixed(1); return `${t.endsWith('.0') ? t.slice(0, -2) : t}%` }
const day = (t) => `${t.slice(8, 10)}.${t.slice(5, 7)}`   // '2026-07-04 12:00' is 04.07
const word = (v) => (v % 10 === 1 && v % 100 !== 11 ? 'година'
  : [2, 3, 4].includes(v % 10) && ![12, 13, 14].includes(v % 100) ? 'години' : 'годин')
const n = (v) => `<span class="num">${v}</span>`
// file paths and code names live only in this folded block at the end of a note
const src = (text) => `<details class="how-src"><summary>Джерела</summary><p>${text}</p></details>`
const label = (x, y, str, { anchor = 'start', size = 22, fill = 'var(--ink)', display = false, bold = false } = {}) => {
  const style = { fill }
  if (display) style.fontFamily = 'var(--font-display)'
  if (bold) style.fontWeight = 600
  return s('text', { x, y, 'text-anchor': anchor, 'font-size': size, style, text: str })
}

// What the steps tell, from the two files; null when a file or a field is missing.
function facts(rows, trust) {
  const sp = trust?.split, test = trust?.replay?.test
  const pts = (Array.isArray(rows) ? rows : []).filter((r) => r && Number.isFinite(r.p))
    .map((r) => ({ p: r.p, busy: r.busy ? 1 : 0 })).sort((a, b) => a.p - b.p)
  if (!pts.length || !sp?.dev_folds || !sp.folds_from || !sp.test_start || !test?.tiers
    || LEVELS.some(([key]) => !test.tiers[key])) return null
  const N = pts.length
  const B = pts.reduce((a, d) => a + d.busy, 0)
  const caught = (v) => pts.reduce((a, d) => a + (d.busy && d.p >= v ? 1 : 0), 0)
  // forecast.rules(): the highest line whose warnings (a forecast at or above it) still catch 80% of the attacks ...
  let l1 = pts[0].p
  for (let r = N - 1, got = 0; r >= 0; r--) {
    got += pts[r].busy
    if ((r === 0 || pts[r - 1].p < pts[r].p) && got >= RECALL * B) { l1 = pts[r].p; break }
  }
  // ... and the high risk: the upper third, from the forecast two thirds up the sorted list
  const l2 = pts[Math.floor((2 * N) / 3)].p
  // forecast.py keeps both lines rounded to 3 digits (0.1968 to 0.197, 0.2997 to 0.3): count with the lines the site
  // uses, so розділ 9 and 10 show the same 354 and 266
  const r3 = (v) => Math.round(v * 1000) / 1000
  return {
    pts, N, B, caught, l1: r3(l1), l2: r3(l2), top: pts.filter((d) => d.p >= r3(l2)).length,
    weeks: sp.dev_folds.length, from: day(sp.folds_from), testWeeks: sp.test_weeks, testFrom: day(sp.test_start),
    // trust.json keeps the share of the hours with an attack; times the hours it gives back the count
    tiers: LEVELS.map(([key, name]) => ({ name, hours: test.tiers[key].hours,
      busy: Math.round(test.tiers[key].hours * test.tiers[key].busy_share) })),
  }
}
const F = facts(ROWS, TRUST)
const ten = (t) => Math.round((t.busy / t.hours) * 10)

const NOTES = F && [
  `<p>Це ${n(F.N)} годин навчальних даних (${F.weeks} тижнів з ${F.from}), коли в Києві було тихо. ` +
    'Кожній з них модель, навчена лише на попередніх тижнях, дала <b>прогноз</b>: ймовірність атаки в наступні 3 години. ' +
    `Рожеве: після ${F.B} годин атака справді була, приблизно ${ten({ busy: F.B, hours: F.N })} з 10; сіре: після ` +
    `${F.N - F.B} не було, і чим вищий прогноз, тим більша рожева частка.</p>` +
    src('site/data/dev_predictions.json, її пише scripts/site/dev_predictions.py; site/data/trust.json, split.'),
  `<p><b>Межа</b>: прогноз, від якого сайт уже попереджає; атаку <b>спіймано</b>, якщо прогноз перед нею був не нижче межі. ` +
    'Правило веде межу згори вниз і зупиняє, щойно спіймано <b>4 з 5 атак</b> (80%), бо нижче лише більше зайвих попереджень. ' +
    `Так вийшло ${n(pctx(F.l1))}: спіймано ${F.caught(F.l1)} з ${F.B}, майже 4 з 5.</p>` +
    src('docs/METHODOLOGY.md, 4.4; docs/quiet/forecast.md, «Звідки межі»; src/airalerts/quiet/forecast.py, rules(), RECALL = 0.8; правило дало 0.1968, а forecast.py зберігає межу округленою до 0.197 (BUSY_AT), тож спіймано трохи менше 80%.'),
  '<p>Друга межа ділить попередження на середній і високий ризик. ' +
    `Правило: високий ризик це <b>верхня третина</b> всіх прогнозів, ${F.top} з ${F.N} годин, і вона починається з ${n(pctx(F.l2))}. ` +
    `Отже нижче ${pctx(F.l1)} ризик низький, від ${pctx(F.l1)} до ${pctx(F.l2)} середній, від ${pctx(F.l2)} високий.</p>` +
    src('docs/quiet/forecast.md, «Звідки межі»; src/airalerts/quiet/forecast.py, rules() і level(); tests/test_quiet_forecast.py.'),
  `<p><b>Тестові дані</b>: ${F.testWeeks} тижнів з ${F.testFrom}, відкладені до кінця і відкриті один раз. ` +
    `Після низького ризику атака була у ${n(`${F.tiers[0].busy} з ${F.tiers[0].hours}`)} годин, приблизно ${ten(F.tiers[0])} з 10, ` +
    `після високого у ${n(`${F.tiers[2].busy} з ${F.tiers[2].hours}`)}, приблизно ${ten(F.tiers[2])} з 10. ` +
    'Тож рівні справді різні, але й низький ризик не означає «точно тихо».</p>' +
    src('site/data/trust.json, replay.test.tiers, його пише scripts/site/trust.py; docs/adr/0008-time-split.md.'),
]
const MISSING = '<p>Не вдалося прочитати дані: файла немає або в ньому бракує потрібних полів.</p>' +
  src('site/data/dev_predictions.json і site/data/trust.json, їх пишуть scripts/site/dev_predictions.py і scripts/site/trust.py.')

function draw(svg) {
  const bands = Array.from({ length: BANDS }, () => ({ busy: [], calm: [] }))
  for (const d of F.pts) bands[Math.min(BANDS - 1, Math.floor(d.p * 10 + 1e-9))][d.busy ? 'busy' : 'calm'].push(d.p)
  const per = LEN / Math.max(...bands.map((b) => b.busy.length + b.calm.length))   // units per hour
  // a band: the hours with an attack from the axis, then the hours without; the bright copies on top light up
  // the hours at or above a line, the pale ones under them stay
  const bars = bands.map((b, i) => {
    const y = Y0 - (i + 1) * BH + 5, wb = b.busy.length * per, wc = b.calm.length * per
    const rect = (x, width, style) => s('rect', { x, y, width, height: BH - 10, style })
    const busyEl = rect(X0, wb, { fill: 'var(--pink)' })
    const calmEl = rect(X0 + wb, wc, { fill: 'var(--soft)', fillOpacity: 0.55 })
    const g = s('g', {}, rect(X0, wb, { fill: 'var(--pink-soft)' }), rect(X0 + wb, wc, { fill: 'var(--soft)', fillOpacity: 0.15 }),
      busyEl, calmEl)
    return { ...b, g, busyEl, calmEl }
  })
  // a line ends in a dark tag with its value, so the tag never reads as a part of the panel next to it
  const line = (v) => {
    const lab = label(X0 + LEN + 50, YT + 7, pctx(v), { anchor: 'middle', size: 20, display: true, fill: 'var(--card)' })
    const g = s('g', {}, s('path', { d: `M${X0 - 6},${YT}H${X0 + LEN + 8}`, style: { stroke: 'var(--ink)', strokeWidth: 3 } }),
      s('rect', { x: X0 + LEN + 8, y: YT - 15, width: 84, height: 30, rx: 15, style: { fill: 'var(--ink)' } }), lab)
    return { g, lab }
  }
  const L1 = line(F.l1), L2 = line(F.l2)
  const chart = s('g', {},
    s('path', { d: `M${X0},${YT}V${Y0}`, style: { stroke: 'var(--line)', strokeWidth: 2 } }),
    ...[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 1].map((v) =>
      label(X0 - 10, yOf(v) + 7, `${Math.round(v * 100)}%`, { anchor: 'end', size: 20, fill: 'var(--soft)' })),
    ...bars.map((b) => b.g), L1.g, L2.g,
    label(X0, Y0 + 32, 'довжина смуги: кількість годин', { size: 20, fill: 'var(--soft)' }))

  // the panel on the right: counts, and blocks that fill up to 4 of 5 attacks or 1 of 3 hours
  const blocks = (count, fill) => {
    const w = (624 - P - (count - 1) * 8) / count
    return Array.from({ length: count }, (_, i) => {
      const el = s('rect', { x: P + i * (w + 8), y: 198, width: w, height: 40, rx: 4, style: { fill } })
      return { el, g: s('g', {}, s('rect', { x: P + i * (w + 8), y: 198, width: w, height: 40, rx: 4, style: { fill: 'var(--line)' } }), el) }
    })
  }
  const fill = (bl, value, size, o) => bl.forEach((b, i) =>
    put(b.el, { kx: Math.max(0, Math.min(1, value / size - i)) }, { origin: 'left', ...o }))
  const B5 = blocks(5, 'var(--pink)'), B3 = blocks(3, 'var(--ink)')
  const cnt = label(P, 146, '', { size: 48, display: true, fill: 'var(--pink)' })
  const four = s('g', {}, label(P, 304, '4 з 5', { size: 34, display: true }),
    label(P, 334, `кожен блок: ${Math.round(F.B / 5)} атак`, { size: 20, fill: 'var(--soft)' }))
  const swatch = (y, style) => s('rect', { x: P, y, width: 24, height: 24, rx: 4, style })
  const P0 = s('g', {},
    swatch(76, { fill: 'var(--pink)' }), label(P + 36, 100, String(F.B), { size: 40, display: true, fill: 'var(--pink)' }),
    label(P, 132, `${word(F.B)} з атакою`),
    swatch(166, { fill: 'var(--soft)', fillOpacity: 0.55 }), label(P + 36, 190, String(F.N - F.B), { size: 40, display: true, fill: 'var(--soft)' }),
    label(P, 222, `${word(F.N - F.B)} без атаки`),
    label(P, 290, `разом ${F.N} ${word(F.N)}`, { fill: 'var(--soft)' }))
  const P1 = s('g', {}, label(P, 92, 'спіймано'), cnt, label(P, 178, `з ${F.B} атак`), ...B5.map((b) => b.g), four)
  const P2 = s('g', {}, label(P, 92, `від ${pctx(F.l2)}`), label(P, 146, String(F.top), { size: 48, display: true }),
    label(P, 178, `з ${F.N} годин`), ...B3.map((b) => b.g),
    label(P, 304, '1 з 3', { size: 34, display: true }), label(P, 334, 'верхня третина', { size: 20, fill: 'var(--soft)' }))

  // the last step: one row per level on the test hours, the pink part of a bar is the share with an attack after it
  const range = [`нижче ${pctx(F.l1)}`, `від ${pctx(F.l1)} до ${pctx(F.l2)}`, `від ${pctx(F.l2)}`]
  const rows = F.tiers.map((t, i) => {
    const c = 100 + i * 92
    const bar = s('rect', { x: 200, y: c - 20, width: 220, height: 40, rx: 4, style: { fill: 'var(--pink)' } })
    const g = s('g', {}, label(16, c - 2, t.name, { size: 24, bold: true }), label(16, c + 26, range[i], { size: 20, fill: 'var(--soft)' }),
      s('rect', { x: 200, y: c - 20, width: 220, height: 40, rx: 4, style: { fill: 'var(--soft)', fillOpacity: 0.3 } }), bar,
      label(436, c + 4, `${t.busy} з ${t.hours}`, { size: 28, display: true, fill: 'var(--pink)' }),
      label(436, c + 32, `приблизно ${ten(t)} з 10`, { size: 20, fill: 'var(--soft)' }))
    return { t, c, g, bar, share: t.busy / t.hours }
  })
  const P3 = s('g', {}, ...rows.map((r) => r.g),
    s('rect', { x: 16, y: 356, width: 22, height: 22, rx: 4, style: { fill: 'var(--pink)' } }),
    label(48, 375, 'атака в наступні 3 години', { size: 20 }),
    s('rect', { x: 330, y: 356, width: 22, height: 22, rx: 4, style: { fill: 'var(--soft)', fillOpacity: 0.3 } }),
    label(362, 375, 'без атаки', { size: 20 }))

  const head = label(16, 30, '', { bold: true })
  const HEAD = ['Скільки годин мали який прогноз', 'Межа йде вниз, доки не спіймає 4 з 5 атак',
    `З ${pctx(F.l2)} починається верхня третина прогнозів`, 'Тестові дані: як часто після рівня була атака']
  const panels = [P0, P1, P2, P3]
  svg.append(chart, head, ...panels)

  const share = (arr, v) => (arr.length ? arr.filter((p) => p >= v).length / arr.length : 0)
  const light = (busyFrom, calmFrom, o) => bars.forEach((b) => {
    put(b.busyEl, { kx: share(b.busy, busyFrom) }, { origin: 'left', ...o })
    put(b.calmEl, { kx: share(b.calm, calmFrom) }, { origin: 'left', ...o })
  })

  function end(k, instant, intro = false) {
    const o = (delay = 0) => ({ instant, delay: instant ? 0 : delay })
    head.textContent = HEAD[k]
    put(chart, { o: k < 3 ? 1 : 0 }, o())
    if (intro) {   // the bands grow out of the axis
      bars.forEach((b) => put(b.g, { kx: 0 }, { origin: 'left', instant: true }))
      svg.getBoundingClientRect()
    }
    bars.forEach((b, i) => put(b.g, {}, { origin: 'left', ...o(intro ? 100 + i * 70 : 0) }))
    light(k === 0 ? 0 : k === 1 ? F.l1 : F.l2, k === 0 ? 0 : k === 1 ? Infinity : F.l2, o())
    L1.lab.textContent = pctx(F.l1)
    put(L1.g, { y: yOf(F.l1) - YT, o: k === 1 || k === 2 ? 1 : 0 }, o())
    put(L2.g, { y: yOf(F.l2) - YT, o: k === 2 ? 1 : 0 }, o())
    panels.forEach((p, i) => put(p, { o: i === k ? 1 : 0 }, o(i === k ? 150 : 0)))
    cnt.textContent = F.caught(F.l1)
    fill(B5, F.caught(F.l1), F.B / 5, o(200))
    put(four, {}, o())
    fill(B3, F.top, F.N / 3, o(250))
    rows.forEach((r, i) => put(r.bar, { kx: k === 3 ? r.share : 0 }, { origin: 'left', ...o(k === 3 ? 300 + i * 150 : 0) }))
  }

  // step 2 told forward: the line goes down from 100% band by band, the counter and the blocks follow it
  function sweep(later) {
    head.textContent = HEAD[1]
    put(L1.g, { o: 0 }, { instant: true })
    L1.g.getBoundingClientRect()
    L1.lab.textContent = '100%'
    put(L1.g, {})
    light(Infinity, Infinity, {})
    cnt.textContent = '0'
    fill(B5, 0, 1, {})
    put(four, { o: 0 }, { instant: true })
    panels.forEach((p, i) => put(p, { o: i === 1 ? 1 : 0 }))
    const stops = [0.6, 0.5, 0.4, 0.3, 0.2].filter((v) => v > F.l1).concat(F.l1)
    stops.forEach((v, i) => later(500 + i * 450, () => {
      put(L1.g, { y: yOf(v) - YT }, { dur: 380 })
      L1.lab.textContent = pctx(v)
      light(v, Infinity, { dur: 380 })
      cnt.textContent = F.caught(v)
      fill(B5, F.caught(v), F.B / 5, { dur: 380 })
    }))
    later(500 + stops.length * 450, () => put(four, {}))
  }

  end(0, true)
  return {
    end,
    sweep,
    near(ux, uy, k) {
      if (k === 3) {
        const r = rows.find((x) => Math.abs(uy - x.c) < 46)
        return r ? `${r.t.name} ризик: ${r.t.hours} ${word(r.t.hours)}, після ${r.t.busy} з них атака` : ''
      }
      if (ux > P - 8 || uy < YT || uy > Y0) return ''
      const i = Math.min(BANDS - 1, Math.floor((Y0 - uy) / BH)), b = bands[i], all = b.busy.length + b.calm.length
      const r = i < BANDS - 1 ? `від ${i * 10}% до ${i * 10 + 10}%` : 'від 60% до 100%'
      // a band the line cuts: how many of its hours are above the line, the short bright part of its bar; left out
      // when the line reads as the band's top edge (30%), or the tip would say «вище 30%» under 30%
      const v = k === 1 ? F.l1 : F.l2, up = (k === 1 ? b.busy : b.busy.concat(b.calm)).filter((p) => p >= v).length
      const cut = k > 0 && up > 0 && up < (k === 1 ? b.busy.length : all) && pctx(v) !== `${(i + 1) * 10}%`
      return `прогноз ${r}: ${all} ${word(all)}, після ${b.busy.length} з них атака`
        + (cut ? (k === 1 ? `; спіймано з них ${up}` : `; вище ${pctx(v)} з них ${up}`) : '')
    },
  }
}

const scene = {
  id: 'thresholds',
  title: 'Звідки взялися межі ризику',
  lead: F ? `Межі ризику дало правило, записане до будь-яких чисел: ${pctx(F.l1)} ловить 4 з 5 атак, ` +
    `а з ${pctx(F.l2)} починається верхня третина прогнозів.`
    : 'Межі ризику дало правило, записане до будь-яких чисел, на навчальних даних.',
  steps: (NOTES || Array(4).fill(MISSING)).map((note) => ({ note })),
  prompts: [RULE],
  mount(stage) {
    const root = h('div', { class: 'scene-thresholds' }, h('style', { text: '.scene-thresholds { position: absolute; inset: 0; } .scene-thresholds .tip { position: absolute; z-index: 2; max-width: 260px; '
      + 'padding: 6px 10px; border-radius: var(--r-small); background: var(--card); border: 1px solid var(--line); color: var(--ink); font-size: 15px; '
      + 'line-height: 1.35; pointer-events: none; } .scene-thresholds .tip[hidden] { display: none; } '
      + '@media (max-width: 600px) { .scene-thresholds .tip { max-width: 220px; font-size: 14px; } }' }))
    stage.append(root)
    const svg = canvas(root, 'Прогнози навчальних годин смугами від низьких до високих, дві межі ризику і що було після кожного рівня на тестових даних')
    if (!F) {
      svg.append(label(320, 200, 'Не вдалося завантажити дані', { anchor: 'middle', fill: 'var(--soft)' }))
      return { show() {}, destroy() {} }
    }
    const tip = h('div', { class: 'tip', role: 'tooltip', hidden: true })
    root.append(tip)
    const view = draw(svg)
    let cur = -1
    let timers = []
    const later = (ms, f) => timers.push(setTimeout(f, ms))
    const clear = () => { timers.forEach(clearTimeout); timers = [] }
    const showTip = (e) => {
      const b = root.getBoundingClientRect()
      const text = view.near(((e.clientX - b.left) * 640) / b.width, ((e.clientY - b.top) * 400) / b.height, cur)
      tip.hidden = !text
      if (!text) return
      tip.textContent = text
      tip.style.left = `${Math.max(4, Math.min(e.clientX - b.left + 14, b.width - tip.offsetWidth - 4))}px`
      tip.style.top = `${Math.max(4, Math.min(e.clientY - b.top + 14, b.height - tip.offsetHeight - 4))}px`
    }
    svg.addEventListener('pointermove', showTip)
    svg.addEventListener('pointerdown', showTip)
    // only a mouse leaving hides the tip: a finger fires pointerleave, and then mouseleave, as soon as it lifts
    svg.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse') tip.hidden = true })

    return {
      show(k, { instant } = {}) {
        clear()
        tip.hidden = true
        const anim = !instant && !reduced()
        const intro = k === 0 && cur === -1 && !reduced()
        if (anim && k === 1 && cur === 0) view.sweep(later)
        else view.end(k, !anim && !intro, intro)
        cur = k
      },
      destroy() { clear() },
    }
  },
}

export default scene
