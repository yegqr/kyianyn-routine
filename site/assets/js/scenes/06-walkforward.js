// Scene 6 of the methodology deck: how we checked. A split by time (development, then a test opened once), 8 weekly
// walk-forward folds, rules written before scoring, 11 models and the finalist, and BSS of the finalist and the 7-day share.
// Sources: docs/adr/0008-time-split.md, docs/adr/0011-quiet-hours.md, README.md (Поділ і правила, Мірила, Епоха 3).
import { h, s, canvas, put, stagger } from '../how.js'

const CSS = `
.scene-walkforward .ink { fill: var(--ink); }
.scene-walkforward .soft { fill: var(--soft); }
.scene-walkforward .on-pink { fill: var(--card); }
.scene-walkforward .fill-pink { fill: var(--pink); }
.scene-walkforward .fill-soft { fill: var(--pink-soft); }
.scene-walkforward .fill-grey { fill: var(--soft); }
.scene-walkforward .fill-ink { fill: var(--ink); }
.scene-walkforward .chip { fill: var(--card); stroke: var(--pink); stroke-width: 2; }
.scene-walkforward .lock { fill: none; stroke: var(--card); stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }
`

// Days from 2026-05-01 00:00 Kyiv. The gold data ends 2026-10-10 17:00Z, 20:00 Kyiv (docs/data/gold/kyiv_quiet.md); the test
// starts 2026-08-29 12:00 Kyiv; 8 weekly folds start 2026-07-04 12:00 Kyiv (docs/adr/0008-time-split.md).
const END = 162 + 20 / 24
const SPLIT = 120.5
const FOLD0 = 64.5
const FOLDS = 8
const X = (day) => 40 + (day * 560) / END
// BSS on the hours «зараз тихо» (README.md, Епоха 3): the finalist logit_signals and naive_7d, the share over 7 days.
const BSS = [
  { group: 'розробка', model: 0.094, naive: -0.061 },
  { group: 'тест', model: 0.284, naive: 0.277 },
]
const MODELS = 11 // README.md, Епоха 3: 11 models in three modules
const RULES = ['до 6 варіантів на модель', 'простіша, якщо гірша < 0.01', 'поріг за правилом з розробки']

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

const RULES_0011 = `- **Правила, задані до оцінки будь-якої моделі:**
  - головна оцінка на годинах «зараз тихо»: тривоги немає, і в минулу годину не було жодної мітки;
  - «тихо» модель каже, коли p не вища за поріг; поріг найвищий, за якого серед годин розробки, названих тихими, справді тихих щонайменше 95%;
  - фіналіст: найкращий BSS на розробці на годинах «зараз тихо», а модель з меншою кількістю ознак, якщо вона гірша менш ніж на 0.01;
  - до 6 варіантів на модель, список до запуску;
  - тест рахується один раз (\`.venv/bin/python -I -m airalerts.quiet.score final\`).`

