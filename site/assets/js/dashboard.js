// Tab 1 "Відповідь" of kyianyn-routine.isakov.fyi. It answers one question: will you make it to the other bank of the
// Dnipro in the next 3 hours. The hero, top to bottom: the pills (alert, curfew, late data), the question with its
// window, the answer (Так, Ризиковано or Ні in the colour of its tier), one line, the crossing map, the probability on
// a 3-part scale, at most two chips (details in tooltips) and the safety line. Below, every block folded: what crosses
// the Dnipro now, why this forecast, the charts (charts.js, mounted by app.js on the first open of their block), the
// words and the live sources. Live numbers come from site/api/*.json at runtime (app.js loads them, the contract is
// in docs/ARCHITECTURE.md, section "Живий сайт").
//
// The crossing picture #hero-map (aspect ratio 2:1, site.css) shows the small train on the bridge until
// ./hero.js loads. When it does, mountHero(el, data) draws in it; it may return { update(data), train() }:
// update gets every new data, train runs on the key T. Without update, mountHero is called again on new data.

import { kyivTime, kyivDay, kyivStamp, pct, ago } from './api.js'
import { CURFEW, CHECKED, SOURCES, crossingsFor } from './crossing.js'

// Where the yellow and red levels are defined (the lore notes, section "Рівні тривоги").
const LEVEL_SOURCE = { text: 'kyiv.news, 03.09.2026', url: 'https://kyiv.news/bezpeka-kriminal/kyiv-vvodyt-zhovtyi-chervonyi-rivni-tryvohy/' }

// The answer and its one line by the shown tier; level is the word of the risk scale.
const TIER = {
  low: { word: 'Так', line: 'Атаки, найімовірніше, не буде.', level: 'низький' },
  medium: { word: 'Ризиковано', line: 'Атака можлива. Якщо треба, їдь зараз.', level: 'середній' },
  high: { word: 'Ні', line: 'Краще не їхати найближчі 3 години.', level: 'високий' },
}
const ORDER = ['low', 'medium', 'high']
// The pill above the question while an alert is on; an alert without a level stops at least the red line.
const ALERT_FLAG = {
  yellow: 'Жовта тривога: з метро через Дніпро ходить лише зелена лінія',
  red: 'Червона тривога: метро через Дніпро не ходить',
  alert: 'Тривога: червона лінія метро через Дніпро не ходить',
}
const ALERT_STATE = { yellow: 'Зараз жовта тривога.', red: 'Зараз червона тривога.', alert: 'Зараз тривога, рівень не названо.' }
const STATUS_WORD = { open: 'відкрито', limited: 'обмежено', closed: 'закрито', unknown: 'невідомо' }
const METRO = new Set(['m1', 'm3'])
const PATH = {
  open: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7 5.3-5.7"/>',
  limited: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>',
  closed: '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
  unknown: '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.6a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5v.5M12 16.9v.1"/>',
  siren: '<path d="M7 18v-5a5 5 0 0 1 10 0v5"/><path d="M5 18h14v2.5H5z"/><path d="M12 3.5V5M4.5 6.5l1.2 1.2M19.5 6.5l-1.2 1.2"/>',
  moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
  late: '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17v.1"/>',
  drone: '<path d="M12 4l8.5 14L12 15l-8.5 3z"/>',
  rocket: '<path d="M12 2.5c3 2.4 4.2 6 4.2 10.5L12 17.5 7.8 13C7.8 8.5 9 4.9 12 2.5z"/><path d="M7.8 13 5 16v3.5l3.5-2.2M16.2 13l2.8 3v3.5l-3.5-2.2"/>',
  past: '<path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1"/><path d="M3.5 4v4.5H8"/><path d="M12 7.5V12l3 2"/>',
}
const TIMES = ['раз', 'рази', 'разів']
const ANSWERS = ['відповідь', 'відповіді', 'відповідей']
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
// Each sentence wraps as a whole (site.css .sent), so a short line never leaves one word alone on its second line.
const sentences = (text) => text.split(/(?<=\.) /).flatMap((s, i) => [i ? ' ' : null, h('span', { class: 'sent', text: s })]).filter(Boolean)
const isNum = (x) => typeof x === 'number' && Number.isFinite(x)
const num = (x) => (isNum(x) ? x.toLocaleString('uk-UA') : '?')
const pct1 = (x) => pct(x, 1).replace(/\.0%$/, '%') // thresholds: 0.197 -> "19.7%", 0.3 -> "30%"
const sign = (x) => `${x < 0 ? '-' : '+'}${Math.abs(x).toFixed(2)}`
const day = (iso) => String(iso).slice(0, 10).split('-').reverse().join('.') // "2026-07-04" -> "04.07.2026"
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

