// The shell of kyianyn-routine.isakov.fyi: two tabs by hash (#/ "Відповідь" and #/how/<scene>/<step>), keys, the help dialog,
// the live pill and the data loop. The JSON files are loaded at start and every 2 minutes, the small ones first and
// history.json (only the charts use it) after, and only what changed is redrawn. Until the first answer the hero
// shows a skeleton (body.is-loading). The deck (how.js) loads on the first visit of its tab and shares the data.

import { ago, kyivStamp, kyivTime, kyivDay } from './api.js'
import { renderDashboard, mountChartsInto, runTrain } from './dashboard.js'

const $ = (sel) => document.querySelector(sel)
const tabMain = $('#tab-main')
const tabHow = $('#tab-how')
const howRoot = $('#how-root')
const help = $('#help')
const live = $('#live')
const liveWord = $('#live-word')
const liveAgo = $('#live-ago')
const liveMore = $('#live-more')
const toast = $('#toast')
const RM = window.matchMedia('(prefers-reduced-motion: reduce)')
const SMALL = ['now', 'model', 'meta'] // a few KB each: the answer and every block but the charts
const FONT_WAIT_MS = 2500
const EVERY_MS = 2 * 60 * 1000

const data = { now: null, history: null, model: null, meta: null } // one object, shared with the deck
const seen = {}
let how = null
let howLoad = null
let lastHow = ''
let shown = ''
let toastTimer = 0
let ready = false // the first data is drawn and the page has left its loading skeleton

const isHow = () => location.hash.startsWith('#/how')
const behavior = () => (RM.matches ? 'auto' : 'smooth')
const typing = (t) => t instanceof Element && t.closest('input, textarea, select, [contenteditable]:not([contenteditable="false"])')
const control = (t) => t instanceof Element && t.closest('button, a, summary, [role="button"]')

// One file of site/api/ by the rules of loadAll in api.js: a missing or broken file is null. The files load one
// by one, so the answer does not wait for history.json, the biggest file, which only the charts need.
async function getJSON(name) {
  try {
    const r = await fetch(`api/${name}.json`, { cache: 'no-store' })
    return r.ok ? await r.json() : null
  } catch {
    return null
  }
}

// The web fonts of the page, asked for at once. The first answer waits for them (FONT_WAIT_MS at most), so its
// text does not change size under the reader when a font swaps in.
const fontsReady = Promise.race([
  Promise.all(['400 16px Onest', '600 16px Onest', '700 16px Onest', '700 16px Unbounded', '800 16px Unbounded']
    .map((f) => (document.fonts ? document.fonts.load(f, 'Чи встигну? 0123456789%') : Promise.resolve()).catch(() => null))),
  new Promise((done) => { setTimeout(done, FONT_WAIT_MS) }),
])

async function refresh() {
  const changed = new Set()
  const take = (k, v) => {
    const text = JSON.stringify(v ?? null)
    if (text === seen[k]) return
    seen[k] = text
    data[k] = v ?? null
    changed.add(k)
  }
  const big = getJSON('history')
  const small = await Promise.all(SMALL.map(getJSON))
  if (!ready) await fontsReady
  SMALL.forEach((k, i) => take(k, small[i]))
  if (changed.size) renderDashboard(tabMain, data)
  if (!ready) reveal()
  pill()
  take('history', await big)
  if (changed.has('history') || changed.has('now')) mountChartsInto($('#charts'), data)
  return changed
}

// The first data is drawn: the skeleton gives way to the answer and the other blocks show in the same frame.
// They were display none, not just empty, so nothing that was on screen moves (no layout shift).
function reveal() {
  ready = true
  document.body.classList.remove('is-loading')
  $('#hero').removeAttribute('aria-busy')
}

const tick = () => refresh().catch((err) => {
  console.warn('refresh', err)
  return new Set()
})

// The live pill: a green dot and "оновлено N хв тому"; stale data: an amber chip "дані за HH:MM, оновлюємо" (on a
// phone just "дані за HH:MM"); no data yet: a grey dot.
function pill() {
  const now = data.now
  const stale = Boolean(now?.stale)
  live.classList.toggle('is-stale', stale)
  live.classList.toggle('is-empty', !now)
  liveWord.hidden = !now || stale
  liveMore.hidden = !now || !stale
  if (!now) {
    liveAgo.textContent = 'чекаю на дані'
    live.title = 'Дані ще не готові'
    live.setAttribute('aria-label', 'Дані ще не готові. Перейти до джерел')
    return
  }
  const reason = now.stale_reason || 'дані застаріли'
  const fresh = now.generated_at ? ago(now.generated_at) : 'невідомо коли'
  if (stale) {
    const at = now.hour || now.data_until
    const date = document.createElement('span')
    date.className = 'live-date'
    date.textContent = at && kyivDay(at) !== kyivDay(new Date().toISOString()) ? `${kyivDay(at)} ` : ''
    liveAgo.replaceChildren('дані за ', date, at ? kyivTime(at) : '?')
  } else {
    liveAgo.textContent = fresh
  }
  live.title = stale ? `Дані застаріли: ${reason}`
    : `Оновлено ${now.generated_at ? kyivStamp(now.generated_at) : ''}${now.data_until ? `, найсвіжіший пост ${kyivStamp(now.data_until)}` : ''}`
  live.setAttribute('aria-label', `${stale ? `Дані застаріли: ${reason}` : `Оновлено ${fresh}`}. Перейти до джерел`)
}

