// Scene 1 of the methodology deck: why the site asks "will you cross the river in the next 3 hours".
// Crossing facts: docs/product/crossing.md, checked 2026-10-12: the eight bridges over the main stream of the Dnipro from north
// to south, the KMVA car rules of 03.10 for any alert, M1 off the river in any alert, M3 on it at yellow and off it at red.
// The tier thresholds are read at runtime from api/model.json (busy_at, high_at), now.json is the fallback; the rule that found
// them: docs/quiet/forecast.md and docs/METHODOLOGY.md 4.4, scene 8 draws it.
// The test shares of step 4 (17%, 5 of 29; 74%): docs/quiet/forecast.md, table 3, an official alert in the next 3 hours.
// Colours: the metro lines in their official colours (--m1, --m2, --m3), states in status colours
// (--go open, --risk limited, --stop closed), pink only for the brand accents: the river and the 3 hour window.
import { h, s, canvas, put, stagger } from '../how.js'
import { pct } from '../api.js'

const ID = 'question'
const LEFT = 'left center'
const TOP = 'center top'

const CSS = `
.scene-question text { font-family: var(--font); font-size: 22px; fill: var(--ink); }
.scene-question .lbl { font-size: 19px; }
.scene-question .name { font-size: 18px; fill: var(--body); }
.scene-question .soft { fill: var(--soft); }
.scene-question .bold { font-weight: 600; }
.scene-question .on-dark { fill: var(--card); font-weight: 600; }
.scene-question .river { fill: var(--pink-soft); }
.scene-question .island { fill: var(--card); }
.scene-question .deck, .scene-question .band, .scene-question .rail { fill: none; stroke: var(--soft); }
.scene-question .deck { stroke-opacity: .45; stroke-width: 10; }
.scene-question .band { stroke-opacity: .3; stroke-width: 22; }
.scene-question .rail { stroke-width: 4; stroke-dasharray: 8 5; }
.scene-question .on-go { stroke: var(--go); stroke-opacity: .8; }
.scene-question .on-amber { stroke: var(--risk-fill); stroke-opacity: 1; }
.scene-question .line { fill: none; stroke-width: 8; stroke-linecap: round; }
.scene-question .far { stroke-opacity: .4; }
.scene-question .m1 { stroke: var(--m1); }
.scene-question .m2 { stroke: var(--m2); }
.scene-question .m3 { stroke: var(--m3); }
.scene-question .station { fill: var(--card); stroke-width: 3; }
.scene-question .hub { fill: var(--card); stroke: var(--m2); stroke-width: 3; }
.scene-question .fill-m1 { fill: var(--m1); }
.scene-question .fill-m2 { fill: var(--m2); }
.scene-question .fill-m3 { fill: var(--m3); }
.scene-question .pill-yellow { fill: var(--risk-soft); stroke: var(--risk-fill); stroke-width: 2; }
.scene-question .pill-red { fill: var(--stop); }
.scene-question .risk-text { fill: var(--risk); font-weight: 600; }
.scene-question .q-train { fill: var(--card); stroke: var(--ink); stroke-width: 2.5; }
.scene-question .stop circle { fill: var(--card); stroke: var(--stop); stroke-width: 3; }
.scene-question .stop path { fill: none; stroke: var(--stop); stroke-width: 3; stroke-linecap: round; }
.scene-question .cell { fill: var(--pink-soft); stroke: var(--pink); stroke-width: 2; }
.scene-question .tick { fill: none; stroke: var(--ink); stroke-width: 2; }
.scene-question .lead { fill: none; stroke: var(--soft); stroke-width: 1.5; }
.scene-question .bar-none { fill: var(--pink-soft); }
.scene-question .bar-0 { fill: var(--go); }
.scene-question .bar-1 { fill: var(--risk-fill); }
.scene-question .bar-2 { fill: var(--stop); }
.scene-question .pill-0 { fill: var(--go-soft); stroke: var(--go); stroke-width: 2; }
.scene-question .pill-1 { fill: var(--risk-soft); stroke: var(--risk-fill); stroke-width: 2; }
.scene-question .pill-2 { fill: var(--stop-soft); stroke: var(--stop); stroke-width: 2; }
.scene-question .txt-0 { fill: var(--go); font-weight: 600; }
.scene-question .txt-1 { fill: var(--risk); font-weight: 600; }
.scene-question .txt-2 { fill: var(--stop); font-weight: 600; }
.scene-question.tip { position: fixed; z-index: 20; display: none; max-width: 280px; padding: 6px 10px; border-radius: var(--r-small);
  background: var(--ink); color: var(--card); font: 500 14px/1.35 var(--font); pointer-events: none; }
`