let tierNow = null // the model's own tier
let answerTier = null // the tier the answer shows: the model's, but never Так while an alert holds the metro
let alertNow = false
let alertLevel = null
let m1Status = 'open'
let bound = false
let heroLoad = null
let heroInst = null
let lastWord = ''

export function renderDashboard(root, data) {
  const now = data.now
  const f = forecastOf(now)
  tierNow = f ? tierOf(f) : null
  alertNow = Boolean(now?.now?.alert)
  alertLevel = alertNow ? (ALERT_FLAG[now.now.level] ? now.now.level : 'alert') : null
  m1Status = crossingsFor(alertLevel).find((c) => c.id === 'm1')?.status || 'unknown'
  answerTier = f ? shownTier(tierNow, alertLevel) : null
  const hero = root.querySelector('#hero')
  if (hero) hero.dataset.tier = answerTier || 'none'
  if (!bound) bindTrain()
  renderPills(root, data)
  part(root, 'window', () => windowText(now))
  part(root, 'answer', () => answer(f))
  part(root, 'line', () => (f ? sentences(TIER[answerTier].line) : 'Відповідь з’явиться, щойно будуть перші дані.'))
  part(root, 'prob', () => prob(f))
  part(root, 'chips', () => chips(now, f))
  part(root, 'crossings', () => crossings(now))
  part(root, 'reasons', () => reasons(now))
  part(root, 'glossary', () => glossary(now, data.model))
  part(root, 'sources', () => sources(now, data.meta, data.model))
  // The first render happens under the loading skeleton (no width yet): fit in the next frame, after app.js reveals
  // the hero and before it paints, and again once the web fonts are in.
  requestAnimationFrame(() => fitAnswer(root))
  document.fonts?.ready.then(() => fitAnswer(root))
  paintTrain()
  heroMap(root, data)
}

// The pills above the question depend on the clock too (the curfew), so app.js redraws them every 30 seconds.
export function renderPills(root, data) {
  part(root, 'pills', () => pills(data.now))
  requestAnimationFrame(() => fitAnswer(root)) // the number of pills sets the size of the answer on a phone (site.css)
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

// Tooltips of a group (chips, reasons): one dark box under the row of the item, inside the group's width, so it never
// leaves the screen. The mouse shows it on hover, the keyboard on focus, a finger on a tap. It hides when the mouse
// leaves, on blur, on Escape, and on a tap of the same item or anywhere else: Safari on iPhone gives a tapped button
// no focus, so there no blur ever comes.
let openTip = null // { el, tip }: the item whose tooltip is shown now

function hideTip() {
  if (openTip) openTip.tip.hidden = true
  openTip = null
}

document.addEventListener('pointerdown', (e) => { if (openTip && !openTip.el.contains(e.target)) hideTip() }, true)
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hideTip() })

