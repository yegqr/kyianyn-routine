// Scene 1 of the methodology deck: why the project asks "will the next 3 hours be quiet".
// Crossing facts: city announcements quoted by the media, checked 2026-10-11 (the same facts as ../crossing.js).
// The tier thresholds are read at runtime from api/model.json (busy_at, high_at), now.json is the fallback.
import { h, s, canvas, put, stagger } from '../how.js'
import { pct } from '../api.js'

const ID = 'question'
const LEFT = 'left center'

const CSS = `
.scene-question text { font-family: var(--font); font-size: 22px; fill: var(--ink); }
.scene-question .soft { fill: var(--soft); }
.scene-question .bold { font-weight: 600; }
.scene-question .on-dark { fill: var(--card); font-weight: 600; }
.scene-question .river { fill: var(--pink-soft); }
.scene-question .deck { fill: none; stroke: var(--soft); stroke-opacity: .45; stroke-width: 6; stroke-linecap: round; }
.scene-question .line { fill: none; stroke-width: 8; stroke-linecap: round; }
.scene-question .m1 { stroke: var(--pink); }
.scene-question .m3 { stroke: var(--ink); }
.scene-question .station { fill: var(--card); stroke-width: 3; }
.scene-question .fill-pink { fill: var(--pink); }
.scene-question .fill-ink { fill: var(--ink); }
.scene-question .pill-out { fill: var(--card); stroke: var(--ink); stroke-width: 2; }
.scene-question .train { fill: var(--card); stroke: var(--ink); stroke-width: 2.5; }
.scene-question .stop circle { fill: var(--card); stroke: var(--pink); stroke-width: 3; }
.scene-question .stop path { fill: none; stroke: var(--pink); stroke-width: 3; stroke-linecap: round; }
.scene-question .cell { fill: var(--pink-soft); stroke: var(--pink); stroke-width: 2; }
.scene-question .tick { fill: none; stroke: var(--ink); stroke-width: 2; }
.scene-question .lead { fill: none; stroke: var(--soft); stroke-width: 1.5; }
.scene-question .tier-0 { fill: var(--pink-soft); }
.scene-question .tier-1 { fill: var(--pink); fill-opacity: .5; }
.scene-question .tier-2 { fill: var(--pink); }
.scene-question.tip { position: fixed; z-index: 20; display: none; max-width: 280px; padding: 6px 10px; border-radius: var(--r-small);
  background: var(--ink); color: var(--card); font: 500 14px/1.35 var(--font); pointer-events: none; }
`

const RIVER = 'M285 0C255 120 315 260 280 400L370 400C405 260 345 120 375 0Z'
// Bridge decks from north to south: Північний, Подільсько-Воскресенський, Метро (M1), Патона, Дарницький, Південний (M3)
const DECKS = [70, 115, 175, 230, 285, 345]
const ROAD_TIPS = [
  [70, 'Північний міст: авто без обмежень під час тривоги'],
  [115, 'Подільсько-Воскресенський міст: під час тривоги стоп 15 хв на початку і після відбою'],
  [230, 'Міст Патона: авто без обмежень під час тривоги'],
  [285, 'Дарницький міст: авто без обмежень під час тривоги'],
]
const MAP_TIPS = [
  'Схема Києва: правий берег ліворуч, лівий праворуч, північ угорі',
  'Жовтий рівень, загроза дронів: M1 лише під землею, M3 їде мостом',
  'Червоний рівень, ракети або масована атака: метро через Дніпро не їде',
]
const TIERS = ['швидше тихо', 'середній ризик', 'високий ризик']
const X0 = 60
const X1 = 580
const PILL_W = 190
const PILL_X = [20, 225, 430]

const T = (x, y, text, cls = '', anchor) => s('text', { x, y, class: cls, 'text-anchor': anchor, text })
const fmt = (p) => pct(p, 1).replace('.0%', '%')
const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null)

const badge = (y, label, cls) => s('g', {},
  s('rect', { x: 20, y: y - 16, width: 46, height: 32, rx: 16, class: cls }), T(43, y + 8, label, 'on-dark', 'middle'))
const levelPill = (label, cls, tcls) => s('g', {},
  s('rect', { x: 200, y: 6, width: 240, height: 40, rx: 20, class: cls }), T(320, 34, label, tcls, 'middle'))
const train = (cx, cy) => s('rect', { x: cx - 16, y: cy - 8, width: 32, height: 16, rx: 8, class: 'train' })
const stop = (cx, cy) => s('g', { class: 'stop' },
  s('circle', { cx, cy, r: 14 }), s('path', { d: `M${cx - 9} ${cy - 9}L${cx + 9} ${cy + 9}` }))
const stations = (xs, y, cls) => xs.map((x) => s('circle', { cx: x, cy: y, r: 5, class: `station ${cls}` }))

let TH = null // thresholds of the last mount, used by the note of step 4

function thresholds() {
  if (!TH) return 'Пороги рівнів беремо з api/model.json, зараз він не завантажився.'
  return `Нижче ${fmt(TH.busy)} це «швидше тихо», від ${fmt(TH.high)} «високий ризик», між ними «середній ризик» (пороги з api/model.json).`
}

