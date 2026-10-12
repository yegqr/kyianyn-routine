// Scene 9 of the methodology deck: what the four epochs answered and where the quiet forecast stops.
// Numbers: README.md («Коротко», «Епоха 3») and docs/quiet/model.md, section 10. Quote: docs/HISTORY.md.
import { h, s, canvas, put, stagger } from '../how.js'

const ID = 'results'
const SRC = (t) => `<details class="how-src"><summary>Джерела</summary><p>${t}</p></details>`

const CSS = `
.scene-results text { font-size: 22px; fill: var(--body); }
.scene-results .num { font-family: var(--font-display); font-size: 34px; fill: var(--pink); }
.scene-results .word { font-size: 24px; font-weight: 600; fill: var(--ink); }
.scene-results .big { font-family: var(--font-display); font-size: 30px; fill: var(--ink); }
.scene-results .soft { fill: var(--soft); }
.scene-results .ink { fill: var(--ink); }
.scene-results .pinkt { fill: var(--pink); font-weight: 600; }
.scene-results .card { fill: var(--card); stroke: var(--line); stroke-width: 2; }
.scene-results .hot { stroke: var(--pink); }
.scene-results .rule { stroke: var(--line); stroke-width: 2; }
.scene-results .seg { fill: var(--pink-soft); }
.scene-results .dev { fill: var(--card); stroke: var(--soft); stroke-width: 3; }
.scene-results .test, .scene-results .pinkf { fill: var(--pink); }
.scene-results .hollow { fill: var(--card); stroke: var(--soft); stroke-width: 2; }
.scene-results .wline, .scene-results .sline, .scene-results .iline { fill: none; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
.scene-results .wline { stroke: var(--card); }
.scene-results .sline { stroke: var(--soft); }
.scene-results .iline { stroke: var(--ink); }
.tip.scene-results { position: absolute; z-index: 2; max-width: 280px; padding: 6px 10px; border-radius: var(--r-small); background: var(--card);
  border: 1px solid var(--line); color: var(--ink); font-size: 14px; line-height: 1.35; pointer-events: none; }
.tip.scene-results[hidden] { display: none; }
`

const pct = (v) => `${Math.round(v * 100)}%`
const fix3 = (v) => v.toFixed(3)

// README.md, «Коротко»: the honest answer of each epoch in one number.
const EPOCHS = [
  { word: 'Удари', big: '7 з 9', small: 'ударів', mark: 'part' },
  { word: 'Ночі', big: '2 з 7', small: 'ночей', mark: 'no' },
  { word: 'Спокій', big: '83%', small: 'збувся', mark: 'yes' },
  { word: 'Джерела', big: '10', small: 'каналів', mark: 'yes' },
]
const MARK = { yes: 'M-10 1l6 6 13-13', no: 'M-8-8L8 8M8-8L-8 8', part: 'M-11 2c4-7 7-7 11-2s7 5 11-2' }

// docs/quiet/model.md section 10 and README.md «Епоха 3», quiet-now hours: development, then test.
// The «високий ризик» row is from docs/quiet/forecast.md, where the forecast is refit every hour.
const ROWS = [
  { label: 'виграш над правилом (BSS)', dev: 0.094, test: 0.284, f: fix3 },
  { label: 'розрізнення атак (ROC AUC)', dev: 0.684, test: 0.749, f: fix3 },
  { label: 'каже «низький ризик»', dev: 0.37, test: 0.07, f: pct },
  { label: 'після «низького» атаки не було', dev: 0.83, test: 0.83, f: pct },
  { label: 'після «високого» атака була', dev: 0.5, test: 0.8, f: pct },
]

const X0 = 40
const X1 = 600
const xs = (v) => X0 + v * (X1 - X0)
const only = (k, dy = 12) => (st) => (st === k ? {} : { o: 0, y: st < k ? dy : -dy })