export default {
  id: 'walkforward',
  title: 'Як ми перевіряли',
  lead: 'Модель вчиться лише на минулому і прогнозує наступний тиждень, а останні 6 тижнів ми відкрили один раз, для фінальної оцінки.',
  steps: [
    {
      note: '<p>Дані ділимо за часом, а не випадково: інакше години однієї атаки потрапили б і в навчання, і в перевірку. Розробка: з 2026-05-01 до 2026-08-29 12:00 за Києвом, на ній вибирали все. Тест: останні 6 тижнів, його відкривали один раз на кожне питання (<code>docs/adr/0008-time-split.md</code>, README).</p>',
      prompts: [{
        title: 'Тест',
        text: '- **Тест:** усі години з 2026-08-29 12:00 за Києвом (09:00Z) до кінця міток, тобто останні 6 повних тижнів: 1014 рядків, 31 true, 9 атак. Тест відкриваємо один раз, для фінальної оцінки, і модель на ньому перенавчається щотижня на всьому, що відомо до початку тижня.',
        source: 'docs/adr/0008-time-split.md',
      }],
    },
    {
      note: `<p>Усередині розробки <span class="num">${FOLDS}</span> тижневих фолдів з 2026-07-04: модель вчиться на всьому минулому і прогнозує наступний тиждень, потім межа зсувається на тиждень. Так кожен прогноз зроблено на годинах, яких модель не бачила. Перший фолд вчиться на травні і червні (<code>docs/adr/0008-time-split.md</code>).</p>`,
      prompts: [{
        title: 'Розробка',
        text: '- **Розробка:** години, чия мітка відома до межі: 2890 рядків, 107 true, 26 атак. Ознаки, модель, поріг і розмір вікна навчання обираємо на 8 тижневих фолдах walk-forward з 2026-07-04 12:00 за Києвом. ...',
        source: 'docs/adr/0008-time-split.md',
      }],
    },
    {
      note: '<p>Правила вибору записали до першої оцінки: до 6 варіантів на модель зі списком до запуску; фіналіст з найкращим BSS на розробці, але простіша модель, якщо вона гірша менш ніж на 0.01; поріг за правилом з розробки (<code>docs/adr/0011-quiet-hours.md</code>). Так вибір не можна було підігнати під тест.</p>',
    },
    {
      note: `<p>Для питання про спокійні 3 години агенти запропонували <span class="num">${MODELS}</span> моделей у трьох модулях: baselines, linear, trees. За правилом фіналістом стала <code>logit_signals</code>: логістична регресія на 7 входах, година доби, давність атаки, сигнали про дрони (README, Епоха 3).</p>`,
    },
    {
      note: `<p>BSS показує, наскільки ймовірності точніші за сталу частку подій, відому на початок тижня: 0 той самий рівень, більше 0 краще. На годинах «зараз тихо» <code>logit_signals</code> має ${BSS[0].model} на розробці і ${BSS[1].model} на тесті, частка неспокійних вікон за 7 днів ${BSS[0].naive} і ${BSS[1].naive} (README, Епоха 3). На тесті неспокійних годин 71% проти 31% на розробці, і проста частка майже наздогнала модель.</p>`,
      prompts: [{
        title: 'Як читати BSS',
        text: '**Мірила простими словами.** BSS: наскільки ймовірності точніші за сталу частку подій, відому на початок тижня; 0 той самий рівень, більше 0 краще.',
        source: 'README.md',
      }],
    },
  ],
  prompts: [{ title: 'Правила до оцінки', text: RULES_0011, source: 'docs/adr/0011-quiet-hours.md' }],

  mount(stage) {
    stage.append(h('style', { text: CSS }))
    const svg = canvas(stage, 'Розробка і тест на осі часу, 8 тижневих фолдів, правила, 11 моделей і BSS фіналіста')
    svg.classList.add('scene-walkforward')
    const d = director()
    const add = (node) => svg.appendChild(node)
    const only = (from, to = from, hidden = { o: 0 }) => (k) => (k >= from && k <= to ? {} : hidden)

    // step 1: the split by time, the test is locked; mid stage on step 1, it moves up to make room for the next steps
    const xs = X(SPLIT)
    d.add(add(s('g', {},
      s('rect', { x: 40, y: 80, width: xs - 42, height: 40, rx: 8, class: 'fill-soft' }),
      s('rect', { x: xs + 2, y: 80, width: 600 - xs - 2, height: 40, rx: 8, class: 'fill-pink' }),
      T((40 + xs) / 2, 107, 'розробка', 'ink', 22, { 'text-anchor': 'middle' }),
      s('rect', { x: 496, y: 96, width: 16, height: 13, rx: 2, class: 'lock' }),
      s('path', { d: 'M499 96 v-4 a5 5 0 0 1 10 0 v4', class: 'lock' }),
      T(518, 108, 'тест', 'on-pink', 22, { 'font-weight': 700 }),
      T(40, 148, '01.05', 'soft'),
      T(xs, 148, '29.08', 'soft', 22, { 'text-anchor': 'middle' }),
      T(600, 148, '10.10', 'soft', 22, { 'text-anchor': 'end' }))),
    (k) => (k < 0 ? { o: 0, y: 122 } : k === 0 ? { y: 110 } : {}), { dur: 400 })

    // step 2: 8 folds, each learns on all the past and predicts the next week
    const x0 = X(FOLD0)
    d.add(add(T(x0, 148, '04.07', 'soft', 22, { 'text-anchor': 'middle' })), only(1, 1), { delay: (k) => (k === 1 ? 100 : 0) })
    for (let i = 0; i < FOLDS; i++) {
      const a = X(FOLD0 + 7 * i)
      const b = X(FOLD0 + 7 * (i + 1))
      const y = 172 + i * 22
      d.add(add(s('g', {},
        s('rect', { x: 40, y, width: a - 42, height: 14, rx: 4, class: 'fill-soft' }),
        s('rect', { x: a, y, width: b - a - 2, height: 14, rx: 4, class: 'fill-pink' }))),
      only(1, 1, { o: 0, x: -12 }), { delay: (k) => (k === 1 ? stagger(i, 110, 200) : 0) })
    }
    d.add(add(s('g', {},
      s('rect', { x: 40, y: 360, width: 18, height: 18, rx: 4, class: 'fill-soft' }), T(66, 376, 'вчиться на минулому'),
      s('rect', { x: 330, y: 360, width: 18, height: 18, rx: 4, class: 'fill-pink' }), T(356, 376, 'прогноз на тиждень'))),
    only(1, 1), { delay: (k) => (k === 1 ? 1100 : 0) })

    // step 3: the rules written before any score
    d.add(add(T(320, 180, 'записано до першої оцінки', 'soft', 22, { 'text-anchor': 'middle' })), only(2, 2))
    RULES.forEach((r, i) => {
      const y = 198 + i * 60
      d.add(add(s('g', {},
        s('rect', { x: 100, y, width: 440, height: 46, rx: 23, class: 'chip' }),
        T(320, y + 30, r, 'ink', 22, { 'text-anchor': 'middle' }))),
      only(2, 2, { o: 0, y: 12 }), { delay: (k) => (k === 2 ? stagger(i, 160, 200) : 0) })
    })

    // step 4: 11 models, one finalist by the rule
    const FIN = 5
    d.add(add(T(320, 200, `${MODELS} моделей, 3 модулі`, 'soft', 22, { 'text-anchor': 'middle' })), only(3, 3))
    for (let i = 0; i < MODELS; i++) {
      d.add(add(s('circle', { cx: 70 + i * 50, cy: 256, r: 14, class: 'fill-grey' })),
        (k) => (k === 3 ? { o: 0.45 } : { o: 0, k: 0.5 }), { delay: (k) => (k === 3 ? stagger(i, 50, 100) : 0) })
    }
    d.add(add(s('circle', { cx: 70 + FIN * 50, cy: 256, r: 14, class: 'fill-pink' })),
      (k) => (k === 3 ? { k: 1.5 } : { o: 0, k: 0.5 }), { delay: (k) => (k === 3 ? 900 : 0) })
    d.add(add(T(70 + FIN * 50, 312, 'logit_signals', 'ink', 22, { 'text-anchor': 'middle', 'font-weight': 700 })),
      only(3, 3, { o: 0, y: 8 }), { delay: (k) => (k === 3 ? 1100 : 0) })

    // step 5: BSS of the finalist and of the 7-day share, development and test
    const Z = 300
    const U = 900 // units per 1.0 of BSS
    d.add(add(s('g', {},
      s('rect', { x: 40, y: 180, width: 18, height: 18, rx: 4, class: 'fill-pink' }), T(66, 196, 'logit_signals'),
      s('rect', { x: 330, y: 180, width: 18, height: 18, rx: 4, class: 'fill-grey' }), T(356, 196, 'частка за 7 днів'),
      s('rect', { x: Z - 1, y: 212, width: 2, height: 152, class: 'fill-ink' }),
      T(Z, 388, '0', 'soft', 22, { 'text-anchor': 'middle' }),
      T(600, 388, 'BSS, «зараз тихо»', 'soft', 22, { 'text-anchor': 'end' }))),
    only(4, 4))
    BSS.forEach((b, gi) => {
      const y0 = 222 + gi * 82
      d.add(add(T(40, y0 + 32, b.group, 'ink', 22, { 'font-weight': 600 })), only(4, 4))
      ;[['model', 'fill-pink'], ['naive', 'fill-grey']].forEach(([key, cls], j) => {
        const v = b[key]
        const w = Math.abs(v) * U
        const y = y0 + j * 28
        const delay = (k) => (k === 4 ? stagger(gi * 2 + j, 160, 200) : 0)
        d.add(add(s('rect', { x: v >= 0 ? Z : Z - w, y, width: w, height: 22, rx: 4, class: cls })),
          only(4, 4, { o: 0, kx: 0 }), { origin: v >= 0 ? 'left center' : 'right center', dur: 400, delay })
        d.add(add(T(v >= 0 ? Z + w + 8 : Z - w - 8, y + 18, v.toFixed(3), 'ink', 22,
          { 'font-weight': 600, 'text-anchor': v >= 0 ? 'start' : 'end' })),
        only(4, 4), { delay: (k) => (k === 4 ? delay(k) + 300 : 0) })
      })
    })

    d.apply(-1, true)
    svg.getBoundingClientRect()
    return {
      show(step, { instant } = {}) { d.apply(step, instant) },
      destroy() {},
    }
  },
}
