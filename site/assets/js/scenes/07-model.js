// Scene "model" of the methodology deck: how the frozen quiet model turns 7 numbers about an hour into one
// probability, step by step, with its real weights from api/model.json (fallback: docs/quiet/model.md sections 4, 5, 7).
import { h, s, canvas, put, reduced } from '../how.js'

const SIGNALS = {
  title: 'Входи моделі',
  source: 'src/airalerts/quiet/linear.py',
  text: `EVENING = (18, 23)                   # Kyiv hours, both included

# A feature is (column, how): "sin" and "cos" of the Kyiv hour on the 24 h circle, "evening" a 0/1 flag, "log1p", "raw".
SMALL = (("hour_kyiv", "sin"), ("hour_kyiv", "cos"), ("hour_kyiv", "evening"), ("hours_since_busy", "log1p"))
SIGNALS = SMALL + (("p_drone_max_1h", "raw"), ("s4_kyiv_6h", "raw"), ("s4_3h", "raw"), ("posts_jev_1h", "log1p"),
                   ("hours_since_drone", "log1p"))`,
}
const FORMULA = {
  title: 'Формула',
  source: 'src/airalerts/live/model.py',
  text: 'A fitted model as api/model.json: p = 1 / (1 + exp(-(intercept + sum(coef * (x - mean) / scale)))).',
}

// When api/model.json is missing: docs/quiet/model.md section 5 (means, spreads, weights), sections 4 and 7 (the shift
// -0.729, the scale 0.197 and 0.300).
const FALLBACK = {
  source: 'docs/quiet/model.md, розділи 4, 5 і 7',
  intercept: -0.729, busy_at: 0.197, high_at: 0.3, evening: [18, 23],
  features: [
    { column: 'hour_kyiv', how: 'sin', mean: 0.002, scale: 0.707, coef: -0.067 },
    { column: 'hour_kyiv', how: 'cos', mean: 0.001, scale: 0.707, coef: 0.044 },
    { column: 'hour_kyiv', how: 'evening', mean: 0.249, scale: 0.433, coef: 0.281 },
    { column: 'hours_since_busy', how: 'log1p', mean: 1.82, scale: 1.185, coef: -0.41 },
    { column: 'p_drone_max_1h', how: 'raw', mean: 0.177, scale: 0.258, coef: 0.242 },
    { column: 's4_kyiv_6h', how: 'raw', mean: 0.57, scale: 1.547, coef: 0.628 },
    { column: 's4_3h', how: 'raw', mean: 5.751, scale: 2.297, coef: 0.121 },
    { column: 'posts_jev_1h', how: 'log1p', mean: 1.728, scale: 1.269, coef: 0.138 },
    { column: 'hours_since_drone', how: 'log1p', mean: 2.658, scale: 1.335, coef: 0.182 },
  ],
}

// The base quiet hour of docs/quiet/model.md section 6 and its "together" case (+1.184 points, 77% there).
const BASE = { hour_kyiv: 14, hours_since_busy: 12, hours_since_drone: 24, p_drone_max_1h: 0.05, s4_kyiv_6h: 0, s4_3h: 5, posts_jev_1h: 8 }
const BASE_WI = { hour: 14, waves: 0, since: 12, pdrone: 0.05 }
const TOGETHER_WI = { hour: 21, waves: 2, since: 2, pdrone: 0.6 }
const CONTROLS = [
  { key: 'hour', label: 'година доби', min: 0, max: 23, fmt: (v) => `${v}:00` },
  { key: 'waves', label: 'хвилі на Київ', min: 0, max: 8, fmt: (v) => String(v) },
  { key: 'since', label: 'від атаки, год', min: 1, max: 72, fmt: (v) => `${v} год` },
]

const LABEL = {
  hour_kyiv: 'година', hours_since_busy: 'від атаки, год', p_drone_max_1h: 'пости про дрони',
  s4_kyiv_6h: 'хвилі на Київ', s4_3h: 'запуски за 3 год', posts_jev_1h: 'постів за год', hours_since_drone: 'від дронів, год',
}
const LOG = { hours_since_busy: 'від атаки, log', posts_jev_1h: 'постів, log', hours_since_drone: 'від дронів, log' }
const HOWS = ['sin', 'cos', 'evening', 'log1p', 'raw']
const CAPTION = ['7 входів', '9 чисел', 'одна шкала', 'множимо на ваги', 'плюс зсув: бали', 'S-крива: бали стають p', 'що якщо']
const LEVEL = ['швидше тихо', 'середній ризик', 'високий ризик']   // src/airalerts/quiet/forecast.py level()