// Tabs: every hash that starts with #/how shows the deck, everything else shows tab 1.
function route() {
  const onHow = isHow()
  if (location.hash.startsWith('#/how/')) lastHow = location.hash
  else if (onHow && how && lastHow) history.replaceState(null, '', lastHow)
  tabMain.hidden = onHow
  tabHow.hidden = !onHow
  for (const a of document.querySelectorAll('.tab[data-tab]')) {
    if ((a.dataset.tab === 'how') === onHow) a.setAttribute('aria-current', 'page')
    else a.removeAttribute('aria-current')
  }
  const tab = onHow ? 'how' : 'main'
  if (shown && shown !== tab) window.scrollTo(0, 0)
  shown = tab
  if (onHow) openHow()
  else how?.stop()
}

function waitNote(text) {
  const p = document.createElement('p')
  p.className = 'calm'
  p.textContent = text
  return p
}

function openHow() {
  howLoad ??= (async () => {
    howRoot.replaceChildren(waitNote('Завантажую кроки...'))
    try {
      await first
      const { createHow } = await import('./how.js')
      how = await createHow(howRoot, data)
      if (!isHow()) how.stop()
    } catch (err) {
      console.warn('how', err)
      howRoot.replaceChildren(waitNote('Цей розділ ще готується. Загляньте трохи згодом.'))
    }
  })()
  return howLoad
}

// Arrows up and down: the previous or next section of tab 1, under the sticky header.
function section(dir) {
  const list = [...tabMain.querySelectorAll(':scope > section')]
  const top = (s) => s.getBoundingClientRect().top - parseFloat(getComputedStyle(s).scrollMarginTop || '0')
  const target = dir > 0 ? list.find((s) => top(s) > 4) : list.reverse().find((s) => top(s) < -4)
  if (!target) return
  target.scrollIntoView({ behavior: behavior(), block: 'start' })
  target.focus({ preventScroll: true })
}

function train() {
  if (isHow()) {
    location.hash = '#/'
    setTimeout(train, 80)
    return
  }
  const btn = $('#hero-map') || $('#train')
  if (!btn) return
  const r = btn.getBoundingClientRect()
  if (r.top < 60 || r.bottom > window.innerHeight) btn.scrollIntoView({ behavior: behavior(), block: 'center' })
  runTrain()
}

function say(text) {
  toast.textContent = text
  toast.classList.add('on')
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => toast.classList.remove('on'), 2400)
}

async function reload() {
  say('Перевіряю дані...')
  const changed = await tick()
  say(changed.size ? 'Дані оновлено' : 'Нових даних поки немає')
}

function openHelp() {
  if (!help.open) help.showModal()
}

document.addEventListener('keydown', (e) => {
  if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || typing(e.target) || help.open) return
  if (e.key === '?' || (e.code === 'Slash' && e.shiftKey)) {
    e.preventDefault()
    openHelp()
    return
  }
  if (e.shiftKey || (e.repeat && !e.code.startsWith('Arrow'))) return
  const onHow = isHow()
  switch (e.code) {
    case 'Digit1': case 'Numpad1':
      e.preventDefault()
      if (onHow) location.hash = '#/'
      else window.scrollTo({ top: 0, behavior: behavior() })
      break
    case 'Digit2': case 'Numpad2':
      e.preventDefault()
      if (!onHow) location.hash = '#/how'
      break
    case 'KeyT':
      e.preventDefault()
      train()
      break
    case 'KeyR':
      e.preventDefault()
      reload()
      break
    case 'ArrowDown': case 'ArrowUp':
      if (!onHow) {
        e.preventDefault()
        section(e.code === 'ArrowDown' ? 1 : -1)
      }
      break
    case 'ArrowRight': case 'ArrowLeft':
      if (onHow && how) {
        e.preventDefault()
        if (e.code === 'ArrowRight') how.next()
        else how.prev()
      }
      break
    case 'Space':
      if (onHow && how && !control(e.target)) {
        e.preventDefault()
        how.toggle()
      }
      break
    default:
  }
})

window.addEventListener('hashchange', (e) => {
  const old = new URL(e.oldURL).hash
  if (old.startsWith('#/how/')) lastHow = old
  route()
})
$('#help-open').addEventListener('click', openHelp)
$('#help-close').addEventListener('click', () => help.close())
help.addEventListener('click', (e) => { if (e.target === help) help.close() })
live.addEventListener('click', () => {
  const go = () => {
    const box = $('#sources')
    box.querySelector('details')?.setAttribute('open', '')
    box.scrollIntoView({ behavior: behavior(), block: 'start' })
    box.focus({ preventScroll: true })
  }
  if (isHow()) {
    location.hash = '#/'
    setTimeout(go, 80)
  } else go()
})
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') tick() })

const first = tick()
route()
setInterval(tick, EVERY_MS)
setInterval(pill, 30 * 1000)