function tips(box, tip) {
  const show = (el) => {
    if (openTip && openTip.tip !== tip) hideTip()
    tip.textContent = el.dataset.tip
    tip.style.top = `${el.offsetTop + el.offsetHeight + 8}px`
    tip.hidden = false
    openTip = { el, tip }
  }
  for (const el of box.querySelectorAll('[data-tip]')) {
    let tap = false // this press is a finger or a pen
    let was = false // and the tooltip of this item was already open when it began
    el.addEventListener('pointerdown', (e) => {
      tap = e.pointerType !== 'mouse'
      was = openTip?.el === el && !tip.hidden
    })
    el.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse') show(el) })
    el.addEventListener('pointerleave', (e) => {
      if (e.pointerType === 'mouse' && openTip?.el === el && document.activeElement !== el) hideTip()
    })
    el.addEventListener('focus', () => show(el))
    el.addEventListener('blur', () => { if (openTip?.el === el) hideTip() })
    el.addEventListener('click', () => {
      if (was && (tap || openTip?.pinned)) hideTip()
      else {
        show(el)
        openTip.pinned = !tap
      }
      tap = false
      was = false
    })
  }
}

// a) the pills, the question's window, the answer, the probability and the chips

function forecastOf(now) {
  const f = now?.forecast
  return f && isNum(f.p) ? f : null
}

function tierOf(f) {
  if (TIER[f.tier]) return f.tier
  if (isNum(f.busy_at) && f.p < f.busy_at) return 'low'
  return isNum(f.high_at) && f.p >= f.high_at ? 'high' : 'medium'
}

// During an alert the metro already stops at the river (docs/product/crossing.md), so the answer never says Так:
// a red level means Ні (no metro crosses), a yellow or an unnamed level at least Ризиковано.
function shownTier(tier, level) {
  if (!level) return tier
  if (level === 'red') return 'high'
  return tier === 'low' ? 'medium' : tier
}

function inCurfew(at = new Date()) {
  const t = kyivTime(at.toISOString())
  return t >= CURFEW.from && t < CURFEW.to
}

// A pill above the question; the words before the first colon in bold ("Жовта тривога:"), so its kind reads first.
function flag(kind, ico, text, title) {
  const cut = text.indexOf(': ')
  const words = cut > 0 ? [h('b', { text: text.slice(0, cut + 1) }), text.slice(cut + 1)] : [text]
  return h('p', { class: `flag flag-${kind}`, title }, icon(ico), h('span', {}, words))
}

function pills(now) {
  const out = []
  if (now?.now?.alert) {
    const since = now.now.alert_since ? `Тривога з ${kyivTime(now.now.alert_since)}. ` : ''
    out.push(flag(alertLevel === 'yellow' ? 'yellow' : 'red', 'siren', ALERT_FLAG[alertLevel], `${since}Коли тривога, йди в укриття.`))
  }
  if (inCurfew()) out.push(flag('night', 'moon', `Комендантська година до ${CURFEW.to}`, `Щодня з ${CURFEW.from} до ${CURFEW.to}.`))
  if (now?.stale) {
    const at = now.hour || now.data_until
    const date = at && kyivDay(at) !== kyivDay(new Date().toISOString()) ? `${kyivDay(at)} ` : ''
    out.push(flag('stale', 'late', `Дані запізнюються: останні за ${at ? date + kyivTime(at) : '?'}`,
      'Нових даних поки немає, тож прогноз може бути застарілим.'))
  }
  return out
}

function windowText(now) {
  if (!now?.hour) return ''
  const d = kyivDay(now.hour)
  const end = now.window_end ? ` до ${kyivTime(now.window_end)}` : ''
  return `${d === kyivDay(new Date().toISOString()) ? '' : `${d}, `}з ${kyivTime(now.hour)}${end}`
}

// The word rises in only when it changes, with transform alone: it is in its full colour from the first frame.
function answer(f) {
  if (!f) return h('p', { class: 'answer answer-wait', text: 'Дані ще не готові' })
  const word = TIER[answerTier].word
  const fresh = word !== lastWord
  lastWord = word
  return h('p', { class: `answer answer-${answerTier}${fresh ? ' answer-new' : ''}`, text: word })
}

