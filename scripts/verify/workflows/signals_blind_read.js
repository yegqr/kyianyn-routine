export const meta = {
  name: 'prep-signals-blind-read',
  description: 'Haiku agents read every post of the 6 signal channels batch by batch and mark strategic aviation, MiG-31K and attack drones per hour, blind to silver',
  phases: [{ title: 'Read', detail: 'one Haiku agent per batch of whole UTC hours', model: 'haiku' }],
}

const DIR = args.dir
const N = args.n  // args: {dir: batches folder of signals_check.py batches, n: number of batch files}

const SCHEMA = {
  type: 'object',
  properties: {
    batch: { type: 'string' },
    hours: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          hour: { type: 'string' },
          s1: { type: 'string', enum: ['live', 'recap', 'none'] },
          s1_refs: { type: 'array', items: { type: 'string' } },
          s2_airborne: { type: 'boolean' },
          s2_all_clear: { type: 'boolean' },
          s2_refs: { type: 'array', items: { type: 'string' } },
          s4: { type: 'string', enum: ['attack', 'other_drone', 'none'] },
          s4_ref: { type: 'string' },
        },
        required: ['hour', 's1', 's2_airborne', 's2_all_clear', 's4'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['batch', 'hours'],
}

function prompt(bid) {
  return `You check Telegram posts by hand. Read the WHOLE file ${DIR}/${bid}.txt with the Read tool (if it is refused as too large, pass allow_large: true or read it in parts with offset and limit; never skip a part). Do not open any other file.

The file holds every post of 6 Ukrainian monitoring channels for some UTC hours, grouped under "=== HOUR YYYY-MM-DDTHH:00Z" headers. Each line: [time UTC] channel/post_id: text (" / " marks a line break). Posts are in Ukrainian or Russian. Read them literally, do not guess.

For EACH hour decide, from the posts under that hour's header only:

1. s1, Russian strategic or long-range bombers (Tu-95MS, Tu-160, Tu-22M3; slang "борти", "СА/ДА", "стратеги", "стратегічна авіація"):
   - "live": a post says they took off, are in the air, are launching missiles, or are relocating between airfields NOW or within the last hour;
   - "recap": only a summary of earlier activity ("за сьогодні відмічено", "станом на ...", "за добу"), a forecast, satellite imagery or analysis;
   - "none": nothing about these bombers in this hour.
2. s2_airborne: a post says MiG-31K (Kinzhal carrier, "МіГ-31К", "МиГ-31К") took off or is in the air now. s2_all_clear: a post says the MiG-31K landed or gives an all clear for the MiG-31K. A generic air raid all clear without MiG-31K does not count.
3. s4, attack drones (Shahed, Geran/"Герань", Gerbera, "мопеди", "шахеди", jet drones "реактивні БпЛА", "ударні БпЛА", tracks like "БпЛА на ...", "🛵", "🏍"):
   - "attack": a post reports attack drones launched or flying over or toward Ukraine now, any region;
   - "other_drone": only reconnaissance drones, or a drone you cannot tell is an attack drone;
   - "none": no drone in flight reported in this hour. A summary of last night ("вночі збито N") alone is "none".

Reposts count like normal posts.

Return "hours" ONLY for hours where s1 is not "none", or s2_airborne or s2_all_clear is true, or s4 is not "none". An omitted hour means all none. "hour" is "YYYY-MM-DDTHH" exactly as in the header. Refs are "channel/post_id" copied from the lines: 1-3 refs for s1 and for s2 (the earliest posts that show it), s4_ref is the earliest s4 post of the hour. "batch" is "${bid}". "notes": anything unclear, at most 300 characters.`
}

phase('Read')
const ids = Array.from({ length: N }, (_, i) => 'b' + String(i).padStart(4, '0'))
const results = await parallel(ids.map(bid => () =>
  agent(prompt(bid), { label: bid, phase: 'Read', schema: SCHEMA, model: 'haiku' })))

const done = results.filter(Boolean)
const missing = ids.filter((_, i) => !results[i])
if (missing.length) log(`no result for ${missing.length} batches: ${missing.join(' ')}`)
let s1 = 0, s2a = 0, s2c = 0, s4 = 0, rows = 0
for (const r of done) for (const h of r.hours || []) {
  rows++
  if (h.s1 === 'live') s1++
  if (h.s2_airborne) s2a++
  if (h.s2_all_clear) s2c++
  if (h.s4 === 'attack') s4++
}
return { batches: N, done: done.length, missing, hour_rows: rows, s1_live_hours: s1, s2_airborne_hours: s2a, s2_all_clear_hours: s2c, s4_attack_hours: s4 }