const RIVER = 'M266 0C258 120 274 250 262 400L400 400C390 250 406 120 396 0Z'
// Гідропарк stands on an island: M1 crosses the main stream by міст Метро, then the Русанівська протока
const ISLAND = { x: 358, y: 156, width: 26, height: 40, rx: 12 }
const XW = 252 // a bridge runs from the right bank (x 252) to the left bank (x 408)
const XE = 408
const Y1 = 176 // the M1 row: міст Метро
const Y3 = 326 // the M3 row: Південний міст
// The blue line M2 runs north to south on the right bank only: it meets M1 and M3 at transfers and never crosses the river
const M2X = 72

// The bridges over the main stream, north to south. kind: deck (cars), rail (trains only), band (metro with cars beside it).
// st: cars in any alert by the KMVA rule of 03.10, go no limits, amber 15 minutes; a rail bridge has no city rule.
// tips: no alert, any alert (and red, when it differs); at: the name's place when the left bank row is taken by a metro line;
// tag: the 15 minute sign at the right bank end, «15 хв» and which way.
const UZ = 'на час загрози поїзди може зупинити Укрзалізниця'
const SOUTH = 'Південний міст: з правого берега на лівий рух авто обмежують 15 хв від оголошення тривоги, з лівого на правий без обмежень'
const BRIDGES = [
  { y: 70, name: 'Північний', kind: 'deck', st: 'go',
    tips: ['Північний міст: авто, ходять тролейбуси', 'Північний міст: під час тривоги авто без обмежень'] },
  { y: 100, name: 'Рибальський', kind: 'rail',
    tips: ['Рибальський залізничний міст: лише поїзди, ним їде міська електричка від Почайни до Райдужного',
      `Рибальський залізничний міст: лише поїзди, ${UZ}`] },
  { y: 130, name: 'Подільський', kind: 'deck', st: 'amber', tag: [116, 'в обидва боки'],
    tips: ['Подільсько-Воскресенський міст: авто, з Подолу через Труханів острів',
      'Подільсько-Воскресенський міст: авто в обидва боки стоять 15 хв після оголошення тривоги і 15 хв після відбою'] },
  { y: Y1, name: 'міст Метро', kind: 'band', st: 'go', at: [XE + 6, Y1 - 15],
    tips: ['Міст Метро: червона M1 і авто, від станції Дніпро до Гідропарку',
      'Міст Метро: авто без обмежень, а M1 за будь-якої тривоги мостом не їде'] },
  { y: 222, name: 'Патона', kind: 'deck', st: 'go',
    tips: ['Міст Патона: авто', 'Міст Патона: під час тривоги авто без обмежень'] },
  { y: 254, name: 'Дарницький', kind: 'deck', st: 'go',
    tips: ['Дарницький залізнично-автомобільний міст: авто і поїзди',
      'Дарницький залізнично-автомобільний міст: під час тривоги авто без обмежень'] },
  { y: 276, name: 'Дарницький залізничний', kind: 'rail',
    tips: ['Дарницький залізничний міст: лише поїзди, стоїть поруч із Дарницьким', `Дарницький залізничний міст: лише поїзди, ${UZ}`] },
  { y: Y3, name: 'Південний', kind: 'band', st: 'amber', at: [330, Y3 - 18, 'middle'], tag: [290, 'на лівий берег'],
    tips: ['Південний міст: зелена M3 і авто; з 06.10 у піки на мосту по одному поїзду, чи діє це зараз, не підтверджено',
      `${SOUTH}; M3 за жовтого рівня мостом їде`, `${SOUTH}; M3 за червоного рівня мостом не їде`] },
]

