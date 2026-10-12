// Scene 6 of the methodology deck: how we checked. A split by time (training data, then test data opened once), 8 weekly
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
.scene-walkforward.tip { position: absolute; z-index: 2; max-width: 260px; padding: 6px 10px; border-radius: var(--r-small); background: var(--card);
  border: 1px solid var(--line); color: var(--ink); font-size: 15px; line-height: 1.35; pointer-events: none; }
.scene-walkforward.tip[hidden] { display: none; }
@media (max-width: 600px) { .scene-walkforward.tip { max-width: 220px; font-size: 14px; } }
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
  { group: 'навчальні', model: 0.094, naive: -0.061 },
  { group: 'тестові', model: 0.284, naive: 0.277 },
]
const MODELS = 11 // README.md, Епоха 3: 11 models in three modules
const RULES = ['до 6 варіантів на модель', 'простіша, якщо гірша < 0.01', 'межі ризику за правилом']

const T = (x, y, text, cls = 'ink', size = 22, more = {}) =>
  s('text', { x, y, class: cls, 'font-size': size, ...more, text })
const num = (v) => `<span class="num">${v}</span>`
// file paths and code names live only in this folded block at the end of a note
const src = (text) => `<details class="how-src"><summary>Джерела</summary><p>${text}</p></details>`

