// Scene 4 of the methodology deck: bronze, silver, gold. A real post becomes a silver row with available_at, and the hours
// become one gold row per hour t: features only from before t, the target after t.
// Sources: docs/data/PARSING.md 0.1 (bronze fields), data/bronze/telegram/truexakyiv.jsonl (the post), docs/data/silver/
// kyiv_threat_hourly.md (Час доступності), docs/data/gold/kyiv_quiet.md, README.md (Дані), docs/ARCHITECTURE.md.
import { h, s, canvas, put, stagger } from '../how.js'

const CSS = `
.scene-layers .ink { fill: var(--ink); }
.scene-layers .soft { fill: var(--soft); }
.scene-layers .pink { fill: var(--pink); }
.scene-layers .on-pink { fill: var(--card); }
.scene-layers .card { fill: var(--card); stroke: var(--line); stroke-width: 2; }
.scene-layers .fill-pink { fill: var(--pink); }
.scene-layers .fill-soft { fill: var(--pink-soft); }
.scene-layers .fill-line { fill: var(--line); }
.scene-layers .fill-ink { fill: var(--ink); }
`

// The real line of data/bronze/telegram/truexakyiv.jsonl for post 91762 (the text is trimmed, the views and url are left out).
const FIELDS = [
  ['channel', '"truexakyiv"'],
  ['post_id', '91762'],
  ['published_at', '"2026-10-07T00:14:55Z"'],
  ['text', '"Гучно!\\n\\nТруха..."'],
  ['edited', 'true'],
  ['fetched_at', '"2026-10-10T17:38:39Z"'],
]
const POST_MIN = 14 + 55 / 60 // 00:14:55 UTC, minutes into its hour
const GOLD_ROWS = 3909 // docs/data/gold/kyiv_quiet.md: 3909 rows, 70 columns
const SILVER_TABLES = 11 // README.md, Дані

const T = (x, y, text, cls = 'ink', size = 22, more = {}) =>
  s('text', { x, y, class: cls, 'font-size': size, ...more, text })

// Every node has a state per step; show(step) moves all of them, so any step works from any other, also backwards.
function director() {
  const tracks = []
  return {
    add(node, state, opts = {}) {
      tracks.push([node, state, opts])
      return node
    },
    apply(step, instant) {
      for (const [node, state, opts] of tracks) {
        const delay = typeof opts.delay === 'function' ? opts.delay(step) : opts.delay
        put(node, state(step), { ...opts, delay, instant })
      }
    },
  }
}

const CONTRACT = `- Кожна таблиця silver має колонку \`available_at\` (TIMESTAMP, UTC): коли рядок став відомим.
...
  - \`features(con, t_table)\`: ... повертає \`pyarrow.Table\` з \`t_utc\` і колонками gold свого класу, рівно рядок на кожен \`t_utc\`. Читає silver лише через ці view і бере лише те, що відомо до \`t_utc\`.
...
- Тест на витік: для випадкових t зібрати view з \`ASOF\` (усе, що відомо до t), порахувати \`features()\` і порівняти з розрахунком на повних даних.`