// geometry in the 640 x 400 units of the canvas
const XL = 16, XV = 330, X0 = 470, RAW = 25, U = 50, BAR = 50, P = 67.5
const AX = { zero: 340, y: 220, h: 160, lo: -4, hi: 4 }
const EQ = [284, 318, 352], EQX = 400
const ax = (score) => AX.zero + Math.max(AX.lo, Math.min(AX.hi, score)) * P
const ay = (p) => AX.y - p * AX.h
const sig = (z) => 1 / (1 + Math.exp(-z))

const num = (v, d) => (Number.isFinite(v) ? v : d)
const pct = (p) => `${Math.round(p * 100)}%`
const plain = (v) => (Number.isInteger(v) ? String(v) : Math.abs(v) < 0.005 ? '0' : v.toFixed(2))
function sign(v, d = 2) {
  const t = Math.abs(v).toFixed(d)
  return Number(t) === 0 ? t : (v < 0 ? '-' : '+') + t
}

function pick(m) {
  const ok = m && Number.isFinite(m.intercept) && Array.isArray(m.features) && m.features.length > 0 &&
    m.features.every((f) => f && f.column in LABEL && HOWS.includes(f.how) && Number.isFinite(f.mean) &&
      Number.isFinite(f.scale) && f.scale > 0 && Number.isFinite(f.coef))
  if (!ok) return FALLBACK
  const day = typeof m.trained_at === 'string' ? m.trained_at.slice(0, 10) : ''
  return {
    ...m,
    evening: Array.isArray(m.evening) && m.evening.length === 2 ? m.evening : FALLBACK.evening,
    busy_at: num(m.busy_at, FALLBACK.busy_at), high_at: num(m.high_at, FALLBACK.high_at),
    source: day ? `api/model.json, навчена ${day}` : 'api/model.json',
  }
}

function transform(how, v, ev) {
  if (how === 'sin') return Math.sin((2 * Math.PI * v) / 24)
  if (how === 'cos') return Math.cos((2 * Math.PI * v) / 24)
  if (how === 'evening') return v >= ev[0] && v <= ev[1] ? 1 : 0
  if (how === 'log1p') return Math.log1p(v)
  return v
}

// p = 1 / (1 + exp(-(intercept + sum(coef * (x - mean) / scale)))), x after its transform
function compute(m, x) {
  let sum = 0
  const parts = m.features.map((f) => {
    const t = transform(f.how, x[f.column], m.evening)
    const z = (t - f.mean) / f.scale
    sum += f.coef * z
    return { t, z, w: f.coef * z }
  })
  const score = m.intercept + sum
  return { parts, sum, score, p: sig(score) }
}

// Drones are an attack too, so the last drones are never fresher than the last attack (docs/quiet/model.md section 6).
const whatIf = (wi) => ({ ...BASE, hour_kyiv: wi.hour, s4_kyiv_6h: wi.waves, hours_since_busy: wi.since,
  hours_since_drone: Math.max(BASE.hours_since_drone, wi.since), p_drone_max_1h: wi.pdrone })

function label9(f, ev) {
  if (f.how === 'sin' || f.how === 'cos') return `година, ${f.how}`
  if (f.how === 'evening') return `вечір ${ev[0]}..${ev[1]}`
  return f.how === 'log1p' ? LOG[f.column] || `${LABEL[f.column]}, log` : LABEL[f.column]
}

function text(x, y, str, { anchor = 'start', size = 22, display = false, fill = 'var(--body)' } = {}) {
  const style = { fill }
  if (display) style.fontFamily = 'var(--font-display)'
  return s('text', { x, y, 'text-anchor': anchor, 'dominant-baseline': 'central', 'font-size': size, style, text: str })
}