// Every station of the drawn part, west to east: [x, name, where, in an alert]. Further west the lines run under the ground,
// drawn faded and without stations.
const M1_OUT = 'за будь-якої тривоги поїзди сюди не їдуть, замість них наземний транспорт'
const M1_ST = [
  [190, 'Арсенальна', 'правий берег, під землею', 'за будь-якої тривоги поїзди їдуть лише до неї'],
  [254, 'Дніпро', 'правий берег, звідси мостом Метро через річку'],
  [371, 'Гідропарк', 'на острові посеред Дніпра'],
  [414, 'Лівобережна', 'лівий берег, за Русанівською протокою'],
  [474, 'Дарниця', 'лівий берег'],
  [534, 'Чернігівська', 'лівий берег'],
  [594, 'Лісова', 'кінцева на лівому березі'],
]
const M3_RED = 'за червоного рівня їде ділянка Осокорки - Червоний хутір'
const M3_ST = [
  [254, 'Видубичі', 'правий берег, звідси Південним мостом через річку', 'за червоного рівня тут кінець ділянки Сирець - Видубичі'],
  [414, 'Славутич', 'лівий берег, перша станція за мостом', 'за червоного рівня поїзди сюди не їдуть'],
  [450, 'Осокорки', 'лівий берег', 'за червоного рівня звідси ходить ділянка Осокорки - Червоний хутір'],
  [486, 'Позняки', 'лівий берег'],
  [522, 'Харківська', 'лівий берег'],
  [558, 'Вирлиця', 'лівий берег'],
  [594, 'Бориспільська', 'лівий берег'],
  [630, 'Червоний хутір', 'кінцева на лівому березі'],
]
const SPOTS = [
  ...M1_ST.map(([x, name, where, alert = M1_OUT]) => ({ x, y: Y1, tips: [`${name}, M1: ${where}`, `${name}, M1: ${alert}`] })),
  ...M3_ST.map(([x, name, where, red = M3_RED]) => ({ x, y: Y3, tips: [`${name}, M3: ${where}`, `${name}, M3: ${where}`, `${name}, M3: ${red}`] })),
  { x: M2X, y: Y1, tips: ['Пересадка між M1 і M2'] },
  { x: M2X, y: Y3, tips: ['Пересадка між M3 і M2'] },
]

// Where a tap shows what, after the stations: each bridge (deck, name, 15 minute sign), the lines, M2, the legend
const AREAS = [
  ...BRIDGES.map((b) => {
    const half = b.kind === 'band' ? 13 : 11
    return { x0: 244, x1: b.at ? XE : 640, y0: b.y - half, y1: b.y + half, tips: b.tips }
  }),
  ...BRIDGES.filter((b) => b.at).map(({ at: [x, y, anchor], tips }) => ({
    x0: anchor ? x - 50 : x - 4, x1: anchor ? x + 50 : x + 100, y0: y - 16, y1: y + 5, tips })),
  ...BRIDGES.filter((b) => b.tag).map(({ tag: [y], tips }) => ({ x0: 100, x1: 250, y0: y - 16, y1: y + 26, tips: [null, ...tips.slice(1)] })),
  { x0: M2X - 14, x1: M2X + 14, y0: 40, y1: 366, tips: ['M2, синя лінія: лише правий берег, через Дніпро не йде; з нею є пересадки на M1 і M3'] },
  { x0: 0, x1: 190, y0: Y1 - 14, y1: Y1 + 14,
    tips: ['M1 далі під землею на захід, до Академмістечка: ці станції тут не показано',
      'M1 далі під землею на захід, до Академмістечка: тут поїзди ходять і під час тривоги'] },
  { x0: 190, x1: 640, y0: Y1 - 14, y1: Y1 + 14,
    tips: ['M1, червона лінія: мостом Метро через Дніпро, далі лівим берегом до Лісової',
      'M1 за будь-якої тривоги: лише під землею, від Академмістечка до Арсенальної; від Дніпра до Лісової поїзди не їдуть'] },
  { x0: 0, x1: 254, y0: Y3 - 14, y1: Y3 + 14,
    tips: ['M3 далі під землею, до Сирця: ці станції тут не показано', 'M3 далі під землею, до Сирця: ці станції тут не показано',
      'M3 далі під землею, до Сирця: за червоного рівня тут ходить ділянка Сирець - Видубичі'] },
  { x0: 254, x1: 640, y0: Y3 - 14, y1: Y3 + 14,
    tips: ['M3, зелена лінія: Південним мостом через Дніпро, далі лівим берегом до Червоного хутора',
      'M3 за жовтого рівня: Південним мостом через Дніпро, далі лівим берегом до Червоного хутора',
      'M3 за червоного рівня: Сирець - Видубичі і Осокорки - Червоний хутір, через Дніпро не їде'] },
  { x0: 0, x1: 640, y0: 368, y1: 400,
    tips: ['Суцільний міст: для авто; пунктир: лише поїзди',
      'Під час тривоги: зелений міст для авто без обмежень; жовтогарячий з підписом «15 хв»: рух там стоїть або обмежений 15 хв; пунктир: лише поїзди'] },
]
const MAP_TIPS = [
  'Схема Києва: правий берег ліворуч, лівий праворуч, північ угорі',
  'Жовтий рівень, наліт дронів: M1 лише під землею, M3 їде мостом',
  'Червоний рівень, ракетна небезпека або масована атака: метро через Дніпро не їде',
]
const TIERS = ['низький ризик', 'середній ризик', 'високий ризик']
const X0 = 60
const X1 = 580
const PILL_W = 190
const PILL_X = [20, 225, 430]

