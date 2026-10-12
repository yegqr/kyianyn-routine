// The methodology deck "Як це працює": 12 sections (a "розділ" each), every section animates in a few steps ("крок").
// Scenes live in ./scenes/ and follow the contract in ./scenes/README.md. URL: #/how/<scene id>/<step number from 1>.
// The shell (app.js) shows the tab and forwards keys: next(), prev(), toggle().
// Layout (how.css): on a desktop the text is on the left and the stage on the right; a phone shows the section title,
// the stage with its controls in one row, then the lead, the note and the prompt cards.

import { SCENES } from './scenes/index.js'

const SVG_NS = 'http://www.w3.org/2000/svg'
const RM = window.matchMedia('(prefers-reduced-motion: reduce)')
export const reduced = () => RM.matches

const AUTO_MS = 3200   // Автопрогравання: the next step every 3.2 s
const HINT_MS = 2000   // the swipe hint shows this long when the deck opens, later on hover

// h('p', {class: 'x', text: 'hi'}), h('div', {html: '<b>x</b>'}), h('button', {on: {click: f}}, child, ...)
export function h(tag, attrs = {}, ...kids) {
  return fill(document.createElement(tag), attrs, kids, false)
}

// s('circle', {cx: 10, cy: 10, r: 4, class: 'dot'}): an SVG element, attributes as they are
export function s(tag, attrs = {}, ...kids) {
  return fill(document.createElementNS(SVG_NS, tag), attrs, kids, true)
}

function fill(node, attrs, kids, svg) {
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue
    if (k === 'text') node.textContent = v
    else if (k === 'html') node.innerHTML = v
    else if (k === 'style' && typeof v === 'object') Object.assign(node.style, v)
    else if (k === 'on') for (const [ev, f] of Object.entries(v)) node.addEventListener(ev, f)
    else if (k === 'class' && !svg) node.className = v
    else node.setAttribute(k, v === true ? '' : v)
  }
  for (const kid of kids.flat()) if (kid != null) node.append(kid)
  return node
}

// A fresh SVG canvas for a scene: every scene draws in 640 x 400 units (16:10). On a phone the stage is about 358 px
// wide (0.56 px per unit), so SVG text needs font-size 18 or more (about 10 px on screen). A label that cannot be that
// big is shortened or hidden while the stage is narrower than 500 px (the stage is the CSS container "how-stage").
export function canvas(stage, label) {
  const svg = s('svg', { viewBox: '0 0 640 400', class: 'how-svg', role: 'img', 'aria-label': label || '' })
  stage.append(svg)
  return svg
}

// Moves a node to a state with a transform and opacity transition only (the house rule for animation).
// state: {o: opacity, x, y: translate in px (SVG user units for SVG nodes), k: scale, kx, ky: scale per axis}
// opts: {delay: ms, dur: 200..400 ms, origin: CSS transform-origin, instant: no transition}
export function put(node, state = {}, opts = {}) {
  const { o = 1, x = 0, y = 0, k = 1 } = state
  const kx = state.kx ?? k
  const ky = state.ky ?? k
  const { delay = 0, dur = 320, origin = 'center', instant = false } = opts
  if (node instanceof SVGElement) node.style.transformBox = 'fill-box'
  node.style.transformOrigin = origin
  node.style.transition = instant || reduced() ? 'none'
    : `transform ${dur}ms var(--ease) ${delay}ms, opacity ${dur}ms var(--ease) ${delay}ms`
  node.style.transform = `translate(${x}px, ${y}px) scale(${kx}, ${ky})`
  node.style.opacity = String(o)
  return node
}

// Stagger: the delay of the i-th item of a sequence.
export const stagger = (i, gap = 90, start = 0) => start + i * gap

// A card with a real prompt, question or rule used at this step: {title, text, source}.
export function promptCard({ title, text, source }) {
  return h('figure', { class: 'prompt' },
    h('figcaption', {}, h('span', { class: 'prompt-title', text: title }),
      source ? h('span', { class: 'prompt-source', text: source }) : null),
    h('pre', {}, h('code', { text: text })))
}