// The longest answer, Ризиковано, must fit its box on a phone: shrink the type until it does.
function fitAnswer(root = document) {
  const box = root.querySelector('.hero-answer')
  const el = box?.querySelector('.answer')
  if (!el || el.classList.contains('answer-wait')) return
  el.style.fontSize = ''
  const room = box.clientWidth
  const need = el.scrollWidth
  if (room > 0 && need > room) {
    el.style.fontSize = `${Math.floor(parseFloat(getComputedStyle(el).fontSize) * (room / need) * 0.97)}px`
  }
}

let fitFrame = 0
window.addEventListener('resize', () => {
  cancelAnimationFrame(fitFrame)
  fitFrame = requestAnimationFrame(() => fitAnswer())
})

function prob(f) {
  if (!f) return null
  return [
    h('p', { class: 'p-row' }, h('b', { class: `p-num p-${tierNow}`, text: pct(f.p) }), // the model's own colour, also when an alert raises the answer
      h('span', { class: 'p-label', text: 'ймовірність атаки дронів або ракет на Київ у ці 3 години' })),
    meter(f),
  ]
}

// The scale in three equal parts, низький, середній, високий, with the two thresholds at their borders; the mark
// sits inside the part of the model's own tier, in proportion within it.
function meter(f) {
  const b = f.busy_at
  const hi = f.high_at
  const known = isNum(b) && isNum(hi) && b > 0 && b < hi && hi < 1
  const p = Math.max(0, Math.min(1, f.p))
  const pos = !known ? p
    : p < b ? p / b / 3
      : p < hi ? 1 / 3 + (p - b) / (hi - b) / 3
        : 2 / 3 + (p - hi) / (1 - hi) / 3
  const at = (x) => `${(100 * x).toFixed(2)}%`
  const say = known
    ? `Шкала ризику: низький до ${pct1(b)}, середній від ${pct1(b)} до ${pct1(hi)}, високий від ${pct1(hi)}. Зараз ${pct(f.p)}, ризик ${TIER[tierNow].level}.`
    : `Зараз ${pct(f.p)}, ризик ${TIER[tierNow].level}.`
  return h('div', { class: 'meter', role: 'img', 'aria-label': say, title: say },
    known && h('div', { class: 'meter-cuts', 'aria-hidden': 'true' },
      h('span', { style: `left:${at(1 / 3)}`, text: pct1(b) }),
      h('span', { style: `left:${at(2 / 3)}`, text: pct1(hi) })),
    h('div', { class: 'meter-bar' },
      h('span', { class: 'zone zone-go' }),
      h('span', { class: 'zone zone-risk' }),
      h('span', { class: 'zone zone-stop' }),
      h('span', { class: 'meter-mark', style: `left:${at(pos)}` })),
    h('div', { class: 'meter-words', 'aria-hidden': 'true' },
      ORDER.map((t) => h('span', { class: t === tierNow ? 'is-on' : null, text: TIER[t].level }))))
}

function chip(ico, text, tip) {
  return h('button', { type: 'button', class: 'chip', 'data-tip': tip, 'aria-label': `${text}. ${tip}` }, icon(ico), h('span', { text }))
}

