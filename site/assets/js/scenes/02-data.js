// Scene 2 of the methodology deck: the data. Where it comes from, how much of it there is, which sources helped
// the forecast and what the live site reads. Numbers: README.md (sections Коротко and Дані), docs/quiet/sources.md,
// docs/data/PARSING.md (section 1).
import { h, s, canvas, put, stagger } from '../how.js'

const ID = 'data'
const LEFT = 'left center'

const CSS = `
.scene-data text { font-family: var(--font); font-size: 22px; fill: var(--ink); }
.scene-data .soft { fill: var(--soft); }
.scene-data .bold { font-weight: 600; }
.scene-data .big { font-family: var(--font-display); font-size: 38px; font-weight: 700; }
.scene-data .pink { fill: var(--pink); }
.scene-data .on-dark { fill: var(--card); font-weight: 600; }
.scene-data .src { fill: var(--card); stroke: var(--line); stroke-width: 2; }
.scene-data .hi { fill: var(--pink-soft); stroke: var(--pink); stroke-width: 2; }
.scene-data .plain { fill: var(--card); stroke: var(--ink); stroke-width: 2; }
.scene-data .strike { fill: none; stroke: var(--ink); stroke-width: 2.5; stroke-linecap: round; }
.scene-data .box { fill: var(--card); stroke: var(--ink); stroke-width: 2; }
.scene-data .row { fill: var(--line); }
.scene-data .row-on { fill: var(--pink); }
.scene-data .dot { fill: var(--pink); }
.scene-data .axis { fill: none; stroke: var(--soft); stroke-width: 1.5; }
.scene-data .win { fill: var(--pink); fill-opacity: .3; }
.scene-data .bar { fill: var(--soft); fill-opacity: .45; }
.scene-data .bar-hi { fill: var(--pink); }
.scene-data .wire { fill: none; stroke: var(--soft); stroke-width: 2; }
.scene-data.tip { position: fixed; z-index: 20; display: none; max-width: 280px; padding: 6px 10px; border-radius: var(--r-small);
  background: var(--ink); color: var(--card); font: 500 14px/1.35 var(--font); pointer-events: none; }
`

// The sources of the README table (section Дані), top to bottom, with what each gives
const SOURCES = ['Офіційні тривоги', '7 київських каналів', 'Сигнали підготовки', 'Погода', 'Сонце і місяць', 'Дати й політика', 'Удари по Росії']
const SRC_TIPS = [
  'Офіційні тривоги з каналу КМВА: початок і кінець до хвилини, з вересня ще й рівень',
  '7 київських каналів: мітки «ракетний удар», «ракетна загроза», «дрони на Київ» за годинами',
  'Моніторингові канали: стратегічна авіація, МіГ-31К, хвилі ударних дронів',
  'Погода: прогноз Open-Meteo',
  'Сонце і місяць над Києвом: рахуємо самі, без мережі',
  'Символічні дати, візити, саміти, переговори: таблиця 100 дат, сайт Кремля, Вікіпедія, канал ОП',
  'Удари по Росії і запуски по Україні: мапа ударів дронів, день відомий через 30 годин',
]
// Verdicts of docs/quiet/sources.md, shown on step 3
const VERDICTS = [
  'потрібні, щоб знати, чи тривога зараз',
  'фінальна модель бере з них 4 колонки',
  'головне джерело: разом з годиною й днем тижня 0.081',
  'прогнозу не допомагає',
  'можна, але не потрібно',
  'прогнозу не допомагає',
  'прогнозу не допомагає',
]
const STRUCK = [3, 5, 6]
const PY = (i) => 30 + i * 48
const CY = (i) => PY(i) + 19
const LANES = [110, 200, 290]

