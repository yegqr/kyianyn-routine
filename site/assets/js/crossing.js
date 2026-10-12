// What crosses the Dnipro in Kyiv in each alert state, in three groups: the metro, the city rail ring and the bridges
// for cars. Checked 2026-10-12 from the posts of the city (КМВА), Укрзалізниця and the metro, and the media; sources
// and open questions: docs/product/crossing.md. Every item has [status, note] for each level, the status "open",
// "limited", "closed" or "unknown", and its rule during an alert in one line.

export const CHECKED = '2026-10-12'

export const LEVELS = {
  none: { name: 'Тривоги немає', short: 'тривоги немає' },
  yellow: { name: 'Жовтий рівень', short: 'загроза дронів' },
  red: { name: 'Червоний рівень', short: 'ракети або масована атака' },
  alert: { name: 'Тривога', short: 'рівень не названо' },
}

const OPEN = ['open', '']
const M1_UNDER = ['closed', 'лише під землею Академмістечко - Арсенальна']
const M3_GOES = ['open', 'у піки на мосту по одному поїзду, так повідомили 06.10']
const FIRST_15 = ['limited', 'перші 15 хв тривоги']
const NO_LIMIT = 'Тривога: рух без обмежень.'

const bridge = (id, name, alert, rule) => ({ id, kind: 'road', name, none: OPEN, yellow: alert, red: alert, alert, rule })

export const GROUPS = [
  {
    id: 'metro',
    title: 'Метро',
    items: [
      {
        id: 'm1', kind: 'metro', name: 'Червона лінія M1', via: 'мостом Метро',
        none: OPEN, yellow: M1_UNDER, red: M1_UNDER, alert: M1_UNDER,
        rule: 'Жовта і червона тривога: від Дніпра до Лісової не ходить, через річку замість неї наземний транспорт.',
      },
      {
        id: 'm3', kind: 'metro', name: 'Зелена лінія M3', via: 'Південним мостом',
        none: M3_GOES, yellow: M3_GOES,
        red: ['closed', 'окремо Сирець - Видубичі і Осокорки - Червоний хутір'],
        alert: ['unknown', 'рівень тривоги не названо, а за червоної не ходить'],
        rule: 'Жовта тривога: ходить. Червона: через Дніпро не ходить.',
      },
    ],
  },
  {
    id: 'rail',
    title: 'Міська електричка',
    items: [
      {
        id: 'rail', kind: 'rail', name: 'Почайна - Райдужний і Видубичі - Дарниця', via: 'кільце, Рибальським і Дарницьким мостами',
        none: OPEN,
        yellow: ['limited', 'за правилом ходить, але на час загрози кільце можуть зупинити'],
        red: ['closed', 'посадки і висадки немає'],
        alert: ['unknown', 'рівень тривоги не названо'],
        rule: 'Жовта тривога: ходить, червона: посадки немає; на час загрози все кільце можуть зупинити, як 07.10, 10.10 і 11.10.',
      },
    ],
  },
  {
    id: 'road',
    title: 'Мости для авто',
    items: [ // north to south
      bridge('pivnichnyi', 'Північний міст', OPEN, NO_LIMIT),
      bridge('podilskyi', 'Подільсько-Воскресенський міст', FIRST_15, 'Тривога: рух в обидва боки стоїть 15 хв після оголошення і 15 хв після відбою.'),
      bridge('metro', 'Міст Метро', OPEN, NO_LIMIT),
      bridge('patona', 'Міст Патона', OPEN, NO_LIMIT),
      bridge('darnytskyi', 'Дарницький міст', OPEN, NO_LIMIT),
      bridge('pivdennyi', 'Південний міст', FIRST_15, 'Тривога: з правого берега на лівий рух обмежують на 15 хв від оголошення, з лівого на правий без обмежень.'),
    ],
  },
]

export const CURFEW = { from: '01:00', to: '05:00', since: '2026-09-10' }

export const SOURCES = [
  { title: 'КМВА: що працює за жовтого і червоного рівня', url: 'https://t.me/VA_Kyiv/20278', date: '2026-09-02' },
  { title: 'Червона лінія не виходить з-під землі навіть у жовту тривогу, КМДА', url: 'https://kyiv.znaj.ua/564574-chervona-gilka-metro-kiyeva-ne-vijide-z-pid-zemli-navit-u-zhovtu-trivogu-poyasnennya-kmda', date: '2026-09-17' },
  { title: 'Як курсуватимуть поїзди метро за різного рівня тривог', url: 'https://www.unian.ua/society/metro-kijiv-yak-kursuvatimut-pojizdi-pid-chas-riznogo-rivnya-trivog-13492674.html', date: '2026-09-07' },
  { title: 'Рух зеленої лінії Південним мостом відновили за жовтого рівня', url: 'https://lb.ua/kyiv/2026/10/04/771090_kiievi_vidnovili_ruh_poyizdiv.html', date: '2026-10-04' },
  { title: 'По одному поїзду через міст у піки', url: 'https://zn.ua/ukr/UKRAINE/po-odnomu-pojizdu-cherez-mist-u-kijevi-obmezhili-rukh-zelenoju-linijeju-metro.html', date: '2026-10-06' },
  { title: 'Укрзалізниця: кільце електрички знову через Рибальський міст, з 28.06', url: 'https://t.me/UkrzalInfo/8237', date: '2026-06-24' },
  { title: 'Укрзалізниця: як ходять поїзди за жовтого і червоного рівня', url: 'https://t.me/UkrzalInfo/8509', date: '2026-09-18' },
  { title: 'Електричка: кільце зупинили через підвищену загрозу', url: 'https://t.me/kyiv_city_express/1650', date: '2026-10-07' },
  { title: 'Електричка: рух в обох напрямках призупинено через загрозу', url: 'https://t.me/kyiv_city_express/1695', date: '2026-10-10' },
  { title: 'Електричка: кільце стоїть в обидва боки за вказівкою Укрзалізниці', url: 'https://t.me/kyiv_city_express/1706', date: '2026-10-11' },
  { title: 'КМВА: правила руху мостами під час тривоги', url: 'https://t.me/VA_Kyiv/21404', date: '2026-10-03' },
  { title: 'У Києві змінили правила руху мостами під час тривоги', url: 'https://www.ukrinform.ua/rubric-regions/4170694-u-kievi-zminili-pravila-ruhu-mostami-pid-cas-povitranoi-trivogi.html', date: '2026-10-03' },
  { title: 'Комендантська година з 01:00 до 05:00, від 10 вересня', url: 'https://www.kyivpost.com/uk/post/83945', date: '2026-09-07' },
]

// The groups with the status and the note of every item for an alert level from now.json ("red", "yellow", "alert"
// or null).
export function groupsFor(level) {
  const key = LEVELS[level] ? level : 'none'
  return GROUPS.map((g) => ({ ...g, items: g.items.map((c) => ({ ...c, status: c[key][0], note: c[key][1] })) }))
}

// The same items in one list for hero.js, plus "bridges": the four bridges without alert rules in one entry.
const FREE = ['pivnichnyi', 'metro', 'patona', 'darnytskyi']

export function crossingsFor(level) {
  const all = groupsFor(level).flatMap((g) => g.items)
  const free = all.filter((c) => FREE.includes(c.id))
  const status = free.every((c) => c.status === free[0].status) ? free[0].status : 'unknown'
  return [...all, { id: 'bridges', kind: 'road', name: 'Мости Північний, Метро, Патона і Дарницький', via: 'авто й автобуси', status, note: '' }]
}
