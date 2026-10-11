// Scene 11 of the methodology deck: how the project was built, by a person who decides and a swarm of agents.
// Facts: README.md «Як ми працювали» (also the verifier rule), docs/adr/0009-three-models.md, docs/HISTORY.md;
// the brief is from the author's orchestration rules (~/.claude/skills/swarm/SKILL.md), outside the repo.
import { h, s, canvas, put, stagger } from '../how.js'

const ID = 'agents'

const CSS = `
.scene-agents text { font-size: 22px; fill: var(--body); }
.scene-agents .soft { fill: var(--soft); }
.scene-agents .ink { fill: var(--ink); }
.scene-agents .pinkt { fill: var(--pink); font-weight: 600; }
.scene-agents .wt { fill: var(--card); font-weight: 600; }
.scene-agents .card { fill: var(--card); stroke: var(--line); stroke-width: 2; }
.scene-agents .stamp { fill: var(--card); stroke: var(--pink); stroke-width: 3; }
.scene-agents .rule { stroke: var(--line); stroke-width: 2; }
.scene-agents .halo { fill: var(--pink-soft); }
.scene-agents .pinkf { fill: var(--pink); }
.scene-agents .inkf { fill: var(--ink); }
.scene-agents .dotA { fill: var(--pink-soft); stroke: var(--pink); stroke-width: 3; }
.scene-agents .dotB { fill: var(--ink); }
.scene-agents .dotC { fill: var(--card); stroke: var(--ink); stroke-width: 3; }
.scene-agents .pline, .scene-agents .iline, .scene-agents .sline, .scene-agents .wline { fill: none; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
.scene-agents .pline { stroke: var(--pink); }
.scene-agents .iline { stroke: var(--ink); }
.scene-agents .sline { stroke: var(--soft); }
.scene-agents .wline { stroke: var(--card); }
`

const robot = (x, y) => s('g', { transform: `translate(${x} ${y})` },
  s('rect', { x: -22, y: -16, width: 44, height: 34, rx: 8, class: 'iline' }),
  s('circle', { cx: -8, cy: 0, r: 3.5, class: 'inkf' }),
  s('circle', { cx: 8, cy: 0, r: 3.5, class: 'inkf' }),
  s('path', { d: 'M0-16v-8', class: 'iline' }),
  s('circle', { cx: 0, cy: -27, r: 3.5, class: 'inkf' }))

const only = (k, dy = 12) => (st) => (st === k ? {} : { o: 0, y: st < k ? dy : -dy })

const QUESTIONS = ['ракетний удар за 3 год?', 'спати в коридорі?', '3 години буде тихо?', 'що парсити наживо?']
const MISTAKES = ['тест на кожному запуску', '15 хибних годин з 77', 'переписані пости', 'поріг питали в людини', 'витік у змінних модуля']

