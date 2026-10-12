// Scene 5 of the methodology deck: no peeking into the future. What is known before the moment of the forecast and the
// target window of the next 3 hours, a leak, the leak test, a planted leak the test must catch, and the audit that fixed
// what slipped through.
// Sources: README.md (Дані, Перевірка, Як ми працювали), docs/data/JEV.md (Витік), docs/data/VERIFICATION.md,
// tests/test_gold_hourly.py, tests/test_quiet.py, tests/test_quiet_forecast.py.
import { h, s, canvas, put, stagger } from '../how.js'

const CSS = `
.scene-leakage .ink { fill: var(--ink); }
.scene-leakage .soft { fill: var(--soft); }
.scene-leakage .pink { fill: var(--pink); }
.scene-leakage .on-pink { fill: var(--card); }
.scene-leakage .fill-pink { fill: var(--pink); }
.scene-leakage .fill-soft { fill: var(--pink-soft); }
.scene-leakage .fill-ink { fill: var(--ink); }
.scene-leakage .hollow { fill: var(--card); stroke: var(--soft); stroke-width: 2; }
.scene-leakage .ring { fill: var(--card); stroke: var(--pink); stroke-width: 3; }
.scene-leakage .arc { fill: none; stroke: var(--pink); stroke-width: 4; stroke-linecap: round; }
.scene-leakage .cross { fill: none; stroke: var(--ink); stroke-width: 5; stroke-linecap: round; }
.scene-leakage .disp { font-family: var(--font-display); }
.scene-leakage.tip { position: absolute; z-index: 2; max-width: 260px; padding: 6px 10px; border-radius: var(--r-small); background: var(--card);
  border: 1px solid var(--line); color: var(--ink); font-size: 15px; line-height: 1.35; pointer-events: none; }
.scene-leakage.tip[hidden] { display: none; }
@media (max-width: 600px) { .scene-leakage.tip { max-width: 220px; font-size: 14px; } }
`

const LEAK_TEST = { moments: 50, values: 2400, mismatches: 0 } // README.md, Перевірка (tests/test_gold_hourly.py)
const QUIET_HOURS = 60                                        // tests/test_quiet.py: random hours of kyiv_quiet rebuilt at t
const AUDIT = { hours: 77, wrong: 15 } // README.md, Перевірка; docs/data/VERIFICATION.md
// docs/data/VERIFICATION.md: AerisRimor post 84052 published at 20:45 Kyiv, its text «станом на 02:25» (hours after 20:00)
const PUBLISHED = 0.75
const TEXT_AT = 6 + 25 / 60

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

const VERIFIER = '... кожен шматок будував один агент, а приймав свіжий агент лише з читанням: стартував з «не пройдено», сам запускав перевірки, підкладав витік, який тест мусить зловити, і читав рядки вручну.'

const TEST_FEATURES = `    def test_features_use_only_hours_ended_by_t(self):
        """For random hours t, rebuild row t from what is known at t: flags and post answers of hours that ended by t
        (h + 1 h <= t), S4 events with available_at < t whose direction is hidden until their last post: every feature
        is the same."""
        ...
            again = kyiv_quiet.build_table(self.h.slice(i, 1), flags, drone_max, s4).to_pylist()[0]
            want = self.q.slice(i, 1).to_pylist()[0]
            self.assertEqual({k: v for k, v in again.items() if k not in kyiv_quiet.TARGETS},
                             {k: v for k, v in want.items() if k not in kyiv_quiet.TARGETS})`

const TEST_FLIP = `    def test_nothing_after_t_changes_the_forecast(self):
        """Drop every labelled hour whose target is not known at t, or flip all their targets: the same forecast."""
        ...
            self.assertEqual(forecast.forecast(t, (flipped, every))["p"], want["p"])`