const CSS = `
.scene-model { position: absolute; inset: 0; }
.scene-model .wi { position: absolute; left: 0; right: 0; bottom: 0; height: 50%; box-sizing: border-box; padding: 6px 16px 8px;
  display: grid; grid-template-rows: repeat(4, minmax(0, 1fr)); align-items: center; background: var(--card);
  border-top: 1px solid var(--line); font-size: 15px; color: var(--body); }
.scene-model .wi[hidden] { display: none; }
.scene-model .wi-row { display: grid; grid-template-columns: minmax(0, 8fr) minmax(0, 11fr) minmax(0, 4fr); gap: 12px; align-items: center; }
.scene-model .wi-row label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.scene-model .wi-row output { font-family: var(--font-display); color: var(--ink); text-align: right; white-space: nowrap; font-size: 14px; }
.scene-model input[type=range] { width: 100%; min-width: 0; height: 24px; margin: 0; font-size: 16px; accent-color: var(--pink); cursor: pointer; }
.scene-model input[type=range]:focus-visible { outline: none; box-shadow: var(--focus-ring); border-radius: var(--r-pill); }
.scene-model .wi-presets { display: flex; gap: 8px; align-items: center; min-width: 0; }
.scene-model .wi-pill { font: inherit; font-size: 14px; height: 30px; padding: 0 14px; border-radius: var(--r-pill); border: 1px solid var(--line);
  background: var(--card); color: var(--ink); cursor: pointer; flex: none; }
.scene-model .wi-pill:hover { border-color: var(--pink); }
.scene-model .wi-pill[aria-pressed="true"] { border-color: var(--pink); color: var(--pink); }
.scene-model .wi-pill:focus-visible { outline: none; box-shadow: var(--focus-ring); }
.scene-model .wi-fixed { color: var(--soft); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.scene-model .wi-live { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.scene-model .tip { position: absolute; z-index: 2; max-width: 280px; padding: 6px 10px; border-radius: var(--r-small); background: var(--card);
  border: 1px solid var(--line); color: var(--ink); font-size: 14px; line-height: 1.35; pointer-events: none; }
.scene-model .tip[hidden] { display: none; }
@media (max-width: 600px) {
  .scene-model .wi { padding: 2px 10px 4px; font-size: 13px; }
  .scene-model .wi-row { gap: 8px; }
  .scene-model .wi-row output { font-size: 12px; }
  .scene-model .wi-pill { height: 26px; padding: 0 10px; font-size: 13px; }
}
`

function notes(M, R, T) {
  const ev = M.evening
  const top = M.features.reduce((a, f) => (Math.abs(f.coef) > Math.abs(a.coef) ? f : a))
  const hsb = M.features.find((f) => f.column === 'hours_since_busy')
  const name = (f) => f.text || LABEL[f.column]
  const level = (p) => LEVEL[p < M.busy_at ? 0 : p < M.high_at ? 1 : 2]
  return [
    '<p>Модель дивиться на сім чисел про годину. Візьмемо базову тиху годину з розділу 6 <b>docs/quiet/model.md</b>: ' +
      '14:00, атака була 12 год тому, дрони 24 год тому, пости моніторів про дрони 0.05, 0 хвиль дронів з курсом на Київ, ' +
      '5 запусків за 3 год і 8 постів за годину.</p>',
    `<p>Година стає трьома числами: sin і cos на колі з 24 годин (тоді 23:00 стоїть поруч з 0:00) і прапорець «вечір ${ev[0]}..${ev[1]}». ` +
      'Години й пости беремо як log(1 + x): різниця між 1 і 3 годинами тиші важить більше, ніж між 100 і 102. ' +
      `Разом <span class="num">${M.features.length}</span> чисел (розділ 4 <b>docs/quiet/model.md</b>).</p>`,
    '<p>Числа мають різні одиниці: години, частки, штуки. Від кожного віднімаємо середнє і ділимо на розкид, обидва з годин навчання: ' +
      'рисочки середніх з’їжджаються в 0, і тепер +1 означає «на один розкид більше, ніж зазвичай». ' +
      `Середні й розкиди: <b>${M.source}</b>.</p>`,
    `<p>Кожне число множимо на його вагу. Найбільша вага в колонки «${name(top)}» (<span class="num">${sign(top.coef)}</span>)` +
      (hsb ? `, від’ємна в давності атаки (<span class="num">${sign(hsb.coef)}</span>): що довша тиша, то нижчий ризик` : '') +
      `. Добутки стають в один ряд, їхня сума <span class="num">${sign(R.sum)}</span>.</p>`,
    `<p>До суми додаємо зсув (intercept) <span class="num">${sign(M.intercept)}</span>: так модель запам’ятала звичайний рівень ризику. ` +
      `Виходять бали, або logit: <span class="num">${sign(R.score)}</span> для базової години. 0 балів означало б 50 на 50.</p>`,
    `<p>S-крива p = 1 / (1 + e^(-бали)) стискає будь-які бали в ймовірність від 0 до 1: ${sign(R.score)} бала дають <span class="num">${pct(R.p)}</span>. ` +
      `Пунктири це межі шкали з наступного кроку: від ${M.busy_at.toFixed(3)} «середній ризик», від ${M.high_at.toFixed(3)} «високий ризик». ` +
      `Базова година тут «${level(R.p)}».</p>`,
    '<p>Посувайте повзунки мишею або стрілками клавіатури: p рахується тут же, тими самими вагами. ' +
      'Кнопка «разом» ставить випадок з розділу 6 <b>docs/quiet/model.md</b>: 21:00, атака 2 год тому, пости про дрони 0.6, 2 хвилі на Київ; там вийшло 77%. ' +
      (M === FALLBACK ? `Тут ваги з того ж розділу 5, і виходить <span class="num">${pct(T.p)}</span>.</p>`
        : `Тут ваги з <b>${M.source}</b>, тому число може трохи відрізнятись: <span class="num">${pct(T.p)}</span>.</p>`),
  ]
}

