// Charts of the main tab (#/): the forecast against what really happened, whether its numbers can be trusted, and
// the days by hour. mountCharts(root, data) finds the [data-chart] containers inside root ("timeline", "calibration",
// "days"), draws each one as its own card with D3 v7 (the global d3) and returns {redraw(data)}.
// data is what loadAll() in api.js returns: history (hours, tiers, tiers_since_test, calibration), now and model.
// Every number comes from the JSON at runtime. The timeline has three forms for the same question, set by data-form
// on its container: "bars" (default), "line" or "lanes".

import { kyivDay, kyivStamp, pct } from './api.js'

const HOUR = 3600e3
const DAY = 24 * HOUR
const TIER = { low: 'швидше тихо', medium: 'середній ризик', high: 'високий ризик' }
// The test period starts 2026-08-29 12:00 Kyiv (docs/quiet/model.md, "Розробка і тест"); tiers_since_test counts
// hours from it.
const TEST_START = Date.parse('2026-08-29T09:00:00Z')
// Dark end of the sequential palette of the viz skill (white, pink, dark pink); the other two stops are tokens.
const SEQ_DARK = '#5C0438'
// Calibration rows with fewer hours are drawn pale because their share is shaky (a display rule, not research).
const FEW = 30
const RANGES = [['7', '7 днів', 7], ['30', '30 днів', 30], ['all', 'усе', Infinity]]
const FORMS = ['bars', 'line', 'lanes']

const READ = {
  bars: 'Кожен стовпчик це година: висота показує прогноз моделі, колір показує, що сталося за 3 години після. Добрий прогноз: високі стовпчики рожеві, низькі сірі.',
  line: 'Лінія це прогноз моделі по годинах, рожеві смуги це години, після яких справді було неспокійно. Добрий прогноз: лінія висока на смугах і низька між ними.',
  lanes: 'Згори прогноз моделі по годинах, знизу що сталося: рожеві риски це неспокійні вікна, чорні це тривоги. Добрий прогноз: гора стоїть над рисками.',
}
const KEYS = {
  bars: [['busy', 'потім неспокійно'], ['calm', 'потім тихо'], ['unknown', 'ще невідомо'], ['alert', 'тривога'], ['live', 'наживо'], ['limit', 'межі рівнів']],
  line: [['line', 'прогноз'], ['band', 'потім неспокійно'], ['alert', 'тривога'], ['live', 'наживо'], ['limit', 'межі рівнів']],
  lanes: [['area', 'прогноз'], ['busy', 'потім неспокійно'], ['alert', 'тривога'], ['live', 'наживо'], ['limit', 'межі рівнів']],
}

const PARTS = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Kyiv', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', hourCycle: 'h23' })
const WEEKDAY = new Intl.DateTimeFormat('uk-UA', { timeZone: 'Europe/Kyiv', weekday: 'short' })

const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null)
const int = (n) => Math.round(n).toLocaleString('uk-UA')
const share = (v) => (v == null ? 'немає' : pct(v))
const limPct = (v) => pct(v, Math.abs(v * 100 - Math.round(v * 100)) < 1e-6 ? 0 : 1)
const hh = (h) => String(h).padStart(2, '0')
const iso = (ms) => new Date(ms).toISOString()
const binName = (b) => `${Math.round(b.from * 100)}-${Math.round(b.to * 100)}%`
const plural = (n, one, few, many) => {
  const a = n % 10, b = n % 100
  return a === 1 && b !== 11 ? one : a >= 2 && a <= 4 && (b < 12 || b > 14) ? few : many
}

export function mountCharts(root, data) {
  const st = { data: {}, hours: [], lim: {}, range: '7', anim: true }
  const boxes = [...root.querySelectorAll('[data-chart]')]
  const widths = new WeakMap()
  const set = (next) => {
    st.data = next || {}
    st.hours = prep(st.data.history)
    st.lim = limits(st.data)
  }
  const draw = (box) => {
    const fn = DRAW[box.dataset.chart]
    if (!fn) return
    const focused = [...box.querySelectorAll('.ch-svg')].indexOf(document.activeElement)
    fn(box, st)
    if (focused >= 0) box.querySelectorAll('.ch-svg')[focused]?.focus({ preventScroll: true })
  }
  set(data)
  for (const box of boxes) {
    widths.set(box, box.clientWidth)
    draw(box)
  }
  st.anim = false
  const ro = new ResizeObserver((entries) => {
    for (const e of entries) {
      const w = e.target.clientWidth
      if (w !== widths.get(e.target)) {
        widths.set(e.target, w)
        draw(e.target)
      }
    }
  })
  boxes.forEach((b) => ro.observe(b))
  // A tap outside every chart closes the open tooltips (on a phone there is no pointer leaving).
  document.addEventListener('pointerdown', (e) => {
    if (e.target.closest?.('.ch-plot')) return
    for (const b of boxes) for (const f of b._hide || []) f()
  })
  return {
    redraw(next) {
      set(next)
      boxes.forEach(draw)
    },
  }
}

const DRAW = { timeline: drawTimeline, calibration: drawCalibration, days: drawDays }

