// What crosses the Dnipro in Kyiv in each alert state. Checked 2026-10-11 from city announcements quoted by the media;
// sources and open questions: docs/product/crossing.md. Status: "open", "limited", "closed", "unknown".

export const CHECKED = '2026-10-11'

export const LEVELS = {
  none: { name: 'Тривоги немає', short: 'тихо' },
  yellow: { name: 'Жовтий рівень', short: 'загроза дронів' },
  red: { name: 'Червоний рівень', short: 'ракети або масована атака дронів' },
  alert: { name: 'Тривога', short: 'рівень не названо' },
}

export const CROSSINGS = [
  {
    id: 'm1', kind: 'metro', name: 'Червона лінія M1', via: 'міст Метро',
    none: ['open', 'їде через Дніпро'],
    yellow: ['closed', 'лише під землею Академмістечко - Арсенальна'],
    red: ['closed', 'лише під землею Академмістечко - Арсенальна'],
    alert: ['closed', 'лише під землею Академмістечко - Арсенальна'],
  },
  {
    id: 'm3', kind: 'metro', name: 'Зелена лінія M3', via: 'Південний міст',
    none: ['open', 'їде через Дніпро; у піки на мосту по одному поїзду'],
    yellow: ['open', 'їде через Дніпро; у піки на мосту по одному поїзду'],
    red: ['closed', 'дві окремі ділянки: Сирець - Видубичі і Осокорки - Червоний хутір'],
    alert: ['unknown', 'за жовтого їде, за червоного ні'],
  },
  {
    id: 'pivdennyi', kind: 'road', name: 'Південний міст', via: 'авто й автобуси',
    none: ['open', 'без обмежень'],
    yellow: ['limited', 'з правого берега на лівий стоп 15 хв від початку тривоги'],
    red: ['limited', 'з правого берега на лівий стоп 15 хв від початку тривоги'],
    alert: ['limited', 'з правого берега на лівий стоп 15 хв від початку тривоги'],
  },
  {
    id: 'podilskyi', kind: 'road', name: 'Подільсько-Воскресенський міст', via: 'авто',
    none: ['open', 'без обмежень; стоп 15 хв після відбою'],
    yellow: ['limited', 'стоп 15 хв в обидва боки на початку тривоги і після відбою'],
    red: ['limited', 'стоп 15 хв в обидва боки на початку тривоги і після відбою'],
    alert: ['limited', 'стоп 15 хв в обидва боки на початку тривоги і після відбою'],
  },
  {
    id: 'bridges', kind: 'road', name: 'Північний, Дарницький, Патона, Метро', via: 'авто й автобуси',
    none: ['open', 'без обмежень'],
    yellow: ['open', 'без обмежень'],
    red: ['open', 'без обмежень'],
    alert: ['open', 'без обмежень'],
  },
  {
    id: 'bus', kind: 'bus', name: 'Наземний транспорт', via: 'автобус 1М Палац спорту - Лісова замість червоної лінії',
    none: ['open', 'курсує'],
    yellow: ['open', 'курсує під час тривоги'],
    red: ['open', 'курсує під час тривоги'],
    alert: ['open', 'курсує під час тривоги'],
  },
  {
    id: 'rail', kind: 'rail', name: 'Міська електричка', via: 'Видубичі - Дарниця, Дарницький міст',
    none: ['open', 'їде'],
    yellow: ['unknown', 'чи їде під час тривоги, не знайдено'],
    red: ['unknown', 'чи їде під час тривоги, не знайдено'],
    alert: ['unknown', 'чи їде під час тривоги, не знайдено'],
  },
]

export const CURFEW = { from: '01:00', to: '05:00', since: '2026-09-10' }

export const SOURCES = [
  { title: 'Червона лінія не виходить з-під землі навіть у жовту тривогу, КМДА', url: 'https://kyiv.znaj.ua/564574-chervona-gilka-metro-kiyeva-ne-vijide-z-pid-zemli-navit-u-zhovtu-trivogu-poyasnennya-kmda', date: '2026-09-17' },
  { title: 'Рух зеленої лінії Південним мостом відновили за жовтого рівня', url: 'https://lb.ua/kyiv/2026/10/04/771090_kiievi_vidnovili_ruh_poyizdiv.html', date: '2026-10-04' },
  { title: 'По одному поїзду через міст у піки', url: 'https://zn.ua/ukr/UKRAINE/po-odnomu-pojizdu-cherez-mist-u-kijevi-obmezhili-rukh-zelenoju-linijeju-metro.html', date: '2026-10-06' },
  { title: 'КМВА: правила руху мостами під час тривоги', url: 'https://t.me/VA_Kyiv/21404', date: '2026-10-03' },
  { title: 'У Києві змінили правила руху мостами під час тривоги', url: 'https://www.ukrinform.ua/rubric-regions/4170694-u-kievi-zminili-pravila-ruhu-mostami-pid-cas-povitranoi-trivogi.html', date: '2026-10-03' },
  { title: 'Комендантська година 01:00 - 05:00 з 10 вересня', url: 'https://www.kyivpost.com/uk/post/83945', date: '2026-09-07' },
  { title: 'Як курсуватимуть поїзди метро за різного рівня тривог', url: 'https://www.unian.ua/society/metro-kijiv-yak-kursuvatimut-pojizdi-pid-chas-riznogo-rivnya-trivog-13492674.html', date: '2026-09-07' },
]

// The status of every crossing for an alert level from now.json ("red", "yellow", "alert" or null).
export function crossingsFor(level) {
  const key = level || 'none'
  return CROSSINGS.map((c) => ({ ...c, status: c[key][0], note: c[key][1] }))
}
