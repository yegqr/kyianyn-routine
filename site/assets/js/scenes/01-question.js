// Scene 1 of the methodology deck: why the site asks "will you cross the river in the next 3 hours".
// Crossing facts: city announcements quoted by the media, checked 2026-10-11 (the same facts as ../crossing.js).
// The tier thresholds are read at runtime from api/model.json (busy_at, high_at), now.json is the fallback.
// The test shares of step 4 (17%, 5 of 29; 74%): docs/quiet/forecast.md, table 3, an official alert in the next 3 hours.
// Colours: the metro lines in their official colours (--m1, --m2, --m3), states in status colours
// (--go open, --risk limited, --stop closed), pink only for the brand accents: the river and the 3 hour window.
import { h, s, canvas, put, stagger } from '../how.js'
import { pct } from '../api.js'

const ID = 'question'
const LEFT = 'left center'
const TOP = 'center top'

const CSS = `
.scene-question text { font-family: var(--font); font-size: 22px; fill: var(--ink); }
.scene-question .soft { fill: var(--soft); }
.scene-question .bold { font-weight: 600; }
.scene-question .on-dark { fill: var(--card); font-weight: 600; }
.scene-question .river { fill: var(--pink-soft); }
.scene-question .deck { fill: none; stroke: var(--soft); stroke-opacity: .45; stroke-width: 6; stroke-linecap: round; }
.scene-question .line { fill: none; stroke-width: 8; stroke-linecap: round; }
.scene-question .m1 { stroke: var(--m1); }
.scene-question .m2 { stroke: var(--m2); }
.scene-question .m3 { stroke: var(--m3); }
.scene-question .station { fill: var(--card); stroke-width: 3; }
.scene-question .fill-m1 { fill: var(--m1); }
.scene-question .fill-m2 { fill: var(--m2); }
.scene-question .fill-m3 { fill: var(--m3); }
.scene-question .pill-yellow { fill: var(--risk-soft); stroke: var(--risk-fill); stroke-width: 2; }
.scene-question .pill-red { fill: var(--stop); }
.scene-question .risk-text { fill: var(--risk); font-weight: 600; }
.scene-question .q-train { fill: var(--card); stroke: var(--ink); stroke-width: 2.5; }
.scene-question .stop circle { fill: var(--card); stroke: var(--stop); stroke-width: 3; }
.scene-question .stop path { fill: none; stroke: var(--stop); stroke-width: 3; stroke-linecap: round; }
.scene-question .cell { fill: var(--pink-soft); stroke: var(--pink); stroke-width: 2; }
.scene-question .tick { fill: none; stroke: var(--ink); stroke-width: 2; }
.scene-question .lead { fill: none; stroke: var(--soft); stroke-width: 1.5; }
.scene-question .bar-none { fill: var(--pink-soft); }
.scene-question .bar-0 { fill: var(--go); }
.scene-question .bar-1 { fill: var(--risk-fill); }
.scene-question .bar-2 { fill: var(--stop); }
.scene-question .pill-0 { fill: var(--go-soft); stroke: var(--go); stroke-width: 2; }
.scene-question .pill-1 { fill: var(--risk-soft); stroke: var(--risk-fill); stroke-width: 2; }
.scene-question .pill-2 { fill: var(--stop-soft); stroke: var(--stop); stroke-width: 2; }
.scene-question .txt-0 { fill: var(--go); font-weight: 600; }
.scene-question .txt-1 { fill: var(--risk); font-weight: 600; }
.scene-question .txt-2 { fill: var(--stop); font-weight: 600; }
.scene-question.tip { position: fixed; z-index: 20; display: none; max-width: 280px; padding: 6px 10px; border-radius: var(--r-small);
  background: var(--ink); color: var(--card); font: 500 14px/1.35 var(--font); pointer-events: none; }
`

