# Bronze: журнал завантажень

Рядок на кожен запуск збирача: джерело, час запуску (UTC), записів у файлі після запуску, перший і останній час. Пише лише оркестратор.

| Джерело | Запуск UTC | Записів | Перший | Останній |
|---|---|---|---|---|
| `telegram/UkraineAlarmSignal.jsonl` (латка eTryvoga, `scripts/bronze/etryvoga_patch.py`; перший запуск 17:37:03Z) | 2026-10-10T18:15:50Z | 180 | 2026-10-10T07:58:27Z | 2026-10-10T11:50:44Z |
| `calendar/kremlin_news.jsonl` (`scripts/bronze/kremlin_fetch.py`) | 2026-10-10T17:50:55Z | 580 | 2026-04-22T06:00:00Z | 2026-10-10T07:10:00Z |
| `calendar/kremlin_trips.jsonl` (`scripts/bronze/kremlin_fetch.py`) | 2026-10-10T17:39:18Z | 20 | 2025-12-05T19:00:00Z | 2026-10-08T14:30:00Z |
| `calendar/wiki/List_of_international_presidential_trips_made_by_Vladimir_Putin` (`scripts/bronze/wiki_fetch.py`, ревізії) | 2026-10-10T17:41:20Z | 139 | 2026-04-01T00:34:54Z | 2026-10-10T07:35:36Z |
| `calendar/wiki/List_of_international_presidential_trips_made_by_Volodymyr_Zelenskyy` | 2026-10-10T17:42:35Z | 198 | 2026-04-03T00:19:36Z | 2026-10-06T06:36:23Z |
| `calendar/wiki/List_of_heads_of_state_and_government_who_have_visited_Ukraine_during_the_Russo-Ukrainian_war_(2022-present)` | 2026-10-10T17:42:44Z | 48 | 2026-04-04T17:19:58Z | 2026-09-24T20:48:22Z |
| `calendar/wiki/List_of_European_Council_meetings` | 2026-10-10T17:42:52Z | 8 | 2026-04-14T15:57:57Z | 2026-07-27T06:05:41Z |
| `calendar/wiki/Ukraine_Defense_Contact_Group` | 2026-10-10T17:43:01Z | 6 | 2026-04-15T09:11:45Z | 2026-06-23T00:44:25Z |
| `calendar/wiki/52nd_G7_summit` | 2026-10-10T17:43:24Z | 145 | 2026-04-19T13:49:49Z | 2026-09-27T06:47:10Z |
| `calendar/wiki/2026_Ankara_NATO_summit` | 2026-10-10T17:43:32Z | 71 | 2026-04-12T20:52:37Z | 2026-07-26T09:50:40Z |
| `calendar/wiki/Eastern_Economic_Forum` | 2026-10-10T17:44:05Z | 1 | 2026-09-03T14:53:18Z | 2026-09-03T14:53:18Z |
| `strikes_rf/ukwiki_list_2026/` (ревізії, `scripts/bronze/wiki_fetch.py`) | 2026-10-10T17:44:06Z | 101 | 2026-07-10T20:10:31Z | 2026-10-10T10:41:24Z |
| president.gov.ua (`scripts/bronze/president_fetch.py`): HTTP 403, нічого не збережено | 2026-10-10T17:38:31Z | 0 | | |
| `calendar/dates.csv` (з PARSING.md розділ 5, без мережі, `scripts/bronze/calendar_dates.py`) | 2026-10-10T17:38:53Z | 100 | 2026-01-01 | 2026-12-25 |
| `calendar/dates_added.csv` (кожен рядок підтверджено збереженою сторінкою Вікіпедії) | 2026-10-10T17:43:42Z | 9 | 2026-01-25 | 2026-11-11 |
| `calendar/sources/` (сторінки Вікіпедії en, uk, ru через MediaWiki API) | 2026-10-10T17:38:53Z | 16 | 2026-10-10T17:38:56Z | 2026-10-10T17:41:08Z |