const IDEA = {
  title: 'Ідея автора',
  text: 'Чи встигну я переїхати з одного берега на інший. І для цього закладається три години з моменту виїзду.',
  source: 'бриф автора для Claude Code, 2026-10-11',
}

const QUESTION = {
  title: 'Питання до моделі',
  text: 'На початку кожної години t: чи прилетять у Київ дрони або ракети (або буде ракетна загроза) протягом наступних 3 годин, тобто в години t, t + 1, t + 2? Відповідь: ймовірність, вердикт «швидше тихо» чи «неспокійно» з рівнем ризику, і 3 головні причини.',
  source: 'docs/quiet/model.md, розділ 1',
}

export default {
  id: ID,
  title: 'Питання: чи встигну перетнути Дніпро',
  lead: 'Тривога забирає метро через річку, тому питання «чи встигну» стає прогнозом на 3 години.',
  steps: [
    {
      note: '<p>Київ стоїть на двох берегах Дніпра, на схемі північ угорі. Метро перетинає річку двічі: червона лінія M1 мостом Метро і зелена M3 Південним мостом, а синя M2 через Дніпро не йде. Для авто й автобусів шість мостів: Північний, Подільсько-Воскресенський, Метро, Патона, Дарницький і Південний.</p>'
        + '<p><small>Схема, не мапа: M1 рожева, M3 темна. Джерела: УНІАН, 07.09.2026; Укрінформ, 03.10.2026.</small></p>',
    },
    {
      note: '<p>Жовтий рівень означає загрозу дронів. Будь-яка тривога зупиняє M1 над Дніпром: поїзди ходять лише під землею Академмістечко - Арсенальна, бо відкрита ділянка задовга. Зелена M3 і далі їде Південним мостом, у піки там по одному поїзду.</p>'
        + '<p><small>КМДА через Знай.ua і DSnews, 17.09.2026; LB.ua, 04.10.2026; ZN.ua, 06.10.2026.</small></p>',
    },
    {
      note: '<p>Червоний рівень: ракети або масована атака дронів, треба одразу в укриття. M3 ділиться на дві ділянки, Сирець - Видубичі і Осокорки - Червоний хутір, тож метро через Дніпро не їде зовсім. Мости для авто відкриті: лише Південний з правого берега на лівий стоїть 15 хв від початку тривоги, а Подільсько-Воскресенський 15 хв на початку і після відбою.</p>'
        + '<p><small>Kyiv.news, 03.09.2026; LB.ua, 04.10.2026; КМВА через Укрінформ, 03.10.2026.</small></p>',
    },
    {
      get note() {
        return `<p>Тому питання стає прогнозом: чи буде тихо 3 години від виїзду, тобто в години t, t + 1 і t + 2. Модель дає ймовірність, що за цей час прилетять дрони чи ракети або буде ракетна загроза. ${thresholds()} На тесті після «швидше тихо» тривога за 3 години була у 17% випадків (5 з 29), після «високого ризику» у 74%.</p>`
          + '<p><small>Питання: docs/quiet/model.md, розділ 1. Частки: README.md, docs/quiet/forecast.md.</small></p>'
      },
      prompts: [QUESTION],
    },
  ],
  prompts: [IDEA],

  mount(stage, data) {
    stage.append(h('style', { text: CSS }))
    const svg = canvas(stage, 'Схема Києва: Дніпро, шість мостів і дві лінії метро через річку, далі шкала прогнозу на 3 години')
    svg.classList.add(`scene-${ID}`)

    const busy = num(data?.model?.busy_at) ?? num(data?.now?.forecast?.busy_at)
    const high = num(data?.model?.high_at) ?? num(data?.now?.forecast?.high_at)
    TH = busy != null && high != null && busy < high ? { busy, high } : null

    // Steps 1 to 3: the city from above
    const river = s('path', { d: RIVER, class: 'river' })
    const decks = DECKS.map((y) => s('path', { d: `M256 ${y}H404`, class: 'deck' }))
    const banks = s('g', {}, T(20, 36, 'Правий берег', 'soft'), T(620, 36, 'Лівий берег', 'soft', 'end'))
    const dnipro = T(333, 262, 'Дніпро', 'soft', 'middle')
    const m1Out = s('g', {}, s('path', { d: 'M235 175H612', class: 'line m1' }), stations([262, 330, 420, 480, 540, 600], 175, 'm1'))
    const m1Under = s('g', {}, s('path', { d: 'M70 175H235', class: 'line m1' }), s('circle', { cx: 235, cy: 175, r: 6, class: 'station m1' }))
    const m3West = s('g', {}, s('path', { d: 'M70 345H245', class: 'line m3' }), s('circle', { cx: 245, cy: 345, r: 6, class: 'station m3' }))
    const m3Bridge = s('g', {}, s('path', { d: 'M245 345H465', class: 'line m3' }), stations([420], 345, 'm3'))
    const m3East = s('g', {}, s('path', { d: 'M465 345H612', class: 'line m3' }),
      s('circle', { cx: 465, cy: 345, r: 6, class: 'station m3' }), stations([515, 565, 612], 345, 'm3'))
    const b1 = badge(175, 'M1', 'fill-pink')
    const b3 = badge(345, 'M3', 'fill-ink')
    const t1 = train(305, 175)
    const t3 = train(300, 345)
    const stop1 = stop(300, 175)
    const stop3 = stop(335, 345)
    const lblA = T(238, 155, 'Арсенальна', '', 'end')
    const lblV = T(242, 325, 'Видубичі', '', 'end')
    const lblO = T(468, 325, 'Осокорки')
    const map = s('g', {}, river, decks, banks, dnipro, m1Out, m1Under, m3Bridge, m3West, m3East, b1, b3,
      t1, t3, stop1, stop3, lblA, lblV, lblO)
    const yellow = levelPill('Жовтий рівень', 'pill-out', 'bold')
    const red = levelPill('Червоний рівень', 'fill-pink', 'on-dark')

    // Step 4: the 3 hour window and the probability scale with the two thresholds
    const fq = T(320, 34, 'Чи буде тихо 3 години?', 'bold', 'middle')
    const fTicks = s('g', {},
      s('path', { d: 'M100 84V136', class: 'tick' }), T(100, 74, 'виїзд', 'soft', 'middle'),
      s('path', { d: 'M520 84V136', class: 'tick' }), T(520, 74, '+3 год', 'soft', 'middle'))
    const fCells = ['t', 't + 1', 't + 2'].map((lab, i) => s('g', {},
      s('rect', { x: 102 + i * 140, y: 90, width: 136, height: 40, rx: 8, class: 'cell' }),
      T(170 + i * 140, 117, lab, '', 'middle')))
    const fCap = T(320, 168, 'ймовірність, що прилетить', 'soft', 'middle')
    const xs = (TH ? [0, TH.busy, TH.high, 1] : [0, 1]).map((e) => X0 + (X1 - X0) * e)
    const fBar = s('g', {}, xs.slice(1).map((b, i) => s('rect', {
      x: xs[i] + 1, y: 202, width: Math.max(1, b - xs[i] - 2), height: 16, rx: 3, class: TH ? `tier-${i}` : 'tier-0',
    })))
    const fScale = s('g', {}, T(X0, 244, '0%', 'soft'), T(X1, 244, '100%', 'soft', 'end'),
      TH ? [
        s('path', { d: `M${xs[1]} 196V224`, class: 'tick' }), s('path', { d: `M${xs[2]} 196V224`, class: 'tick' }),
        T(xs[1] - 6, 192, fmt(TH.busy), 'bold', 'end'), T(xs[2] + 6, 192, fmt(TH.high), 'bold'),
      ] : null)
    const ranges = TH ? [`нижче ${fmt(TH.busy)}`, `${fmt(TH.busy)} до ${fmt(TH.high)}`, `від ${fmt(TH.high)}`] : []
    const fTier = TIERS.map((name, i) => {
      const cx = PILL_X[i] + PILL_W / 2
      return s('g', {},
        TH ? s('path', { d: `M${(xs[i] + xs[i + 1]) / 2} 224L${cx} 274`, class: 'lead' }) : null,
        s('rect', { x: PILL_X[i], y: 276, width: PILL_W, height: 40, rx: 20, class: `tier-${i}` }),
        T(cx, 303, name, i === 2 ? 'on-dark' : 'bold', 'middle'),
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
        if (y < 145) return 'Вікно прогнозу: години t, t + 1 і t + 2 від виїзду'
        if (TH && y > 180 && y < 360) {
          const p = (x - X0) / (X1 - X0)
          const i = y < 260 ? (p < TH.busy ? 0 : p < TH.high ? 1 : 2) : x < 217 ? 0 : x < 422 ? 1 : 2
          return [`швидше тихо: ймовірність нижче ${fmt(TH.busy)}`, `середній ризик: від ${fmt(TH.busy)} до ${fmt(TH.high)}`,
            `високий ризик: ${fmt(TH.high)} і вище`][i]
        }
        return 'Ймовірність, що за 3 години прилетять дрони чи ракети або буде ракетна загроза'
      }
      if (Math.abs(y - 175) < 20) {
        return cur === 0 ? 'M1, міст Метро: поїзди їдуть через Дніпро'
          : 'M1 за будь-якої тривоги: лише під землею Академмістечко - Арсенальна'
      }
      if (Math.abs(y - 345) < 20) {
        return cur < 2 ? 'M3, Південний міст: їде через Дніпро, у піки по одному поїзду на мосту'
          : 'M3 за червоного рівня: Сирець - Видубичі і Осокорки - Червоний хутір, через Дніпро не їде'
      }
      const road = ROAD_TIPS.find(([by]) => Math.abs(y - by) < 16 && x > 240 && x < 420)
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
      [river, { o: 0 }], ...decks.map((n) => [n, { kx: 0 }, LEFT]), [banks, { o: 0 }], [dnipro, { o: 0 }], [b1, { o: 0 }], [b3, { o: 0 }],
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
      A(b3, { o: 1 }, 400)
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