// BSS on development, "now quiet" hours, the same model retrained per set (docs/quiet/sources.md)
const BARS = [
  { label: 'година й день тижня', v: 0.024, tip: 'Лише година доби і день тижня: виграш 0.024 на навчальних даних' },
  { label: '+ сигнали підготовки', v: 0.081, hi: true, tip: 'Година, день тижня і сигнали підготовки: виграш 0.081, головне джерело' },
  { label: 'усі джерела разом', v: 0.030, tip: 'Усі джерела разом: виграш 0.030, зайві джерела додають шум' },
]
const BX = 320
const BW = 280
const BMAX = 0.09

// What the live site reads (docs/quiet/sources.md, docs/data/PARSING.md section 1)
const LIVE = [
  { method: 'шаблон', cls: 'plain', out: 'старт, відбій', sub: 'без мовної моделі',
    tip: 'Офіційні тривоги: шаблон тексту без мовної моделі дає старт, відбій і рівень' },
  { method: 'Jev, набір 1', cls: 'hi', out: 'мітки атак', tip: '7 київських каналів: Jev, перший набір питань, мітки атак на Київ' },
  { method: 'Jev, набір 2', cls: 'hi', out: 'хвилі дронів',
    tip: '6 моніторингових каналів: спершу шаблон, потім Jev, другий набір питань, лише для відібраних постів' },
]
const VOL_TIPS = ['163 042 пости з 17 публічних каналів Telegram з 16.04.2026', '36 006 платних запитів до мовної моделі Jev', '$9.06 за всі запити до Jev разом']

// Timeline of step 2: posts from 2026-04-16, the model data 2026-05-01..2026-10-10 (README.md)
const D0 = Date.UTC(2026, 3, 16)
const D1 = Date.UTC(2026, 4, 1)
const D2 = Date.UTC(2026, 9, 10)
const tx = (d) => 320 + (300 * (d - D0)) / (D2 - D0)

const T = (x, y, text, cls = '', anchor) => s('text', { x, y, class: cls, 'text-anchor': anchor, text })

// Sources go into a folded block at the end of the note; file paths and code names live only there
const SRC = (text) => `<details class="how-src"><summary>Джерела</summary><p>${text}</p></details>`

const REGEX = {
  title: 'Як шаблон бачить старт тривоги',
  text: String.raw`Старт: ^((м\.\s*Київ\s*[-${'\u2013'}]\s*)?[Пп]овітряна тривога|(Червоний|Жовтий) рівень небезпеки|(У Києві |У столиці )?[Оо]голошено повітряну тривогу); рівень red, якщо в head є «Червоний», yellow, якщо «Жовтий», інакше alert.`,
  source: 'опис збору даних, розділ 1',
}

const RULE = {
  title: 'Правило, записане до оцінки',
  text: 'До оцінки я записав правило: найменший набір джерел, чий BSS на розробці не нижчий за BSS моделі на всіх джерелах мінус 0.01.',
  source: 'опис джерел, «Формальне правило»',
}

