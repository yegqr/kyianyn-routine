// Tab 1 "Чи встигну?" of livii-bereh.isakov.fyi: the answer for the next 3 hours, what crosses the Dnipro now,
// why the model says so, what flies if it does, a glossary, the slot for charts.js and the live sources.
// Live numbers come from site/api/*.json at runtime (app.js loads them); the few research numbers below come
// from the repo docs, and the page names the doc next to each of them.

import { kyivTime, kyivDay, kyivStamp, pct, ago } from './api.js'
import { LEVELS, CURFEW, CHECKED, SOURCES, crossingsFor } from './crossing.js'

// An official alert within 3 h after the answer, on the 6-week test: docs/quiet/forecast.md, README "Практична цінність".
const DOCS_ALERT = {
  low: { share: 0.17, note: 'на тесті 5 з 29, docs/quiet/forecast.md' },
  high: { share: 0.74, note: 'на тесті, docs/quiet/forecast.md' },
}
// Where the yellow and red levels are defined (the lore notes, section "Рівні тривоги").
const LEVEL_SOURCE = { text: 'kyiv.news, 03.09.2026', url: 'https://kyiv.news/bezpeka-kriminal/kyiv-vvodyt-zhovtyi-chervonyi-rivni-tryvohy/' }

const ANSWER = { low: 'Так, швидше встигнеш', medium: 'Ризиковано', high: 'Краще не плануй' }
const STATUS_WORD = { open: 'їде', limited: 'з обмеженнями', closed: 'не їде', unknown: 'невідомо' }
const PATH = {
  open: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7 5.3-5.7"/>',
  limited: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>',
  closed: '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
  unknown: '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.6a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5v.5M12 16.9v.1"/>',
  warn: '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17v.1"/>',
  siren: '<path d="M7 18v-5a5 5 0 0 1 10 0v5"/><path d="M5 18h14v2.5H5z"/><path d="M12 3.5V5M4.5 6.5l1.2 1.2M19.5 6.5l-1.2 1.2"/>',
  moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
  shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
}
const HOURS = ['година', 'години', 'годин']
const TIMES = ['раз', 'рази', 'разів']
const CALLS = ['запит', 'запити', 'запитів']
const POSTS = ['пост', 'пости', 'постів']
const RM = window.matchMedia('(prefers-reduced-motion: reduce)')

// A tiny element builder. how.js has the same helper, but tab 1 must work without loading the deck module.
function h(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue
    if (k === 'text') node.textContent = v
    else if (k === 'html') node.innerHTML = v
    else if (k === 'class') node.className = v
    else node.setAttribute(k, v === true ? '' : v)
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) node.append(kid)
  return node
}