// Hover or tap on the stage: one short line with the facts behind the nearest mark of this step.
function tips(stage, svg, zonesAt) {
  const tip = h('div', { class: `tip scene-${ID}`, role: 'tooltip', hidden: true })
  stage.append(tip)
  let cur = -1
  const move = (e) => {
    const b = svg.getBoundingClientRect(), sb = stage.getBoundingClientRect()
    const ux = ((e.clientX - b.left) * 640) / b.width, uy = ((e.clientY - b.top) * 400) / b.height
    let best = null, bd = Infinity
    for (const z of zonesAt(cur)) { const d = (z.x - ux) ** 2 + (z.y - uy) ** 2; if (d < bd) { bd = d; best = z } }
    tip.hidden = !best
    if (!best) return
    tip.textContent = best.t
    tip.style.left = `${Math.max(4, Math.min(e.clientX - sb.left + 14, sb.width - tip.offsetWidth - 4))}px`
    tip.style.top = `${Math.max(4, Math.min(e.clientY - sb.top + 14, sb.height - tip.offsetHeight - 4))}px`
  }
  svg.addEventListener('pointermove', move)
  svg.addEventListener('pointerdown', move)
  svg.addEventListener('pointerleave', () => { tip.hidden = true })
  return { set(k) { cur = k; tip.hidden = true } }
}

// Hover texts, step by step: the facts behind each mark.
const ZONES = [
  [
    { x: 86, y: 195, t: 'етап 1, ракетні удари: модель зловила 7 з 9, коли ті вже починались; обидва денні пропущено' },
    { x: 242, y: 195, t: 'етап 2, ночі: о 22:00 модель попередила про 2 з 7 ракетних ночей' },
    { x: 398, y: 195, t: 'етап 3, атака за 3 години: після «низького ризику» атаки не було у 83% випадків' },
    { x: 554, y: 195, t: 'етап 4, живий сайт: досить 10 каналів Telegram' },
  ],
  ROWS.map((r, i) => ({ x: 320, y: 106 + i * 62, t: `${r.label}: навчальні дані ${r.f(r.dev)}, тестові ${r.f(r.test)}` })),
  [
    { x: 164, y: 106, t: 'після «низького ризику» приблизно 1 шанс з 6, що буде атака' },
    { x: 476, y: 106, t: '«високий ризик» у годинах перед ракетним ударом: 58% і 100%, перед атакою лише дронів: 54% і 86% (навчальні і тестові дані)' },
    { x: 164, y: 296, t: 'мітка дронів правильна приблизно у 80% годин' },
    { x: 476, y: 296, t: 'схему рівнів описали вже після відкриття тестових даних, межі взято з навчальних' },
  ],
]

