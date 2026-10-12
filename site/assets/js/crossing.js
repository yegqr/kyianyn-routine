// What crosses the Dnipro in Kyiv in each alert state. Checked 2026-10-11 from city announcements quoted by the media;
// sources and open questions: docs/product/crossing.md. Status: "open", "limited", "closed", "unknown".

export const CHECKED = '2026-10-11'

export const LEVELS = {
  none: { name: 'Тривоги немає', short: 'тривоги немає' },
  yellow: { name: 'Жовтий рівень', short: 'загроза дронів' },
  red: { name: 'Червоний рівень', short: 'ракети або масована атака' },
  alert: { name: 'Тривога', short: 'рівень не названо' },
}

const M1_UNDER = 'ходить лише під землею, Академмістечко - Арсенальна'
const SOUTH_STOP = 'з правого берега на лівий рух зупиняють на 15 хв від початку тривоги'
const PODIL_STOP = 'рух в обидва боки зупиняють на 15 хв на початку тривоги і після відбою'
const RAIL_UNKNOWN = 'чи ходить під час тривоги, невідомо'

export const CROSSINGS = [
  {
    id: 'm1', kind: 'metro', name: 'Червона лінія M1', via: 'міст Метро',
    none: ['open', 'ходить через Дніпро'],
    yellow: ['closed', M1_UNDER],
    red: ['closed', M1_UNDER],
    alert: ['closed', M1_UNDER],
  },
  {
    id: 'm3', kind: 'metro', name: 'Зелена лінія M3', via: 'Південний міст',
    none: ['open', 'ходить через Дніпро; у піки на мосту по одному поїзду'],
    yellow: ['open', 'ходить через Дніпро; у піки на мосту по одному поїзду'],
    red: ['closed', 'дві окремі ділянки: Сирець - Видубичі і Осокорки - Червоний хутір'],
    alert: ['unknown', 'за жовтої тривоги ходить, за червоної ні'],
  },
  {
    id: 'pivdennyi', kind: 'road', name: 'Південний міст', via: 'авто й автобуси',
    none: ['open', 'без обмежень'],
    yellow: ['limited', SOUTH_STOP],
    red: ['limited', SOUTH_STOP],
    alert: ['limited', SOUTH_STOP],
  },
  {
    id: 'podilskyi', kind: 'road', name: 'Подільсько-Воскресенський міст', via: 'авто',
    none: ['open', 'без обмежень; після відбою рух зупиняють на 15 хв'],
    yellow: ['limited', PODIL_STOP],
    red: ['limited', PODIL_STOP],
    alert: ['limited', PODIL_STOP],
  },
  {
    id: 'bridges', kind: 'road', name: 'Мости Північний, Дарницький, Патона і Метро', via: 'авто й автобуси',
    none: ['open', 'без обмежень'],
    yellow: ['open', 'без обмежень'],
    red: ['open', 'без обмежень'],
    alert: ['open', 'без обмежень'],
  },
  {
    id: 'bus', kind: 'bus', name: 'Автобус 1М', via: 'Палац спорту - Лісова, замість червоної лінії',
    none: ['open', 'курсує'],
    yellow: ['open', 'курсує і під час тривоги'],
    red: ['open', 'курсує і під час тривоги'],
    alert: ['open', 'курсує і під час тривоги'],
  },
  {
    id: 'rail', kind: 'rail', name: 'Міська електричка', via: 'Видубичі - Дарниця, Дарницький міст',
    none: ['open', 'ходить'],
    yellow: ['unknown', RAIL_UNKNOWN],
    red: ['unknown', RAIL_UNKNOWN],
    alert: ['unknown', RAIL_UNKNOWN],
  },
]

export const CURFEW = { from: '01:00', to: '05:00', since: '2026-09-10' }

export const SOURCES = [
  { title: 'Червона лінія не виходить з-під землі навіть у жовту тривогу, КМДА', url: 'https://kyiv.znaj.ua/564574-chervona-gilka-metro-kiyeva-ne-vijide-z-pid-zemli-navit-u-zhovtu-trivogu-poyasnennya-kmda', date: '2026-09-17' },
  { title: 'Рух зеленої лінії Південним мостом відновили за жовтого рівня', url: 'https://lb.ua/kyiv/2026/10/04/771090_kiievi_vidnovili_ruh_poyizdiv.html', date: '2026-10-04' },
  { title: 'По одному поїзду через міст у піки', url: 'https://zn.ua/ukr/UKRAINE/po-odnomu-pojizdu-cherez-mist-u-kijevi-obmezhili-rukh-zelenoju-linijeju-metro.html', date: '2026-10-06' },
  { title: 'КМВА: правила руху мостами під час тривоги', url: 'https://t.me/VA_Kyiv/21404', date: '2026-10-03' },
  { title: 'У Києві змінили правила руху мостами під час тривоги', url: 'https://www.ukrinform.ua/rubric-regions/4170694-u-kievi-zminili-pravila-ruhu-mostami-pid-cas-povitranoi-trivogi.html', date: '2026-10-03' },
  { title: 'Комендантська година з 01:00 до 05:00, від 10 вересня', url: 'https://www.kyivpost.com/uk/post/83945', date: '2026-09-07' },
  { title: 'Як курсуватимуть поїзди метро за різного рівня тривог', url: 'https://www.unian.ua/society/metro-kijiv-yak-kursuvatimut-pojizdi-pid-chas-riznogo-rivnya-trivog-13492674.html', date: '2026-09-07' },
]

// The status of every crossing for an alert level from now.json ("red", "yellow", "alert" or null).
export function crossingsFor(level) {
  const key = level || 'none'
  return CROSSINGS.map((c) => ({ ...c, status: c[key][0], note: c[key][1] }))
}
