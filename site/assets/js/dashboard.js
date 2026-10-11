// Tab 1 "Відповідь" of kyianyn-routine.isakov.fyi. It answers one question first: will you make it to the other bank
// of the Dnipro in the next 3 hours. The first screen, top to bottom: an alert chip when an alert is on, the answer
// (ТАК, РИЗИКОВАНО or НІ in the colour of its tier), the question in small type with its window, the crossing
// picture, the probability on a 3-colour scale and two chips whose details live in tooltips. Below, compact: what
// crosses the Dnipro now as status pills, the reasons (folded), the slot for charts.js, the glossary and the live
// sources (folded). Live numbers come from site/api/*.json at runtime (app.js loads them, the contract is in
// docs/ARCHITECTURE.md, section "Живий сайт").
//
// The crossing picture #hero-map (aspect ratio 2:1, site.css) shows the small train on the bridge until
// ./hero.js loads. When it does, mountHero(el, data) draws in it; it may return { update(data), train() }:
// update gets every new data, train runs on the key T. Without update, mountHero is called again on new data.

import { kyivTime, kyivDay, kyivStamp, pct, ago } from './api.js'
import { LEVELS, CURFEW, CHECKED, SOURCES, crossingsFor } from './crossing.js'

// Where the yellow and red levels are defined (the lore notes, section "Рівні тривоги").
const LEVEL_SOURCE = { text: 'kyiv.news, 03.09.2026', url: 'https://kyiv.news/bezpeka-kriminal/kyiv-vvodyt-zhovtyi-chervonyi-rivni-tryvohy/' }

const TIER = {
  low: { word: 'ТАК', line: 'встигнеш на інший берег' },
  medium: { word: 'РИЗИКОВАНО', line: 'може не вийти: їдь зараз або зачекай' },
  high: { word: 'НІ', line: 'краще не їхати найближчі 3 години' },
}
const STATUS_WORD = { open: 'їде', limited: 'з обмеженнями', closed: 'не їде', unknown: 'невідомо' }
// Short names for the pills; the full name, the route and the note go to the tooltip.
const SHORT = { m1: 'M1', m3: 'M3', pivdennyi: 'Південний', podilskyi: 'Подільський', bridges: 'Ще 4 мости', bus: 'Автобус 1М', rail: 'Електричка' }
const METRO = new Set(['m1', 'm3'])
const PATH = {
  open: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7 5.3-5.7"/>',
  limited: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>',
  closed: '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
  unknown: '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.6a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5v.5M12 16.9v.1"/>',
  siren: '<path d="M7 18v-5a5 5 0 0 1 10 0v5"/><path d="M5 18h14v2.5H5z"/><path d="M12 3.5V5M4.5 6.5l1.2 1.2M19.5 6.5l-1.2 1.2"/>',
  moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
  shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/>',
  drone: '<path d="M12 4l8.5 14L12 15l-8.5 3z"/>',
  rocket: '<path d="M12 2.5c3 2.4 4.2 6 4.2 10.5L12 17.5 7.8 13C7.8 8.5 9 4.9 12 2.5z"/><path d="M7.8 13 5 16v3.5l3.5-2.2M16.2 13l2.8 3v3.5l-3.5-2.2"/>',
  past: '<path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1"/><path d="M3.5 4v4.5H8"/><path d="M12 7.5V12l3 2"/>',
}
const HOURS = ['година', 'години', 'годин']
const TIMES = ['раз', 'рази', 'разів']
const CALLS = ['запит', 'запити', 'запитів']
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

let tierNow = null
let answerTier = null // the tier the answer shows: the model's, but never ТАК while an alert holds the metro
let alertNow = false
let alertLevel = null
let m1Status = 'open'
let bound = false
let heroLoad = null
let heroInst = null

