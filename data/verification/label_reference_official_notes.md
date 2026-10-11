# Reference A: missile strikes on Kyiv city, 2026-05-01 to 2026-10-10 (blind, label not opened)

Files: strike_days.csv (55 rows). Scripts in this folder, run with python3 -I. Sources read: kpszsu, VA_Kyiv, vitaliy_klitschko, V_Zelenskiy_official, OP_UA (bronze only).

## Counts per month by verdict
| month | missile_city | missile_oblast_only | unclear_type | drone_only |
|---|---|---|---|---|
| 2026-05 | 2 | 0 | 1 | 1 |
| 2026-06 | 3 | 0 | 1 | 0 |
| 2026-07 | 9 | 0 | 1 | 1 |
| 2026-08 | 5 | 0 | 3 | 4 |
| 2026-09 | 6 | 0 | 4 | 8 |
| 2026-10 | 2 | 0 | 0 | 4 |
| total | 27 | 0 | 10 | 18 |

missile_city = 27 days. drone_only is NOT complete (listed only when seen, not hunted).

## Coverage: kpszsu night/day summaries (posts with ZBYTO/PODAVLENO or "atakuvav") per month
| month | summaries | of them mention missiles |
|---|---|---|
| 2026-05 | 36 | 16 |
| 2026-06 | 30 | 13 |
| 2026-07 | 31 | 24 |
| 2026-08 | 34 | 19 |
| 2026-09 | 37 | 14 |
| 2026-10 | 11 | 1 |
| total | 179 | 87 |

Days with no kpszsu summary: 2026-05-11 (no Kyiv city events found in VA_Kyiv or Klitschko that day either).
Honest reading depth: the 87 summaries that mention missiles were read (30 in full, 57 condensed to attack line, hit line and main direction). The other 92 were only scanned by regex for missile words, not read.

## Rules I used
- Day = "u nich na X" window: 18:00 Kyiv on X-1 to 18:00 Kyiv on X. Events between 18:00 and 24:00 Kyiv go to the next date. Rows where the first city event is before 00:00 Kyiv of the listed date: 2026-05-03 (23:10 Kyiv 05-02, unclear), 2026-06-26 (21:00 Kyiv 06-25), 2026-08-20 (23:57 Kyiv 08-19), 2026-08-30 (23:48 Kyiv 08-29, drone), 2026-09-19 (19:32 Kyiv 09-18).
- Kyiv city evidence comes from Klitschko and VA_Kyiv posts (explosions, AD working, debris, hits in named city districts). Kyiv oblast events (Bucha district, Vyshneve, Boryspil, Mila, Yahotyn) are not city.
- missile_city needs a post that ties the city event to missiles (ballistic, "debris of a missile", Zelensky or VA text about missiles on Kyiv). First_time_utc is the first city event post of that attack. Empty for 2026-09-01 and 2026-09-30 (no post gives the missile time). For 07-02 and 09-29 an earlier drone-only wave the same evening is ignored.
- jet drones: city posts that say "reaktyvni" (2026-09-11, 2026-09-27) are unclear_type per your rule. Plain "shahed" or "BpLA" city posts are drone_only (10-02 to 10-04 included).
- n_missiles filled only where a Kyiv-specific post states it: 06-15 more than 60, 07-06 68, 07-19 more than 40, 08-05 28 (Kyiv and oblast together). Empty otherwise (national counts are in kpszsu posts, not Kyiv-specific).
- missile_types come from the kpszsu summaries of that window and are national, not Kyiv-only. "Banderol" is listed as a type name only.
- Quote = exact substring of the post, newlines replaced by one space, cut at 200 chars or before a dash character.

## Weak missile_city (kept, please judge)
- 2026-07-24: daytime ballistic strike on Kyiv oblast (kpszsu/69965: 3 Iskander at about 11:30, 2 hit Bucha district). City evidence is only Klitschko "Vybukhy v misti, pratsiuiut syly PPO" at 11:29 Kyiv. No debris in the city reported.
- 2026-09-19: evening 09-18 Klitschko "PPO pratsiuiut, Kyiv pid obstrilom balistykoiu". No explosion or debris tied to missiles; kpszsu says the 2 Zircon missiles did not reach targets.
- 2026-07-30: Klitschko "bie po stolytsi balistykoiu" plus debris and fires, debris not named as missile debris.
- 2026-07-06: city debris posts do not name missiles; missile link is VA and Zelensky text (68 missiles, Kyiv main direction).
- 2026-09-01: Klitschko 7375 says debris of drones and missile in Holosiivskyi; no time for the missile.
- 2026-09-30: VA 21255 says ballistic missiles and drones attacked the capital; no post times the missiles.

## Days I could not decide (unclear_type) and why
- 2026-05-03: explosions and AD in Kyiv at 23:10 Kyiv; only 1 ballistic missile nationally and 268 drones, nothing ties the explosions to the missile.
- 2026-06-28: AD in capital, 1 injured; 2 Zircon/Oniks and 6 Iskander launched nationally, city posts name no weapon.
- 2026-07-26: debris and fires on residential buildings; summary has 7 Iskander and Kh-59, city posts name no weapon.
- 2026-08-08: fires in two districts, 4 injured; 6 Iskander nationally, city posts name no weapon.
- 2026-08-22: fire and 1 dead in Darnytskyi; summary main direction Kyiv oblast and Odesa, ballistic and Kh-59, city posts name no weapon.
- 2026-08-27: gymnasium damaged, debris in Podilskyi and Shevchenkivskyi; Zelensky says "drones and ballistic" overall.
- 2026-09-11 and 2026-09-27: daytime attacks on Kyiv by jet Shaheds.
- 2026-09-17: debris in several districts; Zelensky mentions ballistic overall, city posts name no weapon (earlier hit that evening was a BpLA).
- 2026-09-22: night strikes on two districts, 4 injured; summary has Iskander, Kalibr, Oniks but main direction is not Kyiv.

## Gaps and open points
- No missile_oblast_only rows: I did not search Kyiv oblast evidence systematically. Seen but not proven as missiles: 06-05 Yahotyn plant, 08-29 Mila detonation, 09-05 Boryspil damage.
- Days with national missiles and no Kyiv evidence in the posts I used (not listed): 05-04, 05-05, 05-06, 05-09, 05-15, 05-18, 05-20, 05-21, 05-26, 05-28, 05-29, 05-30, 06-04, 06-05, 06-09, 06-11, 06-16, 06-18, 06-21, 06-22, 07-01, 07-03, 07-04, 07-05, 07-09, 07-12, 07-13, 07-15, 07-17, 07-18, 07-20, 07-22, 07-23, 07-25, 08-04, 08-06, 08-09, 08-10, 08-19, 08-24, 08-31, 09-05, 09-12.
- Used kpszsu, VA_Kyiv, Klitschko, Zelensky, OP_UA; GeneralStaffZSU gave nothing about Kyiv city. That list of national-missile days with no Kyiv evidence was built from regex windows, not each day checked by hand. Telegram posts can be edited or missing; a missing post means missing evidence, not a quiet night.
