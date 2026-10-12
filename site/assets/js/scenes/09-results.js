// Scene 9 of the methodology deck: what the four epochs answered, the final live site, and where the quiet forecast stops.
// Numbers: README.md («Коротко», «Епоха 3»), docs/quiet/model.md section 10 (the same as meta.json quality) and
// docs/quiet/forecast.md. Quote: docs/HISTORY.md.
import { h, s, canvas, put, stagger } from '../how.js'

const ID = 'results'
const SRC = (t) => `<details class="how-src"><summary>Джерела</summary><p>${t}</p></details>`

const CSS = `
.scene-results text { font-size: 22px; fill: var(--body); }
.scene-results .num { font-family: var(--font-display); font-size: 34px; fill: var(--pink); }
.scene-results .word { font-size: 24px; font-weight: 600; fill: var(--ink); }
.scene-results .big { font-family: var(--font-display); font-size: 30px; fill: var(--ink); }
.scene-results .val { font-family: var(--font-display); font-size: 40px; fill: var(--ink); }
.scene-results .val.t { fill: var(--pink); }
.scene-results .head { font-weight: 600; fill: var(--ink); }
.scene-results .hint { font-size: 20px; }
.scene-results .soft { fill: var(--soft); }
.scene-results .ink { fill: var(--ink); }
.scene-results .card { fill: var(--card); stroke: var(--line); stroke-width: 2; }
.scene-results .hot { stroke: var(--pink); }
.scene-results .final { fill: var(--pink-soft); }
.scene-results .fin { font-size: 24px; fill: var(--ink); }
.scene-results .rule { stroke: var(--line); stroke-width: 2; }
.scene-results .track { fill: var(--line); }
.scene-results .devf { fill: var(--soft); }
.scene-results .pinkf { fill: var(--pink); }
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
// The final stage, the same words as in scene 12, in the three lines of its band after the bold «Фінал:».
const FINAL = ['живий сайт щогодини відповідає,', 'чи встигнеш переїхати на інший берег,', 'тобто чи буде тихо наступні 3 години']

// Three plain comparisons on the quiet-now hours: development hours (refit every week, as in scene 8), then test.
// «Низький» and the BSS: docs/quiet/model.md section 10, the same as meta.json quality. «Високий»: 174 of 354
// development hours, the count of scene 8 (site/data/dev_predictions.json); its test share is from docs/quiet/forecast.md.
const ROWS = [
  { lines: ['після «низького ризику»', 'атаки не було'], dev: 0.83, test: 0.83, f: pct,
    tip: '«низький ризик» це прогноз нижче 19.7%, модель казала його у 37% навчальних і 7% тестових годин' },
  { lines: ['після «високого ризику»', 'атака була'], dev: 0.49, test: 0.8, f: pct,
    tip: '«високий ризик» це прогноз від 30%, на навчальних даних атака була після 174 з 354 таких годин' },
  { lines: ['виграш над простим', 'правилом (BSS)'], hint: '0: не краще, 1: ідеально', dev: 0.094, test: 0.284, f: fix3,
    tip: '0.284 означає, що помилка ймовірностей на 28% менша, ніж у простого правила' },
]
const COL = [294, 466]  // left edges of the development and the test column
const BAR = 150         // a full track is 100%, or a BSS of 1
const ROW0 = 60
const ROWH = 112

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

// Hover texts, step by step: the facts behind each mark. The card zones sit low so the band below wins its own area.
const ZONES = [
  [
    { x: 86, y: 186, t: 'етап 1, ракетні удари: модель зловила 7 з 9, коли ті вже починались; обидва денні пропущено' },
    { x: 242, y: 186, t: 'етап 2, ночі: о 22:00 модель попередила про 2 з 7 ракетних ночей' },
    { x: 398, y: 186, t: 'етап 3, атака за 3 години: після «низького ризику» атаки не було у 83% випадків' },
    { x: 554, y: 186, t: 'етап 4, живий сайт: досить 10 каналів Telegram' },
    ...[86, 242, 398, 554].map((x) => ({ x, y: 324, t: 'фінал: прогноз етапу 3 на 10 каналах етапу 4, живий сайт оновлює його щогодини' })),
  ],
  ROWS.map((r, i) => ({ x: 320, y: ROW0 + i * ROWH + 56, t: `${r.lines.join(' ')}: навчальні дані ${r.f(r.dev)}, тестові ${r.f(r.test)}; ${r.tip}` })),
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
      note: '<p>Числа фінальної моделі на <b>спокійних годинах</b> (зараз ні тривоги, ні атаки): <b>навчальні</b> з 01.05 до 29.08, на них модель вчилась, '
        + 'і <b>тестові</b>, 6 тижнів з 29.08 до 10.10, відкриті один раз. '
        + '<b>Виграш над простим правилом</b> (BSS): наскільки ймовірності точніші, ніж правило «щогодини казати ту саму частку атак, відому на початок тижня»: 0 не краще, 1 ідеально. '
        + 'Два тестові числа вищі, бо восени атак більше: неспокійних годин <span class="num">71%</span> проти <span class="num">31%</span> влітку.</p>'
        + SRC('docs/quiet/model.md, розділ 10 (те саме в meta.json, quality); «після високого ризику»: site/data/dev_predictions.json, 174 з 354, як у розділі 8, і docs/quiet/forecast.md (тестові дані); README.md, «Епоха 3»; фінальна модель: logit_signals.'),
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
    const svg = canvas(stage, 'Чотири етапи проєкту і фінал, три порівняння навчальних і тестових даних, межі прогнозу')
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

    // Step 1: four epochs as cards, the quiet one (the finalist) outlined in pink, then the final stage as a band.
    EPOCHS.forEach((e, i) => {
      const x = 16 + i * 156
      const y = 16
      const big = s('text', { x: x + 20, y: y + 164, class: 'big', text: e.big })
      const card = s('g', {},
        s('rect', { x, y, width: 140, height: 232, rx: 16, class: i === 2 ? 'card hot' : 'card' }),
        s('text', { x: x + 20, y: y + 50, class: 'num', text: String(i + 1) }),
        s('g', { transform: `translate(${x + 102} ${y + 40})` },
          s('circle', { r: 22, class: e.mark === 'yes' ? 'pinkf' : 'hollow' }),
          s('path', { d: MARK[e.mark], class: e.mark === 'yes' ? 'wline' : 'sline' })),
        s('text', { x: x + 20, y: y + 92, class: 'word', text: e.word }),
        s('line', { x1: x + 20, x2: x + 120, y1: y + 112, y2: y + 112, class: 'rule' }),
        big,
        s('text', { x: x + 20, y: y + 198, class: 'soft', text: e.small }))
      add(card, (st) => (st === 0 ? {} : { o: 0, y: st < 0 ? 24 : -16 }),
        { delay: (st) => (st === 0 ? stagger(i, 90) : stagger(i, 40)) })
      add(big, (st) => (st === 0 ? {} : { o: 0, k: 0.6 }), { delay: (st) => (st === 0 ? 300 + stagger(i, 90) : 0) })
    })
    add(s('g', {},
      s('rect', { x: 16, y: 262, width: 608, height: 124, rx: 16, class: 'final' }),
      s('g', { transform: 'translate(60 324)' }, s('circle', { r: 22, class: 'pinkf' }), s('path', { d: MARK.yes, class: 'wline' })),
      ...FINAL.map((t, j) => s('text', { x: 100, y: 298 + j * 30, class: 'fin' }, j ? null : s('tspan', { class: 'head', text: 'Фінал: ' }), t))),
    (st) => (st === 0 ? {} : { o: 0, y: st < 0 ? 24 : -16 }), { delay: (st) => (st === 0 ? 480 : 160) })

    // Step 2: three comparisons, development and test side by side; each bar fills a track that ends at 100% (or 1).
    add(s('g', {},
      s('text', { x: 16, y: 40, class: 'soft', text: 'спокійні години' }),
      ...['навчальні', 'тестові'].map((t, j) => s('g', {},
        s('rect', { x: COL[j], y: 24, width: 18, height: 18, rx: 4, class: j ? 'pinkf' : 'devf' }),
        s('text', { x: COL[j] + 26, y: 40, class: 'head', text: t })))),
    only(1))
    ROWS.forEach((r, i) => {
      const y = ROW0 + i * ROWH
      const enter = (extra) => ({ delay: (st) => (st === 1 ? i * 160 + extra : 0) })
      add(s('g', {},
        s('line', { x1: 16, x2: 624, y1: y, y2: y, class: 'rule' }),
        ...r.lines.map((t, j) => s('text', { x: 16, y: y + 44 + j * 28, class: 'ink', text: t })),
        r.hint ? s('text', { x: 16, y: y + 98, class: 'soft hint', text: r.hint }) : null,
        ...COL.map((x) => s('rect', { x, y: y + 64, width: BAR, height: 14, rx: 7, class: 'track' }))),
      only(1), enter(0))
      ;[r.dev, r.test].forEach((v, j) => {
        add(s('rect', { x: COL[j], y: y + 64, width: Math.max(v * BAR, 14), height: 14, rx: 7, class: j ? 'pinkf' : 'devf' }),
          (st) => (st === 1 ? {} : { o: 0, kx: 0 }), { ...enter(100 + j * 200), dur: 400, origin: 'left' })
        add(s('text', { x: COL[j], y: y + 52, class: j ? 'val t' : 'val', text: r.f(v) }), only(1, 8), enter(100 + j * 200))
      })
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
