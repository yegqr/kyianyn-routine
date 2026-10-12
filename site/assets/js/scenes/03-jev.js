// Scene 3 of the methodology deck: how the language model Jev reads posts and how code turns its answers into hour flags.
// Contract: ./README.md. Numbers: docs/data/JEV.md (section Приклад), docs/data/silver/kyiv_threat_hourly.md (section
// Правило години), docs/quiet/model.md section 2 (the drone label read by hand). The post: data/bronze/telegram/truexakyiv.jsonl.
import { h, s, canvas, put, stagger } from '../how.js'

const CSS = `
.scene-jev .ink { fill: var(--ink); }
.scene-jev .soft { fill: var(--soft); }
.scene-jev .pink { fill: var(--pink); }
.scene-jev .on-pink { fill: var(--card); }
.scene-jev .card { fill: var(--card); stroke: var(--line); stroke-width: 2; }
.scene-jev .chip { fill: var(--card); stroke: var(--pink); stroke-width: 2; }
.scene-jev .fill-pink { fill: var(--pink); }
.scene-jev .fill-soft { fill: var(--pink-soft); }
.scene-jev .fill-ink { fill: var(--ink); }
.scene-jev .hollow { fill: var(--card); stroke: var(--soft); stroke-width: 2; }
.scene-jev .wire { fill: none; stroke: var(--line); stroke-width: 3; }
.scene-jev .disp { font-family: var(--font-display); }
.scene-jev.tip { position: fixed; z-index: 20; display: none; max-width: 280px; padding: 6px 10px; border-radius: var(--r-small);
  background: var(--ink); color: var(--card); font: 500 14px/1.35 var(--font); pointer-events: none; }
`

// Jev answers for the posts of the strike of 2026-10-07 (docs/data/JEV.md, Приклад) and the thresholds of the hour rule
// (docs/data/silver/kyiv_threat_hourly.md: a strike post needs p >= 0.7, the other flags one post with p >= 0.8).
const ROWS = [
  { q: 'удар?', p: 0.89, thr: 0.7 },
  { q: 'загроза?', p: 0.97, thr: 0.8 },
  { q: 'дрони?', p: 0.13, thr: 0.8 },
]
const Y = [105, 195, 285]
const READ = { hours: 25, right: 20 } // docs/quiet/model.md section 2: 20 of 25 drone hours read by hand were right

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

// Sources go into a folded block at the end of the note; file paths and code names live only there
const SRC = (text) => `<details class="how-src"><summary>Джерела</summary><p>${text}</p></details>`

const QUESTIONS = `Post "{pid}" (a post without a place name from a Kyiv channel is about the city of Kyiv; war_monitor covers all of Ukraine).

"strike": Does this post report that missiles caused explosions, a shoot-down, falling debris or a hit in the city of Kyiv? Earlier posts of the state only show the weapon type.
"threat": Does this post warn that missiles are flying toward the city of Kyiv or that the city of Kyiv is under a missile threat?
"drone": Does this post say that drones are flying toward or over the city of Kyiv, or exploding there?
"ballistic": Does this post say that ballistic missiles are heading to the city of Kyiv?`

// The questions belong to step 2, where they are asked. The verbatim text is cut in two before the "threat" question, so each
// card fits without its own scroll on a 390 px phone (a scrolled code box reads as an overlap to the layout check)
const CUT = QUESTIONS.indexOf('\n"threat"')
const ASKED = [
  { title: 'Питання до Jev: вступ і удар', text: QUESTIONS.slice(0, CUT), source: 'програма розмітки постів, дослівно' },
  { title: 'Питання до Jev: загроза, дрони, балістика', text: QUESTIONS.slice(CUT + 1), source: 'програма розмітки постів, дослівно' },
]