// Two chips at most, both from forecast.kind, the past hours when the model gave its own tier of now and the hour was
// calm (no alert, no attack) when it did: n is how many such forecasts, busy_share the share followed by an attack in
// 3 hours, missile_share and drone_only_share the shares of those attacks with missiles or with drones only. The
// record chip hides during an alert: those hours were all calm ones.
function chips(now, f) {
  const k = f?.kind
  if (!k || !isNum(k.n) || k.n <= 0) return null
  const said = `«${TIER[tierNow].level} ризик»` // the words of the scale, never forecast.label
  const when = period(k.period)
  const items = []
  // The two whole percents of a pair always add up to 100%: the second is 100 minus the first (64% and 36%).
  if (isNum(k.missile_share)) {
    const rockets = Math.round(k.missile_share * 100)
    const drones = 100 - rockets
    const missiles = rockets >= drones
    items.push(chip(missiles ? 'rocket' : 'drone',
      missiles ? `якщо атака, то в ${rockets}% з ракетами` : `якщо атака, то в ${drones}% лише дрони`,
      `Атаки після прогнозів ${said} ${when}: з ракетами ${rockets}%, лише дрони ${drones}%. Масовану ракетну атаку модель майже не відрізняє від атаки дронів.`))
  }
  if (isNum(k.busy_share) && !alertNow) {
    const hit = Math.round(k.busy_share * 100)
    items.push(chip('past', `атака була після ${hit}% таких прогнозів`, [
      `Модель казала ${said} ${num(k.n)} ${plural(k.n, TIMES)} ${when}, щоразу о спокійній годині.`,
      `Атака за 3 години після цього була у ${hit}% випадків, спокійно було у ${100 - hit}%.`,
      now?.now?.quiet_now === false ? 'Зараз година не спокійна, тож цей прогноз перевірено менше.' : '',
    ].filter(Boolean).join(' ')))
  }
  if (!items.length) return null
  const tip = h('p', { class: 'tip', role: 'tooltip', hidden: true })
  const box = h('div', { class: 'chips' }, items, tip)
  tips(box, tip)
  return box
}

// b) what crosses the Dnipro now: every crossing with its status, the curfew and the sources

function crossings(now) {
  const level = now?.now?.alert ? (ALERT_FLAG[now.now.level] ? now.now.level : 'alert') : null
  const state = !now ? 'Стан тривоги невідомий, показано як без тривоги.' : level ? ALERT_STATE[level] : 'Зараз тривоги немає.'
  const curfew = inCurfew() // until it ends nobody crosses without a pass, whatever the alert
  const rows = crossingsFor(level).map((c) => {
    const st = curfew ? 'closed' : STATUS_WORD[c.status] ? c.status : 'unknown'
    const note = curfew ? `до ${CURFEW.to} комендантська година, без перепустки не можна` : c.note
    return h('li', { class: `cross-row is-${st}` }, icon(st),
      h('div', { class: 'cross-txt' },
        h('p', { class: 'cross-name' },
          METRO.has(c.id) && h('i', { class: `metro metro-${c.id}`, 'aria-hidden': 'true' }),
          h('b', { text: c.name }), h('span', { class: 'cross-via', text: c.via })),
        h('p', { class: 'cross-note' }, h('b', { class: 'cross-st', text: STATUS_WORD[st] }), `: ${note}`)))
  })
  return [
    h('ul', { class: 'cross-list' }, rows),
    h('p', { class: 'cross-meta' }, icon('moon'),
      h('span', { text: curfew ? `${state} Зараз комендантська година, до ${CURFEW.to}.` : `${state} Комендантська година щодня з ${CURFEW.from} до ${CURFEW.to}.` })),
    h('details', { class: 'srcs' }, h('summary', { text: `Джерела, ${SOURCES.length}` }),
      h('ul', {}, SOURCES.map((s) => h('li', {},
        h('a', { href: s.url, target: '_blank', rel: 'noopener', text: s.title }),
        h('span', { class: 'src', text: `, ${day(s.date)}` })))),
      h('p', { class: 'src', text: `Перевірено ${day(CHECKED)}. Правила змінюються, перед виїздом глянь свіжі новини.` })),
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
    h('p', { class: 'src' }, h('a', { href: `data:text/csv;charset=utf-8,${encodeURIComponent(`﻿${csv}`)}`, download: 'prychyny.csv', text: 'Завантажити таблицю' })),
  ]
}

// d) the words

