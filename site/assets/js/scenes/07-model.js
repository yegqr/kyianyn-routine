// Scene "model" of the methodology deck: which of the 11 candidate models we chose and why, then how the chosen one turns
// 7 signals about an hour into one probability, step by step, with its real weights from api/model.json (fallback:
// docs/quiet/model.md sections 4, 5, 7).
import { h, s, canvas, put, reduced } from '../how.js'

const RULE = {
  title: 'Правило вибору, записане наперед',
  source: 'звіт про моделі, його пише код',
  text: '**Фіналіст** (★, правило задано до запуску): найкращий BSS на розробці на годинах «зараз тихо»; модель з меншою ' +
    'кількістю ознак, якщо вона гірша менш ніж на 0.01.\n\nФіналіст за правилом: ★ `logit_signals`.',
}
const SIGNALS = {
  title: 'Сигнали моделі в коді',
  source: 'код моделі',
  text: `EVENING = (18, 23)                   # Kyiv hours, both included

# A feature is (column, how): "sin" and "cos" of the Kyiv hour on the 24 h circle, "evening" a 0/1 flag, "log1p", "raw".
SMALL = (("hour_kyiv", "sin"), ("hour_kyiv", "cos"), ("hour_kyiv", "evening"), ("hours_since_busy", "log1p"))
SIGNALS = SMALL + (("p_drone_max_1h", "raw"), ("s4_kyiv_6h", "raw"), ("s4_3h", "raw"), ("posts_jev_1h", "log1p"),
                   ("hours_since_drone", "log1p"))`,
}
const FORMULA = {
  title: 'Формула в коді',
  source: 'код живого прогнозу',
  text: 'A fitted model as api/model.json: p = 1 / (1 + exp(-(intercept + sum(coef * (x - mean) / scale)))).',
}

// reports/quiet_leaderboard.md: the 11 candidates and the simplest forecast naive_7d, by kind and where they stand on the
// stage; n is the number of signals, bss the gain over the simple rule on development, quiet-now hours (the finalist rule).
const KINDS = [
  { name: 'прості правила і таблиці', col: 0, y: 52, models: [
    { id: 'clim_hour', short: 'частка за годиною', full: 'Частка атак для кожної години доби', n: 1, bss: 0.027 },
    { id: 'recency_table', short: 'частка за давністю', full: 'Частка атак за тим, скільки годин минуло від останньої атаки', n: 1, bss: 0.047 },
    { id: 'hour_recency_nb', short: 'обидві таблиці', full: 'Дві попередні таблиці, їхні шанси перемножено', n: 2, bss: 0.075 },
  ] },
  { name: 'інші', col: 0, y: 184, models: [
    { id: 'gaussian_nb', short: 'наївний Баєс', full: 'Наївний Баєс: перемножує шанси 13 сигналів, ніби вони не пов’язані', n: 13, bss: -0.052 },
  ] },
  { name: 'для порівняння', col: 0, y: 256, models: [
    { id: 'naive_7d', short: 'частка за 7 днів', full: 'Найпростіший прогноз: частка 3-годинних вікон з атакою за останні 7 днів, та сама щогодини', n: 1, bss: -0.061 },
  ] },
  { name: 'лінійні: логістична регресія', col: 1, y: 52, models: [
    { id: 'logit_small', short: 'на годині й давності', full: 'Логістична регресія лише на годині доби і давності атаки', n: 2, bss: 0.073 },
    { id: 'logit_signals', short: 'на сигналах', full: 'Логістична регресія на сигналах: зважена сума і S-крива', n: 7, bss: 0.094 },
    { id: 'two_heads', short: 'дрони й ракети окремо', full: 'Дві логістичні регресії, для дронів і для ракет, з них одна ймовірність', n: 11, bss: 0.103 },
    { id: 'logit_all_l2', short: 'на всіх сигналах', full: 'Логістична регресія на всіх 66 стовпчиках таблиці: перевірка, чи шкодить зайве', n: 66, bss: 0.025 },
  ] },
  { name: 'дерева рішень', col: 1, y: 214, models: [
    { id: 'rf_small', short: 'випадковий ліс', full: 'Випадковий ліс: 500 дерев рішень, у кожному до 4 питань «так чи ні»', n: 13, bss: 0.077 },
    { id: 'lgbm_small', short: 'бустинг', full: 'Бустинг: 300 дерев по 3 питання, кожне виправляє помилки попередніх', n: 13, bss: 0.072 },
    { id: 'lgbm_all', short: 'бустинг на всіх', full: 'Той самий бустинг на всіх 66 стовпчиках: перевірка, чи шкодить зайве', n: 66, bss: 0.037 },
  ] },
]
const CHOSEN = 'logit_signals', BEST = 'two_heads', SIMPLEST = 'naive_7d'
const MODELS = KINDS.flatMap((k) => k.models)
const CANDIDATES = MODELS.filter((m) => m.id !== SIMPLEST).length
const COLX = [16, 334], COLW = 296, ROW = 30