const T = (x, y, text, cls = '', anchor) => s('text', { x, y, class: cls, 'text-anchor': anchor, text })
const fmt = (p) => pct(p, 1).replace('.0%', '%')
const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null)

const badge = (y, label, cls, cx) => s('g', {},
  s('rect', { x: cx - 23, y: y - 16, width: 46, height: 32, rx: 16, class: cls }), T(cx, y + 8, label, 'on-dark', 'middle'))
const levelPill = (label, cls, tcls) => s('g', {},
  s('rect', { x: 200, y: 6, width: 240, height: 40, rx: 20, class: cls }), T(320, 34, label, tcls, 'middle'))
const train = (cx, cy) => s('rect', { x: cx - 16, y: cy - 8, width: 32, height: 16, rx: 8, class: 'q-train' }) // not .train: the answer tab styles that class
const stop = (cx, cy) => s('g', { class: 'stop' },
  s('circle', { cx, cy, r: 14 }), s('path', { d: `M${cx - 9} ${cy - 9}L${cx + 9} ${cy + 9}` }))
const dot = (x, y, cls, r = 5) => s('circle', { cx: x, cy: y, r, class: `station ${cls}` })
const deck = (b, cls) => s('path', { d: `M${XW} ${b.y}H${XE}`, class: cls })
const tag = ([y, way]) => s('g', {}, T(246, y, '15 хв', 'lbl risk-text', 'end'), T(246, y + 20, way, 'lbl soft', 'end'))
const legItem = (x, cls, label) => s('g', {}, s('path', { d: `M${x} 384H${x + 24}`, class: cls }), T(x + 32, 390, label, 'lbl'))

let TH = null // thresholds of the last mount, used by the note of step 4

// The stage pills show the three ranges, so the note says only where the two limits come from
const TRAIN = 'на навчальних даних (01.05 - 29.08, на них модель вчилась)'
function thresholds() {
  if (!TH) return `Межі ризику зараз не завантажились; їх не обирали руками, а дало правило ${TRAIN}.`
  return `Межі ризику не обирали руками: ${TRAIN} правило дало ${fmt(TH.busy)}, найвищу межу, що ловить 4 з 5 атак, і ${fmt(TH.high)}, початок верхньої третини прогнозів.`
}

// Sources go into a folded block at the end of the note; file paths and code names live only there
const SRC = (text) => `<details class="how-src"><summary>Джерела</summary><p>${text}</p></details>`

const IDEA = {
  title: 'Ідея автора',
  text: 'Чи встигну я переїхати з одного берега на інший. І для цього закладається три години з моменту виїзду.',
  source: 'із завдання автора, 11.10.2026',
}

const QUESTION = {
  title: 'Питання до моделі',
  text: 'На початку кожної години t: чи прилетять у Київ дрони або ракети (або буде ракетна загроза) протягом наступних 3 годин, тобто в години t, t + 1, t + 2? Відповідь: ймовірність, вердикт «швидше тихо» чи «неспокійно» з рівнем ризику, і 3 головні причини.',
  source: 'опис моделі, розділ 1',
}