export default {
  id: ID,
  title: 'Що вийшло і де межа',
  lead: 'Чотири етапи, чотири питання: кожну відповідь перевірено на тестових даних (з 29.08, відкладені до кінця), і в прогнозу є межі.',
  steps: [
    {
      note: '<p><b>Удари:</b> нічні ракетні удари модель ловить, коли ті вже починаються (<span class="num">7 з 9</span>), а обидва денні пропустила. '
        + '<b>Ночі:</b> о 22:00 ракетну ніч не передбачити, модель попередила про <span class="num">2 з 7</span> таких ночей. '
        + '<b>Спокій:</b> після «низького ризику» атаки не було у <span class="num">83%</span> випадків; <b>джерела:</b> для живого сайту досить <span class="num">10</span> каналів Telegram.</p>'
        + SRC('README.md, «Коротко» і «Епоха 4»; питання етапів: docs/HISTORY.md.'),
    },
    {
      note: '<p>Фінальна модель (логістична регресія на 7 сигналах) на спокійних годинах, коли не було ні тривоги, ні атаки. '
        + 'Виграш над простим правилом (BSS): <span class="num">0.094</span> на навчальних даних і <span class="num">0.284</span> на тестових; як добре прогноз відрізняє години з атакою від спокійних (ROC AUC): <span class="num">0.684</span> і <span class="num">0.749</span>, де 0.5 це монетка. '
        + 'Після «високого ризику» атака була у 50% і 80% годин; тут модель вчилась заново щогодини, а 49% у розділі 8 пораховано на тижневих перевірках.</p>'
        + SRC('docs/quiet/model.md, розділ 10; docs/quiet/forecast.md, рядок «високий ризик» (прогноз перенавчали щогодини); README.md, «Епоха 3»; фінальна модель: logit_signals.'),
    },
    {
      note: '<p>Спокою не гарантує ніщо: навіть після «низького ризику» приблизно <span class="num">1</span> шанс з <span class="num">6</span>, що буде атака. '
        + 'Масовану ракетну атаку модель майже не відрізняє від дронів: у годинах перед ракетним ударом «високий ризик» стояв у 58% і 100% (навчальні і тестові дані), перед атакою лише дронів у 54% і 86%. '
        + 'Мітка дронів правильна приблизно у 80% годин, а схему рівнів описали вже після відкриття тестових даних, хоча межі взято з навчальних.</p>'
        + SRC('docs/quiet/model.md, розділ 10, «Межі»; docs/quiet/forecast.md; README.md, «Епоха 3».'),
    },
  ],
  prompts: [{
    title: 'Питання користувача, що відкривали новий етап',
    text: '2026-10-11 | Нове питання: о 22:00 чи спати в коридорі; перебудувати дані, багато моделей; дозволено scikit-learn і Workflow ...\n'
      + '2026-10-11 | Спершу задокументувати, потім питання «чи будуть 3 години тихими», дрони враховано, тим самим процесом\n'
      + '2026-10-11 | Живий продукт на сайті, прогноз оновлюється приблизно кожні 10 хвилин, парсити лише потрібні джерела',
    source: 'Рішення користувача 11.10, з історії проєкту',
  }],

  mount(stage) {
    const svg = canvas(stage, 'Чотири етапи проєкту, якість фінальної моделі на навчальних і тестових даних, межі прогнозу')
    svg.classList.add(`scene-${ID}`)
    stage.append(h('style', { text: CSS }))
    const items = []
    const add = (node, at, opt = {}) => {
      if (!node.parentNode) svg.append(node)
      items.push({ node, at, opt })
      return node
    }
    const apply = (step, instant) => {
      for (const { node, at, opt } of items) {
        put(node, at(step), {
          delay: instant || !opt.delay ? 0 : opt.delay(step),
          dur: opt.dur || 320, origin: opt.origin || 'center', instant,
        })
      }
    }

    // Step 1: four epochs as cards, the quiet one (the finalist) outlined in pink.
    EPOCHS.forEach((e, i) => {
      const x = 16 + i * 156
      const y = 40
      const big = s('text', { x: x + 20, y: y + 182, class: 'big', text: e.big })
      const card = s('g', {},
        s('rect', { x, y, width: 140, height: 310, rx: 16, class: i === 2 ? 'card hot' : 'card' }),
        s('text', { x: x + 20, y: y + 54, class: 'num', text: String(i + 1) }),
        s('text', { x: x + 20, y: y + 96, class: 'word', text: e.word }),
        s('line', { x1: x + 20, x2: x + 120, y1: y + 120, y2: y + 120, class: 'rule' }),
        big,
        s('text', { x: x + 20, y: y + 216, class: 'soft', text: e.small }),
        s('g', { transform: `translate(${x + 42} ${y + 266})` },
          s('circle', { r: 22, class: e.mark === 'yes' ? 'pinkf' : 'hollow' }),
          s('path', { d: MARK[e.mark], class: e.mark === 'yes' ? 'wline' : 'sline' })))
      add(card, (st) => (st === 0 ? {} : { o: 0, y: st < 0 ? 24 : -16 }),
        { delay: (st) => (st === 0 ? stagger(i, 90) : stagger(i, 40)) })
      add(big, (st) => (st === 0 ? {} : { o: 0, k: 0.6 }), { delay: (st) => (st === 0 ? 300 + stagger(i, 90) : 0) })
    })

    // Step 2: each measure on one track; the test dot starts on the development dot and slides to its own value.
    add(s('g', {},
      s('circle', { cx: 50, cy: 30, r: 9, class: 'dev' }),
      s('text', { x: 68, y: 38, text: 'навчальні' }),
      s('circle', { cx: 210, cy: 30, r: 9, class: 'test' }),
      s('text', { x: 228, y: 38, text: 'тестові' }),
      s('text', { x: X1, y: 38, 'text-anchor': 'end', class: 'soft', text: 'спокійні години' }),
      ...[0, 0.5, 1].map((v) => s('text', { x: xs(v), y: 394, 'text-anchor': 'middle', class: 'soft', text: String(v) }))),
    only(1))
    ROWS.forEach((r, i) => {
      const ly = 80 + i * 62
      const ty = ly + 26
      const a = xs(r.dev)
      const b = xs(r.test)
      const up = r.test >= r.dev
      const base = i * 150
      const enter = (extra) => ({ delay: (st) => (st === 1 ? base + extra : 0) })
      add(s('text', { x: X0, y: ly, class: 'ink', text: r.label }), only(1), enter(0))
      add(s('g', {},
        s('line', { x1: X0, x2: X1, y1: ty, y2: ty, class: 'rule' }),
        ...[0, 0.5, 1].map((v) => s('line', { x1: xs(v), x2: xs(v), y1: ty - 7, y2: ty + 7, class: 'rule' }))),
      only(1), enter(0))
      add(s('rect', { x: Math.min(a, b), y: ty - 4, width: Math.max(Math.abs(b - a), 1), height: 8, rx: 4, class: 'seg' }),
        (st) => (st === 1 ? {} : { o: 0, kx: 0 }), { ...enter(260), dur: 400, origin: up ? 'left' : 'right' })
      add(s('circle', { cx: a, cy: ty, r: 9, class: 'dev' }), (st) => (st === 1 ? {} : { o: 0, k: 0.4 }), enter(100))
      add(s('circle', { cx: b, cy: ty, r: 9, class: 'test' }), (st) => (st === 1 ? {} : { o: 0, x: a - b }), { ...enter(260), dur: 400 })
      add(s('text', { x: up ? a - 16 : a + 16, y: ty + 8, 'text-anchor': up ? 'end' : 'start', class: 'soft', text: r.f(r.dev) }),
        only(1), enter(100))
      add(s('text', { x: up ? b + 16 : b - 16, y: ty + 8, 'text-anchor': up ? 'start' : 'end', class: 'pinkt', text: r.f(r.test) }),
        only(1), enter(560))
    })

    // Step 3: four limits, each a small picture.
    const PANELS = [[16, 20], [328, 20], [16, 210], [328, 210]]
    const panel = (j, ...kids) => {
      const [x, y] = PANELS[j]
      return add(s('g', {}, s('rect', { x, y, width: 296, height: 172, rx: 16, class: 'card' }), ...kids),
        only(2), { delay: (st) => (st === 2 ? stagger(j, 120) : 0) })
    }
    const dots = [0, 1, 2, 3, 4, 5].map((j) => s('circle', { cx: 56 + j * 42, cy: 88, r: 15, class: 'hollow' }))
    const hit = s('circle', { cx: 56 + 3 * 42, cy: 88, r: 15, class: 'pinkf' })
    panel(0, ...dots, hit, s('text', { x: 36, y: 158, class: 'ink', text: 'після «низького»: 1 з 6' }))
    add(hit, (st) => (st === 2 ? {} : { o: 0, k: 0 }), { delay: (st) => (st === 2 ? 700 : 0) })
    panel(1,
      s('g', { transform: 'translate(400 92)' }, s('path', { d: 'M-40-8h50l18 8-18 8h-50zM-40-8l-10-12M-40 8l-10 12', class: 'iline' })),
      s('text', { x: 472, y: 104, 'text-anchor': 'middle', class: 'big', text: '≈' }),
      s('g', { transform: 'translate(548 92)' }, s('path', { d: 'M34 0L-26-30L-14 0L-26 30Z', class: 'iline' })),
      s('text', { x: 348, y: 158, class: 'ink', text: 'ракети чи дрони?' }))
    const sq = [...Array(10)].map((_, j) => s('rect', {
      x: 38 + j * 26, y: 258, width: 20, height: 20, rx: 4, class: j === 4 || j === 8 ? 'hollow' : 'pinkf',
    }))
    panel(2, ...sq, s('text', { x: 36, y: 348, class: 'ink', text: 'мітка дронів ≈80%' }))
    sq.forEach((q, j) => add(q, (st) => (st === 2 ? {} : { o: 0, k: 0.3 }), { delay: (st) => (st === 2 ? 360 + j * 40 : 0) }))
    panel(3,
      s('g', { transform: 'translate(476 280)' },
        s('path', { d: 'M-56 0C-30-34 30-34 56 0C30 34-30 34-56 0Z', class: 'iline' }),
        s('circle', { r: 13, class: 'pinkf' }),
        s('path', { d: 'M-56 0C-30-16 30-16 56 0', class: 'iline' })),
      s('text', { x: 348, y: 348, class: 'ink', text: 'тестові не зовсім сліпі' }))

    const tip = tips(stage, svg, (k) => ZONES[k] || [])
    apply(-1, true)
    return {
      show(step, { instant = false } = {}) {
        if (!instant) svg.getBoundingClientRect()
        tip.set(step)
        apply(step, instant)
      },
      destroy() {},
    }
  },
}
