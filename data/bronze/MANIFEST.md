# Bronze: журнал завантажень

Рядок на джерело або запуск збирача: джерело, час (UTC: запуск збирача або, для Telegram, рядок `done` у лозі потоку), записів у файлі після запуску, перший і останній час. Пише лише оркестратор.

| Джерело | Час UTC | Записів | Перший | Останній |
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
| `strikes_rf/dronestrikemap/20261011T083437Z/` (знімок API dronestrikemap.com: strikes, timeline, events, sources, meta і 179 файлів `days/`; `scripts/bronze/dronestrikemap_fetch.py`; 184 запити, усі HTTP 200) | 2026-10-11T08:38:54Z | 8735 точок ударів | 2024-07-30 | 2026-10-11 |
| president.gov.ua (`scripts/bronze/president_fetch.py`): HTTP 403, нічого не збережено | 2026-10-10T17:38:31Z | 0 | | |
| `calendar/dates.csv` (з PARSING.md розділ 5, без мережі, `scripts/bronze/calendar_dates.py`) | 2026-10-10T17:38:53Z | 100 | 2026-01-01 | 2026-12-25 |
| `calendar/dates_added.csv` (кожен рядок підтверджено збереженою сторінкою Вікіпедії) | 2026-10-10T17:43:42Z | 9 | 2026-01-25 | 2026-11-11 |
| `calendar/sources/` (сторінки Вікіпедії en, uk, ru через MediaWiki API) | 2026-10-10T17:38:53Z | 16 | 2026-10-10T17:38:56Z | 2026-10-10T17:41:08Z |
| `weather/ecmwf_ifs_runs.csv` (Open-Meteo single runs ECMWF IFS, `scripts/bronze/wx_backfill.py`; 681 сирих JSON, прогін 2026-06-10T12:00 дав HTTP 400, він у `ecmwf_ifs_missing_runs.csv`) | 2026-10-10T17:37:24Z | 114408 | прогін 2026-04-23T00:00Z | прогін 2026-10-10T06:00Z |
| `astro/kyiv_astro_hourly.csv` (формули, без мережі, `scripts/bronze/kyiv_astro.py`) | 2026-10-10T17:37:16Z | 4608 | 2026-04-23T00:00:00Z | 2026-10-31T23:00:00Z |
| `astro/kyiv_astro_daily.csv` (те саме) | 2026-10-10T17:37:16Z | 192 | 2026-04-23 | 2026-10-31 |
| `telegram/VA_Kyiv.jsonl` (`tg_fetch.py`, потік A, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T17:12:21Z | 2762 | 2026-04-17T05:59:01Z | 2026-10-10T17:11:31Z |
| `telegram/vitaliy_klitschko.jsonl` (`tg_fetch.py`, потік A, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T17:12:25Z | 840 | 2026-04-18T09:15:59Z | 2026-10-10T16:28:10Z |
| `telegram/truexakyiv.jsonl` (`tg_fetch.py`, потік A, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T18:55:25Z | 13787 | 2026-04-17T02:17:55Z | 2026-10-10T17:34:47Z |
| `telegram/war_monitor.jsonl` (`tg_fetch.py`, потік A, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T19:44:58Z | 8361 | 2026-04-16T21:01:15Z | 2026-10-10T11:36:43Z |
| `telegram/AerisRimor.jsonl` (`tg_fetch.py`, потік A, 4 частини, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T19:45:00Z | 22729 | 2026-04-16T22:13:16Z | 2026-10-10T19:36:49Z |
| `telegram/kyiv_nebo.jsonl` (`tg_fetch.py`, потік B, 3 частини, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T19:44:42Z | 8215 | 2026-04-17T16:51:31Z | 2026-10-10T18:13:59Z |
| `telegram/kyiv_airdef.jsonl` (`tg_fetch.py`, потік B, 4 частини, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T19:39:21Z | 45341 | 2026-04-17T16:51:57Z | 2026-10-10T16:59:33Z |
| `telegram/OP_UA.jsonl` (`tg_fetch.py`, потік A, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T17:23:19Z | 808 | 2026-04-17T11:30:23Z | 2026-10-10T15:03:01Z |
| `telegram/V_Zelenskiy_official.jsonl` (`tg_fetch.py`, потік A, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T17:35:32Z | 1341 | 2026-04-17T10:59:55Z | 2026-10-10T16:54:31Z |
| `telegram/StrategicaviationT.jsonl` (`tg_fetch.py`, потік B, 3 частини, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T19:40:21Z | 12786 | 2026-04-17T05:48:30Z | 2026-10-10T19:37:24Z |
| `telegram/kpszsu.jsonl` (`tg_fetch.py`, потік C, 4 частини, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T20:11:16Z | 24792 | 2026-04-16T21:12:38Z | 2026-10-10T18:47:27Z |
| `telegram/monitorwarr.jsonl` (`tg_fetch.py`, потік C, 3 частини, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T20:07:38Z | 6748 | 2026-04-16T23:03:30Z | 2026-10-10T19:33:49Z |
| `telegram/vanek_nikolaev.jsonl` (`tg_fetch.py`, потік C, 2 частини, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T19:59:44Z | 3112 | 2026-04-16T22:26:03Z | 2026-10-09T20:16:48Z |
| `telegram/mod_russia.jsonl` (`tg_fetch.py`, потік C, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T17:40:30Z | 4028 | 2026-04-16T22:02:48Z | 2026-10-10T15:51:01Z |
| `telegram/GeneralStaffZSU.jsonl` (`tg_fetch.py`, потік C, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T18:05:34Z | 2009 | 2026-04-17T04:00:12Z | 2026-10-10T12:01:01Z |
| `telegram/mos_sobyanin.jsonl` (`tg_fetch.py`, потік C, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T18:23:19Z | 1233 | 2026-04-17T08:00:14Z | 2026-10-10T12:30:44Z |
| `telegram/favt_info.jsonl` (`tg_fetch.py`, потік C, розширено до FETCH_FROM 2026-04-16T21:00Z) | 2026-10-10T18:49:24Z | 3970 | 2026-04-16T21:17:59Z | 2026-10-10T14:10:19Z |
