// Scene 10 of the methodology deck: the live pipeline behind this page, one station per step.
// Facts: src/airalerts/live/ (fetch.py, features.py, model.py), tests/test_live_features.py, docs/adr/0012-live-site.md,
// docs/adr/0013-retrain-cadence.md, deploy/systemd/kyianyn-routine-cycle.timer and kyianyn-routine-train.timer, README.md «Епоха 4»,
// docs/quiet/sources.md. The hours the model learned from are read from the live model.json at run time.
import { h, s, canvas, put, stagger } from '../how.js'

const ID = 'live'
const SRC = (t) => `<details class="how-src"><summary>Джерела</summary><p>${t}</p></details>`

const CSS = `
.scene-live text { font-size: 22px; fill: var(--body); }
.scene-live .word { font-size: 24px; font-weight: 600; fill: var(--ink); }
.scene-live .soft { fill: var(--soft); }
.scene-live .ink { fill: var(--ink); }
.scene-live .pinkt { fill: var(--pink); font-weight: 600; }
.scene-live .wt { fill: var(--card); font-weight: 600; }
.scene-live .card { fill: var(--card); stroke: var(--line); stroke-width: 2; }
.scene-live .hotr { fill: none; stroke: var(--pink); stroke-width: 3; }
.scene-live .rule { stroke: var(--line); stroke-width: 2; }
.scene-live .pinkf { fill: var(--pink); }
.scene-live .softf { fill: var(--pink-soft); }
.scene-live .hollow { fill: var(--card); stroke: var(--soft); stroke-width: 2; }
.scene-live .ring { fill: none; stroke: var(--pink); stroke-width: 3; }
.scene-live .dash { stroke: var(--pink); stroke-width: 3; stroke-dasharray: 8 8; }
.scene-live .pline, .scene-live .iline, .scene-live .xline { fill: none; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
.scene-live .pline { stroke: var(--pink); }
.scene-live .iline { stroke: var(--ink); }
.scene-live .xline { stroke: var(--pink); stroke-width: 5; }
.tip.scene-live { position: absolute; z-index: 2; max-width: 280px; padding: 6px 10px; border-radius: var(--r-small); background: var(--card);
  border: 1px solid var(--line); color: var(--ink); font-size: 14px; line-height: 1.35; pointer-events: none; }
.tip.scene-live[hidden] { display: none; }
`

// The serpentine of the pipeline: `at` is the step that reaches the station, `hot` the steps that talk about it.
const STATIONS = [
  { label: 'Telegram', cx: 90, cy: 120, at: 0, hot: [0, 1] },
  { label: 'Jev', cx: 320, cy: 120, at: 2, hot: [2] },
  { label: 'срібло', cx: 550, cy: 120, at: 2, hot: [2] },
  { label: 'ознаки', cx: 550, cy: 300, at: 3, hot: [3] },
  { label: 'модель', cx: 320, cy: 300, at: 4, hot: [4] },
  { label: 'сторінка', cx: 90, cy: 300, at: 1, hot: [1, 5] },
]
const LINKS = [
  { x: 165, y: 118.5, w: 80, h: 3, at: 2, origin: 'left', head: 'M237 112l8 8-8 8' },
  { x: 395, y: 118.5, w: 80, h: 3, at: 2, origin: 'left', head: 'M467 112l8 8-8 8' },
  { x: 548.5, y: 153, w: 3, h: 114, at: 3, origin: 'top', head: 'M542 259l8 8 8-8' },
  { x: 395, y: 298.5, w: 80, h: 3, at: 4, origin: 'right', head: 'M403 292l-8 8 8 8' },
  { x: 165, y: 298.5, w: 80, h: 3, at: 5, origin: 'right', head: 'M173 292l-8 8 8 8' },
]

const only = (k, dy = 10) => (st) => (st === k ? {} : { o: 0, y: st < k ? dy : -dy })

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
const hoursWord = (n) => {
  const a = n % 10
  const b = n % 100
  if (a === 1 && b !== 11) return 'година'
  if (a >= 2 && a <= 4 && (b < 12 || b > 14)) return 'години'
  return 'годин'
}
const doc = (x, y, cls) => s('g', {},
  s('rect', { x, y, width: 22, height: 28, rx: 4, class: cls }),
  s('path', { d: `M${x + 5} ${y + 10}h12M${x + 5} ${y + 18}h8`, class: cls === 'hollow' ? 'iline' : 'pline' }))