export default {
  id: 'layers',
  title: 'Бронза, срібло, золото',
  lead: 'Дані проходять три рівні: сирі пости, таблиці з часом, коли кожен рядок став відомим, і таблиця на питання, де рядок це момент рішення t.',
  steps: [
    {
      note: '<p>Bronze: джерела як є. Пост Telegram це рядок JSON з полями channel, post_id, published_at, text, edited, views, forwarded_from, url, fetched_at (<code>docs/data/PARSING.md</code>, розділ 0.1). Ось справжній рядок з <code>data/bronze/telegram/<wbr>truexakyiv.jsonl</code>: «Гучно!» о 00:14:55 UTC, тобто 03:14 за Києвом.</p>',
      prompts: [{
        title: 'Сирий формат bronze',
        text: '**Сирий формат:** `data/bronze/telegram/<channel>.jsonl`, один JSON на пост, `<channel>` точно як у `data-post`. Рядки не відсортовані: читати, прибирати дублі за `post_id` (лишати перший рядок) і сортувати.',
        source: 'docs/data/PARSING.md, розділ 0.1',
      }],
    },
    {
      note: `<p>Silver: ${SILVER_TABLES} таблиць, і в кожного рядка є <code>available_at</code>, момент, коли він став відомим (README, розділ Дані). Пости години стають рядком <code>kyiv_threat_hourly</code>: година 00:00 UTC 7 жовтня має мітку удару. Мітку години знають лише в її кінці, тому <code>available_at</code> це година плюс 1 год (<code>docs/data/silver/<wbr>kyiv_threat_hourly.md</code>, розділ Час доступності).</p>`,
      prompts: [{
        title: 'Час доступності',
        text: 'Мітка години h бачить пости лише до h+1 год, тож рядок години відомий з h+1 год: `available_at` = `hour_utc` + 1 год.',
        source: 'docs/data/silver/kyiv_threat_hourly.md',
      }],
    },
    {
      note: '<p>Gold: одна таблиця на питання, рядок на кожну годину t. Ознаки рахуються лише з годин, що закінчились до t, а ціль <code>y_busy_3h</code> з годин t, t + 1, t + 2: чи будуть дрони, ракетна загроза чи удар (<code>docs/data/gold/kyiv_quiet.md</code>).</p>',
      prompts: [{
        title: 'Звідки ознаки рядка t',
        text: 'Мітки і пости години відомі в її кінці, тож ознаки рядка t читають лише години, що закінчились до t; подію S4 лише з `available_at` < t, а її курс на Київ лише тоді, коли її останній пост раніший за t.',
        source: 'docs/data/gold/kyiv_quiet.md',
      }],
    },
    {
      note: `<p>Вікно зсувається на годину, і виходить наступний рядок. Так <code>kyiv_quiet</code> має <span class="num">${GOLD_ROWS}</span> рядків і 70 колонок, з 2026-04-30 21:00 UTC до 2026-10-10 17:00 UTC (<code>docs/data/gold/kyiv_quiet.md</code>). Правила для всіх таблиць записано в контракті silver і gold (<code>docs/ARCHITECTURE.md</code>).</p>`,
    },
  ],
  prompts: [{ title: 'Контракт silver і gold', text: CONTRACT, source: 'docs/ARCHITECTURE.md, розділ Контракт silver і gold' }],

  mount(stage) {
    stage.append(h('style', { text: CSS }))
    const svg = canvas(stage, 'Пост з bronze стає рядком silver, а години стають рядками gold')
    svg.classList.add('scene-layers')
    const d = director()
    const add = (node) => svg.appendChild(node)
    const only = (from, to = from, hidden = { o: 0 }, shown = {}) => (k) => (k >= from && k <= to ? shown : hidden)

    // step 1: bronze, the raw post
    d.add(add(s('g', {},
      T(40, 50, 'bronze', 'pink', 26, { 'font-weight': 700 }),
      T(600, 50, 'data/bronze/telegram', 'soft', 22, { 'text-anchor': 'end' }),
      s('rect', { x: 40, y: 72, width: 560, height: 292, rx: 16, class: 'card' }),
      s('rect', { x: 52, y: 174, width: 536, height: 40, rx: 8, class: 'fill-soft' }),
      FIELDS.flatMap(([key, val], i) => [T(64, 112 + i * 44, key, 'soft'), T(240, 112 + i * 44, val, 'ink')]))),
    (k) => (k < 0 ? { o: 0, y: 24 } : k === 0 ? {} : { o: 0, y: -40 }), { dur: 400 })

    // step 2: silver, the hour row and its available_at on a time axis 23:00..02:00 UTC
    const HX = (hoursFrom23) => 64 + (hoursFrom23 * 512) / 3
    d.add(add(s('g', {},
      T(40, 50, 'silver', 'pink', 26, { 'font-weight': 700 }),
      T(600, 50, 'kyiv_threat_hourly', 'soft', 22, { 'text-anchor': 'end' }),
      T(64, 108, 'hour_utc', 'soft'), T(250, 108, 'missile_strike', 'soft'), T(448, 108, 'available_at', 'soft'),
      s('rect', { x: 40, y: 124, width: 560, height: 60, rx: 12, class: 'card' }),
      T(64, 163, '00:00', 'ink', 24, { 'font-weight': 600 }),
      T(250, 163, 'true', 'ink', 24, { 'font-weight': 600 }),
      s('rect', { x: 64, y: 290, width: 512, height: 3, class: 'fill-ink' }),
      ['23:00', '00:00', '01:00', '02:00'].map((lab, i) =>
        T(HX(i), 324, lab, 'soft', 22, { 'text-anchor': i === 0 ? 'start' : i === 3 ? 'end' : 'middle' })))),
    (k) => (k < 1 ? { o: 0, y: 40 } : k === 1 ? {} : { o: 0, y: -40 }), { dur: 400 })
    d.add(add(s('rect', { x: HX(1), y: 256, width: HX(2) - HX(1), height: 34, class: 'fill-soft' })),
      only(1, 1, { o: 0, kx: 0 }), { origin: 'left center', dur: 400, delay: (k) => (k === 1 ? 350 : 0) })
    const px = HX(1 + POST_MIN / 60)
    d.add(add(s('g', {},
      s('circle', { cx: px, cy: 273, r: 8, class: 'fill-pink' }),
      T(px, 244, 'пост 00:14:55', 'ink', 22, { 'text-anchor': 'middle' }))),
    only(1, 1, { o: 0, y: -10 }), { delay: (k) => (k === 1 ? 200 : 0) })
    d.add(add(s('g', {},
      s('rect', { x: HX(2) - 2, y: 246, width: 4, height: 56, rx: 2, class: 'fill-pink' }),
      T(HX(2) + 10, 244, 'рядок відомий', 'pink', 22, { 'font-weight': 600 }),
      T(448, 163, '01:00', 'pink', 24, { 'font-weight': 700 }))),
    only(1, 1, { o: 0, y: -8 }), { delay: (k) => (k === 1 ? 800 : 0) })

    // steps 3 and 4: gold, a strip of hours with the window [past | t | 3 hours], then the rows
    const head = (text, from, to) => d.add(add(T(600, 50, text, 'soft', 22, { 'text-anchor': 'end' })), only(from, to))
    d.add(add(T(40, 50, 'gold', 'pink', 26, { 'font-weight': 700 })), only(2, 3, { o: 0, y: 30 }), { delay: 100 })
    head('kyiv_quiet', 2, 2)
    head(`kyiv_quiet, ${GOLD_ROWS} рядків`, 3, 3)
    const CELL = 56
    const cx = (i) => 40 + i * CELL
    for (let i = 0; i < 10; i++) {
      const cell = (cls) => add(s('rect', { x: cx(i), y: 100, width: CELL - 4, height: 48, rx: 6, class: cls }))
      d.add(cell('fill-line'), only(2, 3), { delay: (k) => (k === 2 ? stagger(i, 30) : 0) })
      // t sits before cell 6 on step 3 and before cell 7 on step 4
      d.add(cell('fill-soft'), (k) => (k === 2 ? (i < 6 ? {} : { o: 0 }) : k === 3 ? (i < 7 ? {} : { o: 0 }) : { o: 0 }),
        { delay: (k) => (k >= 2 ? stagger(i, 40, 300) : 0) })
      d.add(cell('fill-pink'), (k) => (k === 2 ? (i >= 6 && i < 9 ? {} : { o: 0 }) : k === 3 ? (i >= 7 ? {} : { o: 0 }) : { o: 0 }),
        { delay: (k) => (k >= 2 ? stagger(i, 40, 300) : 0) })
    }
    d.add(add(T(206, 131, 'ознаки', 'ink', 22, { 'text-anchor': 'middle' })),
      (k) => (k === 2 ? {} : k === 3 ? { x: CELL / 2 } : { o: 0 }), { delay: (k) => (k === 2 ? 600 : 0) })
    d.add(add(T(458, 131, 'ціль', 'on-pink', 22, { 'text-anchor': 'middle', 'font-weight': 700 })),
      (k) => (k === 2 ? {} : k === 3 ? { x: CELL } : { o: 0 }), { delay: (k) => (k === 2 ? 600 : 0) })
    d.add(add(s('g', {},
      s('rect', { x: cx(6) - 4, y: 88, width: 4, height: 72, rx: 2, class: 'fill-ink' }),
      T(cx(6) - 2, 80, 't', 'ink', 28, { 'text-anchor': 'middle', 'font-weight': 700 }))),
    (k) => (k === 2 ? {} : k === 3 ? { x: CELL } : { o: 0, y: -10 }), { delay: (k) => (k === 2 ? 450 : 0) })

    // one gold row per t: [t | features before t | target after t]; on step 4 a new row comes and the rest stack below
    const row = (y, tLabel) => [
      s('g', {}, s('rect', { x: 40, y, width: 76, height: 52, rx: 8, class: 'card' }),
        T(78, y + 34, tLabel, 'ink', 22, { 'text-anchor': 'middle', 'font-weight': 700 })),
      s('g', {}, s('rect', { x: 122, y, width: 318, height: 52, rx: 8, class: 'fill-soft' }),
        T(281, y + 34, 'ознаки: лише до t', 'ink', 22, { 'text-anchor': 'middle' })),
      s('g', {}, s('rect', { x: 446, y, width: 154, height: 52, rx: 8, class: 'fill-pink' }),
        T(523, y + 34, 'y_busy_3h', 'on-pink', 22, { 'text-anchor': 'middle', 'font-weight': 700 })),
    ]
    row(210, 't').forEach((part, j) => d.add(add(part),
      (k) => (k < 2 ? { o: 0, y: -110 } : k === 2 ? {} : { o: 0.5, y: 64 }),
      { dur: 400, delay: (k) => (k === 2 ? stagger(j, 120, 750) : 0) }))
    row(210, 't + 1').forEach((part, j) => d.add(add(part),
      (k) => (k === 3 ? {} : { o: 0, y: -110 }),
      { dur: 400, delay: (k) => (k === 3 ? stagger(j, 120, 450) : 0) }))
    for (let j = 0; j < 4; j++) {
      d.add(add(s('rect', { x: 40, y: 340 + j * 12, width: 560, height: 4, rx: 2, class: 'fill-line' })),
        only(3, 3), { delay: (k) => (k === 3 ? stagger(j, 80, 900) : 0) })
    }

    d.apply(-1, true)
    svg.getBoundingClientRect()
    return {
      show(step, { instant } = {}) { d.apply(step, instant) },
      destroy() {},
    }
  },
}
