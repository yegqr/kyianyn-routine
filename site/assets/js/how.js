// The methodology deck: one scene per step of the project, each scene animates in a few steps.
// Scenes live in ./scenes/ and follow the contract in ./scenes/README.md. URL: #/how/<scene id>/<step number from 1>.
// The shell (app.js) shows the tab and forwards keys: next(), prev(), toggle().

import { SCENES } from './scenes/index.js'

const SVG_NS = 'http://www.w3.org/2000/svg'
const RM = window.matchMedia('(prefers-reduced-motion: reduce)')
export const reduced = () => RM.matches

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

// A fresh SVG canvas for a scene: every scene draws in 640 x 400 units (16:10). On a phone the stage is about
// 360 px wide, so SVG text needs font-size 22 or more to stay readable; long text goes to the notes, not the SVG.
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
    id, title: 'Цей крок ще готується', lead: 'Сцена з’явиться тут найближчим часом.',
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
    stage: h('div', { class: 'how-stage' }),
    cap: h('p', { class: 'how-cap', 'aria-hidden': 'true' }),
    step: h('span', { class: 'how-step' }),
    play: h('button', { class: 'pill how-play', type: 'button', 'aria-pressed': 'false', html: ICON.play + '<span>Грати</span>' }),
  }
  const prevBtn = h('button', { class: 'pill how-arrow', type: 'button', 'aria-label': 'Назад', html: ICON.prev })
  const nextBtn = h('button', { class: 'pill how-arrow', type: 'button', 'aria-label': 'Далі', html: ICON.next })
  const dots = scenes.map((sc, i) => h('button', {
    class: 'how-dot', type: 'button', 'aria-label': `Крок ${i + 1}: ${sc.title}`, title: sc.title,
    on: { click: () => go(i, 0, true) },
  }))
  root.replaceChildren(h('div', { class: 'how' },
    h('div', { class: 'how-text' }, el.kicker, el.title, el.lead, el.note, el.prompts),
    h('div', { class: 'how-side' }, h('div', { class: 'how-frame' }, el.stage, el.cap),
      h('nav', { class: 'how-nav', 'aria-label': 'Кроки методології' },
        prevBtn, h('div', { class: 'how-dots' }, dots), el.step, el.play, nextBtn))))

  let i = -1
  let step = 0
  let ctrl = null
  let timer = null

  function render() {
    const sc = scenes[i]
    const st = sc.steps[step] || {}
    el.kicker.textContent = `Крок ${i + 1} з ${scenes.length}`
    el.title.textContent = sc.title
    el.lead.textContent = sc.lead || ''
    el.note.innerHTML = st.note || ''
    el.prompts.replaceChildren(...[...(st.prompts || []), ...(sc.prompts || [])].map(promptCard))
    el.step.textContent = `${step + 1} / ${sc.steps.length}`
    el.cap.textContent = `Крок ${step + 1} з ${sc.steps.length}: стрілки або свайп`
    el.stage.setAttribute('aria-label', sc.title)
    dots.forEach((d, j) => d.setAttribute('aria-current', j === i ? 'step' : 'false'))
    prevBtn.disabled = i === 0 && step === 0
    nextBtn.disabled = i === scenes.length - 1 && step === sc.steps.length - 1
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
        el.stage.replaceChildren(h('p', { class: 'how-empty', text: 'Сцена не змогла намалюватись' }))
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
    el.play.setAttribute('aria-pressed', 'false')
    el.play.innerHTML = ICON.play + '<span>Грати</span>'
  }

  function toggle() {
    if (timer) return stop()
    timer = setInterval(next, 3200)
    el.play.setAttribute('aria-pressed', 'true')
    el.play.innerHTML = ICON.pause + '<span>Пауза</span>'
  }

  function fromHash() {
    const m = location.hash.match(/^#\/how\/([\w-]+)(?:\/(\d+))?/)
    if (!m) return false
    const to = scenes.findIndex((sc) => sc.id === m[1])
    if (to < 0) return false
    const toStep = Math.max(0, (Number(m[2]) || 1) - 1)
    if (to !== i || toStep !== step) go(to, toStep, true)
    return true
  }

  prevBtn.addEventListener('click', prev)
  nextBtn.addEventListener('click', next)
  el.play.addEventListener('click', toggle)
  let x0 = null
  el.stage.addEventListener('pointerdown', (e) => { x0 = e.clientX })
  el.stage.addEventListener('pointerup', (e) => {
    if (x0 != null && Math.abs(e.clientX - x0) > 48) (e.clientX < x0 ? next : prev)()
    x0 = null
  })
  window.addEventListener('hashchange', fromHash)
  if (!fromHash()) go(0, 0)

  return {
    next, prev, toggle, stop,
    goTo: (k, kStep = 0) => go(k, kStep, true),
    destroy() {
      stop()
      window.removeEventListener('hashchange', fromHash)
      try { ctrl?.destroy() } catch (err) { console.warn(err) }
    },
  }
}