function glossary(now, model) {
  const b = now?.forecast?.busy_at ?? model?.busy_at
  const hi = now?.forecast?.high_at ?? model?.high_at
  const known = isNum(b) && isNum(hi)
  const items = [
    ['Так', 'go', known ? `ймовірність атаки менша за ${pct1(b)}: ризик низький` : 'ризик атаки низький'],
    ['Ризиковано', 'risk', known ? `ймовірність атаки від ${pct1(b)} до ${pct1(hi)}: ризик середній` : 'ризик атаки середній'],
    ['Ні', 'stop', known ? `ймовірність атаки ${pct1(hi)} і більше: ризик високий` : 'ризик атаки високий'],
    ['Ймовірність', null, 'як часто після схожих годин у минулому була атака: 28% це приблизно 3 рази з 10'],
    ['Атака', null, 'дрони летять на Київ, ракетна загроза або удар'],
    ['Спокійна година', null, 'на момент прогнозу немає ні тривоги, ні атаки'],
    ['Тривога', null, 'офіційна повітряна тривога в Києві; під час неї відповідь ніколи не «Так»'],
    ['Жовтий рівень', 'risk', 'загроза дронів: червона лінія метро через Дніпро не ходить, зелена ходить'],
    ['Червоний рівень', 'stop', 'ракети або масована атака: метро через Дніпро не ходить, одразу в укриття'],
    ['Комендантська година', null, `щодня з ${CURFEW.from} до ${CURFEW.to}: без перепустки на вулиці бути не можна`],
  ]
  return [
    h('dl', { class: 'gloss' }, items.map(([term, sw, text]) => h('div', {},
      h('dt', {}, sw && h('i', { class: `sw sw-${sw}`, 'aria-hidden': 'true' }), term),
      h('dd', { text })))),
    h('p', { class: 'src' }, 'Рівні тривоги: ',
      h('a', { href: LEVEL_SOURCE.url, target: '_blank', rel: 'noopener', text: LEVEL_SOURCE.text }),
      known ? `. Межі ${pct1(b)} і ${pct1(hi)} обрано на навчальних даних (до 28.08).` : '.'),
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
    ['Перевірка каналів', pl?.last_cycle ? ago(pl.last_cycle) : 'ще не було'],
    ['Останній пост', now?.data_until ? `${kyivStamp(now.data_until)}, ${ago(now.data_until)}` : 'ще немає'],
    ['Модель', md?.trained_at ? `навчена ${kyivStamp(md.trained_at)} на ${num(md.rows)} годинах` : 'ще не готова'],
    ['ШІ читає пости', jev
      ? `${num(jev.calls)} ${isNum(jev.calls) ? plural(jev.calls, ANSWERS) : 'відповідей'} Jev збережено, $${isNum(jev.usd) ? jev.usd.toFixed(2) : '?'}`
      : 'даних ще немає'],
  ]
  const day1 = 24 * 3600 * 1000
  return [
    h('dl', { class: 'facts' }, facts.map(([k, v]) => h('div', {}, h('dt', { text: k }), h('dd', { text: v })))),
    h('p', { class: 'sub', text: 'Публічні канали в Telegram' }),
    chans.length
      ? h('ul', { class: 'chans', 'aria-label': `Канали в Telegram, ${chans.length}` }, chans.map((c) => {
        const old = !c.last_post || Date.now() - new Date(c.last_post).getTime() > day1
        const when = c.last_post ? ago(c.last_post) : 'постів ще не було'
        return h('li', { class: `chan${old ? ' is-old' : ''}`, title: `${c.name}: останній пост ${when}` },
          h('span', { class: 'chan-name', text: c.name }), h('span', { class: 'chan-ago', text: when }))
      }))
      : calm('Список каналів ще не готовий.'),
  ]
}

// f) charts: another file (charts.js) draws them; app.js calls this on the first open of their folded block

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
  btn.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse') trainTip(trainText()) })
  btn.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse' && document.activeElement !== btn) trainTip('') })
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