export default {
  id: 'leakage',
  title: 'Не підглядати в майбутнє',
  lead: 'У момент прогнозу модель знає лише минуле, і це перевіряють тести, які мусять ловити навмисно підкладений витік.',
  steps: [
    {
      note: '<p>Щогодини модель робить прогноз. У цей момент вона бачить лише минуле, наприклад скільки годин минуло від останньої атаки, ' +
        'а вгадати має, чи буде атака в наступні 3 години.</p>' +
        src('README.md, розділ Дані: рядок таблиці gold це момент рішення t; ознаки лише з того, що відомо до t, ціль з годин [t, t + 3 год).'),
      prompts: [{ title: 'Рядок таблиці даних', text: 'gold (таблиця на питання: рядок на момент рішення t, ознаки лише з того, що відомо до t, ціль після t)', source: 'опис проєкту, розділ Дані' }],
    },
    {
      note: '<p>Витік: у момент прогнозу модель знає хоч щось, що сталося пізніше. На історії така модель блищить, а наживо провалюється. ' +
        'Приклад: мітка години, тобто що в цю годину загрожувало Києву, читає лише пости до кінця цієї години; пост з наступної години вже майбутнє.</p>' +
        src('docs/data/JEV.md, розділ Витік: інакше ознака threat_prev_1h у момент h+1 знала б майбутнє.'),
      prompts: [{
        title: 'Правило проти витоку',
        text: '- Мітка години h бачить пости лише до кінця години h. Контекст з години h-1 можна, з години h+1 ніколи: інакше ознака `threat_prev_1h` у момент h+1 знала б майбутнє.',
        source: 'інструкція для Jev, розділ Витік',
      }],
    },
    {
      note: `<p>Тест: програма, яка сама перевіряє правило. Для ${num(LEAK_TEST.moments)} випадкових моментів вона заново рахує всі числа ` +
        `лише з того, що було відомо до моменту, і порівнює з таблицею: ${num(LEAK_TEST.values)} значень, ${num(LEAK_TEST.mismatches)} розбіжностей. ` +
        `Таблицю для питання про 3 години так само перевіряють на ${QUIET_HOURS} випадкових годинах.</p>` +
        src('README.md, розділ Перевірка; tests/test_gold_hourly.py (таблиця gold); tests/test_quiet.py (таблиця kyiv_quiet).'),
      prompts: [{ title: 'Код тесту на витік', text: TEST_FEATURES, source: 'тест таблиці для питання' }],
    },
    {
      note: '<p>Тест, який ніколи не падає, нічого не доводить. Тому роботу приймав окремий ШІ-агент, який не міг змінювати код: ' +
        'він навмисно підкладав витік, і тест мусив упасти. Ще один тест міняє всі ще невідомі мітки на протилежні, а прогноз мусить лишитись тим самим.</p>' +
        src('README.md, розділ Як ми працювали; tests/test_quiet_forecast.py.'),
      prompts: [
        { title: 'Правило для агента-перевірника', text: VERIFIER, source: 'опис проєкту, розділ Як ми працювали' },
        { title: 'Код тесту: перевернути майбутнє', text: TEST_FLIP, source: 'тест прогнозу' },
      ],
    },
    {
      note: `<p>Аудит, тобто ручна перевірка: перед навчанням моделі прочитано пости кожної з ${num(AUDIT.hours)} годин з ударом. ` +
        '60 справді були ударом, 14 звітами про наслідки, 1 реактивним дроном, 2 неясні. ' +
        `${num(AUDIT.wrong)} хибних годин виправлено, і рядків з ударом стало 138 замість 151.</p>` +
        src('docs/data/VERIFICATION.md; README.md, розділ Перевірка.'),
      prompts: [{
        title: 'Питання перевірки: мітка удару',
        text: '| мітка | прочитано пости кожної з 77 годин удару | 60 удар, 14 звіти про наслідки, 1 реактивний дрон, 2 неясні; 15 виправлено (нижче) |',
        source: 'звіт перевірки даних',
      }],
    },
    {
      note: '<p>Пост можуть переписати вже після публікації. Канал моніторів опублікував пост о 20:45, а пізніше в ньому стояло нічне зведення ' +
        '«станом на 02:25» про зльоти Ту-95 і Ту-160. Через такі пости 4 події починались на 1.3 до 5.7 години раніше за свій текст; аудит це виправив.</p>' +
        src('docs/data/VERIFICATION.md: канал AerisRimor, пост 84052, 4 події S1.'),
      prompts: [{
        title: 'Питання перевірки: час поста',
        text: '| сигнали | чи може текст першого поста події бути написаним пізніше | так: 4 події S1 починались на 1.3..5.7 год раніше за свій текст; виправлено (нижче) |',
        source: 'звіт перевірки даних',
      }],
    },
  ],
  prompts: [],

  mount(stage) {
    stage.append(h('style', { text: CSS }))
    const svg = canvas(stage, 'Вісь часу: що відомо до моменту прогнозу, атака в наступні 3 години, тест на витік і аудит')
    svg.classList.add('scene-leakage')
    let cur = -1
    const TIP = [
      (x) => (x < 400 ? 'Що відомо: усе, що сталося до моменту прогнозу' : 'Наступні 3 години: чи буде атака'),
      () => 'Витік: те, що відомо, не може брати нічого з майбутнього',
      () => `${LEAK_TEST.moments} випадкових моментів: ${LEAK_TEST.values} значень, ${LEAK_TEST.mismatches} розбіжностей`,
      () => 'Підкладений витік перетнув момент прогнозу, і тест упав, як і мусив',
      (x) => (x < 250 ? `${AUDIT.hours} годин з ударом, ${AUDIT.wrong} хибних виправлено` : '60 удар, 14 звітів про наслідки, 1 реактивний дрон, 2 неясні'),
      () => `Опубліковано о 20:45, а текст «станом на 02:25»: ${(TEXT_AT - PUBLISHED).toFixed(1)} години різниці`,
    ]
    const tip = hoverTip(stage, svg, 'scene-leakage', (x, y) => (TIP[cur] ? TIP[cur](x, y) : ''))
    const d = director()
    const add = (node) => svg.appendChild(node)
    const on = (...ks) => (k) => ks.includes(k)
    const show = (when, hidden = { o: 0 }) => (k) => (when(k) ? {} : hidden)
    const axisSteps = on(0, 1, 2, 3)
    const tSteps = on(0, 1, 3)

    // step 1: the axis, the moment of the forecast, what is known before it and the next 3 hours after it
    d.add(add(s('rect', { x: 40, y: 229, width: 560, height: 3, class: 'fill-ink' })),
      show(axisSteps, { o: 0, kx: 0 }), { origin: 'left center', dur: 400 })
    d.add(add(s('g', {},
      s('rect', { x: 398.5, y: 150, width: 3, height: 110, class: 'fill-pink' }),
      T(400, 292, 'зараз', 'ink', 26, { 'text-anchor': 'middle', 'font-weight': 700 }))),
    show(tSteps, { o: 0, y: -10 }), { delay: (k) => (k === 0 ? 300 : 0) })
    d.add(add(s('g', {},
      s('rect', { x: 160, y: 180, width: 236, height: 44, rx: 6, class: 'fill-soft' }),
      T(278, 209, 'що відомо', 'ink', 22, { 'text-anchor': 'middle' }))),
    show(tSteps, { o: 0, kx: 0 }), { origin: 'right center', dur: 400, delay: (k) => (k === 0 ? 500 : 0) })
    d.add(add(s('g', {},
      s('rect', { x: 404, y: 180, width: 116, height: 44, rx: 6, class: 'fill-pink' }),
      T(462, 209, 'атака?', 'on-pink', 22, { 'text-anchor': 'middle', 'font-weight': 700 }))),
    show(tSteps, { o: 0, kx: 0 }), { origin: 'left center', dur: 400, delay: (k) => (k === 0 ? 750 : 0) })
    d.add(add(s('g', {},
      T(462, 262, '3 години', 'soft', 22, { 'text-anchor': 'middle' }),
      T(40, 292, 'минуле', 'soft'),
      T(600, 292, 'майбутнє', 'soft', 22, { 'text-anchor': 'end' }))),
    show(tSteps), { delay: (k) => (k === 0 ? 900 : 0) })

    // step 2: a leak, the future reaching into what is known, is not allowed
    d.add(add(s('g', {},
      s('path', { d: 'M 470 176 Q 400 100 330 176', class: 'arc' }),
      s('circle', { cx: 470, cy: 176, r: 7, class: 'fill-pink' }))),
    show(on(1), { o: 0, y: 10 }), { delay: (k) => (k === 1 ? 150 : 0) })
    d.add(add(s('g', {},
      s('path', { d: 'M386 124 L414 152 M414 124 L386 152', class: 'cross' }),
      T(426, 120, 'заборонено', 'ink', 22, { 'font-weight': 600 }))),
    show(on(1), { o: 0, k: 0.6 }), { delay: (k) => (k === 1 ? 550 : 0) })

    // step 3: the leak test at 50 random moments
    let seed = 11
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647
    for (let i = 0; i < LEAK_TEST.moments; i++) {
      const x = 44 + rnd() * 552
      d.add(add(s('rect', { x: x - 1.5, y: 214, width: 3, height: 32, rx: 1.5, class: 'fill-pink' })),
        show(on(2), { o: 0, ky: 0 }), { dur: 240, delay: (k) => (k === 2 ? stagger(i, 14, 150) : 0) })
    }
    ;[[40, LEAK_TEST.moments, 'моментів', 'ink'], [230, LEAK_TEST.values, 'значень', 'ink'],
      [450, LEAK_TEST.mismatches, 'розбіжностей', 'pink']].forEach(([x, n, lab, cls], i) => {
      d.add(add(s('g', {},
        T(x, 112, String(n), `${cls} disp`, 44, { 'font-weight': 800 }),
        T(x, 146, lab, 'soft'))),
      show(on(2), { o: 0, y: 10 }), { delay: (k) => (k === 2 ? stagger(i, 250, 600) : 0) })
    })

    // step 4: a planted leak crosses the moment of the forecast and the test must fail
    d.add(add(s('circle', { cx: 462, cy: 160, r: 10, class: 'fill-pink' })),
      (k) => (k === 3 ? { x: -162 } : { o: 0 }), { dur: 400, delay: (k) => (k === 3 ? 200 : 0) })
    d.add(add(T(300, 142, 'підкладений витік', 'ink', 22, { 'text-anchor': 'middle', 'font-weight': 600 })),
      show(on(3), { o: 0, y: 8 }), { delay: (k) => (k === 3 ? 550 : 0) })
    d.add(add(s('g', {},
      s('rect', { x: 120, y: 56, width: 400, height: 48, rx: 24, class: 'fill-pink' }),
      T(320, 87, 'тест упав: витік спіймано', 'on-pink', 22, { 'text-anchor': 'middle', 'font-weight': 700 }))),
    show(on(3), { o: 0, k: 0.9 }), { delay: (k) => (k === 3 ? 850 : 0) })

    // step 5: the audit read all 77 strike hours, 15 were wrong and fixed by hand
    d.add(add(s('g', {},
      T(40, 150, String(AUDIT.hours), 'ink disp', 52, { 'font-weight': 800 }),
      T(40, 182, 'годин з ударом', 'soft'),
      T(40, 262, String(AUDIT.wrong), 'pink disp', 52, { 'font-weight': 800 }),
      T(40, 294, 'хибних,', 'soft'),
      T(40, 322, 'виправлено', 'soft'))),
    show(on(4), { o: 0, y: 10 }), { delay: (k) => (k === 4 ? 100 : 0) })
    for (let i = 0; i < AUDIT.hours; i++) {
      const wrong = i >= AUDIT.hours - AUDIT.wrong
      d.add(add(s('rect', {
        x: 264 + (i % 11) * 32, y: 92 + Math.floor(i / 11) * 32, width: 24, height: 24, rx: 4,
        class: wrong ? 'hollow' : 'fill-pink',
      })), show(on(4), { o: 0, k: 0.6 }), { dur: 240, delay: (k) => (k === 4 ? stagger(i, 8, wrong ? 900 : 150) : 0) })
    }

    // step 6: a rewritten post dated its event 5.7 h before its own text
    const HX = (hours) => 60 + (hours * 520) / 7 // hours after 20:00 Kyiv
    d.add(add(s('g', {},
      s('rect', { x: 60, y: 249, width: 520, height: 3, class: 'fill-ink' }),
      [0, 2, 4, 6].flatMap((hr) => [
        s('rect', { x: HX(hr) - 1.5, y: 242, width: 3, height: 14, class: 'fill-ink' }),
        T(HX(hr), 284, `${String((20 + hr) % 24).padStart(2, '0')}:00`, 'soft', 22, { 'text-anchor': 'middle' }),
      ]),
      T(580, 150, 'текст: «станом на 02:25»', 'ink', 22, { 'text-anchor': 'end' }))),
    show(on(5), { o: 0, y: 10 }), { dur: 400 })
    d.add(add(s('circle', { cx: HX(TEXT_AT), cy: 250, r: 11, class: 'ring' })),
      show(on(5), { o: 0, k: 0.5 }), { delay: (k) => (k === 5 ? 200 : 0) })
    d.add(add(s('circle', { cx: HX(TEXT_AT), cy: 250, r: 11, class: 'fill-pink' })),
      (k) => (k === 5 ? { x: HX(PUBLISHED) - HX(TEXT_AT) } : { o: 0 }), { dur: 400, delay: (k) => (k === 5 ? 500 : 0) })
    d.add(add(T(60, 200, 'опубліковано 20:45', 'soft')), show(on(5)), { delay: (k) => (k === 5 ? 850 : 0) })
    const a = HX(PUBLISHED)
    const b = HX(TEXT_AT)
    d.add(add(s('g', {},
      s('rect', { x: a, y: 316, width: b - a, height: 3, class: 'fill-pink' }),
      s('rect', { x: a - 1.5, y: 309, width: 3, height: 17, class: 'fill-pink' }),
      s('rect', { x: b - 1.5, y: 309, width: 3, height: 17, class: 'fill-pink' }),
      T((a + b) / 2, 350, `${(TEXT_AT - PUBLISHED).toFixed(1)} години раніше`, 'pink', 22, { 'text-anchor': 'middle', 'font-weight': 700 }))),
    show(on(5), { o: 0, y: -8 }), { delay: (k) => (k === 5 ? 1050 : 0) })
    d.add(add(s('g', {},
      s('rect', { x: 60, y: 60, width: 170, height: 44, rx: 22, class: 'ring' }),
      T(145, 89, 'виправлено', 'ink', 22, { 'text-anchor': 'middle', 'font-weight': 600 }))),
    show(on(5), { o: 0, k: 0.9 }), { delay: (k) => (k === 5 ? 1350 : 0) })

    d.apply(-1, true)
    svg.getBoundingClientRect()
    return {
      show(step, { instant } = {}) { cur = step; tip.hidden = true; d.apply(step, instant) },
      destroy() {},
    }
  },
}