export function renderDashboard(root, data) {
  const now = data.now
  const f = forecastOf(now)
  tierNow = f ? tierOf(f) : null
  alertNow = Boolean(now?.now?.alert)
  alertLevel = alertNow ? (now.now.level || 'alert') : null
  m1Status = crossingsFor(alertLevel).find((c) => c.id === 'm1')?.status || 'unknown'
  answerTier = f ? shownTier(tierNow, alertLevel) : null
  const hero = root.querySelector('#hero')
  if (hero) hero.dataset.tier = answerTier || 'none'
  if (!bound) bindTrain()
  part(root, 'alert', () => alertChip(now))
  part(root, 'answer', () => answer(f))
  part(root, 'line', () => (f ? ALERT_LINE[alertLevel] || TIER[answerTier].line : 'відповідь з’явиться, щойно сервер опублікує перші дані'))
  part(root, 'window', () => windowText(now))
  part(root, 'prob', () => prob(f))
  part(root, 'chips', () => chips(now, f))
  part(root, 'crossings', () => crossings(now))
  part(root, 'reasons', () => reasons(now))
  part(root, 'glossary', () => glossary(now, data.model))
  part(root, 'sources', () => sources(now, data.meta, data.model))
  paintTrain()
  heroMap(root, data)
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

// Tooltips of a group (chips, pills, reasons): one dark box under the row of the item, inside the group's width,
// so it never leaves the screen. Hover, focus or a tap shows it; leaving or blur hides it.
function tips(box, tip) {
  const show = (el) => {
    tip.textContent = el.dataset.tip
    tip.style.top = `${el.offsetTop + el.offsetHeight + 8}px`
    tip.hidden = false
  }
  for (const el of box.querySelectorAll('[data-tip]')) {
    el.addEventListener('pointerenter', () => show(el))
    el.addEventListener('focus', () => show(el))
    el.addEventListener('click', () => show(el))
    el.addEventListener('pointerleave', () => { if (document.activeElement !== el) tip.hidden = true })
    el.addEventListener('blur', () => { tip.hidden = true })
  }
}

// a) the answer, the question's window, the probability and the chips

function forecastOf(now) {
  const f = now?.forecast
  return f && isNum(f.p) ? f : null
}

function tierOf(f) {
  if (TIER[f.tier]) return f.tier
  if (isNum(f.busy_at) && f.p < f.busy_at) return 'low'
  return isNum(f.high_at) && f.p >= f.high_at ? 'high' : 'medium'
}

function windowText(now) {
  if (!now?.hour) return ''
  const d = kyivDay(now.hour)
  const end = now.window_end ? ` до ${kyivTime(now.window_end)}` : ''
  return `${d === kyivDay(new Date().toISOString()) ? '' : `${d}, `}з ${kyivTime(now.hour)}${end}`
}

function alertChip(now) {
  if (!now?.now?.alert) return null
  const level = now.now.level
  const name = level === 'yellow' ? 'жовтий рівень' : level === 'red' ? 'червоний рівень' : ''
  const since = now.now.alert_since ? `з ${kyivTime(now.now.alert_since)}` : ''
  const lv = LEVELS[level] || LEVELS.alert
  return h('p', { class: `alert-chip alert-${level === 'yellow' ? 'yellow' : 'red'}`, role: 'status',
    title: `${upper(lv.short)}. Під час тривоги йдіть в укриття.` },
  icon('siren'), h('span', { text: ['тривога', name, since].filter(Boolean).join(', ') }))
}

// During an alert the metro already stops at the river (docs/product/crossing.md), so the answer never says ТАК:
// a red level means НІ (no metro crosses), a yellow or an unnamed level at least РИЗИКОВАНО (only M3 and cars).
const ALERT_LINE = {
  red: 'зараз червона тривога: метро через Дніпро не їде',
  yellow: 'зараз жовта тривога: через Дніпро їде лише зелена M3 і авто',
  alert: 'зараз тривога: червона M1 через Дніпро не їде',
}

function shownTier(tier, level) {
  if (!level) return tier
  if (level === 'red') return 'high'
  return tier === 'low' ? 'medium' : tier
}

function answer(f) {
  if (!f) return h('p', { class: 'answer answer-wait', text: 'Дані ще не готові' })
  return h('p', { class: `answer answer-${answerTier}`, text: TIER[answerTier].word })
}

function prob(f) {
  if (!f) return null
  return [
    h('p', { class: 'p-row' }, h('b', { class: 'p-num', text: pct(f.p) }),
      h('span', { class: 'p-label', text: 'ймовірність, що прилетять дрони або ракети' })),
    meter(f),
  ]
}

function meter(f) {
  const clamp = (x) => Math.max(0, Math.min(1, isNum(x) ? x : 0))
  const p = clamp(f.p)
  const b = clamp(f.busy_at)
  const hi = Math.max(b, clamp(f.high_at))
  const at = (x) => `${(100 * x).toFixed(2)}%`
  const say = `Шкала від 0 до 100%: зелене менше ${pct1(b)}, жовте від ${pct1(b)} до ${pct1(hi)}, червоне від ${pct1(hi)}. Зараз ${pct(f.p)}.`
  return h('div', { class: 'meter', role: 'img', 'aria-label': say, title: say },
    h('div', { class: 'meter-bar' },
      h('span', { class: 'zone zone-go', style: `width:${at(b)}` }),
      h('span', { class: 'zone zone-risk', style: `width:${at(hi - b)}` }),
      h('span', { class: 'zone zone-stop' }),
      h('span', { class: 'meter-mark', style: `left:${at(p)}` })),
    h('div', { class: 'meter-ticks', 'aria-hidden': 'true' },
      h('span', { class: 'to-left', style: `left:${at(b)}`, text: pct1(b) }),
      h('span', { class: 'to-right', style: `left:${at(hi)}`, text: pct1(hi) })))
}

function chip(ico, text, tip) {
  return h('button', { type: 'button', class: 'chip', 'data-tip': tip, 'aria-label': `${text}. ${tip}` }, icon(ico), h('span', { text }))
}

// Two chips at most, both from forecast.kind: what flew in the past busy windows at this tier, and how often the
// same answer came true. The details (hours, period, shares, caveats) go to the tooltip.
function chips(now, f) {
  const k = f?.kind
  if (!k || !isNum(k.n) || k.n <= 0) return null
  const said = `«${f.label || TIER[tierNow].word.toLowerCase()}»`
  const hours = `${num(k.n)} ${plural(k.n, HOURS)} ${period(k.period)}`.trim()
  const told = `так казали ${num(k.n)} ${plural(k.n, TIMES)}`
  const items = []
  if (isNum(k.missile_share)) {
    const drones = isNum(k.drone_only_share) ? k.drone_only_share : 1 - k.missile_share
    const mostly = drones >= k.missile_share
    items.push(chip(mostly ? 'drone' : 'rocket', `якщо прилетить: найчастіше ${mostly ? 'дрони' : 'ракети'}, ${pct(mostly ? drones : k.missile_share)}`,
      `Коли модель казала ${said} і прилітало (${hours}): лише дрони ${pct(drones)}, з ракетами ${pct(k.missile_share)}. Масовану ракетну атаку модель майже не відрізняє від дронів.`))
  }
  if (isNum(k.busy_share)) {
    const quiet = 1 - k.busy_share
    const text = tierNow === 'low' ? `${told}, справдилось ${pct(quiet)}`
      : tierNow === 'high' ? `${told}, справдилось ${pct(k.busy_share)}` : `${told}, прилітало у ${pct(k.busy_share)}`
    items.push(chip('past', text, [`Модель казала ${said} ${hours}.`,
      `За 3 години після цього дрони або ракети прилітали у ${pct(k.busy_share)} випадків, тихо було у ${pct(quiet)}.`,
      isNum(k.alert_share) ? `Офіційна тривога була у ${pct(k.alert_share)}.` : '',
      now?.now?.quiet_now === false && !now.now.alert ? 'Зараз не тихо, а модель перевіряли на тихих годинах, тож ця відповідь менш перевірена.' : '',
    ].filter(Boolean).join(' ')))
  }
  if (!items.length) return null
  const tip = h('p', { class: 'tip', role: 'tooltip', hidden: true })
  const box = h('div', { class: 'chips' }, items, tip)
  tips(box, tip)
  return box
}

// b) what crosses the Dnipro now: one row of status pills, the note of each in its tooltip

function crossings(now) {
  const level = now?.now?.alert ? (now.now.level || 'alert') : null
  const tip = h('p', { class: 'tip', role: 'tooltip', hidden: true })
  const pills = h('ul', { class: 'pills' }, crossingsFor(level).map((c) => {
    const st = STATUS_WORD[c.status] ? c.status : 'unknown'
    const say = `${c.name}, ${c.via}: ${STATUS_WORD[st]}, ${c.note}.`
    return h('li', {}, h('button', { type: 'button', class: `pill pill-${st}`, 'data-tip': say, 'aria-label': say },
      icon(st), METRO.has(c.id) && h('i', { class: `metro metro-${c.id}`, 'aria-hidden': 'true' }), h('span', { text: SHORT[c.id] || c.name })))
  }))
  const box = h('div', { class: 'pills-box' }, pills, tip)
  tips(box, tip)
  const state = !now ? 'Стан тривоги невідомий, показано без тривоги.'
    : level ? `Зараз ${(LEVELS[level] || LEVELS.alert).name.toLowerCase()}.` : 'Зараз тривоги немає.'
  return [
    box,
    h('div', { class: 'cross-line' }, icon('moon'),
      h('span', { text: `${state} Комендантська година ${CURFEW.from} - ${CURFEW.to}.` }),
      h('details', { class: 'srcs' }, h('summary', { text: `джерела, ${SOURCES.length}` }),
        h('ul', {}, SOURCES.map((s) => h('li', {},
          h('a', { href: s.url, target: '_blank', rel: 'noopener', text: s.title }),
          h('span', { class: 'src', text: `, ${day(s.date)}` })))),
        h('p', { class: 'src', text: `Перевірено ${day(CHECKED)}. Правила змінюються, перед виходом гляньте свіжі новини.` }))),
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
    return h('li', { class: 'reason', tabindex: '0', 'data-tip': say, 'aria-label': say },
      h('p', { class: 'reason-text' }, h('span', { text: r.text }), h('b', { class: 'reason-val', text: String(r.value ?? '') })),
      h('div', { class: 'reason-bar' },
        h('span', { class: 'reason-track' },
          h('span', { class: `reason-fill ${up ? 'up' : 'down'}`, style: `left:${up ? 50 : 50 - w}%;width:${w}%` })),
        h('span', { class: 'reason-w', text: sign(r.logit) })))
  })
  const box = h('div', { class: 'reasons-box' }, h('ul', { class: 'reasons' }, rows), tip)
  tips(box, tip)
  const csv = ['key,text,value,logit', ...rs.map((r) => [r.key, r.text, r.value, r.logit].map(cell).join(','))].join('\n')
  return [
    h('div', { class: 'reason-axis', 'aria-hidden': 'true' }, h('span', { text: '← знижує ризик' }), h('span', { text: 'підвищує ризик →' })),
    box,
    h('p', { class: 'src' }, h('a', { href: `data:text/csv;charset=utf-8,${encodeURIComponent(`﻿${csv}`)}`, download: 'prychyny.csv', text: 'Сирі дані, CSV' })),
  ]
}