const scene = {
  id: 'model',
  title: 'Модель крок за кроком',
  lead: 'Сім чисел про годину стають однією ймовірністю: перетворення, одна шкала, ваги, S-крива.',
  steps: [
    { note: '', prompts: [SIGNALS] }, { note: '', prompts: [SIGNALS] }, { note: '', prompts: [FORMULA] },
    { note: '', prompts: [FORMULA] }, { note: '', prompts: [FORMULA] }, { note: '', prompts: [FORMULA] },
    { note: '', prompts: [FORMULA] },
  ],
  prompts: [],
  mount(stage, data) {
    const M = pick(data?.model)
    const R = compute(M, BASE)
    const T = compute(M, whatIf(TOGETHER_WI))
    notes(M, R, T).forEach((n, i) => { scene.steps[i].note = n })
    const level = (p) => LEVEL[p < M.busy_at ? 0 : p < M.high_at ? 1 : 2]

    const root = h('div', { class: 'scene-model' }, h('style', { text: CSS }))
    stage.append(root)
    const svg = canvas(root, 'Як сім чисел про годину стають однією ймовірністю')
    const cols = [...new Set(M.features.map((f) => f.column))]
    const n9 = M.features.length
    const g9 = Math.min(36, 288 / Math.max(1, n9 - 1))
    const g7 = Math.min(44, 264 / Math.max(1, cols.length - 1))
    const Y9 = (j) => 56 + j * g9
    const Y7 = (i) => 70 + i * g7
    const top = Y9(0) - 20, bot = Y9(n9 - 1) + 20

    // the table: 7 inputs, then 9 numbers with their number lines
    const caption = text(XL, 20, CAPTION[0], { fill: 'var(--soft)' })
    const zero = s('line', { x1: X0, x2: X0, y1: top, y2: bot, style: { stroke: 'var(--line)', strokeWidth: 2 } })
    const brackets = s('path', { d: `M236,${top}H228V${bot}H236M334,${top}H342V${bot}H334`,
      style: { fill: 'none', stroke: 'var(--ink)', strokeWidth: 2 } })
    const ins = cols.map((c, i) => ({
      label: text(XL, Y7(i), LABEL[c]),
      value: text(XV, Y7(i), c === 'hour_kyiv' ? `${BASE[c]}:00` : plain(BASE[c]), { anchor: 'end', display: true, fill: 'var(--ink)' }),
      to: M.features.findIndex((f) => f.column === c),
    }))
    let cum = 0
    const rows = M.features.map((f, j) => {
      const y = Y9(j)
      const q = R.parts[j]
      const r = {
        f, q, y, cum, from: cols.indexOf(f.column),
        label: text(XL, y, label9(f, M.evening)),
        tX: text(XV, y, plain(q.t), { anchor: 'end', display: true, fill: 'var(--ink)' }),
        tZ: text(XV, y, sign(q.z), { anchor: 'end', display: true, fill: 'var(--ink)' }),
        tW: text(XV, y, sign(q.w), { anchor: 'end', display: true, fill: 'var(--pink)' }),
        tick: s('line', { x1: X0, x2: X0, y1: y - 11, y2: y + 11, style: { stroke: 'var(--ink)', strokeWidth: 2.5 } }),
        dot: s('circle', { cx: X0, cy: y, r: 5, style: { fill: 'var(--ink)' } }),
        bar: s('rect', { x: X0, y: y - 6, width: BAR, height: 12, 'vector-effect': 'non-scaling-stroke',
          style: { fill: 'var(--pink)', stroke: 'var(--card)', strokeWidth: 1 } }),
      }
      cum += q.w
      return r
    })

    // the plot: score axis, shift, curve, the two lines of the scale, the point
    const axis = s('g', {},
      s('line', { x1: ax(AX.lo), x2: ax(AX.hi), y1: AX.y, y2: AX.y, style: { stroke: 'var(--soft)', strokeWidth: 1.5 } }),
      ...[AX.lo, 0, AX.hi].map((v) => s('line', { x1: ax(v), x2: ax(v), y1: AX.y - 5, y2: AX.y + 5, style: { stroke: 'var(--soft)', strokeWidth: 1.5 } })),
      s('g', {}, text(ax(AX.lo), AX.y + 26, String(AX.lo), { fill: 'var(--soft)' }),
      text(ax(0), AX.y + 26, '0', { anchor: 'middle', fill: 'var(--soft)' }),
      text(ax(AX.hi), AX.y + 26, `+${AX.hi}`, { anchor: 'end', fill: 'var(--soft)' }),
      text(ax(2), AX.y + 26, 'бали', { anchor: 'middle', fill: 'var(--soft)' })))
    const icpt = s('rect', { x: AX.zero, y: AX.y - 6, width: BAR, height: 12, style: { fill: 'var(--soft)' } })
    const marker = s('circle', { cx: AX.zero, cy: AX.y, r: 7, style: { fill: 'var(--pink)', stroke: 'var(--card)', strokeWidth: 2 } })
    const clipRect = s('rect', { x: ax(AX.lo), y: 40, width: ax(AX.hi) - ax(AX.lo), height: 190 })
    let d = ''
    for (let i = 0; i <= 80; i++) {
      const z = AX.lo + ((AX.hi - AX.lo) * i) / 80
      d += `${i ? 'L' : 'M'}${ax(z).toFixed(1)},${ay(sig(z)).toFixed(1)}`
    }
    const curve = s('path', { d, 'clip-path': 'url(#how-model-clip)', style: { fill: 'none', stroke: 'var(--ink)', strokeWidth: 3 } })
    const dash = { stroke: 'var(--pink)', strokeWidth: 1.5, strokeDasharray: '5 5' }
    const thresholds = s('g', {},
      s('line', { x1: ax(AX.lo), x2: ax(AX.hi), y1: ay(M.high_at), y2: ay(M.high_at), style: dash }),
      s('line', { x1: ax(AX.lo), x2: ax(AX.hi), y1: ay(M.busy_at), y2: ay(M.busy_at), style: dash }),
      text(ax(AX.hi), ay(M.high_at) - 14, M.high_at.toFixed(3), { anchor: 'end', display: true, fill: 'var(--ink)' }),
      text(ax(AX.hi), ay(M.busy_at) + 16, M.busy_at.toFixed(3), { anchor: 'end', display: true, fill: 'var(--ink)' }))
    const point = s('circle', { cx: 0, cy: 0, r: 9, style: { fill: 'var(--pink)', stroke: 'var(--card)', strokeWidth: 3 } })
    const pText = text(80, 104, pct(R.p), { size: 40, display: true, fill: 'var(--pink)' })
    const tierText = text(80, 142, level(R.p), { fill: 'var(--ink)' })
    const plot = s('g', {}, axis, icpt, marker, curve, thresholds, point, pText, tierText)
    const eq = (y, a, b, fill) => s('g', {}, text(70, y, a), text(EQX, y, b, { anchor: 'end', display: true, fill }))
    const eqA = eq(EQ[0], `сума ${n9} добутків`, sign(R.sum), 'var(--ink)')
    const eqB = eq(EQ[1], '+ зсув', sign(M.intercept), 'var(--ink)')
    const eqC = eq(EQ[2], '= бали', sign(R.score), 'var(--pink)')

    svg.append(s('defs', {}, s('clipPath', { id: 'how-model-clip' }, clipRect)), caption, zero, brackets,
      ...rows.map((r) => r.bar), ...rows.flatMap((r) => [r.tick, r.dot, r.label, r.tX, r.tZ, r.tW]),
      ...ins.flatMap((r) => [r.label, r.value]), plot, eqA, eqB, eqC)

    // what if: three sliders recompute p with the same weights
    let wi = { ...BASE_WI }
    let W = compute(M, whatIf(wi))
    const inputs = {}, outs = {}
    const live = h('span', { class: 'wi-live', 'aria-live': 'polite' })
    const fixed = h('span', { class: 'wi-fixed' })
    const presetBtn = (label, preset) => h('button', { class: 'wi-pill', type: 'button', text: label, 'aria-pressed': 'false',
      on: { click: () => { wi = { ...preset }; update() } } })
    const presets = [[presetBtn('база', BASE_WI), BASE_WI], [presetBtn('разом', TOGETHER_WI), TOGETHER_WI]]
    const panel = h('div', { class: 'wi', hidden: true },
      ...CONTROLS.map((c) => {
        const id = `how-model-${c.key}`
        inputs[c.key] = h('input', { id, type: 'range', min: c.min, max: c.max, step: 1, value: wi[c.key],
          on: { input: (e) => { wi[c.key] = Number(e.target.value); update() } } })
        outs[c.key] = h('output', { for: id })
        return h('div', { class: 'wi-row' }, h('label', { for: id, text: c.label }), inputs[c.key], outs[c.key])
      }),
      h('div', { class: 'wi-presets' }, ...presets.map(([b]) => b), fixed, live))
    // keys and drags inside the panel belong to the controls, not to the deck
    const own = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' ', 'Enter']
    panel.addEventListener('keydown', (e) => { if (own.includes(e.key)) e.stopPropagation() })
    panel.addEventListener('pointerdown', (e) => e.stopPropagation())
    panel.addEventListener('pointerup', (e) => e.stopPropagation())
    root.append(panel)
    // hover or tap: the exact numbers behind the nearest mark
    const tip = h('div', { class: 'tip', role: 'tooltip', hidden: true })
    root.append(tip)
    const near = (list, f) => list.reduce((a, b) => (Math.abs(f(b)) < Math.abs(f(a)) ? b : a))
    function tipText(ux, uy) {
      if (cur <= 0) {
        const i = near(ins.map((_, j) => j), (j) => Y7(j) - uy)
        return `${LABEL[cols[i]]}: ${ins[i].value.textContent}, базова година з розділу 6 docs/quiet/model.md`
      }
      if (cur <= 2) {
        const r = near(rows, (q) => q.y - uy)
        return `${label9(r.f, M.evening)}: x ${plain(r.q.t)}, середнє ${r.f.mean.toFixed(3)}, розкид ${r.f.scale.toFixed(3)}, в одній шкалі ${sign(r.q.z)}`
      }
      if (cur === 3) {
        const r = near(rows, (q) => ax(q.cum + q.q.w / 2) - ux)
        return `${label9(r.f, M.evening)}: вага ${sign(r.f.coef, 3)} x ${sign(r.q.z)} = ${sign(r.q.w)}`
      }
      if (cur === 4) return `сума ${sign(R.sum)} + зсув ${sign(M.intercept)} = бали ${sign(R.score)}`
      const S = cur >= 6 ? W : R
      return `бали ${sign(S.score)}: p ${pct(S.p)}, ${level(S.p)}`
    }
    function showTip(e) {
      const b = root.getBoundingClientRect()
      tip.textContent = tipText(((e.clientX - b.left) * 640) / b.width, ((e.clientY - b.top) * 400) / b.height)
      tip.hidden = false
      tip.style.left = `${Math.max(4, Math.min(e.clientX - b.left + 14, b.width - tip.offsetWidth - 4))}px`
      tip.style.top = `${Math.max(4, Math.min(e.clientY - b.top + 14, b.height - tip.offsetHeight - 4))}px`
    }
    svg.addEventListener('pointermove', showTip)
    svg.addEventListener('pointerdown', showTip)
    svg.addEventListener('pointerleave', () => { tip.hidden = true })

    let cur = -1
    let timers = []
    const later = (ms, f) => timers.push(setTimeout(f, ms))
    const clear = () => { timers.forEach(clearTimeout); timers = [] }

    function update() {
      for (const c of CONTROLS) {
        inputs[c.key].value = String(wi[c.key])
        outs[c.key].textContent = c.fmt(wi[c.key])
      }
      presets.forEach(([b, pr]) => b.setAttribute('aria-pressed', String(Object.keys(pr).every((k) => pr[k] === wi[k]))))
      fixed.textContent = `пости про дрони ${wi.pdrone}`
      W = compute(M, whatIf(wi))
      live.textContent = `p ${pct(W.p)}, ${level(W.p)}`
      if (cur === 6) {
        pText.textContent = pct(W.p)
        pText.setAttribute('data-p', W.p.toFixed(4))
        tierText.textContent = level(W.p)
        put(point, { x: ax(W.score), y: ay(W.p) })
        put(marker, { x: ax(W.score) - AX.zero })
      }
    }

    // the end state of step k; o.instant jumps there
    function end(k, o) {
      const go = (el, st, delay = 0, origin) => put(el, st, { instant: o.instant, delay: o.instant ? 0 : delay, origin })
      ins.forEach((r, i) => {
        const st = k < 0 ? { o: 0 } : k === 0 ? { o: 1 } : { y: Y9(r.to) - Y7(i), o: 0 }
        go(r.label, st, i * 60)
        go(r.value, st, i * 60)
      })
      go(brackets, { o: k >= 0 && k <= 2 ? 1 : 0 })
      go(zero, { o: k === 2 ? 1 : 0 })
      rows.forEach((r, j) => {
        const dl = j * 50
        const from = { y: Y7(r.from) - r.y, o: 0 }
        go(r.label, k < 1 ? from : { o: k <= 2 ? 1 : 0 }, dl)
        go(r.tX, k < 1 ? from : { o: k === 1 ? 1 : 0 }, dl)
        go(r.tZ, { o: k === 2 ? 1 : 0 }, dl)
        go(r.tW, k < 3 ? { o: 0 } : { x: EQX - XV, y: EQ[0] - r.y, o: 0 }, dl)
        go(r.tick, { x: k < 2 ? r.f.mean * RAW : 0, o: k === 2 ? 1 : 0 }, dl)
        go(r.dot, { x: k < 2 ? r.q.t * RAW : r.q.z * U, o: k === 2 ? 1 : 0 }, dl)
        go(r.bar, k < 2 ? { x: r.f.mean * RAW, kx: ((r.q.t - r.f.mean) * RAW) / BAR, o: 0 }
          : k === 2 ? { kx: (r.q.z * U) / BAR, o: 0.85 }
          : { x: ax(r.cum) - X0, y: AX.y - r.y, kx: (r.q.w * P) / BAR, o: k >= 6 ? 0 : k === 5 ? 0.35 : 1 }, dl, 'left center')
      })
      go(axis, { o: k >= 3 ? 1 : 0 }, k === 3 ? 300 : 0)
      go(axis.lastChild, { o: k >= 6 ? 0 : 1 })
      go(eqA, { o: k >= 3 && k <= 5 ? 1 : 0 }, k === 3 ? 500 : 0)
      go(eqB, { o: k === 4 || k === 5 ? 1 : 0 })
      go(eqC, { o: k === 4 || k === 5 ? 1 : 0 }, k === 4 ? 400 : 0)
      go(icpt, { x: R.sum * P, kx: k < 4 ? 0 : (M.intercept * P) / BAR, o: k === 4 ? 1 : k === 5 ? 0.35 : 0 }, 0, 'left center')
      const S = k >= 6 ? W : R
      go(marker, { x: ax(S.score) - AX.zero, o: k >= 4 ? 1 : 0 }, k === 4 ? 400 : 0)
      go(clipRect, { kx: k >= 5 ? 1 : 0 }, 0, 'left center')
      go(thresholds, { o: k >= 5 ? 1 : 0 }, k === 5 ? 200 : 0)
      go(point, k < 5 ? { x: ax(AX.lo), y: ay(sig(AX.lo)), o: 0 } : { x: ax(S.score), y: ay(S.p), o: 1 })
      pText.textContent = pct(S.p)
      pText.setAttribute('data-p', S.p.toFixed(4))
      tierText.textContent = level(S.p)
      go(pText, { o: k >= 5 ? 1 : 0 })
      go(tierText, { o: k >= 5 ? 1 : 0 })
      go(plot, { y: k >= 6 ? -40 : 0 })
    }

    end(-1, { instant: true })
    update()
    svg.getBoundingClientRect()   // the start state is rendered before the first move

    function show(k, { instant } = {}) {
      clear()
      tip.hidden = true
      const anim = !instant && !reduced()
      const fwd = anim && k === cur + 1
      cur = k
      caption.textContent = CAPTION[k] || ''
      panel.hidden = k !== 6
      if (k === 6) update()
      if (!fwd || k < 2 || k > 5) return end(k, { instant: !anim })
      if (k === 2) {            // the number lines appear in raw units, then move to one scale
        put(zero, { o: 1 })
        rows.forEach((r, j) => {
          put(r.tick, { x: r.f.mean * RAW, o: 1 }, { delay: j * 40 })
          put(r.dot, { x: r.q.t * RAW, o: 1 }, { delay: j * 40 })
          put(r.bar, { x: r.f.mean * RAW, kx: ((r.q.t - r.f.mean) * RAW) / BAR, o: 0.85 }, { delay: j * 40, origin: 'left center' })
        })
        later(750, () => end(2, {}))
      } else if (k === 3) {     // each bar becomes weight x number, then the products fly into one sum
        rows.forEach((r, j) => {
          put(r.bar, { kx: (r.q.w * P) / BAR, o: 0.85 }, { delay: j * 40, origin: 'left center' })
          put(r.tZ, { o: 0 }, { delay: j * 40 })
          put(r.tW, { o: 1 }, { delay: j * 40 })
          put(r.dot, { x: r.q.z * U, o: 0 })
          put(r.tick, { x: 0, o: 0 })
        })
        put(zero, { o: 0 })
        later(1000, () => end(3, {}))
      } else if (k === 4) {     // the shift joins the row and gives the score
        put(icpt, { x: R.sum * P, kx: 0, o: 1 }, { origin: 'left center' })
        put(eqB, { o: 1 })
        later(300, () => end(4, {}))
      } else {                  // the curve is drawn, the point slides along it to the score
        put(clipRect, { kx: 1 }, { dur: 400, origin: 'left center' })
        put(thresholds, { o: 1 }, { delay: 250 })
        put(point, { x: ax(AX.lo), y: ay(sig(AX.lo)), o: 1 }, { delay: 300 })
        put(icpt, { x: R.sum * P, kx: (M.intercept * P) / BAR, o: 0.35 }, { origin: 'left center' })
        rows.forEach((r) => put(r.bar, { x: ax(r.cum) - X0, y: AX.y - r.y, kx: (r.q.w * P) / BAR, o: 0.35 }, { origin: 'left center' }))
        const n = 4
        for (let i = 1; i <= n; i++) {
          const z = AX.lo + ((R.score - AX.lo) * i) / n
          later(500 + (i - 1) * 280, () => put(point, { x: ax(z), y: ay(sig(z)), o: 1 }, { dur: 260 }))
        }
        later(500 + n * 280, () => end(5, {}))
      }
    }

    return { show, destroy() { clear() } }
  },
}

export default scene