const RIVER = 'M285 0C255 120 315 260 280 400L370 400C405 260 345 120 375 0Z'
// Bridge decks from north to south: Північний, Подільсько-Воскресенський, Метро (M1), Патона, Дарницький, Південний (M3)
const DECKS = [70, 115, 175, 230, 285, 345]
// The blue line M2 runs north to south on the right bank only: it meets M1 and M3 at transfer stations and never crosses the river
const M2X = 94
const ROAD_TIPS = [
  [70, 'Північний міст: авто без обмежень під час тривоги'],
  [115, 'Подільсько-Воскресенський міст: під час тривоги стоїть 15 хвилин на початку і після відбою'],
  [230, 'Міст Патона: авто без обмежень під час тривоги'],
  [285, 'Дарницький міст: авто без обмежень під час тривоги'],
]
const MAP_TIPS = [
  'Схема Києва: правий берег ліворуч, лівий праворуч, північ угорі',
  'Жовтий рівень, загроза дронів: M1 лише під землею, M3 їде мостом',
  'Червоний рівень, ракети або масована атака: метро через Дніпро не їде',
]
const TIERS = ['низький ризик', 'середній ризик', 'високий ризик']
const X0 = 60
const X1 = 580
const PILL_W = 190
const PILL_X = [20, 225, 430]

const T = (x, y, text, cls = '', anchor) => s('text', { x, y, class: cls, 'text-anchor': anchor, text })
const fmt = (p) => pct(p, 1).replace('.0%', '%')
const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null)

const badge = (y, label, cls, cx = 43) => s('g', {},
  s('rect', { x: cx - 23, y: y - 16, width: 46, height: 32, rx: 16, class: cls }), T(cx, y + 8, label, 'on-dark', 'middle'))
const levelPill = (label, cls, tcls) => s('g', {},
  s('rect', { x: 200, y: 6, width: 240, height: 40, rx: 20, class: cls }), T(320, 34, label, tcls, 'middle'))
const train = (cx, cy) => s('rect', { x: cx - 16, y: cy - 8, width: 32, height: 16, rx: 8, class: 'q-train' }) // not .train: the answer tab styles that class
const stop = (cx, cy) => s('g', { class: 'stop' },
  s('circle', { cx, cy, r: 14 }), s('path', { d: `M${cx - 9} ${cy - 9}L${cx + 9} ${cy + 9}` }))
const stations = (xs, y, cls) => xs.map((x) => s('circle', { cx: x, cy: y, r: 5, class: `station ${cls}` }))

let TH = null // thresholds of the last mount, used by the note of step 4

function thresholds() {
  if (!TH) return 'Пороги рівнів ризику зараз не завантажились.'
  return `Нижче ${fmt(TH.busy)} ризик низький, від ${fmt(TH.high)} високий, між ними середній.`
}

// Sources go into a folded block at the end of the note; file paths and code names live only there
const SRC = (text) => `<details class="how-src"><summary>Джерела</summary><p>${text}</p></details>`

const IDEA = {
  title: 'Ідея автора',
  text: 'Чи встигну я переїхати з одного берега на інший. І для цього закладається три години з моменту виїзду.',
  source: 'із завдання автора, 11.10.2026',
}

const QUESTION = {
  title: 'Питання до моделі',
  text: 'На початку кожної години t: чи прилетять у Київ дрони або ракети (або буде ракетна загроза) протягом наступних 3 годин, тобто в години t, t + 1, t + 2? Відповідь: ймовірність, вердикт «швидше тихо» чи «неспокійно» з рівнем ризику, і 3 головні причини.',
  source: 'опис моделі, розділ 1',
}