// When api/model.json is missing: docs/quiet/model.md section 5 (means, spreads, weights, fitted on the 2890 development
// hours), sections 4 and 7 (the shift -0.729, the scale 0.197 and 0.300).
const FALLBACK = {
  source: 'docs/quiet/model.md, розділи 4, 5 і 7', day: '', rows: 2890,
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

// The base quiet hour of docs/quiet/model.md section 6 and its last case (+1.184 points, 77% there).
const BASE = { hour_kyiv: 14, hours_since_busy: 12, hours_since_drone: 24, p_drone_max_1h: 0.05, s4_kyiv_6h: 0, s4_3h: 5, posts_jev_1h: 8 }
const BASE_WI = { hour: 14, waves: 0, since: 12, pdrone: 0.05 }
const TOGETHER_WI = { hour: 21, waves: 2, since: 2, pdrone: 0.6 }
const hh = (v) => `${String(v % 24).padStart(2, '0')}:00`
const CONTROLS = [
  { key: 'hour', label: 'година доби', min: 0, max: 23, fmt: hh },
  { key: 'waves', label: 'хвилі на Київ', min: 0, max: 8, fmt: (v) => String(v) },
  { key: 'since', label: 'годин від атаки', min: 1, max: 72, fmt: (v) => `${v} год` },
]

// the 7 signals in plain words, in the order of the stage (the names of api/model.json feature.text, shortened)
const LABEL = {
  hour_kyiv: 'година доби', hours_since_busy: 'годин від останньої атаки', hours_since_drone: 'годин від останніх дронів',
  posts_jev_1h: 'постів моніторів за годину', p_drone_max_1h: 'оцінка «дрони на Київ»',
  s4_kyiv_6h: 'хвилі дронів на Київ за 6 год', s4_3h: 'запуски хвиль дронів за 3 год',
}
// what each signal means, for the hover tip (docs/quiet/model.md section 3)
const MEANS = {
  hour_kyiv: 'Година за Києвом; ввечері атак більше.',
  hours_since_busy: 'Скільки годин минуло від кінця останньої години з атакою.',
  hours_since_drone: 'Скільки годин минуло від останньої години з дронами на Київ.',
  posts_jev_1h: 'Скільки постів про загрозу написали 7 каналів моніторингу за минулу годину.',
  p_drone_max_1h: 'Найвища за минулу годину оцінка від 0 до 1, що пост каналу каже «дрони летять на Київ»; 0, якщо постів нема.',
  s4_kyiv_6h: 'Скільки окремих груп дронів з курсом на Київ повідомили канали моніторингу за 6 годин; хвиля долітає за кілька годин.',
  s4_3h: 'Скільки груп дронів запустили за 3 години, куди завгодно: сила атаки цієї ночі.',
}
const SHORT = { hours_since_busy: 'від атаки', hours_since_drone: 'від дронів', posts_jev_1h: 'постів', p_drone_max_1h: 'оцінка «дрони»',
  s4_kyiv_6h: 'хвилі на Київ', s4_3h: 'запуски хвиль' }
const ORDER = Object.keys(LABEL)
const HOWS = ['sin', 'cos', 'evening', 'log1p', 'raw']   // also the order of the 9 numbers: the hour, logarithms, as is
const rank = (f) => HOWS.indexOf(f.how) * 10 + ORDER.indexOf(f.column)
const PLAY = 8   // the step with the sliders
const LEVEL = ['низький ризик', 'середній ризик', 'високий ризик']   // src/airalerts/quiet/forecast.py level()

// geometry in the 640 x 400 units of the canvas
const XL = 16, XV = 330, XV7 = 440, X0 = 470, RAW = 25, U = 50, BAR = 50, P = 67.5
const AX = { zero: 340, y: 220, h: 160, lo: -4, hi: 4 }
const EQ = [284, 318, 352], EQX = 400
const ax = (score) => AX.zero + Math.max(AX.lo, Math.min(AX.hi, score)) * P
const ay = (p) => AX.y - p * AX.h
const sig = (z) => 1 / (1 + Math.exp(-z))

const num = (v, d) => (Number.isFinite(v) ? v : d)
const pct = (p) => `${Math.round(p * 100)}%`
// a scale line as the reader sees it: 0.197 is 19.7%, 0.3 is 30%
const pctx = (p) => { const t = (p * 100).toFixed(1); return `${t.endsWith('.0') ? t.slice(0, -2) : t}%` }
const plain = (v) => (Number.isInteger(v) ? String(v) : Math.abs(v) < 0.005 ? '0' : v.toFixed(2))
function sign(v, d = 2) {
  const t = Math.abs(v).toFixed(d)
  return Number(t) === 0 ? t : (v < 0 ? '-' : '+') + t
}
const n = (v) => `<span class="num">${v}</span>`
// file paths and code names live only in this folded block at the end of a note
const src = (text) => `<details class="how-src"><summary>Джерела</summary><p>${text}</p></details>`

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
    day: /^\d{4}-\d{2}-\d{2}$/.test(day) ? `${day.slice(8, 10)}.${day.slice(5, 7)}` : '',
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

function label9(f) {
  if (f.how === 'sin') return 'година: синус'
  if (f.how === 'cos') return 'година: косинус'
  if (f.how === 'evening') return 'вечір: 1 так, 0 ні'
  return f.how === 'log1p' ? `${SHORT[f.column]}: логарифм` : SHORT[f.column]
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
  border-top: 1px solid var(--line); font-size: 16px; color: var(--body); }
.scene-model .wi[hidden] { display: none; }
.scene-model .wi-row { display: grid; grid-template-columns: minmax(0, 10fr) minmax(0, 9fr) minmax(0, 5fr); gap: 12px; align-items: center; }
.scene-model .wi-row label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.scene-model .wi-row output { font-family: var(--font-display); color: var(--ink); text-align: right; white-space: nowrap; font-size: 15px; }
.scene-model input[type=range] { width: 100%; min-width: 0; height: 24px; margin: 0; font-size: 16px; accent-color: var(--pink); cursor: pointer; }
.scene-model input[type=range]:focus-visible { outline: none; box-shadow: var(--focus-ring); border-radius: var(--r-pill); }
.scene-model .wi-presets { display: flex; gap: 8px; align-items: center; min-width: 0; }
.scene-model .wi-pill { font: inherit; font-size: 15px; height: 32px; padding: 0 16px; border-radius: var(--r-pill); border: 1px solid var(--line);
  background: var(--card); color: var(--ink); cursor: pointer; flex: none; }
.scene-model .wi-pill:hover { border-color: var(--pink); }
.scene-model .wi-pill[aria-pressed="true"] { border-color: var(--pink); color: var(--pink); }
.scene-model .wi-pill:focus-visible { outline: none; box-shadow: var(--focus-ring); }
.scene-model .wi-fixed { color: var(--soft); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.scene-model .wi-live { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.scene-model .tip { position: absolute; z-index: 2; max-width: 280px; padding: 6px 10px; border-radius: var(--r-small); background: var(--card);
  border: 1px solid var(--line); color: var(--ink); font-size: 15px; line-height: 1.35; pointer-events: none; }
.scene-model .tip[hidden] { display: none; }
@media (max-width: 600px) {
  .scene-model .wi { padding: 2px 10px 4px; font-size: 14px; }
  .scene-model .wi-row { gap: 8px; }
  .scene-model .wi-row output { font-size: 14px; }
  .scene-model .wi-pill { height: 26px; padding: 0 12px; font-size: 14px; }
  .scene-model .tip { max-width: 220px; font-size: 14px; }
}
/* on a phone the two presets fill the row: the fixed drone score would be cut */
@container how-stage (max-width: 499px) { .scene-model .wi-fixed { display: none; } }
`

function notes(M, R, T) {
  const ev = M.evening
  const k = new Set(M.features.map((f) => f.column)).size
  const top = M.features.reduce((a, f) => (Math.abs(f.coef) > Math.abs(a.coef) ? f : a))
  const hsb = M.features.find((f) => f.column === 'hours_since_busy')
  const name = (f) => f.text || LABEL[f.column]
  const level = (p) => LEVEL[p < M.busy_at ? 0 : p < M.high_at ? 1 : 2]
  const live = M === FALLBACK ? '' : `з вагами живої моделі${M.day ? ` (навченої ${M.day})` : ''}`
  const ours = MODELS.find((m) => m.id === CHOSEN), best = MODELS.find((m) => m.id === BEST)
  return [
    `<p>Ми спробували ${n(CANDIDATES)} моделей чотирьох видів: прості таблиці частки атак, лінійні (зважена сума сигналів), ` +
      'дерева рішень (сотні ланцюжків питань «так чи ні») та інші. Для порівняння є найпростіший прогноз <b>«частка за 7 днів»</b>: ' +
      'щогодини казати, яка частка 3-годинних вікон за минулий тиждень мала атаку. Обрана модель рожева: ' +
      '<b>логістична регресія на сигналах</b>.</p>' +
      src('reports/quiet_leaderboard.md, розділ «Моделі»: 11 моделей і naive_7d; обрана logit_signals.'),
    '<p>Число біля моделі це <b>виграш над простим правилом</b> на навчальних даних (01.05-29.08): 0 означає «не точніше, ніж ' +
      'щогодини казати частку атак, відому на початок тижня», більше 0 краще. Правило вибору записали до будь-яких чисел: ' +
      'найбільший виграш, але простіша модель, якщо гірша менш ніж на 0.01. ' +
      `Тож обрали ${n(ours.bss.toFixed(3))} з ${ours.n} сигналами, а не ${best.bss.toFixed(3)} з ${best.n}.</p>` +
      src('reports/quiet_leaderboard.md, таблиця «Розробка, години «зараз тихо»»: BSS, two_heads 0.103 (11 ознак), ' +
        'logit_signals 0.094 (7 ознак), правило «Фіналіст»; docs/adr/0008-time-split.md.'),
    `<p>Модель дивиться на ${n(k)} сигналів про годину: час доби, давність атак, пости каналів моніторингу і хвилі дронів. ` +
      '<b>Хвиля</b> це окрема група дронів, про яку написали канали: «на Київ за 6 год» рахує групи з курсом на Київ, ' +
      '«запуски за 3 год» усі групи, куди завгодно. Тут звичайна спокійна година; торкнись рядка, і побачиш, що він означає.</p>' +
      src('назви: api/model.json, features[].text; docs/quiet/model.md, розділ 3: сім входів; розділ 6: базова тиха година.'),
    `<p>Година стає 3 числами, тож ${k} сигналів дають ${n(M.features.length)}: <b>синус і косинус</b> ставлять її на циферблат, ` +
      `де 23:00 поруч з 00:00, а <b>«вечір»</b> (1 з ${hh(ev[0])} до ${String(ev[1]).padStart(2, '0')}:59) ловить вечірній ` +
      'сплеск: атака приблизно в 40% вікон проти 18-27% в інші години. <b>Логарифм</b> для давності й постів: після 1-2 годин ' +
      'тиші атака в 45% вікон, після доби лише 17%, тож перша година важить більше за соту. Решта як є.</p>' +
      src('docs/quiet/model.md, розділ 3: 40% і 18..27% за годиною, 45% і 17% після тиші; розділ 4: sin, cos, evening, log1p.'),
    '<p>Числа мають різні одиниці: години, частки, штуки. Від кожного віднімаємо його середнє і ділимо на розкид, тож ' +
      'рисочки середніх з’їжджаються в 0, а +1 означає «на один розкид більше, ніж зазвичай». Середні й розкиди з ' +
      (M === FALLBACK ? `${M.rows} годин навчальних даних.</p>`
        : `${Number.isFinite(M.rows) ? `${M.rows} годин` : 'годин'}${M.day ? ` до ${M.day}` : ''}: жива модель вчилась заново ` +
          'на всіх годинах, про які вже відомо, чи була після них атака, а не лише на навчальних даних.</p>') +
      src(`Середні й розкиди: ${M.source}` +
        (M === FALLBACK ? '.' : '; docs/adr/0012-live-site.md: перенавчання на всіх годинах, чиї 3 години вже минули.')),
    '<p>Кожне число множимо на його вагу: вона каже, наскільки сильно це число штовхає ризик вгору чи вниз. ' +
      `Найбільша вага в сигналу «${name(top)}» (${n(sign(top.coef))})` +
      (hsb ? `, від’ємна в давності атаки (${n(sign(hsb.coef))}): що довше без атак, то нижчий ризик` : '') +
      `. Добутки стають в один ряд, і ряд закінчується на ${n(sign(R.sum))}.</p>` +
      src(`Ваги: ${M.source}.`),
    `<p>До добутків додаємо <b>стартове число (зсув)</b> ${n(sign(M.intercept))}: з нього модель починає, коли кожне з ` +
      `${M.features.length} чисел дорівнює своєму середньому, і тоді каже ${pct(sig(M.intercept))}. ` +
      `Виходить <b>сума</b>: ${n(sign(R.score))} для нашої години. Сума 0 означала б 50 на 50, від’ємна менше 50%.</p>` +
      src(`Стартове число (intercept, bias) і сума (logit): ${M.source}; docs/quiet/model.md, розділ 4.`),
    `<p>Крива у формі літери S перетворює будь-яку суму на ймовірність від 0% до 100%: сума ${sign(R.score)} дає ${n(pct(R.p))}. ` +
      `Пунктири це межі ризику з наступного розділу: від ${pctx(M.busy_at)} середній, від ${pctx(M.high_at)} високий. ` +
      `Наша година має ${level(R.p)}.</p>` +
      src(`docs/quiet/model.md, розділ 4: p = 1 / (1 + e^(-сума)); межі busy_at і high_at: ${M.source}.`),
    '<p>Посувай повзунки пальцем, мишею або стрілками: ймовірність рахується тут же, тими самими вагами. ' +
      `«Тиха година» повертає наш приклад: ${hh(BASE_WI.hour)}, атака ${BASE_WI.since} годин тому, ${BASE_WI.waves} хвиль. ` +
      `«Тривожний вечір» ставить ${hh(TOGETHER_WI.hour)}, атаку ${TOGETHER_WI.since} години тому, ${TOGETHER_WI.waves} хвилі ` +
      `на Київ і оцінку «дрони на Київ» ${TOGETHER_WI.pdrone} з 1: у звіті про модель 77%, ` +
      `${live ? `а ${live} ${n(pct(T.p))}` : `тут ${n(pct(T.p))}`}.</p>` +
      src(`docs/quiet/model.md, розділ 6: базова тиха година і останній рядок таблиці, +1.184, 77%; ваги: ${M.source}.`),
  ]
}

const scene = {
  id: 'model',
  title: 'Як модель рахує ймовірність',
  lead: 'З 11 моделей ми обрали логістичну регресію на сигналах: вона бере 7 сигналів про годину, робить з них 9 чисел, ' +
    'множить кожне на його вагу, додає стартове число і S-кривою перетворює суму на ймовірність атаки.',
  steps: [
    { note: '', prompts: [RULE] }, { note: '', prompts: [RULE] }, { note: '', prompts: [SIGNALS] },
    { note: '', prompts: [SIGNALS] }, { note: '', prompts: [FORMULA] }, { note: '', prompts: [FORMULA] },
    { note: '', prompts: [FORMULA] }, { note: '', prompts: [FORMULA] }, { note: '', prompts: [FORMULA] },
  ],
  prompts: [],
  mount(stage, data) {
    const M = pick(data?.model)
    const R = compute(M, BASE)
    const T = compute(M, whatIf(TOGETHER_WI))
    notes(M, R, T).forEach((note, i) => { scene.steps[i].note = note })
    const level = (p) => LEVEL[p < M.busy_at ? 0 : p < M.high_at ? 1 : 2]

    const root = h('div', { class: 'scene-model' }, h('style', { text: CSS }))
    stage.append(root)
    const svg = canvas(root, `${CANDIDATES} моделей, яку з них обрали і як вона робить з 7 сигналів про годину одну ймовірність атаки`)
    const cols = ORDER.filter((c) => M.features.some((f) => f.column === c))
    const n9 = M.features.length
    const CAPTION = [`${CANDIDATES} моделей і найпростіший прогноз`, 'чому обрали цю', `${cols.length} сигналів про годину`,
      `${cols.length} сигналів стають ${n9} числами`, 'одна шкала', 'множимо на ваги', 'плюс стартове число: сума',
      'S-крива: сума стає ймовірністю', 'спробуй сам']
    const g9 = Math.min(36, 288 / Math.max(1, n9 - 1))
    const g7 = Math.min(44, 264 / Math.max(1, cols.length - 1))
    const Y9 = (i) => 56 + i * g9
    const Y7 = (i) => 70 + i * g7
    const top = Y9(0) - 20, bot = Y9(n9 - 1) + 20

    // the models by kind, the chosen one on a pink pill; the scores, the best one's ring and the reason come at step 2
    const listG = s('g', {}), scores = s('g', {})
    const spots = []
    for (const kind of KINDS) {
      const x = COLX[kind.col]
      listG.append(text(x, kind.y, kind.name, { size: 18, fill: 'var(--soft)' }))
      kind.models.forEach((m, i) => {
        const y = kind.y + ROW * (i + 1)
        const mine = m.id === CHOSEN
        if (mine) listG.append(s('rect', { x: x - 8, y: y - 16, width: COLW + 14, height: 32, rx: 16, style: { fill: 'var(--pink-soft)' } }))
        listG.append(text(x, y, m.short, { size: 20, fill: mine ? 'var(--pink)' : 'var(--body)' }))
        scores.append(text(x + COLW, y, m.bss.toFixed(3), { anchor: 'end', size: 20, fill: mine ? 'var(--pink)' : 'var(--ink)' }))
        spots.push({ m, x, y })
      })
    }
    const ours = spots.find((q) => q.m.id === CHOSEN), best = spots.find((q) => q.m.id === BEST)
    const ring = s('rect', { x: best.x - 8, y: best.y - 16, width: COLW + 14, height: 32, rx: 16,
      style: { fill: 'none', stroke: 'var(--ink)', strokeWidth: 1.5 } })
    const named = text(XL, 356, `обрана: логістична регресія ${ours.m.short}`, { fill: 'var(--pink)' })
    const reason = s('g', {},
      text(XL, 344, `${best.m.short}: ${best.m.bss.toFixed(3)} з ${best.m.n} сигналами`, { size: 20, fill: 'var(--ink)' }),
      text(XL, 374, `${ours.m.short}: ${ours.m.bss.toFixed(3)} з ${ours.m.n}, різниця лише ${(best.m.bss - ours.m.bss).toFixed(3)}`,
        { size: 20, fill: 'var(--pink)' }))

    // the table: 7 signals, then 9 numbers grouped by how they are made (the hour, logarithms, as is), each with its number line
    const caption = text(XL, 20, CAPTION[0], { fill: 'var(--soft)' })
    const zero = s('line', { x1: X0, x2: X0, y1: top, y2: bot, style: { stroke: 'var(--line)', strokeWidth: 2 } })
    const order = M.features.map((f, j) => j).sort((a, b) => rank(M.features[a]) - rank(M.features[b]))
    let cum = 0
    const rows = order.map((j, i) => {
      const f = M.features[j], q = R.parts[j], y = Y9(i)
      const r = {
        f, q, y, cum, from: cols.indexOf(f.column),
        label: text(XL, y, label9(f)),
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
    const ins = cols.map((c, i) => ({
      label: text(XL, Y7(i), LABEL[c]),
      value: text(XV7, Y7(i), c === 'hour_kyiv' ? hh(BASE[c]) : plain(BASE[c]), { anchor: 'end', display: true, fill: 'var(--ink)' }),
      to: rows.findIndex((r) => r.f.column === c),
    }))

    // why each signal becomes what it is: the hour on a clock face, the logarithm squeezes long waits, the rest as it is
    const explain = s('g', {})
    const span = (hows) => {
      const ix = rows.flatMap((r, i) => (hows.includes(r.f.how) ? [i] : []))
      return ix.length ? [Y9(ix[0]), Y9(ix[ix.length - 1])] : null
    }
    const brace = ([a, b]) => s('path', { d: `M344,${a - 14}H352V${b + 14}H344`, style: { fill: 'none', stroke: 'var(--soft)', strokeWidth: 2 } })
    const hourSpan = span(['sin', 'cos', 'evening']), logSpan = span(['log1p']), rawSpan = span(['raw'])
    if (hourSpan) {
      const cy = (hourSpan[0] + hourSpan[1]) / 2, cx = 394, rr = 28, a = (2 * Math.PI * BASE.hour_kyiv) / 24
      explain.append(brace(hourSpan),
        s('circle', { cx, cy, r: rr, style: { fill: 'none', stroke: 'var(--soft)', strokeWidth: 2 } }),
        text(cx, cy - rr - 12, '00:00', { anchor: 'middle', size: 18, fill: 'var(--soft)' }),
        s('circle', { cx: cx + rr * Math.sin(a), cy: cy - rr * Math.cos(a), r: 6, style: { fill: 'var(--pink)' } }),
        text(436, cy - 22, 'циферблат: 23:00', { size: 18 }), text(436, cy, 'поруч з 00:00', { size: 18 }),
        text(436, cy + 22, '+ вечір: 1 або 0', { size: 18 }))
    }
    if (logSpan) {
      const cy = (logSpan[0] + logSpan[1]) / 2, L = (v) => plain(Math.log1p(v))
      explain.append(brace(logSpan), text(362, cy - 24, 'логарифм стискає:', { size: 18 }),
        text(362, cy, `1 год: ${L(1)}, 12 год: ${L(12)}`, { size: 18 }),
        text(362, cy + 24, `100 год: ${L(100)}, 102: ${L(102)}`, { size: 18 }))
    }
    if (rawSpan) explain.append(brace(rawSpan), text(362, (rawSpan[0] + rawSpan[1]) / 2, 'як є, без змін', { size: 18 }))

    // the plot: sum axis, shift, curve, the two lines of the scale, the point
    const axis = s('g', {},
      s('line', { x1: ax(AX.lo), x2: ax(AX.hi), y1: AX.y, y2: AX.y, style: { stroke: 'var(--soft)', strokeWidth: 1.5 } }),
      ...[AX.lo, 0, AX.hi].map((v) => s('line', { x1: ax(v), x2: ax(v), y1: AX.y - 5, y2: AX.y + 5, style: { stroke: 'var(--soft)', strokeWidth: 1.5 } })),
      s('g', {}, text(ax(AX.lo), AX.y + 26, String(AX.lo), { fill: 'var(--soft)' }),
      text(ax(0), AX.y + 26, '0', { anchor: 'middle', fill: 'var(--soft)' }),
      text(ax(AX.hi), AX.y + 26, `+${AX.hi}`, { anchor: 'end', fill: 'var(--soft)' }),
      text(ax(2), AX.y + 26, 'сума', { anchor: 'middle', fill: 'var(--soft)' })))
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
      text(ax(AX.hi), ay(M.high_at) - 14, pctx(M.high_at), { anchor: 'end', display: true, fill: 'var(--ink)' }),
      text(ax(AX.hi), ay(M.busy_at) + 16, pctx(M.busy_at), { anchor: 'end', display: true, fill: 'var(--ink)' }))
    const point = s('circle', { cx: 0, cy: 0, r: 9, style: { fill: 'var(--pink)', stroke: 'var(--card)', strokeWidth: 3 } })
    const pText = text(80, 104, pct(R.p), { size: 40, display: true, fill: 'var(--pink)' })
    const tierText = text(80, 142, level(R.p), { fill: 'var(--ink)' })
    const plot = s('g', {}, axis, icpt, marker, curve, thresholds, point, pText, tierText)
    const eq = (y, a, b, fill) => s('g', {}, text(70, y, a), text(EQX, y, b, { anchor: 'end', display: true, fill }))
    const eqA = eq(EQ[0], `${n9} добутків`, sign(R.sum), 'var(--ink)')
    const eqB = eq(EQ[1], '+ стартове число', sign(M.intercept), 'var(--ink)')
    const eqC = eq(EQ[2], '= сума', sign(R.score), 'var(--pink)')

    svg.append(s('defs', {}, s('clipPath', { id: 'how-model-clip' }, clipRect)), caption, listG, scores, ring, named, reason,
      zero, explain, ...rows.map((r) => r.bar), ...rows.flatMap((r) => [r.tick, r.dot, r.label, r.tX, r.tZ, r.tW]),
      ...ins.flatMap((r) => [r.label, r.value]), plot, eqA, eqB, eqC)

    // what if: three sliders recompute the probability with the same weights
    let wi = { ...BASE_WI }
    let W = compute(M, whatIf(wi))
    const inputs = {}, outs = {}
    const live = h('span', { class: 'wi-live', 'aria-live': 'polite' })
    const fixed = h('span', { class: 'wi-fixed' })
    const presetBtn = (label, preset) => h('button', { class: 'wi-pill', type: 'button', text: label, 'aria-pressed': 'false',
      on: { click: () => { wi = { ...preset }; update() } } })
    const presets = [[presetBtn('тиха година', BASE_WI), BASE_WI], [presetBtn('тривожний вечір', TOGETHER_WI), TOGETHER_WI]]
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
    // hover or tap: what the nearest mark means, with its exact numbers
    const tip = h('div', { class: 'tip', role: 'tooltip', hidden: true })
    root.append(tip)
    const near = (list, f) => list.reduce((a, b) => (Math.abs(f(b)) < Math.abs(f(a)) ? b : a))
    function tipText(ux, uy) {
      if (cur < 2) {
        const q = near(spots, (p) => Math.hypot(p.x + COLW / 2 - ux, p.y - uy))
        return `${q.m.full}; сигналів ${q.m.n}` + (cur === 1 ? `, виграш ${q.m.bss.toFixed(3)}` : '')
      }
      const j = cur - 2
      if (j <= 0) {
        const i = near(ins.map((_, q) => q), (q) => Y7(q) - uy)
        return `${LABEL[cols[i]]}: ${ins[i].value.textContent}. ${MEANS[cols[i]]}`
      }
      if (j <= 2) {
        const r = near(rows, (q) => q.y - uy)
        return `${label9(r.f)} = ${plain(r.q.t)}; середнє ${r.f.mean.toFixed(3)}, розкид ${r.f.scale.toFixed(3)}, в одній шкалі ${sign(r.q.z)}`
      }
      if (j === 3) {
        const r = near(rows, (q) => ax(q.cum + q.q.w / 2) - ux)
        return `${label9(r.f)}, вага ${sign(r.f.coef, 3)} × ${sign(r.q.z)} = ${sign(r.q.w)}`
      }
      if (j === 4) return `добутки ${sign(R.sum)} + стартове число ${sign(M.intercept)} = сума ${sign(R.score)}`
      const S = cur >= PLAY ? W : R
      return `сума ${sign(S.score)}: ймовірність ${pct(S.p)}, ${level(S.p)}`
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
      fixed.textContent = `оцінка «дрони на Київ» ${wi.pdrone} з 1`
      W = compute(M, whatIf(wi))
      live.textContent = `ймовірність ${pct(W.p)}, ${level(W.p)}`
      if (cur === PLAY) {
        pText.textContent = pct(W.p)
        pText.setAttribute('data-p', W.p.toFixed(4))
        tierText.textContent = level(W.p)
        put(point, { x: ax(W.score), y: ay(W.p) })
        put(marker, { x: ax(W.score) - AX.zero })
      }
    }

    // the end state of step k; o.instant jumps there. Steps 0 and 1 are the models, j counts the steps of the computation.
    function end(k, o) {
      const go = (el, st, delay = 0, origin) => put(el, st, { instant: o.instant, delay: o.instant ? 0 : delay, origin })
      go(listG, { o: k === 0 || k === 1 ? 1 : 0 })
      go(named, { o: k === 0 ? 1 : 0 })
      go(scores, { o: k === 1 ? 1 : 0 })
      go(ring, { o: k === 1 ? 1 : 0 })
      go(reason, { o: k === 1 ? 1 : 0 }, k === 1 ? 300 : 0)
      const j = k - 2
      ins.forEach((r, i) => {
        const st = j < 0 ? { o: 0 } : j === 0 ? { o: 1 } : { y: Y9(r.to) - Y7(i), o: 0 }
        go(r.label, st, i * 60)
        go(r.value, st, i * 60)
      })
      go(explain, { o: j === 1 ? 1 : 0 }, j === 1 ? 450 : 0)
      go(zero, { o: j === 2 ? 1 : 0 })
      rows.forEach((r, i) => {
        const dl = i * 50
        const from = { y: Y7(r.from) - r.y, o: 0 }
        go(r.label, j < 1 ? from : { o: j <= 2 ? 1 : 0 }, dl)
        go(r.tX, j < 1 ? from : { o: j === 1 ? 1 : 0 }, dl)
        go(r.tZ, { o: j === 2 ? 1 : 0 }, dl)
        go(r.tW, j < 3 ? { o: 0 } : { x: EQX - XV, y: EQ[0] - r.y, o: 0 }, dl)
        go(r.tick, { x: j < 2 ? r.f.mean * RAW : 0, o: j === 2 ? 1 : 0 }, dl)
        go(r.dot, { x: j < 2 ? r.q.t * RAW : r.q.z * U, o: j === 2 ? 1 : 0 }, dl)
        go(r.bar, j < 2 ? { x: r.f.mean * RAW, kx: ((r.q.t - r.f.mean) * RAW) / BAR, o: 0 }
          : j === 2 ? { kx: (r.q.z * U) / BAR, o: 0.85 }
          : { x: ax(r.cum) - X0, y: AX.y - r.y, kx: (r.q.w * P) / BAR, o: j >= 6 ? 0 : j === 5 ? 0.35 : 1 }, dl, 'left center')
      })
      go(axis, { o: j >= 3 ? 1 : 0 }, j === 3 ? 300 : 0)
      go(axis.lastChild, { o: j >= 6 ? 0 : 1 })
      go(eqA, { o: j >= 3 && j <= 5 ? 1 : 0 }, j === 3 ? 500 : 0)
      go(eqB, { o: j === 4 || j === 5 ? 1 : 0 })
      go(eqC, { o: j === 4 || j === 5 ? 1 : 0 }, j === 4 ? 400 : 0)
      go(icpt, { x: R.sum * P, kx: j < 4 ? 0 : (M.intercept * P) / BAR, o: j === 4 ? 1 : j === 5 ? 0.35 : 0 }, 0, 'left center')
      const S = j >= 6 ? W : R
      go(marker, { x: ax(S.score) - AX.zero, o: j >= 4 ? 1 : 0 }, j === 4 ? 400 : 0)
      go(clipRect, { kx: j >= 5 ? 1 : 0 }, 0, 'left center')
      go(thresholds, { o: j >= 5 ? 1 : 0 }, j === 5 ? 200 : 0)
      go(point, j < 5 ? { x: ax(AX.lo), y: ay(sig(AX.lo)), o: 0 } : { x: ax(S.score), y: ay(S.p), o: 1 })
      pText.textContent = pct(S.p)
      pText.setAttribute('data-p', S.p.toFixed(4))
      tierText.textContent = level(S.p)
      go(pText, { o: j >= 5 ? 1 : 0 })
      go(tierText, { o: j >= 5 ? 1 : 0 })
      go(plot, { y: j >= 6 ? -40 : 0 })
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
      const j = k - 2
      caption.textContent = CAPTION[k] || ''
      panel.hidden = k !== PLAY
      if (k === PLAY) update()
      if (!fwd || j < 2 || j > 5) return end(k, { instant: !anim })
      if (j === 2) {            // the number lines appear in raw units, then move to one scale
        put(zero, { o: 1 })
        rows.forEach((r, i) => {
          put(r.tick, { x: r.f.mean * RAW, o: 1 }, { delay: i * 40 })
          put(r.dot, { x: r.q.t * RAW, o: 1 }, { delay: i * 40 })
          put(r.bar, { x: r.f.mean * RAW, kx: ((r.q.t - r.f.mean) * RAW) / BAR, o: 0.85 }, { delay: i * 40, origin: 'left center' })
        })
        put(explain, { o: 0 })
        later(750, () => end(k, {}))
      } else if (j === 3) {     // each bar becomes weight x number, then the products fly into one row
        rows.forEach((r, i) => {
          put(r.bar, { kx: (r.q.w * P) / BAR, o: 0.85 }, { delay: i * 40, origin: 'left center' })
          put(r.tZ, { o: 0 }, { delay: i * 40 })
          put(r.tW, { o: 1 }, { delay: i * 40 })
          put(r.dot, { x: r.q.z * U, o: 0 })
          put(r.tick, { x: 0, o: 0 })
        })
        put(zero, { o: 0 })
        later(1000, () => end(k, {}))
      } else if (j === 4) {     // the starting number joins the row and gives the sum
        put(icpt, { x: R.sum * P, kx: 0, o: 1 }, { origin: 'left center' })
        put(eqB, { o: 1 })
        later(300, () => end(k, {}))
      } else {                  // the curve is drawn, the point slides along it to the sum
        put(clipRect, { kx: 1 }, { dur: 400, origin: 'left center' })
        put(thresholds, { o: 1 }, { delay: 250 })
        put(point, { x: ax(AX.lo), y: ay(sig(AX.lo)), o: 1 }, { delay: 300 })
        put(icpt, { x: R.sum * P, kx: (M.intercept * P) / BAR, o: 0.35 }, { origin: 'left center' })
        rows.forEach((r) => put(r.bar, { x: ax(r.cum) - X0, y: AX.y - r.y, kx: (r.q.w * P) / BAR, o: 0.35 }, { origin: 'left center' }))
        const steps = 4
        for (let i = 1; i <= steps; i++) {
          const z = AX.lo + ((R.score - AX.lo) * i) / steps
          later(500 + (i - 1) * 280, () => put(point, { x: ax(z), y: ay(sig(z)), o: 1 }, { dur: 260 }))
        }
        later(500 + steps * 280, () => end(k, {}))
      }
    }

    return { show, destroy() { clear() } }
  },
}

export default scene