export default {
  id: ID,
  title: 'Як це будували',
  lead: 'Користувач питає й вирішує, Claude Code ділить роботу, агенти будують, а свіжі агенти перевіряють.',
  steps: [
    {
      note: '<p>Питання ставив і рішення ухвалював користувач: що прогнозувати, які дані брати, які пакети дозволити, коли відкрити тест. '
        + 'Після кожної епохи він ставив нове питання: від ударів до ночей, від ночей до спокою, від спокою до живого сайту.</p>'
        + '<p>Джерело: docs/HISTORY.md, «Рішення користувача» і «Рішення користувача в моделюванні».</p>',
      prompts: [{
        title: 'Рішення користувача',
        text: '2026-10-10 | Ціль: ракетний удар по місту Київ (вибухи, збиття, уламки, влучання), горизонт 3 год. ... Агенти на Sonnet',
        source: 'docs/HISTORY.md, «Рішення користувача»',
      }],
    },
    {
      note: '<p>Оркестратор, Claude Code, ділить роботу на шматки, і кожен шматок будує один агент. '
        + 'Агент отримує короткий бриф: задача одним реченням, команда для перевірки, дозволені файли, бюджет часу й викликів і що повернути. '
        + 'Так будували і цей сайт: кілька агентів пишуть різні файли одночасно.</p>'
        + '<p>Джерела: README.md, «Як ми працювали»; правила оркестрації автора, ~/.claude/skills/swarm/SKILL.md.</p>',
      prompts: [{
        title: 'Бриф для агента',
        text: 'TASK one sentence | DONE MEANS command + expected output | FILES allowed paths only | BUDGET time + calls, on exceed stop and return blocked | RETURN status pass/fail/blocked, evidence path, changed files, question | RULES ~/.agent/AGENTS.md',
        source: '~/.claude/skills/swarm/SKILL.md',
      }],
    },
    {
      note: '<p>Кожен шматок приймає свіжий агент, який лише читає код. '
        + 'Він стартує з «не пройдено», сам запускає перевірки, підкладає витік, який тест мусить зловити, і читає рядки вручну. '
        + 'Якщо перевірка не пройшла, будівник мав одну спробу виправити, решту виправляв оркестратор після власної перевірки.</p>'
        + '<p>Джерела: README.md, «Як ми працювали»; docs/adr/0009-three-models.md.</p>',
      prompts: [{
        title: 'Правило перевіряльника',
        text: 'кожен шматок будував один агент, а приймав свіжий агент лише з читанням: стартував з «не пройдено», сам запускав перевірки, підкладав витік, який тест мусить зловити, і читав рядки вручну.',
        source: 'README.md, «Як ми працювали»',
      }],
    },
    {
      note: '<p>Моделі шукали 4 агенти-дослідники, кожен у своїй родині: лінійні, дерева, процес подій, глибоке навчання. '
        + 'Двоє суддів з різними поглядами незалежно обрали ту саму трійку, а 3 скептики, по одному на модель, шукали в ній слабкі місця. '
        + 'Так з\'явились share_table, logistic і lgbm.</p>'
        + '<p>Джерело: docs/adr/0009-three-models.md.</p>',
      prompts: [{
        title: 'Правила проти перенавчання',
        text: '- до 6 варіантів налаштувань на модель, список пишеться до запуску;\n'
          + '- кожен результат записується в опис моделі;\n'
          + '- обирається найкращий BSS на фолдах розробки, але простіший варіант, якщо він гірший менш ніж на 0.01;\n'
          + '- налаштування заморожуються в коді, `t_utc` не буває ознакою, тест закритий.',
        source: 'docs/adr/0009-three-models.md',
      }],
    },
    {
      note: '<p>Помилки, які зловили й виправили:</p><ol>'
        + '<li>Таблиця порівняння друкувала тест на кожному запуску: тепер тест лише через final.</li>'
        + '<li>Аудит знайшов 15 хибних годин удару з 77: їх виправлено в CORRECTIONS.</li>'
        + '<li>Пости, переписані після публікації, починали події сигналів на 1.3..5.7 год раніше: тепер вони подій не створюють.</li>'
        + '<li>Оркестратор попросив користувача обрати поріг: тепер поріг дає правило з розробки, 0.197.</li>'
        + '<li>Тест на витік не ловив дані, сховані в змінних модуля: тепер перевіряє і їх.</li></ol>'
        + '<p>Джерела: README.md, «Як ми працювали»; docs/HISTORY.md, «Помилки і як їх виправлено».</p>',
      prompts: [{
        title: 'Запис про помилку',
        text: 'Помилка 4. Оркестратор попросив користувача обрати поріг (19%, 30% чи 50%) | поріг з правила розробки 0.197, «високий ризик» від 0.300; більше так не питати',
        source: 'docs/HISTORY.md, «Помилки і як їх виправлено»',
      }],
    },
  ],

  mount(stage) {
    const svg = canvas(stage, 'Хто що робив: користувач, Claude Code, агенти-будівники і перевіряльники')
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

    // The spine on the left: who acts, with a pink halo on the one this step is about.
    const SPINE = [
      { y: 54, label: 'користувач', hot: [0], icon: s('g', { transform: 'translate(70 54)' },
        s('circle', { cy: -12, r: 13, class: 'iline' }), s('path', { d: 'M-22 26c0-16 10-22 22-22s22 6 22 22', class: 'iline' })) },
      { y: 188, label: 'Claude Code', hot: [1], icon: s('g', { transform: 'translate(70 188)' },
        s('rect', { x: -24, y: -24, width: 48, height: 48, rx: 10, class: 'iline' }), s('path', { d: 'M-12-8l8 8-8 8M2 10h12', class: 'iline' })) },
      { y: 320, label: 'агенти', hot: [2, 3], icon: robot(70, 324) },
    ]
    SPINE.forEach((p) => {
      add(s('g', {}, s('circle', { cx: 70, cy: p.y, r: 36, class: 'halo' })), (st) => (p.hot.includes(st) ? {} : { o: 0, k: 0.6 }))
      add(s('g', {}, p.icon, s('text', { x: 70, y: p.y + 50, 'text-anchor': 'middle', class: 'ink', text: p.label })),
        (st) => (st >= 0 ? {} : { o: 0 }))
    })
    add(s('path', { d: 'M70 116v42M62 150l8 8 8-8M70 250v42M62 284l8 8 8-8', class: 'sline' }), (st) => (st >= 0 ? {} : { o: 0 }))

    // Step 1: the questions leave the person and line up as the epochs of the project.
    QUESTIONS.forEach((q, i) => {
      const cy = 56 + i * 84
      add(s('g', {},
        s('rect', { x: 190, y: cy - 26, width: 400, height: 52, rx: 26, class: 'card' }),
        s('text', { x: 212, y: cy + 8, class: 'pinkt', text: String(i + 1) }),
        s('text', { x: 236, y: cy + 8, class: 'ink', text: q }),
        s('circle', { cx: 560, cy, r: 15, class: 'pinkf' }),
        s('text', { x: 560, y: cy + 8, 'text-anchor': 'middle', class: 'wt', text: '?' })),
      (st) => (st === 0 ? {} : st < 0 ? { o: 0, x: -150, y: 54 - cy, k: 0.4 } : { o: 0, y: -12 }),
      { delay: (st) => (st === 0 ? stagger(i, 120) : 0), dur: 400 })
    })

    // Step 2: the work splits into pieces that fly from Claude Code to one builder each.
    for (let i = 0; i < 4; i++) {
      const px = 200 + (i % 2) * 215
      const py = 48 + Math.floor(i / 2) * 150
      add(s('g', {},
        s('rect', { x: px, y: py, width: 84, height: 104, rx: 10, class: 'card' }),
        ...[24, 44, 64, 84].map((dy, k) => s('line', { x1: px + 14, x2: px + (k === 0 ? 70 : 58), y1: py + dy, y2: py + dy, class: 'rule' }))),
      (st) => (st === 1 ? {} : st < 1 ? { o: 0, x: 70 - (px + 42), y: 188 - (py + 52), k: 0.3 } : { o: 0, y: -12 }),
      { delay: (st) => (st === 1 ? stagger(i, 110) : 0), dur: 400 })
      add(s('g', {}, robot(px + 150, py + 56)), (st) => (st === 1 ? {} : { o: 0, k: 0.5 }),
        { delay: (st) => (st === 1 ? 450 + stagger(i, 110) : 0) })
    }
    add(s('text', { x: 200, y: 372, class: 'ink', text: 'кожному агенту свій шматок' }), only(1), { delay: (st) => (st === 1 ? 700 : 0) })

    // Step 3: a fresh read-only agent starts from «не пройдено», plants a leak, the test catches it, only then «пройдено».
    add(s('g', {},
      s('rect', { x: 200, y: 70, width: 130, height: 180, rx: 12, class: 'card' }),
      ...[100, 124, 148].map((y) => s('line', { x1: 220, x2: 310, y1: y, y2: y, class: 'rule' })),
      s('g', { transform: 'translate(250 204)' }, s('path', { d: 'M0-24l20 8v12c0 14-9 22-20 26-11-4-20-12-20-26v-12z', class: 'iline' }))),
    only(2))
    add(s('g', {}, s('g', { transform: 'translate(250 204)' }, s('path', { d: 'M-8 2l6 6 10-12', class: 'pline' }))),
      (st) => (st === 2 ? {} : { o: 0, k: 0.3 }), { delay: (st) => (st === 2 ? 850 : 0) })
    add(s('g', {}, s('g', { transform: 'translate(304 206)' }, s('path', { d: 'M0-16c8 10 12 16 12 22a12 12 0 0 1-24 0c0-6 4-12 12-22z', class: 'pinkf' }))),
      (st) => (st === 2 ? {} : { o: 0, x: 258, y: -10 }), { delay: (st) => (st === 2 ? 450 : 0), dur: 400 })
    add(s('text', { x: 265, y: 288, 'text-anchor': 'middle', class: 'ink', text: 'витік зловлено' }), only(2),
      { delay: (st) => (st === 2 ? 900 : 0) })
    add(s('g', {},
      s('rect', { x: 342, y: 86, width: 156, height: 44, rx: 8, class: 'stamp' }),
      s('text', { x: 420, y: 116, 'text-anchor': 'middle', class: 'pinkt', text: 'не пройдено' })),
    (st) => (st === 2 ? {} : { o: 0, k: 1.4 }), { delay: (st) => (st === 2 ? 150 : 0) })
    add(s('rect', { x: 336, y: 106.5, width: 168, height: 3, class: 'pinkf' }), (st) => (st === 2 ? {} : { o: 0, kx: 0 }),
      { delay: (st) => (st === 2 ? 1000 : 0), origin: 'left' })
    add(s('g', {},
      s('rect', { x: 354, y: 196, width: 132, height: 44, rx: 8, class: 'pinkf' }),
      s('text', { x: 420, y: 226, 'text-anchor': 'middle', class: 'wt', text: 'пройдено' })),
    (st) => (st === 2 ? {} : { o: 0, k: 1.4 }), { delay: (st) => (st === 2 ? 1150 : 0) })
    add(s('g', {},
      robot(562, 196),
      s('circle', { cx: 592, cy: 214, r: 9, class: 'pline' }),
      s('path', { d: 'M599 221l8 8', class: 'pline' }),
      s('text', { x: 562, y: 268, 'text-anchor': 'middle', class: 'ink', text: 'свіжий агент' }),
      s('text', { x: 562, y: 298, 'text-anchor': 'middle', class: 'soft', text: 'лише читає' })),
    only(2))

    // Step 4: 4 researchers, 2 judges, 3 skeptics, 3 models.
    const COLS = [
      { x: 230, ys: [90, 150, 210, 270], cls: 'dotA', label: '4 дослідники', ly: 340 },
      { x: 340, ys: [150, 210], cls: 'dotB', label: '2 судді', ly: 372 },
      { x: 450, ys: [120, 180, 240], cls: 'dotC', label: '3 скептики', ly: 340 },
    ]
    COLS.forEach((c, ci) => {
      const next = COLS[ci + 1]
      if (next) {
        const wires = s('g', {}, ...c.ys.flatMap((y1) => next.ys.map((y2) => s('line', { x1: c.x, y1, x2: next.x, y2, class: 'rule' }))))
        add(wires, only(3, 0), { delay: (st) => (st === 3 ? 250 + ci * 300 : 0) })
      }
      c.ys.forEach((y, k) => add(s('circle', { cx: c.x, cy: y, r: 12, class: c.cls }), (st) => (st === 3 ? {} : { o: 0, k: 0.3 }),
        { delay: (st) => (st === 3 ? ci * 300 + stagger(k, 50) : 0) }))
      add(s('text', { x: c.x, y: c.ly, 'text-anchor': 'middle', class: 'ink', text: c.label }), only(3),
        { delay: (st) => (st === 3 ? ci * 300 : 0) })
    })
    ;['share_table', 'logistic', 'lgbm'].forEach((m, k) => {
      const y = 120 + k * 60
      add(s('line', { x1: 450, y1: y, x2: 494, y2: y, class: 'rule' }), only(3, 0), { delay: (st) => (st === 3 ? 850 : 0) })
      add(s('g', {},
        s('rect', { x: 494, y: y - 20, width: 136, height: 40, rx: 20, class: 'card' }),
        s('text', { x: 562, y: y + 8, 'text-anchor': 'middle', class: 'ink', text: m })),
      (st) => (st === 3 ? {} : { o: 0, k: 0.5 }), { delay: (st) => (st === 3 ? 950 + stagger(k, 90) : 0) })
    })
    add(s('text', { x: 562, y: 372, 'text-anchor': 'middle', class: 'ink', text: '3 моделі' }), only(3), { delay: (st) => (st === 3 ? 950 : 0) })

    // Step 5: five caught mistakes, each bug struck out and checked off.
    MISTAKES.forEach((m, i) => {
      const cy = 52 + i * 72
      const d = stagger(i, 160)
      add(s('g', {}, s('g', { transform: `translate(214 ${cy})` },
        s('ellipse', { rx: 11, ry: 14, class: 'iline' }),
        s('path', { d: 'M-11-5h-8M-11 5h-8M11-5h8M11 5h8M-5-13l-4-6M5-13l4-6', class: 'iline' }))),
      only(4), { delay: (st) => (st === 4 ? d : 0) })
      add(s('g', {}, s('g', { transform: `translate(214 ${cy}) rotate(-45)` }, s('rect', { x: -24, y: -2, width: 48, height: 4, rx: 2, class: 'pinkf' }))),
        (st) => (st === 4 ? {} : { o: 0, kx: 0 }), { delay: (st) => (st === 4 ? d + 350 : 0), origin: 'left' })
      add(s('text', { x: 246, y: cy + 8, class: 'ink', text: m }), only(4), { delay: (st) => (st === 4 ? d + 60 : 0) })
      add(s('g', {}, s('g', { transform: `translate(596 ${cy})` },
        s('circle', { r: 16, class: 'pinkf' }), s('path', { d: 'M-7 1l5 5 9-10', class: 'wline' }))),
      (st) => (st === 4 ? {} : { o: 0, k: 0.3 }), { delay: (st) => (st === 4 ? d + 450 : 0) })
    })

    apply(-1, true)
    return {
      show(step, { instant = false } = {}) {
        if (!instant) svg.getBoundingClientRect()
        apply(step, instant)
      },
      destroy() {},
    }
  },
}
