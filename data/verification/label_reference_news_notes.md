# Blind reference B: Russian missile strikes on Kyiv city, 2026-05-01..2026-10-10

Built only from web pages (no project data). Tools: WebSearch and WebFetch. WebFetch answers come from a small model that summarises the page, so quotes are as the tool returned them, not raw HTML.

## Counts per month (rows in strike_days.csv)
- 2026-05: missile_city 2, missile_oblast_only 0, unclear_type 1, drone_only 3 (drone_only not hunted)
- 2026-06: missile_city 3, missile_oblast_only 0, unclear_type 1, drone_only 0 (drone_only not hunted)
- 2026-07: missile_city 9, missile_oblast_only 0, unclear_type 1, drone_only 0 (drone_only not hunted)
- 2026-08: missile_city 7, missile_oblast_only 0, unclear_type 0, drone_only 4 (drone_only not hunted)
- 2026-09: missile_city 6, missile_oblast_only 0, unclear_type 2, drone_only 1 (drone_only not hunted)
- 2026-10: missile_city 3, missile_oblast_only 0, unclear_type 0, drone_only 0 (drone_only not hunted)

Totals: missile_city 30, unclear_type 5, drone_only 8. missile_city + unclear_type = 35 days. missile_oblast_only: none found.

## Sources found
- uk.wikipedia Обстріли Києва (2026): https://uk.wikipedia.org/wiki/%D0%9E%D0%B1%D1%81%D1%82%D1%80%D1%96%D0%BB%D0%B8_%D0%9A%D0%B8%D1%94%D0%B2%D0%B0_(2026) . Per-address table with time range and weapon column (Ракета / Дрон-камікадзе). Content ends at 29 Aug; nothing for September or October. Monthly rows: May 58 alerts, June 46, July 58; August row shows two unlabeled numbers 33 and 122 (label "Атаки: ракетні та БпЛА"). No missile counts per month.
- en.wikipedia Kyiv strikes (2022-present): https://en.wikipedia.org/wiki/Kyiv_strikes_(2022%E2%80%93present) . Only major strikes (16 rows 14 May..7 Oct).
- en.wikipedia 2026 in Ukraine: thin for Kyiv (only 24 May and 5 June).
- Official KMVA monthly totals for May..Sep 2026: NOT found. The UNIAN piece "Ніколи за історію планети..." (85 missiles over Kyiv in May) is about May 2025, not used.
- Air Force figures seen in search summaries are Ukraine-wide, not Kyiv-only (2 Jun: 73 missiles; 15 Jun: 70 missiles; 2 Jul: 74 missiles).

## Evidence level per row
- Article opened: 2026-09-01 (tsn), 09-08, 09-27, 09-30 (Kyiv Independent), 10-03 (Kyiv Post), 10-10 (slovoidilo).
- Wikipedia table only (no news article opened): 06-02, 06-15, 06-25, 07-08, 07-11, 07-14, 07-19, 07-30, 08-11, 08-16, 08-20, 08-22 and all drone_only August rows, 09-11, 09-28.
- Headline only (search result title, article not opened; quote is the title): 05-02, 05-12, 05-14, 05-15, 05-23, 05-24, 06-28, 07-02, 07-06, 07-16, 07-24, 07-26, 08-01, 08-05, 08-08, 09-17, 09-24, 09-29, 10-07.

## Coverage and limits
- The uk.wikipedia table lists days with recorded damage at an address. A day where missiles were only shot down over Kyiv with no damage is likely missing, so missile_city is a lower bound.
- Days not checked by any news article: May 1 to 13 (only 2 May and 12 May seen), most of June outside 2, 15, 25, 28, most of July and August between listed dates, 2 to 7 Sep, 9 to 10 Sep, 12 to 16 Sep, 18 to 23 Sep, 25 to 26 Sep, 1 to 2 Oct, 4 to 6 Oct, 8 to 9 Oct. September and October rest on news headlines, not on a list.
- Weakest rows: 05-02 (explosions in alert for ballistic threat, weapon not confirmed), 06-25 (weapon column blank), 07-24 (headline only), 09-27 (headline says "missile strike market"; the opened article says the market was just outside the capital and overnight 28 Sep was drones; en.wikipedia says drones), 09-11 (jet drones, put in unclear_type by the rule).

## Date questions
- 2026-08-01: en.wikipedia says 31 July; uk.wikipedia times 01:28-03:54 and Al Jazeera dated 1 Aug, so 1 Aug used.
- 2026-08-07: en.wikipedia lists a 7 Aug ballistic strike on the Kyiv area (4 dead, a boy and grandparents); uk.wikipedia has no 7 Aug row (it has 8 Aug, 4 injured). Left out, unresolved.
- 2026-08-20: uk.wikipedia lists the night raid as 19-20 Aug (23:51-08:36) plus a day strike 17:03-18:55 on 20 Aug; counted as 20 Aug.
- 2026-09-24: US News headline is dated 23 Sep (US time, fetch timed out), espreso and my.ua say 24 Sep; counted as one raid on 24 Sep.
- 2026-07-02: alert ran 19:52 on 1 Jul to 07:05 on 2 Jul; counted as 2 Jul.
- 2026-09-26/27: Kyiv Independent says the night of 26 to 27 Sep killed 1 and injured 5, weapon not stated; not listed separately.
- 2026-06-05: a Nova Poshta depot explosion killed one, not attributed to a missile; not listed.
- 2026-05-13: uk.wikipedia calendar marks 13 May as a massed attack with 1 location, no details seen; not listed.
