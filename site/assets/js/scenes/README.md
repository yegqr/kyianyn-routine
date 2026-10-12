# Scenes of the deck "Як це працює"

One file per scene, `NN-id.js`, listed in order in `index.js`. The engine is `../how.js`, its styles `../../css/how.css`.
The reader watches the deck, often on a phone, and never saw the code.

Words the reader sees: a scene is a "розділ", a step inside it is a "крок". The engine writes the header "Розділ 3 з 12",
the progress "крок 2 з 5", the controls "Назад", "Далі", "Автопрогравання" (a pause icon and aria-pressed while it runs)
and the stage hint "Гортай стрілками або свайпом". A step opens at `#/how/<scene id>/<step from 1>`.

Layout: on a desktop the header, title, lead, note and prompt cards are on the left, the stage and its controls on the
right. On a phone (760 px and narrower): header and title, the stage, the controls in one row, then the lead, the note
and the prompt cards. So the lead must read on its own under the picture.

```js
import { h, s, canvas, put, stagger, promptCard, reduced } from '../how.js'

export default {
  id: 'model',                         // unique, used in the URL #/how/model/2
  title: 'Як модель рахує ймовірність', // at most 6 words, plain, a claim or a question
  lead: 'Одне речення: головний висновок розділу.',
  steps: [                             // one entry per крок; arrows go through the steps, then to the next розділ
    {
      note: '<p>До 3 коротких речень, кожен термін пояснений на прикладі з наших даних.</p>'
        + '<details class="how-src"><summary>Джерела</summary><p>docs/quiet/model.md, розділ 10</p></details>',
      prompts: [],
    },
  ],
  prompts: [{ title: 'Питання до агента', text: '...', source: 'хто і коли, простими словами' }],  // on every крок
  mount(stage, data) {                 // stage: an empty div 16:10; data: {now, history, model, meta}, any may be null
    const svg = canvas(stage, 'що на малюнку, для читача екрана')   // viewBox 0 0 640 400
    // draw everything once, in its start state
    return {
      show(step, { instant }) {},      // move to the state of `step` (0-based); must work from any step and backwards
      destroy() {},                    // stop timers and listeners
    }
  },
}
```

Rules:
- Words: title at most 6 words, a claim or a question; lead one sentence, the takeaway; note at most 3 short sentences
  (about 60 words), every term defined at first use with an example from our data. Address the reader as "ти".
  No English words, file paths, module or variable names in visible text, except inside "Джерела".
- Note markup: `<p>` paragraphs, `<b>` for the key words, `<span class="num">28%</span>` for a big number.
- Sources: the last thing in a note is `<details class="how-src"><summary>Джерела</summary><p>...</p></details>`, one
  `<p>` with the sources separated by "; " (a doc and its section, a file). The engine shows it folded: small soft text,
  a chevron, the whole summary row is the tap target (44 px tall on touch).
- Prompt cards: `promptCard({title, text, source})` under the note. The quoted `text` is real and never edited;
  `title` and `source` are plain words (what it is, who wrote it and when); a file path goes into "Джерела".
- Animate only transform and opacity, through `put(node, {o, x, y, k, kx, ky}, {delay, dur, origin, instant})`; each
  move 200 to 400 ms, longer stories are chained with delays (`stagger`). `instant` and prefers-reduced-motion jump to
  the end state.
- A line or curve is "drawn" by revealing it: put it under a clipPath whose rect grows with `kx` from origin left.
- SVG text: font-size 18 units or more (the stage is about 358 px wide on a phone, so 18 units are about 10 px). A label
  that cannot be that big is shortened or hidden while the stage is narrower than 500 px: the stage is a CSS size
  container named `how-stage`, so a scene's style can say
  `@container how-stage (max-width: 499px) { .scene-<id> .wide-label { display: none } }` (or read `stage.clientWidth`
  in `mount`). Nothing may run off the stage edge: the stage clips at its border.
- Colors and fonts only from `../../css/tokens.css` (`var(--pink)`, `var(--ink)` and so on, set as `style` or
  `fill="var(--pink)"`); labels on colored marks are white or outside the mark.
- Every number is real: from `data` (the live JSON) or from the repo docs, and "Джерела" names the doc and its section.
  Never invent; a shortened text keeps its numbers.
- Never use the middle dot or the long dash characters.
- Styles a scene needs beyond tokens: one `<style>` element appended inside its own stage, every selector under
  `.scene-<id>`.