// ---- data ----

function kyiv(ms) {
  const o = {}
  for (const p of PARTS.formatToParts(ms)) o[p.type] = p.value
  return { day: `${o.year}-${o.month}-${o.day}`, hour: Number(o.hour) % 24 }
}

function prep(history) {
  const raw = Array.isArray(history?.hours) ? history.hours : []
  const out = []
  for (const h of raw) {
    const ms = Date.parse(h?.t)
    if (!Number.isFinite(ms) || num(h.p) == null) continue
    out.push({ ...h, ms, ...kyiv(ms) })
  }
  return out.sort((a, b) => a.ms - b.ms)
}

function limits(data) {
  const f = data?.now?.forecast || {}
  const m = data?.model || {}
  return { busyAt: num(f.busy_at) ?? num(m.busy_at), highAt: num(f.high_at) ?? num(m.high_at) }
}

// The scores of the tiles: hours that were quiet at forecast time and whose 3 hour window is over.
function score(hours) {
  const k = hours.filter((h) => h.quiet_now && h.busy_3h != null)
  const busy = k.filter((h) => h.busy_3h)
  const said = k.filter((h) => h.tier === 'low')
  const part = (a, b) => (b ? a / b : null)
  return {
    n: k.length, nBusy: busy.length, nSaid: said.length,
    busy: part(busy.length, k.length),
    caught: part(busy.filter((h) => h.tier !== 'low').length, busy.length),
    quietTrue: part(said.filter((h) => !h.busy_3h).length, said.length),
  }
}

// Contiguous runs of hours that pass a test, as [start, end) in ms.
function runs(hours, test) {
  const out = []
  let r = null
  for (const h of hours) {
    if (!test(h)) { r = null; continue }
    if (r && h.ms === r.end) r.end = h.ms + HOUR
    else out.push((r = { start: h.ms, end: h.ms + HOUR }))
  }
  return out
}

function happened(h) {
  if (h.busy_3h == null) return 'ще невідомо, вікно не скінчилось'
  if (!h.busy_3h) return 'тихо'
  const what = [h.drone_3h && 'дрони', h.missile_3h && 'ракети'].filter(Boolean)
  return what.length ? `неспокійно, ${what.join(' і ')}` : 'неспокійно'
}

function hourLines(h) {
  return [
    `${WEEKDAY.format(h.ms)}, ${kyivStamp(h.t)} за Києвом`,
    `Прогноз: ${pct(h.p)}, ${TIER[h.tier] || h.tier}`,
    `Наступні 3 год: ${happened(h)}`,
    `Тривога в цю годину: ${h.alert ? 'так' : 'ні'}`,
    h.source === 'live' ? 'Записано наживо' : 'Відтворення: модель знала лише минуле',
  ]
}

const hourRow = (h) => ({
  t_utc: h.t, kyiv: `${h.day} ${hh(h.hour)}:00`, p: h.p, tier: h.tier, source: h.source, quiet_now: h.quiet_now,
  alert: h.alert, busy_3h: h.busy_3h, drone_3h: h.drone_3h, missile_3h: h.missile_3h,
})

function tierRange(k, { busyAt, highAt }) {
  if (busyAt == null || highAt == null) return ''
  if (k === 'low') return `, прогноз до ${limPct(busyAt)}`
  if (k === 'medium') return `, прогноз ${limPct(busyAt)}-${limPct(highAt)}`
  return `, прогноз від ${limPct(highAt)}`
}

// ---- DOM helpers ----

function el(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue
    if (k === 'text') node.textContent = v
    else if (k === 'class') node.className = v
    else if (k === 'on') for (const [ev, f] of Object.entries(v)) node.addEventListener(ev, f)
    else node.setAttribute(k, v === true ? '' : v)
  }
  for (const kid of kids.flat()) if (kid != null) node.append(kid)
  return node
}

function card(box, id, title, sub) {
  box.textContent = ''
  box._hide = []
  const art = el('article', { class: 'ch-card', 'aria-labelledby': `ch-${id}-t` },
    el('h3', { class: 'ch-title', id: `ch-${id}-t`, text: title }),
    sub ? el('p', { class: 'ch-sub', text: sub }) : null)
  box.append(art)
  return art
}

const calm = (art, text) => art.append(el('p', { class: 'ch-calm', text }))
const note = (text) => el('p', { class: 'ch-note', text })
const plotClass = (st) => (st.anim ? 'ch-plot ch-in' : 'ch-plot')

function tiles(list) {
  return el('div', { class: 'ch-tiles' }, list.map(([label, value, sub]) =>
    el('div', { class: 'ch-tile' },
      el('span', { class: 'ch-tile-label', text: label }),
      el('strong', { class: 'ch-tile-value', text: value }),
      el('span', { class: 'ch-tile-note', text: sub || '' }))))
}

function legend(items) {
  return el('ul', { class: 'ch-legend' }, items.map(([k, text]) =>
    el('li', {}, el('span', { class: `ch-key ch-key-${k}` }), text)))
}

