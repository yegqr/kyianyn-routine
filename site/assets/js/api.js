// Loads the JSON files the live pipeline writes (airalerts.live.publish, contract in docs/ARCHITECTURE.md) and
// formats numbers and Kyiv times the same way everywhere on the site.

const FILES = ['now', 'history', 'model', 'meta']

export async function loadAll(base = 'api/') {
  const out = {}
  await Promise.all(FILES.map(async (name) => {
    try {
      const r = await fetch(`${base}${name}.json`, { cache: 'no-store' })
      out[name] = r.ok ? await r.json() : null
    } catch {
      out[name] = null
    }
  }))
  return out
}

const KYIV = 'Europe/Kyiv'
const hm = new Intl.DateTimeFormat('uk-UA', { timeZone: KYIV, hour: '2-digit', minute: '2-digit' })
const dm = new Intl.DateTimeFormat('uk-UA', { timeZone: KYIV, day: '2-digit', month: '2-digit' })

export const kyivTime = (iso) => hm.format(new Date(iso))
export const kyivDay = (iso) => dm.format(new Date(iso))
export const kyivStamp = (iso) => `${kyivDay(iso)} ${kyivTime(iso)}`

// 0.231 -> "23%", digits for the thresholds: pct(0.197, 1) -> "19.7%"
export const pct = (p, digits = 0) => `${(100 * p).toFixed(digits)}%`

export function ago(iso, now = Date.now()) {
  const min = Math.max(0, Math.round((now - new Date(iso).getTime()) / 60000))
  if (min < 1) return 'щойно'
  if (min < 60) return `${min} хв тому`
  const h = Math.floor(min / 60)
  return h < 24 ? `${h} год тому` : `${Math.floor(h / 24)} дн тому`
}
