export const meta = {
  name: 'prep-signals-judge',
  description: 'Sonnet judges read the 147 hours where silver signals and the blind Haiku reading disagree and answer each question from the posts',
  phases: [{ title: 'Judge', detail: 'one Sonnet agent per file of about 19 hours', model: 'sonnet' }],
}
const DIR = args.dir + '/judge'
const SCHEMA = {
  type: 'object',
  properties: {
    items: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          answer: { type: 'string', enum: ['yes', 'no', 'unclear'] },
          refs: { type: 'array', items: { type: 'string' } },
          reason: { type: 'string' },
        },
        required: ['id', 'answer', 'reason'],
      },
    },
  },
  required: ['items'],
}
function prompt(g) {
  return `You are a careful judge. Read the WHOLE file ${DIR}/g${g}.txt with the Read tool (if it is refused as too large, read it in parts with offset and limit; never skip a part). Open no other file.

The file has items. Each item starts with a line "##### ITEM <id> | hour <hour> UTC | QUESTION: <question>", followed by every post of 6 Ukrainian monitoring channels published in that UTC hour, one per line: [time UTC] channel/post_id: text (" / " marks a line break). Posts are in Ukrainian or Russian.

For every item answer its QUESTION from the posts of that item only: "yes", "no", or "unclear" when the posts really do not let you decide. Read literally and do not guess. For "yes" give 1-3 refs (channel/post_id) of the posts that show it. "reason": one short sentence, at most 200 characters, quoting the decisive words.

Return one entry per item, with the item id exactly as written.`
}
// args: {dir: batches folder (judge files in dir/judge), n: number of judge files}
phase('Judge')
const res = await parallel(Array.from({ length: args.n }, (_, g) => () =>
  agent(prompt(g), { label: 'g' + g, phase: 'Judge', schema: SCHEMA, model: 'sonnet' })))
const missing = res.map((r, i) => (r ? null : 'g' + i)).filter(Boolean)
if (missing.length) log('no result for ' + missing.join(' '))
return { files: args.n, done: res.filter(Boolean).length, items: res.filter(Boolean).reduce((a, r) => a + r.items.length, 0), missing }