function footer(name, rows) {
  const raw = el('a', { class: 'ch-raw', href: '#', download: `${name}.csv`, text: 'Сирі дані (CSV)' })
  raw.addEventListener('click', () => {
    const list = rows()
    const cols = list.length ? Object.keys(list[0]) : []
    const cell = (v) => (v == null ? '' : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v))
    const csv = [cols.join(','), ...list.map((r) => cols.map((c) => cell(r[c])).join(','))].join('\n')
    if (raw.href.startsWith('blob:')) URL.revokeObjectURL(raw.href)
    raw.href = URL.createObjectURL(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }))
  })
  return el('footer', { class: 'ch-foot' }, raw,
    el('a', { class: 'ch-credit', href: 'https://isakov.fyi', text: 'ЄІ', 'aria-label': 'Автор: isakov.fyi' }))
}

function newSvg(wrap, W, H, label) {
  return d3.select(wrap).append('svg').attr('class', 'ch-svg').attr('width', W).attr('height', H)
    .attr('viewBox', `0 0 ${W} ${H}`).attr('tabindex', 0).attr('role', 'group').attr('aria-label', label)
}

function tipFor(wrap) {
  const tip = el('div', { class: 'ch-tip', 'aria-hidden': 'true' })
  wrap.append(tip)
  return {
    show(x, y, lines) {
      tip.replaceChildren(...lines.map((t, i) => el(i ? 'span' : 'strong', { text: t })))
      tip.classList.add('on')
      const left = Math.max(0, Math.min(x - tip.offsetWidth / 2, wrap.clientWidth - tip.offsetWidth))
      let top = y - tip.offsetHeight - 14
      if (top < 0) top = y + 18
      tip.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`
    },
    hide() { tip.classList.remove('on') },
  }
}

const srLive = (wrap) => wrap.appendChild(el('p', { class: 'ch-sr', 'aria-live': 'polite' }))

// Hover, tap and keyboard for one chart: pick(x, y) maps a pointer to an item, show(i) draws it and returns the lines.
// Arrows left and right move by one item, Shift by 24 (a day of hours), Home and End jump, Esc hides.
function bind(box, svg, live, n, start, pick, show, hide) {
  let cur = null
  const go = (i, kb) => {
    if (i == null || i < 0 || i >= n) return
    cur = i
    const lines = show(i)
    if (kb) live.textContent = lines.join('. ')
  }
  const at = (e) => {
    const r = svg.getBoundingClientRect()
    return pick(e.clientX - r.left, e.clientY - r.top)
  }
  svg.addEventListener('pointermove', (e) => go(at(e)))
  svg.addEventListener('pointerdown', (e) => go(at(e)))
  svg.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse' && document.activeElement !== svg) hide() })
  svg.addEventListener('focus', () => go(cur ?? start, true))
  svg.addEventListener('blur', hide)
  svg.addEventListener('keydown', (e) => {
    let i = cur ?? start
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') i += (e.key === 'ArrowRight' ? 1 : -1) * (e.shiftKey ? 24 : 1)
    else if (e.key === 'Home') i = 0
    else if (e.key === 'End') i = n - 1
    else {
      if (e.key === 'Escape') hide()
      return
    }
    e.preventDefault()
    e.stopPropagation()
    go(Math.max(0, Math.min(n - 1, i)), true)
  })
  box._hide.push(hide)
}

// ---- 1. timeline: the forecast of every hour against what happened in the 3 hours after it ----

function drawTimeline(box, st) {
  const form = FORMS.includes(box.dataset.form) ? box.dataset.form : 'bars'
  const art = card(box, 'timeline', 'Прогноз і що сталося', READ[form])
  const all = st.hours
  if (all.length < 2) return calm(art, `Історія прогнозів ще збирається. Графік з'явиться, щойно буде хоча б кілька годин.`)
  const last = all[all.length - 1]
  const span = (last.ms - all[0].ms) / DAY
  const days = (RANGES.find((r) => r[0] === st.range) || RANGES[0])[2]
  const shown = all.filter((h) => h.ms > last.ms - days * DAY)
  const s = score(shown)
  const pills = el('div', { class: 'ch-pills', role: 'group', 'aria-label': 'Період графіка' },
    RANGES.map(([v, text], i) => el('button', {
      type: 'button', class: 'ch-pill', 'data-range': v, 'aria-pressed': String(st.range === v),
      disabled: i > 0 && span <= RANGES[i - 1][2], text,
      on: {
        click: () => {
          st.range = v
          st.anim = true
          drawTimeline(box, st)
          st.anim = false
          box.querySelector(`[data-range="${v}"]`)?.focus()
        },
      },
    })))
  const wrap = el('div', { class: plotClass(st) })
  art.append(pills, tiles([
    ['Потім було неспокійно', share(s.busy), `тихих годин: ${int(s.n)}`],
    ['Модель попередила', share(s.caught), `неспокійних вікон: ${int(s.nBusy)}`],
    ['«Тихо» справдилось', share(s.quietTrue), `прогнозів «тихо»: ${int(s.nSaid)}`],
  ]), legend(KEYS[form]), wrap,
  note('Тиха година: на момент прогнозу тривоги й атаки не було; плитки рахують лише такі години. Відтворення: до запуску модель щодня перенавчали лише на минулому і рахували прогноз так, ніби наживо. Як обрали межі рівнів: docs/quiet/model.md.'),
  footer('prognoz-i-shcho-stalosia', () => shown.map(hourRow)))

  const W = wrap.clientWidth
  if (!W) return
  const phone = W < 560
  const m = { t: 26, r: 12, b: 24, l: 40 }
  const ph = phone ? 150 : 200
  const lanes = form === 'lanes'
  const rows = lanes ? { busy: ph + 10, alert: ph + 28, h: 12 } : { alert: ph + 6, h: 6 }
  const bottom = rows.alert + rows.h
  const H = m.t + bottom + m.b
  const iw = W - m.l - m.r
  const x0 = shown[0].ms, x1 = last.ms + HOUR
  const x = d3.scaleUtc().domain([x0, x1]).range([0, iw])
  const top = Math.max(d3.max(shown, (h) => h.p), st.lim.highAt ?? 0, 0.05)
  const y = d3.scaleLinear().domain([0, top * 1.08]).nice().range([ph, 0])
  const name = { 7: '7 днів', 30: '30 днів' }[days] || 'усю історію'
  const svg = newSvg(wrap, W, H, `Прогноз по годинах за ${name}. Стрілки вліво і вправо переходять між годинами.`)
  const g = svg.append('g').attr('transform', `translate(${m.l},${m.t})`)
  const span1 = (sel, list, cls, yy, hgt) => sel.selectAll('rect').data(list).join('rect').attr('class', cls)
    .attr('x', (r) => x(r.start)).attr('width', (r) => Math.max(1, x(r.end) - x(r.start))).attr('y', yy).attr('height', hgt)

  if (form === 'line') span1(g.append('g'), runs(shown, (h) => h.busy_3h === true), 'ch-band', 0, ph)
  const yt = y.ticks(phone ? 3 : 4)
  g.append('g').attr('class', 'ch-grid').selectAll('line').data(yt).join('line')
    .attr('x1', 0).attr('x2', iw).attr('y1', y).attr('y2', y)
  g.append('g').attr('class', 'ch-tick').selectAll('text').data(yt).join('text')
    .attr('x', -8).attr('y', y).attr('dy', '0.32em').attr('text-anchor', 'end').text((d) => pct(d))

  const step = iw / ((x1 - x0) / HOUR)
  const line = d3.line().x((h) => x(h.ms + HOUR / 2)).y((h) => y(h.p))
  if (form === 'bars') {
    const gap = step >= 5 ? 2 : step >= 3 ? 1 : 0
    g.append('g').selectAll('rect').data(shown).join('rect')
      .attr('class', (h) => (h.busy_3h == null ? 'ch-b-unknown' : h.busy_3h ? 'ch-b-busy' : 'ch-b-calm'))
      .attr('x', (h) => x(h.ms) + gap / 2).attr('width', Math.max(0.6, step - gap))
      .attr('y', (h) => y(h.p)).attr('height', (h) => Math.max(0, ph - y(h.p)))
  } else if (form === 'line') {
    g.append('path').attr('class', 'ch-line').attr('d', line(shown))
  } else {
    g.append('path').attr('class', 'ch-area').attr('d', d3.area().x((h) => x(h.ms + HOUR / 2)).y0(ph).y1((h) => y(h.p))(shown))
    g.append('path').attr('class', 'ch-line ch-line-ink').attr('d', line(shown))
    span1(g.append('g'), runs(shown, (h) => h.busy_3h === true), 'ch-b-busy', rows.busy, rows.h)
  }
  span1(g.append('g'), runs(shown, (h) => h.alert === true), 'ch-alert', rows.alert, rows.h)

  // live hours: a bracket over the plot; the test start: a thin rule
  const live = runs(shown, (h) => h.source === 'live')
  span1(g.append('g'), live, 'ch-live', -9, 3)
  if (live.length) {
    const lx = x(live[0].start)
    const right = lx > iw - 70
    g.append('text').attr('class', 'ch-lab').attr('x', right ? x(live[0].end) : lx).attr('y', -14)
      .attr('text-anchor', right ? 'end' : 'start').text('наживо')
  }
  if (TEST_START > x0 && TEST_START < x1) {
    const tx = x(TEST_START)
    g.append('line').attr('class', 'ch-test').attr('x1', tx).attr('x2', tx).attr('y1', -8).attr('y2', bottom)
    g.append('text').attr('class', 'ch-lab').attr('x', tx + 4).attr('y', -14).text(`тест з ${kyivDay(iso(TEST_START))}`)
  }
  for (const [v, label] of [[st.lim.busyAt, 'середній ризик від'], [st.lim.highAt, 'високий від']]) {
    if (v == null || v > y.domain()[1]) continue
    g.append('line').attr('class', 'ch-limit').attr('x1', 0).attr('x2', iw).attr('y1', y(v)).attr('y2', y(v))
    g.append('text').attr('class', 'ch-lab ch-halo').attr('x', 4).attr('y', y(v) - 5)
      .text(phone ? limPct(v) : `${label} ${limPct(v)}`)
  }

  // x axis: Kyiv midnights, thinned to fit, the newest day always labelled
  const mids = shown.filter((h) => h.hour === 0).map((h) => h.ms)
  const stride = Math.max(1, Math.ceil(mids.length / Math.max(2, Math.floor(iw / (phone ? 64 : 80)))))
  const xt = mids.filter((_, i) => (mids.length - 1 - i) % stride === 0)
  const ax = g.append('g').attr('class', 'ch-tick').attr('transform', `translate(0,${bottom})`)
  ax.selectAll('line').data(xt).join('line').attr('x1', x).attr('x2', x).attr('y1', 0).attr('y2', 4)
  ax.selectAll('text').data(xt).join('text').attr('x', x).attr('y', 18)
    .attr('text-anchor', (ms) => (x(ms) > iw - 22 ? 'end' : x(ms) < 22 ? 'start' : 'middle')).text((ms) => kyivDay(iso(ms)))

  const cross = g.append('line').attr('class', 'ch-cross').attr('y1', -4).attr('y2', bottom).style('opacity', 0)
  const dot = g.append('circle').attr('class', 'ch-dot').attr('r', 4).style('opacity', 0)
  const tip = tipFor(wrap)
  const bis = d3.bisector((h) => h.ms).right
  bind(box, svg.node(), srLive(wrap), shown.length, shown.length - 1,
    (px) => Math.max(0, Math.min(shown.length - 1, bis(shown, +x.invert(px - m.l)) - 1)),
    (i) => {
      const h = shown[i]
      const cx = x(h.ms + HOUR / 2), cy = y(h.p)
      cross.attr('x1', cx).attr('x2', cx).style('opacity', 1)
      dot.attr('cx', cx).attr('cy', cy).style('opacity', 1)
      const lines = hourLines(h)
      tip.show(m.l + cx, m.t + cy, lines)
      return lines
    },
    () => {
      cross.style('opacity', 0)
      dot.style('opacity', 0)
      tip.hide()
    })
}

// ---- 2. calibration: when the model said X, what share of hours was really busy; and the truth of each tier ----

function drawCalibration(box, st) {
  const hist = st.data?.history || {}
  const bins = (Array.isArray(hist.calibration) ? hist.calibration : [])
    .filter((b) => b && b.n > 0 && num(b.p_mean) != null && num(b.busy_share) != null)
  const tiers = ['low', 'medium', 'high'].map((k) => ({ k, all: hist.tiers?.[k], test: hist.tiers_since_test?.[k] }))
    .filter((r) => r.all?.hours > 0 || r.test?.hours > 0)
  const N = d3.sum(bins, (b) => b.n)
  const gap = N ? d3.sum(bins, (b) => b.n * (b.busy_share - b.p_mean)) / N : null
  const sub = gap == null ? null
    : gap > 0.03 ? 'Модель обережна: насправді неспокійно частіше, ніж вона каже. Її відсоток краще читати як нижню межу.'
      : gap < -0.03 ? 'Модель перестраховується: насправді неспокійно рідше, ніж вона каже.'
        : 'Цифрам можна вірити: що модель каже, те в середньому й буває.'
  const art = card(box, 'calibration', 'Чи можна вірити цифрам', sub)
  if (!bins.length && !tiers.length) return calm(art, 'Перевірених годин ще немає. Щойно мине 3 години після перших прогнозів, тут буде видно, чи справджуються цифри.')
  const testDay = kyivDay(iso(TEST_START))
  const firstDay = st.hours.length ? kyivDay(st.hours[0].t) : null
  if (gap != null) {
    const pts = Math.round(Math.abs(gap) * 100)
    art.append(tiles([
      ['Годин перевірено', int(N), 'на момент прогнозу було тихо'],
      [gap >= 0 ? 'Насправді частіше, ніж каже' : 'Насправді рідше, ніж каже', `${pts} ${plural(pts, 'пункт', 'пункти', 'пунктів')}`, 'у середньому по всіх годинах'],
    ]))
  }
  if (bins.length) {
    const wrap = el('div', { class: plotClass(st) })
    art.append(el('h4', { class: 'ch-h4', text: 'Коли модель каже X, як часто справді неспокійно' }),
      legend([['said', 'модель казала, у середньому'], ['real', 'справді неспокійно']]), wrap)
    drawBins(box, wrap, bins)
  }
  if (tiers.length) {
    const wrap = el('div', { class: plotClass(st) })
    art.append(el('h4', { class: 'ch-h4', text: 'Кожен рівень: як часто потім справді неспокійно' }),
      legend([['whole', `уся історія${firstDay ? ` з ${firstDay}` : ''}`], ['test', `з ${testDay}, перевірка на нових годинах`]]), wrap)
    drawTiers(box, wrap, tiers, st.lim, testDay)
  }
  art.append(note(`Рахуємо лише години, коли на момент прогнозу було тихо і 3 години після вже минули. Рядки, де менше ${FEW} годин, бліді: там цифра хитка. Перевірка з ${testDay}: на цих годинах нічого не підбирали (docs/quiet/model.md).`),
    footer('chy-mozhna-viryty-tsyfram', () => [
      ...bins.map((b) => ({ part: 'said_vs_real', group: binName(b), hours: b.n, said_mean: b.p_mean, busy_share: b.busy_share })),
      ...tiers.flatMap((r) => [['tier_whole_history', r.all], ['tier_since_test', r.test]].filter(([, t]) => t)
        .map(([part, t]) => ({ part, group: r.k, hours: t.hours, said_mean: '', busy_share: t.busy_share }))),
    ]))
}

function drawBins(box, wrap, bins) {
  const W = wrap.clientWidth
  if (!W) return
  const phone = W < 560
  const m = { t: 6, r: 48, b: 26, l: 72 }
  const rh = 32
  const iw = W - m.l - m.r, ih = bins.length * rh, H = m.t + ih + m.b
  const x = d3.scaleLinear().domain([0, 1]).range([0, iw])
  const svg = newSvg(wrap, W, H, 'Коли модель каже певний відсоток, яка частка годин справді неспокійна. Стрілки вліво і вправо переходять між рядками.')
  const g = svg.append('g').attr('transform', `translate(${m.l},${m.t})`)
  const hl = g.append('rect').attr('class', 'ch-hl').attr('x', 2 - m.l).attr('width', W - 4).attr('height', rh).attr('rx', 8)
  const xt = phone ? [0, 0.5, 1] : [0, 0.25, 0.5, 0.75, 1]
  g.append('g').attr('class', 'ch-grid').selectAll('line').data(xt).join('line')
    .attr('x1', x).attr('x2', x).attr('y1', 0).attr('y2', ih)
  g.append('g').attr('class', 'ch-tick').attr('transform', `translate(0,${ih + 18})`).selectAll('text').data(xt).join('text')
    .attr('x', x).attr('text-anchor', (d) => (d === 1 ? 'end' : d === 0 ? 'start' : 'middle')).text((d) => pct(d))
  const row = g.selectAll('g.ch-row').data(bins).join('g').attr('class', (b) => (b.n < FEW ? 'ch-row ch-pale' : 'ch-row'))
    .attr('transform', (b, i) => `translate(0,${i * rh + rh / 2})`)
  row.append('text').attr('class', 'ch-lab').attr('x', -10).attr('y', -2).attr('text-anchor', 'end').text(binName)
  row.append('text').attr('class', 'ch-tick').attr('x', -10).attr('y', 12).attr('text-anchor', 'end').text((b) => `${int(b.n)} год`)
  row.append('line').attr('class', 'ch-seg').attr('x1', (b) => x(b.p_mean)).attr('x2', (b) => x(b.busy_share))
  row.append('circle').attr('class', 'ch-said').attr('cx', (b) => x(b.p_mean)).attr('r', 5)
  row.append('circle').attr('class', 'ch-real').attr('cx', (b) => x(b.busy_share)).attr('r', 6)
  row.append('text').attr('class', 'ch-lab ch-strong').attr('y', 4)
    .attr('x', (b) => x(Math.max(b.p_mean, b.busy_share)) + 10).text((b) => pct(b.busy_share))
  const tip = tipFor(wrap)
  bind(box, svg.node(), srLive(wrap), bins.length, bins.length - 1,
    (px, py) => Math.max(0, Math.min(bins.length - 1, Math.floor((py - m.t) / rh))),
    (i) => {
      const b = bins[i]
      hl.attr('y', i * rh).classed('on', true)
      const lines = [`Модель казала ${binName(b)}`, `У середньому казала: ${pct(b.p_mean)}`,
        `Справді неспокійно: ${pct(b.busy_share)}`, `Годин: ${int(b.n)}${b.n < FEW ? ', замало, цифра хитка' : ''}`]
      tip.show(m.l + x(b.busy_share), m.t + i * rh + 6, lines)
      return lines
    },
    () => {
      hl.classed('on', false)
      tip.hide()
    })
}

function drawTiers(box, wrap, tiers, lim, testDay) {
  const W = wrap.clientWidth
  if (!W) return
  const phone = W < 560
  const m = { t: 4, r: 8, b: 26, l: 8 }
  const gh = 62
  const iw = W - m.l - m.r, ih = tiers.length * gh, H = m.t + ih + m.b
  const x = d3.scaleLinear().domain([0, 1]).range([0, iw])
  const svg = newSvg(wrap, W, H, 'Для кожного рівня прогнозу: яка частка годин потім справді була неспокійною, за всю історію і з початку перевірки. Стрілки вліво і вправо переходять між рівнями.')
  const g = svg.append('g').attr('transform', `translate(${m.l},${m.t})`)
  const hl = g.append('rect').attr('class', 'ch-hl').attr('x', 2 - m.l).attr('width', W - 4).attr('height', gh - 4).attr('rx', 8)
  const xt = phone ? [0, 0.5, 1] : [0, 0.25, 0.5, 0.75, 1]
  g.append('g').attr('class', 'ch-grid').selectAll('line').data(xt).join('line')
    .attr('x1', x).attr('x2', x).attr('y1', 20).attr('y2', ih)
  g.append('g').attr('class', 'ch-tick').attr('transform', `translate(0,${ih + 18})`).selectAll('text').data(xt).join('text')
    .attr('x', x).attr('text-anchor', (d) => (d === 1 ? 'end' : d === 0 ? 'start' : 'middle')).text((d) => pct(d))
  const grp = g.selectAll('g.ch-row').data(tiers).join('g').attr('class', 'ch-row').attr('transform', (r, i) => `translate(0,${i * gh})`)
  grp.append('text').attr('class', 'ch-lab ch-strong').attr('x', 0).attr('y', 14).text((r) => `«${TIER[r.k]}»${tierRange(r.k, lim)}`)
  for (const [key, cls, dy] of [['all', 'ch-whole', 22], ['test', 'ch-testbar', 38]]) {
    grp.each(function (r) {
      const t = r[key]
      const gg = d3.select(this)
      if (!t || !(t.hours > 0) || num(t.busy_share) == null) {
        gg.append('text').attr('class', 'ch-tick').attr('x', 0).attr('y', dy + 10).text('немає даних')
        return
      }
      const w = Math.max(2, x(t.busy_share))
      gg.append('rect').attr('class', cls).attr('x', 0).attr('y', dy).attr('width', w).attr('height', 12).attr('rx', 3)
      const label = gg.append('text').attr('class', 'ch-lab').attr('y', dy + 10).text(`${pct(t.busy_share)}, ${int(t.hours)} год`)
      const tw = label.node().getComputedTextLength()
      if (w + 6 + tw <= iw) label.attr('x', w + 6)
      else label.attr('x', w - 6).attr('text-anchor', 'end').classed('ch-on-bar', true)
    })
  }
  const part = (t) => (t && t.hours > 0 && num(t.busy_share) != null ? `${pct(t.busy_share)} із ${int(t.hours)} год` : 'немає даних')
  const tip = tipFor(wrap)
  bind(box, svg.node(), srLive(wrap), tiers.length, tiers.length - 1,
    (px, py) => Math.max(0, Math.min(tiers.length - 1, Math.floor((py - m.t) / gh))),
    (i) => {
      const r = tiers[i]
      hl.attr('y', i * gh - 2).classed('on', true)
      const lines = [`Рівень «${TIER[r.k]}»${tierRange(r.k, lim)}`, `Потім неспокійно, уся історія: ${part(r.all)}`, `З ${testDay}: ${part(r.test)}`]
      tip.show(m.l + Math.min(iw * 0.6, x(num(r.test?.busy_share) ?? num(r.all?.busy_share) ?? 0)), m.t + i * gh + 18, lines)
      return lines
    },
    () => {
      hl.classed('on', false)
      tip.hide()
    })
}

// ---- 3. days by hour: rows are Kyiv days (newest on top), columns the 24 Kyiv hours ----

function drawDays(box, st) {
  const art = card(box, 'days', 'Коли зазвичай неспокійно',
    'Рядок це день, клітинка це година за Києвом. Чим темніша клітинка, тим вищий прогноз моделі; крапка означає, що за 3 години після справді було неспокійно.')
  const all = st.hours
  if (all.length < 2) return calm(art, `Днів ще замало: сітка з'явиться, щойно набереться історія прогнозів.`)
  const css = getComputedStyle(document.documentElement)
  const seq = d3.scaleSequential(d3.piecewise(d3.interpolateRgb,
    [css.getPropertyValue('--card').trim(), css.getPropertyValue('--pink').trim(), SEQ_DARK])).domain([0, 1])
  const head = el('div')
  const wrap = el('div', { class: plotClass(st) })
  const notes = note('')
  art.append(head, seqLegend(seq, st.lim), wrap, notes)
  const W = wrap.clientWidth
  if (!W) return
  const phone = W < 560
  const keys = [...new Set(all.map((h) => h.day))].sort().reverse().slice(0, phone ? 14 : 30)
  const rowOf = new Map(keys.map((k, i) => [k, i]))
  const cells = all.filter((h) => rowOf.has(h.day))
  const per = d3.rollups(cells.filter((h) => h.busy_3h != null),
    (v) => ({ n: v.length, busy: d3.mean(v, (h) => (h.busy_3h ? 1 : 0)) }), (h) => h.hour).filter(([, s]) => s.n >= 3)
  const most = d3.greatest(per, ([, s]) => s.busy)
  const least = d3.least(per, ([, s]) => s.busy)
  head.replaceWith(most ? tiles([
    ['Найнеспокійніша година', `${hh(most[0])}:00`, `у ${pct(most[1].busy)} днів`],
    ['Найспокійніша година', `${hh(least[0])}:00`, `у ${pct(least[1].busy)} днів`],
  ]) : el('span'))
  notes.textContent = `Останні ${keys.length} днів, нові згори. Порожня клітинка: на цю годину прогнозу немає. Позначки на шкалі це межі рівнів (docs/quiet/model.md).`
  art.append(footer('dni-po-hodynakh', () => cells.map(hourRow)))

  const m = { t: 22, r: 2, b: 4, l: phone ? 68 : 76 }
  const cw = (W - m.l - m.r) / 24
  const rh = 20
  const H = m.t + keys.length * rh + m.b
  const svg = newSvg(wrap, W, H, `Останні ${keys.length} днів по годинах: колір це прогноз, крапка це неспокійне вікно. Стрілки вліво і вправо переходять між годинами.`)
  const g = svg.append('g').attr('transform', `translate(${m.l},${m.t})`)
  g.append('rect').attr('class', 'ch-gridbg').attr('width', 24 * cw).attr('height', keys.length * rh).attr('rx', 4)
  g.append('g').attr('class', 'ch-tick').selectAll('text').data(d3.range(0, 24, phone ? 6 : 3)).join('text')
    .attr('x', (h) => h * cw + cw / 2).attr('y', -8).attr('text-anchor', 'middle').text((h) => `${hh(h)}:00`)
  const firstOf = new Map()
  for (const h of cells) if (!firstOf.has(h.day)) firstOf.set(h.day, h)
  g.append('g').attr('class', 'ch-tick').selectAll('text').data(keys).join('text')
    .attr('x', -8).attr('y', (k, i) => i * rh + rh / 2).attr('dy', '0.32em').attr('text-anchor', 'end')
    .text((k) => `${WEEKDAY.format(firstOf.get(k).ms)} ${kyivDay(firstOf.get(k).t)}`)
  const gap = cw >= 8 ? 1 : 0.5
  g.append('g').selectAll('rect').data(cells).join('rect')
    .attr('x', (h) => h.hour * cw + gap).attr('y', (h) => rowOf.get(h.day) * rh + gap)
    .attr('width', cw - 2 * gap).attr('height', rh - 2 * gap).attr('rx', 2).attr('fill', (h) => seq(h.p))
  g.append('g').selectAll('circle').data(cells.filter((h) => h.busy_3h === true)).join('circle')
    .attr('class', (h) => (d3.lab(seq(h.p)).l < 60 ? 'ch-mark-dark' : 'ch-mark-light'))
    .attr('cx', (h) => h.hour * cw + cw / 2).attr('cy', (h) => rowOf.get(h.day) * rh + rh / 2)
    .attr('r', Math.max(1.6, Math.min(cw, rh) * 0.13))
  const focus = g.append('rect').attr('class', 'ch-focus').attr('width', cw).attr('height', rh).attr('rx', 3).style('opacity', 0)
  const idx = new Map(cells.map((h, i) => [`${h.day}|${h.hour}`, i]))
  const tip = tipFor(wrap)
  bind(box, svg.node(), srLive(wrap), cells.length, cells.length - 1,
    (px, py) => {
      const c = Math.floor((px - m.l) / cw), r = Math.floor((py - m.t) / rh)
      if (c < 0 || c > 23 || r < 0 || r >= keys.length) return null
      return idx.get(`${keys[r]}|${c}`) ?? null
    },
    (i) => {
      const h = cells[i]
      const cx = h.hour * cw, cy = rowOf.get(h.day) * rh
      focus.attr('x', cx).attr('y', cy).style('opacity', 1)
      const lines = hourLines(h)
      tip.show(m.l + cx + cw / 2, m.t + cy, lines)
      return lines
    },
    () => {
      focus.style('opacity', 0)
      tip.hide()
    })
}

// The color scale of the days: a gradient bar with ticks at the two tier limits.
function seqLegend(seq, lim) {
  const w = 240, ht = 34
  const x = d3.scaleLinear().domain([0, 1]).range([6, w - 6])
  const row = el('div', { class: 'ch-legend' }, el('span', { class: 'ch-lead', text: 'Прогноз' }))
  const svg = d3.select(row).append('svg').attr('class', 'ch-seq').attr('width', w).attr('height', ht)
    .attr('viewBox', `0 0 ${w} ${ht}`).attr('aria-hidden', 'true')
  const id = `ch-grad-${Math.random().toString(36).slice(2, 8)}`
  const grad = svg.append('defs').append('linearGradient').attr('id', id)
  d3.range(0, 11).forEach((i) => grad.append('stop').attr('offset', `${i * 10}%`).attr('stop-color', seq(i / 10)))
  svg.append('rect').attr('class', 'ch-seqbar').attr('x', 6).attr('y', 3).attr('width', w - 12).attr('height', 10).attr('rx', 5).attr('fill', `url(#${id})`)
  const marks = [[lim.busyAt, 'end'], [lim.highAt, 'start'], [1, 'end']].filter(([v]) => v != null)
  const t = svg.append('g').attr('class', 'ch-tick')
  t.selectAll('line').data(marks).join('line').attr('x1', (d) => x(d[0])).attr('x2', (d) => x(d[0])).attr('y1', 1).attr('y2', 17)
  t.selectAll('text').data(marks).join('text').attr('x', (d) => x(d[0]) + (d[1] === 'end' ? 2 : -2)).attr('y', 30)
    .attr('text-anchor', (d) => d[1]).text((d) => limPct(d[0]))
  row.append(el('span', { class: 'ch-li' }, el('span', { class: 'ch-key ch-key-dot' }), 'потім неспокійно'))
  return row
}