export default {
  id: ID,
  title: 'Чи встигнеш переїхати на інший берег?',
  lead: 'Під час тривоги метро через Дніпро ходить менше або стоїть, тому ми прогнозуємо атаку на 3 години вперед.',
  steps: [
    {
      note: '<p>Київ стоїть на двох берегах Дніпра. Річку перетинають дві лінії метро: червона M1 мостом Метро і зелена M3 Південним мостом. Синя M2 лишається на правому березі, а для авто є шість мостів.</p>'
        + SRC('Схема, не мапа: північ угорі, кольори ліній як у метро. УНІАН, 07.09.2026; Укрінформ, 03.10.2026.'),
    },
    {
      note: '<p>Тривога це офіційна повітряна тривога в Києві, жовтий рівень означає загрозу дронів. За будь-якої тривоги червона M1 ходить лише під землею, від Академмістечка до Арсенальної. Через Дніпро їде лише зелена M3, Південним мостом.</p>'
        + SRC('КМДА через Знай.ua і DSnews, 17.09.2026; LB.ua, 04.10.2026; ZN.ua, 06.10.2026.'),
    },
    {
      note: '<p>Червоний рівень означає ракети або масовану атаку дронів: одразу в укриття. Метро через Дніпро не їде, M3 ходить двома ділянками: Сирець - Видубичі і Осокорки - Червоний хутір. Мости для авто відкриті, лише Південний (з правого берега на лівий) стоїть 15 хвилин від початку тривоги, а Подільсько-Воскресенський 15 хвилин на початку і після відбою.</p>'
        + SRC('Kyiv.news, 03.09.2026; LB.ua, 04.10.2026; КМВА через Укрінформ, 03.10.2026.'),
    },
    {
      get note() {
        return `<p>Тому модель щогодини дає ймовірність атаки на Київ у наступні 3 години: дрони летять на Київ, ракетна загроза або удар; 28% це приблизно 3 рази з 10. ${thresholds()} На тестових даних (з 29.08, відкладені до кінця) після низького ризику тривога в наступні 3 години була у 17% випадків (5 з 29), після високого у 74%.</p>`
          + SRC('Питання: docs/quiet/model.md, розділ 1. Пороги: api/model.json (busy_at, high_at). Частки: docs/quiet/forecast.md, таблиця 3, там рівень низького ризику ще зветься «швидше тихо»; README.md.')
      },
      prompts: [QUESTION],
    },
  ],
  prompts: [IDEA],

  mount(stage, data) {
    stage.append(h('style', { text: CSS }))
    const svg = canvas(stage, 'Схема Києва: Дніпро, шість мостів, лінії метро M1 і M3 через річку і M2 лише на правому березі, далі шкала прогнозу на 3 години')
    svg.classList.add(`scene-${ID}`)

    const busy = num(data?.model?.busy_at) ?? num(data?.now?.forecast?.busy_at)
    const high = num(data?.model?.high_at) ?? num(data?.now?.forecast?.high_at)
    TH = busy != null && high != null && busy < high ? { busy, high } : null

    // Steps 1 to 3: the city from above
    const river = s('path', { d: RIVER, class: 'river' })
    const decks = DECKS.map((y) => s('path', { d: `M256 ${y}H404`, class: 'deck' }))
    const banks = s('g', {}, T(20, 36, 'Правий берег', 'soft'), T(620, 36, 'Лівий берег', 'soft', 'end'))
    const dnipro = T(333, 262, 'Дніпро', 'soft', 'middle')
    const m1Out = s('g', {}, s('path', { d: 'M235 175H576', class: 'line m1' }), stations([262, 330, 418, 470, 522], 175, 'm1'),
      s('circle', { cx: 576, cy: 175, r: 7, class: 'station m1' }), T(584, 155, 'Лісова', 'soft', 'end'))
    const m1Under = s('g', {}, s('path', { d: 'M70 175H235', class: 'line m1' }), s('circle', { cx: 235, cy: 175, r: 6, class: 'station m1' }))
    const m3West = s('g', {}, s('path', { d: 'M70 345H245', class: 'line m3' }), s('circle', { cx: 245, cy: 345, r: 6, class: 'station m3' }))
    const m3Bridge = s('g', {}, s('path', { d: 'M245 345H465', class: 'line m3' }), stations([420], 345, 'm3'))
    const m3East = s('g', {}, s('path', { d: 'M465 345H576', class: 'line m3' }),
      s('circle', { cx: 465, cy: 345, r: 6, class: 'station m3' }), stations([502, 539], 345, 'm3'),
      s('circle', { cx: 576, cy: 345, r: 7, class: 'station m3' }), T(584, 380, 'Червоний хутір', 'soft', 'end'))
    const m2 = s('g', {}, s('path', { d: `M${M2X} 100V382`, class: 'line m2' }),
      s('circle', { cx: M2X, cy: 128, r: 5, class: 'station m2' }), s('circle', { cx: M2X, cy: 382, r: 6, class: 'station m2' }))
    const m2Hubs = s('g', {}, [175, 345].map((cy) => s('circle', { cx: M2X, cy, r: 6, class: 'station m2' })))
    const b1 = badge(175, 'M1', 'fill-m1')
    const b2 = badge(80, 'M2', 'fill-m2', M2X)
    const b3 = badge(345, 'M3', 'fill-m3')
    const t1 = train(305, 175)
    const t3 = train(300, 345)
    const stop1 = stop(300, 175)
    const stop3 = stop(335, 345)
    const lblA = T(238, 155, 'Арсенальна', '', 'end')
    const lblV = T(242, 325, 'Видубичі', '', 'end')
    const lblO = T(468, 325, 'Осокорки')
    const map = s('g', {}, river, decks, banks, dnipro, m2, m1Out, m1Under, m3Bridge, m3West, m3East, m2Hubs, b1, b2, b3,
      t1, t3, stop1, stop3, lblA, lblV, lblO)
    const yellow = levelPill('Жовтий рівень', 'pill-yellow', 'risk-text')
    const red = levelPill('Червоний рівень', 'pill-red', 'on-dark')

    // Step 4: the 3 hour window and the probability scale with the two thresholds
    const fq = T(320, 34, 'Чи буде атака в ці 3 години?', 'bold', 'middle')
    const fTicks = s('g', {},
      s('path', { d: 'M100 84V136', class: 'tick' }), T(100, 74, 'виїзд', 'soft', 'middle'),
      s('path', { d: 'M520 84V136', class: 'tick' }), T(520, 74, '04:00', 'soft', 'middle'))
    const fCells = ['01:00', '02:00', '03:00'].map((lab, i) => s('g', {},
      s('rect', { x: 102 + i * 140, y: 90, width: 136, height: 40, rx: 8, class: 'cell' }),
      T(170 + i * 140, 117, lab, '', 'middle')))
    const fCap = T(320, 168, 'ймовірність атаки', 'soft', 'middle')
    const xs = (TH ? [0, TH.busy, TH.high, 1] : [0, 1]).map((e) => X0 + (X1 - X0) * e)
    const fBar = s('g', {}, xs.slice(1).map((b, i) => s('rect', {
      x: xs[i] + 1, y: 202, width: Math.max(1, b - xs[i] - 2), height: 16, rx: 3, class: TH ? `bar-${i}` : 'bar-none',
    })))
    const fScale = s('g', {}, T(X0, 244, '0%', 'soft'), T(X1, 244, '100%', 'soft', 'end'),
      TH ? [
        s('path', { d: `M${xs[1]} 196V224`, class: 'tick' }), s('path', { d: `M${xs[2]} 196V224`, class: 'tick' }),
        T(xs[1] - 6, 192, fmt(TH.busy), 'bold', 'end'), T(xs[2] + 6, 192, fmt(TH.high), 'bold'),
      ] : null)
    const ranges = TH ? [`нижче ${fmt(TH.busy)}`, `від ${fmt(TH.busy)} до ${fmt(TH.high)}`, `від ${fmt(TH.high)}`] : []
    const fTier = TIERS.map((name, i) => {
      const cx = PILL_X[i] + PILL_W / 2
      return s('g', {},
        TH ? s('path', { d: `M${(xs[i] + xs[i + 1]) / 2} 224L${cx} 274`, class: 'lead' }) : null,
        s('rect', { x: PILL_X[i], y: 276, width: PILL_W, height: 40, rx: 20, class: `pill-${i}` }),
        T(cx, 303, name, `txt-${i}`, 'middle'),
        ranges[i] ? T(cx, 350, ranges[i], 'soft', 'middle') : null)
    })
    const fc = s('g', {}, fq, fTicks, fCells, fCap, fBar, fScale, fTier)
    svg.append(map, yellow, red, fc)

    // Tooltip: what is under the pointer at the current step (hover, or tap on a phone)
    let cur = 0
    const tip = h('div', { class: `scene-${ID} tip`, role: 'tooltip' })
    stage.append(tip)
    const hide = () => { tip.style.display = 'none' }
    function describe(x, y) {
      if (cur === 3) {
        if (y < 145) return 'Вікно прогнозу: 3 години від виїзду, наприклад з 01:00 до 04:00'
        if (TH && y > 180 && y < 360) {
          const p = (x - X0) / (X1 - X0)
          const i = y < 260 ? (p < TH.busy ? 0 : p < TH.high ? 1 : 2) : x < 217 ? 0 : x < 422 ? 1 : 2
          return [`низький ризик: ймовірність нижче ${fmt(TH.busy)}`, `середній ризик: від ${fmt(TH.busy)} до ${fmt(TH.high)}`,
            `високий ризик: від ${fmt(TH.high)}`][i]
        }
        return 'Ймовірність атаки на Київ за 3 години: дрони летять на Київ, ракетна загроза або удар'
      }
      const onBridge = x > 240 && x < 420
      if (Math.abs(y - 175) < 20) {
        if (cur === 0) return 'M1, міст Метро: поїзди їдуть через Дніпро'
        return 'M1 за будь-якої тривоги: лише під землею, від Академмістечка до Арсенальної'
          + (cur === 2 && onBridge ? '. Авто мостом Метро їдуть без обмежень' : '')
      }
      if (Math.abs(y - 345) < 20) {
        if (cur < 2) return 'M3, Південний міст: їде через Дніпро, у піки по одному поїзду на мосту'
        return 'M3 за червоного рівня: Сирець - Видубичі і Осокорки - Червоний хутір, через Дніпро не їде'
          + (onBridge ? '. Авто Південним мостом з правого берега на лівий стоять 15 хвилин від початку тривоги' : '')
      }
      if (Math.abs(x - M2X) < 18 && y > 60) return 'M2, синя лінія: лише правий берег, через Дніпро не йде'
      const road = ROAD_TIPS.find(([by]) => Math.abs(y - by) < 16 && onBridge)
      return road ? road[1] : MAP_TIPS[cur]
    }
    function say(e) {
      const m = svg.getScreenCTM()
      const p = m ? new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse()) : { x: -1, y: -1 }
      tip.textContent = describe(p.x, p.y)
      tip.style.display = 'block'
      const w = tip.offsetWidth
      const ht = tip.offsetHeight
      tip.style.left = `${Math.max(8, Math.min(e.clientX + 14, innerWidth - w - 8))}px`
      tip.style.top = `${e.clientY + 18 + ht > innerHeight ? Math.max(8, e.clientY - ht - 12) : e.clientY + 18}px`
    }
    const EVENTS = ['mousemove', 'mouseover', 'pointerdown']
    for (const ev of EVENTS) svg.addEventListener(ev, say)
    svg.addEventListener('mouseleave', hide)

    // Start state of every moving part, committed before the first show() so the first step animates in
    const PRE = [
      [river, { o: 0 }], ...decks.map((n) => [n, { kx: 0 }, LEFT]), [banks, { o: 0 }], [dnipro, { o: 0 }],
      [b1, { o: 0 }], [b2, { o: 0 }], [b3, { o: 0 }], [m2, { ky: 0 }, TOP], [m2Hubs, { o: 0 }],
      [m1Under, { kx: 0 }, LEFT], [m1Out, { kx: 0 }, LEFT], [m3West, { kx: 0 }, LEFT], [m3Bridge, { kx: 0 }, LEFT], [m3East, { kx: 0 }, LEFT],
      [t1, { o: 0, x: -24 }], [t3, { o: 0, x: -24 }], [stop1, { o: 0, k: 0.5 }], [stop3, { o: 0, k: 0.5 }],
      [lblA, { o: 0 }], [lblV, { o: 0 }], [lblO, { o: 0 }], [yellow, { o: 0, y: -6 }], [red, { o: 0, y: -6 }],
      [fc, { o: 0 }], [fq, { o: 0, y: 8 }], [fTicks, { o: 0 }], ...fCells.map((n) => [n, { o: 0, kx: 0.2 }, LEFT]),
      [fCap, { o: 0 }], [fBar, { kx: 0 }, LEFT], [fScale, { o: 0 }], ...fTier.map((n) => [n, { o: 0, y: 10 }]),
    ]
    for (const [n, st, origin] of PRE) put(n, st, { instant: true, origin })
    svg.getBoundingClientRect()

    function show(step, { instant = false } = {}) {
      cur = step
      hide()
      const A = (node, st, delay = 0, dur = 320, origin) => put(node, st, { delay, dur, origin, instant })
      const onMap = step < 3
      A(map, { o: onMap ? 1 : 0, k: onMap ? 1 : 0.97 }, onMap ? 120 : 0, 360)
      A(river, { o: 1 }, 0, 400)
      decks.forEach((n, i) => A(n, { kx: 1 }, stagger(i, 60, 150), 320, LEFT))
      A(banks, { o: 1 }, 250)
      A(dnipro, { o: 1 }, 350)
      A(b1, { o: 1 }, 400)
      A(b2, { o: 1 }, 400)
      A(b3, { o: 1 }, 400)
      A(m2, { ky: 1 }, 450, 400, TOP)
      A(m2Hubs, { o: 1 }, 850, 300)
      A(m1Under, { kx: 1 }, 450, 400, LEFT)
      A(m1Out, { kx: 1, o: step >= 1 ? 0.18 : 1 }, step >= 1 ? 250 : 650, 400, LEFT)
      A(m3West, { kx: 1, x: step >= 2 ? -12 : 0 }, step >= 2 ? 300 : 450, 400, LEFT)
      A(m3Bridge, { kx: 1, o: step >= 2 ? 0.15 : 1 }, step >= 2 ? 250 : 650, 400, LEFT)
      A(m3East, { kx: 1, x: step >= 2 ? 12 : 0 }, step >= 2 ? 300 : 850, 400, LEFT)
      // a yellow alert sends the M1 train back under the ground, a red one sends the M3 train back too
      A(t1, { o: 1, x: step >= 1 ? -120 : 0 }, step >= 1 ? 0 : 1050, 400)
      A(t3, { o: 1, x: step === 0 ? 0 : step === 1 ? 50 : -110 }, step === 0 ? 1050 : 0, 400)
      A(stop1, { o: step >= 1 ? 1 : 0, k: step >= 1 ? 1 : 0.5 }, step >= 1 ? 380 : 0, 300)
      A(stop3, { o: step >= 2 ? 1 : 0, k: step >= 2 ? 1 : 0.5 }, step >= 2 ? 380 : 0, 300)
      A(lblA, { o: step >= 1 ? 1 : 0 }, step >= 1 ? 450 : 0)
      A(lblV, { o: step >= 2 ? 1 : 0 }, step >= 2 ? 450 : 0)
      A(lblO, { o: step >= 2 ? 1 : 0 }, step >= 2 ? 450 : 0)
      A(yellow, { o: step === 1 ? 1 : 0, y: step === 1 ? 0 : -6 }, 0, 300)
      A(red, { o: step === 2 ? 1 : 0, y: step === 2 ? 0 : -6 }, 0, 300)

      const on = step === 3
      const d = (ms) => (on ? ms : 0)
      A(fc, { o: on ? 1 : 0 }, d(200), 300)
      A(fq, { o: on ? 1 : 0, y: on ? 0 : 8 }, d(250))
      A(fTicks, { o: on ? 1 : 0 }, d(400))
      fCells.forEach((n, i) => A(n, { o: on ? 1 : 0, kx: on ? 1 : 0.2 }, d(stagger(i, 160, 500)), 320, LEFT))
      A(fCap, { o: on ? 1 : 0 }, d(950))
      A(fBar, { kx: on ? 1 : 0 }, d(1000), 400, LEFT)
      A(fScale, { o: on ? 1 : 0 }, d(1300))
      fTier.forEach((n, i) => A(n, { o: on ? 1 : 0, y: on ? 0 : 10 }, d(stagger(i, 120, 1400))))
    }

    return {
      show,
      destroy() {
        for (const ev of EVENTS) svg.removeEventListener(ev, say)
        svg.removeEventListener('mouseleave', hide)
        tip.remove()
      },
    }
  },
}