// d) glossary

function glossary(now, model) {
  const b = now?.forecast?.busy_at ?? model?.busy_at
  const hi = now?.forecast?.high_at ?? model?.high_at
  const known = isNum(b) && isNum(hi)
  const items = [
    ['ТАК', 'go', known ? `ймовірність менша за ${pct1(b)}: найпевніше, за 3 години не прилетить нічого` : 'найнижчий з трьох рівнів ризику'],
    ['РИЗИКОВАНО', 'risk', known ? `від ${pct1(b)} до ${pct1(hi)}: може бути і так, і так` : 'середній з трьох рівнів ризику'],
    ['НІ', 'stop', known ? `${pct1(hi)} і більше: прилітає частіше, ніж зазвичай` : 'найвищий з трьох рівнів ризику'],
    ['Ймовірність', null, 'як часто після схожих годин у минулому прилітало: 30% це приблизно 3 рази з 10'],
    ['Жовтий рівень', 'risk', 'загроза дронів: червона лінія метро через Дніпро не їде, зелена їде'],
    ['Червоний рівень', 'stop', 'ракети або масована атака дронів: одразу в укриття, метро через Дніпро не їде'],
  ]
  return [
    h('dl', { class: 'gloss' }, items.map(([term, sw, text]) => h('div', {},
      h('dt', {}, sw && h('i', { class: `sw sw-${sw}`, 'aria-hidden': 'true' }), term),
      h('dd', { text })))),
    h('p', { class: 'src' }, 'Рівні тривоги: ',
      h('a', { href: LEVEL_SOURCE.url, target: '_blank', rel: 'noopener', text: LEVEL_SOURCE.text }),
      '. Межі рівнів ризику взято з даних розробки.'),
  ]
}