// hover or tap on the stage: one plain line about what is under the pointer at this step
function hoverTip(stage, svg, cls, textAt) {
  const tip = h('div', { class: `${cls} tip`, role: 'tooltip', hidden: true })
  stage.append(tip)
  const move = (e) => {
    const b = svg.getBoundingClientRect()
    const t = textAt(((e.clientX - b.left) * 640) / b.width, ((e.clientY - b.top) * 400) / b.height)
    if (!t) { tip.hidden = true; return }
    tip.textContent = t
    tip.hidden = false
    const sb = stage.getBoundingClientRect()
    tip.style.left = `${Math.max(4, Math.min(e.clientX - sb.left + 14, sb.width - tip.offsetWidth - 4))}px`
    tip.style.top = `${Math.max(4, Math.min(e.clientY - sb.top + 14, sb.height - tip.offsetHeight - 4))}px`
  }
  svg.addEventListener('pointermove', move)
  svg.addEventListener('pointerdown', move)
  svg.addEventListener('pointerleave', () => { tip.hidden = true })
  return tip
}

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
  title: 'Як ми перевіряли модель',
  lead: 'Модель вчилась лише на минулому, а останні 6 тижнів ми відклали і відкрили один раз, для фінальної оцінки.',
  steps: [
    {
      note: '<p>Дані ділимо за часом, а не навмання, інакше години однієї атаки потрапили б і в навчання, і в перевірку. ' +
        'Навчальні дані (до 28.08): на них вибирали все. ' +
        'Тестові дані (з 29.08, відкладені до кінця): останні 6 тижнів, їх відкрили один раз, для фінальної оцінки.</p>' +
        src('docs/adr/0008-time-split.md: межа 2026-08-29 12:00 за Києвом; README.md, розділ Поділ і правила.'),
      prompts: [{
        title: 'Тестові дані',
        text: '- **Тест:** усі години з 2026-08-29 12:00 за Києвом (09:00Z) до кінця міток, тобто останні 6 повних тижнів: 1014 рядків, 31 true, 9 атак. Тест відкриваємо один раз, для фінальної оцінки, і модель на ньому перенавчається щотижня на всьому, що відомо до початку тижня.',
        source: 'рішення про поділ даних',
      }],
    },
    {
      note: '<p>Перевірка тиждень за тижнем: модель вчиться на всьому до 4 липня і прогнозує наступний тиждень, потім межа зсувається на тиждень. ' +
        `Так ${num(FOLDS)} разів, тож кожен прогноз зроблено на годинах, яких модель не бачила. Уперше вона вчиться лише на травні і червні.</p>` +
        src('docs/adr/0008-time-split.md: 8 тижневих фолдів walk-forward з 2026-07-04 12:00 за Києвом.'),
      prompts: [{
        title: 'Навчальні дані',
        text: '- **Розробка:** години, чия мітка відома до межі: 2890 рядків, 107 true, 26 атак. Ознаки, модель, поріг і розмір вікна навчання обираємо на 8 тижневих фолдах walk-forward з 2026-07-04 12:00 за Києвом. ...',
        source: 'рішення про поділ даних',
      }],
    },
    {
      note: '<p>Правила вибору записали до першої оцінки: до 6 варіантів на модель, список до запуску. ' +
        'Перемагає найбільший виграш над простим правилом (BSS) на навчальних даних, але простіша модель, якщо вона гірша менш ніж на 0.01; межі ризику теж за правилом. ' +
        'Так вибір не можна було підігнати під тестові дані.</p>' +
        src('docs/adr/0011-quiet-hours.md, правила до оцінки.'),
      prompts: [{ title: 'Правила, записані до оцінки', text: RULES_0011, source: 'запис рішення про спокійні години' }],
    },
    {
      note: `<p>Для питання про 3 години агенти запропонували ${num(MODELS)} моделей трьох видів: прості правила, лінійні моделі, дерева рішень. ` +
        'За правилом перемогла фінальна модель: логістична регресія на 7 сигналах, тобто зважена сума сигналів, перетворена на ймовірність. ' +
        'Сигнали: година доби, давність атаки і дронів, хвилі дронів, пости моніторів.</p>' +
        src('README.md, Епоха 3: 11 моделей у модулях baselines, linear, trees; фіналіст logit_signals.'),
    },
    {
      note: '<p><b>BSS</b>, «виграш над простим правилом» (розділ 2): 0 так само, більше 0 краще, менше 0 гірше. ' +
        '<b>«Частка за 7 днів»</b>: найпростіший прогноз без моделі, частка 3-годинних вікон з атакою за останні 7 днів; якщо таких 50 із 168, щогодини він каже 30%.</p>' +
        `<p>Атака йшла за 31% спокійних годин навчальних даних і 71% тестових: на навчальних модель ${BSS[0].model} проти ${BSS[0].naive} у частки, ` +
        `на тестових ${num(BSS[1].model)} проти ${BSS[1].naive}.</p>` +
        src('README.md, розділи Мірила і Епоха 3: BSS на годинах «зараз тихо», logit_signals і naive_7d (частка за 7 днів).'),
      prompts: [{
        title: 'Як читати BSS',
        text: '**Мірила простими словами.** BSS: наскільки ймовірності точніші за сталу частку подій, відому на початок тижня; 0 той самий рівень, більше 0 краще.',
        source: 'опис проєкту, розділ Мірила',
      }],
    },
  ],
  prompts: [],

  mount(stage) {
    stage.append(h('style', { text: CSS }))
    const svg = canvas(stage, 'Навчальні і тестові дані на осі часу, 8 тижнів перевірки, правила, 11 моделей і виграш фінальної моделі')
    svg.classList.add('scene-walkforward')
    let cur = -1
    const day = (v) => { const t = new Date(Date.UTC(2026, 4, 1) + v * 864e5); return `${String(t.getUTCDate()).padStart(2, '0')}.${String(t.getUTCMonth() + 1).padStart(2, '0')}` }
    const TIP = [
      (x) => (x < X(SPLIT) ? 'Навчальні дані: з 01.05 до 29.08, на них вибирали все' : 'Тестові дані: з 29.08 до 10.10, відкриті один раз'),
      (x, y) => { const i = Math.max(0, Math.min(FOLDS - 1, Math.floor((y - 172) / 22))); return `Тиждень ${i + 1} з ${FOLDS}: модель вчиться на всьому до ${day(FOLD0 + 7 * i)} і прогнозує наступні 7 днів` },
      (x, y) => (y > 190 ? RULES[Math.max(0, Math.min(RULES.length - 1, Math.floor((y - 198) / 60)))] : 'Правила записали до першої оцінки'),
      () => `${MODELS} моделей трьох видів; рожева перемогла за правилом`,
      (x, y) => (y < 290 ? `Навчальні дані: фінальна модель ${BSS[0].model}, частка за 7 днів ${BSS[0].naive}` : `Тестові дані: фінальна модель ${BSS[1].model}, частка за 7 днів ${BSS[1].naive}`),
    ]
    const tip = hoverTip(stage, svg, 'scene-walkforward', (x, y) => (TIP[cur] ? TIP[cur](x, y) : ''))
    const d = director()
    const add = (node) => svg.appendChild(node)
    const only = (from, to = from, hidden = { o: 0 }) => (k) => (k >= from && k <= to ? {} : hidden)

    // step 1: the split by time, the test data is locked; mid stage on step 1, it moves up to make room for the next steps
    const xs = X(SPLIT)
    d.add(add(s('g', {},
      s('rect', { x: 40, y: 80, width: xs - 42, height: 40, rx: 8, class: 'fill-soft' }),
      s('rect', { x: xs + 2, y: 80, width: 600 - xs - 2, height: 40, rx: 8, class: 'fill-pink' }),
      T((40 + xs) / 2, 107, 'навчальні дані', 'ink', 22, { 'text-anchor': 'middle' }),
      s('rect', { x: 470, y: 96, width: 16, height: 13, rx: 2, class: 'lock' }),
      s('path', { d: 'M473 96 v-4 a5 5 0 0 1 10 0 v4', class: 'lock' }),
      T(493, 108, 'тестові', 'on-pink', 22, { 'font-weight': 700 }),
      T(40, 148, '01.05', 'soft'),
      T(xs, 148, '29.08', 'soft', 22, { 'text-anchor': 'middle' }),
      T(600, 148, '10.10', 'soft', 22, { 'text-anchor': 'end' }))),
    (k) => (k < 0 ? { o: 0, y: 122 } : k === 0 ? { y: 110 } : {}), { dur: 400 })

    // step 2: 8 weeks, each learns on all the past and predicts the next week
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
    d.add(add(T(320, 200, `${MODELS} моделей, 3 види`, 'soft', 22, { 'text-anchor': 'middle' })), only(3, 3))
    for (let i = 0; i < MODELS; i++) {
      d.add(add(s('circle', { cx: 70 + i * 50, cy: 256, r: 14, class: 'fill-grey' })),
        (k) => (k === 3 ? { o: 0.45 } : { o: 0, k: 0.5 }), { delay: (k) => (k === 3 ? stagger(i, 50, 100) : 0) })
    }
    d.add(add(s('circle', { cx: 70 + FIN * 50, cy: 256, r: 14, class: 'fill-pink' })),
      (k) => (k === 3 ? { k: 1.5 } : { o: 0, k: 0.5 }), { delay: (k) => (k === 3 ? 900 : 0) })
    d.add(add(T(70 + FIN * 50, 312, 'фінальна модель', 'ink', 22, { 'text-anchor': 'middle', 'font-weight': 700 })),
      only(3, 3, { o: 0, y: 8 }), { delay: (k) => (k === 3 ? 1100 : 0) })

    // step 5: BSS of the finalist and of the 7-day share, training and test data
    const Z = 320
    const U = 840 // units per 1.0 of BSS
    d.add(add(s('g', {},
      s('rect', { x: 40, y: 180, width: 18, height: 18, rx: 4, class: 'fill-pink' }), T(66, 196, 'фінальна модель'),
      s('rect', { x: 330, y: 180, width: 18, height: 18, rx: 4, class: 'fill-grey' }), T(356, 196, 'частка за 7 днів'),
      s('rect', { x: Z - 1, y: 212, width: 2, height: 152, class: 'fill-ink' }),
      T(Z, 388, '0', 'soft', 22, { 'text-anchor': 'middle' }),
      T(600, 388, 'виграш (BSS)', 'soft', 22, { 'text-anchor': 'end' }))),
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
      show(step, { instant } = {}) { cur = step; tip.hidden = true; d.apply(step, instant) },
      destroy() {},
    }
  },
}