export default {
  id: ID,
  title: 'Як сторінка оновлюється сама',
  lead: 'Кожні 5 хвилин той самий шлях: від постів у Telegram до цієї сторінки.',
  steps: [
    {
      note: '<p>Кожні <span class="num">5</span> хвилин сервер читає <span class="num">10</span> каналів Telegram: 7 київських (КМВА, Кличко, монітори) і 6 моніторингових, 3 з них спільні; одинадцятий, єТривога, потрібен лише для тривоги (крок 2). '
        + 'Канали читаються по одному з паузою 1.5 с, і додаються лише пости, новіші за останній відомий.</p>'
        + SRC('src/airalerts/live/fetch.py (EVERY = 300 секунд; публічні сторінки t.me/s; eTryvoga); deploy/systemd/kyianyn-routine-cycle.timer; docs/adr/0012-live-site.md, «Рішення».'),
    },
    {
      note: '<p>Канал КМВА іде окремою гілкою: тривогу і відбій розпізнає простий шаблон тексту, без мовної моделі. '
        + 'Тому статус тривоги на сторінці свіжий кожні 5 хвилин і не чекає моделі. '
        + 'Канал єТривога лише підказує початок тривоги, коли КМВА опублікувала відбій без початку.</p>'
        + SRC('src/airalerts/live/fetch.py (regex для VA_Kyiv; підказка eTryvoga); docs/adr/0012-live-site.md, «Рішення»; README.md, «Епоха 4».'),
    },
    {
      note: '<p>Нові пости київських каналів читає класифікатор Jev (розділ 3) і ставить мітки «ракетний удар», «ракетна загроза», «дрони на Київ»; на вже бачений пост відповідь береться з кешу, тобто зі збережених відповідей. '
        + 'Пости, мітки й сигнали лягають у срібний шар (розділ 4): таблиці подій з часом. '
        + 'Цикл з перебудовою срібного шару триває близько хвилини (вимір 11.10).</p>'
        + SRC('src/airalerts/live/fetch.py; docs/adr/0012-live-site.md (silver; кеш відповідей Jev; вимір 2026-10-11).'),
    },
    {
      note: '<p>Зі срібного шару ознаки, тобто числа, з яких модель рахує прогноз, рахують ті самі функції, що будували золотий шар для дослідження (розділ 4). '
        + 'Тест перевіряє це на кожній минулій годині: кожна спільна колонка дорівнює золотому шару, і жодна не змінюється, якщо прибрати дані, що з\'явились пізніше.</p>'
        + SRC('src/airalerts/live/features.py; tests/test_live_features.py (порівняння з gold).'),
    },
    {
      note: '<p>Модель вчиться заново щотижня, у суботу о <span class="num">12:00</span> за Києвом, на всіх годинах, чиї 3 години вже минули: лише для них відомо, чи була атака. '
        + 'Частоту обрали правилом з картки, записаним до підрахунку: на навчальних даних виграш (BSS) щотижня <span class="num">0.094</span>, а в найкращої частоти, щогодини, <span class="num">0.098</span>, різниця менша за 0.01. '
        + 'Межі рівнів 19.7% і 30% лишаються з навчальних даних і заново не підбираються.</p>'
        + SRC('src/airalerts/live/model.py (CADENCE = "weekly"); deploy/systemd/kyianyn-routine-train.timer; docs/adr/0013-retrain-cadence.md; README.md, «Епоха 3».'),
      prompts: [{
        title: 'Як часто модель вчиться заново',
        text: 'найрідше перенавчання, чий BSS на розробці не нижчий за найкращий BSS на розробці мінус 0.01 (правило простоти проєкту: рідше означає менше запусків і менше місць для збою).',
        source: 'Записане рішення про частоту навчання',
      }],
    },
    {
      note: '<p>Наприкінці циклу сервер записує прогноз у файл, а ця сторінка його читає. '
        + 'Ймовірність змінюється раз на годину, бо модель перевіряли лише на прогнозах о повній годині; статус тривоги і нові хвилі дронів оновлюються кожні 5 хвилин. '
        + 'У першому плані цикл був раз на 10 хвилин, а живий зробили кожні 5.</p>'
        + SRC('docs/adr/0012-live-site.md, «Рішення» (картка); src/airalerts/live/fetch.py (EVERY = 300 секунд); docs/quiet/model.md, розділ 10; план на 10 хвилин: README.md, «Епоха 4».'),
    },
    {
      note: '<p>Погоду, політичні події, символічні дати й удари по Росії ми не читаємо. '
        + 'Додані до набору «годинник + сигнали», вони змінюють виграш (BSS) на навчальних даних від <span class="num">-0.014</span> до <span class="num">+0.003</span>, а модель на всіх джерелах без ударів по Росії навіть краща, ніж з ними (0.052 проти 0.030). '
        + 'Кожне зайве джерело це шум і ще один збирач, який треба тримати живим.</p>'
        + SRC('docs/quiet/sources.md.'),
    },
  ],
  prompts: [{
    title: 'Чому ймовірність щогодини',
    text: 'Ймовірність щогодини, бо модель перевірено лише на повних годинах; статус тривоги і хвилі дронів кожні 5 хв (README, епоха 4).',
    source: 'Записане рішення про живий сайт',
  }],

  mount(stage, data) {
    const svg = canvas(stage, 'Живий цикл: Telegram, Jev, срібло, ознаки, модель, сторінка')
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
    const pipe = add(s('g', {}), (st) => (st === 6 || st < 0 ? { o: 0 } : {}))
    const P = (node, at, opt) => { pipe.append(node); return add(node, at, opt) }
    const upto = (st) => Math.min(st, 5)

    // The 10 channels fan into Telegram (step 1); the dot nearest the bypass is the alert channel VA_Kyiv.
    const fan = s('g', {})
    const chans = [...Array(10)].map((_, j) => {
      fan.append(s('line', { x1: 24 + j * 28, y1: 44, x2: 90, y2: 87, class: 'rule' }))
      return s('circle', { cx: 24 + j * 28, cy: 36, r: 8, class: 'pinkf' })
    })
    P(fan, (st) => (st >= 0 ? {} : { o: 0 }), { delay: (st) => (st === 0 ? 500 : 0) })
    chans.forEach((c, j) => P(c, (st) => (st >= 0 ? {} : { o: 0, k: 0 }), { delay: (st) => (st === 0 ? stagger(j, 50) : 0) }))
    P(s('text', { x: 318, y: 44, class: 'ink', text: '10 каналів, кожні 5 хв' }), (st) => (st >= 0 ? {} : { o: 0, y: 10 }),
      { delay: (st) => (st === 0 ? 600 : 0) })
    P(s('circle', { cx: 80, cy: 36, r: 13, class: 'ring' }), (st) => (st === 1 ? {} : { o: 0, k: 1.6 }))

    // Links between the stations, drawn by growing from the side the data comes from.
    for (const l of LINKS) {
      const tall = l.h > l.w
      P(s('rect', { x: l.x, y: l.y, width: l.w, height: l.h, class: 'pinkf' }),
        (st) => (upto(st) >= l.at ? {} : tall ? { o: 0, ky: 0 } : { o: 0, kx: 0 }), { dur: 400, origin: l.origin })
      P(s('path', { d: l.head, class: 'pline' }), (st) => (upto(st) >= l.at ? {} : { o: 0 }),
        { delay: (st) => (st === l.at ? 300 : 0) })
    }
    // The alert branch: VA_Kyiv by regex straight to the page.
    P(s('g', {}, s('line', { x1: 90, x2: 90, y1: 153, y2: 259, class: 'dash' })),
      (st) => (upto(st) >= 1 ? {} : { o: 0, ky: 0 }), { dur: 400, origin: 'top' })
    P(s('path', { d: 'M82 259l8 8 8-8', class: 'pline' }), (st) => (upto(st) >= 1 ? {} : { o: 0 }), { delay: (st) => (st === 1 ? 300 : 0) })
    P(s('text', { x: 104, y: 216, class: 'pinkt', text: 'шаблон' }), (st) => (upto(st) >= 1 ? {} : { o: 0 }))

    for (const st0 of STATIONS) {
      const x = st0.cx - 75
      const y = st0.cy - 33
      P(s('g', {},
        s('rect', { x, y, width: 150, height: 66, rx: 16, class: 'card' }),
        s('text', { x: st0.cx, y: st0.cy + 8, 'text-anchor': 'middle', class: 'word', text: st0.label })),
      (st) => (st < 0 ? { o: 0 } : upto(st) >= st0.at ? {} : { o: 0.3 }))
      P(s('rect', { x, y, width: 150, height: 66, rx: 16, class: 'hotr' }), (st) => (st0.hot.includes(st) ? {} : { o: 0 }))
    }
    // The alert status lands on the page as a pink badge and stays there.
    P(s('circle', { cx: 90, cy: 262, r: 10, class: 'pinkf' }), (st) => (upto(st) >= 1 ? {} : { o: 0, y: -108 }),
      { delay: (st) => (st === 1 ? 300 : 0), dur: 400 })

    // Step 3: a new post goes into Jev and comes out as a label; old posts go to the cache.
    P(s('rect', { x: 262, y: 176, width: 116, height: 54, rx: 8, class: 'card' }), only(2))
    P(s('text', { x: 334, y: 211, class: 'ink', text: 'кеш' }), only(2))
    P(doc(252, 106, 'softf'), (st) => (st === 2 ? {} : { o: 0, x: st < 2 ? -77 : 0 }), { delay: (st) => (st === 2 ? 100 : 0), dur: 400 })
    P(doc(272, 189, 'hollow'), (st) => (st === 2 ? {} : { o: 0, x: st < 2 ? -97 : 0, y: st < 2 ? -85 : 0 }),
      { delay: (st) => (st === 2 ? 250 : 0), dur: 400 })
    P(doc(300, 189, 'hollow'), (st) => (st === 2 ? {} : { o: 0, x: st < 2 ? -125 : 0, y: st < 2 ? -85 : 0 }),
      { delay: (st) => (st === 2 ? 350 : 0), dur: 400 })
    P(s('g', {},
      s('rect', { x: 410, y: 76, width: 50, height: 28, rx: 14, class: 'pinkf' }),
      s('text', { x: 435, y: 97, 'text-anchor': 'middle', class: 'wt', text: 'так' })),
    (st) => (st === 2 ? {} : { o: 0, k: 0.4 }), { delay: (st) => (st === 2 ? 550 : 0) })
    P(s('text', { x: 320, y: 252, 'text-anchor': 'middle', class: 'soft', text: 'нові → Jev, старі → кеш' }), only(2),
      { delay: (st) => (st === 2 ? 600 : 0) })

    // Step 4: live features against gold, hour by hour, every pair equal.
    P(s('text', { x: 290, y: 212, 'text-anchor': 'end', class: 'ink', text: 'наживо' }), only(3))
    P(s('text', { x: 460, y: 212, class: 'ink', text: 'золото' }), only(3))
    ;[172, 194, 216, 238].forEach((y, i) => {
      const d = (extra) => ({ delay: (st) => (st === 3 ? stagger(i, 120, extra) : 0) })
      P(s('rect', { x: 300, y, width: 50, height: 16, rx: 4, class: 'softf' }), (st) => (st === 3 ? {} : { o: 0, kx: 0 }),
        { ...d(0), origin: 'left' })
      P(s('text', { x: 375, y: y + 14, 'text-anchor': 'middle', class: 'pinkt', text: '=' }), (st) => (st === 3 ? {} : { o: 0, k: 0.3 }), d(150))
      P(s('rect', { x: 400, y, width: 50, height: 16, rx: 4, class: 'softf' }), (st) => (st === 3 ? {} : { o: 0, kx: 0 }),
        { ...d(250), origin: 'left' })
    })

    // Step 5: the week between two retrains, 7 rows of 24 hours ending at Saturday 12:00 (deploy/systemd/kyianyn-routine-train.timer).
    // The last 3 hours are still unknown (known_by of src/airalerts/evaluation/split.py: t + 3 h <= the retrain moment),
    // so the retrain learns from all the rest; the count under the model box is every hour it learned from.
    P(s('text', { x: 190, y: 182, class: 'ink', text: 'щотижня, субота 12:00' }), only(4))
    for (let i = 0; i < 7; i++) {
      for (let j = 0; j < 24; j++) {
        const late = i === 6 && j >= 21
        P(s('rect', { x: 190 + j * 13.5, y: 194 + i * 9, width: 9, height: 6, rx: 2, class: late ? 'hollow' : 'pinkf' }),
          (st) => (st === 4 ? {} : { o: 0, ky: 0.2 }),
          { delay: (st) => (st === 4 ? (late ? 450 : stagger(i, 40)) : 0), origin: 'bottom' })
      }
    }
    P(s('text', { x: 517, y: 256, class: 'pinkt', text: '?' }), only(4), { delay: (st) => (st === 4 ? 650 : 0) })
    const rows = Number(data?.model?.rows ?? data?.now?.model?.rows)
    if (Number.isFinite(rows) && rows > 0) {
      P(s('text', { x: 320, y: 368, 'text-anchor': 'middle', class: 'soft', text: `${rows} ${hoursWord(rows)} у навчанні` }), only(4),
        { delay: (st) => (st === 4 ? 700 : 0) })
    }

    // Step 6: within one hour the probability moves once, the alert status and drone waves every 5 minutes.
    P(s('text', { x: 200, y: 177, class: 'ink', text: 'ймовірність' }), only(5))
    P(s('line', { x1: 200, x2: 520, y1: 196, y2: 196, class: 'rule' }), only(5))
    P(s('rect', { x: 200, y: 186, width: 6, height: 20, rx: 2, class: 'pinkf' }), (st) => (st === 5 ? {} : { o: 0, k: 0.3 }),
      { delay: (st) => (st === 5 ? 200 : 0) })
    P(s('text', { x: 200, y: 226, class: 'ink', text: 'тривога і хвилі дронів' }), only(5))
    P(s('line', { x1: 200, x2: 520, y1: 244, y2: 244, class: 'rule' }), only(5))
    for (let j = 0; j < 12; j++) {
      P(s('rect', { x: 200 + j * (320 / 12), y: 234, width: 6, height: 20, rx: 2, class: 'pinkf' }),
        (st) => (st === 5 ? {} : { o: 0, k: 0.3 }), { delay: (st) => (st === 5 ? stagger(j, 50, 300) : 0) })
    }

    // Step 7: the sources we do not parse bounce off.
    const ICONS = [
      { cx: 140, label: 'погода', d: 'M-34 20h62a20 20 0 0 0 2-40a28 28 0 0 0-54-6a20 20 0 0 0-10 46z' },
      { cx: 320, label: 'політика', d: 'M-22 40V-40M-22-34h44l-10 14 10 14h-44' },
      { cx: 500, label: 'удари по РФ', d: 'M0-34a34 34 0 1 0 0.1 0zM0-18a18 18 0 1 0 0.1 0zM0-46v14M0 32v14M-46 0h14M32 0h14' },
    ]
    ICONS.forEach((ic, j) => {
      add(s('g', {},
        s('g', { transform: `translate(${ic.cx} 150)` }, s('path', { d: ic.d, class: 'iline' })),
        s('text', { x: ic.cx, y: 236, 'text-anchor': 'middle', class: 'ink', text: ic.label })),
      only(6), { delay: (st) => (st === 6 ? stagger(j, 120) : 0) })
      add(s('g', {}, s('g', { transform: `translate(${ic.cx} 150)` }, s('path', { d: 'M-44-44L44 44M44-44L-44 44', class: 'xline' }))),
        (st) => (st === 6 ? {} : { o: 0, k: 0.3 }), { delay: (st) => (st === 6 ? 450 + stagger(j, 120) : 0) })
    })
    add(s('text', { x: 320, y: 312, 'text-anchor': 'middle', class: 'ink', text: 'додають від -0.014 до +0.003' }), only(6),
      { delay: (st) => (st === 6 ? 800 : 0) })
    add(s('text', { x: 320, y: 346, 'text-anchor': 'middle', class: 'soft', text: 'виграш (BSS) на навчальних даних' }), only(6),
      { delay: (st) => (st === 6 ? 850 : 0) })

    // Hover texts: what each station does, and the facts of this step.
    const STOP = {
      Telegram: '10 каналів Telegram кожні 5 хвилин, по одному з паузою 1.5 с',
      Jev: 'класифікатор Jev ставить мітки новим постам, відповіді на старі беруться з кешу',
      'срібло': 'срібний шар: пости, мітки й сигнали, таблиці подій з часом',
      'ознаки': 'ознаки рахують ті самі функції, що будували золотий шар',
      'модель': Number.isFinite(rows) && rows > 0 ? `вчиться заново щотижня, у суботу о 12:00; зараз ${rows} ${hoursWord(rows)} у навчанні`
        : 'вчиться заново щотижня, у суботу о 12:00',
      'сторінка': 'ймовірність раз на годину, тривога і хвилі дронів кожні 5 хвилин',
    }
    const OFF = [
      { x: 140, y: 170, t: 'погода: не читаємо' },
      { x: 320, y: 170, t: 'політичні події і символічні дати: не читаємо' },
      { x: 500, y: 170, t: 'удари по Росії: не читаємо, модель без них навіть краща (0.052 проти 0.030)' },
      { x: 320, y: 330, t: 'додані до набору «годинник + сигнали», ці джерела змінюють виграш (BSS) на навчальних даних від -0.014 до +0.003' },
    ]
    const zonesAt = (k) => (k === 6 ? OFF : k < 0 ? [] : [
      ...(k === 0 ? [{ x: 150, y: 40, t: '10 каналів: 7 київських і 6 моніторингових, 3 з них спільні' }] : []),
      ...(k >= 1 ? [{ x: 120, y: 210, t: 'канал КМВА: тривогу і відбій розпізнає шаблон тексту, без мовної моделі' }] : []),
      ...STATIONS.filter((st0) => upto(k) >= st0.at).map((st0) => ({ x: st0.cx, y: st0.cy, t: STOP[st0.label] })),
    ])
    const tip = tips(stage, svg, zonesAt)
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