export default {
  id: ID,
  title: 'Дані: що читали і що допомогло',
  lead: 'Ми прочитали 163 тисячі постів із 17 каналів, і головне для прогнозу дали сигнали підготовки удару.',
  steps: [
    {
      note: '<p>Сюди стікається все: офіційні тривоги, 7 київських каналів, сигнали підготовки удару (зліт стратегічної авіації, хвилі дронів), погода, сонце й місяць, дати й політика, удари по Росії. Усе сходиться в таблицю для питання: рядок на годину, і в ньому лише те, що було відомо до цієї години.</p>'
        + SRC('README.md, розділ «Дані»; docs/data/PARSING.md. Тривоги з каналу КМВА @VA_Kyiv, погода Open-Meteo, удари по Росії з dronestrikemap.com; публічні канали Telegram читаємо зі сторінки t.me/s; таблиця для питання це рівень gold, docs/data/gold/kyiv_quiet.md.'),
    },
    {
      note: '<p>З 16 квітня 2026 зібрано 163 042 пости з 17 каналів, а дані для моделі охоплюють години з 1 травня до 10 жовтня. Пости читала Jev, мовна модель штучного інтелекту, що відповідає на питання про текст. 36 006 платних запитів до неї коштували разом $9.06.</p>'
        + SRC('README.md, розділи «Коротко» і «Дані»; docs/HANDOFF.md; docs/HISTORY.md.'),
    },
    {
      note: '<p>Виграш над простим правилом (BSS) показує, наскільки прогноз точніший, ніж завжди казати звичайну частку атак: 0 означає не краще. На навчальних даних (до 28.08) година й день тижня дають 0.024, із сигналами підготовки 0.081, усі джерела разом 0.030. Правило з картки рівнялось на цей слабкий результат, тож формально перемогла сама година; вибір відклали, і сайт працює на фінальній моделі (година, сигнали, київські канали): 0.094.</p>'
        + SRC('docs/quiet/sources.md: «Відповідь», «Формальне правило», таблиця джерел. Ту саму модель навчали заново для кожного набору джерел; виграш рахували на спокійних годинах (quiet_now), 8 тижнів навчальних даних (dev); година й день тижня там звуться «годинник». Погода, політика, дати й удари по Росії прогнозу не допомагають.'),
      prompts: [RULE],
    },
    {
      note: '<p>Живий сайт читає лише 10 каналів: 7 київських і 6 моніторингових, 3 з них спільні. Офіційні тривоги розбирає простий шаблон тексту, без мовної моделі: старт, відбій і рівень. Jev отримує два набори питань: про атаки з київських каналів і про сигнали підготовки з моніторингових.</p>'
        + SRC('docs/quiet/sources.md; README.md; docs/data/PARSING.md, розділ 1. Шаблон тексту це regex; тривоги з каналу КМВА @VA_Kyiv.'),
    },
  ],
  prompts: [REGEX],

  mount(stage) {
    stage.append(h('style', { text: CSS }))
    const svg = canvas(stage, 'Джерела даних, їх обсяг, які з них допомогли прогнозу і що читає живий сайт')
    svg.classList.add(`scene-${ID}`)

    // Source pills; the signals pill gets a pink overlay, three useless sources get a strike line
    const hi = s('rect', { x: 20, y: PY(2), width: 250, height: 38, rx: 19, class: 'hi' })
    const strikes = []
    const srcs = SOURCES.map((label, i) => {
      const g = s('g', {}, s('rect', { x: 20, y: PY(i), width: 250, height: 38, rx: 19, class: 'src' }), i === 2 ? hi : null,
        T(145, PY(i) + 26, label, '', 'middle'))
      if (STRUCK.includes(i)) {
        const line = s('path', { d: `M38 ${CY(i)}H252`, class: 'strike' })
        strikes.push(line)
        g.append(line)
      }
      return g
    })

    // Step 1: every source sends a post into the gold table, a row per hour lights up
    const rowsOn = [0, 1, 2, 3].map((r) => s('rect', { x: 446, y: 122 + r * 34, width: 158, height: 20, rx: 6, class: 'row-on' }))
    const box = s('g', {},
      T(525, 60, 'таблиця', 'bold', 'middle'), T(525, 88, 'для питання', 'bold', 'middle'),
      s('rect', { x: 430, y: 102, width: 190, height: 160, rx: 12, class: 'box' }),
      [0, 1, 2, 3].map((r) => s('rect', { x: 446, y: 122 + r * 34, width: 158, height: 20, rx: 6, class: 'row' })),
      rowsOn,
      T(525, 296, 'рядок на годину', 'soft', 'middle'))
    const dots = SOURCES.map((_, i) => {
      const c = s('circle', { cx: 280, cy: CY(i), r: 6, class: 'dot' })
      const mv = s('g', {}, c)
      return { c, mv, out: s('g', {}, mv), dx: 440 - 280, dy: 132 + i * 18 - CY(i) }
    })

    // Step 2: the volume
    const vol = [
      ['163 042', 'постів у 17 каналах', 'big'],
      ['36 006', 'платних запитів до Jev', 'big'],
      ['$9.06', 'за всі запити разом', 'big pink'],
    ].map(([n, lab, cls], i) => s('g', {}, T(320, 76 + i * 90, n, cls), T(320, 104 + i * 90, lab, 'soft')))
    const tl = s('g', {},
      s('path', { d: 'M320 340H620', class: 'axis' }), s('path', { d: 'M320 330V350', class: 'axis' }),
      T(320, 374, '16.04', 'soft'), T(tx(D1), 324, '01.05', 'soft'), T(620, 374, '10.10', 'soft', 'end'),
      T(620, 324, 'дані моделі', 'soft', 'end'))
    const win = s('rect', { x: tx(D1), y: 333, width: 620 - tx(D1), height: 14, rx: 4, class: 'win' })

    // Step 3: BSS of three source sets
    const bssHead = s('g', {}, T(BX, 40, 'виграш (BSS)', 'bold'), T(BX, 340, 'більше краще', 'soft'), s('path', { d: `M${BX} 90V300`, class: 'axis' }))
    const bars = BARS.map((b, i) => {
      const y = 96 + i * 84
      const w = (BW * b.v) / BMAX
      return {
        label: T(BX + 8, y - 10, b.label),
        rect: s('rect', { x: BX, y, width: w, height: 28, rx: 4, class: b.hi ? 'bar-hi' : 'bar' }),
        value: b.hi ? T(BX + w - 8, y + 21, b.v.toFixed(3), 'on-dark', 'end') : T(BX + w + 8, y + 21, b.v.toFixed(3)),
      }
    })

    // Step 4: three live lanes, source to method to what comes out
    const liveHead = T(20, 48, 'наживо: 10 каналів', 'bold')
    const lanes = LIVE.map((l, i) => {
      const cy = LANES[i]
      return s('g', {},
        s('path', { d: `M272 ${cy}H290`, class: 'wire' }),
        s('rect', { x: 290, y: cy - 19, width: 150, height: 38, rx: 19, class: l.cls }),
        T(365, cy + 7, l.method, '', 'middle'),
        s('path', { d: `M440 ${cy}H456`, class: 'wire' }),
        T(462, cy + 7, l.out),
        l.sub ? T(365, cy + 44, l.sub, 'soft', 'middle') : null)
    })

    svg.append(...srcs, box, ...dots.map((d) => d.out), ...vol, tl, win, bssHead,
      ...bars.flatMap((b) => [b.rect, b.label, b.value]), liveHead, ...lanes)

    // Tooltip: what is under the pointer at the current step (hover, or tap on a phone)
    let cur = 0
    const tip = h('div', { class: `scene-${ID} tip`, role: 'tooltip' })
    stage.append(tip)
    const hide = () => { tip.style.display = 'none' }
    const clamp = (v, n) => Math.max(0, Math.min(n - 1, v))
    function describe(x, y) {
      if (cur === 3) {
        const i = LANES.findIndex((c) => Math.abs(y - c) < 45)
        return i >= 0 ? LIVE[i].tip : 'Живий сайт: 10 каналів Telegram, 3 з них спільні для київських і моніторингових'
      }
      if (x < 285) {
        const i = clamp(Math.floor((y - 25) / 48), SOURCES.length)
        return cur === 2 ? `${SOURCES[i]}: ${VERDICTS[i]}` : SRC_TIPS[i]
      }
      if (cur === 0) return 'Таблиця для питання: рядок на кожну годину, у ньому лише те, що було відомо до неї'
      if (cur === 1) {
        return y > 305 ? 'Пости з 16.04.2026; дані для моделі: години з 01.05.2026 до 10.10.2026'
          : VOL_TIPS[clamp(Math.floor((y - 40) / 90), 3)]
      }
      return BARS[clamp(Math.floor((y - 60) / 84), 3)].tip
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

    const PRE = [
      ...srcs.map((n) => [n, { o: 0, x: -20 }]), ...strikes.map((n) => [n, { kx: 0 }, LEFT]), [hi, { o: 0 }], [box, { o: 0, k: 0.94 }],
      ...dots.flatMap((d) => [[d.out, { o: 1 }], [d.mv, {}], [d.c, { o: 0 }]]), ...rowsOn.map((n) => [n, { o: 0 }]),
      ...vol.map((n) => [n, { o: 0, y: 10 }]), [tl, { o: 0 }], [win, { kx: 0 }, LEFT], [bssHead, { o: 0 }],
      ...bars.flatMap((b) => [[b.label, { o: 0 }], [b.rect, { kx: 0 }, LEFT], [b.value, { o: 0 }]]),
      [liveHead, { o: 0 }], ...lanes.map((n) => [n, { o: 0, x: -12 }]),
    ]
    for (const [n, st, origin] of PRE) put(n, st, { instant: true, origin })
    svg.getBoundingClientRect()

    function show(step, { instant = false } = {}) {
      cur = step
      hide()
      const A = (node, st, delay = 0, dur = 320, origin) => put(node, st, { delay, dur, origin, instant })
      srcs.forEach((g, i) => {
        const keep = i <= 2
        const gone = step === 3 && !keep
        const o = gone ? 0 : step === 1 ? 0.35 : step === 2 && !keep ? 0.4 : 1
        const y = step === 3 && keep ? LANES[i] - CY(i) : 0
        A(g, { o, x: gone ? -20 : 0, y }, step === 0 ? stagger(i, 70) : step === 3 && keep ? 300 : 0, step === 3 ? 400 : 320)
      })
      strikes.forEach((n, j) => A(n, { kx: step === 2 ? 1 : 0 }, step === 2 ? stagger(j, 120, 600) : 0, 320, LEFT))
      A(hi, { o: step >= 2 ? 1 : 0 }, step === 2 ? 900 : 0)

      // step 1: replay the flow of posts into the table whenever the step is entered with animation
      A(box, { o: step === 0 ? 1 : 0, k: step === 0 ? 1 : 0.94 }, step === 0 ? 350 : 0)
      const replay = step === 0 && !instant
      if (replay) {
        for (const d of dots) {
          put(d.out, { o: 1 }, { instant: true })
          put(d.mv, {}, { instant: true })
          put(d.c, { o: 0 }, { instant: true })
        }
        for (const r of rowsOn) put(r, { o: 0 }, { instant: true })
        svg.getBoundingClientRect()
      }
      dots.forEach((d, i) => {
        A(d.c, { o: 1 }, replay ? stagger(i, 80, 500) : 0, 200)
        A(d.mv, { x: d.dx, y: d.dy }, replay ? stagger(i, 80, 650) : 0, 400)
        A(d.out, { o: 0 }, replay ? stagger(i, 80, 1000) : 0, 200)
      })
      rowsOn.forEach((r, k) => A(r, { o: step === 0 ? 1 : 0 }, replay ? stagger(k, 120, 1150) : 0))

      // step 2: the volume and the window of the model data sliding along the timeline
      const v = step === 1
      vol.forEach((g, i) => A(g, { o: v ? 1 : 0, y: v ? 0 : 10 }, v ? stagger(i, 200, 250) : 0))
      A(tl, { o: v ? 1 : 0 }, v ? 800 : 0)
      A(win, { kx: v ? 1 : 0 }, v ? 1000 : 0, 400, LEFT)

      // step 3: what helped
      const b = step === 2
      A(bssHead, { o: b ? 1 : 0 }, b ? 200 : 0)
      bars.forEach((bar, i) => {
        A(bar.label, { o: b ? 1 : 0 }, b ? stagger(i, 250, 300) : 0)
        A(bar.rect, { kx: b ? 1 : 0 }, b ? stagger(i, 250, 350) : 0, 400, LEFT)
        A(bar.value, { o: b ? 1 : 0 }, b ? stagger(i, 250, 700) : 0)
      })

      // step 4: what the live site reads
      const l = step === 3
      A(liveHead, { o: l ? 1 : 0 }, l ? 200 : 0)
      lanes.forEach((g, i) => A(g, { o: l ? 1 : 0, x: l ? 0 : -12 }, l ? stagger(i, 150, 700) : 0))
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