const ICON = {
  prev: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>',
  next: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>',
  play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5l11 7-11 7z"/></svg>',
  pause: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14M16 5v14"/></svg>',
}

function placeholder(path, err) {
  const id = path.replace(/^.*\/\d+-|\.js$/g, '')
  return {
    id, title: 'Цей розділ ще готується', lead: 'Він з’явиться тут згодом.',
    steps: [{ note: '' }],
    mount(stage) {
      if (err) console.warn('scene', path, err)
      stage.append(h('p', { class: 'how-empty', text: 'Скоро' }))
      return { show() {}, destroy() {} }
    },
  }
}

async function loadScenes() {
  return Promise.all(SCENES.map(async (path) => {
    try {
      const mod = await import(new URL(path, new URL('./scenes/', import.meta.url)))
      return mod.default
    } catch (err) {
      return placeholder(path, err)
    }
  }))
}

export async function createHow(root, data) {
  const scenes = await loadScenes()
  const el = {
    kicker: h('p', { class: 'how-kicker' }),
    title: h('h2', { class: 'how-title' }),
    lead: h('p', { class: 'how-lead' }),
    note: h('div', { class: 'how-note', 'aria-live': 'polite' }),
    prompts: h('div', { class: 'how-prompts' }),
    stage: h('div', { class: 'how-stage', role: 'group' }),
    cap: h('p', { class: 'how-cap', 'aria-hidden': 'true', text: 'Гортай стрілками або свайпом' }),
    step: h('span', { class: 'how-step' }),
    play: h('button', { class: 'pill how-play', type: 'button' }),
  }
  const prevBtn = h('button', {
    class: 'pill how-arrow how-prev', type: 'button', 'aria-label': 'Назад', html: ICON.prev + '<span>Назад</span>',
  })
  const nextBtn = h('button', {
    class: 'pill how-arrow how-next', type: 'button', 'aria-label': 'Далі', html: '<span>Далі</span>' + ICON.next,
  })
  // One segment per section: past ones are full, the current one fills step by step.
  const dots = scenes.map((sc, j) => h('button', {
    class: 'how-dot', type: 'button', 'aria-label': `Розділ ${j + 1} з ${scenes.length}: ${sc.title}`, title: sc.title,
    on: { click: () => { go(j, 0, true); restart() } },
  }, h('span', { class: 'how-dot-bar' })))
  const frame = h('div', { class: 'how-frame is-hint' }, el.stage, el.cap)
  root.replaceChildren(h('div', { class: 'how' },
    h('div', { class: 'how-head' }, el.kicker, el.title),
    h('div', { class: 'how-side' }, frame,
      h('nav', { class: 'how-nav', 'aria-label': 'Розділи і кроки' },
        h('div', { class: 'how-dots', role: 'group', 'aria-label': 'Розділи' }, dots),
        h('div', { class: 'how-ctrl' }, el.play,
          h('div', { class: 'how-pager' }, prevBtn, el.step, nextBtn)))),
    h('div', { class: 'how-body' }, el.lead, el.note, el.prompts)))

  let i = -1
  let step = 0
  let ctrl = null
  let timer = null
  const hintTimer = setTimeout(() => frame.classList.remove('is-hint'), HINT_MS)

  const atEnd = () => i === scenes.length - 1 && step === scenes[i].steps.length - 1

  // The toggle keeps its word; the icon and aria-pressed show whether it runs.
  function setPlay(on) {
    el.play.setAttribute('aria-pressed', on ? 'true' : 'false')
    el.play.innerHTML = (on ? ICON.pause : ICON.play) + '<span>Автопрогравання</span>'
  }

  function render() {
    const sc = scenes[i]
    const st = sc.steps[step] || {}
    el.kicker.textContent = `Розділ ${i + 1} з ${scenes.length}`
    el.title.textContent = sc.title
    el.lead.textContent = sc.lead || ''
    el.note.innerHTML = st.note || ''
    el.prompts.replaceChildren(...[...(st.prompts || []), ...(sc.prompts || [])].map(promptCard))
    el.step.textContent = `крок ${step + 1} з ${sc.steps.length}`
    el.stage.setAttribute('aria-label', `Малюнок до розділу «${sc.title}»`)
    dots.forEach((d, j) => {
      d.setAttribute('aria-current', j === i ? 'step' : 'false')
      d.style.setProperty('--p', String(j < i ? 1 : j > i ? 0 : (step + 1) / sc.steps.length))
    })
    prevBtn.disabled = i === 0 && step === 0
    nextBtn.disabled = atEnd()
    const hash = `#/how/${sc.id}/${step + 1}`
    if (location.hash !== hash && location.hash.startsWith('#/how')) history.replaceState(null, '', hash)
  }

  function go(to, toStep = 0, instant = false) {
    to = Math.max(0, Math.min(scenes.length - 1, to))
    if (to !== i) {
      try { ctrl?.destroy() } catch (err) { console.warn(err) }
      el.stage.replaceChildren()
      i = to
      try {
        ctrl = scenes[i].mount(el.stage, data) || { show() {}, destroy() {} }
      } catch (err) {
        console.warn('scene', scenes[i].id, err)
        el.stage.replaceChildren(h('p', { class: 'how-empty', text: 'Малюнок не вийшов. Онови сторінку.' }))
        ctrl = { show() {}, destroy() {} }
      }
      instant = instant || toStep > 0
    }
    step = Math.max(0, Math.min(scenes[i].steps.length - 1, toStep))
    try { ctrl.show(step, { instant }) } catch (err) { console.warn('scene', scenes[i].id, err) }
    render()
  }

  function next() {
    const last = scenes[i].steps.length - 1
    if (step < last) go(i, step + 1)
    else if (i < scenes.length - 1) go(i + 1, 0)
    else stop()
  }

  function prev() {
    if (step > 0) go(i, step - 1)
    else if (i > 0) go(i - 1, scenes[i - 1].steps.length - 1, true)
  }

  function stop() {
    clearInterval(timer)
    timer = null
    setPlay(false)
  }

  // A move by hand while Автопрогравання runs starts its 3.2 s count again.
  function restart() {
    if (!timer) return
    clearInterval(timer)
    timer = setInterval(next, AUTO_MS)
  }

  function toggle() {
    if (timer) return stop()
    if (atEnd()) go(0, 0)
    timer = setInterval(next, AUTO_MS)
    setPlay(true)
  }

  const userNext = () => { next(); restart() }
  const userPrev = () => { prev(); restart() }

  function fromHash() {
    const m = location.hash.match(/^#\/how\/([\w-]+)(?:\/(\d+))?/)
    if (!m) return false
    const to = scenes.findIndex((sc) => sc.id === m[1])
    if (to < 0) return false
    const toStep = Math.max(0, (Number(m[2]) || 1) - 1)
    if (to !== i || toStep !== step) go(to, toStep, true)
    return true
  }

  prevBtn.addEventListener('click', userPrev)
  nextBtn.addEventListener('click', userNext)
  el.play.addEventListener('click', toggle)
  // Swipe: a mostly sideways move of more than 48 px over the stage; a vertical drag scrolls the page as usual.
  let x0 = null
  let y0 = 0
  el.stage.addEventListener('pointerdown', (e) => { x0 = e.clientX; y0 = e.clientY })
  el.stage.addEventListener('pointercancel', () => { x0 = null })
  el.stage.addEventListener('pointerup', (e) => {
    const dx = x0 == null ? 0 : e.clientX - x0
    if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(e.clientY - y0)) (dx < 0 ? userNext : userPrev)()
    x0 = null
  })
  window.addEventListener('hashchange', fromHash)
  setPlay(false)
  if (!fromHash()) go(0, 0)

  return {
    next: userNext, prev: userPrev, toggle, stop,
    goTo: (k, kStep = 0) => go(k, kStep, true),
    destroy() {
      stop()
      clearTimeout(hintTimer)
      window.removeEventListener('hashchange', fromHash)
      try { ctrl?.destroy() } catch (err) { console.warn(err) }
    },
  }
}
