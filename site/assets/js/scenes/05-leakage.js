// Scene 5 of the methodology deck: no peeking into the future. The features window before t and the target window
// [t, t + 3 h), a leak, the leak test, a planted leak the test must catch, and the audit that fixed what slipped through.
// Sources: README.md (Дані, Перевірка, Як ми працювали), docs/data/JEV.md (Витік), docs/data/VERIFICATION.md,
// tests/test_quiet.py, tests/test_quiet_forecast.py.
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
`

const LEAK_TEST = { moments: 50, values: 2400, mismatches: 0 } // README.md, Перевірка (tests/test_gold_hourly.py)
const AUDIT = { hours: 77, wrong: 15 } // README.md, Перевірка; docs/data/VERIFICATION.md
// docs/data/VERIFICATION.md: AerisRimor post 84052 published at 20:45 Kyiv, its text «станом на 02:25» (hours after 20:00)
const PUBLISHED = 0.75
const TEXT_AT = 6 + 25 / 60

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
  lead: 'У момент t модель знає лише минуле. Ми перевіряли це тестами, які мусять ловити навмисно підкладений витік.',
  steps: [
    {
      note: '<p>Кожен рядок gold це момент рішення t. Ознаки рахуються лише з того, що відомо до t, а ціль з годин [t, t + 3 год) (README, розділ Дані). Модель бачить ліве вікно і має вгадати праве.</p>',
      prompts: [{ title: 'Рядок gold', text: 'gold (таблиця на питання: рядок на момент рішення t, ознаки лише з того, що відомо до t, ціль після t)', source: 'README.md, розділ Дані' }],
    },
    {
      note: '<p>Витік це коли ознака в момент t знає хоч щось після t. Тоді модель блищить на історії і провалюється наживо. Приклад з <code>docs/data/JEV.md</code>: якби мітка години h читала пост з години h + 1, ознака <code>threat_prev_1h</code> знала б майбутнє.</p>',
      prompts: [{
        title: 'Правило витоку для Jev',
        text: '- Мітка години h бачить пости лише до кінця години h. Контекст з години h-1 можна, з години h+1 ніколи: інакше ознака `threat_prev_1h` у момент h+1 знала б майбутнє.',
        source: 'docs/data/JEV.md, розділ Витік',
      }],
    },
    {
      note: `<p>Тест на витік: для ${LEAK_TEST.moments} випадкових моментів t ознаки перераховано лише з того, що було відомо до t, і порівняно з gold: <span class="num">${LEAK_TEST.values}</span> значень, <span class="num">${LEAK_TEST.mismatches}</span> розбіжностей (<code>tests/test_gold_hourly.py</code>, README, розділ Перевірка). Для <code>kyiv_quiet</code> так само перебудовуються 60 випадкових годин (<code>tests/test_quiet.py</code>).</p>`,
      prompts: [{ title: 'Перевірка в тесті', text: TEST_FEATURES, source: 'tests/test_quiet.py' }],
    },
    {
      note: '<p>Тест, який ніколи не падає, нічого не доводить. Роботу приймав свіжий агент лише з читанням: він стартував з «не пройдено» і підкладав витік, який тест мусить зловити (README, розділ Як ми працювали). Тест прогнозу перевертає всі мітки, ще не відомі в t, і прогноз не має змінитись (<code>tests/test_quiet_forecast.py</code>).</p>',
      prompts: [{ title: 'Правило перевірника', text: VERIFIER, source: 'README.md, розділ Як ми працювали' }, { title: 'Перевернути майбутнє', text: TEST_FLIP, source: 'tests/test_quiet_forecast.py' }],
    },
    {
      note: `<p>Аудит перед моделюванням: прочитано пости кожної з ${AUDIT.hours} годин удару. 60 були ударом, 14 звітами про наслідки, 1 реактивним дроном, 2 неясні; <span class="num">${AUDIT.wrong}</span> годин виправлено вручну, і рядків з ударом стало 138 замість 151 (<code>docs/data/VERIFICATION.md</code>, README).</p>`,
      prompts: [{
        title: 'Питання аудиту: мітка',
        text: '| мітка | прочитано пости кожної з 77 годин удару | 60 удар, 14 звіти про наслідки, 1 реактивний дрон, 2 неясні; 15 виправлено (нижче) |',
        source: 'docs/data/VERIFICATION.md',
      }],
    },
    {
      note: '<p>Текст поста може бути написаним пізніше за публікацію. AerisRimor переписує нічне зведення: пост 84052 опубліковано о 20:45 за Києвом, а текст «станом на 02:25» зі зльотами Ту-95 і Ту-160. Через це 4 події S1 починались на 1.3 до 5.7 год раніше за свій текст; аудит це виправив (<code>docs/data/VERIFICATION.md</code>).</p>',
      prompts: [{
        title: 'Питання аудиту: сигнали',
        text: '| сигнали | чи може текст першого поста події бути написаним пізніше | так: 4 події S1 починались на 1.3..5.7 год раніше за свій текст; виправлено (нижче) |',
        source: 'docs/data/VERIFICATION.md',
      }],
    },
  ],
  prompts: [],

  mount(stage) {
    stage.append(h('style', { text: CSS }))
    const svg = canvas(stage, 'Вісь часу з моментом t: ознаки до t, ціль після t, тест на витік і аудит')
    svg.classList.add('scene-leakage')
    const d = director()
    const add = (node) => svg.appendChild(node)
    const on = (...ks) => (k) => ks.includes(k)
    const show = (when, hidden = { o: 0 }) => (k) => (when(k) ? {} : hidden)
    const axisSteps = on(0, 1, 2, 3)
    const tSteps = on(0, 1, 3)

    // step 1: the axis, t, the features window before t and the target window [t, t + 3 h)
    d.add(add(s('rect', { x: 40, y: 229, width: 560, height: 3, class: 'fill-ink' })),
      show(axisSteps, { o: 0, kx: 0 }), { origin: 'left center', dur: 400 })
    d.add(add(s('g', {},
      s('rect', { x: 398.5, y: 150, width: 3, height: 110, class: 'fill-pink' }),
      T(400, 292, 't', 'ink', 28, { 'text-anchor': 'middle', 'font-weight': 700 }))),
    show(tSteps, { o: 0, y: -10 }), { delay: (k) => (k === 0 ? 300 : 0) })
    d.add(add(s('g', {},
      s('rect', { x: 160, y: 180, width: 236, height: 44, rx: 6, class: 'fill-soft' }),
      T(278, 209, 'ознаки', 'ink', 22, { 'text-anchor': 'middle' }))),
    show(tSteps, { o: 0, kx: 0 }), { origin: 'right center', dur: 400, delay: (k) => (k === 0 ? 500 : 0) })
    d.add(add(s('g', {},
      s('rect', { x: 404, y: 180, width: 116, height: 44, rx: 6, class: 'fill-pink' }),
      T(462, 209, 'ціль', 'on-pink', 22, { 'text-anchor': 'middle', 'font-weight': 700 }))),
    show(tSteps, { o: 0, kx: 0 }), { origin: 'left center', dur: 400, delay: (k) => (k === 0 ? 750 : 0) })
    d.add(add(s('g', {},
      T(462, 262, '3 год', 'soft', 22, { 'text-anchor': 'middle' }),
      T(60, 292, 'минуле', 'soft'),
      T(600, 292, 'майбутнє', 'soft', 22, { 'text-anchor': 'end' }))),
    show(tSteps), { delay: (k) => (k === 0 ? 900 : 0) })

    // step 2: a leak, the future reaching into the features, is not allowed
    d.add(add(s('g', {},
      s('path', { d: 'M 470 176 Q 400 100 330 176', class: 'arc' }),
      s('circle', { cx: 470, cy: 176, r: 7, class: 'fill-pink' }))),
    show(on(1), { o: 0, y: 10 }), { delay: (k) => (k === 1 ? 150 : 0) })
    d.add(add(s('g', {},
      s('path', { d: 'M386 124 L414 152 M414 124 L386 152', class: 'cross' }),
      T(426, 120, 'заборонено', 'ink', 22, { 'font-weight': 600 }))),
    show(on(1), { o: 0, k: 0.6 }), { delay: (k) => (k === 1 ? 550 : 0) })

    // step 3: the leak test at 50 random moments t
    let seed = 11
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647
    for (let i = 0; i < LEAK_TEST.moments; i++) {
      const x = 44 + rnd() * 552
      d.add(add(s('rect', { x: x - 1.5, y: 214, width: 3, height: 32, rx: 1.5, class: 'fill-pink' })),
        show(on(2), { o: 0, ky: 0 }), { dur: 240, delay: (k) => (k === 2 ? stagger(i, 14, 150) : 0) })
    }
    ;[[40, LEAK_TEST.moments, 'моментів t', 'ink'], [230, LEAK_TEST.values, 'значень', 'ink'],
      [450, LEAK_TEST.mismatches, 'розбіжностей', 'pink']].forEach(([x, n, lab, cls], i) => {
      d.add(add(s('g', {},
        T(x, 112, String(n), `${cls} disp`, 44, { 'font-weight': 800 }),
        T(x, 146, lab, 'soft'))),
      show(on(2), { o: 0, y: 10 }), { delay: (k) => (k === 2 ? stagger(i, 250, 600) : 0) })
    })

    // step 4: a planted leak crosses t and the test must fail
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
      T(40, 182, 'годин удару', 'soft'),
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
      T((a + b) / 2, 350, `${(TEXT_AT - PUBLISHED).toFixed(1)} год раніше`, 'pink', 22, { 'text-anchor': 'middle', 'font-weight': 700 }))),
    show(on(5), { o: 0, y: -8 }), { delay: (k) => (k === 5 ? 1050 : 0) })
    d.add(add(s('g', {},
      s('rect', { x: 60, y: 60, width: 170, height: 44, rx: 22, class: 'ring' }),
      T(145, 89, 'виправлено', 'ink', 22, { 'text-anchor': 'middle', 'font-weight': 600 }))),
    show(on(5), { o: 0, k: 0.9 }), { delay: (k) => (k === 5 ? 1350 : 0) })

    d.apply(-1, true)
    svg.getBoundingClientRect()
    return {
      show(step, { instant } = {}) { d.apply(step, instant) },
      destroy() {},
    }
  },
}