const icon = (name) => h('span', { class: 'ico', 'aria-hidden': 'true', html: `<svg viewBox="0 0 24 24">${PATH[name]}</svg>` })
const calm = (text) => h('p', { class: 'calm', text })
const isNum = (x) => typeof x === 'number' && Number.isFinite(x)
const num = (x) => (isNum(x) ? x.toLocaleString('uk-UA') : '?')
const pct1 = (x) => pct(x, 1).replace(/\.0%$/, '%') // thresholds: 0.197 -> "19.7%", 0.3 -> "30%"
const sign = (x) => `${x < 0 ? '-' : '+'}${Math.abs(x).toFixed(2)}`
const day = (iso) => String(iso).slice(0, 10).split('-').reverse().join('.') // "2026-07-04" -> "04.07.2026"
const upper = (t) => (t ? t[0].toUpperCase() + t.slice(1) : '')
const cell = (v) => {
  const t = String(v ?? '')
  return /[",\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t
}

function plural(n, [one, few, many]) {
  const d = Math.abs(n) % 10
  const dd = Math.abs(n) % 100
  if (d === 1 && dd !== 11) return one
  if (d >= 2 && d <= 4 && (dd < 12 || dd > 14)) return few
  return many
}

function period(p) { // "2026-07-04..2026-10-10" -> "з 04.07 до 10.10.2026"
  const [a, b] = String(p || '').split('..')
  return a && b ? `з ${day(a).slice(0, 5)} до ${day(b)}` : ''
}

let alertNow = false
let alertLevel = null
let bound = false

export function renderDashboard(root, data) {
  const now = data.now
  alertNow = Boolean(now?.now?.alert)
  alertLevel = alertNow ? (now.now.level || 'alert') : null
  if (!bound) bindTrain()
  part(root, 'answer', () => answer(now))
  part(root, 'scale', () => heroScale(now))
  part(root, 'more', () => heroMore(now))
  part(root, 'crossings', () => crossings(now))
  part(root, 'reasons', () => reasons(now))
  part(root, 'kind', () => kind(now))
  part(root, 'glossary', () => glossary(now, data.model))
  part(root, 'sources', () => sources(now, data.meta, data.model))
  trainHint()
}

function part(root, name, build) {
  const box = root.querySelector(`[data-part="${name}"]`)
  if (!box) return
  try {
    box.replaceChildren(...[build()].flat().filter(Boolean))
  } catch (err) {
    console.warn('dashboard', name, err)
    box.replaceChildren(calm('Дані для цього блоку ще не готові.'))
  }
}

// a) the answer

function tierOf(f) {
  if (ANSWER[f.tier]) return f.tier
  if (f.p < f.busy_at) return 'low'
  return f.p >= f.high_at ? 'high' : 'medium'
}

function windowText(now) {
  const d = kyivDay(now.hour)
  const today = kyivDay(new Date().toISOString())
  return `${d === today ? 'Сьогодні' : d}, з ${kyivTime(now.hour)} до ${kyivTime(now.window_end)} за київським часом`
}

function banner(kind, ico, title, text) {
  return h('div', { class: `banner banner-${kind}`, role: kind === 'alert' ? 'alert' : 'status' }, icon(ico),
    h('div', {}, h('p', { class: 'banner-title', text: title }), h('p', { class: 'banner-text', text })))
}

function answer(now) {
  const f = now?.forecast
  if (!f || !isNum(f.p)) {
    return [h('p', { class: 'answer answer-wait', text: 'Дані ще не готові' }),
      calm('Прогноз з’явиться, щойно сервер опублікує перші дані. Сторінка перевіряє їх кожні 2 хвилини сама.')]
  }
  const tier = tierOf(f)
  const alert = Boolean(now.now?.alert)
  const lv = LEVELS[now.now?.level] || LEVELS.alert
  return [
    h('p', { class: 'hero-window', text: windowText(now) }),
    now.stale && banner('stale', 'warn', 'Дані застаріли',
      `${upper(now.stale_reason || 'нових постів давно не було')}. Відповідь нижче може бути неточною.`),
    alert && banner('alert', 'siren', `Зараз тривога: ${lv.name}${now.now.alert_since ? `, з ${kyivTime(now.now.alert_since)}` : ''}`,
      `${upper(lv.short)}. Під час тривоги йдіть в укриття.`),
    h('p', { class: `answer answer-${tier}`, text: ANSWER[tier] }),
    f.label && h('p', { class: `tier tier-${tier}`, text: f.label }),
  ]
}

// The scale and the lines under the answer are parts of their own: on a wide screen the scale stands under the
// train and the lines beside it (site.css, "a) hero"), so neither column stays half empty; on a phone they follow
// the answer in this order.
function readyForecast(now) {
  const f = now?.forecast
  return f && isNum(f.p) ? f : null
}

function heroScale(now) {
  const f = readyForecast(now)
  return f ? scale(f) : null
}

function heroMore(now) {
  const f = readyForecast(now)
  if (!f) return null
  return [
    h('p', { class: 'p-line' }, 'ймовірність, що прилетять дрони або ракети: ', h('b', { text: pct(f.p) })),
    honest(f, tierOf(f)),
    !now.now?.alert && now.now?.quiet_now === false && h('p', { class: 'src',
      text: 'Зараз не тихо: тривога або атака була за минулу годину. Модель перевіряли лише на тихих годинах, тож ця відповідь менш перевірена.' }),
  ]
}

function scale(f) {
  const clamp = (x) => Math.max(0, Math.min(1, isNum(x) ? x : 0))
  const p = clamp(f.p)
  const b = clamp(f.busy_at)
  const hi = clamp(f.high_at)
  const at = (x) => `${(100 * x).toFixed(2)}%`
  const align = p < 0.08 ? 'start' : p > 0.92 ? 'end' : 'mid'
  return h('div', { class: 'scale', role: 'img', 'aria-label': `Шкала від 0 до 100%. Межі рівнів ${pct1(b)} і ${pct1(hi)}. Зараз ${pct(f.p)}.` },
    h('div', { class: 'scale-row' }, h('span', { class: `scale-p align-${align}`, style: `left:${at(p)}`, text: pct(f.p) })),
    h('div', { class: 'scale-bar' },
      h('span', { class: 'zone zone-low', style: `width:${at(b)}` }),
      h('span', { class: 'zone zone-mid', style: `width:${at(Math.max(0, hi - b))}` }),
      h('span', { class: 'zone zone-high' }),
      h('span', { class: 'scale-tick', style: `left:${at(b)}` }),
      h('span', { class: 'scale-tick', style: `left:${at(hi)}` }),
      h('span', { class: 'scale-dot', style: `left:${at(p)}` })),
    h('div', { class: 'scale-row scale-bottom' },
      h('span', { class: 'scale-end', text: '0%' }),
      h('span', { class: 'scale-num to-left', style: `left:${at(b)}`, text: pct1(b) }),
      h('span', { class: 'scale-num to-right', style: `left:${at(hi)}`, text: pct1(hi) }),
      h('span', { class: 'scale-end end-right', text: '100%' })),
    h('ul', { class: 'scale-legend' },
      h('li', {}, h('i', { class: 'sw sw-low' }), `швидше тихо: менше ${pct1(b)}`),
      h('li', {}, h('i', { class: 'sw sw-mid' }), `середній ризик: від ${pct1(b)} до ${pct1(hi)}`),
      h('li', {}, h('i', { class: 'sw sw-high' }), `високий ризик: від ${pct1(hi)}`)))
}

function honest(f, tier) {
  const k = f.kind
  let share
  let note
  if (isNum(k?.alert_share)) {
    share = k.alert_share
    note = [isNum(k.n) ? `${num(k.n)} ${plural(k.n, HOURS)}` : '', period(k.period)].filter(Boolean).join(' ')
  } else if (DOCS_ALERT[tier]) {
    ({ share, note } = DOCS_ALERT[tier])
  } else {
    return null
  }
  const n = Math.round(share * 10)
  const say = n <= 0 ? 'рідше, ніж 1 раз з 10' : n >= 10 ? 'майже завжди' : `приблизно ${n} ${plural(n, TIMES)} з 10`
  return h('p', { class: 'honest' }, `Після такої відповіді тривога за 3 години траплялась ${say}. `,
    h('span', { class: 'src', text: `(${pct(share)}${note ? `, ${note}` : ''})` }))
}

// b) what crosses the Dnipro now

function crossings(now) {
  const level = now?.now?.alert ? (now.now.level || 'alert') : null
  const lv = LEVELS[level || 'none']
  const state = !now ? 'Стан тривоги невідомий, тож показано, як їде без тривоги.'
    : level ? `Зараз: ${lv.name.toLowerCase()}, ${lv.short}. Так їде транспорт через Дніпро:`
      : 'Зараз тривоги немає. Так їде транспорт через Дніпро:'
  return [
    h('p', { class: 'cross-state', text: state }),
    h('ul', { class: 'crosses' }, crossingsFor(level).map((c) => {
      const st = PATH[c.status] && STATUS_WORD[c.status] ? c.status : 'unknown'
      return h('li', { class: `cross cross-${st}` },
        h('p', { class: 'cross-status' }, icon(st), h('span', { text: STATUS_WORD[st] })),
        h('h3', { class: 'cross-name', text: c.name }),
        h('p', { class: 'cross-via', text: c.via }),
        h('p', { class: 'cross-note', text: c.note }))
    })),
    h('p', { class: 'cross-meta' }, icon('moon'),
      h('span', { text: `Комендантська година з ${CURFEW.from} до ${CURFEW.to}, діє з ${day(CURFEW.since)}.` })),
    h('p', { class: 'cross-meta' }, icon('check'),
      h('span', { text: `Перевірено ${day(CHECKED)} за повідомленнями міста в медіа. Правила змінюються, тож перед виходом гляньте свіжі новини.` })),
    h('details', { class: 'sources' }, h('summary', { text: `Джерела, ${SOURCES.length}` }),
      h('ul', {}, SOURCES.map((s) => h('li', {},
        h('a', { href: s.url, target: '_blank', rel: 'noopener', text: s.title }),
        h('span', { class: 'src', text: `, ${day(s.date)}` }))))),
  ]
}

// c) why: the reasons as signed bars of their weight in the model's score (logit)

function reasons(now) {
  const rs = (now?.forecast?.reasons || []).filter((r) => isNum(r?.logit))
  if (!rs.length) return calm(now ? 'Для цієї години причин немає.' : 'Дані ще не готові.')
  const most = Math.max(0.5, ...rs.map((r) => Math.abs(r.logit)))
  const tip = h('p', { class: 'tip', role: 'tooltip', hidden: true })
  const rows = rs.map((r) => {
    const up = r.logit >= 0
    const w = (Math.abs(r.logit) / most) * 50
    const say = `${r.text}: ${r.value}. ${up ? 'Додає' : 'Віднімає'} ${Math.abs(r.logit).toFixed(2)} ${up
      ? 'до рахунку моделі, тож ризик вищий.' : 'від рахунку моделі, тож ризик нижчий.'}`
    const row = h('li', { class: 'reason', tabindex: '0', 'aria-label': say },
      h('p', { class: 'reason-text' }, h('span', { text: r.text }), h('b', { class: 'reason-val', text: String(r.value ?? '') })),
      h('div', { class: 'reason-bar' },
        h('span', { class: 'reason-track' },
          h('span', { class: `reason-fill ${up ? 'up' : 'down'}`, style: `left:${up ? 50 : 50 - w}%;width:${w}%` })),
        h('span', { class: 'reason-w', text: sign(r.logit) })))
    const show = () => {
      tip.textContent = say
      tip.style.top = `${row.offsetTop + row.offsetHeight + 6}px`
      tip.hidden = false
    }
    row.addEventListener('pointerenter', show)
    row.addEventListener('focus', show)
    row.addEventListener('click', show)
    row.addEventListener('pointerleave', () => { if (document.activeElement !== row) tip.hidden = true })
    row.addEventListener('blur', () => { tip.hidden = true })
    return row
  })
  const csv = ['key,text,value,logit', ...rs.map((r) => [r.key, r.text, r.value, r.logit].map(cell).join(','))].join('\n')
  return [
    h('p', { class: 'lead', text: 'Модель складає рахунок із сигналів останніх годин. Плюс додає до рахунку, і ризик вищий; мінус віднімає, і ризик нижчий. Тут найсильніші причини цієї години.' }),
    h('div', { class: 'reason-axis', 'aria-hidden': 'true' }, h('span', { text: '← знижує ризик' }), h('span', { text: 'підвищує ризик →' })),
    h('ul', { class: 'reasons' }, rows),
    tip,
    foot(csv, 'prychyny.csv'),
  ]
}

function foot(csv, name) {
  return h('div', { class: 'card-foot' },
    h('a', { href: `data:text/csv;charset=utf-8,${encodeURIComponent(`﻿${csv}`)}`, download: name, text: 'Сирі дані, CSV' }),
    h('a', { class: 'credit', href: 'https://isakov.fyi', text: 'ЄІ' }))
}

// d) if it flies, what: missiles or drones only in the past busy windows at this tier

function kind(now) {
  const f = now?.forecast
  const k = f?.kind
  if (!k || !isNum(k.missile_share)) return calm(now ? 'Для цього рівня ще немає історії.' : 'Дані ще не готові.')
  const drones = isNum(k.drone_only_share) ? k.drone_only_share : 1 - k.missile_share
  const m = Math.max(0, Math.min(10, Math.round(k.missile_share * 10)))
  const csv = ['n,busy_share,missile_share,drone_only_share,alert_share,period',
    [k.n, k.busy_share, k.missile_share, drones, k.alert_share, k.period].map(cell).join(',')].join('\n')
  const fig = (value, sw, label) => h('div', { class: 'kind-fig' }, h('p', { class: 'fig-num', text: value }),
    h('p', { class: 'fig-label' }, h('i', { class: `sw sw-${sw}`, 'aria-hidden': 'true' }), label))
  return [
    h('p', { class: 'lead' },
      `Так було в минулому, коли модель казала «${f.label || 'те саме'}»: ${num(k.n)} ${isNum(k.n) ? plural(k.n, HOURS) : 'годин'} ${period(k.period)}.`,
      isNum(k.busy_share) ? ` Після такої відповіді прилітало у ${pct(k.busy_share)} випадків.` : ''),
    h('div', { class: 'kind-grid' },
      fig(pct(k.missile_share), 'm', 'з ракетами'),
      fig(pct(drones), 'd', 'лише дрони'),
      h('div', { class: 'kind-cells', role: 'img', 'aria-label': `З 10 разів, коли прилітало, приблизно ${m} з ракетами і ${10 - m} лише дрони` },
        Array.from({ length: 10 }, (_, i) => h('span', { class: `cell cell-${i < m ? 'm' : 'd'}`, style: `animation-delay:${i * 30}ms` })))),
    h('p', { class: 'kind-cap', text: `З 10 разів, коли прилітало: приблизно ${m} з ракетами, ${10 - m} лише дрони.` }),
    h('p', { class: 'note' }, h('b', { text: 'Чесно: ' }),
      'модель майже не відрізняє масовану ракетну атаку від дронів, перед обома каже «високий ризик». ',
      h('span', { class: 'src', text: 'docs/quiet/model.md, розділ 10' })),
    foot(csv, 'shcho-pryletyt.csv'),
  ]
}

// e) glossary

function glossary(now, model) {
  const b = now?.forecast?.busy_at ?? model?.busy_at
  const hi = now?.forecast?.high_at ?? model?.high_at
  const known = isNum(b) && isNum(hi)
  const items = [
    ['Тихо', null, 'За 3 години на Київ не прилетіло нічого: ні дронів, ні ракет.'],
    ['Неспокійно', null, 'За ці 3 години на Київ летіли дрони або ракети, хоча б раз.'],
    ['Швидше тихо', 'low', known ? `Ймовірність менша за ${pct1(b)}. Найпевніше, вікно буде тихим, але гарантії немає.` : 'Найнижчий з трьох рівнів ризику.'],
    ['Середній ризик', 'mid', known ? `Ймовірність від ${pct1(b)} до ${pct1(hi)}. Може бути і так, і так.` : 'Середній з трьох рівнів ризику.'],
    ['Високий ризик', 'high', known ? `Ймовірність ${pct1(hi)} і більше. Прилітає частіше, ніж зазвичай.` : 'Найвищий з трьох рівнів ризику.'],
    ['Ймовірність', null, 'Число від 0 до 100%: як часто після схожих годин у минулому прилітало. 30% означає приблизно 3 рази з 10.'],
    ['«Зараз тихо»', null, 'Тривоги немає, і за минулу годину атаки не було. Саме на таких годинах прогноз перевіряли.'],
    ['Жовтий рівень тривоги', null, 'Загроза дронів. Червона лінія метро через Дніпро не їде, зелена їде.'],
    ['Червоний рівень тривоги', null, 'Ракети, ракети разом з дронами або масована атака дронів. Одразу в укриття. Метро через Дніпро не їде.'],
  ]
  return [
    h('dl', { class: 'gloss' }, items.map(([term, sw, text]) => h('div', {},
      h('dt', {}, sw && h('i', { class: `sw sw-${sw}`, 'aria-hidden': 'true' }), term),
      h('dd', { text })))),
    h('p', { class: 'src' }, 'Рівні тривоги: ',
      h('a', { href: LEVEL_SOURCE.url, target: '_blank', rel: 'noopener', text: LEVEL_SOURCE.text }),
      '. Межі рівнів ризику взято з даних розробки, docs/quiet/model.md.'),
  ]
}

// g) live sources

function sources(now, meta, model) {
  const chans = (meta?.channels || []).slice()
    .sort((a, b) => String(b.last_post || '').localeCompare(String(a.last_post || '')))
  const pl = meta?.pipeline
  const md = now?.model || model
  const jev = meta?.jev
  const facts = [
    ['Збір даних', pl?.last_cycle
      ? `останній цикл ${ago(pl.last_cycle)}${isNum(pl.cycle_seconds) ? `, тривав ${Math.round(pl.cycle_seconds)} с` : ''}`
      : 'даних про цикл ще немає'],
    ['Найсвіжіший пост', now?.data_until ? `${kyivStamp(now.data_until)}, ${ago(now.data_until)}` : 'ще немає'],
    ['Модель', md?.trained_at ? `навчена ${kyivStamp(md.trained_at)} на ${num(md.rows)} годинах історії` : 'ще не готова'],
    ['Jev, мовна модель, що читає пости', jev
      ? `${num(jev.calls)} ${isNum(jev.calls) ? plural(jev.calls, CALLS) : 'запитів'}, $${isNum(jev.usd) ? jev.usd.toFixed(2) : '?'}`
      : 'даних ще немає'],
  ]
  const day1 = 24 * 3600 * 1000
  return [
    h('p', { class: 'lead', text: 'Звідки береться прогноз і наскільки свіжі дані.' }),
    h('h3', { class: 'sub', text: chans.length ? `Telegram-канали, ${chans.length}` : 'Telegram-канали' }),
    chans.length
      ? h('ul', { class: 'chans' }, chans.map((c) => {
        const old = !c.last_post || Date.now() - new Date(c.last_post).getTime() > day1
        const n = isNum(c.posts_24h) ? c.posts_24h : 0
        return h('li', { class: `chan${old ? ' is-old' : ''}` },
          h('span', { class: 'chan-name', text: c.name, title: c.name }),
          h('span', { class: 'chan-ago', text: c.last_post ? `останній пост ${ago(c.last_post)}` : 'постів ще не було' }),
          h('span', { class: 'chan-n', text: `за 24 год: ${num(n)} ${plural(n, POSTS)}` }))
      }))
      : calm('Список каналів ще не готовий.'),
    h('dl', { class: 'facts' }, facts.map(([k, v]) => h('div', {}, h('dt', { text: k }), h('dd', { text: v })))),
    h('p', { class: 'safety' }, icon('shield'), h('span', { text: 'Прогноз не дозвіл виходити з укриття. Під час тривоги йдіть в укриття.' })),
  ]
}

// f) charts: another file (charts.js) draws them; until it ships the section keeps its calm placeholders

export async function mountChartsInto(section, data) {
  if (!section || !data.history) return
  let mod
  try {
    mod = await import('./charts.js')
  } catch {
    return
  }
  try {
    section.querySelectorAll('.chart-wait').forEach((n) => n.remove())
    await mod.mountCharts?.(section, data)
  } catch (err) {
    console.warn('charts', err)
  }
}

// The trick: a tiny pink train on the bridge. It crosses the Dnipro; in an alert it does what the red line M1
// does: rolls up to the bridge, stops at the edge and goes back under ground. Transform only, 400 ms moves.

const TRAIN = { cross: 342, edge: 42, dur: 400, pause: 700 }
let side = 0 // 0: on the right bank (west, left in the picture), 1: on the left bank
let busy = false

function move(node, x) {
  node.style.transition = RM.matches ? 'none' : `transform ${TRAIN.dur}ms var(--ease)`
  node.style.transform = `translateX(${x}px)`
}

function trainHint(text) {
  const hint = document.getElementById('train-hint')
  if (!hint) return
  hint.textContent = text || (alertNow
    ? 'Зараз тривога. Натисни або T: подивись, що робить червона лінія.'
    : side ? 'Потяг на лівому березі. Натисни ще раз, і він повернеться.' : 'Натисни або T: потяг перетне Дніпро.')
}

// Hover or focus on the train: a tooltip with what the red line M1 does right now (crossing.js).
function trainTip(show) {
  const tip = document.getElementById('train-tip')
  if (!tip) return
  const m1 = crossingsFor(alertLevel).find((c) => c.id === 'm1')
  tip.textContent = m1 ? `${m1.name}, ${m1.via}: ${STATUS_WORD[m1.status] || STATUS_WORD.unknown}` : ''
  tip.hidden = !show || !m1
}

function bindTrain() {
  const btn = document.getElementById('train')
  if (!btn) return
  bound = true
  btn.addEventListener('pointerenter', () => trainTip(true))
  btn.addEventListener('pointerleave', () => trainTip(false))
  btn.addEventListener('focus', () => trainTip(true))
  btn.addEventListener('blur', () => trainTip(false))
}

export function runTrain() {
  const car = document.getElementById('train-car')
  if (!car || busy) return
  const base = side ? TRAIN.cross : 0
  if (alertNow) {
    trainHint('Тривога: червона лінія не виходить на міст і повертається під землю.')
    if (RM.matches) return
    busy = true
    move(car, side ? base - TRAIN.edge : base + TRAIN.edge)
    setTimeout(() => move(car, base), TRAIN.dur + TRAIN.pause)
    setTimeout(() => { busy = false }, 2 * TRAIN.dur + TRAIN.pause)
    return
  }
  side = 1 - side
  move(car, side ? TRAIN.cross : 0)
  trainHint()
}