export default {
  id: 'jev',
  title: 'Як Jev читає пости',
  lead: 'Мовна модель Jev відповідає на точні питання про кожен пост числом від 0 до 1, а мітку години ставить програма.',
  steps: [
    {
      note: '<p>Ніч на 7 жовтня 2026, 03:14. Київський канал truexakyiv пише одне слово: «Гучно!». Про цей удар пишуть ще 4 канали, серед них КМВА і Віталій Кличко.</p>'
        + SRC('docs/data/JEV.md, розділ «Приклад»: пости kyiv_airdef, VA_Kyiv, truexakyiv, war_monitor і Кличка; пост з data/bronze/telegram/truexakyiv.jsonl.'),
    },
    {
      note: '<p>Програма ставить Jev англійською однакові питання про кожен пост: чи був ракетний удар по Києву, чи є ракетна загроза, чи летять дрони, чи летить балістика. Кожне питання перевіряє одну річ, складне ділимо на прості: це правило 2 з картки. На схемі три питання з чотирьох.</p>'
        + SRC('Питання дослівно: src/airalerts/silver/threat_hourly.py; правила: docs/data/JEV.md.'),
      prompts: [...ASKED, { title: 'Правило питань 2 з 8', text: '2. Одне судження на питання. Складне ділимо на кілька простих і поєднуємо в коді.', source: 'правила питань до Jev' }],
    },
    {
      note: '<p>Jev відповідає не словами, а ймовірністю «так» від 0 до 1: 0.97 означає майже напевно так, 0.13 майже напевно ні. Для постів цього удару: ракетний удар <span class="num">0.89</span>, ракетна загроза <span class="num">0.97</span>, дрони <span class="num">0.13</span>.</p>'
        + SRC('docs/data/JEV.md, розділ «Приклад», перевірено 10.10.2026.'),
      prompts: [{ title: 'Правило питань 8 з 8', text: '8. Поріг для noul за замовчуванням 0.5. У silver зберігаємо самі ймовірності, а не лише 0 чи 1.', source: 'правила питань до Jev' }],
    },
    {
      note: '<p>Мітку години (так чи ні: удар, загроза, дрони) ставить програма, а не Jev. Удар: оригінальний, не пересланий пост після ракетної тривоги з ймовірністю від 0.7; загроза і дрони: пост від 0.8 або пост офіційного каналу від 0.5. Тож приклад дає удар і загрозу, але не дрони, і в таблиці міток година 03:00 7 жовтня справді має мітку удару.</p>'
        + SRC('docs/data/silver/kyiv_threat_hourly.md, розділ «Правило години»; 03:00 за Києвом це 00:00 UTC.'),
      prompts: [{
        title: 'Правило години',
        text: 'Година `missile_strike` = true, коли є хоч один пост-доказ: оригінальний пост (`originals`), що йде після ракетної тривоги (`fresh`) і має `p_strike` >= 0.7 ...\n...\nГодина true, коли є пост з ймовірністю >= 0.8 (`one`), або пост офіційного каналу (VA_Kyiv, vitaliy_klitschko) >= 0.5 (`official`), або ...',
        source: 'опис таблиці міток, розділ «Правило години»',
      }],
    },
    {
      note: '<p>Чи можна вірити мітці? Агент штучного інтелекту перечитав пости 25 годин з міткою дронів на навчальних даних: правильні 20, тобто <span class="num">80%</span>, хибні здебільшого звіти про наслідки і дрони в області без тривоги в Києві. Хвилі ударних дронів, що злетіли чи летять зараз, Jev перевіряє окремим питанням з картки.</p>'
        + SRC('docs/quiet/model.md, розділ 2; питання про хвилю дронів (сигнал S4, drone_launch): src/airalerts/silver/signals.py.'),
      prompts: [{
        title: 'Питання про хвилю дронів',
        text: 'Does post {pid} report attack drones (Shahed, Geran, jet drones, mopeds) that were launched or are flying now, one drone or many?',
        source: 'програма сигналів підготовки, дослівно',
      }],
    },
  ],
  prompts: [],

  mount(stage) {
    stage.append(h('style', { text: CSS }))
    const svg = canvas(stage, 'Пост «Гучно!» стає питаннями до Jev, ймовірностями і прапорцями години')
    svg.classList.add('scene-jev')
    const d = director()
    const add = (node) => svg.appendChild(node)

    // step 1: the post «Гучно!» on top of the other posts of the attack
    const post = add(s('g', {},
      [3, 2, 1].map((i) => s('rect', { x: 30 - 6 * i, y: 120 + 6 * i, width: 200, height: 150, rx: 16, class: 'card' })),
      s('rect', { x: 30, y: 120, width: 200, height: 150, rx: 16, class: 'card' }),
      T(44, 154, 'truexakyiv', 'soft'),
      T(44, 214, 'Гучно!', 'ink', 40, { 'font-weight': 700 }),
      T(44, 252, '03:14', 'soft')))
    d.add(post, (k) => (k < 0 ? { o: 0, x: 199, y: -9, k: 1.1 }
      : k === 0 ? { x: 199, y: -9, k: 1.25 }
        : k <= 2 ? {} : { o: 0, k: 0.92 }), { dur: 400 })
    d.add(add(s('g', {},
      s('rect', { x: 205, y: 318, width: 230, height: 46, rx: 23, class: 'chip' }),
      T(320, 348, 'пости 5 каналів', 'ink', 22, { 'text-anchor': 'middle' }))),
    (k) => (k === 0 ? {} : { o: 0, y: 10 }), { delay: (k) => (k === 0 ? 300 : 0) })

    // step 4: the hour the posts belong to
    d.add(add(s('g', {},
      s('rect', { x: 30, y: 120, width: 200, height: 150, rx: 16, class: 'card' }),
      T(44, 154, 'година', 'soft'),
      T(44, 214, '03:00', 'ink', 40, { 'font-weight': 700 }),
      T(44, 252, 'за Києвом', 'soft'))),
    (k) => (k === 3 ? {} : { o: 0, k: 1.08 }), { delay: (k) => (k === 3 ? 150 : 0) })

    // steps 2 to 4: a question per row, its probability, the threshold and the flag
    ROWS.forEach((r, i) => {
      const y = Y[i]
      const flag = r.p >= r.thr
      d.add(add(s('path', { d: `M230 195 C 244 195 242 ${y} 256 ${y}`, class: 'wire' })),
        (k) => (k >= 1 && k <= 3 ? {} : { o: 0 }), { delay: (k) => (k === 1 ? stagger(i, 90, 200) : 0) })
      d.add(add(s('g', {},
        s('rect', { x: 256, y: y - 24, width: 140, height: 48, rx: 24, class: 'chip' }),
        T(326, y + 8, r.q, 'ink', 22, { 'text-anchor': 'middle' }))),
      (k) => (k < 1 || k > 3 ? { o: 0, x: -16 } : k === 3 && !flag ? { o: 0.45 } : {}),
      { delay: (k) => (k === 1 ? stagger(i, 90, 200) : 0) })
      d.add(add(s('g', {},
        s('rect', { x: 256, y: y - 24, width: 140, height: 48, rx: 24, class: 'fill-pink' }),
        T(326, y + 8, r.q, 'on-pink', 22, { 'text-anchor': 'middle', 'font-weight': 600 }))),
      (k) => (k === 3 && flag ? {} : { o: 0 }), { delay: (k) => (k === 3 ? stagger(i, 120, 450) : 0) })
      d.add(add(s('rect', { x: 408, y: y - 12, width: 160, height: 24, rx: 4, class: 'fill-soft' })),
        (k) => (k === 2 || k === 3 ? {} : { o: 0 }))
      d.add(add(s('rect', { x: 408, y: y - 12, width: 160 * r.p, height: 24, rx: 4, class: 'fill-pink' })),
        (k) => (k < 2 || k > 3 ? { o: 0, kx: 0 } : k === 3 && !flag ? { o: 0.35 } : {}),
        { origin: 'left center', dur: 400, delay: (k) => (k === 2 ? stagger(i, 120, 100) : 0) })
      d.add(add(T(576, y + 8, r.p.toFixed(2), 'ink', 22, { 'font-weight': 600 })),
        (k) => (k === 2 || k === 3 ? {} : { o: 0 }), { delay: (k) => (k === 2 ? stagger(i, 120, 380) : 0) })
      const tx = 408 + 160 * r.thr
      d.add(add(s('g', {},
        s('rect', { x: tx - 2, y: y - 20, width: 4, height: 40, rx: 2, class: 'fill-ink' }),
        T(tx, y - 28, String(r.thr), 'ink', 22, { 'text-anchor': 'middle' }))),
      (k) => (k === 3 ? {} : { o: 0, y: -8 }), { delay: (k) => (k === 3 ? stagger(i, 90, 100) : 0) })
    })

    // step 5: 25 drone hours read by hand, 20 right
    const pct = Math.round((100 * READ.right) / READ.hours)
    d.add(add(s('g', {},
      T(40, 170, `${pct}%`, 'pink disp', 60, { 'font-weight': 800 }),
      T(40, 222, 'мітка дронів', 'ink', 24),
      T(40, 254, 'правильна', 'ink', 24),
      T(40, 300, `${READ.right} з ${READ.hours} годин`, 'soft'))),
    (k) => (k === 4 ? {} : { o: 0, y: 12 }), { delay: (k) => (k === 4 ? 150 : 0) })
    for (let i = 0; i < READ.hours; i++) {
      const sq = add(s('rect', {
        x: 360 + (i % 5) * 50, y: 64 + Math.floor(i / 5) * 50, width: 40, height: 40, rx: 6,
        class: i < READ.right ? 'fill-pink' : 'hollow',
      }))
      d.add(sq, (k) => (k === 4 ? {} : { o: 0, k: 0.6 }), { dur: 240, delay: (k) => (k === 4 ? stagger(i, 24, 200) : 0) })
    }
    d.add(add(s('g', {},
      s('rect', { x: 360, y: 330, width: 20, height: 20, rx: 4, class: 'fill-pink' }),
      T(388, 347, 'правильні'),
      s('rect', { x: 516, y: 330, width: 20, height: 20, rx: 4, class: 'hollow' }),
      T(544, 347, 'хибні'))),
    (k) => (k === 4 ? {} : { o: 0 }), { delay: (k) => (k === 4 ? 800 : 0) })

    // Tooltip: what is under the pointer at the current step (hover, or tap on a phone)
    let cur = -1
    const tip = h('div', { class: 'scene-jev tip', role: 'tooltip' })
    stage.append(tip)
    const hide = () => { tip.style.display = 'none' }
    const NAMES = ['Ракетний удар по Києву', 'Ракетна загроза Києву', 'Дрони на Київ']
    const ASK = ['чи був ракетний удар по Києву: вибухи, збиття, уламки?', 'чи летять ракети на Київ?', 'чи летять дрони на Київ або над ним?']
    function describe(x, y) {
      const i = Y.reduce((b, c, k) => (Math.abs(y - c) < Math.abs(y - Y[b]) ? k : b), 0)
      const r = ROWS[i]
      const p = r.p.toFixed(2)
      if (cur === 0) return y > 305 ? 'Про цей удар пишуть 5 каналів, серед них КМВА і Віталій Кличко' : 'Пост каналу truexakyiv о 03:14 за Києвом, ніч на 7 жовтня 2026'
      if (cur === 4) return x > 340 ? 'Квадрат це година з міткою дронів: заповнений правильна, порожній хибна' : 'Агент перечитав пости 25 годин з міткою дронів: правильні 20'
      if (x < 240) return cur === 3 ? 'Година 03:00 за Києвом, 7 жовтня 2026: їй програма ставить мітки' : 'Пост «Гучно!»: Jev відповідає на питання про нього'
      if (cur === 1) return `Питання до Jev: ${ASK[i]}`
      if (cur === 2) return `${NAMES[i]}: Jev каже «так» з ймовірністю ${p}`
      return r.p >= r.thr ? `${NAMES[i]}: ${p} не нижче порога ${r.thr}, мітка є` : `${NAMES[i]}: ${p} нижче порога ${r.thr}, мітки немає`
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

    d.apply(-1, true)
    svg.getBoundingClientRect()
    return {
      show(step, { instant } = {}) {
        cur = step
        hide()
        d.apply(step, instant)
      },
      destroy() {
        for (const ev of EVENTS) svg.removeEventListener(ev, say)
        svg.removeEventListener('mouseleave', hide)
        tip.remove()
      },
    }
  },
}