// e) live sources

function sources(now, meta, model) {
  const chans = (meta?.channels || []).slice()
    .sort((a, b) => String(b.last_post || '').localeCompare(String(a.last_post || '')))
  const pl = meta?.pipeline
  const md = now?.model || model
  const jev = meta?.jev
  const facts = [
    ['Збір даних', pl?.last_cycle ? `останній цикл ${ago(pl.last_cycle)}` : 'даних про цикл ще немає'],
    ['Найсвіжіший пост', now?.data_until ? `${kyivStamp(now.data_until)}, ${ago(now.data_until)}` : 'ще немає'],
    ['Модель', md?.trained_at ? `навчена ${kyivStamp(md.trained_at)} на ${num(md.rows)} годинах` : 'ще не готова'],
    ['Jev читає пости', jev
      ? `${num(jev.calls)} ${isNum(jev.calls) ? plural(jev.calls, CALLS) : 'запитів'}, $${isNum(jev.usd) ? jev.usd.toFixed(2) : '?'}`
      : 'даних ще немає'],
  ]
  const day1 = 24 * 3600 * 1000
  return [
    h('dl', { class: 'facts' }, facts.map(([k, v]) => h('div', {}, h('dt', { text: k }), h('dd', { text: v })))),
    chans.length
      ? h('ul', { class: 'chans', 'aria-label': `Telegram-канали, ${chans.length}` }, chans.map((c) => {
        const old = !c.last_post || Date.now() - new Date(c.last_post).getTime() > day1
        const when = c.last_post ? ago(c.last_post) : 'постів ще не було'
        return h('li', { class: `chan${old ? ' is-old' : ''}`, title: `${c.name}: останній пост ${when}` },
          h('span', { class: 'chan-name', text: c.name }), h('span', { class: 'chan-ago', text: when }))
      }))
      : calm('Список каналів ще не готовий.'),
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

// g) the crossing picture: hero.js when it is there, else the small train on the bridge (index.html)

function heroMap(root, data) {
  const el = root.querySelector('#hero-map')
  if (!el) return
  heroLoad ??= import('./hero.js').then((m) => (typeof m?.mountHero === 'function' ? m : null), () => null)
  heroLoad.then(async (mod) => {
    if (!mod) return
    try {
      if (typeof heroInst?.update === 'function') heroInst.update(data)
      else heroInst = (await mod.mountHero(el, data)) || {}
    } catch (err) {
      console.warn('hero', err)
    }
  })
}

// The trick: the train of the red line M1 on the bridge. It crosses the Dnipro; in an alert it does what M1 does:
// rolls up to the bridge, stops at the edge and goes back under ground. The arch shows the status of M1 now
// (green: it crosses, red: it does not). Transform only, 400 ms moves.

const TRAIN = { cross: 342, edge: 42, dur: 400, pause: 700 }
let side = 0 // 0: on the right bank (west, left in the picture), 1: on the left bank
let busy = false
let tipTimer = 0

function move(node, x) {
  node.style.transition = RM.matches ? 'none' : `transform ${TRAIN.dur}ms var(--ease)`
  node.style.transform = `translateX(${x}px)`
}

function trainText() {
  const m1 = crossingsFor(alertLevel).find((c) => c.id === 'm1')
  const state = m1 ? `${m1.name}, ${m1.via}: ${STATUS_WORD[m1.status] || STATUS_WORD.unknown}. ` : ''
  return `${state}Натисни або T: ${alertNow ? 'подивись, що робить потяг.' : 'потяг перетне Дніпро.'}`
}

function trainTip(text) {
  const tip = document.getElementById('train-tip')
  if (!tip) return
  tip.textContent = text || ''
  tip.hidden = !text
}

function say(text) { // the live hint for screen readers and, for a moment, the tooltip on the picture
  const hint = document.getElementById('train-hint')
  if (hint) hint.textContent = text
  trainTip(text)
  clearTimeout(tipTimer)
  tipTimer = setTimeout(() => { if (document.activeElement?.id !== 'train') trainTip('') }, 2400)
}

function paintTrain() {
  const btn = document.getElementById('train')
  if (btn) btn.dataset.m1 = m1Status
  const hint = document.getElementById('train-hint')
  if (hint && !hint.textContent) hint.textContent = trainText()
}

function bindTrain() {
  const btn = document.getElementById('train')
  if (!btn) return
  bound = true
  btn.addEventListener('click', () => runTrain())
  btn.addEventListener('pointerenter', () => trainTip(trainText()))
  btn.addEventListener('pointerleave', () => { if (document.activeElement !== btn) trainTip('') })
  btn.addEventListener('focus', () => trainTip(trainText()))
  btn.addEventListener('blur', () => trainTip(''))
}

export function runTrain() {
  if (typeof heroInst?.train === 'function') {
    heroInst.train()
    return
  }
  const car = document.getElementById('train-car')
  if (!car || busy) return
  const base = side ? TRAIN.cross : 0
  if (alertNow) {
    say('Тривога: червона лінія не виходить на міст і повертається під землю.')
    if (RM.matches) return
    busy = true
    move(car, side ? base - TRAIN.edge : base + TRAIN.edge)
    setTimeout(() => move(car, base), TRAIN.dur + TRAIN.pause)
    setTimeout(() => { busy = false }, 2 * TRAIN.dur + TRAIN.pause)
    return
  }
  side = 1 - side
  move(car, side ? TRAIN.cross : 0)
  say(side ? 'Потяг на лівому березі. Ще раз, і він повернеться.' : 'Потяг знову на правому березі.')
}
