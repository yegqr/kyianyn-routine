# Scenes of the methodology deck

One file per scene, `NN-id.js`, listed in order in `index.js`. The engine is `../how.js`.

```js
import { h, s, canvas, put, stagger, promptCard, reduced } from '../how.js'

export default {
  id: 'model',                      // unique, used in the URL #/how/model/2
  title: 'Модель крок за кроком',   // short, Ukrainian
  lead: 'Одне речення простими словами.',
  steps: [                          // one entry per animation step; arrows go through steps, then to the next scene
    { note: '<p>Що видно на цьому кроці, з числами.</p>', prompts: [] },
  ],
  prompts: [{ title: 'Питання до Jev', text: '...', source: 'src/airalerts/silver/threat_hourly.py' }],  // shown on every step
  mount(stage, data) {              // stage: an empty div 16:10; data: {now, history, model, meta}, any may be null
    const svg = canvas(stage, 'опис для читача екрана')   // viewBox 0 0 640 400
    // draw everything once, in its start state
    return {
      show(step, { instant }) {},   // move to the state of `step` (0-based); must work from any step and backwards
      destroy() {},                 // stop timers and listeners
    }
  },
}
```

Rules:
- Animate only transform and opacity, through `put(node, {o, x, y, k, kx, ky}, {delay, dur, origin, instant})`; each move 200 to 400 ms, longer stories are chained with delays (`stagger`). `instant` and prefers-reduced-motion jump to the end state.
- A line or curve is "drawn" by revealing it: put it under a clipPath whose rect grows with `kx` from origin left.
- SVG text: font-size 22 units or more (the stage is about 360 px wide on a phone). Long text goes into the step notes, not into the SVG.
- Colors and fonts only from `../../css/tokens.css` (`var(--pink)`, `var(--ink)` and so on, set as `style` or `fill="var(--pink)"`); labels on colored marks are white or outside the mark.
- Every number is real: from `data` (the live JSON) or from the repo docs, and the notes name the source file. Never invent.
- Each scene shows the real prompt, question or rule used at its step in a prompt card.
- Never use the middle dot or the long dash characters.
- Styles a scene needs beyond tokens: one `<style>` element appended inside its own stage, every selector under `.scene-<id>`.