export default {
  id: ID,
  title: 'Чи встигнеш переїхати на інший берег?',
  lead: 'Під час тривоги метро через Дніпро ходить менше або стоїть, тому ми прогнозуємо атаку на 3 години вперед.',
  steps: [
    {
      note: '<p>Київ стоїть на двох берегах Дніпра, з берега на берег ведуть вісім мостів: шість для авто і два лише для поїздів. Червона M1 перетинає річку мостом Метро, зелена M3 Південним мостом, а синя M2 лишається на правому березі. Точками показано всі станції від Арсенальної до Лісової і від Видубичів до Червоного хутора: торкнись точки, щоб побачити назву.</p>'
        + SRC('Схема, не мапа: північ угорі, кольори ліній як у метро. Мости і станції: docs/product/crossing.md, розділи «Мости через головне русло Дніпра» і «Метро», звірено 12.10.2026; OpenStreetMap; Вікіпедія, «Мости Києва». Один поїзд на Південному мосту в піки: ZN.ua, 06.10.2026, чи діє зараз, не підтверджено.'),
    },
    {
      note: '<p>Тривога це офіційна повітряна тривога в Києві, жовтий рівень означає наліт дронів. За будь-якої тривоги червона M1 ходить лише під землею, від Академмістечка до Арсенальної; за жовтого зелена M3 їде Південним мостом. Мости для авто працюють без обмежень, крім двох: Подільсько-Воскресенський стоїть 15 хвилин в обидва боки після оголошення і після відбою, а на Південному 15 хвилин від оголошення обмежують рух з правого берега на лівий.</p>'
        + SRC('Рівні: КМВА, 02.09.2026. M1: КМДА через Знай.ua і DSnews, 17.09.2026. M3: LB.ua, 04.10.2026. Мости: КМВА і Укрінформ, 03.10.2026. Усе звірено 12.10.2026: docs/product/crossing.md.'),
    },
    {
      note: '<p>Червоний рівень означає ракетну небезпеку або масовану атаку: найкраще в укриття. Метро через Дніпро не їде, зелена M3 ходить двома ділянками: Сирець - Видубичі і Осокорки - Червоний хутір. Мости для авто за тими ж правилами, що й за жовтого.</p>'
        + SRC('Рівні: КМВА, 02.09.2026; Kyiv.news, 03.09.2026. M3: LB.ua, 04.10.2026. Мости: КМВА через Укрінформ, 03.10.2026. Усе звірено 12.10.2026: docs/product/crossing.md.'),
    },
    {
      get note() {
        return `<p>Тому модель щогодини дає ймовірність атаки на Київ за 3 години: дрони, ракетна загроза або удар. ${thresholds()} На тестових даних (з 29.08, відкладені до кінця) тривога була після 17% прогнозів низького ризику і 74% високого.</p>`
          + SRC('Питання: docs/quiet/model.md, розділ 1. Межі: api/model.json (busy_at, high_at); правило: docs/quiet/forecast.md, docs/METHODOLOGY.md 4.4. Частки: docs/quiet/forecast.md, таблиця 3, там рівень низького ризику ще зветься «швидше тихо»; README.md.')
      },
      prompts: [QUESTION],
    },
  ],
  prompts: [IDEA],

  mount(stage, data) {
    stage.append(h('style', { text: CSS }))
    const svg = canvas(stage, 'Схема Києва: Дніпро і вісім мостів з півночі на південь, лінії метро M1 і M3 з усіма станціями біля річки, M2 лише на правому березі; далі шкала прогнозу на 3 години')
    svg.classList.add(`scene-${ID}`)

    const busy = num(data?.model?.busy_at) ?? num(data?.now?.forecast?.busy_at)
    const high = num(data?.model?.high_at) ?? num(data?.now?.forecast?.high_at)
    TH = busy != null && high != null && busy < high ? { busy, high } : null

    // Steps 1 to 3: the city from above
    const river = s('path', { d: RIVER, class: 'river' })
    const island = s('rect', { ...ISLAND, class: 'island' })
    const decks = BRIDGES.map((b) => deck(b, b.kind))
    // the cars in an alert: green or amber over the grey decks
    const overlays = BRIDGES.filter((b) => b.st).map((b) => deck(b, `${b.kind} on-${b.st}`))
    const names = s('g', {}, BRIDGES.map((b) => {
      const [x, y, anchor] = b.at ?? [XE + 6, b.y + 6]
      return T(x, y, b.name, 'name', anchor)
    }))
    const tags = BRIDGES.filter((b) => b.tag).map((b) => tag(b.tag))
    const banks = s('g', {}, T(16, 30, 'Правий берег', 'soft'), T(624, 30, 'Лівий берег', 'soft', 'end'))
    const riverName = T(331, 30, 'Дніпро', 'soft', 'middle')
    const m1Out = s('g', {}, s('path', { d: `M190 ${Y1}H594`, class: 'line m1' }),
      M1_ST.slice(1).map(([x], i, a) => dot(x, Y1, 'm1', i === a.length - 1 ? 7 : 5)))
    const m1Under = s('g', {}, s('path', { d: `M0 ${Y1}H190`, class: 'line m1 far' }), dot(190, Y1, 'm1'))
    const m3Bridge = s('g', {}, s('path', { d: `M254 ${Y3}H450`, class: 'line m3' }), dot(414, Y3, 'm3'))
    const m3East = s('g', {}, s('path', { d: `M450 ${Y3}H630`, class: 'line m3' }),
      M3_ST.slice(2).map(([x], i, a) => dot(x, Y3, 'm3', i === a.length - 1 ? 7 : 5)))
    const m3West = s('g', {}, s('path', { d: `M0 ${Y3}H254`, class: 'line m3 far' }), dot(254, Y3, 'm3'))
    const m2 = s('path', { d: `M${M2X} 74V362`, class: 'line m2' })
    const m2Hubs = s('g', {}, [Y1, Y3].map((cy) => s('circle', { cx: M2X, cy, r: 6, class: 'hub' })))
    const b1 = badge(Y1, 'M1', 'fill-m1', 28)
    const b2 = badge(58, 'M2', 'fill-m2', M2X)
    const b3 = badge(Y3, 'M3', 'fill-m3', 28)
    // the stations at both ends of each crossing and the line ends; the others are named in the tip
    const labels = s('g', {}, T(254, Y1 - 18, 'Дніпро', 'lbl', 'middle'), T(406, Y1 + 26, 'Лівобережна', 'lbl'),
      T(594, Y1 + 26, 'Лісова', 'lbl', 'middle'), T(250, Y3 + 26, 'Видубичі', 'lbl', 'end'),
      T(414, Y3 + 26, 'Славутич', 'lbl', 'middle'), T(636, Y3 + 26, 'Червоний хутір', 'lbl', 'end'))
    const lblA = T(190, Y1 + 26, 'Арсенальна', 'lbl', 'middle')
    const lblO = T(450, Y3 - 18, 'Осокорки', 'lbl', 'middle')
    const leg0 = s('g', {}, legItem(186, 'deck', 'для авто'), legItem(314, 'rail', 'лише поїзди'))
    const leg1 = s('g', {}, legItem(56, 'deck on-go', 'без обмежень'), legItem(233, 'deck on-amber', 'обмеження 15 хв'),
      legItem(443, 'rail', 'лише поїзди'))
    const t1 = train(300, Y1)
    const t3 = train(300, Y3)
    const stop1 = stop(300, Y1)
    const stop3 = stop(330, Y3)
    const map = s('g', {}, river, island, decks, overlays, banks, riverName, m2, m1Out, m1Under, m3Bridge, m3East, m3West,
      m2Hubs, b1, b2, b3, names, labels, lblA, lblO, tags, leg0, leg1, t1, t3, stop1, stop3)
    const yellow = levelPill('Жовтий рівень', 'pill-yellow', 'risk-text')
    const red = levelPill('Червоний рівень', 'pill-red', 'on-dark')

    // Step 4: the 3 hour window and the probability scale with the two thresholds
    const fq = T(320, 34, 'Чи буде атака в ці 3 години?', 'bold', 'middle')
    const fTicks = s('g', {},
      s('path', { d: 'M100 84V136', class: 'tick' }), T(100, 74, 'виїзд', 'soft', 'middle'),
      s('path', { d: 'M520 84V136', class: 'tick' }), T(520, 74, '04:00', 'soft', 'middle'))
    const fCells = ['01:00', '02:00', '03:00'].map((lab, i) => s('g', {},
      s('rect', { x: 102 + i * 140, y: 90, width: 136, height: 40, rx: 8, class: 'cell' }),
      T(170 + i * 140, 117, lab, '', 'middle')))
    const fCap = T(320, 168, 'ймовірність атаки', 'soft', 'middle')
    const xs = (TH ? [0, TH.busy, TH.high, 1] : [0, 1]).map((e) => X0 + (X1 - X0) * e)
    const fBar = s('g', {}, xs.slice(1).map((b, i) => s('rect', {
      x: xs[i] + 1, y: 202, width: Math.max(1, b - xs[i] - 2), height: 16, rx: 3, class: TH ? `bar-${i}` : 'bar-none',
    })))
    const fScale = s('g', {}, T(X0, 244, '0%', 'soft'), T(X1, 244, '100%', 'soft', 'end'),
      TH ? [
        s('path', { d: `M${xs[1]} 196V224`, class: 'tick' }), s('path', { d: `M${xs[2]} 196V224`, class: 'tick' }),
        T(xs[1] - 6, 192, fmt(TH.busy), 'bold', 'end'), T(xs[2] + 6, 192, fmt(TH.high), 'bold'),
      ] : null)
    const ranges = TH ? [`нижче ${fmt(TH.busy)}`, `від ${fmt(TH.busy)} до ${fmt(TH.high)}`, `від ${fmt(TH.high)}`] : []
    const fTier = TIERS.map((name, i) => {
      const cx = PILL_X[i] + PILL_W / 2
      return s('g', {},
        TH ? s('path', { d: `M${(xs[i] + xs[i + 1]) / 2} 224L${cx} 274`, class: 'lead' }) : null,
        s('rect', { x: PILL_X[i], y: 276, width: PILL_W, height: 40, rx: 20, class: `pill-${i}` }),
        T(cx, 303, name, `txt-${i}`, 'middle'),
        ranges[i] ? T(cx, 350, ranges[i], 'soft', 'middle') : null)
    })
    const fWhy = T(320, 388, 'межі дало правило на навчальних даних, розділ 8', 'lbl soft', 'middle')
    const fc = s('g', {}, fq, fTicks, fCells, fCap, fBar, fScale, fTier, fWhy)
    svg.append(map, yellow, red, fc)

    // Tooltip: what is under the pointer at the current step (hover, or tap on a phone)
    let cur = 0
    const tip = h('div', { class: `scene-${ID} tip`, role: 'tooltip' })
    stage.append(tip)
    const hide = () => { tip.style.display = 'none' }
    const pick = (tips) => tips[Math.min(cur, tips.length - 1)]
    function describe(x, y) {
      if (cur === 3) {
        if (y < 145) return 'Вікно прогнозу: 3 години від виїзду, наприклад з 01:00 до 04:00'
        if (y > 366) return 'Межі не обирали руками, їх дало правило на навчальних даних (01.05 - 29.08); розділ 8 показує це на графіку'
        if (TH && y > 172 && y < 199 && x > xs[1] - 70 && x < xs[1] + 8) {
          return `${fmt(TH.busy)}: найвища межа, вище якої на навчальних даних ще лишаються 4 з 5 атак`
        }
        if (TH && y > 172 && y < 199 && x > xs[2] - 8 && x < xs[2] + 50) {
          return `${fmt(TH.high)}: тут починається верхня третина всіх прогнозів на навчальних даних`
        }
        if (TH && y > 180 && y < 360) {
          const p = (x - X0) / (X1 - X0)
          const i = y < 260 ? (p < TH.busy ? 0 : p < TH.high ? 1 : 2) : x < 217 ? 0 : x < 422 ? 1 : 2
          return [`низький ризик: ймовірність нижче ${fmt(TH.busy)}`, `середній ризик: від ${fmt(TH.busy)} до ${fmt(TH.high)}`,
            `високий ризик: від ${fmt(TH.high)}`][i]
        }
        return 'Ймовірність атаки на Київ за 3 години: дрони летять на Київ, ракетна загроза або удар'
      }
      let best = null
      for (const p of SPOTS) {
        const d = Math.hypot(p.x - x, p.y - y)
        if (d < 18 && (!best || d < best.d)) best = { d, p }
      }
      if (best) return pick(best.p.tips)
      const area = AREAS.find((a) => x >= a.x0 && x <= a.x1 && y >= a.y0 && y <= a.y1 && pick(a.tips))
      return area ? pick(area.tips) : MAP_TIPS[cur]
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
    // only a mouse leaving hides the tip: a finger fires pointerleave, and then mouseleave, as soon as it lifts;
    // a scroll hides it too, the map moves away from under the tip
    const away = (e) => { if (e.pointerType === 'mouse') hide() }
    svg.addEventListener('pointerleave', away)
    window.addEventListener('scroll', hide, true)

    // Start state of every moving part, committed before the first show() so the first step animates in
    const PRE = [
      [river, { o: 0 }], [island, { o: 0 }], ...decks.map((n) => [n, { kx: 0 }, LEFT]), ...overlays.map((n) => [n, { o: 0 }]),
      [names, { o: 0 }], [banks, { o: 0 }], [riverName, { o: 0 }], [labels, { o: 0 }],
      [b1, { o: 0 }], [b2, { o: 0 }], [b3, { o: 0 }], [m2, { ky: 0 }, TOP], [m2Hubs, { o: 0 }],
      [m1Under, { kx: 0 }, LEFT], [m1Out, { kx: 0 }, LEFT], [m3West, { kx: 0 }, LEFT], [m3Bridge, { kx: 0 }, LEFT], [m3East, { kx: 0 }, LEFT],
      [t1, { o: 0, x: -24 }], [t3, { o: 0, x: -24 }], [stop1, { o: 0, k: 0.5 }], [stop3, { o: 0, k: 0.5 }],
      [lblA, { o: 0 }], [lblO, { o: 0 }], ...tags.map((n) => [n, { o: 0, x: 8 }]), [leg0, { o: 0 }], [leg1, { o: 0 }],
      [yellow, { o: 0, y: -6 }], [red, { o: 0, y: -6 }],
      [fc, { o: 0 }], [fq, { o: 0, y: 8 }], [fTicks, { o: 0 }], ...fCells.map((n) => [n, { o: 0, kx: 0.2 }, LEFT]),
      [fCap, { o: 0 }], [fBar, { kx: 0 }, LEFT], [fScale, { o: 0 }], ...fTier.map((n) => [n, { o: 0, y: 10 }]), [fWhy, { o: 0 }],
    ]
    for (const [n, st, origin] of PRE) put(n, st, { instant: true, origin })
    svg.getBoundingClientRect()

    function show(step, { instant = false } = {}) {
      cur = step
      hide()
      const A = (node, st, delay = 0, dur = 320, origin) => put(node, st, { delay, dur, origin, instant })
      const onMap = step < 3
      const alarm = step === 1 || step === 2
      A(map, { o: onMap ? 1 : 0, k: onMap ? 1 : 0.97 }, onMap ? 120 : 0, 360)
      A(river, { o: 1 }, 0, 400)
      A(island, { o: 1 }, 150)
      decks.forEach((n, i) => A(n, { kx: 1 }, stagger(i, 50, 150), 320, LEFT))
      A(names, { o: 1 }, 550)
      A(banks, { o: 1 }, 250)
      A(riverName, { o: step === 0 ? 1 : 0 }, step === 0 ? 350 : 0)
      A(b1, { o: 1 }, 400)
      A(b2, { o: 1 }, 400)
      A(b3, { o: 1 }, 400)
      A(m2, { ky: 1 }, 450, 400, TOP)
      A(m2Hubs, { o: 1 }, 850, 300)
      A(m1Under, { kx: 1 }, 450, 400, LEFT)
      A(m1Out, { kx: 1, o: step >= 1 ? 0.18 : 1 }, step >= 1 ? 250 : 650, 400, LEFT)
      A(m3West, { kx: 1 }, 450, 400, LEFT)
      A(m3Bridge, { kx: 1, o: step >= 2 ? 0.15 : 1 }, step >= 2 ? 250 : 650, 400, LEFT)
      A(m3East, { kx: 1 }, 850, 400, LEFT)
      A(labels, { o: 1 }, 950)
      // an alert colours the bridges for cars and brings the 15 minute signs and their legend
      overlays.forEach((n, i) => A(n, { o: alarm ? 1 : 0 }, alarm ? stagger(i, 70, 300) : 0, 300))
      tags.forEach((n, i) => A(n, { o: alarm ? 1 : 0, x: alarm ? 0 : 8 }, alarm ? stagger(i, 80, 700) : 0))
      A(leg0, { o: step === 0 ? 1 : 0 }, step === 0 ? 1100 : 0)
      A(leg1, { o: alarm ? 1 : 0 }, alarm ? 800 : 0)
      // a yellow alert sends the M1 train back under the ground, a red one sends the M3 train back too
      A(t1, { o: 1, x: step >= 1 ? -150 : 0 }, step >= 1 ? 0 : 1050, 400)
      A(t3, { o: 1, x: step === 0 ? 0 : step === 1 ? 50 : -130 }, step === 0 ? 1050 : 0, 400)
      A(stop1, { o: step >= 1 ? 1 : 0, k: step >= 1 ? 1 : 0.5 }, step >= 1 ? 380 : 0, 300)
      A(stop3, { o: step >= 2 ? 1 : 0, k: step >= 2 ? 1 : 0.5 }, step >= 2 ? 380 : 0, 300)
      A(lblA, { o: step >= 1 ? 1 : 0 }, step >= 1 ? 450 : 0)
      A(lblO, { o: step >= 2 ? 1 : 0 }, step >= 2 ? 450 : 0)
      A(yellow, { o: step === 1 ? 1 : 0, y: step === 1 ? 0 : -6 }, 0, 300)
      A(red, { o: step === 2 ? 1 : 0, y: step === 2 ? 0 : -6 }, 0, 300)

      const on = step === 3
      const d = (ms) => (on ? ms : 0)
      A(fc, { o: on ? 1 : 0 }, d(200), 300)
      A(fq, { o: on ? 1 : 0, y: on ? 0 : 8 }, d(250))
      A(fTicks, { o: on ? 1 : 0 }, d(400))
      fCells.forEach((n, i) => A(n, { o: on ? 1 : 0, kx: on ? 1 : 0.2 }, d(stagger(i, 160, 500)), 320, LEFT))
      A(fCap, { o: on ? 1 : 0 }, d(950))
      A(fBar, { kx: on ? 1 : 0 }, d(1000), 400, LEFT)
      A(fScale, { o: on ? 1 : 0 }, d(1300))
      fTier.forEach((n, i) => A(n, { o: on ? 1 : 0, y: on ? 0 : 10 }, d(stagger(i, 120, 1400))))
      A(fWhy, { o: on ? 1 : 0 }, d(1800))
    }

    return {
      show,
      destroy() {
        for (const ev of EVENTS) svg.removeEventListener(ev, say)
        svg.removeEventListener('pointerleave', away)
        window.removeEventListener('scroll', hide, true)
        tip.remove()
      },
    }
  },
}
