# Чат 04: Аудит даних перед моделюванням

11.10.2026, 12:33 до 13:17 за київським часом, сесія ad9ddb95

Повідомлень користувача: 3 | відповідей Claude: 13 | викликів інструментів: 141 | прихованих міркувань пропущено: 164

[← Чат 03](03-2026-10-11-cleanup-and-signal-check.md) | [усі чати](all-chats.md) | [Чат 05 →](05-2026-10-11-modelling.md)

*службова примітка Claude Code про локальні команди*

*команда /clear*

### Користувач, 11.10 12:33

> Так, диви, попередній агент наробив різних дивних діїв, в тому числі Slop.pu. Твоя задача – йти в репозиторі і перевірити наші рівні зверху вниз, від голда до сільвера. і перевірити якість даних, перевірити дані на предмет витоку, на предмет агрегації, чи коректно була створена агрегація. І, загалом, наступний наш крок буде модулювання і створення моделі, прогнозування. І твоя задача – це все перевірити і спробувати якось оцінити. Твоя задача – допомогти мені верифікувати якість даних, враховуючи, що минулий агент міг галюціонувати дуже жорстко, міг потрапляти в просаки, в проблемні місця і так далі. Тобі треба це все вичистити та перевірити.  

### Користувач, 11.10 12:33

> Так, диви, попередній агент наробив різних дивних діїв, в тому числі Slop.pu. Твоя задача – йти в репозиторі і перевірити наші рівні зверху вниз, від голда до сільвера. і перевірити якість даних, перевірити дані на предмет витоку, на предмет агрегації, чи коректно була створена агрегація. І, загалом, наступний наш крок буде модулювання і створення моделі, прогнозування. І твоя задача – це все перевірити і спробувати якось оцінити. Твоя задача – допомогти мені верифікувати якість даних, враховуючи, що минулий агент міг галюціонувати дуже жорстко, міг потрапляти в просаки, в проблемні місця і так далі. Тобі треба це все вичистити та перевірити. HANDOFF.md у доках бери  

**Bash**: Show repo history, branches and file list

```
git log --oneline | head -30 && echo ---- && git branch -a && echo ---- && ls -la && echo ---- && find . -path ./.git -prune -o -type f -print | grep -v -E '\.venv|__pycache__|node_modules' | head -200
```

<details><summary>результат: 246 рядків</summary>

```
6ea2cd9 Drop the temp folder note from the handoff: the old agent files are deleted
8ab163c Shorten the five longest docs and fix the statements that were stale
94ed080 Rewrite the handoff for the leakage review and fix stale methodology lines
4709e7d Remove dead code, files and doc statements found by the repository audit
1163744 Document why the data can be trusted and how we got here
b45404b Add the external checks of the label and the signals with their evidence
07c282c Correct two label hours found by the external check and commit the gold table
bcc6a75 Log the rf_strikes rebuild, the mass signal check and the regex-only label hours
6013a20 Correct the rf_strikes doc: 297 oblast-centre points and the weaker UTC day evidence
59a6ae3 Rebuild silver rf_strikes from dronestrikemap.com with a 30 hour day lag
d8f601c Add a bronze fetcher for the dronestrikemap.com API with one snapshot per run
4d591b2 Build silver political_events with versioned Wikipedia rows and without the world class
03b30de Add a handoff on what was built, how it was checked and what not to trust yet
296d3ab Log the gold build and the political events leak fix in the plan
2b7cf54 Add the gold, DuckDB and leakage test commands to ARCHITECTURE
3cec39d Build gold kyiv_hourly with a leakage test over every silver module
3dcd07c Log the S3b label, the F4c retry and the gold launch in the plan
a672fba Build silver kyiv_threat_hourly and kyiv_threat_posts with features and labels
c519461 Log S4 verified and the first S3b check in the plan
a922c91 Build silver prep_signal_events: strategic aviation, MiG-31K and drone waves
7f9f796 Put the 2026-10-09 signal counts of the stored text into PARSING 7
1259f71 Refresh tg_posts for the complete channels from 2026-04-16T21:00Z
c515c72 List the real bronze collectors and the silver order in ARCHITECTURE
65ed226 Log the label run, the S4 build and the new political importance scale
23693ce Rebuild rf_strikes from the new data start 2026-04-16T21:00Z
d350d04 Rebuild kyiv_alerts from the new data start 2026-04-16T21:00Z
31dbdf5 Log the S3a result, the complete Telegram bronze and the full label run
3de494e Add the Jev classifier for the hourly Kyiv missile strike label
d251407 Add the Telegram channels to the bronze manifest
750f2b0 Record the user's decisions and the political importance rework in the plan
----
* data-layers
----
total 44
drwxrwxr-x 9 ye ye 4096 Oct 10 20:26 .
drwxrwxr-x 3 ye ye 4096 Oct 10 15:17 ..
drwxrwxr-x 7 ye ye 4096 Oct 11 12:32 .git
-rw-rw-r-- 1 ye ye  107 Oct 11 12:15 .gitignore
drwxrwxr-x 5 ye ye 4096 Oct 10 20:20 .venv
drwxrwxr-x 6 ye ye 4096 Oct 11 12:16 data
```

... ще 206 рядків

</details>

**Bash**: Read the handoff document

```
cat docs/HANDOFF.md
```

<details><summary>результат: 83 рядки</summary>

```
# Хендоф: дані для прогнозу удару по Києву

Стан на 2026-10-11 близько 13:00Z. Гілка `data-layers`, 44 коміти, віддаленого репозиторію немає, нічого не запушено. Етап даних завершено: gold зібрано, перевірено і задокументовано. Далі: прискіплива перевірка витоків окремим агентом, потім моделювання. Здача завдання KSE: 2026-10-12 23:59 за Києвом ([ASSIGNMENT.md](ASSIGNMENT.md)).

Читати в такому порядку: цей файл, [ARCHITECTURE.md](ARCHITECTURE.md) (рівні, контракт, як запустити), [VERIFICATION.md](data/VERIFICATION.md) (чому даним можна довіряти), [kyiv_hourly.md](data/gold/kyiv_hourly.md) (колонки gold), [HISTORY.md](HISTORY.md) (як дійшли і від чого відмовились), [adr/](adr/).

## Що є

| Рівень | Що | Де | У git |
|---|---|---|---|
| bronze | 17 Telegram-каналів з 2026-04-16T21:00Z (163 042 пости), прогони ECMWF, астрономія, дати, Kremlin, Вікіпедія, знімок dronestrikemap; журнал `data/bronze/MANIFEST.md` | `data/bronze/`, 175 МБ | лише MANIFEST |
| silver | 11 таблиць, по документу на кожну | `data/silver/*.parquet`, `docs/data/silver/` | ні |
| кеш Jev | кожна відповідь Jev; без нього перебудова мітки й оцінок коштує гроші і дає трохи інші числа | `data/silver/_jev_cache/` (34 073 виклики, $8.97) | ні, не видаляти |
| gold | `kyiv_hourly`: 3909 годин 2026-04-30T21:00Z..2026-10-10T17:00Z, 52 колонки (`t_utc`, 50 ознак, ціль), `y_strike_3h` true 151 з 3906 (3.9%), null лише в 3 останніх цілях | `data/gold/kyiv_hourly.parquet` | так |
| докази | зовнішня перевірка мітки і сигналів | `data/verification/`, `scripts/verify/` | так |

## Що змінилось після попереднього хендофу (2026-10-11 08:00Z)

Попередній хендоф (коміт 03b30de) перелічував, чому не вірити наосліп. Стан кожного пункту:

| Пункт попереднього хендофу | Зараз |
|---|---|
| 1. Мітка без еталону, 297 годин «regex без мітки» ніхто не читав | перевірено трьома незалежними джерелами і читанням постів: 33 з 35 дат підтверджено, 2 інші підтверджують пости; 2 помилки правила виправлено (`CORRECTIONS`, колонка `corrected`); 295 годин «regex без мітки» розібрано: дрони і пости про наслідки ([VERIFICATION.md](data/VERIFICATION.md)) |
| 2. Політичні події не пройшли перевірку, у gold витік з Вікіпедії | F4d (pol-v8, версії рядків Вікіпедії) прийнято; клас `world` прибрано рішенням користувача (pol-v9, [ADR-0005](adr/0005-political-events-without-world.md)); gold перебудовано |
| 3. Тест на витік не бачить витоку всередині значень | так і є; відомі випадки перелічено нижче для перевіряльника |
| 4. Оцінки Jev типу score тягнуться до середини | у датах лишилось (дні родів військ рівно 2.0), модель бачить лише «висока дата»; оцінки ударів по РФ прибрано разом зі старою таблицею |
| 5. Telegram: видалені і відредаговані пости | без змін, масштаб для мітки не міряли |
| 6. Рішення оркестратора без «так» | правило «військове влучання» зникло разом зі старими ударами по РФ; інші рішення в [HISTORY.md](HISTORY.md), «Рішення оркестратора, що діють» |
| 7. Документи довгі | п'ять найдовших скорочено,
```

... ще 54 рядки

</details>

**Bash**: Read assignment, architecture and methodology docs

```
cat docs/ASSIGNMENT.md && echo ======= && cat docs/ARCHITECTURE.md && echo ====== && cat docs/METHODOLOGY.md
```

<details><summary>результат: 296 рядків</summary>

```
# KSE AI Agentic School: Stage 2 Assignment

Source: invitation email from the Admissions Team and the Stage 2 submission form.

## Key facts

| Item | Value |
|---|---|
| Program | KSE AI Agentic School, Stage 2 of the selection pipeline |
| Candidate email | yisakov@kse.org.ua (same as in the Stage 1 submission) |
| Deadline | Monday, 12 October 2026, 23:59 Kyiv time (EEST) |
| Language | Python |
| Task | Mini pet project: time series analysis of air raid alerts in Ukraine |
| Next stage | Stage 3: technical and motivational screening with two interviewers, including a discussion of this solution |

## Task

Build a working Python project that analyzes and forecasts air raid alerts in Ukraine as a time series.

Domain expertise in forecasting or defense analytics is not expected. AI must be the primary engineering tool used to bridge that gap, not an ornament.

## Data rules

1. Use the most recent data available.
2. Evaluate the solution on the latest period.
3. No data leakage: nothing the model is trained on or takes as input may come from after the moment the forecast is made.

### Optional: text and media data

Encouraged but not required: go beyond alert history and use text or media sources, for example:

- news
- official statements
- public Telegram channels

The same leakage rule applies: only content published before the forecast time.

## Deliverables

Submitted via the Stage 2 form. All fields are required.
```

... ще 256 рядків

</details>

**Bash**: Read gold table doc and verification doc

```
cat docs/data/gold/kyiv_hourly.md && echo ====== && cat docs/data/VERIFICATION.md
```

<details><summary>результат: 31 рядок</summary>

```
<persisted-output>
Output too large (34.5KB). Full output saved to: /home/ye/.claude/projects/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/tool-results/bvl0184st.txt

Preview (first 2KB):
# kyiv_hourly

## Що це

Один рядок це одна година t (UTC, початок години): ознаки, відомі до t, і ціль `y_strike_3h`, чи буде ракетний удар по місту Київ у `[t, t + 3 год)`. Файл `data/gold/kyiv_hourly.parquet`: 3909 рядків, 52 колонки, від 2026-04-30T21:00Z (2026-05-01 00:00 за Києвом) до зрізу 2026-10-10T17:00Z. Код `src/airalerts/gold/kyiv_hourly.py`, тест `tests/test_no_leakage.py`. Jev не викликається, усе береться з silver.

## Входи

Колонки це `features()` восьми модулів silver у порядку нижче, ціль це `labels()` модуля `threat_hourly`. Модуль читає лише view своїх таблиць silver і бере тільки відоме до t (контракт: [ARCHITECTURE.md](../../ARCHITECTURE.md)).

| модуль | таблиці silver | документ |
|---|---|---|
| `alerts` | `kyiv_alerts` | [kyiv_alerts.md](../silver/kyiv_alerts.md) |
| `threat_hourly` | `kyiv_threat_hourly` | [kyiv_threat_hourly.md](../silver/kyiv_threat_hourly.md) |
| `signals` | `prep_signal_events` | [prep_signal_events.md](../silver/prep_signal_events.md) |
| `weather` | `weather_runs` | [weather_runs.md](../silver/weather_runs.md) |
| `astro` | `astro_hourly` | [astro_hourly.md](../silver/astro_hourly.md) |
| `calendar_dates` | `calendar_dates` | [calendar_dates.md](../silver/calendar_dates.md) |
| `political_events` | `political_events` | [political_events.md](../silver/political_events.md) |
| `rf_strikes` | `strike_points`, `strike_days` | [rf_strikes.md](../silver/rf_strikes.md) |

Кожен модуль використовує власний `ASOF` як написано: `threat_hourly` бере `available_at <= t` (година, що закінчується в t, відома в t); `kyiv_alerts` ховає кінець тривоги, що не раніший за t, а `prep_signal_events` ховає колонки, відомі лише після останнього поста події; решта бере `available_at < t`.

## Зріз

...
</persisted-output>
```

</details>

**Read**: /home/ye/.claude/projects/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/tool-results/bvl0184st.txt

```
/home/ye/.claude/projects/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/tool-results/bvl0184st.txt
```

<details><summary>результат: 250 рядків</summary>

```
1	# kyiv_hourly
2	
3	## Що це
4	
5	Один рядок це одна година t (UTC, початок години): ознаки, відомі до t, і ціль `y_strike_3h`, чи буде ракетний удар по місту Київ у `[t, t + 3 год)`. Файл `data/gold/kyiv_hourly.parquet`: 3909 рядків, 52 колонки, від 2026-04-30T21:00Z (2026-05-01 00:00 за Києвом) до зрізу 2026-10-10T17:00Z. Код `src/airalerts/gold/kyiv_hourly.py`, тест `tests/test_no_leakage.py`. Jev не викликається, усе береться з silver.
6	
7	## Входи
8	
9	Колонки це `features()` восьми модулів silver у порядку нижче, ціль це `labels()` модуля `threat_hourly`. Модуль читає лише view своїх таблиць silver і бере тільки відоме до t (контракт: [ARCHITECTURE.md](../../ARCHITECTURE.md)).
10	
11	| модуль | таблиці silver | документ |
12	|---|---|---|
13	| `alerts` | `kyiv_alerts` | [kyiv_alerts.md](../silver/kyiv_alerts.md) |
14	| `threat_hourly` | `kyiv_threat_hourly` | [kyiv_threat_hourly.md](../silver/kyiv_threat_hourly.md) |
15	| `signals` | `prep_signal_events` | [prep_signal_events.md](../silver/prep_signal_events.md) |
16	| `weather` | `weather_runs` | [weather_runs.md](../silver/weather_runs.md) |
17	| `astro` | `astro_hourly` | [astro_hourly.md](../silver/astro_hourly.md) |
18	| `calendar_dates` | `calendar_dates` | [calendar_dates.md](../silver/calendar_dates.md) |
19	| `political_events` | `political_events` | [political_events.md](../silver/political_events.md) |
20	| `rf_strikes` | `strike_points`, `strike_days` | [rf_strikes.md](../silver/rf_strikes.md) |
21	
22	Кожен модуль використовує власний `ASOF` як написано: `threat_hourly` бере `available_at <= t` (година, що закінчується в t, відома в t); `kyiv_alerts` ховає кінець тривоги, що не раніший за t, а `prep_signal_events` ховає колонки, відомі лише після останнього поста події; решта бере `available_at < t`.
23	
24	## Зріз
25	
26	Зріз це остання година t, яку приймає `features()` кожного модуля: 2026-10-10T17:00:00Z. Код (`find_cutoff`) шукає її діленням навпіл між T0 і поточною годиною: модуль приймає t до кінця своїх даних, тож прийняті години йдуть префіксом. На годині 2026-10-10T18:00:00Z відмовляють два модулі (`ValueError`):
27	
28	- `alerts`: дані VA_Kyiv закінчуються 2026-10-10T17:11:31Z (ключ `data_until` у Parquet `kyiv_alerts`);
29	- `threat_hourly`: `label_end` 2026-10-10T17:11:14Z, остання допустима година `floor_hour(label_end)` = 2026-10-10T17:00:00Z.
30	
31	Інші шість модулів цю годину приймають. Рядків 3909 = годин від T0 до зрізу включно, `t_utc` унікальні й безперервні (крок 1 год). T0 і зріз записані в метаданих Parquet (`t0_utc`, `cutoff_utc`). Дані silver починаються з FETCH_FROM = 2026-04-16T21:00Z, тож вікна до 14 діб повні вже в T0.
32	
33	## Колонки
34	
35	Тип це тип у Parquet. День `d` (колонки `hol_*`, `*_imp_today`, `*_days_to_imp4`) це київський календарний день t (`Europe/Kyiv`). Повні означення і час доступності: документи silver у таблиці вище.
36	
37	| колонка | тип | джерело | означення |
38	|---|---|---|---|
39	| `t_utc` | timestamp[us] | вхід |
```

... ще 211 рядків

</details>

**Bash**: Count lines of code and docs, list skills

```
wc -l src/airalerts/*.py src/airalerts/silver/*.py src/airalerts/gold/*.py tests/*.py scripts/verify/*.py scripts/bronze/*.py docs/*.md docs/data/silver/*.md docs/adr/*.md && ls [REDACTED: приватний шлях] 2>/dev/null; ls [REDACTED: приватний шлях] 2>/dev/null | head; cat .gitignore; cat pyproject.toml
```

*прочитано інструкції skills, plugins*

**Bash**: Read gold builder and db helpers

```
cat -n src/airalerts/gold/kyiv_hourly.py && cat -n src/airalerts/db.py src/airalerts/paths.py
```

<details><summary>результат: 206 рядків</summary>

```
     1	"""Gold table kyiv_hourly: a row per hour t from T0 to the cutoff, the features() of every silver module (only what is known
     2	before t) and the label y_strike_3h (a missile strike on Kyiv in [t, t + 3 h)). Documentation: docs/data/gold/kyiv_hourly.md.
     3	
     4	    .venv/bin/python -I -m airalerts.gold.kyiv_hourly           build data/gold/kyiv_hourly.parquet, then report
     5	    .venv/bin/python -I -m airalerts.gold.kyiv_hourly report    report on the existing file
     6	"""
     7	import os
     8	import random
     9	import sys
    10	from datetime import datetime, timedelta, timezone
    11	
    12	import pyarrow.parquet as pq
    13	
    14	from ..db import connect, register_layers
    15	from ..paths import GOLD, T0
    16	from ..silver import alerts, astro, calendar_dates, political_events, rf_strikes, signals, threat_hourly, weather
    17	
    18	TABLE = "kyiv_hourly"
    19	PATH = GOLD / f"{TABLE}.parquet"
    20	T_TABLE = "gold_t"  # the table of hours that features() and labels() read
    21	HOUR = timedelta(hours=1)
    22	LABEL = "y_strike_3h"
    23	# The column groups follow t_utc, hour_kyiv and dow_kyiv in this order; the label comes last.
    24	MODULES = (("alerts", alerts), ("threat_hourly", threat_hourly), ("signals", signals), ("weather", weather),
    25	           ("astro", astro), ("calendar_dates", calendar_dates), ("political_events", political_events),
    26	           ("rf_strikes", rf_strikes))
    27	
    28	
    29	def parse_utc(s):
    30	    """'2026-04-30T21:00:00Z' to a naive datetime (UTC)."""
    31	    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    32	
    33	
    34	def iso(t):
    35	    return f"{t:%Y-%m-%dT%H:%M:%SZ}"
    36	
    37	
    38	def sql_ts(t):
    39	    return f"TIMESTAMP '{t:%Y-%m-%d %H:%M:%S}'"
    40	
```

... ще 166 рядків

</details>

**Bash**: Read the leakage test

```
cat -n tests/test_no_leakage.py
```

<details><summary>результат: 179 рядків</summary>

```
     1	"""No-leakage test of the gold table kyiv_hourly (docs/data/gold/kyiv_hourly.md, section "Тест на витік").
     2	
     3	Under -I the project root is not on sys.path, so `-m unittest tests/test_no_leakage.py` cannot import the package `tests`.
     4	Run from the project root with either of:
     5	    .venv/bin/python -I -m unittest discover -s tests -v
     6	    .venv/bin/python -I tests/test_no_leakage.py
     7	"""
     8	import ast
     9	import inspect
    10	import random
    11	import textwrap
    12	import unittest
    13	from datetime import timedelta, timezone
    14	from unittest import mock
    15	from zoneinfo import ZoneInfo
    16	
    17	import pyarrow.parquet as pq
    18	
    19	from airalerts.db import connect, register_layers
    20	from airalerts.gold import kyiv_hourly as gold
    21	from airalerts.paths import SILVER
    22	from airalerts.silver import threat_hourly
    23	
    24	N_RANDOM = 50    # random hours t checked against the ASOF views
    25	SEED = 20261011  # fixed: the same 50 hours on every run
    26	HOUR = timedelta(hours=1)
    27	KYIV = ZoneInfo("Europe/Kyiv")
    28	
    29	
    30	def sql_ts(t):
    31	    return f"TIMESTAMP '{t:%Y-%m-%d %H:%M:%S}'"
    32	
    33	
    34	def arrow(con, sql):
    35	    r = con.execute(sql)
    36	    return (r.to_arrow_table if hasattr(r, "to_arrow_table") else r.fetch_arrow_table)()
    37	
    38	
    39	def same(a, b):
    40	    """Identical values, no tolerance; null equals only null; NaN equals NaN."""
```

... ще 139 рядків

</details>

**Bash**: Read threat\_hourly module first part

```
cd /home/ye/PROJECTS/ai-school/airalerts && cat -n src/airalerts/silver/threat_hourly.py | sed -n 1,400p
```

<details><summary>помилка, 2 рядки</summary>

```
Exit code 1
/bin/bash: line 1: cd: /home/ye/PROJECTS/ai-school/airalerts: No such file or directory
```

</details>

**Bash**: Check whether the project folder still exists

```
ls /home/ye/PROJECTS/ai-school/ ; ls /home/ye/PROJECTS/ | head -50; pwd
```

<details><summary>результат: 17 рядків</summary>

```
[REDACTED: перелік служб і сайтів сервера]
```

</details>

**Bash**: Read threat\_hourly module first part

```
cat -n src/airalerts/silver/threat_hourly.py | sed -n 1,420p
```

<details><summary>результат: 420 рядків</summary>

```
     1	"""Hourly missile strike label for Kyiv city: the Jev classifier of the posts of the 7 Kyiv channels (piece S3a).
     2	Docs: docs/data/silver/kyiv_threat_hourly.md. Input: data/silver/tg_posts.parquet; bronze only for `fetched_at` (label_end).
     3	
     4	Label of hour h = 1 when missiles (ballistic, cruise, hypersonic) exploded over, were shot down over, fell as debris on
     5	or hit Kyiv city in [h, h+1h). Drones alone, the Kyiv region outside the city and a warning alone do not count.
     6	
     7	Classifier and hour rule (S3a):
     8	- label_end(), label_hours(): the data end of the label and the hours that may be labelled;
     9	- build_requests(hours): one Jev request per hour (several for a busy hour), state = prefiltered posts of [h-1h, h+1h);
    10	- post_probabilities(hours): probabilities per post of hour h (strike, threat, drone, ballistic), from the Jev cache or Jev;
    11	- hour_labels(rows, prev_rows): the hour rule, post probabilities to four booleans;
    12	- regex_rules(): rules A and B of PARSING 2 per hour (reference).
    13	Silver (S3b), contract of docs/ARCHITECTURE.md:
    14	- main() / build(): kyiv_threat_posts and kyiv_threat_hourly from the Jev cache; makes no Jev call, a request that is not
    15	  cached stops the build with the missing hours;
    16	- ASOF, features(con, t_table), labels(con, t_table, horizon_h=3).
    17	Commands (no command = build): build, report, selftest, classify, check, pilot, stats, calibrate, label_end.
    18	"""
    19	import argparse
    20	import bisect
    21	import datetime as dt
    22	import functools
    23	import json
    24	import os
    25	import random
    26	import time
    27	from collections import Counter, defaultdict
    28	
    29	import pyarrow as pa
    30	import pyarrow.parquet as pq
    31	
    32	from .. import telegram
    33	from ..db import connect
    34	from ..jev import CACHE, MODEL, USD_PER_MTOK, ask_many, usage
    35	from ..paths import FETCH_FROM, SILVER, T0
    36	from .telegram_rx import KYIV_ONLY
    37	
    38	TABLE = "kyiv_threat_hourly"          # Jev cache tag and name of the silver table
    39	PROMPT_VERSION = "kyiv_threat_hourly-v1"  # change it together with any change of the questions or of the state layout
    40	CHANNELS = ("VA_Kyiv", "vitaliy_klitschko", "truexakyiv", "war_monitor", "AerisRimor", "kyiv_nebo", "kyiv_airdef")
```

... ще 380 рядків

</details>

**Bash**: List functions and ASOF in threat\_hourly

```
grep -n "def \|ASOF\|available_at" src/airalerts/silver/threat_hourly.py | sed -n 1,200p
```

<details><summary>результат: 68 рядків</summary>

```
16:- ASOF, features(con, t_table), labels(con, t_table, horizon_h=3).
148:def questions_for(i, pid):
155:def parse_utc(s):
163:def iso(t):
167:def floor_hour(t):
172:def label_end():
182:def label_hours(start=None, end=None):
193:def _by_hour():
206:def _entry(p, h):
211:def _plan(prev, this, h):
247:def build_requests(hours, by_hour=None):
281:def _prob(a):
285:def post_probabilities(hours, workers=MAX_WORKERS, by_hour=None):
301:def hour_flag(rows, kind, one=None, two=None, official=None):
311:def fresh_rows(rows, prev_rows=()):
327:def strike_flag(rows, prev_rows=(), fresh=False, originals=False, **kw):
334:def hour_labels(rows, prev_rows=()):
349:def regex_rules():
356:    def threat_before(t):
382:def _cache_files():
387:def classify(start=None, end=None, workers=MAX_WORKERS, chunk_hours=24, log=print):
411:def calibrate():
427:def stats(start=None, end=None, log=print):
448:def check(n=20, seed=20261010, log=print):
503:def pilot_hours(seed=20261010):
511:    def add(h, g):
524:    def sample(pool, k, g):
529:    def spread(pool, k, g):
543:    def boom(h):
554:def _txt(r, n=150):
558:def pilot(workers=MAX_WORKERS, log=print):
570:    def labels(h):
630:# ---------------------------------------------------------------- silver build, ASOF, features and labels (S3b)
640:    ("jev_model", pa.string()), ("prompt_version", pa.string()), ("available_at", pa.timestamp("us"))])
646:    ("available_at", pa.timestamp("us"))])
649:# test is `available_at <= {t}`; the generic `< {t}` would hide the hour that ends exactly at t, which features() reads.
650:ASOF = {"kyiv_threat_posts": "SELECT * FROM kyiv_threat_posts WHERE available_at <= {t}",
651:        "kyiv_threat_hourly": "SELECT * FROM kyiv_threat_hourly WHERE available_at <= {t}"}
654:# available_at <= t (h + 1h <= t) are joined; the longest window is 336 h.
660:        ON k.available_at <= h.t AND k.hour_utc >= date_trunc('hour', h.t) - INTERVAL 336 HOUR)
```

... ще 28 рядків

</details>

**Bash**: Read threat\_hourly silver build, features and labels

```
sed -n 630,846p src/airalerts/silver/threat_hourly.py
```

<details><summary>результат: 215 рядків</summary>

```
# ---------------------------------------------------------------- silver build, ASOF, features and labels (S3b)
HOURLY = SILVER / "kyiv_threat_hourly.parquet"
POSTS = SILVER / "kyiv_threat_posts.parquet"
BUILD_CHUNK_HOURS = 48      # hours read from the Jev cache at a time (memory)
SINCE_CAP_H = 336           # hours_since_strike stops here: 14 days, the longest window of the features
FEATURE_COLUMNS = ("threat_prev_1h", "threat_hours_6h", "threat_hours_24h", "ballistic_hours_3h", "ballistic_hours_6h",
                   "ballistic_hours_24h", "drone_threat_prev_1h", "strikes_7d", "strikes_14d", "hours_since_strike")
POSTS_SCHEMA = pa.schema([
    ("channel", pa.string()), ("post_id", pa.int64()), ("published_at", pa.timestamp("us")), ("hour_utc", pa.timestamp("us")),
    ("p_strike", pa.float64()), ("p_threat", pa.float64()), ("p_drone", pa.float64()), ("p_ballistic", pa.float64()),
    ("jev_model", pa.string()), ("prompt_version", pa.string()), ("available_at", pa.timestamp("us"))])
HOURLY_SCHEMA = pa.schema([
    ("hour_utc", pa.timestamp("us")), ("n_posts", pa.int64()), ("n_posts_jev", pa.int64()), ("missile_strike", pa.bool_()),
    ("missile_threat", pa.bool_()), ("drone_threat", pa.bool_()), ("ballistic", pa.bool_()), ("p_strike_max", pa.float64()),
    ("first_strike_at", pa.timestamp("us")), ("evidence", pa.list_(pa.string())), ("rx_rule_a", pa.bool_()),
    ("rx_rule_b", pa.bool_()), ("corrected", pa.bool_()), ("jev_model", pa.string()), ("prompt_version", pa.string()),
    ("available_at", pa.timestamp("us"))])

# What was known before {t}. The row of hour h is known at h + 1h: all its posts were published before that instant. So the
# test is `available_at <= {t}`; the generic `< {t}` would hide the hour that ends exactly at t, which features() reads.
ASOF = {"kyiv_threat_posts": "SELECT * FROM kyiv_threat_posts WHERE available_at <= {t}",
        "kyiv_threat_hourly": "SELECT * FROM kyiv_threat_hourly WHERE available_at <= {t}"}

# Windows are whole hours before floor_hour(t): [tf - N h, tf). For t on the hour that is [t - N h, t). Only rows with
# available_at <= t (h + 1h <= t) are joined; the longest window is 336 h.
SQL_FEATURES = """
WITH h AS (SELECT DISTINCT t_utc, CAST(t_utc AS TIMESTAMP) AS t FROM {t_table}),
j AS (SELECT h.t_utc, h.t, date_trunc('hour', h.t) AS tf, k.hour_utc AS hr, k.missile_strike AS s, k.missile_threat AS m,
             k.drone_threat AS d, k.ballistic AS b
      FROM h LEFT JOIN kyiv_threat_hourly k
        ON k.available_at <= h.t AND k.hour_utc >= date_trunc('hour', h.t) - INTERVAL 336 HOUR)
SELECT t_utc,
  COALESCE(bool_or(m) FILTER (WHERE hr = tf - INTERVAL 1 HOUR), FALSE) AS threat_prev_1h,
  COUNT(*) FILTER (WHERE m AND hr >= tf - INTERVAL 6 HOUR) AS threat_hours_6h,
  COUNT(*) FILTER (WHERE m AND hr >= tf - INTERVAL 24 HOUR) AS threat_hours_24h,
  COUNT(*) FILTER (WHERE b AND hr >= tf - INTERVAL 3 HOUR) AS ballistic_hours_3h,
  COUNT(*) FILTER (WHERE b AND hr >= tf - INTERVAL 6 HOUR) AS
```

... ще 178 рядків

</details>

**Skill**

```
{
 "skill": "swarm"
}
```

<details><summary>результат: 1 рядок</summary>

```
Launching skill: swarm
```

</details>

*завантажено навичку swarm*

**Bash**: Read agent rules and ASOF of every silver module

```
cat [REDACTED: приватний шлях] 2>/dev/null | head -60; echo ----; cd /home/ye/PROJECTS/ai-school/airalers && for f in alerts signals weather astro calendar_dates political_events rf_strikes; do echo "=== $f"; grep -n -A6 "^ASOF" src/airalerts/silver/$f.py; done
```

*прочитано інструкції AGENTS.md*

**Bash**: Run the existing leakage test suite in background

```
mkdir -p /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad && (time .venv/bin/python -I -m unittest discover -s tests -v) > /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/leak_test.log 2>&1
```

<details><summary>результат: 1 рядок</summary>

```
Command running in background with ID: bslw1wivr. Output is being written to: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/871ac248-baa9-4c3a-b3df-13308891b9ff/tasks/bslw1wivr.output. You will be notified when it completes. To check interim output, use Read on that file path.
```

</details>

**Bash**: Compute univariate AUC of each gold feature against the label

```
.venv/bin/python -I -c "
import pyarrow.parquet as pq, math
t = pq.read_table('data/gold/kyiv_hourly.parquet').to_pylist()
cols = list(t[0].keys())
lab = [r for r in t if r['y_strike_3h'] is not None]
y = [int(r['y_strike_3h']) for r in lab]
def auc(x, y):
    pairs = sorted(zip(x, y))
    # rank-based AUC with ties
    n1 = sum(y); n0 = len(y)-n1
    ranks = {}
    i=0; r=[0]*len(pairs)
    while i < len(pairs):
        j=i
        while j+1 < len(pairs) and pairs[j+1][0]==pairs[i][0]: j+=1
        avg=(i+j)/2+1
        for k in range(i,j+1): r[k]=avg
        i=j+1
    s=sum(rk for rk,(xv,yv) in zip(r,pairs) if yv==1)
    return (s - n1*(n1+1)/2)/(n1*n0)
print('rows', len(t), 'labelled', len(lab), 'pos', sum(y))
for c in cols[1:-1]:
    x = [float(r[c]) for r in lab]
    a = auc(x, y)
    vals = len(set(x))
    pos_mean = sum(v for v,yy in zip(x,y) if yy)/sum(y); neg_mean = sum(v for v,yy in zip(x,y) if not yy)/(len(y)-sum(y))
    print(f'{c:26s} auc={a:.3f} distinct={vals:5d} mean_pos={pos_mean:10.3f} mean_neg={neg_mean:10.3f}')
"

```

<details><summary>результат: 51 рядок</summary>

```
rows 3909 labelled 3906 pos 151
hour_kyiv                  auc=0.303 distinct=   24 mean_pos=     6.954 mean_neg=    11.668
dow_kyiv                   auc=0.502 distinct=    7 mean_pos=     3.033 mean_neg=     3.015
alert_active               auc=0.653 distinct=    2 mean_pos=     0.444 mean_neg=     0.137
alert_active_min           auc=0.655 distinct=  563 mean_pos=    44.807 mean_neg=    13.916
alerts_started_3h          auc=0.628 distinct=    5 mean_pos=     0.682 mean_neg=     0.409
alerts_started_6h          auc=0.647 distinct=    6 mean_pos=     1.291 mean_neg=     0.819
alerts_started_24h         auc=0.515 distinct=   17 mean_pos=     3.351 mean_neg=     3.333
alert_minutes_24h          auc=0.521 distinct= 1543 mean_pos=   211.165 mean_neg=   210.538
alerts_7d                  auc=0.470 distinct=   74 mean_pos=    21.000 mean_neg=    22.574
alerts_14d                 auc=0.495 distinct=  104 mean_pos=    41.132 mean_neg=    43.010
hours_since_alert_end      auc=0.310 distinct= 3272 mean_pos=     8.664 mean_neg=    11.817
threat_prev_1h             auc=0.704 distinct=    2 mean_pos=     0.497 mean_neg=     0.089
threat_hours_6h            auc=0.755 distinct=    7 mean_pos=     1.954 mean_neg=     0.573
threat_hours_24h           auc=0.594 distinct=   14 mean_pos=     3.377 mean_neg=     2.466
ballistic_hours_3h         auc=0.670 distinct=    4 mean_pos=     0.642 mean_neg=     0.157
ballistic_hours_6h         auc=0.658 distinct=    7 mean_pos=     0.868 mean_neg=     0.329
ballistic_hours_24h        auc=0.499 distinct=    8 mean_pos=     1.305 mean_neg=     1.394
drone_threat_prev_1h       auc=0.624 distinct=    2 mean_pos=     0.437 mean_neg=     0.189
strikes_7d                 auc=0.443 distinct=   10 mean_pos=     2.887 mean_neg=     3.219
strikes_14d                auc=0.533 distinct=   14 mean_pos=     6.695 mean_neg=     6.280
hours_since_strike         auc=0.429 distinct=  306 mean_pos=    75.709 mean_neg=    93.447
s1_takeoff_6h              auc=0.685 distinct=   10 mean_pos=     2.199 mean_neg=     0.555
s1_takeoff_24h             auc=0.659 distinct=   21 mean_pos=     4.755 mean_neg=     2.391
hours_since_s1             auc=0.332 distinct= 3841 mean_pos=    12.661 mean_neg=    22.331
s2_mig31k_airborne         auc=0.529 distinct=    2 mean_pos=     0.066 mean_neg=     0.009
s4_drone_waves_6h          auc=0.684 distinct=   24 mean_pos=    15.437 mean_neg=    12.635
wx_cloud_mean_3h           auc=0.382 distinct=  301 mean_pos=    29.684 mean_neg=    43.871
wx_precip_sum_3h           auc=0.440 distinct=   98 mean_pos=     0.272 mean_neg=     0.240
wx_wind_max_3h             auc=0.444 distinct=  217 mean_pos=    10.128 mean_neg=    10.854
wx_visibility_min_3h       auc=0.469 distinct= 1232 mean_pos= 35177.616 mean_neg= 33887.340
dark_share_3h              auc=0.767 distinct=  184 mean_pos=     0.748 mean_neg=     0.313
moon_illum                 auc=0.506 distinct= 3007 mean_pos=     0.531 mean_neg=     0.525
hol_rf_symb_today       
```

... ще 17 рядків

</details>

**Bash**: Inspect bronze format and check strike hours against alerts

```
head -c 1500 data/bronze/telegram/VA_Kyiv.jsonl; echo; echo ----; .venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
print(con.execute('DESCRIBE kyiv_alerts').fetchall())
print(con.execute('DESCRIBE tg_posts').fetchall())
# strike hours vs alerts
r = con.execute('''
SELECT k.hour_utc, k.corrected,
  (SELECT count(*) FROM kyiv_alerts a WHERE a.start_utc < k.hour_utc + INTERVAL 1 HOUR AND coalesce(a.end_utc, TIMESTAMP '2100-01-01') > k.hour_utc) AS n_alert
FROM kyiv_threat_hourly k WHERE missile_strike ORDER BY 1''').fetchall()
print('strike hours', len(r), 'without any alert overlapping the hour', [x for x in r if x[2]==0])
"

```

<details><summary>результат: 7 рядків</summary>

```
{"channel": "VA_Kyiv", "post_id": 21656, "published_at": "2026-10-10T09:58:49Z", "text": "🟢 Відбій повітряної тривоги.", "edited": false, "views": "10.1K", "forwarded_from": null, "url": "https://t.me/VA_Kyiv/21656", "fetched_at": "2026-10-10T15:55:45Z"}
{"channel": "VA_Kyiv", "post_id": 21657, "published_at": "2026-10-10T10:03:19Z", "text": "У Солом'янському районі внаслідок ворожої атаки пошкоджено офісну будівлю та 25-поверховий житловий будинок на іншій локації.", "edited": true, "views": "10.3K", "forwarded_from": null, "url": "https://t.me/VA_Kyiv/21657", "fetched_at": "2026-10-10T15:55:45Z"}
{"channel": "VA_Kyiv", "post_id": 21658, "published_at": "2026-10-10T11:20:27Z", "text": "В Оболонському районі уламки впали на відкритій території житлового будинку. Інформація про пошкодження та постраждалих уточнюється.\n\nТакож за попередньою інформацією, на іншій локації в Оболонському районі пошкоджено ресторан.\n\nПросимо перебувати в укриттях до відбою повітряної тривоги.", "edited": false, "views": "11.3K", "forwarded_from": null, "url": "https://t.me/VA_Kyiv/21658", "fetched_at": "2026-10-10T15:55:45Z"
----
[('alert_id', 'BIGINT', 'YES', None, None, None), ('start_utc', 'TIMESTAMP', 'YES', None, None, None), ('end_utc', 'TIMESTAMP', 'YES', None, None, None), ('duration_min', 'DOUBLE', 'YES', None, None, None), ('max_level', 'VARCHAR', 'YES', None, None, None), ('start_source', 'VARCHAR', 'YES', None, None, None), ('start_post_id', 'BIGINT', 'YES', None, None, None), ('end_post_id', 'BIGINT', 'YES', None, None, None), ('gap_from_prev_min', 'DOUBLE', 'YES', None, None, None), ('available_at', 'TIMESTAMP', 'YES', None, None, None)]
[('channel', 'VARCHAR', 'YES', None, None, None), ('post_id', 'BIGINT', 'YES', None, None, None), ('published_at', 'TIMESTAMP', 'YES', None, None, None), ('text', 'VARCHAR', 'YES', None, None, None), ('edited', 'BOOLEAN', 'YES', None, None, None), ('forwarded_from', 'VARCHAR', 'YES', None, None, None), ('is_original', 'BOOLEAN', 'YES', None, None, None), ('views', 'BIGINT', 'YES', None, None, None), ('url', 'VARCHAR', 'YES', None, None, None), ('channel_role', 'VARCHAR', 'YES', None, None, None), ('rx_classes', 'VARCHAR[]', 'YES', None, None, None), ('rx_kyiv_city', 'BOOLEAN', 'YES', None, None, None), ('rx_evidence', 'BOOLEAN', 'YES', None, None, None), ('rx_signals', 'VARCHAR[]', 'YES', None, None, None), ('available_at', 'TIMESTAMP', 'YES', None, None, None)]
strike hours 77 without any alert overlapping the hour [(datetime.datetime(2026, 6, 2, 5, 0), False, 0), (datetime.datetime(2026, 8, 8, 1, 0), False, 0), (datetime.datetime(2026, 9, 17, 0, 0), False, 0)]
```

</details>

*сповіщення про фонове завдання: Background command "Run the existing leakage test suite in background" completed (exit code 0)*

**Bash**: Show test result and inspect strike hours with no alert

```
cat /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/leak_test.log | tail -30; cd /home/ye/PROJECTS/ai-school/airalers && .venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
for h in ['2026-06-02 05:00:00','2026-08-08 01:00:00','2026-09-17 00:00:00']:
    print('=====', h)
    print(con.execute(f\"SELECT hour_utc, missile_threat, ballistic, drone_threat, p_strike_max, first_strike_at, evidence FROM kyiv_threat_hourly WHERE hour_utc BETWEEN TIMESTAMP '{h}' - INTERVAL 2 HOUR AND TIMESTAMP '{h}' + INTERVAL 1 HOUR ORDER BY 1\").fetchall())
    print('alerts near:', con.execute(f\"SELECT start_utc, end_utc FROM kyiv_alerts WHERE start_utc BETWEEN TIMESTAMP '{h}' - INTERVAL 6 HOUR AND TIMESTAMP '{h}' + INTERVAL 3 HOUR\").fetchall())
    ev = con.execute(f\"SELECT unnest(evidence) FROM kyiv_threat_hourly WHERE hour_utc = TIMESTAMP '{h}'\").fetchall()
    for (e,) in ev:
        ch, pid = e.split('/')
        print('  ', con.execute(f\"SELECT published_at, channel, edited, left(replace(text, chr(10), ' '), 300) FROM tg_posts WHERE channel='{ch}' AND post_id={pid}\").fetchall())
"

```

<details><summary>результат: 36 рядків</summary>

```
test_01_shape_and_columns (test_no_leakage.NoLeakage.test_01_shape_and_columns) ... ok
test_02_gold_is_not_older_than_silver (test_no_leakage.NoLeakage.test_02_gold_is_not_older_than_silver) ... ok
test_03_features_on_asof_views_equal_gold (test_no_leakage.NoLeakage.test_03_features_on_asof_views_equal_gold) ... ok
test_04_hour_and_dow_in_kyiv_time (test_no_leakage.NoLeakage.test_04_hour_and_dow_in_kyiv_time) ... ok
test_05_label_is_a_strike_in_the_next_3_hours (test_no_leakage.NoLeakage.test_05_label_is_a_strike_in_the_next_3_hours) ... ok
test_06_no_feature_column_is_the_label (test_no_leakage.NoLeakage.test_06_no_feature_column_is_the_label) ... ok
test_07_labels_is_not_called_by_any_features (test_no_leakage.NoLeakage.test_07_labels_is_not_called_by_any_features) ... ok

----------------------------------------------------------------------
Ran 7 tests in 10.260s

OK

shape: 3909 rows, 52 columns, T0 2026-04-30T21:00:00Z, cutoff 2026-10-10T17:00:00Z

ASOF: 50 random t (seed 20261011) from 2026-05-01T11:00:00Z to 2026-10-09T19:00:00Z, 8 modules, 2400 feature values compared with the gold rows, differences 0; rows hidden by the ASOF views in total 6762447

real	0m10.561s
user	0m11.538s
sys	0m1.849s
===== 2026-06-02 05:00:00
[(datetime.datetime(2026, 6, 2, 3, 0), False, False, True, 0.79, None, []), (datetime.datetime(2026, 6, 2, 4, 0), True, True, True, 0.93, datetime.datetime(2026, 6, 2, 4, 20, 28), ['truexakyiv/77389', 'war_monitor/40386']), (datetime.datetime(2026, 6, 2, 5, 0), False, False, False, 0.83, datetime.datetime(2026, 6, 2, 5, 3, 20), ['truexakyiv/77412', 'truexakyiv/77414', 'truexakyiv/77421']), (datetime.datetime(2026, 6, 2, 6, 0), False, False, False, 0.7, None, [])]
alerts near: [(datetime.datetime(2026, 6, 2, 2, 58, 43), datetime.datetime(2026, 6, 2, 3, 47, 57)), (datetime.datetime(2026, 6, 2, 4, 15, 26), datetime.datetime(2026, 6, 2, 4, 49, 2))]
   [(datetime.datetime(2026, 6, 2, 5, 3, 20), 'truexakyiv', True, '🤬Є прильот по налоговій та будинках поруч у Святошинському район, – соцмережі.  ㅤ Труха⚡️Київ | Надіслати новину')]
   [(datetime.datetime(2026, 6, 2, 5, 12, 57), 'truexakyiv', True, 'Наслідки прильоту по ЖК «Медовий» з середини. ㅤ Труха⚡️Київ | Надіслати новину')]
   [(datetime.datetime(2026, 6, 2, 5, 36, 55), 'truexakyiv', True, 'Збито/подавлено 642 цілі: 40 ракет та 602 БпЛА, – ПС.  Основний напрямок удару – Київ. Також атаковано Дніпро, Харків, Запоріжжя, Полтавщину та інші регіони.  Усього ворог запустив 729 засобів повітряного нападу – 73 ракети і 656 БпЛА різних типів. ㅤ Труха⚡️Київ | Надіслати новину')]
===== 2026-08-08 01:00:00
[(datetime.datetime(2026, 8, 7, 23, 0), False, False, False, 0.08, None, []), (datetime.datetime(2026, 8, 8, 0, 0), True, True, False, 0.93, datetime.datetime(2026, 8, 8, 0, 4, 5), ['war_monitor/42340', 'truexakyiv/81861', 'truexakyiv/81867']), (datetime.datetime(2026, 8, 8, 1, 0), False, False, False, 0.72, datetime.datetime(2026, 8, 8, 1, 2, 2), ['truexakyiv/81869']),
```

... ще 8 рядків

</details>

**Bash**: Count strike hours whose evidence lies outside any alert

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
rows = con.execute('''
WITH s AS (SELECT hour_utc, first_strike_at, corrected, evidence FROM kyiv_threat_hourly WHERE missile_strike)
SELECT s.hour_utc, s.first_strike_at, s.corrected, len(s.evidence),
  (SELECT max(a.end_utc) FROM kyiv_alerts a WHERE a.start_utc <= s.first_strike_at) AS last_end_before,
  (SELECT count(*) FROM kyiv_alerts a WHERE a.start_utc - INTERVAL 10 MINUTE <= s.first_strike_at AND coalesce(a.end_utc, TIMESTAMP '2100-01-01') + INTERVAL 5 MINUTE >= s.first_strike_at) AS in_alert
FROM s ORDER BY 1''').fetchall()
out = [r for r in rows if r[5]==0]
print('strike hours', len(rows), 'first evidence post not within an alert (start-10min..end+5min):', len(out))
for r in out: print(r[:4], 'last alert end before', r[4], 'minutes after end', (r[1]-r[4]).total_seconds()/60 if r[4] else None)
# per-night structure: number of strike hours per attack night
import itertools
hs = [r[0] for r in rows]
runs=[]; cur=[hs[0]]
for a,b in zip(hs,hs[1:]):
    if (b-a).total_seconds()<=3*3600: cur.append(b)
    else: runs.append(cur); cur=[b]
runs.append(cur)
print('attack episodes', len(runs), 'hours per episode', sorted([len(r) for r in runs]))
"

```

<details><summary>результат: 5 рядків</summary>

```
strike hours 77 first evidence post not within an alert (start-10min..end+5min): 3
(datetime.datetime(2026, 6, 2, 5, 0), datetime.datetime(2026, 6, 2, 5, 3, 20), False, 3) last alert end before 2026-06-02 04:49:02 minutes after end 14.3
(datetime.datetime(2026, 8, 8, 1, 0), datetime.datetime(2026, 8, 8, 1, 2, 2), False, 1) last alert end before 2026-08-08 00:35:09 minutes after end 26.883333333333333
(datetime.datetime(2026, 9, 17, 0, 0), datetime.datetime(2026, 9, 17, 0, 34, 52), False, 3) last alert end before 2026-09-16 23:55:28 minutes after end 39.4
attack episodes 35 hours per episode [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 5, 5]
```

</details>

**Bash**: Check the dronestrikemap fetcher and bronze folders

```
sed -n 1,40p scripts/bronze/dronestrikemap_fetch.py; ls -la data/bronze/ data/bronze/*/ | head -60; ls data/silver/_jev_cache 2>/dev/null | head
```

<details><summary>результат: 104 рядки</summary>

```
#!/usr/bin/env python3
"""Bronze fetcher for dronestrikemap.com: strikes on Russia and Ukraine from its open JSON API (stdlib only).

Run: python3 -I scripts/bronze/dronestrikemap_fetch.py

Every run is one snapshot: data/bronze/strikes_rf/dronestrikemap/<fetched_at YYYYMMDDTHHMMSSZ>/ with the raw answers
  meta.json      /api/meta: every day the site has, first and last day
  strikes.json   /api/strikes: the whole strike record, one point per (day, place) with summary, confidence, sources count
  timeline.json  /api/timeline: per day and country (RU, UA): launched min/max and intercepted, by weapon, with the basis
  events.json    /api/events: truces and similar periods
  sources.json   /api/sources: the feeds the site reads
  days/<d>.json  /api/day/<d> for every day from FETCH_FROM: strikes with weapons and the articles behind them
and fetch_log.jsonl (url, status, bytes, sha256, fetched_at per request). Nothing is ever overwritten: the site has no
revision history, so the snapshots are how we know what it said at a given time. The answers carry dates only, no time
of day and no publication time (silver has to set available_at with a lag).
Polite: one request at a time, 1 s pause, browser User-Agent, retry with backoff on 429, 5xx and network errors.
"""
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "bronze" / "strikes_rf" / "dronestrikemap"
FETCH_FROM = "2026-04-16"  # Kyiv day of FETCH_FROM in src/airalerts/paths.py (2026-04-16T21:00:00Z): 14-day windows full at T0
BASE = "https://dronestrikemap.com/api/"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
           "Accept": "application/json"}
PAUSE = 1.0


def now():
    return datetime.now(timezone.utc)


def get(path, log, tries=6):
```

... ще 64 рядки

</details>

**Bash**: Check machine CPU and memory limits

```
nproc; free -g; cd /home/ye/PROJECTS/ai-school/airalers && grep -n -i "cpu\|RAM\|choom\|memory" docs/HISTORY.md | head
```

<details><summary>результат: 12 рядків</summary>

```
5
               total        used        free      shared  buff/cache   available
Mem:              30          18           2           6          16          12
Swap:              7           7           0
7:- Оркестратор (Claude Opus, Claude Code) ділив роботу на шматки; кожен шматок будував агент Sonnet (bronze, silver, документ таблиці), а приймав свіжий агент Sonnet лише з читанням: стартував з FAIL, сам запускав перевірки, пробував вхід, що мусить впасти, читав 15-30 рядків вручну. Провал повертався будівнику одним рядком, до 3 спроб, далі питання користувачу. Шматки йшли через Workflow Claude Code двома потоками: повільний (Telegram, bronze ~4 год) і швидкий (API).
9:- Ресурси сесії: 5 ядер і 10 ГБ на всі процеси, важкі команди через `choom -n 500`, DuckDB 2 потоки і 2 ГБ, до 5 агентів одночасно.
37:| Telegram bronze | один потік на канал | довгі канали (kyiv_airdef 46 тис., kpszsu 24 тис.) розбито на частини і злито; старт зсунуто на 2026-04-16 | 17 каналів, 163 042 пости |
41:| Удари по РФ S5 | 4 канали Telegram, укрВікі, важливість Jev | спроба 2: дати в state Jev; 2026-10-11 замінено на dronestrikemap: і дані, і міра слабкі, правило «військове влучання» змішувало Росію з окупованими територіями (81 з 97 постів) | переписано, прийнято |
43:| Календар F2, F3 | | president.gov.ua 403, замість нього Telegram ОП | прийнято |
65:| 2026-10-10T17:11Z | bronze Telegram, потоки A, B, C | іде |
66:| 2026-10-10T17:25Z | спільний код: paths, db, telegram, jev (перевірено пробним викликом) | є |
79:| 2026-10-10T19:32Z | S2 `tg_posts`, `telegram_rx.py` | перевірено з 1 спроби; PARSING 2 і 7 тепер посилаються на код |
```

</details>

**Write**: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/PLAN.md

```
файл: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/PLAN.md, 1867 символів
# Audit plan: data layers of airalers before modelling

Goal: confirm or refute, with commands and outputs, that gold `kyiv_hourly` is correct, free of leakage and correctly aggregated from silver, and that silver matches bronze. Read-only on the repo. Confirmed findings only.

Known before launch (orchestrator, 2026-10-11):
- tests/test_no_leakage.py: 7 OK. It is circular: features() on ASOF views vs features() on full data. It does not check that available_at itself is true.
- Univariate AUC of every gold feature vs y_strike_3h: max 0.77 (dark_share_3h). No blatant leak.
- 3 of 77 strike hours lie outside any Kyiv alert: 2026-06-02T05, 2026-08-08T01, 2026-09-17T00; evidence = aftermath posts 14-39 min after the alert end.

## Pieces (one agent each, read-only, max 5 at once)

| # | Piece | Check | Out |
|---|---|---|---|
| 1 | label: kyiv_threat_hourly.missile_strike, y_strike_3h | every strike hour classified live/aftermath/drone/unclear with posts; Jev state and cache; CORRECTIONS; effect on gold | audit/label/ |
| 2 | alerts + threat features | kyiv_alerts rebuilt from bronze; 17 gold columns recomputed in plain Python for all rows | audit/history/ |
| 3 | signals | event formation and classification do not use later posts; 5 gold columns recomputed | audit/signals/ |
| 4 | calendar_dates + political_events | available_at true; scheduled vs not; Jev sees no hindsight; 8 gold columns recomputed | audit/political/ |
| 5 | rf_strikes | 30 h lag justified; second snapshot
... ще 367 символів
```

<details><summary>результат: 1 рядок</summary>

```
File created successfully at: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/PLAN.md (file state is current in your context — no need to Read it back)
```

</details>

**Agent**: Audit strike label quality

```
You are a read-only auditor of a data pipeline. A previous AI agent built it and may have hallucinated; treat every doc statement as a claim to check, never as fact.

CONTEXT
Repo: /home/ye/PROJECTS/ai-school/airalers (Python, DuckDB, Parquet). Goal of the project: forecast a missile strike on Kyiv city in the next 3 hours, one row per hour t. Leakage rule: a forecast made at t may use only data published before t. Gold table data/gold/kyiv_hourly.parquet; target y_strike_3h = any hour in [t, t+3h) with missile_strike in silver kyiv_threat_hourly. The label comes from an LLM classifier ("Jev") run on Telegram posts of 7 Kyiv channels plus an hour rule in src/airalerts/silver/threat_hourly.py (RULE, fresh_rows, hour_labels, CORRECTIONS). Docs: docs/data/silver/kyiv_threat_hourly.md, docs/data/VERIFICATION.md, data/verification/label_compare.txt. Silver tables: data/silver/kyiv_threat_hourly.parquet, kyiv_threat_posts.parquet (p_strike etc per post), tg_posts.parquet (all posts: channel, post_id, published_at UTC, text, edited, forwarded_from), kyiv_alerts.parquet (Kyiv air raid alerts start_utc/end_utc). Quick access: `from airalerts.db import connect, register_layers; con = register_layers(connect())` gives a view per Parquet. Run Python as `.venv/bin/python -I` from the repo root.

Orchestrator already found: of 77 strike hours, 3 lie outside any Kyiv alert (2026-06-02T05, 2026-08-08T01, 2026-09-17T00); their evidence posts are 14-39 min after the alert end and read as
... ще 3206 символів
```

<details><summary>результат: 6 рядків</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a70c1b267a8530e2e (internal ID - do not mention to user. Use SendMessage with to: 'a70c1b267a8530e2e', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do not report, assume, or predict them; continue other work or respond to the user in the meantime.
Do not duplicate this agent's work — avoid working with the same files or topics it is using.
output_file: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/871ac248-baa9-4c3a-b3df-13308891b9ff/tasks/a70c1b267a8530e2e.output
Do NOT Read or tail this file via the shell tool — it is the full subagent JSONL transcript and reading it will overflow your context. If the user asks for progress, say the agent is still running; you'll get a completion notification.
```

</details>

**Agent**: Audit alerts and threat features

```
You are a read-only auditor of a data pipeline. A previous AI agent built it and may have hallucinated; treat every doc statement as a claim to check, never as fact.

CONTEXT
Repo: /home/ye/PROJECTS/ai-school/airalers (Python, DuckDB, Parquet). Goal: forecast a missile strike on Kyiv city in the next 3 hours, one row per hour t (UTC, on the hour). Leakage rule: a forecast at t may use only data published before t. Gold: data/gold/kyiv_hourly.parquet (3909 rows, 2026-04-30T21Z..2026-10-10T17Z). Column definitions: docs/data/gold/kyiv_hourly.md. Silver modules: src/airalerts/silver/alerts.py (kyiv_alerts, from Telegram channel VA_Kyiv in data/bronze/telegram/VA_Kyiv.jsonl plus scripts/bronze/etryvoga_patch.py) and src/airalerts/silver/threat_hourly.py (kyiv_threat_hourly: per hour flags missile_strike, missile_threat, drone_threat, ballistic; available_at = hour + 1h). Each module has ASOF (SQL that shows a table as known before t) and features(con, t_table). The existing test tests/test_no_leakage.py compares features() on ASOF views with gold. It is circular: it does not prove that available_at or ASOF themselves are true, nor that the SQL windows match the documented definitions. Quick access: `from airalerts.db import connect, register_layers; con = register_layers(connect())`. Run Python as `.venv/bin/python -I` from the repo root.

TASK: Independently verify the 9 alert columns (alert_active, alert_active_min, alerts_started_3h, alerts_started_6h, alerts_started_24h,
... ще 3502 символів
```

<details><summary>результат: 6 рядків</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a267e2d83d314e656 (internal ID - do not mention to user. Use SendMessage with to: 'a267e2d83d314e656', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do not report, assume, or predict them; continue other work or respond to the user in the meantime.
Do not duplicate this agent's work — avoid working with the same files or topics it is using.
output_file: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/871ac248-baa9-4c3a-b3df-13308891b9ff/tasks/a267e2d83d314e656.output
Do NOT Read or tail this file via the shell tool — it is the full subagent JSONL transcript and reading it will overflow your context. If the user asks for progress, say the agent is still running; you'll get a completion notification.
```

</details>

**Agent**: Audit preparation signals

```
You are a read-only auditor of a data pipeline. A previous AI agent built it and may have hallucinated; treat every doc statement as a claim to check, never as fact.

CONTEXT
Repo: /home/ye/PROJECTS/ai-school/airalers (Python, DuckDB, Parquet). Goal: forecast a missile strike on Kyiv city in the next 3 hours, one row per hour t (UTC, on the hour). Leakage rule: a forecast at t may use only data published before t. Gold: data/gold/kyiv_hourly.parquet (3909 rows, 2026-04-30T21Z..2026-10-10T17Z), column definitions in docs/data/gold/kyiv_hourly.md. Silver table prep_signal_events (data/silver/prep_signal_events.parquet) is built by src/airalerts/silver/signals.py from Telegram posts (data/silver/tg_posts.parquet; bronze data/bronze/telegram/*.jsonl) and possibly the LLM classifier Jev (cache in data/silver/_jev_cache/prep_signal_events/, code src/airalerts/jev.py). Signals: S1 strategic aviation takeoff/relocation, S2 MiG-31K airborne/all_clear, S4 drone waves. Doc: docs/data/silver/prep_signal_events.md, external check docs/data/VERIFICATION.md and data/verification/signals_*. available_at = first post of the event; ASOF hides some columns until last_post_at < t. The existing leak test tests/test_no_leakage.py is circular: it compares features() on ASOF views with gold, so it cannot see a leak inside the value of a row (for example an event whose existence or class was decided using posts published after available_at). Quick access: `from airalerts.db import connect,
... ще 3458 символів
```

<details><summary>результат: 6 рядків</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: ad4b7792679f1cbf6 (internal ID - do not mention to user. Use SendMessage with to: 'ad4b7792679f1cbf6', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do not report, assume, or predict them; continue other work or respond to the user in the meantime.
Do not duplicate this agent's work — avoid working with the same files or topics it is using.
output_file: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/871ac248-baa9-4c3a-b3df-13308891b9ff/tasks/ad4b7792679f1cbf6.output
Do NOT Read or tail this file via the shell tool — it is the full subagent JSONL transcript and reading it will overflow your context. If the user asks for progress, say the agent is still running; you'll get a completion notification.
```

</details>

**Agent**: Audit calendar and political events

```
You are a read-only auditor of a data pipeline. A previous AI agent built it and may have hallucinated; treat every doc statement as a claim to check, never as fact.

CONTEXT
Repo: /home/ye/PROJECTS/ai-school/airalers (Python, DuckDB, Parquet). Goal: forecast a missile strike on Kyiv city in the next 3 hours, one row per hour t (UTC, on the hour). Leakage rule: a forecast at t may use only data published before t; scheduled events (holidays, announced summits) may be used before they happen only if the announcement itself was public before t. Gold: data/gold/kyiv_hourly.parquet (3909 rows, 2026-04-30T21Z..2026-10-10T17Z), column definitions in docs/data/gold/kyiv_hourly.md. Two silver modules:
- src/airalerts/silver/calendar_dates.py -> data/silver/calendar_dates.parquet (symbolic dates, symbolism 0-5 scored by the LLM classifier Jev, available_at 2000-01-01 = known in advance); gold columns hol_rf_symb_today, hol_ua_symb_today, hol_high_tomorrow, hol_days_to_next_high. Doc docs/data/silver/calendar_dates.md.
- src/airalerts/silver/political_events.py (1700 lines) -> data/silver/political_events.parquet (events of class kyiv and russia, importance 0-5 by Jev; sources: Telegram channels, kremlin.ru pages in data/bronze/calendar/kremlin_*.jsonl with available_at = page time + 24h except announcements of future events, Wikipedia revisions in data/bronze/calendar/wiki and sources); gold columns kyiv_imp_today, russia_imp_today, kyiv_days_to_imp4, russia_days_to_imp4. Doc
... ще 3945 символів
```

<details><summary>результат: 6 рядків</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a2d041c6a6920e84a (internal ID - do not mention to user. Use SendMessage with to: 'a2d041c6a6920e84a', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do not report, assume, or predict them; continue other work or respond to the user in the meantime.
Do not duplicate this agent's work — avoid working with the same files or topics it is using.
output_file: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/871ac248-baa9-4c3a-b3df-13308891b9ff/tasks/a2d041c6a6920e84a.output
Do NOT Read or tail this file via the shell tool — it is the full subagent JSONL transcript and reading it will overflow your context. If the user asks for progress, say the agent is still running; you'll get a completion notification.
```

</details>

**Agent**: Audit RF strikes and launches

```
You are a read-only auditor of a data pipeline. A previous AI agent built it and may have hallucinated; treat every doc statement as a claim to check, never as fact.

CONTEXT
Repo: /home/ye/PROJECTS/ai-school/airalers (Python, DuckDB, Parquet). Goal: forecast a missile strike on Kyiv city in the next 3 hours, one row per hour t (UTC, on the hour). Leakage rule: a forecast at t may use only data published before t. Gold: data/gold/kyiv_hourly.parquet (3909 rows, 2026-04-30T21Z..2026-10-10T17Z), column definitions in docs/data/gold/kyiv_hourly.md. Silver module src/airalerts/silver/rf_strikes.py builds data/silver/strike_points.parquet and strike_days.parquet from one snapshot of the dronestrikemap.com API in data/bronze/strikes_rf/dronestrikemap/<timestamp>/ (fetcher scripts/bronze/dronestrikemap_fetch.py). The site has dates only, no publication time and no revision history, so the module sets available_at = day d + 30 h. Gold columns: rf_points_1d, rf_points_3d, rf_regions_3d, rf_energy_1d, rf_energy_3d, rf_moscow_3d, rf_drones_intercepted_1d, ua_missiles_launched_1d, ua_drones_launched_1d, hours_since_rf_energy. Docs: docs/data/silver/rf_strikes.md, docs/adr/0004-rf-strikes-dronestrikemap.md, data/verification/mod_russia_daily_drones.csv. The existing leak test tests/test_no_leakage.py is circular (features() on ASOF views vs gold), so it cannot see a wrong available_at. ua_missiles_launched_1d (missiles launched at Ukraine on a day) is the most dangerous column: if the lag
... ще 3419 символів
```

<details><summary>результат: 6 рядків</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a136833fce597d3a8 (internal ID - do not mention to user. Use SendMessage with to: 'a136833fce597d3a8', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do not report, assume, or predict them; continue other work or respond to the user in the meantime.
Do not duplicate this agent's work — avoid working with the same files or topics it is using.
output_file: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/871ac248-baa9-4c3a-b3df-13308891b9ff/tasks/a136833fce597d3a8.output
Do NOT Read or tail this file via the shell tool — it is the full subagent JSONL transcript and reading it will overflow your context. If the user asks for progress, say the agent is still running; you'll get a completion notification.
```

</details>

**Bash**: Log launch and read the weather module and doc

```
cat >> /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/PLAN.md <<'EOF'
- 2026-10-11: launched pieces 1-5 in parallel (general-purpose, read-only). Orchestrator takes weather, astro, gold-level probes.
EOF
cd /home/ye/PROJECTS/ai-school/airalers && cat -n src/airalerts/silver/weather.py && sed -n 1,60p docs/data/silver/weather_runs.md
```

<details><summary>результат: 155 рядків</summary>

```
     1	"""Silver weather_runs: ECMWF IFS forecast runs for Kyiv, and the wx_* features for gold.
     2	
     3	Doc: docs/data/silver/weather_runs.md. Rebuild: .venv/bin/python -I -m airalerts.silver.weather
     4	"""
     5	import os
     6	
     7	from ..db import connect
     8	from ..paths import BRONZE, SILVER
     9	
    10	SRC = BRONZE / "weather" / "ecmwf_ifs_runs.csv"
    11	OUT = SILVER / "weather_runs.parquet"
    12	LAG_H = 8  # available_at = run_utc + 8 h: actual delay 6.4 h plus margin (PARSING 3)
    13	
    14	CSV_COLUMNS = {
    15	    "run_utc": "VARCHAR", "valid_utc": "VARCHAR", "lead_h": "INTEGER", "cloud_cover_pct": "DOUBLE",
    16	    "precipitation_mm": "DOUBLE", "wind_speed_10m_kmh": "DOUBLE", "wind_gusts_10m_kmh": "DOUBLE",
    17	    "wind_direction_10m_deg": "DOUBLE", "visibility_m": "DOUBLE", "available_at_utc": "VARCHAR",
    18	    "fetched_at_utc": "VARCHAR",
    19	}
    20	ASOF = {"weather_runs": "SELECT * FROM weather_runs WHERE available_at < {t}"}
    21	
    22	
    23	def _table(res):
    24	    t = res.to_arrow_table() if hasattr(res, "to_arrow_table") else res.fetch_arrow_table()
    25	    return t.read_all() if hasattr(t, "read_all") else t
    26	
    27	
    28	def main():
    29	    con = connect()
    30	    SILVER.mkdir(parents=True, exist_ok=True)
    31	    cols = ", ".join(f"'{k}': '{v}'" for k, v in CSV_COLUMNS.items())
    32	    src = f"read_csv('{SRC}', header = true, columns = {{{cols}}})"
    33	    tmp = OUT.with_name(OUT.name + ".tmp")
    34	    con.execute(f"""
    35	        COPY (
    36	            WITH one AS (
    37	                SELECT * FROM {src}
    38	                QUALIFY row_number() OVER (PARTITION BY run_utc, valid_utc ORDER BY fetched_at_utc) = 1
    39	            )
    40	            SELECT strptime(run_utc, '%Y-%m-%dT%H:%M:%SZ') AS run_utc,
```

... ще 115 рядків

</details>

**Bash**: List installed packages and sample astro bronze

```
.venv/bin/pip list 2>/dev/null | head -40; head -3 data/bronze/astro/kyiv_astro_daily.csv; grep -E "^2026-06-21|^2026-12-21|^2026-09-22" data/bronze/astro/kyiv_astro_daily.csv; head -3 data/bronze/astro/kyiv_astro_hourly.csv
```

<details><summary>результат: 14 рядків</summary>

```
Package   Version Editable project location
--------- ------- ------------------------------------
airalerts 0.1.0   /home/ye/PROJECTS/ai-school/airalers
duckdb    1.5.6
pip       26.2.1
pyarrow   26.0.0
date_kyiv,sunrise_utc,sunset_utc,civil_dawn_utc,civil_dusk_utc,nautical_dawn_utc,nautical_dusk_utc,astro_dawn_utc,astro_dusk_utc,day_length_h,night_civil_h,night_nautical_h,moon_illum_midnight,moon_phase_midnight
2026-04-23,2026-04-23T02:48:23Z,2026-04-23T17:05:08Z,2026-04-23T02:12:46Z,2026-04-23T17:40:57Z,2026-04-23T01:28:05Z,2026-04-23T18:25:59Z,2026-04-23T00:36:42Z,2026-04-23T19:18:00Z,14.279,8.495,6.994,0.4739,0.2417
2026-04-24,2026-04-24T02:46:26Z,2026-04-24T17:06:43Z,2026-04-24T02:10:39Z,2026-04-24T17:42:42Z,2026-04-24T01:25:39Z,2026-04-24T18:28:03Z,2026-04-24T00:33:39Z,2026-04-24T19:20:43Z,14.338,8.431,6.92,0.5844,0.277
2026-06-21,2026-06-21T01:46:12Z,2026-06-21T18:13:12Z,2026-06-21T01:00:40Z,2026-06-21T18:58:45Z,2026-06-20T23:52:38Z,2026-06-21T20:06:46Z,,,16.45,6.036,3.768,0.4988,0.2496
2026-09-22,2026-09-22T03:43:55Z,2026-09-22T15:56:28Z,2026-09-22T03:11:18Z,2026-09-22T16:28:59Z,2026-09-22T02:32:45Z,2026-09-22T17:07:23Z,2026-09-22T01:52:39Z,2026-09-22T17:47:15Z,12.209,10.731,9.45,0.8492,0.3731
hour_utc,sun_alt_deg,dark_civil,dark_nautical,moon_illum,moon_phase
2026-04-23T00:00:00Z,-21.53,1,1,0.3758,0.21
2026-04-23T01:00:00Z,-15.42,1,1,0.3804,0.2116
```

</details>

**Bash**: Recompute weather features from bronze for all gold rows

```
mkdir -p /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me && cd /home/ye/PROJECTS/ai-school/airalers && cat > /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/weather_check.py <<'EOF'
import csv, json, glob, os
from datetime import datetime, timedelta
from collections import defaultdict
import pyarrow.parquet as pq
R = "/home/ye/PROJECTS/ai-school/airalers/"
H = timedelta(hours=1)
# from bronze CSV directly, not silver
runs = defaultdict(dict)  # valid -> run -> row
n = 0
for r in csv.DictReader(open(R + "data/bronze/weather/ecmwf_ifs_runs.csv")):
    n += 1
    run = datetime.strptime(r["run_utc"], "%Y-%m-%dT%H:%M:%SZ"); v = datetime.strptime(r["valid_utc"], "%Y-%m-%dT%H:%M:%SZ")
    f = lambda k: float(r[k]) if r[k] != "" else None
    runs[v].setdefault(run, (f("cloud_cover_pct"), f("precipitation_mm"), f("wind_speed_10m_kmh"), f("visibility_m")))
print("bronze csv rows", n)
gold = pq.read_table(R + "data/gold/kyiv_hourly.parquet").to_pylist()
mism = defaultdict(list); leads = []
for g in gold:
    t = g["t_utc"]; vals = []
    for k in range(3):
        v = t + k * H
        known = sorted((run, x) for run, x in runs.get(v, {}).items() if run + timedelta(hours=8) < t)
        per = []
        for i in range(4):
            c = [x[i] for run, x in known if x[i] is not None]
            per.append(c[-1] if c else None)
        if known: leads.append((v
... ще 835 символів
```

<details><summary>результат: 3 рядки</summary>

```
bronze csv rows 114408
mismatches {} {}
lead hours of the forecast used: min 9.0 max 22.0
```

</details>

**Bash**: Recompute dark share and moon illumination from bronze

```
cat > /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/astro_check.py <<'EOF'
import csv
from datetime import datetime, timedelta
import pyarrow.parquet as pq
R = "/home/ye/PROJECTS/ai-school/airalers/"
P = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ") if s else None
light = []  # civil light intervals [dawn, dusk)
for r in csv.DictReader(open(R + "data/bronze/astro/kyiv_astro_daily.csv")):
    light.append((P(r["civil_dawn_utc"]), P(r["civil_dusk_utc"])))
moon = {P(r["hour_utc"]): float(r["moon_illum"]) for r in csv.DictReader(open(R + "data/bronze/astro/kyiv_astro_hourly.csv"))}
def dark_frac(a, b):
    lit = sum(max(timedelta(0), min(b, d1) - max(a, d0)).total_seconds() for d0, d1 in light)
    return 1 - lit / (b - a).total_seconds()
gold = pq.read_table(R + "data/gold/kyiv_hourly.parquet").to_pylist()
bad_d, bad_m, worst = 0, 0, 0
for g in gold:
    t = g["t_utc"]
    e = dark_frac(t, t + timedelta(hours=3))
    worst = max(worst, abs(e - g["dark_share_3h"]))
    if abs(e - g["dark_share_3h"]) > 0.02: bad_d += 1
    if abs(moon[t] - g["moon_illum"]) > 1e-3: bad_m += 1
print("rows", len(gold), "dark_share_3h off by >0.02:", bad_d, "max abs diff", round(worst, 4), "moon_illum off:", bad_m)
EOF
.venv/bin/python -I /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/astro_check.py
```

<details><summary>результат: 1 рядок</summary>

```
rows 3909 dark_share_3h off by >0.02: 0 max abs diff 0.0056 moon_illum off: 0
```

</details>

**Bash**: Profile positives by month, onset type and recent window

```
cat > /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/gold_shape.py <<'EOF'
from collections import Counter, defaultdict
import pyarrow.parquet as pq
R = "/home/ye/PROJECTS/ai-school/airalers/"
g = [r for r in pq.read_table(R + "data/gold/kyiv_hourly.parquet").to_pylist() if r["y_strike_3h"] is not None]
m = defaultdict(lambda: [0, 0])
for r in g:
    k = f'{r["t_utc"]:%Y-%m}'; m[k][0] += 1; m[k][1] += r["y_strike_3h"]
print("month rows pos rate:", {k: (a, b, round(b / a, 3)) for k, (a, b) in sorted(m.items())})
pos = [r for r in g if r["y_strike_3h"]]
cont = [r for r in pos if r["hours_since_strike"] < 3]
alert = [r for r in pos if r["alert_active"]]
cold = [r for r in pos if r["hours_since_strike"] >= 3 and not r["alert_active"] and r["threat_hours_6h"] == 0]
print("positives", len(pos), "| strike in last 3h (continuation)", len(cont), "| alert active at t", len(alert),
      "| no recent strike, no alert, no threat in 6h (true onset with cold start)", len(cold))
# episodes of positives in the last 28 days and 14 days of the labelled range
last = g[-1]["t_utc"]
from datetime import timedelta
for d in (14, 28, 42):
    w = [r for r in g if r["t_utc"] > last - timedelta(days=d)]
    # count episodes: runs of consecutive positive rows
    ep, prev = 0, False
    for r in w:
        if r["y_strike_3h"] and not prev: ep += 1
        prev = r["y_strike_3h"]
    print(f"last {d} days: rows {len(w)}, positive rows
... ще 328 символів
```

<details><summary>результат: 6 рядків</summary>

```
month rows pos rate: {'2026-04': (3, 0, 0.0), '2026-05': (744, 13, 0.017), '2026-06': (720, 25, 0.035), '2026-07': (744, 46, 0.062), '2026-08': (744, 35, 0.047), '2026-09': (720, 24, 0.033), '2026-10': (231, 8, 0.035)}
positives 151 | strike in last 3h (continuation) 46 | alert active at t 67 | no recent strike, no alert, no threat in 6h (true onset with cold start) 32
last 14 days: rows 336, positive rows 15, positive runs (attacks) 4
last 28 days: rows 672, positive rows 26, positive runs (attacks) 7
last 42 days: rows 1008, positive rows 35, positive runs (attacks) 9
hour_kyiv of positive rows: [(0, 24), (1, 26), (2, 22), (3, 17), (4, 10), (5, 5), (6, 2), (7, 2), (8, 2), (9, 2), (10, 1), (11, 1), (12, 1), (13, 1), (14, 1), (17, 1), (18, 2), (19, 2), (20, 1), (21, 2), (22, 7), (23, 19)]
```

</details>

**Bash**: Run a time-split logistic regression leak probe in background

```
cat > /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/probe.py <<'EOF'
"""Leak probe: L2 logistic regression, time split (train before the last 42 days, test on them). Pure Python."""
import math, random
from datetime import timedelta
import pyarrow.parquet as pq
R = "/home/ye/PROJECTS/ai-school/airalers/"
g = [r for r in pq.read_table(R + "data/gold/kyiv_hourly.parquet").to_pylist() if r["y_strike_3h"] is not None]
cols = [c for c in g[0] if c not in ("t_utc", "y_strike_3h")]
split = g[-1]["t_utc"] - timedelta(days=42)
tr = [r for r in g if r["t_utc"] <= split]; te = [r for r in g if r["t_utc"] > split]
def X(rows, cs):
    return [[float(r[c]) for c in cs] for r in rows]
def auc(p, y):
    s = sorted(zip(p, y)); n1 = sum(y); n0 = len(y) - n1; rk = 0; i = 0; tot = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1][0] == s[i][0]: j += 1
        avg = (i + j) / 2 + 1
        tot += avg * sum(yy for _, yy in s[i:j + 1]); i = j + 1
    return (tot - n1 * (n1 + 1) / 2) / (n1 * n0)
def fit(cs, iters=400, lr=0.1, l2=1e-2):
    xt = X(tr, cs); yt = [int(r["y_strike_3h"]) for r in tr]
    mu = [sum(c) / len(c) for c in zip(*xt)]; sd = [max(1e-9, math.sqrt(sum((v - m) ** 2 for v in c) / len(c))) for c, m in zip(zip(*xt), mu)]
    z = lambda xs: [[(v - m) / s for v, m, s in zip(x, mu, sd)] for x in xs]
    xt = z(xt); w = [0.0] * len(cs); b = 0.0; mw = [0.0] * len(cs); vw = [0.0] * len(cs); mb =
... ще 2701 символів
```

<details><summary>результат: 1 рядок</summary>

```
Command running in background with ID: bw3udu8qt. Output is being written to: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/871ac248-baa9-4c3a-b3df-13308891b9ff/tasks/bw3udu8qt.output. You will be notified when it completes. To check interim output, use Read on that file path.
```

</details>

### Claude, 12:39

Поки працюють агенти і проба, читаю HISTORY.md: там рішення попереднього агента, ухвалені без твого «так».

**Bash**: Read the history doc and orchestrator decisions

```
sed -n 1,60p docs/HISTORY.md; grep -n -A25 "Рішення оркестратора" docs/HISTORY.md | head -40
```

<details><summary>результат: 86 рядків</summary>

```
# Історія: як зібрано дані для gold

Етап даних, 2026-10-10..2026-10-11. Мета: `data/gold/kyiv_hourly.parquet` з даних від 2026-05-01, без витоку, з перевіреними числами і документацією на кожному рівні; ціль `y_strike_3h`, ракетний удар по місту Київ у наступні 3 години. Як влаштовано зараз: [ARCHITECTURE.md](ARCHITECTURE.md); чому даним можна довіряти: [VERIFICATION.md](data/VERIFICATION.md); рішення: [adr/](adr/).

## Як працювали

- Оркестратор (Claude Opus, Claude Code) ділив роботу на шматки; кожен шматок будував агент Sonnet (bronze, silver, документ таблиці), а приймав свіжий агент Sonnet лише з читанням: стартував з FAIL, сам запускав перевірки, пробував вхід, що мусить впасти, читав 15-30 рядків вручну. Провал повертався будівнику одним рядком, до 3 спроб, далі питання користувачу. Шматки йшли через Workflow Claude Code двома потоками: повільний (Telegram, bronze ~4 год) і швидкий (API).
- Класифікацію тексту робив Jev (TypeSafe, `jev-1.13.0`) лише через `src/airalerts/jev.py`, з кешем кожної відповіді. Усього 36006 платних викликів, $9.06; кеш видаленої таблиці ударів по РФ (1933 виклики, $0.10) прибрано 2026-10-11, у кеші 34073 виклики, $8.97 (`.venv/bin/python -I -m airalerts.jev`). Перебудова з кешу безкоштовна і дає ті самі числа ([JEV.md](JEV.md)).
- Ресурси сесії: 5 ядер і 10 ГБ на всі процеси, важкі команди через `choom -n 500`, DuckDB 2 потоки і 2 ГБ, до 5 агентів одночасно.
- 2026-10-11 користувач засумнівався в мітці; далі робота йшла в одній сесії з незалежними перевірками (Haiku, Sonnet) і переробкою слабких частин.

## Рішення користувача

| Дата | Рішення |
|---|---|
| 2026-10-10 | Ціль: ракетний удар по місту Київ (вибухи, збиття, уламки, влучання), горизонт 3 год. Gold лише з ознак для моделі, вікна до 14 днів. Три рівні bronze, silver, gold; Parquet і DuckDB; Jev для мітки і оцінок 0-5. `data/bronze/` і `data/silver/` не в git. Агенти на Sonnet |
| 2026-10-10 | Свята: лише високосимволічні дати (День Конституції, дні народження Путіна і Зеленського, початок Другої світової, 8 і 9 травня). Події: офіційні анонси ОП і Kremlin, лише важливе. Погода і темрява на вікно [t, t+3) |
| 2026-10-10 | Дані з 2026-04-16T21:00Z (T0 мінус 14 діб), щоб вікна 14 діб були повні з T0. @vanek_nikolaev прибрати з сигналів |
| 2026-10-10 | Шкала важливості політичних подій «неправильна», якщо Росія не досягає 4: перероблено на складену шкалу (нижче) |
| 2026-10-11 | Версії рядків Вікіпедії замість найновішої ревізії (виправлення витоку) |
| 2026-10-11 | Клас політичних подій `world` прибрати ([ADR-0005](adr/0005-political-events-without-world.md)) |
| 2026-10-11 | Удари по РФ переробити на dronestrikemap.com, день відомий через 30 год ([ADR-0004](adr/0004-rf-strikes-dronestrikemap.md)) |
| 2026-10-11 | Реактивні дрони («Герань-3/5») і «Бандероль» не удар. Обидві знайдені помилки мітки виправити ([ADR-0006](adr/0006-external-verification.md)). Старі таблиці ударів по РФ видалити; gold і докази перевірок у git |

## Рішення оркестратора, що
```

... ще 61 рядок

</details>

**Bash**: Check probe progress

```
sleep 5; cat /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/probe.log
```

<details><summary>результат: 8 рядків</summary>

```
train 2898 rows (116 pos), test 1008 rows (35 pos), split 2026-08-29 14:00:00
naive 7-day rate AUC 0.323
all features: test AUC 0.800, AUC without continuation rows 0.761 (27 pos), Brier 0.0324 (base 0.0335)
   top weights: [('dark_share_3h', 0.73), ('threat_hours_6h', 0.37), ('strikes_7d', -0.33), ('strikes_14d', 0.29), ('alert_minutes_24h', -0.28), ('drone_threat_prev_1h', 0.27), ('s1_takeoff_6h', 0.26), ('threat_prev_1h', 0.24)]
hour+dark only: test AUC 0.780, AUC without continuation rows 0.774 (27 pos), Brier 0.0319 (base 0.0335)
   top weights: [('dark_share_3h', 0.76), ('hour_kyiv', -0.34)]
all minus kyiv history (alerts, threat): test AUC 0.839, AUC without continuation rows 0.830 (27 pos), Brier 0.0280 (base 0.0335)
   top weights: [('dark_share_3h', 0.77), ('s1_takeoff_6h', 0.44), ('s4_drone_waves_6h', 0.43), ('ua_drones_launched_1d', -0.27), ('hour_kyiv', -0.23), ('kyiv_imp_today', -0.23), ('ua_missiles_launched_1d', 0.22), ('rf_energy_1d', 0.2)]
```

</details>

*сповіщення про фонове завдання: Background command "Run a time-split logistic regression leak probe in background" completed (exit code 0)*

**Write**: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/report.md

```
файл: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/report.md, 1491 символів
# Orchestrator checks (weather, astro, gold-level)

All scripts in this folder, run with `.venv/bin/python -I <script>` from the repo root.

- tests/test_no_leakage.py: 7 OK, 2400 values, 0 differences (scratchpad/leak_test.log). Circular by design: does not check available_at itself.
- Univariate AUC per gold feature vs y_strike_3h: max dark_share_3h 0.767, threat_hours_6h 0.755. No single column looks like the label.
- weather_check.py: wx_* recomputed from bronze CSV (not silver) for all 3909 rows, run known if run + 8 h < t: 0 mismatches. Lead of the forecast used: 9..22 h.
- astro_check.py: dark_share_3h from bronze civil dawn/dusk: max diff 0.0056, 0 rows off by > 0.02; moon_illum 0 off. Sunrise/sunset 2026-06-21 and 2026-09-22 match real Kyiv times within a minute.
- Strike hours vs alerts: 3 of 77 strike hours lie outside any Kyiv alert (2026-06-02T05, 2026-08-08T01, 2026-09-17T00), evidence = aftermath posts 14-39 min after the all clear.
- gold_shape.py: 151 positive rows from 35 attacks; 46 positives have a strike in the last 3 h (continuation); 32 are cold onsets (no strike in 3 h, no alert, no threat in 6 h). Last 28 days: 7 attacks, 26 positive rows. Positives by month 13, 25, 46, 35, 24, 8 (Oct partial).
- probe.py: L2 logistic, train before 2026-08-29T14Z, test last 42 days (1008 rows, 35 pos): all features AUC 0.800; hour + dark only 0.780; without Kyiv history 0.839. Brier 0.0324 vs base 0.0335. No sign of a leak; most of the signal is time of day.

```

<details><summary>результат: 1 рядок</summary>

```
File created successfully at: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/report.md (file state is current in your context — no need to Read it back)
```

</details>

**Bash**: Find stale statements and banned characters in docs

```
grep -n "^ча$\|PLAN\|Світ\|оцінює Jev (0-5)" docs/*.md docs/data/*.md docs/data/*/*.md docs/adr/*.md | head -20; grep -rn "·\|—" docs/ src/ scripts/ tests/ | wc -l
```

<details><summary>результат: 9 рядків</summary>

```
docs/METHODOLOGY.md:47:| **Світ** | Саміти НАТО, G7, ЄС; переговори щодо війни; дзвінки Трамп і Путін; оголошення військової допомоги та санкцій |
docs/METHODOLOGY.md:78:  - Важливість кожного удару оцінює Jev (0-5) за рубрикою; реальний вплив на обстріли вчить модель.
docs/METHODOLOGY.md:86:ча
docs/METHODOLOGY.md:138:docs/                   ASSIGNMENT, METHODOLOGY, PARSING, ARCHITECTURE, JEV, PLAN, adr/, data/silver/, data/gold/
docs/data/silver/kyiv_alerts.md:33:Склеювання (PARSING 1): старт відкриває тривогу; ще один старт при відкритій тривозі це пояснення або зміна рівня (піднімає `max_level`); відбій закриває. Відбій без відкритого старту бере старт з латки: останній старт Києва в eTryvoga перед відбоєм, пізніший за кінець попередньої тривоги, інакше модуль зупиняється з помилкою. Виняток: перший відбій у даних без старту (перед першою тривогою) закриває тривогу, що почалась до FETCH_FROM; це не тривога нашого періоду, і модуль його відкидає. Старт з eTryvoga для нього береться, лише якщо він пізніший за FETCH_FROM. Відкинуті відбої друкує `main()` у `dropped_end_post_ids`. Відбій і новий старт за кілька секунд чи хвилин лишаються двома тривогами (PLAN: червоний на жовтий з паузою до 2 хв): склеїти пізніше можна за `gap_from_prev_min`.
docs/data/silver/kyiv_alerts.md:43:`features(con, t_table)` повертає `pyarrow.Table`: `t_utc` першою, рівно один рядок на кожен різний `t_utc`, далі колонки нижче. Читає лише view `kyiv_alerts`, бере тривоги з `available_at < t_utc`; кінець `end_utc >= t_utc` вважається невідомим (тривога відкрита). Усе в UTC, київської доби немає. Рівні тривоги в ознаки не входять (PLAN).
docs/data/silver/kyiv_alerts.md:97:- Рівні. `alert` це старий формат без рівня (340 тривог), `yellow` 200, `red` 22. Порядок `alert` < `yellow` < `red` прийнято за порядком переліку в постановці S1 (рішення будівника, не з PLAN); у ознаки gold `max_level` не входить. `max_level` не тримає порядку змін рівня, лише максимум.
docs/HANDOFF.md:31:Ще: удари по РФ переписано на dronestrikemap.com ([ADR-0004](adr/0004-rf-strikes-dronestrikemap.md)); масова перевірка сигналів (309 агентів Haiku, суддя Sonnet); прибрано мертвий код (збирач president.gov.ua, список укрВікі, невживані вирази), тимчасові symlink, кеш Jev видаленої таблиці; `PLAN.md` став `HISTORY.md`.
0
```

</details>

### Claude, 12:40

Поки що перевірено (сам, з командами):

- **Тест на витік:** 7 OK. Але він кругловий: порівнює ознаки на «зрізі до t» з ознаками на повних даних і не перевіряє, чи правильно задано сам час доступності (`available_at`). Тому кожен модуль перевіряю окремо.
- **Погода:** перерахував з bronze для всіх 3909 годин, 0 розбіжностей. Береться лише прогноз, відомий до t (випередження 9..22 год).
- **Астрономія:** 0 розбіжностей. Схід і захід сонця в Києві збігаються з реальністю до хвилини.
- **Проба на витік:** проста модель на останніх 42 днях має AUC 0.80, а лише година доби і темрява дають 0.78. Явного витоку не видно, але майже весь сигнал дає час доби.
- **Мітка, перша реальна помилка:** 3 з 77 «годин удару» лежать поза будь-якою тривогою в Києві. Їхні докази це пости про наслідки після відбою.
- **Мало подій для моделі:** 151 позитивний рядок це лише 35 атак, з них 46 рядків просто продовжують атаку, що вже йде. За останні 28 днів лише 7 атак, тож оцінка на свіжому періоді буде дуже шумною.
- **Застарілі документи (slop):** у METHODOLOGY є зайвий рядок «ча», клас «Світ», який уже прибрано, оцінки Jev для ударів по РФ, яких уже немає, і посилання на PLAN, що став HISTORY.

Зараз паралельно працюють 5 агентів, усі лише на читання: мітка удару, тривоги з ознаками загроз, сигнали підготовки, календар з політичними подіями, удари по РФ (там знімаємо другий знімок dronestrikemap у тимчасову теку). Коли вони закінчать, перевірю їхні знахідки і дам підсумок з тим, що треба вирішити тобі.

*сповіщення про фонове завдання: Agent "Audit RF strikes and launches" finished*

**Bash**: Check how intercepted and launched counts are built

```
grep -n "intercepted\|launched" src/airalerts/silver/rf_strikes.py | head -30; ls /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/rf/
```

<details><summary>результат: 39 рядків</summary>

```
5:strike_days    one row per (day, country): drones and missiles launched (min, max) and intercepted, from the site's daily totals
7:The site gives a day (UTC, checked against the MoD reports: the RU intercepted total of day d is the sum of the MoD reports
44:    DAYS: pa.schema([("date", pa.date32()), ("country", pa.string()), ("launched_min", pa.int64()), ("launched_max", pa.int64()),
45:                     ("intercepted", pa.int64()), ("estimated", pa.bool_()), ("drones_max", pa.int64()), ("drones_intercepted", pa.int64()),
46:                     ("missiles_max", pa.int64()), ("missiles_intercepted", pa.int64()), ("basis", pa.string()), ("available_at", TS)]),
95:            rows.append({"date": date.fromisoformat(d), "country": c, "launched_min": t.get("min"), "launched_max": t.get("max"),
96:                         "intercepted": t.get("intercepted"), "estimated": t.get("estimated"), "drones_max": dr.get("max"),
97:                         "drones_intercepted": dr.get("intercepted"), "missiles_max": mi.get("max"),
98:                         "missiles_intercepted": mi.get("intercepted"), "basis": t.get("basis"), "available_at": known_from(d)})
129:  COALESCE((SELECT sum(intercepted) FROM strike_days d WHERE d.country = 'RU'
130:            AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc), 0)::INTEGER AS rf_drones_intercepted_1d,
132:            AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc), 0)::INTEGER AS ua_missiles_launched_1d,
134:            AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc), 0)::INTEGER AS ua_drones_launched_1d,
138:COLS = ["rf_points_1d", "rf_points_3d", "rf_regions_3d", "rf_energy_1d", "rf_energy_3d", "rf_moscow_3d", "rf_drones_intercepted_1d",
139:        "ua_missiles_launched_1d", "ua_drones_launched_1d", "hours_since_rf_energy"]
158:    rf_drones_intercepted_1d: drones the Russian MoD said it intercepted on the newest known day; ua_missiles_launched_1d,
159:    ua_drones_launched_1d: missiles and drones launched at Ukraine on the newest known day (Air Force, max of the range);
177:            "rf_drones_intercepted_1d": sum(r["intercepted"] or 0 for r in d1 if r["country"] == "RU"),
178:            "ua_missiles_launched_1d": sum(r["missiles_max"] or 0 for r in d1 if r["country"] == "UA"),
179:            "ua_drones_launched_1d": sum(r["drones_max"] or 0 for r in d1 if r["country"] == "UA"),
204:    print("UA launched by month (missiles max, drones max):",
210:        rows = con.execute(f"""SELECT d.date, d.intercepted, (SELECT mod_drones_downed FROM read_csv('{mod}') m WHERE m.date_utc = d.date)
215:        print(f"RU intercepted of the site vs sum of the MoD Telegram reports published on the same UTC day, 2026-07-01..2026-10-09: "
fetch2.log
fetch2.py
report.md
snapshot2
step1_days.out
step1_days.py
step1b_window.out
step1b_window.py
step2_diff.out
step2_diff.py
step2b_article_dates.out
step2b_article_dates.py
```

... ще 4 рядки

</details>

**Bash**: Verify missing UA missile figures and intercepted totals

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
print(con.execute(\"SELECT count(*), count(*) FILTER (WHERE missiles_max IS NULL), count(*) FILTER (WHERE missiles_max = 0), count(*) FILTER (WHERE drones_max IS NULL), count(*) FILTER (WHERE intercepted IS DISTINCT FROM drones_intercepted) FROM strike_days WHERE country='UA' AND date >= DATE '2026-04-16'\").fetchone())
print(con.execute(\"SELECT count(*), count(*) FILTER (WHERE intercepted IS DISTINCT FROM drones_intercepted), count(*) FILTER (WHERE missiles_intercepted > 0) FROM strike_days WHERE country='RU' AND date >= DATE '2026-04-16'\").fetchone())
"; sed -n 1,200p /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/rf/step4_quality.out | head -40
```

<details><summary>результат: 37 рядків</summary>

```
(178, 55, 2, 0, 68)
(178, 10, 10)
site meta 2024-07-30..2026-10-11: 803 days of 804; missing ['2025-05-09']
silver range 2026-04-16..2026-10-10 = 178 days; strike_days rows 356; days without any RU (non-occupied) point: ['2026-04-27', '2026-05-06', '2026-05-10', '2026-05-11', '2026-05-16', '2026-06-04', '2026-06-07']

nulls per column, strike_days by country:
  RU (178 days): drones_max 12, missiles_max 139, missiles_intercepted 168
  UA (178 days): missiles_max 55, missiles_intercepted 62
  UA missiles_max: null 55, explicit 0 2, >0 121 (null becomes 0 in gold)
  UA estimated=true days: 0; RU estimated=true: 0
nulls per column, strike_points: 
strike_points empty summary 1, empty weapons 924

outliers (daily series 04-16..10-10, 3*IQR rule):
  RU points/day: median 7.0, q1 3.0, q3 12.0, >q3+3IQR 0 [], <q1-3IQR 0
  RU intercepted/day: median 440.5, q1 265.0, q3 605.75, >q3+3IQR 0 [], <q1-3IQR 0
  UA drones_max/day: median 214.0, q1 169.0, q3 284.5, >q3+3IQR 9 [('2026-05-13', 892), ('2026-09-13', 807), ('2026-05-14', 739), ('2026-04-16', 733)], <q1-3IQR 0
  UA missiles_max/day: median 2.0, q1 0.0, q3 7.25, >q3+3IQR 18 [('2026-05-24', 90), ('2026-07-30', 78), ('2026-09-13', 78), ('2026-10-08', 75)], <q1-3IQR 0
  rows with launched_max < launched_min: []
  rows with launched_max > 1.5 x launched_min: 13 [('2026-04-18', 'RU', 304, 568), ('2026-07-11', 'RU', 221, 447), ('2026-07-19', 'RU', 303, 680), ('2026-07-21', 'RU', 209, 400)]

regions filed under RU without '(occupied)' that are Ukrainian (Crimea etc):
  {'Black Sea, off Yalta, occupied Crimea': 1}
  regions containing 'Moscow': {'Moscow': 106, 'Moscow Oblast': 122}
  RU non-occupied points with empty region: 0
  RU confidence: {'confirmed': 748, 'reported': 598, 'claimed': 7}
  duplicate (date,country,place,region): 0 []
  days with a Moscow point: 109/178; Moscow summaries sample: ['European drone facilities hit by Russian strikes o', 'Moscow luxury tower hit by Ukraine drone strike wi', 'Moscow airports hit by drone threat overnight', 'Moscow hit by mass drone attack with fires and dis']

MoD cross-check (data/verification/mod_russia_daily_drones.csv) vs RU intercepted, shift k = site day - MoD day:
  intercepted k=-1: days 101, equal 0, within 10% 13
  intercepted k=+0: days 101, equal 72, within 10% 85
  intercepted k=+1: days 101, equal 0, within 10% 13
  drones_intercepted k=-1: days 101, equal 0, within 10% 13
  drones_intercepted k=+0: days 101, equal 78, within 10% 85
  drones_intercepted k=+1: days 101, equal 0, within 10% 13
  MoD csv range 2026-04-17..2026-10-10 (174 days)
```

</details>

**Bash**: Log piece 5 result in the plan

```
cat >> /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/PLAN.md <<'EOF'
- piece 5 rf: pass, no leak, 10 cols 0 mismatches. Confirmed by me: UA missiles_max null 55/178 days -> 0 in gold; rf_drones_intercepted_1d uses total intercepted (drones + missiles, differs on 10 RU days). Site day for UA = Air Force day 15Z..15Z (doc says UTC; safe side).
EOF
```

<details><summary>результат: 1 рядок</summary>

```
(Bash completed with no output)
```

</details>

### Claude, 12:45

Агент ударів по РФ закінчив: витоку немає, 10 колонок збігаються в усіх рядках. Дві його знахідки я підтвердив сам: у 55 з 178 днів кількість ракет по Україні невідома і в gold стає 0, а `rf_drones_intercepted_1d` насправді рахує дрони разом з ракетами. Чекаю ще 4 агентів.

*сповіщення про фонове завдання: Agent "Audit preparation signals" finished*

### Claude, 12:46

Агент сигналів знайшов витік, перевіряю його сам. Він каже, що (1) відредаговані пости дають події S1 з текстом, написаним через години після публікації, і (2) Jev оцінював дрони (S4) пачками по 8 постів, куди потрапляли й пізніші пости.

**Bash**: Verify the edited S1 post and the S4 batching

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
for ch, pid in [('AerisRimor',84052),('AerisRimor',67431),('StrategicaviationT',30077)]:
    print(con.execute(f\"SELECT published_at, edited, replace(left(text,400), chr(10), ' | ') FROM tg_posts WHERE channel='{ch}' AND post_id={pid}\").fetchall())
print(con.execute(\"SELECT event_id, signal, subtype, first_post_at, available_at, post_refs FROM prep_signal_events WHERE event_id='S1-takeoff-20260907T174502Z'\").fetchall())
"; grep -n "def chunks_of\|BATCH\|batch\|def scrub\|MAX_CHARS\|3000" src/airalerts/silver/signals.py | head -30
```

<details><summary>результат: 8 рядків</summary>

```
[(datetime.datetime(2026, 9, 7, 17, 45, 2), True, '🎩Зведення станом на 02:25. |  | ❗️✈✈СА/ДА. Відбувся виліт ударної групи СА з далекого сходу курсом на північні пускові. 2 борти Ту-160 виявлено в 1:20. На пускових будуть в 3:00. Відбувся виліт 4 бортів СА Ту-95МС в проміжку 1:40-2:20. На північних пускових мають бути також ~ в 3:00. |  | ⚓️Флот. Без ракетоносіїв в АЧМ та АКМ. Очікуваним є застосування з 2 надводних ракетоносіїв з Новоросійська та 1 надво')]
[(datetime.datetime(2026, 4, 24, 19, 6, 43), True, '🎩Зведення станом на 23:23. |  | ❗️✈✈СА/ДА. Зафіксовано активність телекодової апаратури на кількох частотах. Бойова активність. Відбулись вильоти бортів СА з, щонайменше, Оленья. В повітрі 4+ борти Ту-95МС. |  | ❗️Підліт до пускових зон бортами СА з Оленья: |  | Вологодська зона (північний напрямок)  ~0:00 | Саратовська зона 1:30 | Волгоград-Волгодонськ 2:00 | Каспійська зона 3:00-4:00. |  | Відповідно таймінгу вильоту')]
[(datetime.datetime(2026, 4, 24, 19, 21, 47), True, '⚠️ За уточненням в повітрі мінімум 2х борти Ту-95мс з аеродрому «Оленья», курс південний. |  | Орієнтовно район Енгельса- 02:30. |  | ❌ Ту-22м3 в повітрі відсутні, сплутані з Ту-95мс.')]
[('S1-takeoff-20260907T174502Z', 'S1', 'takeoff', datetime.datetime(2026, 9, 7, 17, 45, 2), datetime.datetime(2026, 9, 7, 17, 45, 2), ['AerisRimor/84052', 'AerisRimor/84053', 'StrategicaviationT/39958'])]
40:MAX_POSTS, MAX_CHARS, MAX_TEXT = 8, 3000, 3500   # S4 requests: posts and characters of text; characters per post
114:def scrub(text):
142:    """Posts per request: S1 and S2 posts (rare, decisive, often long) go one per request, S4 posts in batches."""
148:def chunks_of(posts, max_posts=None, max_chars=MAX_CHARS):
```

</details>

*сповіщення про фонове завдання: Agent "Audit strike label quality" finished*

**Bash**: Show non-live strike hour verdicts and effect

```
D=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/label; head -1 $D/strike_hours.csv; grep -v ",live," $D/strike_hours.csv | cut -c1-400; cat $D/effect_out.txt | head -30
```

<details><summary>результат: 27 рядків</summary>

```
hour_utc,episode,pos_in_episode,episode_len,verdict,reason,evidence_ids,corrected,in_alert
hour_utc,episode,pos_in_episode,episode_len,verdict,reason,evidence_ids,corrected,in_alert
2026-05-14T01,1,2,3,aftermath,"only damage reports (vitaliy_klitschko/6602 01:09 ""уламки впали на ... паркінгу""); missile radar clear: kyiv_airdef/35654 01:02 ""Київ надалі чисто"", war_monitor/39791 ""Київ зараз без КР""; rest of hour is drones",vitaliy_klitschko/6602|truexakyiv/75673|vitaliy_klitschko/6605|war_monitor/39798,False,True
2026-06-02T01,3,3,5,unclear,"hour-boundary: impact at 00:59 (truexakyiv/77342) echoed by AerisRimor/71527 01:00 ""Влупило, попередньо"", same minute truexakyiv/77343 ""по ракетах чисто""; later only reports and a jet Shahed (01:09)",AerisRimor/71527|vitaliy_klitschko/6826|truexakyiv/77344|vitaliy_klitschko/6828|truexakyiv/77349|vitaliy_klitschko/6829|truexakyiv/77356
2026-06-02T05,3,5,5,aftermath,"14-47 min after alert end: truexakyiv/77414 ""Наслідки прильоту по ЖК Медовий"", truexakyiv/77421 overnight recap ""Збито/подавлено 642 цілі""",truexakyiv/77412|truexakyiv/77414|truexakyiv/77421,False,False
2026-07-02T01,8,4,4,aftermath,"war_monitor/41134 01:11 recap ""На Київ нарахував 17 балістик, що долетіли""; rest are damage reports; kyiv_nebo/24455 01:34 ""Київ наразі чисто""; the 01:20 Zircon threat brought no explosion",truexakyiv/79326|war_monitor/41134|vitaliy_klitschko/7008|truexakyiv/79330|vitaliy_klitschko/7009|truexakyiv/79337,False,True
2026-07-06T01,9,4,4,aftermath,"kyiv_airdef/41456 01:09 ""Очікуємо на загальний відбій""; evidence are photo reports of earlier hits (truexakyiv/79720 ""Влучання ракети на дитячий майданчик"", 79721 ""Наслідки удару"")",truexakyiv/79717|truexakyiv/79718|truexakyiv/79719|truexakyiv/79720|truexakyiv/79721|truexakyiv/79722,False,Tru
2026-07-11T01,11,2,2,aftermath,"kyiv_airdef/41864 01:20 ""Очікуємо на відбій""; only damage reports (truexakyiv/80158 ""Вирва посеред дороги після атаки"")",truexakyiv/80158|truexakyiv/80159|truexakyiv/80160|vitaliy_klitschko/7083|vitaliy_klitschko/7084|vitaliy_klitschko/7086,False,True
2026-07-19T00,14,3,3,aftermath,"only fire/damage reports, alert ended 00:14: vitaliy_klitschko/7127 00:20 ""продовжують ліквідовувати наслідки ворожої атаки""",vitaliy_klitschko/7124|truexakyiv/80597|vitaliy_klitschko/7126|truexakyiv/80599|truexakyiv/80601|vitaliy_klitschko/7127|vitaliy_klitschko/7128|vitaliy_klitschko/7130,False,True
2026-07-30T00,17,2,2,unclear,"single post truexakyiv/81184 00:59 ""Вибухи у Києві."" (p_drone 0.61) with kyiv_airdef/43293 00:59 ""Мінус""; hour has no missile_threat or ballistic flag and no weapon named",truexakyiv/81184,False,True
2026-08-08T01,20,2,2,aftermath,"26 min after alert end, past tense video: truexakyiv/81869 01:02 ""Вибух за вибухом лунали у місті.""",truexakyiv/81869,False,False
2026-08-16T00,22,2,2,aftermath,"at/after alert end 00:23: vitaliy_klitschko/7229 00:42 ""внаслідок атаки ворога, сталося падіння уламків та
```

... ще 15 рядків

</details>

*сповіщення про фонове завдання: Agent "Audit alerts and threat features" finished*

**Bash**: Read posts around two disputed strike hours

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
for a, b in [('2026-07-18 23:30','2026-07-19 01:00'), ('2026-10-07 00:40','2026-10-07 02:00')]:
    print('=====', a, b, 'alerts:', con.execute(f\"SELECT start_utc, end_utc FROM kyiv_alerts WHERE end_utc > TIMESTAMP '{a}' - INTERVAL 2 HOUR AND start_utc < TIMESTAMP '{b}'\").fetchall())
    for r in con.execute(f\"SELECT strftime(t.published_at, '%H:%M'), t.channel, round(k.p_strike,2), round(k.p_threat,2), round(k.p_drone,2), replace(left(t.text,130), chr(10),' ') FROM kyiv_threat_posts k JOIN tg_posts t USING (channel, post_id) WHERE t.published_at BETWEEN TIMESTAMP '{a}' AND TIMESTAMP '{b}' AND (k.p_strike>=0.3 OR k.p_threat>=0.8) ORDER BY t.published_at\").fetchall(): print(r)
"
```

<details><summary>результат: 46 рядків</summary>

```
===== 2026-07-18 23:30 2026-07-19 01:00 alerts: [(datetime.datetime(2026, 7, 18, 22, 21, 20), datetime.datetime(2026, 7, 19, 0, 14, 29))]
('23:32', 'AerisRimor', 0.07, 0.85, 0.07, 'Залишаємось в укриттях. Ворог ще має спроможності щодо БР/ГКР, та має накопичені КР наземного базування. Очікуємо сьогодні довго.')
('23:36', 'war_monitor', 0.14, 0.88, 0.06, '‼️ Київ / Область — спуск балістики! 28+29')
('23:36', 'AerisRimor', 0.17, 0.94, 0.12, 'КИЇВ ЦІЛІ!')
('23:36', 'AerisRimor', 0.17, 0.88, 0.13, 'На Трою!!')
('23:36', 'kyiv_airdef', 0.1, 0.82, 0.09, 'УВАГА')
('23:36', 'VA_Kyiv', 0.11, 0.96, 0.05, '🚀Нові балістичні ракети на Київ з Брянська!')
('23:36', 'AerisRimor', 0.09, 0.85, 0.07, 'Йдуть одна за одною.')
('23:36', 'kyiv_airdef', 0.18, 0.81, 0.1, 'ОБОЛОНЬ!!!!!')
('23:37', 'kyiv_airdef', 0.12, 0.81, 0.08, 'ТРИ ЦІЛІ')
('23:37', 'truexakyiv', 0.1, 0.93, 0.08, 'Ціль на Київ. ㅤ Труха⚡️Київ | Надіслати новину')
('23:37', 'AerisRimor', 0.55, 0.76, 0.16, 'Перша залітає почайна!')
('23:37', 'kyiv_nebo', 0.78, 0.45, 0.29, 'Падають на Правий берег')
('23:38', 'kyiv_airdef', 0.35, 0.11, 0.08, 'мінус')
('23:38', 'AerisRimor', 0.31, 0.17, 0.12, 'Поки всі дійшли.  4 штуки. Видно було адекватно тільки 3.')
('23:39', 'war_monitor', 0.09, 0.82, 0.05, 'Знову чисто. Загроза балістики триває!')
('23:40', 'truexakyiv', 0.11, 0.96, 0.06, 'Балістика на Київ. ㅤ Труха⚡️Київ | Надіслати новину')
('23:41', 'war_monitor', 0.08, 0.94, 0.17, '☄ Вихід у напрямку Києва')
('23:41', 'kyiv_airdef', 0.07, 0.87, 0.11, 'ЗАХОВАЛИСЬ БУДЬ ЛАСКА!!!!!!!')
('23:41', 'AerisRimor', 0.08, 0.83, 0.13, 'Фіксація неоптимальна. Вилізе перед Києвом.')
('23:41', 'kyiv_nebo', 0.09, 0.81, 0.14, 'Ще летять')
('23:55', 'vitaliy_klitschko', 0.33, 0.05, 0.06, 'Медики госпіталізували одну постраждалу внаслідок атаки ворога на столицю.')
('23:56', 'truexakyiv', 0.44, 0.06, 0.06, 'Медики госпіталізували одну постраждалу внаслідок атаки ворога на столицю, – Кличко. ㅤ Труха⚡️Київ | Надіслати новину')
('23:56', 'vitaliy_klitschko', 0.86, 0.05, 0.11, 'У Соломʼянському районі уламки впали поруч із 9-поверхівкою. У будинку повибивало вікна. З другого поверху врятували одну людину.')
('23:57', 'truexakyiv', 0.83, 0.06, 0.1, 'У Соломʼянському районі уламки впали поруч із 9-поверхівкою, – Кличко.  У будинку повибивало вікна. З другого поверху врятували од')
('00:00', 'vitaliy_klitschko', 0.63, 0.07, 0.22, 'У Соломʼянському районі загоряння на даху будівлі супермаркету. А також — в житловому будинку поруч.')
('00:01', 'truexakyiv', 0.58, 0.06, 0.14, 'У Соломʼянському районі загоряння на даху будівлі супермаркету, – Кличко.  А також – в житловому будинку поруч. ㅤ Труха⚡️Київ | На')
('00:03', 'vitaliy_klitschko', 0.85, 0.06, 0.19, 'У Дніпровському районі, внаслідок падіння уламків, загоряння в гуртожитку.')
('00:04', 'truexakyiv', 0.61, 0.06, 0.15, "Палає житловий будинок в Солом'янському районі. ㅤ Труха⚡️Київ | Надіслати новину")
('00:06', 'truexakyiv', 0.76, 0.05, 0.11, 'У Дніпровському районі, внаслідок падіння
```

... ще 16 рядків

</details>

**Bash**: Log pieces 1, 2 and 3 results in the plan

```
cat >> /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/PLAN.md <<'EOF'
- piece 3 signals: FAIL. Confirmed by me: AerisRimor/84052 published 17:45Z, edited text "станом на 02:25" (23:25Z) -> S1 event 5.5 h early before the 09-08 attack. 4 such S1 events (lower bound): 12 rows s1_takeoff_6h, 48 s1_takeoff_24h, 20 hours_since_s1. S4 Jev batches of 8 include later posts: 50 events depend on batch. 5 gold cols 0 mismatches.
- piece 1 label: FAIL. 60 live, 14 aftermath, 1 drone_only, 2 unclear of 77. Strict: 16 positives flip (151 -> 135). Confirmed by me on 5 of 14 (06-02T05, 08-08T01, 09-17T00, 07-19T00, 10-07T01). Code checks a-c pass (state window, cache keys, CORRECTIONS in hour).
- piece 2 history: pass. 21 cols 0 mismatches; 561 alerts rebuilt from VA_Kyiv match silver to the second; ASOF 0 violations. Alert 391 1057 min likely merged (VA missed all clear). Edited deciding posts in ~71% threat hours, 12.1% flags depend on edited posts; truexakyiv UPD HH:MM later news.
EOF
```

<details><summary>результат: 1 рядок</summary>

```
(Bash completed with no output)
```

</details>

**Bash**: Read the edited S1 posts output

```
D=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/signals; ls $D; head -60 $D/s7_out.txt
```

<details><summary>результат: 20 рядків</summary>

```
s2_first_post.py
s2_out.txt
s3_out.txt
s3_recompute.py
s4_data_end.py
s4_out.txt
s5_context_edits.py
s5_out.txt
s6_edit_examples.py
s6_out.txt
s7_out.txt
s7_stated_time.py
first posts with a 'станом на HH:MM' time (signal, edited): n -> {('S1', False): 11, ('S1', True): 3, ('S4', False): 30, ('S4', True): 12}
of them the stated Kyiv time is 5 min..12 h AFTER publication (text written after available_at) (signal, edited): {('S1', False): 1, ('S1', True): 3, ('S4', False): 1}
  S1-takeoff-20260424T190643Z ch=3 edited=True pub_kyiv=22:06 text says 'станом на 23:23' (+77 min): '🎩Зведення станом на 23:23.\n\n❗️✈✈СА/ДА. Зафіксовано активність телекодової апаратури на кількох частотах. Бойов'
  [REDACTED: ключ] ch=1 edited=False pub_kyiv=21:19 text says 'станом на 00:25' (+186 min): 'Aeris Rimor pinned «🎩Зведення станом на 00:25.  ❗️✈✈СА/ДА. Зафіксовано функціонування телекодової апаратури на'
  S1-relocation-20260618T212018Z ch=1 edited=True pub_kyiv=00:20 text says 'Станом на 3:50' (+210 min): '⚠️ 2х борти Ту-95мс з аеродрому «Українка», ймовірно здійснюють передислокацію на аеродром «Енгельс-2», слідку'
  S1-takeoff-20260907T174502Z ch=2 edited=True pub_kyiv=20:45 text says 'станом на 02:25' (+340 min): '🎩Зведення станом на 02:25.\n\n❗️✈✈СА/ДА. Відбувся виліт ударної групи СА з далекого сходу курсом на північні пус'
  S4-launch-20260926T041717Z ch=2 edited=False pub_kyiv=07:17 text says 'станом на 07:30' (+13 min): '⚡️ ЗБИТО/ПОДАВЛЕНО 134 ВОРОЖІ БПЛА\n➖➖➖➖➖➖➖➖➖➖\nУ ніч на 26 вересня (з 18:00 25 вересня) противник атакував 173 '
affected events 5; dropped (no other post) 2; gold rows that change: {'s1_takeoff_6h': 12, 's1_takeoff_24h': 48, 'hours_since_s1': 20, 's4_drone_waves_6h': 0}
```

</details>

**Bash**: Find label channel posts whose text was written after their hour

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
import re
con = register_layers(connect())
rows = con.execute(\"\"\"SELECT t.channel, t.post_id, t.published_at, t.edited, k.p_threat, k.p_ballistic, k.p_strike, k.p_drone, t.text
FROM kyiv_threat_posts k JOIN tg_posts t USING (channel, post_id) WHERE t.published_at >= TIMESTAMP '2026-04-30 21:00'\"\"\").fetchall()
late = []
for ch, pid, pub, ed, pt, pb, ps, pd, text in rows:
    m = re.search(r'(?:станом на|UPD|Upd|upd|Оновлено)\s*(\d{1,2})[:.](\d{2})', text or '')
    if not m: continue
    hh, mm = int(m.group(1)), int(m.group(2))
    if hh > 23 or mm > 59: continue
    from datetime import timedelta
    kyiv = pub + timedelta(hours=3)
    stated = kyiv.replace(hour=hh, minute=mm, second=0)
    if stated < kyiv - timedelta(hours=12): stated += timedelta(days=1)
    lag = (stated - kyiv).total_seconds()/60
    # post's hour ends at floor(pub)+1h: text from after that instant is a leak for features
    end_kyiv = kyiv.replace(minute=0, second=0) + timedelta(hours=1)
    if stated > end_kyiv and lag < 12*60:
        late.append((ch, pid, pub, ed, round(lag), pt, pb, ps, pd))
print('posts in label channels whose text states a time after the end of their hour:', len(late))
from collections import Counter
print(Counter(r[0] for r in late))
hi = [r for r in late if max(r[5], r[6], r[7]) >= 0.8 or r[8] >= 0.8]
print('of them with p_threat/p_ballistic/p_strike/p_drone >= 0.8:', len(hi))
for r in hi[:12]:
... ще 7 символів
```

<details><summary>результат: 15 рядків</summary>

```
posts in label channels whose text states a time after the end of their hour: 145
Counter({'truexakyiv': 141, 'AerisRimor': 4})
of them with p_threat/p_ballistic/p_strike/p_drone >= 0.8: 20
('truexakyiv', 75493, datetime.datetime(2026, 5, 13, 2, 50, 7), True, 11, 0.8, 0.54, 0.03, 0.03)
('AerisRimor', 69212, datetime.datetime(2026, 5, 13, 17, 15, 36), True, 249, 0.85, 0.28, 0.04, 0.17)
('truexakyiv', 76005, datetime.datetime(2026, 5, 16, 7, 48, 7), True, 19, 0.85, 0.75, 0.05, 0.09)
('truexakyiv', 76169, datetime.datetime(2026, 5, 19, 6, 56, 32), True, 30, 0.89, 0.72, 0.04, 0.04)
('truexakyiv', 77137, datetime.datetime(2026, 5, 30, 14, 57, 24), True, 24, 0.85, 0.62, 0.04, 0.06)
('truexakyiv', 77155, datetime.datetime(2026, 5, 30, 21, 54, 5), True, 23, 0.85, 0.67, 0.04, 0.05)
('truexakyiv', 77366, datetime.datetime(2026, 6, 2, 2, 59), True, 4, 0.07, 0.05, 0.06, 0.86)
('truexakyiv', 78225, datetime.datetime(2026, 6, 15, 1, 43, 27), True, 40, 0.05, 0.06, 0.06, 0.94)
('truexakyiv', 78240, datetime.datetime(2026, 6, 15, 3, 33, 9), True, 42, 0.12, 0.05, 0.09, 0.82)
('truexakyiv', 78862, datetime.datetime(2026, 6, 25, 21, 51, 8), True, 63, 0.82, 0.63, 0.06, 0.06)
('truexakyiv', 78865, datetime.datetime(2026, 6, 25, 23, 54, 5), True, 20, 0.87, 0.79, 0.04, 0.06)
('truexakyiv', 80526, datetime.datetime(2026, 7, 17, 22, 36, 20), True, 30, 0.91, 0.78, 0.07, 0.04)
```

</details>

**Bash**: Check whether one edited post sets a threat flag

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
print(con.execute(\"SELECT hour_utc, missile_threat, ballistic, drone_threat, missile_strike FROM kyiv_threat_hourly WHERE hour_utc = TIMESTAMP '2026-05-13 17:00'\").fetchall())
print(con.execute(\"SELECT channel, post_id, strftime(published_at,'%H:%M'), round(p_threat,2) FROM kyiv_threat_posts WHERE hour_utc = TIMESTAMP '2026-05-13 17:00' AND p_threat >= 0.5\").fetchall())
print(con.execute(\"SELECT replace(left(text,300),chr(10),' | ') FROM tg_posts WHERE channel='AerisRimor' AND post_id=69212\").fetchall())
"
```

<details><summary>результат: 3 рядки</summary>

```
[(datetime.datetime(2026, 5, 13, 17, 0), True, False, False, False)]
[('kyiv_nebo', 23210, '17:02', 0.9), ('truexakyiv', 75604, '17:02', 0.89), ('war_monitor', 39686, '17:05', 0.75), ('AerisRimor', 69212, '17:15', 0.85), ('VA_Kyiv', 18025, '17:23', 0.66), ('kyiv_nebo', 23212, '17:23', 0.6), ('AerisRimor', 69213, '17:23', 0.56), ('war_monitor', 39687, '17:23', 0.54), ('truexakyiv', 75609, '17:23', 0.6), ('AerisRimor', 69214, '17:25', 0.62), ('kyiv_nebo', 23213, '17:25', 0.63), ('truexakyiv', 75610, '17:25', 0.77), ('kyiv_airdef', 35192, '17:25', 0.73), ('VA_Kyiv', 18026, '17:25', 0.89), ('kyiv_nebo', 23214, '17:30', 0.56)]
[('🎩Зведення станом на 00:25. |  | ❗️✈✈СА/ДА. Зафіксовано функціонування телекодової апаратури на кількох частотах. В повітрі 4 борти Ту-95МС з Оленья та 2 борти Ту-160 з Українки. |  | Підліт групи бортів Ту-95МС з Оленья до пускових зон: | Північна пускова зона: ~1:40. | Саратовська зона: ~2:40. | Волгоград-Волгод',)]
```

</details>

*сповіщення про фонове завдання: Agent "Audit calendar and political events" finished*

**Bash**: Read the Wikipedia event set and abroad-twin code

```
sed -n 520,550p src/airalerts/silver/political_events.py; echo ...; sed -n 1040,1065p src/airalerts/silver/political_events.py
```

<details><summary>результат: 58 рядків</summary>

```
    for x in d["revisions"] + d["snapshots"]:
        add(x["response"])
    return [(ts, rid, c) for rid, (ts, c) in sorted(revs.items(), key=lambda kv: (kv[1][0], kv[0]))]


def _wiki_row(info):
    """What a revision says about one event: the fields of the candidate. A change in any of them starts a new version."""
    return (info["title"], info["text"], info["country"], info["event_date"], info["end_date"])


def wiki_events(path, parse):
    """Versions of the events that the newest revision lists (the set of keys is that of the newest revision). A key has one version for
    each distinct row (title, text, country, dates) in the revisions where it appears: a new version starts in the revision where the row
    differs from the previous version of the key (a key that is missing from some revisions and returns unchanged keeps its version).
    announced_at and url are those of the revision where the version starts (the base revision before 2026-04-01 for a row that was
    already there), so a version knows nothing that was added to the page later. latest marks the version of the newest revision."""
    versions, last = {}, {}
    for ts, rid, text in wiki_revisions(path):
        last = parse(text)
        for k, info in last.items():
            vs = versions.setdefault(k, [])
            if not vs or _wiki_row(vs[-1]) != _wiki_row(info):
                vs.append(dict(info, key=k, revid=rid, announced_at=utc(ts), url=f"https://en.wikipedia.org/w/index.php?oldid={rid}"))
    return [dict(v, latest=i == len(versions[k]) - 1) for k in last for i, v in enumerate(versions[k])]


def _infobox(text, typ, title, text2, parts):
    m = re.search(r"^\|\s*date\s*=\s*(.+)$", text, re.M)
    dd = parse_dates(clean(m[1]), 2026) if m else None
    if not dd:
        return {}
...
        chunk = todo[i:i + 120]
        for (key, _), ans in zip(chunk, ask_many([(st, qs) for _, st in chunk], tag=TABLE, workers=WORKERS)):
            got[key] = ans
        print(f"jev {len(got)}/{len(todo)} distinct states, questions {sorted(qs)[:2]}.. ({len(qs)})", flush=True)
    return [got[k] for k in keys]


def mark_abroad_twins(scored):
```

... ще 18 рядків

</details>

**Write**: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/SUMMARY.md

```
файл: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/SUMMARY.md, 3319 символів
# Audit summary, 2026-10-11 (read-only, repo untouched)

Evidence per piece in audit/<piece>/ (scripts + .out). "Confirmed" = orchestrator reran or read it.

## Correct (recomputed independently, all 3909 gold rows, 0 mismatches)
- alerts (9 cols), threat (10), hour/dow: 561 alerts rebuilt from VA_Kyiv match silver to the second; ASOF 0 violations; 18 synthetic edge cases ok.
- signals (5 cols), weather (4, from bronze CSV), astro (2), calendar + political (8), rf (10, incl. t == available_at).
- rf 30 h lag: 0 gold hours see launches of an attack still in [t, t+3h); gold sees an attack 19-38 h after its last strike hour.
- Jev label code: state of hour h only posts of [h-1h, h+1h); 5095 requests -> 5095 distinct cache keys; p_strike = cached answer for 98453 posts.
- Probe: time-split logistic AUC 0.80 (hour + dark alone 0.78). No blatant leak.

## Problems
1. LABEL (confirmed 5 of 14): 17 of 77 strike hours are not live strikes: 14 aftermath (damage reports, recaps after the missiles), 1 drone_only (08-27T01), 2 unclear (06-02T01, 07-30T00). Cause: Jev gives damage reports p_strike 0.7-0.9 and the fresh gate looks back 90 min to the attack alarms. Strict fix: 16 positive rows flip, 151 -> 135. Hand lists READ_TRUE (10-07T01, 06-02T01) and doc kyiv_threat_hourly.md l.34 call some of these strikes.
2. LEAK, edited posts in S1 (confirmed AerisRimor/84052): 4 S1 events whose first post text was written 77-340 min after publication (AerisRimor "Зведення станом на HH:MM" is a
... ще 1819 символів
```

<details><summary>результат: 1 рядок</summary>

```
File created successfully at: /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/SUMMARY.md (file state is current in your context — no need to Read it back)
```

</details>

### Claude, 12:48

Агрегація в gold правильна, а от мітка і сигнали мають реальні проблеми. Усі 50 ознак я перерахував незалежно на всіх 3909 годинах, розбіжностей 0. Але 17 з 77 «годин удару» хибні, і знайшовся один реальний витік через відредаговані пости.

**Що правильно (перевірено перерахунком, не за документами)**
- Тривоги: 561 тривогу я заново зібрав з постів КМВА, вони збігаються з silver до секунди.
- Колонки тривог, загроз, сигналів, погоди, астрономії, дат, політики та ударів по РФ збігаються з gold.
- Удари по РФ: затримка 30 год безпечна. Gold бачить атаку щонайменше через 19 год після її останньої години удару.
- Проба на витік: проста модель на останніх 42 днях дає AUC 0.80. Лише година доби і темрява дають 0.78, тож явного витоку немає.

**Проблеми**
1. **Мітка.** 14 годин це звіти про наслідки після ракет: «уламки впали», «пожежа», підсумок ПС. Ще 1 година це лише дрони, 2 неясні. Я сам прочитав пости 5 з цих годин, вердикт підтверджую. Якщо їх прибрати, 16 позитивних рядків стають негативними (151 → 135). Причина: Jev оцінює звіти про наслідки як удар, а правило години бачить тривожні пости за 90 хв до того.
2. **Витік через відредаговані пости (сигнали S1).** Пост AerisRimor опубліковано о 20:45 за Києвом. Пізніше його переписано на «Зведення станом на 02:25» зі зльотами Ту-95 і Ту-160. Таких подій щонайменше 4, вони змінюють 12..48 рядків ознак S1 перед атаками.
3. **Малі витоки.** 50 з 8821 подій дронів (S4) залежать від пізніших постів у запиті до Jev. Події Вікіпедії відбираються за найновішою ревізією. На gold це майже не впливає.
4. **Удари по РФ.** У 55 з 178 днів кількість ракет по Україні невідома, але в gold стоїть 0. Колонка `rf_drones_intercepted_1d` рахує дрони разом з ракетами.
5. **Документи (slop).** Невірні твердження в METHODOLOGY, rf_strikes.md, kyiv_threat_hourly.md і VERIFICATION.md. Зокрема VERIFICATION пише «мітка тут права», хоча години всередині ночі ніхто не перевіряв.

**Для моделювання**
- 151 позитивний рядок це лише 35 атак, з них 46 рядків просто продовжують атаку, що вже йде.
- За останні 28 днів лише 7 атак, тож оцінка на свіжому періоді буде дуже шумною.
- Онсет (першу годину атаки, коли до t удару ще не було) варто оцінювати окремо.

У репозиторії я нічого не змінював. Повне зведення і скрипти лежать у scratchpad: `audit/SUMMARY.md`.

**AskUserQuestion**

```
{
 "questions": [
  {
   "question": "Як виправити 15 хибних годин удару (14 звітів про наслідки і 1 дрон)?",
   "header": "Мітка",
   "multiSelect": false,
   "options": [
    {
     "label": "CORRECTIONS (Recommended)",
     "description": "Додати 15 годин у список ручних виправлень з доказами, 2 неясні лишити. Швидко і прозоро; позитивів стане ~137."
    },
    {
     "label": "Змінити правило",
     "description": "Переробити правило години (вікно 90 хв, звіти про наслідки). Системніше, але треба наново перевіряти всі 77 годин, ризик нових помилок перед дедлайном."
    },
    {
     "label": "Лишити і описати",
     "description": "Не чіпати дані, лише чесно записати в VERIFICATION.md."
    }
   ]
  },
  {
   "question": "Що робити з відредагованими постами в сигналах S1 (витік)?",
   "header": "Сигнали",
   "multiSelect": false,
   "options": [
    {
     "label": "Прибрати 4-5 подій (Recommended)",
     "description": "Прибрати події, чий перший пост містить час, пізніший за
... ще 1255 символів
```

<details><summary>результат: 1 рядок</summary>

```
Your questions have been answered: "Як виправити 15 хибних годин удару (14 звітів про наслідки і 1 дрон)?"="CORRECTIONS (Recommended)", "Що робити з відредагованими постами в сигналах S1 (витік)?"="Прибрати 4-5 подій (Recommended)", "Дрібні виправлення ударів по РФ: невідомі ракети як NULL замість 0 і перехоплені лише дрони?"="Виправити (Recommended)", "Почистити документи від невірних тверджень і записати результати аудиту у VERIFICATION.md?"="Так (Recommended)". You can now continue with these answers in mind.
```

</details>

**Bash**: Read posts of the remaining 10 disputed strike hours

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
H = ['2026-05-14 01:00','2026-07-02 01:00','2026-07-06 01:00','2026-07-11 01:00','2026-08-16 00:00','2026-08-19 23:00','2026-08-27 01:00','2026-09-01 00:00','2026-09-23 23:00','2026-09-28 23:00']
for h in H:
    al = con.execute(f\"SELECT strftime(start_utc,'%H:%M'), strftime(end_utc,'%H:%M') FROM kyiv_alerts WHERE end_utc > TIMESTAMP '{h}' - INTERVAL 2 HOUR AND start_utc < TIMESTAMP '{h}' + INTERVAL 1 HOUR\").fetchall()
    print('=====', h, 'alerts', al)
    for r in con.execute(f\"SELECT strftime(t.published_at, '%H:%M'), t.channel, round(k.p_strike,2) ps, round(k.p_threat,2) pt, replace(left(t.text,110), chr(10),' ') FROM kyiv_threat_posts k JOIN tg_posts t USING (channel, post_id) WHERE t.published_at >= TIMESTAMP '{h}' - INTERVAL 25 MINUTE AND t.published_at < TIMESTAMP '{h}' + INTERVAL 1 HOUR AND (k.p_strike>=0.5 OR k.p_threat>=0.8 OR t.text ILIKE '%чисто%' OR t.text ILIKE '%відбій%') ORDER BY t.published_at LIMIT 22\").fetchall(): print('  ', r)
" 2>&1 | cut -c1-200
```

<details><summary>результат: 187 рядків</summary>

```
===== 2026-05-14 01:00 alerts [('21:50', '05:43')]
   ('00:35', 'AerisRimor', 0.62, 0.21, 'Втрачена.')
   ('00:35', 'kyiv_nebo', 0.09, 0.81, 'Балістика ще може бути')
   ('00:36', 'truexakyiv', 0.71, 0.09, 'В Оболонському районі також фіксуємо наслідки атаки, – КОВА.  Є пошкодження нежитлової 
   ('00:36', 'VA_Kyiv', 0.74, 0.06, 'В Оболонському районі також фіксуємо наслідки атаки. Є пошкодження нежитлової будівлі, і
   ('00:37', 'kyiv_airdef', 0.08, 0.13, 'Над Києвом локаційно чисто')
   ('00:39', 'vitaliy_klitschko', 0.9, 0.46, 'На Оболоні падіння уламків ракети на нежитлове приміщення.   У Соломʼянському район�
   ('00:40', 'kyiv_nebo', 0.09, 0.92, 'Балістика на Київ')
   ('00:40', 'truexakyiv', 0.75, 0.13, 'Звуки вибухів які лунають в столиці. ㅤ Труха⚡️Київ | Надіслати новину')
   ('00:41', 'truexakyiv', 0.12, 0.93, '❗️Балістика на Київ! ㅤ Труха⚡️Київ | Надіслати новину')
   ('00:42', 'war_monitor', 0.07, 0.84, 'Загроза балістики триває з двох напрямків нагадуємо')
   ('00:43', 'war_monitor', 0.12, 0.94, '‼️Київ — спуск балістики!')
   ('00:43', 'kyiv_airdef', 0.13, 0.81, 'Як я і тут намалював вам, ракети звернули на Білу Церкву - Київ')
   ('00:43', 'kyiv_nebo', 0.16, 0.93, 'Балістика на Київ')
   ('00:43', 'kyiv_airdef', 0.32, 0.91, 'ЦІЛЬ')
   ('00:43', 'AerisRimor', 0.26, 0.94, 'КИЇВ ЦІЛЬ!')
   ('00:43', 'AerisRimor', 0.21, 0.92, 'БАЛІСТИКА!')
   ('00:43', 'kyiv_airdef', 0.3, 0.83, 'ТРОЯ')
   ('00:43', 'kyiv_nebo', 0.8, 0.56, 'Зараз гепне')
   ('00:43', 'kyiv_airdef', 0.27, 0.87, 'ДВІ ЦІЛІ')
   ('00:43', 'war_monitor', 0.14, 0.92, '‼️Київ — спуск балістики! Друга')
   ('00:43', 'VA_Kyiv', 0.61, 0.08, 'На іншій локації в Голосіївському районі пошкоджено недіючу будівлю.')
   ('00:44', 'kyiv_nebo', 0.09, 0.24, 'Чисто по балістиці')
===== 2026-07-02 01:00 alerts [('16:52', '04:05')]
   ('00:35', 'AerisRimor', 0.07, 0.83, 'Підлітають групи крилатих ракет до Броварів, далі на столицю.')
   ('00:36', 'kyiv_airdef', 0.08, 0.07, 'чисто по ракетам')
   ('00:38', 'vitaliy_klitschko', 0.84, 0.08, 'У Дарницькому районі, внаслідок падіння уламків біля житлового будинку, в одній із �
   ('00:39', 'truexakyiv', 0.71, 0.06, 'Заблоковані люди в одній із квартир будинку у Дарницькому районі, – Ткаченко.  Також у Д
   ('00:39', 'truexakyiv', 0.79, 0.07, 'Місце влучання у двір біля ЖК «Бульвар фонтанів» та «Французький квартал». ㅤ Труха⚡️К
   ('00:40', 'AerisRimor', 0.07, 0.06, 'По ракетах чисто.')
   ('00:58', 'AerisRimor', 0.18, 0.96, 'ЦІЛЬ КИЇВ!')
   ('00:58', 'kyiv_airdef', 0.17, 0.94, 'ЦІЛЬ')
   ('00:58', 'kyiv_airdef', 0.17, 0.95, 'КИЇВ')
   ('00:58', 'kyiv_nebo', 0.13, 0.97, 'Балістика на Київ')
   ('00:58', 'truexakyiv', 0.13, 0.97, 'Балістика на Київ. ㅤ Труха⚡️Київ | Надіслати новину')
   ('00:58', 'war_monitor', 0.11, 0.97, '❗️ 1х Циркон на Київ')
   ('00:58', 'kyiv_airdef', 0.24, 0.82, 'ВИНОГРАДАР')
   ('00:58', 'kyiv_airdef', 0.24, 0.85, 'СВЯТОШИН')
   ('00:59', 'AerisRimor', 0.54, 0.78, 'Це Іскандер з Брянська. Оболонь.')
   ('00:59',
```

... ще 147 рядків

</details>

**Bash**: Read the remaining disputed hours in full

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
W = [('2026-05-14 01:00','2026-05-14 02:00'),('2026-07-02 01:20','2026-07-02 02:10'),('2026-07-06 01:30','2026-07-06 02:15'),('2026-07-11 01:00','2026-07-11 02:00'),('2026-08-16 00:00','2026-08-16 01:00'),('2026-09-23 23:00','2026-09-24 00:00')]
for a,b in W:
    print('=====', a, b)
    for r in con.execute(f\"SELECT strftime(t.published_at, '%H:%M'), t.channel, round(k.p_strike,2) ps, round(k.p_threat,2) pt, round(k.p_drone,2) pd, replace(left(t.text,95), chr(10),' ') FROM kyiv_threat_posts k JOIN tg_posts t USING (channel, post_id) WHERE t.published_at >= TIMESTAMP '{a}' AND t.published_at < TIMESTAMP '{b}' AND (k.p_strike>=0.4 OR t.text ILIKE '%вибух%' OR t.text ILIKE '%мінус%' OR t.text ILIKE '%гучно%' OR t.text ILIKE '%чисто%' OR t.text ILIKE '%відбій%' OR t.text ILIKE '%збит%') ORDER BY t.published_at LIMIT 30\").fetchall(): print('  ', r)
" 2>&1 | cut -c1-190
```

<details><summary>результат: 75 рядків</summary>

```
===== 2026-05-14 01:00 2026-05-14 02:00
   ('01:00', 'kyiv_airdef', 0.1, 0.07, 0.08, 'чисто')
   ('01:02', 'kyiv_airdef', 0.06, 0.05, 0.06, 'Київ надалі чисто')
   ('01:02', 'kyiv_nebo', 0.1, 0.12, 0.11, 'По ракетах біля Києва наразі чисто, але ще є на Білу Церкву')
   ('01:02', 'truexakyiv', 0.15, 0.19, 0.31, 'Останні КР на БЦ.  Над Києвом дорозвідка по ракетам.  UPD 04:07: чисто. ㅤ Труха⚡️Киї
   ('01:09', 'VA_Kyiv', 0.49, 0.05, 0.49, 'В Дарницькому районі пошкоджено житловий будинок. Сталося обрушення конструкці
   ('01:09', 'vitaliy_klitschko', 0.85, 0.25, 0.67, 'В Оболонському районі уламки впали на триповерхову будівлю паркінгу та на 
   ('01:09', 'truexakyiv', 0.78, 0.06, 0.46, 'В Оболонському районі уламки впали на будівлю бізнес-центру та житлового буди�
   ('01:09', 'truexakyiv', 0.46, 0.05, 0.44, '❗️В Дарницькому районі Києва сталося обрушення житлового будинку, під завала
   ('01:19', 'vitaliy_klitschko', 0.47, 0.08, 0.62, 'У Дарницькому районі, за попередньою інформацією, обвалилися конструкції �
   ('01:25', 'kyiv_nebo', 0.05, 0.04, 0.06, 'Сам Київ наразі чисто')
   ('01:32', 'kyiv_airdef', 0.07, 0.04, 0.06, 'Київ та агломерація - чисто')
   ('01:32', 'kyiv_nebo', 0.06, 0.04, 0.06, 'Біля Києва чисто')
   ('01:41', 'vitaliy_klitschko', 0.79, 0.07, 0.31, 'У Голосіївському районі сталося падіння уламків на будівлю бізнес-центру. 
   ('01:42', 'war_monitor', 0.56, 0.06, 0.5, 'У Києві відомо про влучання у житловий багатоквартирний будинок. Повідомляєть
===== 2026-07-02 01:20 2026-07-02 02:10
   ('01:33', 'vitaliy_klitschko', 0.77, 0.05, 0.26, 'У Дарницькому районі, внаслідок влучання, сталося руйнування з першого по �
   ('01:33', 'truexakyiv', 0.65, 0.06, 0.27, 'Руйнування з першого по шостий поверхи в 9-поверховому житловому будинку у Дар�
   ('01:34', 'kyiv_nebo', 0.07, 0.08, 0.13, 'Київ наразі чисто')
   ('01:58', 'war_monitor', 0.08, 0.06, 0.09, '⚪️ Відбій загрози балістики.')
   ('02:05', 'truexakyiv', 0.47, 0.06, 0.57, 'Величезна вирва та пошкоджений будинок через атаку. ㅤ Труха⚡️Київ | Надіслат�
   ('02:08', 'kyiv_airdef', 0.23, 0.07, 0.56, 'мінус')
   ('02:08', 'war_monitor', 0.11, 0.12, 0.86, 'По цьому мінус. Новий реактивний БпЛА від Кіпті у напрямку Києва. Так і будуть �
===== 2026-07-06 01:30 2026-07-06 02:15
   ('01:46', 'truexakyiv', 0.62, 0.07, 0.28, 'Дуже сильна пожежа у ЖК «Славутич». ㅤ Труха⚡️Київ | Надіслати новину')
   ('01:48', 'AerisRimor', 0.23, 0.11, 0.16, 'І як ви розумієте усе що вибухає розлітається уламками, тож будьте обережні.')
   ('01:54', 'truexakyiv', 0.09, 0.11, 0.08, 'Не фіксується.  UPD 05:10: відбій. ㅤ Труха⚡️Київ | Надіслати новину')
   ('02:01', 'truexakyiv', 0.9, 0.12, 0.43, 'Деякі з частин ворожих ракет продовжують детонувати.  Звуки вибухів лунають у м
   ('02:05', 'kyiv_airdef', 0.08, 0.09, 0.06, 'очікуємо відбій')
   ('02:06', 'AerisRimor', 0.1, 0.06, 0.07, 'З асфальту ніякі "цікаві" предмети які б вам хотілося собі затрофеїти теж не під
   ('02:09', 'VA_Kyiv', 0.08, 0.04, 0.05, '🟢 м. Київ -
```

... ще 44 рядки

</details>

**Bash**: Find where the hand lists and corrections are used

```
grep -n "READ_TRUE\|READ_FALSE\|EXAMPLE_HOURS\|CORRECTIONS" src/airalerts/silver/threat_hourly.py scripts/verify/*.py tests/*.py; sed -n 847,931p src/airalerts/silver/threat_hourly.py
```

<details><summary>результат: 95 рядків</summary>

```
scripts/verify/label_check.py:78:    L += ["4. THRESHOLDS (before CORRECTIONS)", f"current rule {th.RULE['strike']}: {len(rule)} hours"]
src/airalerts/silver/threat_hourly.py:93:CORRECTIONS = {
src/airalerts/silver/threat_hourly.py:99:EXAMPLE_HOURS = ("2026-10-07T00:00:00Z", "2026-10-07T01:00:00Z", "2026-10-10T11:00:00Z", "2026-06-15T00:00:00Z", "2026-08-16T06:00:00Z",
src/airalerts/silver/threat_hourly.py:105:READ_TRUE = ("2026-06-02T01", "2026-06-15T00", "2026-08-16T06", "2026-10-07T00", "2026-10-07T01", "2026-10-10T11",
src/airalerts/silver/threat_hourly.py:107:READ_FALSE = ("2026-05-14T10", "2026-05-24T09", "2026-06-02T09", "2026-08-19T09", "2026-08-20T09", "2026-05-24T07", "2026-06-10T09",
src/airalerts/silver/threat_hourly.py:611:    for s in EXAMPLE_HOURS:
src/airalerts/silver/threat_hourly.py:776:        fix = CORRECTIONS.get(f"{h:%Y-%m-%dT%H}")
src/airalerts/silver/threat_hourly.py:790:            "corrections": json.dumps({k: v[0] for k, v in CORRECTIONS.items()})}
src/airalerts/silver/threat_hourly.py:884:    ok("hand-read strike hours are missile_strike", all(flags[parse_utc(f"{x}:00:00Z")]["missile_strike"] for x in READ_TRUE),
src/airalerts/silver/threat_hourly.py:885:       f"{len(READ_TRUE)} hours")
src/airalerts/silver/threat_hourly.py:886:    ok("hand-read hours without a strike are not missile_strike", not any(flags[parse_utc(f"{x}:00:00Z")]["missile_strike"] for x in READ_FALSE),
src/airalerts/silver/threat_hourly.py:887:       f"{len(READ_FALSE)} hours")
def selftest(log=print):
    """Structure of the two tables; features() and labels() on every hour from T0 to the last usable t against plain loops;
    the error after the last usable t; ASOF on 3 random t. Reads the two Parquet files only (no Jev, no API)."""
    bad = []

    def ok(name, cond, info=""):
        log(f"{'ok  ' if cond else 'FAIL'} {name}" + (f": {info}" if info else ""))
        if not cond:
            bad.append(name)

    con = _con()
    end = parse_utc(_label_end_meta())
    last_t = floor_hour(end)  # the last usable t: the end of the last labelled hour
    rows = _arrow(con, "SELECT * FROM kyiv_threat_hourly ORDER BY hour_utc").to_pylist()
    posts = _arrow(con, "SELECT * FROM kyiv_threat_posts ORDER BY published_at, channel, post_id").to_pylist()
    flags = {r["hour_utc"]: r for r in rows}
    first, last = rows[0]["hour_utc"], rows[-1]["hour_utc"]
    ok("label_end in the Parquet metadata is label_end() of bronze", iso(end) == label_end(), iso(end))
    ok("one row per hour, no gaps", len(rows) == int((last - first) / HOUR) + 1 and all(b["hour_utc"] - a["hour_utc"] == HOUR
       for a, b in zip(rows, rows[1:])), f"{len(rows)} rows from {iso(first)} to {iso(last)}")
    ok("first hour is FETCH_FROM, last hour ends at or before label_end", iso(first) == FETCH_FROM and last + HOUR <= end < last + 2 * HOUR)
    ok("available_at = hour_utc + 1 h; post hour = floor(published_at)", all(r["available_at"] == r["hour_utc"] + HOUR for r in rows)
       and
```

... ще 60 рядків

</details>

**Edit**: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/threat\_hourly.py

```
файл: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/threat_hourly.py
--- було:
    "2026-08-27T16": (False, ()),  # debris on a dormitory at 16:55Z during a jet drone attack; the ballistic threat of 16:24Z was
                                   # called off at 16:37Z (kpszsu 74865), so no missile reached the city
}
--- стало:
    "2026-08-27T16": (False, ()),  # debris on a dormitory at 16:55Z during a jet drone attack; the ballistic threat of 16:24Z was
                                   # called off at 16:37Z (kpszsu 74865), so no missile reached the city
    # Audit of 2026-10-11 (docs/data/VERIFICATION.md): the last hour of an attack where the posts only report damage after the
    # missiles (p_strike 0.7-0.9 for "уламки впали", "пожежа"), and the fresh gate still sees the alarms of the attack 90 min back.
    # Every hour was read: no explosion, shoot-down or hit in it, only reports, "чисто" and the all
... ще 1738 символів
```

<details><summary>результат: 1 рядок</summary>

```
The file /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/threat_hourly.py has been updated successfully.
```

</details>

**Edit**: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/threat\_hourly.py

```
файл: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/threat_hourly.py
--- було:
# Hours read by hand (the posts and their texts), not a ground truth. Strike: 6 from the S3a pilot, 4 from the verification of S3b.
# No strike: 18 from the S3a pilot; 6 that the verification of S3b read as drones only or damage reports after the attack; 10 threat
# hours without a strike that the verification found right; 3 read in the fix of S3b (an overnight summary, a crater found
# after the attack, a drone that fell).
READ_TRUE = ("2026-06-02T01", "2026-06-15T00", "2026-08-16T06", "2026-10-07T00", "2026-10-07T01", "2026-10-10T11",
             "2026-05-24T02", "2026-06-27T23",
... ще 23 символів
--- стало:
# Hours read by hand (the posts and their texts), not a ground truth. Strike: 5 from the S3a pilot, 4 from the verification of S3b.
# No strike: 18 from the S3a pilot; 6 that the verification of S3b read as drones only or damage reports after the attack; 10 threat
# hours without a strike that the verification found right; 3 read in the fix of S3b (an overnight summary, a crater found
# after the attack, a drone that fell); 1 from the audit of 2026-10-11 (a repeat of an earlier damage report).
READ_TRUE = ("2026-06-02T01", "2026-06-15T00", "2026-08-16T06", "2026-10-07T00", "2026-10-10T11",
   
... ще 77 символів
```

<details><summary>результат: 1 рядок</summary>

```
The file /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/threat_hourly.py has been updated successfully.
```

</details>

**Edit**: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/threat\_hourly.py

```
файл: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/threat_hourly.py
--- було:
              "2026-06-02T03", "2026-07-13T22", "2026-09-25T01")
--- стало:
              "2026-06-02T03", "2026-07-13T22", "2026-09-25T01",
              "2026-10-07T01")
```

<details><summary>результат: 1 рядок</summary>

```
The file /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/threat_hourly.py has been updated successfully.
```

</details>

**Edit**: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/threat\_hourly.py

```
файл: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/threat_hourly.py
--- було:
    known = ("2026-10-07T00:00:00Z", "2026-10-07T01:00:00Z", "2026-10-10T11:00:00Z")
--- стало:
    known = ("2026-10-07T00:00:00Z", "2026-10-10T11:00:00Z")
```

<details><summary>результат: 1 рядок</summary>

```
The file /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/threat_hourly.py has been updated successfully.
```

</details>

**Bash**: Back up silver and gold, rebuild the strike label from cache

```
B=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/backup_before_fix && mkdir -p $B && cp -p data/silver/*.parquet data/gold/kyiv_hourly.parquet $B/ && ls $B | wc -l && time choom -n 500 -- .venv/bin/python -I -m airalerts.silver.threat_hourly build 2>&1 | tail -5
```

<details><summary>результат: 7 рядків</summary>

```
12
label_end 2026-10-10T17:11:14Z; 4244 hours; answers of 98453 posts read from the Jev cache
{'kyiv_threat_posts rows': 98453, 'kyiv_threat_hourly rows': 4244, 'first_hour': '2026-04-16T21:00:00Z', 'last_hour': '2026-10-10T16:00:00Z', 'label_end': '2026-10-10T17:11:14Z', 'strike_hours': 62, 'threat_hours': 425}

real	0m15.353s
user	0m14.924s
sys	0m1.680s
```

</details>

**Bash**: Run the strike label selftest

```
.venv/bin/python -I -m airalerts.silver.threat_hourly selftest 2>&1 | tail -25
```

<details><summary>результат: 25 рядків</summary>

```
ok   label_end in the Parquet metadata is label_end() of bronze: 2026-10-10T17:11:14Z
ok   one row per hour, no gaps: 4244 rows from 2026-04-16T21:00:00Z to 2026-10-10T16:00:00Z
ok   first hour is FETCH_FROM, last hour ends at or before label_end
ok   available_at = hour_utc + 1 h; post hour = floor(published_at)
ok   n_posts_jev = posts of the hour in kyiv_threat_posts: 98453 posts
ok   posts unique by (channel, post_id)
ok   jev_model and prompt_version: jev-1.13.0 kyiv_threat_hourly-v1
ok   evidence and first_strike_at exist exactly for strike hours, first_strike_at inside the hour
ok   known strike hours are missile_strike: 2026-10-07T00:00:00Z, 2026-10-10T11:00:00Z
     2026-10-07T00:00:00Z first_strike_at 2026-10-07 00:14:30 evidence 11 posts, first ['truexakyiv/91761', 'AerisRimor/89414']
     2026-10-10T11:00:00Z first_strike_at 2026-10-10 11:00:27 evidence 16 posts, first ['war_monitor/47542', 'kyiv_airdef/78777']
ok   hand-read strike hours are missile_strike: 9 hours
ok   hand-read hours without a strike are not missile_strike: 38 hours
ok   features: t_utc first, columns as documented, one row per t: 3909 rows, t from 2026-04-30T21:00:00Z to 2026-10-10T17:00:00Z
ok   features: no nulls: none
ok   features equal the plain loops on every t: 3909 t, 0 differ []
ok   labels: t_utc first, y_strike_3h equals the plain loops
ok   labels: null only when t + 3 h is after label_end: 3 null: 2026-10-10T15:00:00Z, 2026-10-10T16:00:00Z, 2026-10-10T17:00:00Z
base rate of y_strike_3h = 0.0353 (138 of 3906 t with a label; 3909 t in all)
     t_utc 2026-10-10 18:00:00 is after the hour after the last labelled hour 2026-10-10T17:00:00Z (label_end 2026-10-10T17:11:14Z)
ok   features() raises ValueError for t = 2026-10-10T18:00:00Z
ok   ASOF t=2026-06-09T16:00:00Z: features equal True; hourly rows 1291 of 4244, posts 15957 of 98453
ok   ASOF t=2026-06-29T15:00:00Z: features equal True; hourly rows 1770 of 4244, posts 20548 of 98453
ok   ASOF t=2026-08-21T20:00:00Z: features equal True; hourly rows 3047 of 4244, posts 39411 of 98453
ALL OK
```

</details>

**Bash**: Commit the label fix and locate event building in signals

```
git add src/airalerts/silver/threat_hourly.py && git commit -q -m "Correct 15 strike hours that only report damage after the missiles

The audit of 2026-10-11 read every strike hour: 14 last hours of an attack
hold only damage reports, recaps and the all clear, and one is a jet drone.
Strike hours 77 -> 62, positive rows of y_strike_3h 151 -> 138.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git log --oneline -1 && grep -n "def build_events\|def main\|def candidates\|rx_signals\|edited\|def events\|published_at" src/airalerts/silver/signals.py | head -40
```

<details><summary>результат: 17 рядків</summary>

```
5f35ff0 Correct 15 strike hours that only report damage after the missiles
4:Input: data/silver/tg_posts.parquet. A candidate is a post of one of CHANNELS whose rx_signals has S1, S2 or S4
196:    rows = con.execute(f"""SELECT channel, post_id, published_at, text, rx_signals, rx_classes, edited, is_original
197:        FROM read_parquet('{SRC}') WHERE channel IN ({chans}) AND published_at >= TIMESTAMP '{since}'
198:        AND (list_contains(rx_signals, 'S1') OR list_contains(rx_signals, 'S2') OR list_contains(rx_signals, 'S4'))
199:        ORDER BY published_at, channel, post_id""").fetchall()
200:    keys = ("channel", "post_id", "published_at", "text", "signals", "classes", "edited", "is_original")
240:    first, last = posts[0]["published_at"], posts[-1]["published_at"]
251:def build_events(posts, probs):
261:        items.sort(key=lambda it: (it[0]["published_at"], it[0]["channel"], it[0]["post_id"]))
264:            if cur and it[0]["published_at"] > cur[0][0]["published_at"] + GAP:
277:    return dict(connect().execute(f"SELECT channel, max(published_at) FROM read_parquet('{SRC}') "
281:def main():
435:                f.write(f"   {ref} {r['published_at']:%H:%M:%SZ} edited={r['edited']} actual_now={p['actual_now']:.2f} "
444:            f.write(f"{r['channel']}/{r['post_id']} {r['published_at']:%Y-%m-%dT%H:%M:%SZ} actual_now={p['actual_now']:.2f} "
450:        n_ed[sig] += bool(byref[ref]["edited"])
451:    print("events whose first post is edited (signal: edited of all):", {s: f"{n_ed[s]} of {n_all[s]}" for s in sorted(n_all)},
```

</details>

**Bash**: Read the signals module structure and main

```
sed -n 1,60p src/airalerts/silver/signals.py && sed -n 186,330p src/airalerts/silver/signals.py
```

<details><summary>результат: 205 рядків</summary>

```
"""Silver table prep_signal_events: events of strike preparation found in the monitoring channels: strategic aviation
(S1), MiG-31K (S2) and waves of attack drones (S4). Jev confirms that a post reports an actual event now.

Input: data/silver/tg_posts.parquet. A candidate is a post of one of CHANNELS whose rx_signals has S1, S2 or S4
(S3 and S5 are dropped and vanek_nikolaev is excluded: docs/HISTORY.md). Jev answers yes/no questions about every candidate
(many posts per request, dates removed from the text); code turns the confirmed posts into events: posts of one signal
and subtype within GAP of the first post of the event are one event, the event time is the earliest post.
Docs: docs/data/silver/prep_signal_events.md.

    .venv/bin/python -I -m airalerts.silver.signals                 # judge (Jev, cached) and build the table
    .venv/bin/python -I -m airalerts.silver.signals check <outdir>  # DONE checks, samples and the features test
"""
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from ..db import connect
from ..jev import MODEL, JevError, ask_many, usage
from ..paths import FETCH_FROM, SILVER
from .telegram_rx import S1_COUNT, S4_COUNT

TABLE = "prep_signal_events"
PATH = SILVER / f"{TABLE}.parquet"
SRC = SILVER / "tg_posts.parquet"
PROMPT_VERSION = "sig-v2"
CHANNELS = ("war_monitor", "kpszsu", "AerisRimor", "StrategicaviationT", "monitorwarr", "kyiv_airdef")
KEPT = ("S1", "S2", "S4")
THRESHOLD = 0.5            # noul threshold (docs/JEV.md rule 8); the table keeps the probabilities
GAP = timedelta(minutes=15)  # a post joins the event when it is at most GAP after the first post of the event
CAP_HOURS = 336.0          # hours_since_s1 cap: 14 days
WORKERS = 8                # Jev workers (the limit is 8)
MAX_POSTS, MAX_CHARS, MAX_TEXT = 8, 3000, 3500   # S4 requests: posts and characters of text; characters per post
```

... ще 165 рядків

</details>

**Bash**: Find build\_events callers and count pinned service posts

```
grep -n "build_events\|load_posts\|pinned\|станом" src/airalerts/silver/signals.py scripts/verify/*.py; .venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
print(con.execute(\"SELECT channel, count(*) FROM tg_posts WHERE text ILIKE '%pinned «%' GROUP BY 1 ORDER BY 2 DESC\").fetchall())
print(con.execute(\"SELECT channel, post_id, published_at, left(text,80) FROM tg_posts WHERE text ILIKE '%pinned «%' AND (list_contains(rx_signals,'S1') OR list_contains(rx_signals,'S2') OR list_contains(rx_signals,'S4')) LIMIT 5\").fetchall())
print(con.execute(\"SELECT count(*) FROM tg_posts WHERE text ILIKE '%pinned «%' AND (list_contains(rx_signals,'S1') OR list_contains(rx_signals,'S2') OR list_contains(rx_signals,'S4'))\").fetchall())
"
```

<details><summary>результат: 8 рядків</summary>

```
src/airalerts/silver/signals.py:192:def load_posts():
src/airalerts/silver/signals.py:251:def build_events(posts, probs):
src/airalerts/silver/signals.py:283:    posts = load_posts()
src/airalerts/silver/signals.py:287:    rows = build_events(posts, probs)
src/airalerts/silver/signals.py:408:    posts = load_posts()
[('AerisRimor', 58), ('kyiv_airdef', 4), ('StrategicaviationT', 3), ('monitorwarr', 3)]
[('AerisRimor', 67437, datetime.datetime(2026, 4, 24, 19, 22, 14), 'Aeris Rimor pinned «🎩Зведення станом на 23:23.  ❗️✈✈СА/ДА. Зафіксовано активніст'), ('StrategicaviationT', 30199, datetime.datetime(2026, 4, 25, 2, 1, 39), '✈️Стратегічна авіація pinned «Друзі, ми намагаємося оперативно попередити вас пр'), ('AerisRimor', 68082, datetime.datetime(2026, 5, 1, 5, 46, 5), 'Aeris Rimor pinned «🎩Зведення станом на 8:30.  ❗️✈✈СА/ДА без активностей які б н'), ('kyiv_airdef', 34207, datetime.datetime(2026, 5, 2, 18, 7, 29), 'Kyiv AirDefense 🌇 pinned «За інформацією, противник планує застосувати від 500 д'), ('AerisRimor', 68375, datetime.datetime(2026, 5, 2, 18, 55, 18), 'Aeris Rimor pinned «Зведення станом на 21:30.  ❗️✈✈СА/ДА. Без активностей які б ')]
[(28,)]
```

</details>

### Claude, 12:55

28 таких службових постів «pinned» серед кандидатів сигналів. Читаю функцію `check`, бо вона теж будує події.

**Bash**: Read the regexes and check function of signals

```
sed -n 60,80p src/airalerts/silver/signals.py; sed -n 340,470p src/airalerts/silver/signals.py
```

<details><summary>результат: 151 рядок</summary>

```
# ---------------------------------------------------------------- Jev questions

LEAD = ("The state lists numbered posts from Ukrainian military Telegram channels that monitor Russian aviation and "
        "drones. The text is Ukrainian or Russian and has no dates. Answer only about post {pid}; ignore all other posts. ")
# name: (question, criteria true, criteria false); {pid} is the id of the post in the state
QUESTIONS = {
    "actual_now": (
        "Does post {pid} report something that is happening right now or happened within the last few minutes (for "
        "example a takeoff, a flight, a launch, aircraft or drones on the move, an all-clear), as opposed to a forecast, "
        "a plan, a warning about what may happen later, a summary of past hours or days, or a general comment?",
        "The post states that an event is happening now or happened minutes ago.",
        "The post is a forecast, a plan, a warning about a possible future event, a daily or multi-day summary, a "
        "retrospective, a general comment, an advertisement, or says that nothing is happening."),
    "takeoff": (
        "Does post {pid} say that Russian strategic bombers (Tu-95, Tu-160 or Tu-22M3) have taken off, are in the air, "
        "or are being relocated (transferred) to another airfield?",
        "The post reports a takeoff, a flight in progress or a relocation (transfer) of Tu-95, Tu-160 or Tu-22M3 bombers.",
        "The post does not report such a takeoff, flight or relocation: it only names an airfield or an aircraft type, "
        "says the bombers stay at their bases or that no takeoff is seen, reports only that bombers landed, or reports "
        "something else."),

def features_check(first="2026-04-30 21:00:00", last=None, seed=20261010):
    """features() on every hour from first to last against plain Python, and ASOF views for 3 random t."""
    con = connect()
    con.execute(f"CREATE VIEW {TABLE} AS SELECT * FROM read_parquet('{PATH}')")
    events = [(s, st, a) for s, st, a in con.execute(f"SELECT signal, subtype, available_at FROM {TABLE}").fetchall()]
    if last is None:
        until = max(r[0] for r in con.execute(f"SELECT max(last_post_at) FROM {TABLE}").fetchall())
        last = f"{until:%Y-%m-%d %H}:00:00"
    f0, f1 = datetime.fromisoformat(first), datetime.fromisoformat(last)
    hours = [f0 + timedelta(hours=i) for i in range(int((f1 - f0).total_seconds() // 3600) + 1)]
    con.execute("CREATE TABLE t_hours AS SELECT * FROM (VALUES " + ",".join(f"(TIMESTAMP '{h}')" for h in hours) + ") v(t_utc)")
    tbl = features(con, "t_hours")
    cols = tbl.column_names
    nulls = {c: tbl.column(c).null_count for c in cols}
    assert tbl.num_rows == len(hours) and len(set(tbl.column("t_utc").to_pylist())) == len(hours), "one row per t_utc"
    assert cols[0] == "t_utc", cols
    bad = 0
    got = {c: tbl.column(c).to_pylist() for c in cols}
    for i, h in enumerate(hours):
```

... ще 111 рядків

</details>

**Edit**: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/signals.py

```
файл: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/signals.py
--- було:
def build_events(posts, probs):
    groups = defaultdict(list)
--- стало:
STATED = re.compile(r"станом на\s*(\d{1,2})[:.](\d{2})", re.I)
PINNED = re.compile(r"^[^\n«]{1,60} pinned «")
KYIV = ZoneInfo("Europe/Kyiv")


def written_later(r):
    """True when the text of post r is not the one published at published_at, so it must not make or start an event (audit of
    2026-10-11): a "pinned" service post (Telegram shows the text of the pinned post as it was when fetched), or a text that
    states a Kyiv time ("станом на HH:MM") 5 min to 12 h after the publication, that is, the post was rewritten later
    (AerisRimor updates its summary through the night). Bronze has
... ще 597 символів
```

<details><summary>результат: 1 рядок</summary>

```
The file /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/signals.py has been updated successfully.
```

</details>

**Edit**: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/signals.py

```
файл: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/signals.py
--- було:
    probs = judge(posts)
    rows = build_events(posts, probs)
--- стало:
    probs = judge(posts)
    later = [r for r in posts if written_later(r)]
    print(f"posts written after their publication, left out of the events: {len(later)}")
    rows = build_events([r for r in posts if not written_later(r)], probs)
```

<details><summary>результат: 1 рядок</summary>

```
The file /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/signals.py has been updated successfully.
```

</details>

**Edit**: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/signals.py

```
файл: /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/signals.py
--- було:
from pathlib import Path

import pyarrow as pa
--- стало:
from pathlib import Path
from zoneinfo import ZoneInfo

import pyarrow as pa
```

<details><summary>результат: 1 рядок</summary>

```
The file /home/ye/PROJECTS/ai-school/airalers/src/airalerts/silver/signals.py has been updated successfully.
```

</details>

**Bash**: Dry run the new filter with the Jev API blocked

```
S=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad && cat > $S/signals_nojev.py <<'EOF'
"""Run airalerts.silver.signals main() with the Jev API blocked: every answer must come from the cache."""
import sys
from airalerts import jev
def _blocked(*a, **k):
    raise RuntimeError("Jev API call blocked: a request is not in the cache")
jev._post = _blocked
from airalerts.silver import signals
if sys.argv[1:] == ["dry"]:
    posts = signals.load_posts()
    later = [r for r in posts if signals.written_later(r)]
    print("candidates", len(posts), "written later", len(later))
    for r in later:
        print(" ", r["channel"], r["post_id"], r["published_at"], r["sigs"], repr(r["text"][:70]))
else:
    signals.main()
EOF
grep -n "_post" src/airalerts/jev.py | head -5; .venv/bin/python -I $S/signals_nojev.py dry 2>&1 | tail -40
```

<details><summary>результат: 42 рядки</summary>

```
29:def _post(body, timeout=120):
56:            status, text = _post(body)
  AerisRimor 70384 2026-05-23 19:40:13 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 22:40.  ❗️✈✈СА/ДА. Від 22:31 а'
  AerisRimor 70988 2026-05-27 09:37:27 ('S1', 'S2') 'Aeris Rimor pinned «🎩Варто проговорити.   Загалом не багато що сказати'
  AerisRimor 71283 2026-06-01 20:03:43 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 22:00.  ❗️✈✈СА/ДА. Маємо попер'
  StrategicaviationT 32579 2026-06-03 10:47:16 ('S1', 'S2') '⚠️❗️ рф проводить модернізацію бортів Ту-22м3 до Ту-22м3м на Казансько'
  StrategicaviationT 32617 2026-06-03 19:15:57 ('S4',) '🛰 Супутникові знімки середньо-високої якості аеродрому «Донецьк» (т.о.'
  StrategicaviationT 32636 2026-06-04 13:15:31 ('S1',) '🛰 Супутникові знімки середньої якості аеродрому «Безімʼянка» (Самара, '
  StrategicaviationT 32671 2026-06-05 20:45:10 ('S1', 'S2') '🛰 Супутникові знімки середньої якості аеродрому «Оленья» (Мурманська о'
  StrategicaviationT 32690 2026-06-06 18:48:34 ('S1',) '🛰 Супутникові знімки середньої якості аеродрому «Енгельс-2» (Саратовсь'
  StrategicaviationT 32720 2026-06-07 17:15:02 ('S1',) '🛰 Супутникові знімки середньої якості аеродрому «Енгельс-2» (Саратовсь'
  AerisRimor 72445 2026-06-14 20:17:32 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 23:00.  ❗️✈✈СА/ДА. Маємо 2+ бо'
  StrategicaviationT 33400 2026-06-18 21:20:18 ('S1',) '⚠️ 2х борти Ту-95мс з аеродрому «Українка», ймовірно здійснюють переди'
  StrategicaviationT 33406 2026-06-19 11:23:06 ('S4',) '🛰 Супутникові знімки високої якості аеродрому «Приморсько-Ахтарськ» (К'
  StrategicaviationT 34042 2026-07-01 14:42:40 ('S1',) '🛰 Супутникові знімки високої якості аеродрому «Оленья» (Мурманська обл'
  AerisRimor 73789 2026-07-01 21:06:00 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 00:05.  ❗️✈✈СА/ДА. Маємо попер'
  StrategicaviationT 34440 2026-07-05 16:30:00 ('S1',) '🛰 Супутникові знімки високої якості аеродрому «Оленья» (Мурманська обл'
  StrategicaviationT 35226 2026-07-16 09:05:01 ('S1',) '🛰 Супутникові знімки середньої якості аеродрому «Українка» (Амурська о'
  AerisRimor 75860 2026-07-18 22:29:25 ('S4',) 'Aeris Rimor pinned «🎩Додатково.  З вечора та до початку світанку є заг'
  StrategicaviationT 35647 2026-07-19 12:32:27 ('S1',) '🛰 Супутникові знімки середньої якості аеродрому «Енгельс-2» (Саратовсь'
  StrategicaviationT 35762 2026-07-20 09:10:33 ('S1',) '🛰 Супутникові знімки середньої якості аеродрому «Українка» (Амурська о'
  AerisRimor 77371 2026-07-29 09:54:07 ('S1',) 'Aeris Rimor pinned «🎩Варто проговорити.   Ворог має завершити підготов'
  AerisRimor 77394 2026-07-29 21:05:03 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 23:55.  ❗️✈✈СА/ДА. Був виліт С'
  StrategicaviationT 36805 2026-08-01 15:30:02 ('S1',) '🛰 Супутникові знімки середньої якості аеродрому «Українка» (Амурська о'
  StrategicaviationT 36829 2026-08-02 15:30:48 ('S4',) '🛰 Супутникові знімки високої якості аеродрому «Балтимор» (Воронезька о'
  StrategicaviationT 37160
```

... ще 16 рядків

</details>

**Bash**: Restrict the stated time to HH:MM and dry run again

```
sed -i 's/STATED = re.compile(r"станом на\\s\*(\\d{1,2})\[:.\](\\d{2})", re.I)/STATED = re.compile(r"станом на\\s*(\\d{1,2}):(\\d{2})", re.I)/' src/airalerts/silver/signals.py && grep -n "^STATED" src/airalerts/silver/signals.py && .venv/bin/python -I /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/signals_nojev.py dry 2>&1 | cut -c1-150
```

<details><summary>результат: 39 рядків</summary>

```
252:STATED = re.compile(r"станом на\s*(\d{1,2}):(\d{2})", re.I)
candidates 36582 written later 37
  kpszsu 60422 2026-04-21 05:52:46 ('S4',) '⚡️ ЗБИТО/ПОДАВЛЕНО 1 РАКЕТУ ТА 116 ВОРОЖИХ БПЛА\n➖➖➖➖➖➖�
  AerisRimor 67431 2026-04-24 19:06:43 ('S1', 'S2', 'S4') '🎩Зведення станом на 23:23.\n\n❗️✈✈СА/ДА. Зафіксова�
  AerisRimor 67437 2026-04-24 19:22:14 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 23:23.  ❗️✈✈СА/ДА. Зафік�
  StrategicaviationT 30199 2026-04-25 02:01:39 ('S1',) '✈️Стратегічна авіація pinned «Друзі, ми намагаємося �
  AerisRimor 68082 2026-05-01 05:46:05 ('S1', 'S2') 'Aeris Rimor pinned «🎩Зведення станом на 8:30.  ❗️✈✈СА/ДА без �
  kyiv_airdef 34207 2026-05-02 18:07:29 ('S4',) 'Kyiv AirDefense 🌇 pinned «За інформацією, противник планує засто
  AerisRimor 68375 2026-05-02 18:55:18 ('S1',) 'Aeris Rimor pinned «Зведення станом на 21:30.  ❗️✈✈СА/ДА. Без акти
  kyiv_airdef 34761 2026-05-11 13:13:29 ('S1',) 'Kyiv AirDefense 🌇 pinned «За наявною інформацією, ворог закінчує
  AerisRimor 68847 2026-05-12 01:17:14 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 3:55.  ❗️Дані актуальних
  AerisRimor 68894 2026-05-12 01:51:53 ('S4',) 'Aeris Rimor pinned «❗️Житомир/район готовність на наступні 45хв
  AerisRimor 69033 2026-05-13 08:12:19 ('S1', 'S2') 'Aeris Rimor pinned «⌨️Варто проговорити 2.0 (Станом на 11:11, 13.05)
  AerisRimor 69212 2026-05-13 17:15:36 ('S1', 'S2', 'S4') '🎩Зведення станом на 00:25.\n\n❗️✈✈СА/ДА. Зафіксова�
  AerisRimor 69218 2026-05-13 18:19:35 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 00:25.  ❗️✈✈СА/ДА. Зафік�
  AerisRimor 69316 2026-05-13 23:26:00 ('S1',) 'Aeris Rimor pinned «❗️✈🚀Увага. Є свідчення про виконання бойо
  AerisRimor 70384 2026-05-23 19:40:13 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 22:40.  ❗️✈✈СА/ДА. Від 22:3
  AerisRimor 70988 2026-05-27 09:37:27 ('S1', 'S2') 'Aeris Rimor pinned «🎩Варто проговорити.   Загалом не багато щ
  AerisRimor 71283 2026-06-01 20:03:43 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 22:00.  ❗️✈✈СА/ДА. Маємо 
  StrategicaviationT 32579 2026-06-03 10:47:16 ('S1', 'S2') '⚠️❗️ рф проводить модернізацію бортів Ту-22м3 д�
  AerisRimor 72445 2026-06-14 20:17:32 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 23:00.  ❗️✈✈СА/ДА. Маємо 
  StrategicaviationT 33400 2026-06-18 21:20:18 ('S1',) '⚠️ 2х борти Ту-95мс з аеродрому «Українка», ймовірно
  AerisRimor 73789 2026-07-01 21:06:00 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 00:05.  ❗️✈✈СА/ДА. Маємо 
  AerisRimor 75860 2026-07-18 22:29:25 ('S4',) 'Aeris Rimor pinned «🎩Додатково.  З вечора та до початку світанк�
  AerisRimor 77371 2026-07-29 09:54:07 ('S1',) 'Aeris Rimor pinned «🎩Варто проговорити.   Ворог має завершити п�
  AerisRimor 77394 2026-07-29 21:05:03 ('S1',) 'Aeris Rimor pinned «🎩Зведення станом на 23:55.  ❗️✈✈СА/ДА. Був ви
  AerisRimor 79019 2026-08-11 21:16:03 ('S1',) 'Aeris Rimor pinned «🎩Зведення актуалізоване станом на 23:30 14.08 ц.
  kpszsu 73403 2026-08-19 05:24:45 ('S4',) '⚡️ ЗБИТО/ПОДАВЛЕНО 58 ЦІЛЕЙ
```

... ще 11 рядків

</details>

**Bash**: Read the one doubtful flagged post

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
import re
con = register_layers(connect())
for pid in (32579,):
    pub, t = con.execute(f\"SELECT published_at, text FROM tg_posts WHERE channel='StrategicaviationT' AND post_id={pid}\").fetchone()
    m = re.search(r'станом на\s*(\d{1,2}):(\d{2})', t, re.I); print(pub, 'Kyiv +3h', repr(t[max(0,m.start()-80):m.end()+60]))
"
```

<details><summary>результат: 1 рядок</summary>

```
2026-06-03 10:47:16 Kyiv +3h 'і «Борисоглебське» на відкритому повітрі знаходилися 2х робочі борти Ту-22м3, а станом на 18:08 вже 4х.\n\n◽️ на початку війни вже було бойове застосування б'
```

</details>

**Bash**: Rebuild signal events from the Jev cache only

```
time choom -n 500 -- .venv/bin/python -I /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/signals_nojev.py 2>&1 | tail -6
```

<details><summary>результат: 10 рядків</summary>

```
  judged 5600/6239 requests, 31474 posts, 3 s
  judged 6000/6239 requests, 34674 posts, 4 s
  judged 6239/6239 requests, 36582 posts, 4 s
Jev: 6239 requests for 36582 posts; cache of prep_signal_events now 6019 calls, 17759877 input tokens, $0.7459 (new in this run: 0 calls, $0.0)
posts written after their publication, left out of the events: 37
wrote prep_signal_events.parquet: 9361 events, {('S1', 'relocation'): 68, ('S1', 'takeoff'): 383, ('S2', 'airborne'): 48, ('S2', 'all_clear'): 41, ('S4', 'launch'): 8821}, 6 s

real	0m6.305s
user	0m5.816s
sys	0m1.365s
```

</details>

**Bash**: Diff old and new signal events and run the module check

```
S=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad && .venv/bin/python -I -c "
import pyarrow.parquet as pq
old = {r['event_id']: r for r in pq.read_table('$S/backup_before_fix/prep_signal_events.parquet').to_pylist()}
new = {r['event_id']: r for r in pq.read_table('data/silver/prep_signal_events.parquet').to_pylist()}
gone = sorted(set(old) - set(new)); added = sorted(set(new) - set(old))
print('gone', len(gone), gone); print('added', len(added), added)
same_id_changed = [k for k in set(old) & set(new) if old[k]['post_refs'] != new[k]['post_refs']]
print('same id, other posts', len(same_id_changed), sorted(same_id_changed)[:10])
" && mkdir -p $S/signals_check && .venv/bin/python -I -c "
from airalerts import jev
def _b(*a, **k): raise RuntimeError('blocked')
jev._post = _b
from airalerts.silver import signals
signals.check('$S/signals_check')
" 2>&1 | grep -E "MISMATCH|mismatches|ASOF|Error|assert|rows " | head -12
```

<details><summary>результат: 8 рядків</summary>

```
gone 7 ['S1-relocation-20260618T212018Z', 'S1-takeoff-20260424T190643Z', 'S1-takeoff-20260424T192147Z', '[REDACTED: ключ]', 'S1-takeoff-20260907T174502Z', 'S4-launch-20260926T041717Z', 'S4-launch-20260926T043400Z']
added 5 ['S1-takeoff-20260424T191323Z', 'S1-takeoff-20260424T192854Z', 'S1-takeoff-20260907T175302Z', 'S4-launch-20260926T041900Z', 'S4-launch-20260926T043528Z']
same id, other posts 0 []
rows 9361 {'data_until': '2026-10-10T11:36:43Z', 'candidates': '36582', 'built_at': '2026-10-11T09:56:12Z'}
  null counts {'t_utc': 0, 's1_takeoff_6h': 0, 's1_takeoff_24h': 0, 'hours_since_s1': 0, 's2_mig31k_airborne': 0, 's4_drone_waves_6h': 0}; mismatches against plain Python: 0
  ASOF t=2026-06-09 16:00:00Z rows known 2331: {'s1_takeoff_6h': 0, 's1_takeoff_24h': 0, 'hours_since_s1': 46.74944444444444, 's2_mig31k_airborne': 0, 's4_drone_waves_6h': 10} identical to full: True
  ASOF t=2026-06-29 15:00:00Z rows known 3258: {'s1_takeoff_6h': 0, 's1_takeoff_24h': 1, 'hours_since_s1': 9.059722222222222, 's2_mig31k_airborne': 0, 's4_drone_waves_6h': 15} identical to full: True
  ASOF t=2026-08-21 20:00:00Z rows known 6051: {'s1_takeoff_6h': 2, 's1_takeoff_24h': 6, 'hours_since_s1': 3.2575, 's2_mig31k_airborne': 0, 's4_drone_waves_6h': 14} identical to full: True
```

</details>

**Bash**: Check the post that now starts the 09-07 S1 event

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
for ch, pid in [('StrategicaviationT',39958)]:
    print(con.execute(f\"SELECT published_at, edited, replace(left(text,500), chr(10), ' | ') FROM tg_posts WHERE channel='{ch}' AND post_id={pid}\").fetchall())
print(con.execute(\"SELECT event_id, first_post_at, post_refs FROM prep_signal_events WHERE event_id IN ('S1-takeoff-20260424T191323Z','S1-takeoff-20260424T192854Z','S1-takeoff-20260907T175302Z')\").fetchall())
for ch, pid in [('StrategicaviationT',30080),('AerisRimor',67440)]:
    pass
"
```

<details><summary>результат: 2 рядки</summary>

```
[(datetime.datetime(2026, 9, 7, 17, 53, 2), True, '⚠️ Відмічено зліт 2х бортів Ту-160 з аеродрому «Українка», підліт до пускових в районі Вологди, орієнтовно 03:00.')]
[('S1-takeoff-20260424T191323Z', datetime.datetime(2026, 4, 24, 19, 13, 23), ['StrategicaviationT/30075', 'StrategicaviationT/30076', 'kyiv_airdef/33409', 'StrategicaviationT/30077', 'AerisRimor/67439']), ('S1-takeoff-20260424T192854Z', datetime.datetime(2026, 4, 24, 19, 28, 54), ['StrategicaviationT/30078', 'kyiv_airdef/33412']), ('S1-takeoff-20260907T175302Z', datetime.datetime(2026, 9, 7, 17, 53, 2), ['StrategicaviationT/39958'])]
```

</details>

**Bash**: Commit the signals fix and read rf\_strikes features

```
git add src/airalerts/silver/signals.py && git commit -q -m "Leave posts rewritten after publication out of the signal events

A pinned service post shows the pinned text as fetched, and a text that
states a Kyiv time 5 min to 12 h after its publication was edited later
(AerisRimor rewrites its night summary). 37 posts, the leak found by the
audit of 2026-10-11: events 9363 -> 9361, no new Jev call.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git log --oneline -1 && sed -n 100,200p src/airalerts/silver/rf_strikes.py
```

<details><summary>результат: 102 рядки</summary>

```
d1a041a Leave posts rewritten after publication out of the signal events


def write(name, rows, meta):
    SILVER.mkdir(parents=True, exist_ok=True)
    path = SILVER / f"{name}.parquet"
    tmp = path.with_suffix(".tmp")
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMAS[name]).replace_schema_metadata(meta), tmp)
    tmp.replace(path)
    return len(rows)


def main():
    snap, fetched = snapshot()
    meta = {"snapshot": snap.name, "fetched_at": f"{fetched:%Y-%m-%dT%H:%M:%SZ}", "lag_hours": str(LAG.total_seconds() / 3600)}
    print({POINTS: write(POINTS, build_points(snap, fetched), meta), DAYS: write(DAYS, build_days(snap, fetched), meta), **meta})


# ------------------------------------------------------------------------------- features for gold

SQL = """
WITH t AS (SELECT DISTINCT CAST(t_utc AS TIMESTAMP) AS t_utc FROM {t_table}),
p AS (SELECT * FROM strike_points WHERE country = 'RU' AND NOT occupied)
SELECT t.t_utc,
  (SELECT count(*) FROM p WHERE p.available_at >= t.t_utc - INTERVAL 24 HOUR AND p.available_at < t.t_utc)::INTEGER AS rf_points_1d,
  (SELECT count(*) FROM p WHERE p.available_at >= t.t_utc - INTERVAL 72 HOUR AND p.available_at < t.t_utc)::INTEGER AS rf_points_3d,
  (SELECT count(DISTINCT region) FROM p WHERE p.available_at >= t.t_utc - INTERVAL 72 HOUR AND p.available_at < t.t_utc)::INTEGER AS rf_regions_3d,
  (SELECT count(*) FROM p WHERE p.is_energy AND p.available_at >= t.t_utc - INTERVAL 24 HOUR AND p.available_at < t.t_utc)::INTEGER AS rf_energy_1d,
  (SELECT count(*) FROM p WHERE p.is_energy AND p.available_at >= t.t_utc - INTERVAL 72 HOUR AND p.available_at < t.t_utc)::INTEGER AS rf_energy_3d,
  (SELECT count(*) > 0 FROM p WHERE p.is_moscow AND p.available_at >= t.t_utc - INTERVAL 72 HOUR AND p.available_at < t.t_utc)::INTEGER AS rf_moscow_3d,
  COALESCE((SELECT sum(intercepted) FROM strike_days d WHERE d.country = 'RU'
            AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc), 0)::INTEGER AS rf_drones_intercepted_1d,
  COALESCE((SELECT sum(missiles_max) FROM strike_days d WHERE d.country = 'UA'
            AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc), 0)::INTEGER AS ua_missiles_launched_1d,
  COALESCE((SELECT sum(drones_max) FROM strike_days d WHERE d.country = 'UA'
            AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc), 0)::INTEGER AS ua_drones_launched_1d,
  LEAST({cap}, COALESCE((SELECT date_diff('second', max(p.available_at), t.t_utc) / 3600.0 FROM p
                          WHERE p.is_energy AND p.available_at < t.t_utc), {cap}))::DOUBLE AS hours_since_rf_energy
FROM t ORDER BY t.t_utc"""
COLS = ["rf_points_1d", "rf_points_3d", "rf_regions_3d", "rf_energy_1d", "rf_energy_3d", "rf_moscow_3d", "rf_drones_intercepted_1d",
```

... ще 62 рядки

</details>

**Bash**: Read the rest of rf\_strikes and check null intercepts

```
sed -n 200,260p src/airalerts/silver/rf_strikes.py; .venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
print(con.execute(\"SELECT count(*), count(*) FILTER (WHERE intercepted IS NULL), count(*) FILTER (WHERE drones_intercepted IS NULL), count(*) FILTER (WHERE intercepted IS NOT NULL AND drones_intercepted IS NULL) FROM strike_days WHERE country='RU'\").fetchone())"
```

<details><summary>результат: 58 рядків</summary>

```
    print("points by country, occupied:", con.execute(f"SELECT country, occupied, count(*) FROM {POINTS} GROUP BY ALL ORDER BY ALL").fetchall())
    print("RU points without occupied, by month (points, energy, Moscow):",
          con.execute(f"""SELECT strftime(date, '%Y-%m'), count(*), count(*) FILTER (WHERE is_energy), count(*) FILTER (WHERE is_moscow)
                          FROM {POINTS} WHERE country = 'RU' AND NOT occupied GROUP BY 1 ORDER BY 1""").fetchall())
    print("UA launched by month (missiles max, drones max):",
          con.execute(f"SELECT strftime(date, '%Y-%m'), sum(missiles_max), sum(drones_max) FROM {DAYS} WHERE country = 'UA' GROUP BY 1 ORDER BY 1").fetchall())
    print("available_at = date + 30 h in every row:", all(con.execute(
        f"SELECT bool_and(available_at = CAST(date AS TIMESTAMP) + INTERVAL 30 HOUR) FROM {t}").fetchone()[0] for t in (POINTS, DAYS)))
    mod = ROOT / "data" / "verification" / "mod_russia_daily_drones.csv"  # drones the MoD reported per UTC publication day,
    if mod.exists():                                                      # parsed from @mod_russia by the previous rf_strikes
        rows = con.execute(f"""SELECT d.date, d.intercepted, (SELECT mod_drones_downed FROM read_csv('{mod}') m WHERE m.date_utc = d.date)
                                 FROM {DAYS} d WHERE d.country = 'RU' AND d.date BETWEEN DATE '2026-07-01' AND DATE '2026-10-09'
                                 ORDER BY 1""").fetchall()
        eq = sum(1 for _, a, b in rows if a == b)
        near = sum(1 for _, a, b in rows if a and b and abs(a - b) <= 0.1 * b)
        print(f"RU intercepted of the site vs sum of the MoD Telegram reports published on the same UTC day, 2026-07-01..2026-10-09: "
              f"days {len(rows)}, equal {eq}, within 10% {near}")


def cmd_features_check(seed=11):
    con = register_layers(connect())
    first, last = datetime.strptime(T0, "%Y-%m-%dT%H:%M:%SZ"), data_end()
    con.execute(f"CREATE OR REPLACE TABLE _t AS SELECT t AS t_utc FROM generate_series(TIMESTAMP '{first}', TIMESTAMP '{last}', INTERVAL 1 HOUR) g(t)")
    f = features(con, "_t").to_pylist()
    print(f"hours {len(f)} ({first:%Y-%m-%dT%H}Z..{last:%Y-%m-%dT%H}Z), unique {len({r['t_utc'] for r in f}) == len(f)}, "
          f"nulls {sum(v is None for r in f for v in r.values())}")
    for c in COLS:
        v = [r[c] for r in f]
        print(f"  {c}: min {min(v)}, max {max(v)}, mean {sum(v) / len(v):.2f}")
    points = _arrow(con.execute(f"SELECT * FROM {POINTS}")).to_pylist()
    days = _arrow(con.execute(f"SELECT * FROM {DAYS}")).to_pylist()
    bad = [r["t_utc"] for r in f if {c: r[c] for c in COLS} != _py_features(points, days, r["t_utc"])]
    print(f"plain-Python recomputation differs in {len(bad)} hours {bad[:3]}")
    ok = not bad and all(v is not None for r in f for v in r.values())
    rnd = random.Random(seed)
    for t in sorted(rnd.sample([r["t_utc"] for r in f], 3)):
        c2 = connect()
        for name, sql
```

... ще 20 рядків

</details>

**Bash**: Apply the rf\_strikes fixes and run its features check

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("src/airalerts/silver/rf_strikes.py")
s = p.read_text()
reps = [
("""  COALESCE((SELECT sum(intercepted) FROM strike_days d WHERE d.country = 'RU'
            AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc), 0)::INTEGER AS rf_drones_intercepted_1d,
  COALESCE((SELECT sum(missiles_max) FROM strike_days d WHERE d.country = 'UA'
            AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc), 0)::INTEGER AS ua_missiles_launched_1d,""",
"""  COALESCE((SELECT sum(drones_intercepted) FROM strike_days d WHERE d.country = 'RU'
            AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc), 0)::INTEGER AS rf_drones_intercepted_1d,
  (SELECT sum(missiles_max) FROM strike_days d WHERE d.country = 'UA'
   AND d.available_at >= t.t_utc - INTERVAL 24 HOUR AND d.available_at < t.t_utc)::INTEGER AS ua_missiles_launched_1d,"""),
("""    rf_drones_intercepted_1d: drones the Russian MoD said it intercepted on the newest known day; ua_missiles_launched_1d,
    ua_drones_launched_1d: missiles and drones launched at Ukraine on the newest known day (Air Force, max of the range);""",
"""    rf_drones_intercepted_1d: drones (without missiles) the Russian MoD said it intercepted on the newest known day;
    ua_missiles_launched_1d, ua_drones_launched_1d: missiles and drones launched at Ukraine on the newest known day (Air Force, max
    of the range);
... ще 1362 символів
```

<details><summary>результат: 17 рядків</summary>

```
ok
hours 3924 (2026-04-30T21Z..2026-10-11T08Z), unique True, nulls 1114
  rf_points_1d: min 0, max 19, mean 7.97, null 0
  rf_points_3d: min 1, max 52, mean 23.68, null 0
  rf_regions_3d: min 1, max 23, mean 12.20, null 0
  rf_energy_1d: min 0, max 7, mean 2.01, null 0
  rf_energy_3d: min 0, max 16, mean 5.95, null 0
  rf_moscow_3d: min 0, max 1, mean 0.87, null 0
  rf_drones_intercepted_1d: min 65, max 1222, mean 477.42, null 0
  ua_missiles_launched_1d: min 0, max 90, mean 12.72, null 1114
  ua_drones_launched_1d: min 76, max 892, mean 255.79, null 0
  hours_since_rf_energy: min 1.0, max 120.0, mean 18.24, null 0
plain-Python recomputation differs in 0 hours []
ASOF t=2026-07-17T01Z identical to the full computation: True
ASOF t=2026-08-04T09Z identical to the full computation: True
ASOF t=2026-09-25T15Z identical to the full computation: True
FEATURES CHECK PASS
```

</details>

**Bash**: Commit rf fix, rebuild gold and the DuckDB views

```
git add src/airalerts/silver/rf_strikes.py && git commit -q -m "Keep unknown missile launches as NULL and count only drones intercepted

ua_missiles_launched_1d was 0 on the 55 days the site has no missile
figure, the same as a real 0; rf_drones_intercepted_1d summed drones and
missiles. Found by the audit of 2026-10-11.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git log --oneline -1 && choom -n 500 -- .venv/bin/python -I -m airalerts.gold.kyiv_hourly 2>&1 | grep -vE "^\s{2}[a-z_0-9]+ +(int|double|bool|timestamp)" | head -20 && .venv/bin/python -I -m airalerts.db | tail -1
```

<details><summary>результат: 22 рядки</summary>

```
4c4d0bb Keep unknown missile launches as NULL and count only drones intercepted
built /home/ye/PROJECTS/ai-school/airalers/data/gold/kyiv_hourly.parquet: 3909 rows, 52 columns, T0 2026-04-30T21:00:00Z, cutoff 2026-10-10T17:00:00Z (the search looked for the last accepted hour up to the current hour 2026-10-11T09:00:00Z)
the hour after the cutoff, 2026-10-10T18:00:00Z, is refused by:
  alerts: t_utc 2026-10-10 18:00:00 is after the end of the VA_Kyiv data 2026-10-10T17:11:31Z
  threat_hourly: t_utc 2026-10-10 18:00:00 is after the hour after the last labelled hour 2026-10-10T17:00:00Z (label_end 2026-10-10T17:11:14Z)
file /home/ye/PROJECTS/ai-school/airalers/data/gold/kyiv_hourly.parquet: rows 3909, columns 52, T0 2026-04-30T21:00:00Z, cutoff 2026-10-10T17:00:00Z, hours from T0 to cutoff inclusive 3909
t_utc first 2026-04-30T21:00:00Z, last 2026-10-10T17:00:00Z, rows = hours True, unique True, continuous (every step 1 h) True
y_strike_3h: labelled rows 3906, true 138, false 3768, null 3 at ['2026-10-10T15:00:00Z', '2026-10-10T16:00:00Z', '2026-10-10T17:00:00Z']
y_strike_3h base rate = true / labelled = 138/3906 = 0.0353
strike hours (kyiv_threat_hourly.missile_strike) from T0: 62 of 3908 hours of the table
null share per column: column, type, nulls, share
5 random rows (seed 2026, row index [487, 1308, 2058, 2096, 3896]), every column:
  t_utc                    2026-05-21T04:00:00Z 2026-06-24T09:00:00Z 2026-07-25T15:00:00Z 2026-07-27T05:00:00Z 2026-10-10T05:00:00Z
  hour_kyiv                                   7                   12                   18                    8                    8
  dow_kyiv                                    3                    2                    5                    0                    5
  alert_active                            False                False                False                False                False
  alert_active_min                            0                    0                    0                    0                    0
  alerts_started_3h                           0                    0                    0                    1                    1
  alerts_started_6h                           0                    0                    0                    1                    2
  alerts_started_24h                          0                    2                    3                    1                   11
  alert_minutes_24h                           0              33.6167                   94              8.88333               754.25
[('astro_hourly',), ('calendar_dates',), ('kyiv_alerts',), ('kyiv_hourly',), ('kyiv_threat_hourly',), ('kyiv_threat_posts',), ('political_events',), ('prep_signal_events',), ('strike_days',), ('strike_points',), ('tg_posts',), ('weather_runs',)]
```

</details>

**Bash**: Run the leak test and diff the new gold against the old

```
.venv/bin/python -I -m airalerts.gold.kyiv_hourly report 2>&1 | grep -E "ua_missiles|y_strike" ; choom -n 500 -- .venv/bin/python -I -m unittest discover -s tests -v 2>&1 | tail -12; .venv/bin/python -I /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/weather_check.py | tail -1; .venv/bin/python -I -c "
import pyarrow.parquet as pq
S='/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/backup_before_fix/kyiv_hourly.parquet'
a = pq.read_table(S).to_pylist(); b = pq.read_table('data/gold/kyiv_hourly.parquet').to_pylist()
from collections import Counter
c = Counter(k for x, y in zip(a, b) for k in x if x[k] != y[k])
print('gold columns changed vs before the fixes (rows):', dict(c))
"
```

<details><summary>результат: 20 рядків</summary>

```
y_strike_3h: labelled rows 3906, true 138, false 3768, null 3 at ['2026-10-10T15:00:00Z', '2026-10-10T16:00:00Z', '2026-10-10T17:00:00Z']
y_strike_3h base rate = true / labelled = 138/3906 = 0.0353
  ua_missiles_launched_1d  int32               1114 0.284983
  y_strike_3h              bool                   3 0.000767
  ua_missiles_launched_1d                     2                    1                    7                    3                   75
  y_strike_3h                             False                False                False                False                False
test_05_label_is_a_strike_in_the_next_3_hours (test_no_leakage.NoLeakage.test_05_label_is_a_strike_in_the_next_3_hours) ... ok
test_06_no_feature_column_is_the_label (test_no_leakage.NoLeakage.test_06_no_feature_column_is_the_label) ... ok
test_07_labels_is_not_called_by_any_features (test_no_leakage.NoLeakage.test_07_labels_is_not_called_by_any_features) ... ok

----------------------------------------------------------------------
Ran 7 tests in 10.087s

OK

shape: 3909 rows, 52 columns, T0 2026-04-30T21:00:00Z, cutoff 2026-10-10T17:00:00Z

ASOF: 50 random t (seed 20261011) from 2026-05-01T11:00:00Z to 2026-10-09T19:00:00Z, 8 modules, 2400 feature values compared with the gold rows, differences 0; rows hidden by the ASOF views in total 6762423
lead hours of the forecast used: min 9.0 max 22.0
gold columns changed vs before the fixes (rows): {'ua_missiles_launched_1d': 1114, 's1_takeoff_6h': 12, 's1_takeoff_24h': 48, 'hours_since_s1': 20, 'strikes_7d': 2149, 'strikes_14d': 2895, 'hours_since_strike': 1231, 'y_strike_3h': 13, 'rf_drones_intercepted_1d': 240}
```

</details>

**Bash**: Commit gold and find stale numbers in the docs

```
git add data/gold/kyiv_hourly.parquet && git commit -q -m "Rebuild gold after the audit fixes of the label, signals and RF strikes

y_strike_3h true 151 -> 138 of 3906; leak test 7 OK.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git log --oneline -1 && grep -rn -E "151|\b77\b|3755|0\.0387|3\.9%|9363|9 363|intercepted|УТС|UTC day|день UTC|доба UTC|33 з 35|мітка тут права|Мітка тут права|295 годин|0\.0346" docs/ src/airalerts/silver/rf_strikes.py | grep -v "^docs/ASSIGNMENT" | cut -c1-220
```

<details><summary>результат: 56 рядків</summary>

```
024645e Rebuild gold after the audit fixes of the label, signals and RF strikes
docs/HANDOFF.md:14:| gold | `kyiv_hourly`: 3909 годин 2026-04-30T21:00Z..2026-10-10T17:00Z, 52 колонки (`t_utc`, 50 ознак, ціль), `y_strike_3h` true 151 з 3906 (3.9%), null лише в 3 остан�
docs/HANDOFF.md:23:| 1. Мітка без еталону, 297 годин «regex без мітки» ніхто не читав | перевірено трьома незалежними джерелами і читан�
docs/HANDOFF.md:41:| `prep_signal_events` | перший пост події | ховає колонки, відомі лише після останнього поста | правки постів (514 з 9363 поді
docs/HISTORY.md:39:| Мітка S3 | Jev на кожен пост, правило години | S3b версія 1: 142 години, 4 з 10 у вибірці хибні (дрони, ранкові звіти) → су
docs/HISTORY.md:85:| 2026-10-10T19:57Z | 14 каналів розширено до 2026-04-16T21:00Z (range mode, без нових постів зверху): kyiv_airdef +350, AerisRimor +377, truexakyiv +282, war_moni
docs/HISTORY.md:93:| 2026-10-10T20:42Z | S4 зібрано (9363 події, $0.75); МіГ-31К 2026-09-17 має 5 каналів, а не 4: StrategicaviationT теж кандидат, оркестратор прий�
docs/HISTORY.md:99:| 2026-10-10T21:50Z | S3b мітка | перевірено з 2 спроби: правило години суворіше (загроза p >= 0.8 з 3 каналів за 90 хв, оригіналь
docs/HISTORY.md:102:| 2026-10-10T22:18Z | FINAL gold `kyiv_hourly`: 3909 рядків, 48 колонок, зріз 2026-10-10T17:00Z, база `y_strike_3h` 0.0387; тест витоку 50 t, 2200 значень, 0 ро
docs/data/VERIFICATION.md:3:Стан на 2026-10-11, gold `data/gold/kyiv_hourly.parquet`: 3909 годин (2026-04-30T21:00Z..2026-10-10T17:00Z), 50 ознак (з годиною і днем тижня) і ціль `y_
docs/data/VERIFICATION.md:31:| dronestrikemap | ракети, запущені по Україні в той самий день UTC | 32 з 35 дат мітки |
docs/data/VERIFICATION.md:34:Результат (`data/verification/label_compare.txt`): дат мітки 35 (77 годин). 33 підтверджує V1 або V2. Дві інші (2026-06-18 і 2026-08-27) обидв
docs/data/VERIFICATION.md:38:295 годин, де простий regex PARSING 2 (правила A, B) каже «удар», а мітка ні (розділ 3 `label_compare.txt`): 41 у межах 3 год від го
docs/data/VERIFICATION.md:68:- Перевірка: якорі користувача (день народження Путіна 4.83, День Незалежності 5.00, День Перемоги 4.77, День Ко
docs/data/VERIFICATION.md:87:- Ризик: пости зібрано з t.me/s 2026-10-10. Видалені до того пости відсутні; відредагований пост збережено в оста�
docs/data/silver/tg_posts.md:84:5. Класи: kyiv_airdef/75885 має missile_threat (і toward_kyiv); vitaliy_klitschko/7775 має impact_damage, `rx_kyiv_city` і `rx_evidence` true; VA_Kyiv/21514 має missile_thr
docs/data/silver/kyiv_alerts.md:85:   - ASOF на 3 випадкових годинах всередині тривог (seed 20261010), одна з першого тижня після T0 (до 2026-05-07T21:00Z), дв�
docs/data/silver/prep_signal_events.md:45:Текст поста з `edited = true` міг отримати доповнення після `published_at` (PARSING 0.1). Подій, чий перший пост зміне
docs/data/silver/prep_signal_events.md:79:3. Подій 9363. Усього подій і постів: S1 takeoff 384 і 555, S1 relocation 69 і 75, S2 airborne 48 і 178, S2 all_clear 41 і 90, S4
```

... ще 37 рядків

</details>

**Bash**: Run the label report to get the new agreement numbers

```
S=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad && sed -n 932,990p src/airalerts/silver/threat_hourly.py | grep -n "open\|write\|out" | head; .venv/bin/python -I -m airalerts.silver.threat_hourly report --out $S/th_report.txt 2>&1 | head -30
```

<details><summary>результат: 21 рядок</summary>

```
20:def report(out, log=print):
22:    texts (written to `out`): 15 hours with a strike label and neither A nor B (most evidence posts first) and 15 hours with A or B
label_end 2026-10-10T17:11:14Z
confusion of missile_strike with the regex rules, all hours, 4244 hours; cells: both | strike only | rule only | neither
  rx_rule_a: 48 | 14 | 284 | 3898
  rx_rule_b: 47 | 15 | 63 | 4119
  A or B: 56 | 6 | 311 | 3871
confusion of missile_strike with the regex rules, hours from T0 2026-04-30T21:00:00Z, 3908 hours; cells: both | strike only | rule only | neither
  rx_rule_a: 48 | 14 | 282 | 3564
  rx_rule_b: 47 | 15 | 62 | 3784
  A or B: 56 | 6 | 308 | 3538
monthly counts of hours (UTC month): month | hours | missile_strike | missile_threat | drone_threat | ballistic
  2026-04 | 339 | 0 | 14 | 19 | 6
  2026-05 | 744 | 7 | 64 | 62 | 34
  2026-06 | 720 | 12 | 57 | 47 | 33
  2026-07 | 744 | 19 | 84 | 65 | 60
  2026-08 | 744 | 13 | 92 | 145 | 52
  2026-09 | 720 | 8 | 89 | 359 | 39
  2026-10 | 233 | 3 | 25 | 101 | 11
  all | 4244 | 62 | 425 | 798 | 235
disagreements: 6 hours strike without A or B, 311 hours A or B without strike; 30 largest with texts written to the --out file
```

</details>

**Bash**: Read the stale parts of the label doc

```
sed -n 25,45p docs/data/silver/kyiv_threat_hourly.md; echo ......; sed -n 120,140p docs/data/silver/kyiv_threat_hourly.md; echo ......; sed -n 170,179p docs/data/silver/kyiv_threat_hourly.md
```

<details><summary>результат: 54 рядки</summary>

```
Година `missile_strike` = true, коли є хоч один пост-доказ: оригінальний пост (`originals`), що йде після ракетної тривоги (`fresh`) і має `p_strike` >= 0.7 (`RULE["strike"]`, ключ `one`). Інших умов немає.

- `fresh`: за 90 хв до поста (`FRESH_MINUTES`; годину h-1 теж читаємо, вікно не сягає раніше за її початок, тож тривога лише в останні до 30 хв години h-2 не враховується; для першої години даних попередньої години немає; сам пост враховується) пости з `p_threat` >= 0.8 (`THREAT_GATE`) прийшли щонайменше з 3 різних каналів із 7 (`THREAT_CHANNELS`). Або пост сам і тривога, і звіт про удар: `p_threat` >= 0.8 і `p_strike` >= 0.7 (`SELF_STRIKE`): так 2026-08-16T06 стала ударом лише через одну умову, тривогу ("Ракета на Київ.", `p_threat` 0.91) дав один канал, і він же `p_strike` 0.72 (truexakyiv/82393). Фільтр прибирає звіти про наслідки через години після атаки, загальні попередження одного каналу і години лише з дронами. Правила A і B з PARSING 2 цього не вміють.
- `originals`: репости (`forwarded_from` не порожнє) не рахуються. КМВА репостить зведення президента, ДСНС і ДТЕК.

Інші три мітки (`missile_threat`, `drone_threat`, `ballistic`) без `fresh` і `originals` (репост попередження AerisRimor з kpszsu може бути єдиним джерелом у 7 каналах). Година true, коли є пост з ймовірністю >= 0.8 (`one`), або пост офіційного каналу (VA_Kyiv, vitaliy_klitschko) >= 0.5 (`official`), або оригінальні пости щонайменше 2 різних каналів, у кожного >= 0.5 (`two`).

Чому так. Гейт 0.5 від одного поста пропускав заперечення ("Бандеролі не спостерігаються"), коментарі і нічні зведення, тож години дронів і звіти про наслідки ставали ударом. Умови `official` і `two` для удару прибрано: з новим гейтом `official` додав би хибну годину 2026-07-13T22. Пороги 0.8, 3 канали і 0.7 підібрано за годинами, прочитаними вручну, а не за еталоном: `READ_TRUE` (10 годин) і `READ_FALSE` (37) у коді, їх перевіряє `selftest`. Пілот (`pilot`, 93 години, `pilot_hours()`, зерно 20261010) і вибір правила: Перевірка та [HISTORY.md](../../HISTORY.md).

Повний діапазон (`report`): 77 годин `missile_strike` з 4244; A або B істинні в 367 годинах (69 збігаються з міткою, 298 без мітки), 8 годин мітки без A і B (2026-06-25T17, 2026-06-27T22, 2026-06-27T23, 2026-07-01T22, 2026-07-30T00, 2026-08-08T01, 2026-09-01T00 і виправлена вручну 2026-09-18T16). Перші сім за текстами це вибухи чи влучання в Києві після тривоги балістики чи крилатих ракет (прочитано вручну, не еталон).

## Виправлення вручну

Зовнішня перевірка 2026-10-11 ([VERIFICATION.md](../VERIFICATION.md)) знайшла серед 33 ночей удару одну пропущену і одну зайву годину. Жоден поріг правила не виправляє їх без нових сумнівних годин (`p_strike >= 0.5` додає ще 10), тож `build` задає їх зі списку `CORRECTIONS` і ставить `corrected`. Після цього годин удару 77, `y_strike_3h` true 151:
- 2026-09-18T16: удар. Циркони на Київ о 16:25Z, Труха «Гучно!» о 16:29Z (`p_strike` 0.56, нижче порога 0.7), Кличко о 16:32Z «У столиці працюють сили ППО.
```

... ще 39 рядків

</details>

**Bash**: Regenerate the label comparison evidence and show the diff

```
.venv/bin/python -I scripts/verify/label_check.py 2>&1 | tail -3; git diff --stat data/verification/; git diff data/verification/label_compare.txt | head -80
```

<details><summary>результат: 85 рядків</summary>

```
one=0.6: 79 hours, added ['2026-09-19T07', '2026-09-30T00'], removed []
one=0.5: 88 hours, added ['2026-05-14T04', '2026-06-02T10', '2026-06-21T00', '2026-07-02T02', '2026-07-13T22', '2026-07-24T09', '2026-08-20T02', '2026-08-28T20', '2026-09-18T16', '2026-09-19T07', '2026-09-30T00'], removed []
one=0.7 or official>=0.5: 79 hours, added ['2026-07-13T22', '2026-09-30T00'], removed []
 data/verification/label_compare.txt | 40 ++++++++++++++++++-------------------
 1 file changed, 20 insertions(+), 20 deletions(-)
diff --git a/data/verification/label_compare.txt b/data/verification/label_compare.txt
index f21a828..83c10e7 100644
--- a/data/verification/label_compare.txt
+++ b/data/verification/label_compare.txt
@@ -1,62 +1,62 @@
 1. NIGHTS: date | label hours (Kyiv) | V1 | V2
-label strike hours 77, Kyiv dates 35; corrected hours ['2026-08-27T16', '2026-09-18T16']
+label strike hours 62, Kyiv dates 35; corrected hours ['2026-05-14T01', '2026-06-02T05', '2026-07-02T01', '2026-07-06T01', '2026-07-11T01', '2026-07-19T00', '2026-08-08T01', '2026-08-16T00', '2026-08-19T23', '2026-08-27T01', '2026-08-27T16', '2026-09-01T00', '2026-09-17T00', '2026-09-18T16', '2026-09-23T23', '2026-09-28T23', '2026-10-07T01']
 2026-05-02 | - | . | ?
 2026-05-03 | - | ? | .
-2026-05-14 | 03,04,06 | M | M
+2026-05-14 | 03,06 | M | M
 2026-05-24 | 01,02,03,04,05 | M | M
-2026-06-02 | 02,03,04,07,08 | M | M
+2026-06-02 | 02,03,04,07 | M | M
 2026-06-15 | 01,02,03 | M | M
 2026-06-18 | 01 | . | .
 2026-06-25 | 20,21 | . | ?
 2026-06-26 | - | M | .
 2026-06-28 | 01,02 | ? | M
-2026-07-02 | 01,02,03,04 | M | M
-2026-07-06 | 01,02,03,04 | M | M
+2026-07-02 | 01,02,03 | M | M
+2026-07-06 | 01,02,03 | M | M
 2026-07-08 | 00 | M | M
-2026-07-11 | 03,04 | M | M
+2026-07-11 | 03 | M | M
 2026-07-14 | 00 | M | M
 2026-07-16 | 00,01 | M | M
-2026-07-19 | 01,02,03 | M | M
+2026-07-19 | 01,02 | M | M
 2026-07-24 | 11 | M | ?
 2026-07-26 | 00 | ? | M
 2026-07-30 | 01,03 | M | M
 2026-08-01 | 01,02,03 | M | M
```

... ще 45 рядків

</details>

**Bash**: Update the label doc with the new numbers and corrections

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/data/silver/kyiv_threat_hourly.md")
s = p.read_text()
reps = [
("`READ_TRUE` (10 годин) і `READ_FALSE` (37)", "`READ_TRUE` (9 годин) і `READ_FALSE` (38)"),
("Повний діапазон (`report`): 77 годин `missile_strike` з 4244; A або B істинні в 367 годинах (69 збігаються з міткою, 298 без мітки), 8 годин мітки без A і B (2026-06-25T17, 2026-06-27T22, 2026-06-27T23, 2026-07-01T22, 2026-07-30T00, 2026-08-08T01, 2026-09-01T00 і виправлена вручну 2026-09-18T16). Перші сім за текстами це вибухи чи влучання в Києві після тривоги балістики чи крилатих ракет (прочитано вручну, не еталон).",
 "Повний діапазон (`report`): 62 години `missile_strike` з 4244; A або B істинні в 367 годинах (56 збігаються з міткою, 311 без мітки), 6 годин мітки без A і B (2026-06-25T17, 2026-06-27T22, 2026-06-27T23, 2026-07-01T22, 2026-07-30T00 і виправлена вручну 2026-09-18T16). Перші чотири за текстами це вибухи чи влучання в Києві після тривоги балістики чи крилатих ракет; 2026-07-30T00 неясна: один пост «Вибухи у Києві.» без типу зброї (прочитано вручну, не еталон)."),
("Зовнішня перевірка 2026-10-11 ([VERIFICATION.md](../VERIFICATION.md)) знайшла серед 33 ночей удару одну пропущену і одну зайву годину. Жоден поріг правила не виправляє їх без нових сумнівних годин (`p_strike >= 0.5` додає ще 10), тож `build` задає їх зі списку `CORRECTIONS` і ставить `corrected`. Після цього годин удару 77, `y_strike_3h` true 151:",
 "Зовнішня перевірка
... ще 3102 символів
```

<details><summary>результат: 3 рядки</summary>

```
ok
38:Зовнішня перевірка 2026-10-11 ([VERIFICATION.md](../VERIFICATION.md)) знайшла серед 33 ночей удару одну пропу
111:`labels(con, t_table, horizon_h=3)` повертає `t_utc` і `y_strike_3h` (BOOLEAN): true, коли хоч одна година з [t, t+3 год) ма
```

</details>

**Bash**: Get new signal totals and the stale lines of the signals doc

```
sed -n 111p docs/data/silver/kyiv_threat_hourly.md; grep -n "9363\|S1 takeoff 384\|edited\|змінен" docs/data/silver/prep_signal_events.md | cut -c1-400; .venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
print(con.execute('SELECT signal, subtype, count(*), sum(n_posts) FROM prep_signal_events GROUP BY ALL ORDER BY ALL').fetchall())
print(con.execute('SELECT count(*) FROM prep_signal_events').fetchone())
"
```

<details><summary>результат: 5 рядків</summary>

```
`labels(con, t_table, horizon_h=3)` повертає `t_utc` і `y_strike_3h` (BOOLEAN): true, коли хоч одна година з [t, t+3 год) має `missile_strike`. Null, коли t + 3 год пізніше за `label_end` (або t раніше за першу годину таблиці): зараз це t = 2026-10-10T15:00Z, 16:00Z, 17:00Z. Частка true на t від T0 з міткою: 0.0387 (151 з 3906).
45:Текст поста з `edited = true` міг отримати доповнення після `published_at` (PARSING 0.1). Подій, чий перший пост змінено: 514 з 9363 (S1 152 з 453, S2 28 з 89, S4 334 з 8821).
79:3. Подій 9363. Усього подій і постів: S1 takeoff 384 і 555, S1 relocation 69 і 75, S2 airborne 48 і 178, S2 all_clear 41 і 90, S4 launch 8821 і 30735. По місяцях (S1 takeoff / S1 relocation / S2 airborne / S2 all_clear / S4 launch; квітень з 16-го, жовтень до 10-го): 2026-04 44 / 5 / 4 / 3 / 507; 2026-05 72 / 17 / 18 / 19 / 1188; 2026-06
[('S1', 'relocation', 68, 74), ('S1', 'takeoff', 383, 550), ('S2', 'airborne', 48, 178), ('S2', 'all_clear', 41, 90), ('S4', 'launch', 8821, 30734)]
(9361,)
```

</details>

**Bash**: Compute monthly signal counts and edited first posts

```
sed -n 40,50p docs/data/silver/prep_signal_events.md; sed -n 79p docs/data/silver/prep_signal_events.md; .venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
for r in con.execute(\"SELECT strftime(first_post_at,'%Y-%m') m, count(*) FILTER (WHERE signal='S1' AND subtype='takeoff'), count(*) FILTER (WHERE signal='S1' AND subtype='relocation'), count(*) FILTER (WHERE signal='S2' AND subtype='airborne'), count(*) FILTER (WHERE signal='S2' AND subtype='all_clear'), count(*) FILTER (WHERE signal='S4') FROM prep_signal_events GROUP BY 1 ORDER BY 1\").fetchall(): print(r)
print(con.execute(\"SELECT e.signal, count(*), count(*) FILTER (WHERE t.edited) FROM prep_signal_events e JOIN tg_posts t ON t.channel = split_part(e.post_refs[1],'/',1) AND t.post_id = CAST(split_part(e.post_refs[1],'/',2) AS BIGINT) GROUP BY 1 ORDER BY 1\").fetchall())
"
```

<details><summary>результат: 19 рядків</summary>

```
## Час доступності

`available_at = first_post_at`: подія відома з першого посту. Решта колонок (`last_post_at`, `n_channels`, `n_posts`, `aircraft_n`, `toward_kyiv`, `post_refs`, `p_actual`, `p_subtype`) стає відомою після останнього посту. `ASOF["prep_signal_events"]` бере рядки з `available_at < {t}` і ховає ці колонки (NULL), якщо `last_post_at >= {t}`. Ознаки gold беруть лише `signal`, `subtype`, `available_at`.

Текст поста з `edited = true` міг отримати доповнення після `published_at` (PARSING 0.1). Подій, чий перший пост змінено: 514 з 9363 (S1 152 з 453, S2 28 з 89, S4 334 з 8821).

## Ознаки для gold

`features(con, t_table)`: `con` має view `prep_signal_events`; повертає `t_utc` і 5 колонок, рівно рядок на `t_utc`. Беруться лише події з `available_at < t_utc`.

3. Подій 9363. Усього подій і постів: S1 takeoff 384 і 555, S1 relocation 69 і 75, S2 airborne 48 і 178, S2 all_clear 41 і 90, S4 launch 8821 і 30735. По місяцях (S1 takeoff / S1 relocation / S2 airborne / S2 all_clear / S4 launch; квітень з 16-го, жовтень до 10-го): 2026-04 44 / 5 / 4 / 3 / 507; 2026-05 72 / 17 / 18 / 19 / 1188; 2026-06 59 / 15 / 11 / 8 / 1360; 2026-07 81 / 13 / 7 / 5 / 1484; 2026-08 70 / 7 / 3 / 3 / 1691; 2026-09 32 / 9 / 4 / 3 / 1935; 2026-10 26 / 3 / 1 / 0 / 656. 20 випадкових подій S1 (з 453) разом з постами і ймовірностями пише `check` у `<тека>/s1_sample_20.txt`; 30 випадкових відхилених постів S1 у `<тека>/s1_rejected_30.txt` (S1 кандидатів поза будь-якою подією 890 з 1520).
('2026-04', 44, 5, 4, 3, 507)
('2026-05', 71, 17, 18, 19, 1188)
('2026-06', 59, 14, 11, 8, 1360)
('2026-07', 81, 13, 7, 5, 1484)
('2026-08', 70, 7, 3, 3, 1691)
('2026-09', 32, 9, 4, 3, 1935)
('2026-10', 26, 3, 1, 0, 656)
[('S1', 451, 149), ('S2', 89, 28), ('S4', 8821, 334)]
```

</details>

**Bash**: Get S1 candidate and edited counts from the module check

```
S=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad && .venv/bin/python -I -c "
from airalerts import jev
def _b(*a, **k): raise RuntimeError('blocked')
jev._post = _b
from airalerts.silver import signals
signals.check('$S/signals_check')
" 2>&1 | grep -E "S1 candidates not|events whose first|DONE 1" -A0
```

<details><summary>результат: 3 рядки</summary>

```
DONE 1 (S2 events 2026-09-17 09:30..11:30 UTC):
S1 candidates not in any event: 896 of 1520; sample in s1_rejected_30.txt
events whose first post is edited (signal: edited of all): {'S1': '149 of 451', 'S2': '28 of 89', 'S4': '334 of 8821'} total 511 of 9361
```

</details>

**Bash**: Update the signals doc with the new rule and counts

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/data/silver/prep_signal_events.md")
s = p.read_text()
reps = [
("Текст поста з `edited = true` міг отримати доповнення після `published_at` (PARSING 0.1). Подій, чий перший пост змінено: 514 з 9363 (S1 152 з 453, S2 28 з 89, S4 334 з 8821).",
 "Текст поста з `edited = true` міг отримати доповнення після `published_at` (PARSING 0.1); часу правки bronze не має. Тому `written_later()` не пускає в події пост, чий текст точно написано пізніше: службовий пост «pinned» (Telegram показує текст закріпленого поста на час забору) і текст «станом на HH:MM» з київським часом на 5 хв..12 год пізніше за публікацію (AerisRimor переписує нічне зведення). Таких постів 37 серед 36582 кандидатів; без правила 4 події S1 починались на 1.3..5.7 год раніше, ніж їхній текст з'явився (аудит 2026-10-11). Інші правки датувати не можна: подій, чий перший пост змінено, 511 з 9361 (S1 149 з 451, S2 28 з 89, S4 334 з 8821).\n\nЩе один залишковий ризик: пости S4 Jev оцінює пачками до 8 у порядку часу, тож у state поста бувають пізніші пости; від пачки залежать 50 з 8821 подій S4 (аудит)."),
("3. Подій 9363. Усього подій і постів: S1 takeoff 384 і 555, S1 relocation 69 і 75, S2 airborne 48 і 178, S2 all_clear 41 і 90, S4 launch 8821 і 30735. По місяцях (S1 takeoff / S1 relocation / S2 airborne / S2 all_clear / S4 launch; квітень з 16-го, жовтень до 10-го): 2026-04 44 / 5 / 4 / 3 / 507; 2026-05 72 / 17 / 18 / 19 / 1188; 2026-06 59 / 15 / 11
... ще 986 символів
```

<details><summary>результат: 3 рядки</summary>

```
ok
87:- Jev помиляється в обидва боки: рахунок хибних і пропущених годин у [VERIFICATION.md](../VERIFICATION.md). Приклад хибної: поді
91:- `aircraft_n` для S1 є у 384 з 453 подій (від 1 до 10), для S2 у 42 з 89 (1 і 2), для S4 у 1715 з 8821 (до 50). Це лічба `S1_COUNT` і `S4_COUNT`, не пере
```

</details>

**Bash**: Check the remaining stale counts in the signals doc

```
sed -n 87p docs/data/silver/prep_signal_events.md | cut -c1-600; .venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
print(con.execute('SELECT signal, count(aircraft_n), count(*), min(aircraft_n), max(aircraft_n) FROM prep_signal_events GROUP BY 1 ORDER BY 1').fetchall())"
```

<details><summary>результат: 2 рядки</summary>

```
- Jev помиляється в обидва боки: рахунок хибних і пропущених годин у [VERIFICATION.md](../VERIFICATION.md). Приклад хибної: подія `[REDACTED: ключ]` це пост про супутникові знімки аеродрому (StrategicaviationT/31216), `p_actual` 0.81. У вибірці `s1_rejected_30.txt` відхилені зведення дня («За сьогодні відмічено», «Обстановка станом на»), оцінки ймовірності атаки і пости про по
[('S1', 382, 451, 1, 10), ('S2', 42, 89, 1, 2), ('S4', 1715, 8821, 1, 50)]
```

</details>

**Bash**: Fix aircraft count and read the RF strikes doc parts

```
sed -i 's/- `aircraft_n` для S1 є у 384 з 453 подій (від 1 до 10)/- `aircraft_n` для S1 є у 382 з 451 події (від 1 до 10)/' docs/data/silver/prep_signal_events.md && grep -c "382 з 451" docs/data/silver/prep_signal_events.md && sed -n 1,12p src/airalerts/silver/rf_strikes.py && sed -n 35,90p docs/data/silver/rf_strikes.md && sed -n 430,440p docs/PARSING.md
```

<details><summary>результат: 80 рядків</summary>

```
1
"""Silver rf_strikes: strikes on Russia and launches at Ukraine per day, from the dronestrikemap.com API. Two tables.

strike_points  one row per strike point of a day (country RU or UA): place, region, target summary, weapons, confidence,
               the articles behind it; flags is_energy, is_moscow, occupied (occupied Ukraine that the site files under RU).
strike_days    one row per (day, country): drones and missiles launched (min, max) and intercepted, from the site's daily totals
               (RU: Russian MoD briefings; UA: Ukrainian Air Force).
The site gives a day (UTC, checked against the MoD reports: the RU intercepted total of day d is the sum of the MoD reports
published on UTC day d) and no time of day, no publication time and no revision history. So a day is known only from
d + 1 day + 6 h (user decision 2026-10-11): available_at = d 00:00Z + 30 h. Bronze is one snapshot per fetch; the newest
snapshot is used. Gold: features(con, t_table). Documentation: docs/data/silver/rf_strikes.md

Run (from the project root):
| `available_at` | TIMESTAMP | `date` 00:00 UTC + 30 год |

`strike_days`: `date`, `country`, `launched_min`, `launched_max`, `intercepted`, `estimated` (сайт позначив оцінку), `drones_max`, `drones_intercepted`, `missiles_max`, `missiles_intercepted`, `basis` (перелік джерел підсумку), `available_at` (як вище).

Метадані Parquet обох таблиць: `snapshot`, `fetched_at`, `lag_hours`.

## Час доступності

На сайті є лише дата, немає години, часу публікації і історії змін. День сайту збігається з днем публікації звітів МО РФ: денна сума збитих дронів над Росією дорівнює сумі звітів МО РФ, опублікованих того ж дня, у 72 з 101 дня і відрізняється не більше ніж на 10% у 85 (`checks`, рядок нижче). Звіти МО виходять близько 05:30Z і 18:00Z, тож день UTC і день за Києвом дають ту саму звірку і їх не розрізнити. В обох випадках день d закінчується не пізніше d + 1 день 00:00Z. Рішення користувача 2026-10-11: день d відомий з d + 1 день + 6 год, `available_at = d 00:00Z + 30 год`. День, який на момент знімка ще не відомий, у таблицю не йде (2026-10-11 відкинуто). `ASOF`: `SELECT * FROM <таблиця> WHERE available_at < {t}`.

Залишковий ризик витоку: сайт міг дописати чи виправити старий день пізніше, а знімок бачить лише останній стан. Наступні знімки дадуть змогу це виміряти.

## Ознаки для gold

`features(con, t_table)`: рядок на кожен `t_utc`, лише рядки з `available_at < t_utc`. «День» = найновіший відомий день (`available_at` у `[t - 24 год, t)`), «три дні» = `[t - 72 год, t)`. Точки Росії беруться без окупованих територій України (`country = 'RU' AND NOT occupied`).

| колонка | тип | визначення |
|---|---|---|
| `rf_points_1d`, `rf_points_3d` | INTEGER | точок ударів по Росії за день і за три дні |
| `rf_regions_3d` | INTEGER | різних регіонів серед точок трьох днів |
| `rf_energy_1d`, `rf_energy_3d` | INTEGER | точок з `is_energy` |
| `rf_moscow_3d` | INTEGER | 1, якщо за три дні є точка з `is_moscow` |
|
```

... ще 44 рядки

</details>

### Claude, 13:00

Перш ніж писати в документ, що день України на сайті це доба ПС (15:00Z..15:00Z), а не UTC, дивлюсь доказ агента.

**Bash**: Read the day boundary and snapshot diff evidence

```
D=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/rf; tail -25 $D/step1b_window.out; head -30 $D/step2_diff.out
```

<details><summary>результат: 49 рядків</summary>

```
  2026-08-21T22Z: utc_day=08-21(3), kyiv_day=08-22(0), night_of_evening_date=08-21(3), AF_day=08-22(0)
  2026-08-31T23Z: utc_day=08-31(1), kyiv_day=09-01(14), night_of_evening_date=08-31(1), AF_day=09-01(14)
  2026-09-16T23Z: utc_day=09-16(None), kyiv_day=09-17(4), night_of_evening_date=09-16(None), AF_day=09-17(4)
  2026-09-18T16Z: utc_day=09-18(None), kyiv_day=09-18(None), night_of_evening_date=09-18(None), AF_day=09-19(4)
  2026-09-23T22Z: utc_day=09-23(None), kyiv_day=09-24(7), night_of_evening_date=09-23(None), AF_day=09-24(7)
  2026-09-28T22Z: utc_day=09-28(None), kyiv_day=09-29(3), night_of_evening_date=09-28(None), AF_day=09-29(3)
  2026-09-29T23Z: utc_day=09-29(3), kyiv_day=09-30(5), night_of_evening_date=09-29(3), AF_day=09-30(5)

leak count per convention: gold t where a strike hour h in [t, t+3h) is filed (by that convention) under a day already in gold's 1d window or earlier
  utc_day: 0
  kyiv_day: 0
  night_of_evening_date (18-09 Kyiv -> d): 0
  AF_day (18:00 Kyiv d-1 .. 18:00 Kyiv d -> d): 0

margin (AF_day convention): first gold t seeing the attack's day (d+31h) minus end of its last strike hour
  min 19 h, max 38 h; all > 0: True
  19 h: last strike hour 2026-10-10T11Z day 2026-10-10 gold ua_missiles_1d at d+31h = None site = 24
  22 h: last strike hour 2026-07-24T08Z day 2026-07-24 gold ua_missiles_1d at d+31h = 7 site = 7
  24 h: last strike hour 2026-08-16T06Z day 2026-08-16 gold ua_missiles_1d at d+31h = 3 site = 3
  25 h: last strike hour 2026-06-02T05Z day 2026-06-02 gold ua_missiles_1d at d+31h = 73 site = 73
  window-end margin: AF day d ends 18:00 Kyiv d = 15:00Z d (EEST); available_at d+30h = d+1 06:00Z -> 15 h after the window closes
  gold ua_missiles_1d at d+31h equals site missiles_max(d) for 34/34 attacks
  2026-08-21 UA by_weapon: {"drone": {"basis": "Ukrainian Air Force daily record; day total, 2 reporting windows", "estimated": false, "intercepted": 209, "max": 237, "min": 237}, "missile": {"basis": "Ukrainian Air Force daily record", "estimated": false, "intercepted": 3, "max": 3, "min": 3}}
  2026-08-22 UA by_weapon: {"drone": {"basis": "Ukrainian Air Force daily record; day total, 2 reporting windows", "estimated": false, "intercepted": 260, "max": 295, "min": 295}, "missile": {"basis": "Ukrainian Air Force daily record", "estimated": false, "intercepted": 0, "max": 0, "min": 0}}
  2026-08-23 UA by_weapon: {"drone": {"basis": "Ukrainian Air Force daily record; day total, 2 reporting windows", "estimated": false, "intercepted": 180, "max": 210, "min": 210}, "missile": {"basis": "Ukrainian Air Force daily record", "estimated": false, "intercepted": 3, "max": 8, "min": 8}}
snapshot1 20261011T083437Z: 184 requests, non-200 0, last 2026-10-11T08:38:54Z
snapshot2 20261011T093813Z: 184 requests, non-200 0, first 2026-10-11T09:38:14Z last 2026-10-11T09:42:31Z
URLs with different sha256: 5 of 184: ['day/2026-10-10', 'day/2026-10-11', 'sources', 'strikes', 'timeline']
meta days equal: True (803 vs 803)

timeline:
```

... ще 18 рядків

</details>

**Bash**: Update RF strikes doc, docstring and PARSING

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
edits = {
"src/airalerts/silver/rf_strikes.py": [
("""The site gives a day (UTC, checked against the MoD reports: the RU intercepted total of day d is the sum of the MoD reports
published on UTC day d) and no time of day, no publication time and no revision history. So a day is known only from""",
"""The site gives a day and no time of day, no publication time and no revision history. For RU the day is the UTC day of the MoD
reports (the RU intercepted total of day d is the sum of the MoD reports published on UTC day d); for UA it is the Air Force
reporting day, 18:00 Kyiv of d - 1 to 18:00 Kyiv of d (15:00Z to 15:00Z in summer; it files 33 of 34 Kyiv missile attacks,
the UTC day 25, audit of 2026-10-11). Both end by d + 1 day 00:00Z. So a day is known only from"""),
],
"docs/data/silver/rf_strikes.md": [
("Звіти МО виходять близько 05:30Z і 18:00Z, тож день UTC і день за Києвом дають ту саму звірку і їх не розрізнити. В обох випадках день d закінчується не пізніше d + 1 день 00:00Z.",
 "Звіти МО виходять близько 05:30Z і 18:00Z, тож день UTC і день за Києвом дають ту саму звірку і їх не розрізнити. День `UA` інший: це доба звіту Повітряних сил, 18:00 за Києвом d - 1 .. 18:00 d (15:00Z..15:00Z влітку): так сайт відносить 33 з 34 ракетних атак на Київ, день UTC лише 25 (аудит 2026-10-11). В обох випадках день d закінчується не пізніше d + 1 день 00:00Z; gold бачить атаку щонайменше через 19 год після її останньої години
... ще 2192 символів
```

<details><summary>результат: 3 рядки</summary>

```
ok
  rf_drones_intercepted_1d: min 65, max 1222, mean 477.42, null 0
FEATURES CHECK PASS
```

</details>

### Claude, 13:01

Тепер документ gold. Числа для таблиці «Перевірка» отримую тими самими командами, що в документі.

**Bash**: Rerun the gold doc check commands

```
.venv/bin/python -I -c "from airalerts.db import connect; from airalerts.paths import DB; print(connect(DB).execute('SELECT count(*), count(*) FILTER (WHERE y_strike_3h) FROM kyiv_hourly').fetchone())"; .venv/bin/python -I -c "from airalerts.db import connect; from airalerts.paths import DB; print(connect(DB).execute('SELECT min(t_utc) FILTER (WHERE y_strike_3h) FROM kyiv_hourly').fetchone()[0])"; .venv/bin/python -I -c "from airalerts.db import connect, register_layers; print(register_layers(connect()).execute('SELECT min(hour_utc) FROM kyiv_threat_hourly WHERE missile_strike').fetchone()[0])"; .venv/bin/python -I -c "import pyarrow.parquet as pq; print(pq.read_metadata('data/silver/prep_signal_events.parquet').metadata[b'data_until'].decode())"
```

<details><summary>результат: 4 рядки</summary>

```
(3909, 138)
2026-05-13 22:00:00
2026-05-14 00:00:00
2026-10-10T11:36:43Z
```

</details>

**Bash**: Update target and column lines of the gold doc

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/data/gold/kyiv_hourly.md"); s = p.read_text()
reps = [
("| `rf_drones_intercepted_1d` | int32 | `strike_days` | дронів, яких МО РФ заявило збитими за найновіший відомий день |",
 "| `rf_drones_intercepted_1d` | int32 | `strike_days` | дронів (без ракет), яких МО РФ заявило збитими за найновіший відомий день |"),
("| `ua_missiles_launched_1d` | int32 | `strike_days` | ракет, запущених по Україні за найновіший відомий день (Повітряні сили, верх діапазону) |",
 "| `ua_missiles_launched_1d` | int32 | `strike_days` | ракет, запущених по Україні за найновіший відомий день (Повітряні сили, верх діапазону); null, коли сайт не має числа ракет для цього дня |"),
("Рядків з міткою 3906: true 151, false 3755, база 151/3906 = 0.0387. Годин `missile_strike` у `kyiv_threat_hourly` від T0 77 (з 3908 годин таблиці від T0).",
 "Рядків з міткою 3906: true 138, false 3768, база 138/3906 = 0.0353. Годин `missile_strike` у `kyiv_threat_hourly` від T0 62 (з 3908 годин таблиці від T0), з них 17 виправлено вручну (`CORRECTIONS`, [kyiv_threat_hourly.md](../silver/kyiv_threat_hourly.md)). 138 рядків true дають 35 атак; у 46 з них удар був і в останні 3 години (атака вже йде), тож прогноз початку атаки варто оцінювати окремо."),
]
for a, b in reps:
    assert s.count(a) == 1, a[:70]
    s = s.replace(a, b)
p.write_text(s)
print("ok")
EOF
sed -n 98,101p docs/data/gold/kyiv_hourly.md; grep -n "151\|0.0387\|3755\|null 0\|Null лише\|null
... ще 50 символів
```

<details><summary>результат: 8 рядків</summary>

```
ok
## Null

Null лише в `y_strike_3h`: 3 з 3909, частка 0.000767. В інших 51 колонці null немає (частка 0.000000), зокрема в `wx_*`, `dark_share_3h` і `moon_illum`. Частки по колонках друкує `report` (блок `null share per column`).

100:Null лише в `y_strike_3h`: 3 з 3909, частка 0.000767. В інших 51 колонці null немає (частка 0.000000), зокрема в `wx_*`, `dark_share_3h` і `moon_illum`. Частки по колонках друкує 
134:| `.venv/bin/python -I -m airalerts.gold.kyiv_hourly report` | `rows 3909, columns 52`, `hours from T0 to cutoff inclusive 3909`, `rows = hours True, unique True, continuous (every step 1 h) True`; `labelled rows 3906, true 151, false 3755, null 
136:| `.venv/bin/python -I -c "from airalerts.db import connect; from airalerts.paths import DB; print(connect(DB).execute('SELECT count(*), count(*) FILTER (WHERE y_strike_3h) FROM kyiv_hourly').fetchone())"` | `(3909, 151)` |
```

</details>

**Bash**: Recompute attack and continuation counts on the new gold

```
.venv/bin/python -I /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/gold_shape.py; .venv/bin/python -I -c "
import pyarrow.parquet as pq
g = [r for r in pq.read_table('data/gold/kyiv_hourly.parquet').to_pylist() if r['y_strike_3h'] is not None]
runs, prev = 0, False
for r in g:
    if r['y_strike_3h'] and not prev: runs += 1
    prev = r['y_strike_3h']
print('runs of consecutive positive rows (whole range):', runs)"
```

<details><summary>результат: 7 рядків</summary>

```
month rows pos rate: {'2026-04': (3, 0, 0.0), '2026-05': (744, 13, 0.017), '2026-06': (720, 24, 0.033), '2026-07': (744, 42, 0.056), '2026-08': (744, 31, 0.042), '2026-09': (720, 20, 0.028), '2026-10': (231, 8, 0.035)}
positives 138 | strike in last 3h (continuation) 33 | alert active at t 58 | no recent strike, no alert, no threat in 6h (true onset with cold start) 32
last 14 days: rows 336, positive rows 14, positive runs (attacks) 4
last 28 days: rows 672, positive rows 23, positive runs (attacks) 7
last 42 days: rows 1008, positive rows 31, positive runs (attacks) 9
hour_kyiv of positive rows: [(0, 24), (1, 26), (2, 19), (3, 13), (4, 5), (5, 5), (6, 2), (7, 2), (8, 1), (9, 2), (10, 1), (11, 1), (12, 1), (13, 1), (14, 1), (17, 1), (18, 2), (19, 2), (20, 1), (21, 2), (22, 7), (23, 19)]
runs of consecutive positive rows (whole range): 35
```

</details>

**Bash**: Fix the gold doc null section and check outputs

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/data/gold/kyiv_hourly.md"); s = p.read_text()
reps = [
("138 рядків true дають 35 атак; у 46 з них удар був і в останні 3 години",
 "138 рядків true дають 35 серій поспіль (атак); у 33 з них удар був і в останні 3 години"),
("Null лише в `y_strike_3h`: 3 з 3909, частка 0.000767. В інших 51 колонці null немає (частка 0.000000), зокрема в `wx_*`, `dark_share_3h` і `moon_illum`.",
 "Null у двох колонках: `y_strike_3h` 3 з 3909 (частка 0.000767) і `ua_missiles_launched_1d` 1114 (0.284983: сайт не має числа ракет для 55 днів; модель має заповнити це сама, 0 тут означав би «ракет не було»). В інших 50 колонках null немає, зокрема в `wx_*`, `dark_share_3h` і `moon_illum`."),
("`labelled rows 3906, true 151, false 3755, null 3`", "`labelled rows 3906, true 138, false 3768, null 3`"),
("| `(3909, 151)` |", "| `(3909, 138)` |"),
]
for a, b in reps:
    assert s.count(a) == 1, a[:70]
    s = s.replace(a, b)
p.write_text(s)
EOF
grep -n "0.0387\|151\|77 of\|null лише\|Null лише\|null 3`" docs/data/gold/kyiv_hourly.md | cut -c1-300; sed -n 134p docs/data/gold/kyiv_hourly.md | cut -c250-700; grep -n "Тест на витік\|Пастки" docs/data/gold/kyiv_hourly.md
```

<details><summary>помилка, 2 рядки</summary>

```
Exit code 2
/bin/bash: eval: line 17: unexpected EOF while looking for matching ``'
```

</details>

**Bash**: Fix the gold doc null section and check outputs

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/data/gold/kyiv_hourly.md"); s = p.read_text()
reps = [
("138 рядків true дають 35 атак; у 46 з них удар був і в останні 3 години",
 "138 рядків true дають 35 серій поспіль (атак); у 33 з них удар був і в останні 3 години"),
("Null лише в `y_strike_3h`: 3 з 3909, частка 0.000767. В інших 51 колонці null немає (частка 0.000000), зокрема в `wx_*`, `dark_share_3h` і `moon_illum`.",
 "Null у двох колонках: `y_strike_3h` 3 з 3909 (частка 0.000767) і `ua_missiles_launched_1d` 1114 (0.284983: сайт не має числа ракет для 55 днів; модель має заповнити це сама, 0 тут означав би «ракет не було»). В інших 50 колонках null немає, зокрема в `wx_*`, `dark_share_3h` і `moon_illum`."),
("`labelled rows 3906, true 151, false 3755, null 3`", "`labelled rows 3906, true 138, false 3768, null 3`"),
("| `(3909, 151)` |", "| `(3909, 138)` |"),
]
for a, b in reps:
    assert s.count(a) == 1, a[:70]
    s = s.replace(a, b)
p.write_text(s)
print("ok")
EOF
grep -n -e "0.0387" -e "151" -e "77 of" -e "лише в" docs/data/gold/kyiv_hourly.md | cut -c1-200
```

<details><summary>результат: 4 рядки</summary>

```
Traceback (most recent call last):
  File "<stdin>", line 12, in <module>
AssertionError: 138 рядків true дають 35 атак; у 46 з них удар був і в останні 3 годин
134:| `.venv/bin/python -I -m airalerts.gold.kyiv_hourly report` | `rows 3909, columns 52`, `hours from T0 to cutoff inclusive 3909`, `rows = hours True, unique True, continuous (every step 1 h) True`
```

</details>

**Bash**: Show the current target and null section of the gold doc

```
sed -n 94,101p docs/data/gold/kyiv_hourly.md; git diff --stat
```

<details><summary>результат: 16 рядків</summary>

```
`y_strike_3h` = true, якщо хоч одна година з `[t, t + 3 год)` має `missile_strike` у `kyiv_threat_hourly`. Це єдина колонка, що дивиться вперед, і її рахує лише `labels()`. Null, коли t + 3 год пізніше за `label_end`: три останні рядки, 2026-10-10T15:00Z, 16:00Z, 17:00Z.

Рядків з міткою 3906: true 138, false 3768, база 138/3906 = 0.0353. Годин `missile_strike` у `kyiv_threat_hourly` від T0 62 (з 3908 годин таблиці від T0), з них 17 виправлено вручну (`CORRECTIONS`, [kyiv_threat_hourly.md](../silver/kyiv_threat_hourly.md)). 138 рядків true дають 35 серій поспіль (атак); у 33 з них удар був і в останні 3 години (атака вже йде), тож прогноз початку атаки варто оцінювати окремо. Перша така година 2026-05-14T00:00Z, до T0 жодної.

## Null

Null у двох колонках: `y_strike_3h` 3 з 3909 (частка 0.000767) і `ua_missiles_launched_1d` 1114 (0.284983: сайт не має числа ракет для 55 днів; модель має заповнити це сама, 0 тут означав би «ракет не було»). В інших 50 колонках null немає, зокрема в `wx_*`, `dark_share_3h` і `moon_illum`. Частки по колонках друкує `report` (блок `null share per column`).

 data/verification/label_compare.txt    | 40 +++++++++++++++++-----------------
 docs/PARSING.md                        |  2 +-
 docs/data/gold/kyiv_hourly.md          | 12 +++++-----
 docs/data/silver/kyiv_threat_hourly.md | 21 ++++++++++--------
 docs/data/silver/prep_signal_events.md |  8 ++++---
 docs/data/silver/rf_strikes.md         | 12 +++++-----
 src/airalerts/silver/rf_strikes.py     |  6 +++--
 7 files changed, 54 insertions(+), 47 deletions(-)
```

</details>

**Bash**: Reorder the gold doc sentence and map VERIFICATION sections

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/data/gold/kyiv_hourly.md"); s = p.read_text()
a = " 138 рядків true дають 35 серій поспіль (атак); у 33 з них удар був і в останні 3 години (атака вже йде), тож прогноз початку атаки варто оцінювати окремо. Перша така година 2026-05-14T00:00Z, до T0 жодної."
b = " Перша така година 2026-05-14T00:00Z, до T0 жодної. 138 рядків true дають 35 серій поспіль (атак); у 33 з них удар був і в останні 3 години (атака вже йде), тож прогноз початку атаки варто оцінювати окремо."
assert s.count(a) == 1
p.write_text(s.replace(a, b)); print("ok")
EOF
sed -n 20,60p docs/data/VERIFICATION.md | head -5; grep -n "^## \|^- Ризик\|^Чого тест" docs/data/VERIFICATION.md
```

<details><summary>результат: 26 рядків</summary>

```
ok
- Повторити: `.venv/bin/python -I -m airalerts.silver.alerts check` (ALL OK).
- Ризик: малий. Кінець тривоги відомий лише з відбою; `ASOF` ховає його до того моменту.

## Мітка удару (`kyiv_threat_hourly`, ціль `y_strike_3h`)

5:## Три рівні перевірки
11:## Витік
15:Чого тест не бачить: витоку всередині значення рядка. Так було з Вікіпедією в політичних подіях (текст з найновішої ревізії при часі з першої) і так може бути з відредагованими постами Telegram. Ці випадки нижче, кожен окремо.
17:## Тривоги в Києві (`kyiv_alerts`)
21:- Ризик: малий. Кінець тривоги відомий лише з відбою; `ASOF` ховає його до того моменту.
23:## Мітка удару (`kyiv_threat_hourly`, ціль `y_strike_3h`)
41:- Ризик:
46:## Сигнали підготовки (`prep_signal_events`)
58:- Ризик: S4 є в 94% годин, тож як «є чи немає» мало розрізняє; ознака `s4_drone_waves_6h` рахує 15-хвилинні серії постів, тобто інтенсивність повідомлень, а не фізичні хвилі.
60:## Погода і астрономія (`weather_runs`, `astro_hourly`)
64:- Ризик: малий. Прогноз це не спостереження.
66:## Символічні дати (`calendar_dates`)
70:- Ризик: оцінка Jev це середнє рівнів, зважене ймовірностями, тож середина шкали стиснута (дні родів військ рівно 2.0). Модель бачить лише «висока дата сьогодні чи завтра» і днів до неї, де це не заважає.
72:## Політичні події (`political_events`)
76:- Ризик: `kyiv_days_to_imp4` майже стала (київські події рівня 4 не анонсують заздалегідь); дописи Telegram у версії на момент забору.
78:## Удари по Росії і запуски по Україні (`strike_points`, `strike_days`)
82:- Ризик: сайт не має історії змін і часу публікації, описи цілей автоматичні. Затримка 30 год від початку дня UTC з запасом; кожен новий знімок bronze дасть змогу виміряти, чи сайт переписує старі дні.
84:## Telegram загалом (`tg_posts`)
87:- Ризик: пости зібрано з t.me/s 2026-10-10. Видалені до того пости відсутні; відредагований пост збережено в останній версії, тож текст міг змінитись після публікації. Частка редагованих: 514 з 9363 подій сигналів мають редагований перший пост; для мітки не міряли.
89:## Що лишається відкритим
```

</details>

**Bash**: Read the VERIFICATION sections to rewrite

```
sed -n 1,16p docs/data/VERIFICATION.md; sed -n 23,45p docs/data/VERIFICATION.md; sed -n 72,95p docs/data/VERIFICATION.md
```

<details><summary>результат: 62 рядки</summary>

```
# Чому даним можна довіряти

Стан на 2026-10-11, gold `data/gold/kyiv_hourly.parquet`: 3909 годин (2026-04-30T21:00Z..2026-10-10T17:00Z), 50 ознак (з годиною і днем тижня) і ціль `y_strike_3h` (true 151 з 3906, 3.9%). Тут на кожен тип даних: як перевіряли, що вийшло, що лишилось під ризиком і як повторити. Як дані зібрано: документи таблиць у `docs/data/`. Як ми до цього дійшли і від чого відмовились: [HISTORY.md](../HISTORY.md).

## Три рівні перевірки

1. **Самоперевірка таблиці.** Кожен модуль silver має команду, що звіряє таблицю з bronze, рахує ключі, null і доступність і порівнює ознаки з окремим розрахунком на Python (розділ «Перевірка» документа таблиці).
2. **Незалежний перевіряльник.** Кожен шматок silver будував один агент, а приймав інший, свіжий, лише з читанням: сам запускав перевірки, звіряв документ з даними, пробував вхід, що мусить впасти, читав 15-30 рядків вручну.
3. **Зовнішня перевірка** самої правди даних там, де її не дає код: мітка удару і сигнали підготовки (нижче, `scripts/verify/`, `data/verification/`).

## Витік

`tests/test_no_leakage.py`, 7 тестів, `.venv/bin/python -I -m unittest discover -s tests -v`. Головний: для 50 випадкових t (seed 20261011) з'єднання DuckDB бачить лише рядки silver, відомі до t (`ASOF` кожного модуля), і ознаки на ньому мають дорівнювати рядку gold. Результат: 2400 значень (8 модулів, 48 колонок), розбіжностей 0. Ще: ціль перераховується з silver, жодна ознака не дорівнює цілі, `labels()` не кличе жодна `features()`.

Чого тест не бачить: витоку всередині значення рядка. Так було з Вікіпедією в політичних подіях (текст з найновішої ревізії при часі з першої) і так може бути з відредагованими постами Telegram. Ці випадки нижче, кожен окремо.

## Мітка удару (`kyiv_threat_hourly`, ціль `y_strike_3h`)

Еталону немає: мітку дає Jev (ймовірності на кожен пост 7 київських каналів) і правило години в коді. Перевірено трьома незалежними джерелами і читанням постів.

| Джерело | Як | Результат |
|---|---|---|
| V1: офіційні підсумки в Telegram | агент Sonnet наосліп (без доступу до мітки) читав підсумки Повітряних сил, КМВА, Кличка, Зеленського, Генштабу, ОП | 27 днів `missile_city`, 10 `unclear_type` |
| V2: новини | агент Sonnet наосліп, лише вебпошук (Вікіпедія, Kyiv Independent, Укрправда тощо), покриття неповне | 30 днів `missile_city`, 5 `unclear_type` |
| dronestrikemap | ракети, запущені по Україні в той самий день UTC | 32 з 35 дат мітки |
| пости | оркестратор (Claude Opus) перечитав кожну ніч, де мітка і джерела розходяться | див. нижче |

Результат (`data/verification/label_compare.txt`): дат мітки 35 (77 годин). 33 підтверджує V1 або V2. Дві інші (2026-06-18 і 2026-08-27) обидва агенти пропустили або назвали дронами, а пости показують балістику над містом: «Київ, спуск балістики», «Вибухи Київ», «2-4 Іскандер-М по Києву», уламки на Подолі. Дати, які V1 чи V2 звуть ударом, а мітка ні: 2026-06-26 і 2026-09-19 (вечір попередньої дати, V1 відносить його до наступної), 2026-10-03 (Kyiv Post
```

... ще 34 рядки

</details>

**Bash**: Read the regenerated regex-only section

```
sed -n '/^3. REGEX/,/^4\./p' data/verification/label_compare.txt | head -20
```

<details><summary>результат: 11 рядків</summary>

```
3. REGEX-ONLY HOURS (rule A or B, no label): attack drones in the hour | within 3 h of a label strike hour | reference day: hours
total 308
  True | False | -: 116
  True | False | M: 108
  True | True | M: 47
  True | False | ?: 23
  False | False | M: 6
  False | False | -: 4
  True | True | ?: 2
  True | True | -: 2
4. THRESHOLDS (before CORRECTIONS)
```

</details>

**Bash**: Write the audit results into VERIFICATION.md

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/data/VERIFICATION.md"); s = p.read_text()
reps = [
("і ціль `y_strike_3h` (true 151 з 3906, 3.9%).", "і ціль `y_strike_3h` (true 138 з 3906, 3.5%)."),
("3. **Зовнішня перевірка** самої правди даних там, де її не дає код: мітка удару і сигнали підготовки (нижче, `scripts/verify/`, `data/verification/`).",
 "3. **Зовнішня перевірка** самої правди даних там, де її не дає код: мітка удару і сигнали підготовки (нижче, `scripts/verify/`, `data/verification/`).\n4. **Аудит перед моделюванням** (2026-10-11, нижче): усе заново, без довіри до документів і до коду модулів."),
("Чого тест не бачить: витоку всередині значення рядка. Так було з Вікіпедією в політичних подіях (текст з найновішої ревізії при часі з першої) і так може бути з відредагованими постами Telegram. Ці випадки нижче, кожен окремо.",
 """Чого тест не бачить: чи правильний сам `available_at`, і витоку всередині значення рядка. Тест порівнює `features()` на view `ASOF` з тими самими `features()` на повних даних, тож хибний `available_at` дає однаковий хибний результат в обох. Так було з Вікіпедією в політичних подіях (текст з найновішої ревізії при часі з першої) і з відредагованими постами в сигналах (аудит нижче). Ці випадки нижче, кожен окремо.

## Аудит перед моделюванням (2026-10-11)

Оркестратор (Claude Opus) і 5 агентів, лише читання, кожен свій модуль; кожну знахідку, що змінила дані, оркестратор перевірив сам. Скрипти й виходи аудиту не в
... ще 7471 символів
```

<details><summary>результат: 1 рядок</summary>

```
ok
```

</details>

**Bash**: Verify edited-post claims against the hour rule

```
.venv/bin/python -I - <<'EOF'
import re
from collections import defaultdict
from datetime import timedelta
from airalerts.db import connect, register_layers
from airalerts.silver import threat_hourly as th
con = register_layers(connect())
rows = con.execute("""SELECT k.hour_utc, k.channel, k.post_id, k.published_at, k.p_strike, k.p_threat, k.p_drone, k.p_ballistic,
  t.forwarded_from IS NULL AS is_original, t.text, t.edited FROM kyiv_threat_posts k JOIN tg_posts t USING (channel, post_id)""").fetchall()
keys = ["hour", "channel", "post_id", "published_at", "p_strike", "p_threat", "p_drone", "p_ballistic", "is_original", "text", "edited"]
posts = [dict(zip(keys, r)) for r in rows]
rx = re.compile(r"(?:станом на|UPD|Upd|upd|Оновлено)\s*(\d{1,2})[:.](\d{2})")
def late(p):
    m = rx.search(p["text"] or "")
    if not m or int(m[1]) > 23 or int(m[2]) > 59: return False
    k = p["published_at"] + timedelta(hours=3)
    st = k.replace(hour=int(m[1]), minute=int(m[2]), second=0)
    if st < k - timedelta(hours=12): st += timedelta(days=1)
    return st > k.replace(minute=0, second=0) + timedelta(hours=1) and (st - k) < timedelta(hours=12)
by = defaultdict(list)
for p in posts: by[p["hour"]].append(p)
flips = defaultdict(list); n_late = sum(late(p) for p in posts)
hourly = {r[0]: r[1:] for r in con.execute("SELECT hour_utc, missile_strike, missile_threat, drone_threat, ballistic, corrected FROM kyiv_threat_hourly").fetchall()}
for h, ps in by.items():
    if not any(late(p) for p in
... ще 735 символів
```

<details><summary>результат: 3 рядки</summary>

```
[REDACTED: перелік служб і сайтів сервера]
```

</details>

**Bash**: Fix the edited-post sentence and read the slop lines

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/data/VERIFICATION.md"); s = p.read_text()
a = "серед постів-доказів мітки 42% (truexakyiv дописує новини «UPD HH:MM», 71% його постів редаговано). 145 постів каналів мітки мають у тексті час, пізніший за кінець своєї години; жоден прапорець години не тримається лише на них (аудит)."
b = "серед постів-доказів мітки 229 з 556 (41%; truexakyiv дописує новини «UPD HH:MM», 71% його постів редаговано). 154 пости каналів мітки мають у тексті час («UPD», «станом на»), пізніший за кінець своєї години; без них правило години змінює лише один прапорець, `missile_threat` 2026-04-24T19, раніше за вікна gold (аудит)."
assert s.count(a) == 1
p.write_text(s.replace(a, b)); print("ok")
EOF
grep -n "PLAN" docs/data/silver/kyiv_alerts.md | cut -c1-80; sed -n 45,48p docs/METHODOLOGY.md; sed -n 76,87p docs/METHODOLOGY.md; sed -n 132,140p docs/METHODOLOGY.md
```

<details><summary>результат: 29 рядків</summary>

````
ok
33:Склеювання (PARSING 1): старт відкриває тривог�
43:`features(con, t_table)` повертає `pyarrow.Table`: `t_utc` першо
97:- Рівні. `alert` це старий формат без рівня (340 �
| **РФ** | Виступи Путіна, його день народження (7 жовтня), державні свята та річниці, форуми і саміти в РФ, візити іноземних лідерів до РФ |
| **Україна** | День Незалежності (24 серпня), День Конституції (28 червня), візити іноземних лідерів і делегацій до Києва |
| **Світ** | Саміти НАТО, G7, ЄС; переговори щодо війни; дзвінки Трамп і Путін; оголошення військової допомоги та санкцій |

  - Ознаки: значення за останні 24 і 72 години, днів від останнього значущого удару по РФ.
  - Джерела для всіх п'яти: див. [PARSING.md](PARSING.md), розділ 8.
  - Важливість кожного удару оцінює Jev (0-5) за рубрикою; реальний вплив на обстріли вчить модель.
- Обережно: ці ознаки шумні й схильні до хибних збігів. Додаємо лише ті, що мають надійне джерело з часом публікації, і перевіряємо, чи вони реально покращують бектест.

### 3.7 Фізичні фактори
- Тривалість темряви, час сходу і заходу сонця, фаза місяця для Києва.
- Гіпотеза: атаки тяжіють до темряви, а освітленість впливає на тактику.
- Витоку немає: астрономія відома наперед. Рахується локально, без зовнішнього джерела, див. [PARSING.md](PARSING.md), розділ 4.
- Ознаки: частка темного часу (Сонце нижче -6°) у [t, t+3), освітленість Місяця.
ча
## 4. Прогноз
## 6. Репозиторій

Три рівні даних: bronze (сирі), silver (таблиця на клас), gold (таблиця для моделі), див. [ARCHITECTURE.md](ARCHITECTURE.md).

```
README.md               звіт
docs/                   ASSIGNMENT, METHODOLOGY, PARSING, ARCHITECTURE, JEV, PLAN, adr/, data/silver/, data/gold/
scripts/bronze/         збирачі сирих даних
src/airalerts/silver/   таблиці silver
````

</details>

**Bash**: Clean stale lines in METHODOLOGY and kyiv\_alerts doc

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
edits = {
"docs/METHODOLOGY.md": [
("| **Світ** | Саміти НАТО, G7, ЄС;", "| **Світ** (прибрано 2026-10-11, [ADR-0005](adr/0005-political-events-without-world.md)) | Саміти НАТО, G7, ЄС;"),
("  - Важливість кожного удару оцінює Jev (0-5) за рубрикою; реальний вплив на обстріли вчить модель.\n", ""),
("- Ознаки: частка темного часу (Сонце нижче -6°) у [t, t+3), освітленість Місяця.\nча\n", "- Ознаки: частка темного часу (Сонце нижче -6°) у [t, t+3), освітленість Місяця.\n\n"),
("ASSIGNMENT, METHODOLOGY, PARSING, ARCHITECTURE, JEV, PLAN, adr/", "ASSIGNMENT, METHODOLOGY, PARSING, ARCHITECTURE, JEV, HISTORY, adr/"),
],
"docs/data/silver/kyiv_alerts.md": [
("(PLAN: червоний на жовтий з паузою до 2 хв)", "([HISTORY.md](../../HISTORY.md): червоний на жовтий з паузою до 2 хв)"),
("Рівні тривоги в ознаки не входять (PLAN).", "Рівні тривоги в ознаки не входять ([HISTORY.md](../../HISTORY.md))."),
("(рішення будівника, не з PLAN)", "(рішення будівника, не з плану)"),
],
}
for f, reps in edits.items():
    p = Path(f); s = p.read_text()
    for a, b in reps:
        assert s.count(a) == 1, (f, a[:60])
        s = s.replace(a, b)
    p.write_text(s)
print("ok")
EOF
grep -n "Рівні\|рівн" docs/HISTORY.md | head -3; grep -n "+ 24\|+24\|24 год" docs/data/silver/political_events.md | cut -c1-300
```

<details><summary>результат: 6 рядків</summary>

```
ok
3:Етап даних, 2026-10-10..2026-10-11. Мета: `data/gold/kyiv_hourly.parquet` з даних від 2026-05-01, без витоку, з перевіреними числами і документацією на кожному рівні; ціль `y_strike_3h`, ракетний удар по місту Київ у наступні 3 години. Як влаштовано зараз: [ARCHITECTURE.md](ARCHITECTURE.md); чому даним можна довіряти: [VERIFICATION.md](data/VERIFICATION.md); рішення: [adr/](adr/).
16:| 2026-10-10 | Ціль: ракетний удар по місту Київ (вибухи, збиття, уламки, влучання), горизонт 3 год. Gold лише з ознак для моделі, вікна до 14 днів. Три рівні bronze, silver, gold; Parquet і DuckDB; Jev для мітки і оцінок 0-5. `data/bronze/` і `data/silver/` не в git. Агенти на Sonnet |
30:- Важливість політичних подій складена: Jev відповідає «так чи ні» на прості факти, рівень рахує код: 5 президент США в Києві або зустріч президентів США і Росії; 4 саміт 5+ лідерів або зустріч з президентом США; 3 лідер великої держави або будь-який лідер у Києві; 2 інший лідер чи міністр; 1 інша особиста зустріч; 0 решта. Причина: `score` Jev це середнє рівнів, тож саміт 24 країн у Києві мав 3.62 і жодна подія не діставала 4.
112:- Kremlin новини і поїздки: `published_at` + 24 год (час на сторінці це час події, запис з'являється пізніше, PARSING 6). Виняток: заголовок про майбутнє («will ...» з датою) вважаємо ого�
160:- Клас `russia` дають Kremlin і Вікіпедія; рядків `russia` з джерелом Telegram у таблиці немає (промова Зеленського з Путіним у тексті не є подією Путіна). Kremlin: +24 год робить більші
```

</details>

**Bash**: Fix the false reference and read the political events lines

```
sed -i 's|Рівні тривоги в ознаки не входять (\[HISTORY.md\](../../HISTORY.md)).|Рівні тривоги в ознаки не входять (план етапу даних).|' docs/data/silver/kyiv_alerts.md && grep -c "план етапу даних" docs/data/silver/kyiv_alerts.md && grep -n "HISTORY.md): червоний" docs/HISTORY.md docs/data/silver/kyiv_alerts.md | cut -c1-60; grep -n "Червоний на жовтий" docs/HISTORY.md | cut -c1-80; sed -n 160p docs/data/silver/political_events.md; grep -n "18 \|зниклих\|зникл" docs/data/silver/political_events.md | cut -c1-300
```

<details><summary>результат: 9 рядків</summary>

```
1
docs/data/silver/kyiv_alerts.md:33:Склеювання (PAR
27:- Відбій без старту (VA_Kyiv 21659): старт з eTryvoga. �
- Клас `russia` дають Kremlin і Вікіпедія; рядків `russia` з джерелом Telegram у таблиці немає (промова Зеленського з Путіним у тексті не є подією Путіна). Kremlin: +24 год робить більшість подій Путіна невидимими в день події; правила за заголовком грубі, факти Jev відсікають розмови, заяви і нагородження, звернення відсікає фільтр заголовків.
5:Один рядок = одна політична подія (візит, саміт, форум, зустріч, переговори, поїздка) класу `kyiv` або `russia` з київською датою від 2026-04-17 (перший київський день `FETCH_FROM`) до 
63:- 18 фактів Jev бере одним запитом (`FACT_QUESTIONS`). `press_remarks` іде окремим запитом з одним питанням (`PRESS_QUESTION`): довгий список інших питань розмивав його.
147:- Збірка (`build --dump FILE`): 246 рядків з 318 кандидатів із 1195 (відкинуто 877, з них клас `world` 355); рядків за класом kyiv 161, russia 84, none 1; версій Вікіпедії 44. `prompt_version` лише `pol-v9`, `jev_model` �
151:- Ознаки (`features-check`): 3909 годин 2026-04-30T21:00Z..2026-10-10T17:00Z, 0 null, збіг з окремим перерахунком на Python, TIMESTAMPTZ дає те саме, ASOF збігається з повним розрахунком на 5 t (PASS). Діапазон, 
158:- Набір подій Вікіпедії береться з найновішої ревізії: події, що були на сторінці, але зникли до неї (18 у діапазоні дат), в таблиці немає, хоч якийсь час були публічн
```

</details>

**Bash**: List political\_events columns

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
print(con.execute('DESCRIBE political_events').fetchall()[:30])
" | tr ')' '\n' | grep -o "'[a-z_]*', '[A-Z]*" | head -30
```

<details><summary>результат: 29 рядків</summary>

```
'event_id', 'VARCHAR
'version_of', 'VARCHAR
'revid', 'BIGINT
'event_date', 'DATE
'end_date', 'DATE
'class', 'VARCHAR
'type', 'VARCHAR
'title', 'VARCHAR
'text', 'VARCHAR
'participants', 'VARCHAR
'importance', 'INTEGER
'importance_confidence', 'DOUBLE
'class_confidence', 'DOUBLE
'scheduled', 'BOOLEAN
'announced_at', 'TIMESTAMP
'available_at', 'TIMESTAMP
'sources', 'VARCHAR
'jev_model', 'VARCHAR
'prompt_version', 'VARCHAR
'p_in_person', 'DOUBLE
'p_us_president', 'DOUBLE
'p_us_russia_presidents', 'DOUBLE
'p_head_major', 'DOUBLE
'p_head_any', 'DOUBLE
'p_minister', 'DOUBLE
'p_remote_call', 'DOUBLE
'p_statement', 'DOUBLE
'p_ceremony', 'DOUBLE
'p_damage_report', 'DOUBLE
```

</details>

**Bash**: Check whether Kremlin rows become visible only after the event

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
print(con.execute(\"SELECT sources, count(*) FROM political_events GROUP BY 1 ORDER BY 2 DESC LIMIT 8\").fetchall())
r = con.execute(\"\"\"SELECT count(*), count(*) FILTER (WHERE available_at >= CAST(end_date + 1 AS TIMESTAMP) - INTERVAL 3 HOUR)
FROM political_events WHERE sources ILIKE '%kremlin%'\"\"\").fetchone()
print('kremlin rows, visible only after the Kyiv end day is over:', r)
"
```

<details><summary>помилка, 15 рядків</summary>

```
Exit code 1
Traceback (most recent call last):
  File "<string>", line 5, in <module>
    r = con.execute("""SELECT count(*), count(*) FILTER (WHERE available_at >= CAST(end_date + 1 AS TIMESTAMP) - INTERVAL 3 HOUR)
        ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    FROM political_events WHERE sources ILIKE '%kremlin%'""").fetchone()
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
_duckdb.BinderException: Binder Error: No function matches the given name and argument types '~~*(VARCHAR[], STRING_LITERAL)'. You might need to add explicit type casts.
	Candidate functions:
	~~*(VARCHAR, VARCHAR) -> BOOLEAN


LINE 2: FROM political_events WHERE sources ILIKE '%kremlin%'
                                            ^
[(['https://en.wikipedia.org/w/index.php?oldid=1365616613'], 3), (['https://en.wikipedia.org/w/index.php?oldid=1375825869'], 2), (['https://t.me/OP_UA/18608'], 1), (['https://t.me/V_Zelenskiy_official/18737'], 1), (['https://t.me/OP_UA/18560'], 1), (['https://en.wikipedia.org/w/index.php?oldid=1351521370', 'https://t.me/OP_UA/18587', 'https://t.me/V_Zelenskiy_official/18793'], 1), (['https://t.me/V_Zelenskiy_official/18797'], 1), (['https://t.me/OP_UA/18563'], 1)]
```

</details>

**Bash**: Check Kremlin row visibility against the event end day

```
.venv/bin/python -I -c "
from airalerts.db import connect, register_layers
con = register_layers(connect())
r = con.execute(\"\"\"SELECT count(*), count(*) FILTER (WHERE available_at >= CAST(end_date + 1 AS TIMESTAMP) - INTERVAL 3 HOUR)
FROM political_events WHERE array_to_string(sources, ' ') ILIKE '%kremlin%' AND class <> 'none'\"\"\").fetchone()
print('kremlin rows (class kyiv/russia), visible only after their last Kyiv day is over:', r)
"
```

<details><summary>результат: 1 рядок</summary>

```
kremlin rows (class kyiv/russia), visible only after their last Kyiv day is over: (69, 69)
```

</details>

**Bash**: Fix the Kremlin statement and read ADR-0006

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/data/silver/political_events.md"); s = p.read_text()
a = "Kremlin: +24 год робить більшість подій Путіна невидимими в день події;"
b = "Kremlin: +24 год робить кожен з 69 рядків з Kremlin видимим лише після останнього дня події, тож на gold вони не впливають, і `russia_*` у gold дає лише Вікіпедія (аудит 2026-10-11);"
assert s.count(a) == 1
p.write_text(s.replace(a, b)); print("ok")
EOF
cat docs/adr/0006-external-verification.md
```

<details><summary>результат: 21 рядок</summary>

```
ok
# ADR-0006: Зовнішня перевірка мітки і сигналів, виправлення мітки вручну

- Статус: прийнято
- Дата: 2026-10-11

## Контекст

Мітку удару і сигнали підготовки дає Jev, а будівник і перевіряльник шматків були однією моделлю. Код перевіряє форму і витік, але не правду: еталону ударів по Києву немає. Користувач не повірив кількості днів удару.

## Рішення

- Мітку перевіряють джерела, що не залежать від неї: два агенти наосліп (офіційні підсумки в Telegram, новини), денні пуски ракет з dronestrikemap і читання постів у кожній розбіжній ночі.
- Сигнали перевіряє інша модель: агенти Haiku читають наосліп усі пости погодинно, кожну розбіжну годину розсуджує Sonnet.
- Знайдені помилки мітки, які не виправляє жодне правило без нових сумнівних годин, задаємо вручну списком `CORRECTIONS` з доказами; рядок має `corrected`.
- Скрипти в `scripts/verify/`, докази в `data/verification/` (у git), висновки в `docs/data/VERIFICATION.md`.

## Наслідки

- Перевірку можна повторити: нарізка і вхід суддям відтворюються байт у байт, читання агентами відтворюється за тими самими промптами (відповіді моделей можуть трохи різнитись).
- Ручні виправлення видно в даних і в коді; нових без доказу не додаємо.
```

</details>

**Bash**: Add the audit line to ADR-0006

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/adr/0006-external-verification.md"); s = p.read_text()
a = "- Ручні виправлення видно в даних і в коді; нових без доказу не додаємо."
b = a + "\n- Аудит перед моделюванням (2026-10-11) прочитав кожну годину удару і додав 15 виправлень: остання година атаки лише зі звітами про наслідки (14) і реактивний дрон (1); причина кожного в коментарі `CORRECTIONS`."
assert s.count(a) == 1
p.write_text(s.replace(a, b)); print("ok")
EOF
git log --oneline | wc -l
```

<details><summary>результат: 2 рядки</summary>

```
ok
51
```

</details>

**Write**: /home/ye/PROJECTS/ai-school/airalers/docs/HANDOFF.md

```
файл: /home/ye/PROJECTS/ai-school/airalers/docs/HANDOFF.md, 6302 символів
# Хендоф: дані для прогнозу удару по Києву

Стан на 2026-10-11 близько 11:00Z. Гілка `data-layers`, віддаленого репозиторію немає, нічого не запушено. Етап даних завершено і пройшов аудит перед моделюванням (нижче). Далі: моделювання. Здача завдання KSE: 2026-10-12 23:59 за Києвом ([ASSIGNMENT.md](ASSIGNMENT.md)).

Читати в такому порядку: цей файл, [ARCHITECTURE.md](ARCHITECTURE.md) (рівні, контракт, як запустити), [VERIFICATION.md](data/VERIFICATION.md) (чому даним можна довіряти, аудит), [kyiv_hourly.md](data/gold/kyiv_hourly.md) (колонки gold), [HISTORY.md](HISTORY.md) (як дійшли і від чого відмовились), [adr/](adr/).

## Що є

| Рівень | Що | Де | У git |
|---|---|---|---|
| bronze | 17 Telegram-каналів з 2026-04-16T21:00Z (163 042 пости), прогони ECMWF, астрономія, дати, Kremlin, Вікіпедія, знімок dronestrikemap; журнал `data/bronze/MANIFEST.md` | `data/bronze/`, 175 МБ | лише MANIFEST |
| silver | 11 таблиць, по документу на кожну | `data/silver/*.parquet`, `docs/data/silver/` | ні |
| кеш Jev | кожна відповідь Jev; без нього перебудова мітки й оцінок коштує гроші і дає трохи інші числа | `data/silver/_jev_cache/` (34 073 виклики, $8.97) | ні, не видаляти |
| gold | `kyiv_hourly`: 3909 годин 2026-04-30T21:00Z..2026-10-10T17:00Z, 52 колонки (`t_utc`, 50 ознак, ціль), `y_strike_3h` true 138 з 3906 (3.5%); null лише в 3 останніх цілях і в `ua_missiles_launched_1d` (1114 годин без числа ракет) | `data/gold/kyiv_hourly.parquet` | так |
| докази | зовнішня перевірка мітки і
... ще 4802 символів
```

<details><summary>результат: 1 рядок</summary>

```
The file /home/ye/PROJECTS/ai-school/airalers/docs/HANDOFF.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

</details>

**Bash**: Fix the hour claim and read the history journal tail

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/HANDOFF.md"); s = p.read_text()
a = "- Майже весь сигнал дає час доби: позитиви майже всі 22..05 за Києвом."
b = "- Більшість сигналу дає час доби: 118 з 138 позитивів о 22..05 за Києвом."
assert s.count(a) == 1
p.write_text(s.replace(a, b)); print("ok")
EOF
tail -8 docs/HISTORY.md | cut -c1-250
```

<details><summary>результат: 9 рядків</summary>

```
ok
| 2026-10-11T08:35Z | користувач: масова перевірка сигналів S1, S2, S4 агентами Haiku. Усі 117081 пости 6 каналів з 2026-04-29T09:00Z до 2026-10-10T17:00Z нарізано на 309 пачок
| 2026-10-11T08:58Z | F4d `political_events` pol-v8 (версії Вікіпедії без витоку) | перевірено з 1 спроби |
| 2026-10-11T09:20Z | звірка мітки з незалежними еталонами: 30 з 33 ночей удару підтверджує V1 або V2, ще 2 (06-18, 08-27) оркестратор підтвердив постами; проп
| 2026-10-11T09:50Z | користувач: клас `world` прибрати («занадто важко відрізнити»). Питання Jev про зв'язок з війною прибрало й G7, NATO, Раду ЄС, тож не вз�
| 2026-10-11T09:50Z | користувач: удари по РФ переробити на dronestrikemap.com. Відкрите API: `/api/strikes`, `/api/timeline`, `/api/day/<d>`; збирач `scripts/bronze/dronestrikemap_fetch.py`, знімок 
| 2026-10-11T10:30Z | `rf_strikes` на dronestrikemap: `strike_points`, `strike_days`, день відомий з d + 30 год, окуповані території поза ознаками Росії; gold 52 колонки, тест 7 OK, 2400 
| 2026-10-11T10:40Z | масова перевірка сигналів: 309 агентів Haiku, 3932 години; розбіжних годин 147, усі розсудив Sonnet. S1: хибних годин у silver 11 з 340 (супутник�
| 2026-10-11T10:45Z | 294 години, де regex A чи B каже удар, а мітка ні: 120 у дні без ракет за еталонами (дрони), 41 у межах 3 год від години мітки, решта денні �
```

</details>

**Bash**: Record the user decisions and the audit in HISTORY

```
date -u +%Y-%m-%dT%H:%MZ && .venv/bin/python -I - <<'EOF'
from pathlib import Path
from datetime import datetime, timezone
now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
p = Path("docs/HISTORY.md"); s = p.read_text()
a = "| 2026-10-11 | Реактивні дрони («Герань-3/5») і «Бандероль» не удар."
i = s.index(a); j = s.index("\n", i)
row = "\n| 2026-10-11 | Після аудиту: 15 хибних годин мітки в `CORRECTIONS`; пости, переписані після публікації, не створюють подій сигналів; `ua_missiles_launched_1d` NULL замість 0, `rf_drones_intercepted_1d` лише дрони; документи почистити |"
s = s[:j] + row + s[j:]
s = s.rstrip("\n") + f"\n| {now} | аудит перед моделюванням (оркестратор Opus і 5 агентів, лише читання): 50 ознак gold перераховано з silver, 0 розбіжностей; 15 з 77 годин удару хибні (звіти про наслідки, реактивний дрон); 4 події S1 з переписаних постів починались на 1.3..5.7 год раніше; `ua_missiles_launched_1d` 0 замість невідомо; `rf_drones_intercepted_1d` з ракетами | виправлено: годин удару 62, ціль true 138, подій сигналів 9361, тест 7 OK |\n"
p.write_text(s); print("ok")
EOF
tail -2 docs/HISTORY.md | cut -c1-200; sed -n 20,24p docs/HISTORY.md | cut -c1-120
```

<details><summary>результат: 9 рядків</summary>

```
2026-10-11T10:04Z
ok
| 2026-10-11T10:45Z | 294 години, де regex A чи B каже удар, а мітка ні: 120 у дні без ракет за еталонами (дрони), 41 у межах 3 год ві�
| 2026-10-11T10:04Z | аудит перед моделюванням (оркестратор Opus і 5 агентів, лише читання): 50 ознак gold перераховано з silver, 
| 2026-10-11 | Версії рядків Вікіпедії замість найновішої ревізії (випр
| 2026-10-11 | Клас політичних подій `world` прибрати ([ADR-0005](adr/0005-political-events-w
| 2026-10-11 | Удари по РФ переробити на dronestrikemap.com, день відомий через 30 
| 2026-10-11 | Реактивні дрони («Герань-3/5») і «Бандероль» не удар. Обидв�
| 2026-10-11 | Після аудиту: 15 хибних годин мітки в `CORRECTIONS`; пости, перепи
```

</details>

**Bash**: Compare journal times with real commit times

```
git log --format="%ad %s" --date=format-local:"%Y-%m-%dT%H:%M" -12 | cut -c1-110; echo; TZ=UTC git log --format="%ad %s" --date=format-local:"%Y-%m-%dT%H:%MZ" -3 | cut -c1-90; date
```

<details><summary>результат: 17 рядків</summary>

```
2026-10-11T12:58 Rebuild gold after the audit fixes of the label, signals and RF strikes
2026-10-11T12:57 Keep unknown missile launches as NULL and count only drones intercepted
2026-10-11T12:57 Leave posts rewritten after publication out of the signal events
2026-10-11T12:54 Correct 15 strike hours that only report damage after the missiles
2026-10-11T12:32 Drop the temp folder note from the handoff: the old agent files are deleted
2026-10-11T12:30 Shorten the five longest docs and fix the statements that were stale
2026-10-11T12:20 Rewrite the handoff for the leakage review and fix stale methodology lines
2026-10-11T12:18 Remove dead code, files and doc statements found by the repository audit
2026-10-11T12:03 Document why the data can be trusted and how we got here
2026-10-11T12:00 Add the external checks of the label and the signals with their evidence
2026-10-11T11:56 Correct two label hours found by the external check and commit the gold table
2026-10-11T11:50 Log the rf_strikes rebuild, the mass signal check and the regex-only label hours

2026-10-11T09:58Z Rebuild gold after the audit fixes of the label, signals and RF strikes
2026-10-11T09:57Z Keep unknown missile launches as NULL and count only drones intercepted
2026-10-11T09:57Z Leave posts rewritten after publication out of the signal events
Sun Oct 11 01:04:53 PM EEST 2026
```

</details>

**Bash**: Fix my handoff time and flag unreliable journal times

```
grep -n "## Журнал запусків" -A3 docs/HISTORY.md | cut -c1-200 && .venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/HANDOFF.md"); s = p.read_text()
a = "Стан на 2026-10-11 близько 11:00Z."
assert s.count(a) == 1
p.write_text(s.replace(a, "Стан на 2026-10-11 близько 10:10Z."))
p = Path("docs/HISTORY.md"); s = p.read_text()
a = "## Журнал запусків\n"
assert s.count(a) == 1
p.write_text(s.replace(a, a + "\nЧас у записах до аудиту (2026-10-11T10:04Z) не збігається з часом комітів: розбіжність 1.5..4 год (наприклад, перебудову `rf_strikes` записано на 10:30Z, а коміт о 08:50Z). Точний час дає `git log`.\n", 1))
print("ok")
EOF
sed -n '/## Журнал запусків/,+5p' docs/HISTORY.md | cut -c1-160
```

<details><summary>результат: 11 рядків</summary>

```
61:## Журнал запусків
62-
63-| Час UTC | Що | Статус |
64-|---|---|---|
ok
## Журнал запусків

Час у записах до аудиту (2026-10-11T10:04Z) не збігається з часом комітів: розбіжність 1.5..4 год (н�

| Час UTC | Що | Статус |
|---|---|---|
```

</details>

### Claude, 13:05

Перевіряю діапазон розбіжності, який щойно вписав, на кількох парах «запис журналу і коміт».

**Bash**: Pair journal entries with their commit times

```
TZ=UTC git log --format="%ad %h %s" --date=format-local:"%Y-%m-%dT%H:%MZ" | grep -i -E "rf_strikes|political_events with versioned|gold kyiv_hourly|S4|Correct two" | cut -c1-100; grep -n -E "^\| 2026-10-1[01]T" docs/HISTORY.md | grep -i -E "rf_strikes|F4d|FINAL gold|S4 зібрано|звірка мітки" | cut -c1-90
```

<details><summary>результат: 17 рядків</summary>

```
2026-10-11T08:56Z 07c282c Correct two label hours found by the external check and commit the gold ta
2026-10-11T08:50Z bcc6a75 Log the rf_strikes rebuild, the mass signal check and the regex-only label
2026-10-11T08:47Z 6013a20 Correct the rf_strikes doc: 297 oblast-centre points and the weaker UTC da
2026-10-11T08:44Z 59a6ae3 Rebuild silver rf_strikes from dronestrikemap.com with a 30 hour day lag
2026-10-11T08:37Z 4d591b2 Build silver political_events with versioned Wikipedia rows and without th
2026-10-10T22:19Z 3cec39d Build gold kyiv_hourly with a leakage test over every silver module
2026-10-10T21:20Z c519461 Log S4 verified and the first S3b check in the plan
2026-10-10T20:42Z 65ed226 Log the label run, the S4 build and the new political importance scale
2026-10-10T20:36Z 23693ce Rebuild rf_strikes from the new data start 2026-04-16T21:00Z
94:| 2026-10-10T20:40Z | R1 `kyiv_alerts` (562 тривоги, 14 діб повні з T0)
96:| 2026-10-10T20:42Z | S4 зібрано (9363 події, $0.75); МіГ-31К 2026-09-1
104:| 2026-10-10T21:55Z | workflow `wf_0659d4f9-f41`: FINAL gold `kyiv_hourly`, тест �
105:| 2026-10-10T22:18Z | FINAL gold `kyiv_hourly`: 3909 рядків, 48 колонок, 
107:| 2026-10-11T07:38Z | користувач: версії з ревізій. Workflow `
110:| 2026-10-11T08:58Z | F4d `political_events` pol-v8 (версії Вікіпедії �
111:| 2026-10-11T09:20Z | звірка мітки з незалежними еталона
114:| 2026-10-11T10:30Z | `rf_strikes` на dronestrikemap: `strike_points`, `strike_days`
```

</details>

**Bash**: Correct the journal time note

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
p = Path("docs/HISTORY.md"); s = p.read_text()
a = "Час у записах до аудиту (2026-10-11T10:04Z) не збігається з часом комітів: розбіжність 1.5..4 год (наприклад, перебудову `rf_strikes` записано на 10:30Z, а коміт о 08:50Z). Точний час дає `git log`."
b = "Записи 2026-10-10 збігаються з часом комітів. Записи 2026-10-11 до аудиту стоять на 0.4..2 год пізніше за свої коміти (перебудову `rf_strikes` записано на 10:30Z, коміт о 08:44Z). Точний час дає `git log`."
assert s.count(a) == 1
p.write_text(s.replace(a, b)); print("ok")
EOF
git status --short
```

<details><summary>результат: 15 рядків</summary>

```
ok
 M data/verification/label_compare.txt
 M docs/HANDOFF.md
 M docs/HISTORY.md
 M docs/METHODOLOGY.md
 M docs/PARSING.md
 M docs/adr/0006-external-verification.md
 M docs/data/VERIFICATION.md
 M docs/data/gold/kyiv_hourly.md
 M docs/data/silver/kyiv_alerts.md
 M docs/data/silver/kyiv_threat_hourly.md
 M docs/data/silver/political_events.md
 M docs/data/silver/prep_signal_events.md
 M docs/data/silver/rf_strikes.md
 M src/airalerts/silver/rf_strikes.py
```

</details>

### Claude, 13:05

Перед комітом перевіряю весь diff на заборонені символи і на числа, які могли лишитись старими.

**Bash**: Check the diff for banned characters and stale numbers

```
git diff -U0 | grep "^+" | grep -c -e "·" -e "—"; grep -rn -e "true 151" -e "0\.0387" -e "77 годин" -e "9363 под" -e "(3909, 151)" docs/ARCHITECTURE.md docs/HANDOFF.md docs/data/ docs/METHODOLOGY.md docs/JEV.md docs/adr/ | cut -c1-160
```

<details><summary>результат: 5 рядків</summary>

```
0
docs/HANDOFF.md:24:  - мітка: 15 з 77 годин удару хибні (14 разів остання година атаки лише зі звітами 
docs/data/VERIFICATION.md:27:| мітка | прочитано пости кожної з 77 годин удару | 60 удар, 14 звіти про насл�
docs/data/gold/kyiv_hourly.md:134:| `.venv/bin/python -I -m airalerts.gold.kyiv_hourly report` | `rows 3909, columns 52`, `hours from T0 to cutoff inclusive 390
docs/data/silver/kyiv_threat_hourly.md:38:Зовнішня перевірка 2026-10-11 ([VERIFICATION.md](../VERIFICATION.md)) знайшла серед 33 н
```

</details>

**Bash**: Compare the gold doc report line with the real report

```
sed -n 134p docs/data/gold/kyiv_hourly.md | grep -o -e "base rate[^;|]*" -e "strike hours[^;|]*" -e "0\.0387[^;]*"; .venv/bin/python -I -m airalerts.gold.kyiv_hourly report 2>&1 | grep -E "base rate|strike hours"
```

<details><summary>результат: 4 рядки</summary>

```
base rate = true / labelled = 151/3906 = 0.0387`
strike hours ... from T0: 77 of 3908`
y_strike_3h base rate = true / labelled = 138/3906 = 0.0353
strike hours (kyiv_threat_hourly.missile_strike) from T0: 62 of 3908 hours of the table
```

</details>

**Bash**: Fix the report line numbers in the gold doc

```
sed -i '134s|base rate = true / labelled = 151/3906 = 0.0387`|base rate = true / labelled = 138/3906 = 0.0353`|; 134s|strike hours ... from T0: 77 of 3908`|strike hours ... from T0: 62 of 3908`|' docs/data/gold/kyiv_hourly.md && sed -n 134p docs/data/gold/kyiv_hourly.md | grep -o -e "base rate[^;|]*" -e "strike hours[^;|]*" -e "null лише[^;|]*" -e "null[^;|]*y_strike_3h[^;|]*"
```

<details><summary>результат: 3 рядки</summary>

```
base rate = true / labelled = 138/3906 = 0.0353`
strike hours ... from T0: 62 of 3908`
null лише в `y_strike_3h`: 3
```

</details>

**Bash**: Fix the last report line, rerun tests and commit the docs

```
sed -i '134s|null лише в `y_strike_3h`: 3|null у `y_strike_3h` 3 і в `ua_missiles_launched_1d` 1114|' docs/data/gold/kyiv_hourly.md && sed -n 134p docs/data/gold/kyiv_hourly.md | grep -o "null у[^;|]*" && .venv/bin/python -I -m unittest discover -s tests 2>&1 | tail -2 && git add -A docs data/verification/label_compare.txt src/airalerts/silver/rf_strikes.py && git status --short && git commit -q -m "Record the audit before modelling and clean stale statements from the docs

VERIFICATION gets the audit: every gold feature recomputed with 0
differences, the 15 label hours, the signal leak, the RF day boundary.
New numbers everywhere (138 positive rows, 62 strike hours, 9361 events),
the UA day of dronestrikemap is the Air Force day, Kremlin rows never
reach gold, the handoff now leads to modelling. label_compare.txt is
rebuilt on the corrected label.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git log --oneline -6
```

<details><summary>результат: 23 рядки</summary>

```
null у `y_strike_3h` 3 і в `ua_missiles_launched_1d` 1114

ASOF: 50 random t (seed 20261011) from 2026-05-01T11:00:00Z to 2026-10-09T19:00:00Z, 8 modules, 2400 feature values compared with the gold rows, differences 0; rows hidden by the ASOF views in total 6762423
M  data/verification/label_compare.txt
M  docs/HANDOFF.md
M  docs/HISTORY.md
M  docs/METHODOLOGY.md
M  docs/PARSING.md
M  docs/adr/0006-external-verification.md
M  docs/data/VERIFICATION.md
M  docs/data/gold/kyiv_hourly.md
M  docs/data/silver/kyiv_alerts.md
M  docs/data/silver/kyiv_threat_hourly.md
M  docs/data/silver/political_events.md
M  docs/data/silver/prep_signal_events.md
M  docs/data/silver/rf_strikes.md
M  src/airalerts/silver/rf_strikes.py
ae36f42 Record the audit before modelling and clean stale statements from the docs
024645e Rebuild gold after the audit fixes of the label, signals and RF strikes
4c4d0bb Keep unknown missile launches as NULL and count only drones intercepted
d1a041a Leave posts rewritten after publication out of the signal events
5f35ff0 Correct 15 strike hours that only report damage after the missiles
6ea2cd9 Drop the temp folder note from the handoff: the old agent files are deleted
```

</details>

**Bash**: Confirm tests pass and list the agents' recompute scripts

```
.venv/bin/python -I -m unittest discover -s tests 2>&1 | grep -E "^(OK|FAILED|Ran)"; A=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit; ls $A/history/*.py $A/signals/s3_recompute.py $A/rf/step3_recompute.py $A/political/*.py 2>/dev/null | head -20; head -15 $A/history/s03*.py | grep -i -E "usage|argv|python" 
```

<details><summary>результат: 16 рядків</summary>

```
Ran 7 tests in 9.383s
OK
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s01_heads.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s02_bronze_alerts.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s03_features.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s04_asof.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s05_boundaries.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s06_edited.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s07_long_alerts.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s08_upd_leak.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/political/cal_check.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/political/extra_check.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/political/gold_check.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/political/pe_audit.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/rf/step3_recompute.py
/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/signals/s3_recompute.py
```

</details>

**Bash**: Rerun the agents' independent recompute scripts on new gold

```
A=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit; for s in history/s03_features.py signals/s3_recompute.py rf/step3_recompute.py political/gold_check.py; do echo "=== $s"; timeout 300 .venv/bin/python -I $A/$s 2>&1 | grep -i -E "mismatch|differ|total|rows|: 0|column" | head -14; done
```

<details><summary>результат: 57 рядків</summary>

```
=== history/s03_features.py
gold rows 3909 first 2026-04-30 21:00:00 last 2026-10-10 17:00:00 unique True steps all 1h True on the hour True tzinfo None
== step 2: mismatches per column (gold vs own recompute), 3 examples (t, gold, expected) ==
rows with >1 active alert: 0 | rows whose 336 h window has hours absent from kyiv_threat_hourly: 0
boundary start: gold t with an alert time exactly at t-0:00:00: 0
boundary start: gold t with an alert time exactly at t-3:00:00: 0
boundary start: gold t with an alert time exactly at t-6:00:00: 0
boundary start: gold t with an alert time exactly at t-1 day, 0:00:00: 0
boundary start: gold t with an alert time exactly at t-7 days, 0:00:00: 0
boundary start: gold t with an alert time exactly at t-14 days, 0:00:00: 0
boundary end: gold t with an alert time exactly at t-0:00:00: 0
gold t with an alert started before t-24h and running into the window: 573 examples ['2026-05-01 00:00:00', '2026-05-01 13:00:00', '2026-05-03 07:00:00'] | of which still running at t: 0
kyiv_alerts rows 562 nulls {'gap_from_prev_min': 1} dup key 0
kyiv_threat_hourly rows 4244 nulls {'p_strike_max': 508, 'first_strike_at': 4182} dup key 0
  n_posts_jev > n_posts: 0 | flags true with n_posts_jev=0: 0 | strike without first_strike_at: 0 | first_strike_at outside its hour: 0 | corrected: [('2026-05-14 01:00:00', False), ('2026-06-02 05:00:00', False), ('2026-07-02 01:00:00', False), ('2026-07-06 01:00:00', False), ('2026-07-11 01:00:00', False), ('2026-07-19 00:00:00', False), ('2026-08-08 01:00:00', False), ('2026-08-16 00:00:00', False), ('2026-08-19 23:00:00', False), ('2026-08-27 01:00:00', False), ('2026-08-27 16:00:00', False), ('2026-09-01 00:00:00', False), ('2026-09-17 00:00:00', False), ('2026-09-18 16:00:00', True), ('2026-09-23 23:00:00', False), ('2026-09-28 23:00:00', False), ('2026-10-07 01:00:00', False)]
=== signals/s3_recompute.py
available_at with sub-second part: 0
gold rows 3909, 2026-04-30 21:00:00 .. 2026-10-10 17:00:00; on the hour: True; continuous hourly: True
mismatches per column (gold vs plain Python, exact equality): {'s1_takeoff_6h': 0, 's1_takeoff_24h': 0, 'hours_since_s1': 0, 's2_mig31k_airborne': 0, 's4_drone_waves_6h': 0}
max |diff| hours_since_s1: 0.0 ; nulls in gold: {'s1_takeoff_6h': 0, 's1_takeoff_24h': 0, 'hours_since_s1': 0, 's2_mig31k_airborne': 0, 's4_drone_waves_6h': 0}
  S1: events at exactly t-0h/t-3h/t-6h/t-24h of some gold t: {0: 0, 3: 0, 6: 0, 24: 0}
  S2air: events at exactly t-0h/t-3h/t-6h/t-24h of some gold t: {0: 0, 3: 0, 6: 0, 24: 0}
  S2clr: events at exactly t-0h/t-3h/t-6h/t-24h of some gold t: {0: 0, 3: 0, 6: 0, 24: 0}
  S2 airborne and all_clear at the identical second: 0
  variant (lo, t): rows differing from gold per column {'s1_takeoff_6h': 0, 's1_takeoff_24h': 0, 'hours_since_s1': 0, 's2_mig31k_airborne': 0, 's4_drone_waves_6h': 3}
  variant [lo, t]: rows differing from gold per column {'s1_takeoff_6h': 0, 's1_takeoff_24h': 0, 'hours_since_s1': 0, 's2_mig31k_airborne': 0,
```

... ще 31 рядок

</details>

**Bash**: Show the alert and threat mismatch table on new gold

```
A=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit; timeout 300 .venv/bin/python -I $A/history/s03_features.py 2>&1 | sed -n '/step 2: mismatches/,/^==/p' | head -26
```

<details><summary>результат: 26 рядків</summary>

```
== step 2: mismatches per column (gold vs own recompute), 3 examples (t, gold, expected) ==
hour_kyiv                    0 []
dow_kyiv                     0 []
alert_active                 0 []
alert_active_min             0 []
alerts_started_3h            0 []
alerts_started_6h            0 []
alerts_started_24h           0 []
alert_minutes_24h            0 []
alerts_7d                    0 []
alerts_14d                   0 []
hours_since_alert_end        0 []
threat_prev_1h               0 []
threat_hours_6h              0 []
threat_hours_24h             0 []
ballistic_hours_3h           0 []
ballistic_hours_6h           0 []
ballistic_hours_24h          0 []
drone_threat_prev_1h         0 []
strikes_7d                   0 []
strikes_14d                  0 []
hours_since_strike           0 []
rows with >1 active alert: 0 | rows whose 336 h window has hours absent from kyiv_threat_hourly: 0
Kyiv UTC offsets seen in gold: [3.0]
boundary start: gold t with an alert time exactly at t-0:00:00: 0
boundary start: gold t with an alert time exactly at t-3:00:00: 0
```

</details>

### Claude, 13:07

Дані перевірено зверху вниз і виправлено, тож gold готовий до моделювання. Агрегація була правильна: усі 50 ознак, перераховані незалежно на всіх 3909 годинах, мають 0 розбіжностей. Помилки знайшлись у мітці удару, в одному витоці і в документах. Тест на витік після виправлень: 7 OK.

**Що попередній агент зробив неправильно (усе перевірив сам, читаючи пости і запускаючи команди):**
- **Мітка:** 15 з 77 «годин удару» хибні. 14 разів це остання година атаки, де є лише звіти «уламки впали», «пожежа», підсумок ПС і відбій, ще 1 година це реактивний дрон. Причина: Jev оцінює такі звіти як удар. У VERIFICATION.md при цьому стояло «мітка тут права».
- **Витік у сигналах S1:** пост AerisRimor опубліковано о 20:45 за Києвом, а його текст «Зведення станом на 02:25» дописано вночі. Через такі пости 4 події стратегічної авіації з'являлись у gold на 1.3..5.7 год раніше, перед атаками.
- **Удари по РФ:** у 55 днях без даних кількість ракет стояла як 0. «Збиті дрони» рахували ще й ракети. У документі день сайту для України названо днем UTC, хоча це доба звіту ПС (безпечний бік).
- **Галюцинації в документах:** вигадані часи в журналі HISTORY (на 0.4..2 год пізніше за коміти), твердження про Kremlin, зайвий рядок «ча» і клас «Світ» у METHODOLOGY.

**Що змінено (6 комітів у `data-layers`, без push):**
- 15 годин додано в `CORRECTIONS` з причиною кожної. Годин удару стало 62, позитивів у цілі 151 → 138.
- Пости, переписані після публікації, тепер не створюють подій сигналів. Jev не викликався, усе взято з кешу, $0.
- `ua_missiles_launched_1d` тепер NULL у днях без даних. `rf_drones_intercepted_1d` рахує лише дрони.
- Документи почищено, результати аудиту записано у VERIFICATION.md, HANDOFF тепер веде до моделювання.

**Важливо для моделювання:**
- 138 позитивів це лише 35 атак, а в 33 рядках атака вже йде на момент t. Початок атаки треба оцінювати окремо.
- Година доби і темрява самі дають AUC 0.78.
- За останні 28 днів лише 7 атак, тож тест на свіжому періоді буде шумним, без bootstrap по днях не обійтись.

**Тобі вирішити:**
- Дані закінчуються 2026-10-10T17Z, а завдання вимагає найсвіжіших. Чи докачувати перед здачею? Потрібен відкритий vault для Jev і кілька годин збору Telegram.
- Дві можливі пропущені години удару, 2026-09-17T04 і 2026-09-27T23. Аудит їх не підтвердив, тож мітку я не міняв.

Копія старих silver і gold лежить у scratchpad `backup_before_fix/`, зведення аудиту в `audit/SUMMARY.md`. Знайдені галюцінації попереднього агента згодяться для рефлексії в завданні.

### Користувач, 11.10 13:13

> Докачувати не треба . ОК . Задоуцлутй резлуаььата свого аудиту  

### Claude, 13:13

Ти маєш рацію: зараз аудит записано в репозиторії лише коротким розділом у VERIFICATION.md, а всі докази (вердикти по кожній годині, скрипти перерахунку) лежать у тимчасовому scratchpad і зникнуть. Переношу їх у репозиторій за тим самим зразком, що й зовнішня перевірка (`scripts/verify/`, `data/verification/`). Спершу дивлюсь, що з написаного агентами варто брати.

**Bash**: Size up the audit scripts and evidence files

```
A=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit; wc -l $A/*/*.py $A/*/*.csv 2>/dev/null; grep -l "/tmp/claude\|scratchpad" $A/*/*.py
```

<details><summary>результат: 39 рядків</summary>

```
    22 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s01_heads.py
   111 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s02_bronze_alerts.py
   114 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s03_features.py
    68 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s04_asof.py
    49 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s05_boundaries.py
    76 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s06_edited.py
    25 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s07_long_alerts.py
    54 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/history/s08_upd_leak.py
    88 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/label/check.py
    22 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/label/ctx.py
    81 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/label/dump.py
   120 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/label/verdicts.py
    21 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/astro_check.py
    27 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/gold_shape.py
    56 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/probe.py
    36 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/me/weather_check.py
    65 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/political/cal_check.py
    39 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/political/extra_check.py
   132 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/political/gold_check.py
   282 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/political/pe_audit.py
    83 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/rf/fetch2.py
    93 /tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/rf/step1b_window.py
   122
```

... ще 16 рядків

</details>

**Bash**: Read the alerts and threat recompute script

```
A=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit; cat $A/history/s03_features.py | sed -n 1,75p
```

<details><summary>результат: 74 рядки</summary>

```
"""Step 2 (recompute 19 feature columns + hour/dow for every gold row by plain loops from silver Parquet, doc definitions)
and step 5 (quality of kyiv_alerts and kyiv_threat_hourly). Read-only; no airalerts import."""
import collections, math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pyarrow.parquet as pq

H = timedelta(hours=1)
gold = pq.read_table("data/gold/kyiv_hourly.parquet").to_pylist()
al = sorted(pq.read_table("data/silver/kyiv_alerts.parquet").to_pylist(), key=lambda a: a["start_utc"])
th = pq.read_table("data/silver/kyiv_threat_hourly.parquet").to_pylist()
flags = {r["hour_utc"]: r for r in th}
ts = [g["t_utc"] for g in gold]
print("gold rows", len(gold), "first", ts[0], "last", ts[-1], "unique", len(set(ts)) == len(ts),
      "steps all 1h", all(b - a == H for a, b in zip(ts, ts[1:])), "on the hour", all(t.minute == t.second == t.microsecond == 0 for t in ts),
      "tzinfo", ts[0].tzinfo)

def alert_feats(t):
    known = [(a["start_utc"], a["end_utc"]) for a in al if a["available_at"] < t]
    act = [(s, e) for s, e in known if e is None or e >= t]
    f = {"alert_active": bool(act)}
    f["alert_active_min"] = (t - act[0][0]).total_seconds() / 60 if act else 0.0
    f["_n_active"] = len(act)
    for n in (3, 6, 24):
        f[f"alerts_started_{n}h"] = sum(1 for s, e in known if t - n * H <= s < t)
    lo = t - 24 * H
    m = 0.0
    for s, e in known:
        hi = e if (e is not None and e < t) else t          # end at/after t is unknown -> counts to t
        a, b = max(s, lo), min(hi, t)
        if b > a: m += (b - a).total_seconds() / 60
    f["alert_minutes_24h"] = m
    f["alerts_7d"] = sum(1 for s, e in known if t - timedelta(days=7) <= s < t)
    f["alerts_14d"] = sum(1 for s, e in known if t - timedelta(days=14) <= s < t)
    ends = [e for s, e in known if e is not None and e < t]
    f["hours_since_alert_end"] = 0.0 if act else ((t - max(ends)).total_seconds() / 3600 if ends else None)
    return f

def threat_feats(t):
    def fl(h, col):
```

... ще 34 рядки

</details>

**Bash**: Read the signals and RF recompute logic

```
A=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit; sed -n 1,45p $A/signals/s3_recompute.py; echo =====; grep -n "def \|energy\|moscow\|occupied\|region" $A/rf/step3_recompute.py | head -30
```

<details><summary>результат: 62 рядки</summary>

```
"""Step 3: recompute the 5 gold signal columns from silver prep_signal_events in plain Python (pyarrow read only,
no airalerts import), following docs/data/gold/kyiv_hourly.md literally; compare with gold for every row."""
from bisect import bisect_left
from collections import Counter
from datetime import timedelta
from pathlib import Path

import pyarrow.parquet as pq

REPO = Path('/home/ye/PROJECTS/ai-school/airalers')
H = timedelta(hours=1)
CAP = 336.0
COLS = ['s1_takeoff_6h', 's1_takeoff_24h', 'hours_since_s1', 's2_mig31k_airborne', 's4_drone_waves_6h']

ev = pq.read_table(REPO / 'data/silver/prep_signal_events.parquet', columns=['signal', 'subtype', 'available_at']).to_pylist()
gold = pq.read_table(REPO / 'data/gold/kyiv_hourly.parquet', columns=['t_utc'] + COLS).to_pylist()
print("silver (signal, subtype):", dict(sorted(Counter((e['signal'], e['subtype']) for e in ev).items())))
print("available_at with sub-second part:", sum(1 for e in ev if e['available_at'].microsecond))
s1 = sorted(e['available_at'] for e in ev if e['signal'] == 'S1' and e['subtype'] in ('takeoff', 'relocation'))
air = sorted(e['available_at'] for e in ev if e['signal'] == 'S2' and e['subtype'] == 'airborne')
clr = sorted(e['available_at'] for e in ev if e['signal'] == 'S2' and e['subtype'] == 'all_clear')
dr = sorted(e['available_at'] for e in ev if e['signal'] == 'S4' and e['subtype'] == 'launch')
ts = [r['t_utc'] for r in gold]
print(f"gold rows {len(gold)}, {ts[0]} .. {ts[-1]}; on the hour: {all(t.minute == t.second == t.microsecond == 0 for t in ts)}; "
      f"continuous hourly: {all(b - a == H for a, b in zip(ts, ts[1:]))}")


def count(lst, lo, hi, lo_incl=True, hi_incl=False):
    """events a with lo <= a < hi (default), bounds switchable for the boundary test."""
    return sum(1 for a in lst if (a >= lo if lo_incl else a > lo) and (a <= hi if hi_incl else a < hi))


def mine(t, lo_incl=True, hi_incl=False):
    known = [a for a in s1 if (a <= t if hi_incl else a < t)]
    last = max(known) if known else None
    airs = [a for a in air if (a >= t - 3 * H if lo_incl else a > t - 3 * H) and (a <= t if hi_incl else a < t)]
    open_ = any(not any(a < c and (c <= t if hi_incl else c < t) for c in clr) for a in airs)
    return {'s1_takeoff_6h': count(s1, t - 6 * H, t, lo_incl, hi_incl),
            's1_takeoff_24h': count(s1, t - 24 * H, t, lo_incl, hi_incl),
            'hours_since_s1': CAP if last is None else min(CAP, (t - last).total_seconds() / 3600.0),
```

... ще 22 рядки

</details>

**Bash**: Read the calendar and political recompute logic

```
A=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit; sed -n 1,95p $A/political/gold_check.py
```

<details><summary>результат: 95 рядків</summary>

```
"""Recompute the 8 gold columns (hol_*, *_imp_today, *_days_to_imp4) in plain Python from silver parquet, literally from the doc
definitions (no project module imported), compare with data/gold/kyiv_hourly.parquet; then quality notes.
Run: .venv/bin/python -I <this file>   (from the repo root)
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pyarrow.parquet as pq

ROOT = "/home/ye/PROJECTS/ai-school/airalers"
KY = ZoneInfo("Europe/Kyiv")
CAP = 14

gold = pq.read_table(ROOT + "/data/gold/kyiv_hourly.parquet").to_pylist()
cal = pq.read_table(ROOT + "/data/silver/calendar_dates.parquet").to_pylist()
pol = pq.read_table(ROOT + "/data/silver/political_events.parquet").to_pylist()
print("gold rows", len(gold), "t_utc type", type(gold[0]["t_utc"]).__name__, gold[0]["t_utc"], "..", gold[-1]["t_utc"])


def naive_utc(t):
    return t.astimezone(timezone.utc).replace(tzinfo=None) if t.tzinfo else t


def kday(t):
    return naive_utc(t).replace(tzinfo=timezone.utc).astimezone(KY).date()


print("calendar rows", len(cal), "available_at values", Counter(str(r["available_at"]) for r in cal),
      "high == (symbolism >= 3.5):", all(r["high"] == (r["symbolism"] >= 3.5) for r in cal))


def cal_feats(d):
    rf = max([r["symbolism"] for r in cal if r["date"] == d and r["group"] == "RF"], default=0.0)
    ua = max([r["symbolism"] for r in cal if r["date"] == d and r["group"] == "UA"], default=0.0)
    tom = any(r["high"] for r in cal if r["date"] == d + timedelta(days=1))
    nxt = min([(r["date"] - d).days for r in cal if r["high"] and r["date"] >= d], default=CAP)
    return {"hol_rf_symb_today": rf, "hol_ua_symb_today": ua, "hol_high_tomorrow": tom, "hol_days_to_next_high": min(CAP, nxt)}


```

... ще 55 рядків

</details>

**Bash**: Read the style of the existing verify script

```
sed -n 1,30p scripts/verify/label_check.py; ls scripts/verify data/verification
```

<details><summary>результат: 46 рядків</summary>

```
"""External check of the missile strike label (silver kyiv_threat_hourly) against the blind references in data/verification.

Run from the project root: .venv/bin/python -I scripts/verify/label_check.py   (writes data/verification/label_compare.txt)

1. nights: every Kyiv date with a label strike hour or a reference verdict, label hours (Kyiv time) next to the verdicts of the
   official summaries (V1, label_reference_official.csv) and of the news (V2, label_reference_news.csv): M missile_city,
   ? unclear_type, d drone_only, o missile_oblast_only, . not listed. V1 counts an attack after 18:00 Kyiv to the next date.
2. launches: label strike days on which dronestrikemap (silver strike_days, country UA) has missiles launched at Ukraine.
3. regex-only hours: hours where rule A or B of PARSING 2 fires and the label does not, split by attack drones in the hour
   (blind reading, signals_blind_hours.csv), by distance to a label strike hour and by the reference verdict of the day.
4. thresholds: strike hours of the current rule and of looser variants (no Jev call: kyiv_threat_posts holds the probabilities).
"""
import csv
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from airalerts.silver import threat_hourly as th  # noqa: E402

V = ROOT / "data" / "verification"
SIL = ROOT / "data" / "silver"
KYIV = timedelta(hours=3)  # the whole period is summer time (UTC+3)
T0 = datetime(2026, 4, 30, 21)
AB = {"missile_city": "M", "unclear_type": "?", "drone_only": "d", "missile_oblast_only": "o"}

data/verification:
label_compare.txt
label_reference_news.csv
label_reference_news_notes.md
label_reference_official.csv
label_reference_official_notes.md
mod_russia_daily_drones.csv
signals_blind_hours.csv
signals_compare.txt
signals_judge.csv
```

... ще 6 рядків

</details>

**Write**: /home/ye/PROJECTS/ai-school/airalers/scripts/verify/audit\_recompute.py

```
файл: /home/ye/PROJECTS/ai-school/airalers/scripts/verify/audit_recompute.py, 12009 символів
"""Audit of gold kyiv_hourly (2026-10-11, docs/data/VERIFICATION.md): every column recomputed by plain Python loops, without the
project modules and their SQL, from the silver Parquet files (weather and astronomy from bronze), following the definitions in
docs/data/gold/kyiv_hourly.md. Unlike tests/test_no_leakage.py it does not reuse features(), so a wrong window or a wrong
available_at in a module shows up as a mismatch.

Run from the project root: .venv/bin/python -I scripts/verify/audit_recompute.py   (writes data/verification/audit_recompute.txt)

Last, a planted leak: the same loops for alerts_started_3h and threat_prev_1h with data one hour later than allowed must differ
from gold, or the check is empty and the script fails.
"""
import csv
import sys
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
SIL, BRONZE = ROOT / "data" / "silver", ROOT / "data" / "bronze"
OUT = ROOT / "data" / "verification" / "audit_recompute.txt"
H, D = timedelta(hours=1), timedelta(days=1)
KYIV = ZoneInfo("Europe/Kyiv")
CAP = 336.0  # hours_since_* cap
DAYS_CAP = 14  # *_days_to_* cap


def rows(name, columns=None):
    return pq.read_table(SIL / f"{name}.parquet", columns=columns).to_pylist()


def utc(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ") if s else None


def kyiv(t):
   
... ще 10509 символів
```

<details><summary>результат: 1 рядок</summary>

```
File created successfully at: /home/ye/PROJECTS/ai-school/airalers/scripts/verify/audit_recompute.py (file state is current in your context — no need to Read it back)
```

</details>

**Edit**: /home/ye/PROJECTS/ai-school/airalers/scripts/verify/audit\_recompute.py

```
файл: /home/ye/PROJECTS/ai-school/airalers/scripts/verify/audit_recompute.py
--- було:
            "s2_mig31k_airborne": int(bool(airborne) and between(s2_clear, max(airborne), t) == between(s2_clear, max(airborne), max(airborne))),
--- стало:
            "s2_mig31k_airborne": int(bool(airborne) and not any(max(airborne) < c < t for c in s2_clear)),
```

<details><summary>результат: 1 рядок</summary>

```
The file /home/ye/PROJECTS/ai-school/airalers/scripts/verify/audit_recompute.py has been updated successfully. (file state is current in your context — no need to Read it back)
```

</details>

**Bash**: Run the independent gold recompute

```
time .venv/bin/python -I scripts/verify/audit_recompute.py; echo "exit $?"
```

<details><summary>результат: 59 рядків</summary>

```
gold 3909 rows 2026-04-30T21Z..2026-10-10T17Z, 51 columns recomputed without the project modules; mismatches per column (3 examples: t, gold, recomputed):
  hour_kyiv                  0
  dow_kyiv                   0
  alert_active               0
  alert_active_min           0
  alerts_started_3h          0
  alerts_started_6h          0
  alerts_started_24h         0
  alert_minutes_24h          0
  alerts_7d                  0
  alerts_14d                 0
  hours_since_alert_end      0
  threat_prev_1h             0
  threat_hours_6h            0
  threat_hours_24h           0
  ballistic_hours_3h         0
  ballistic_hours_6h         0
  ballistic_hours_24h        0
  drone_threat_prev_1h       0
  strikes_7d                 0
  strikes_14d                0
  hours_since_strike         0
  s1_takeoff_6h              0
  s1_takeoff_24h             0
  hours_since_s1             0
  s2_mig31k_airborne         0
  s4_drone_waves_6h          0
  wx_cloud_mean_3h           0
  wx_precip_sum_3h           0
  wx_wind_max_3h             0
  wx_visibility_min_3h       0
  dark_share_3h              0
  moon_illum                 0
  hol_rf_symb_today          0
  hol_ua_symb_today          0
  hol_high_tomorrow          0
  hol_days_to_next_high      0
  kyiv_imp_today             0
  russia_imp_today           0
  kyiv_days_to_imp4          0
```

... ще 19 рядків

</details>

**Bash**: Read the 60 live strike hour verdicts

```
D=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/label; cd /home/ye/PROJECTS/ai-school/airalers && .venv/bin/python -I -c "
import csv
for r in csv.DictReader(open('$D/strike_hours.csv')):
    if r['verdict']=='live': print(r['hour_utc'], r['in_alert'], r['reason'][:150])
"
```

<details><summary>результат: 60 рядків</summary>

```
2026-05-14T00 True truexakyiv/75651 00:29 "Уламок збитої ракети упав у одному з дворів Києва"
2026-05-14T03 True war_monitor/39822 03:43 "У Києві лунали вибухи, балістика з Брянська"
2026-05-23T22 True kyiv_airdef/36629 22:01 "Є ЗБИТТЯ БАЛІСТКИИ"; vitaliy_klitschko/6685 22:38 "уламки ракети впали на 24-поверховий будинок"
2026-05-23T23 True war_monitor/40055 23:55 "В Києві вибухи Балістики"
2026-05-24T00 True AerisRimor/70789 00:45 "Серія вибухів Київ. Це ракети з лівогол берега!"
2026-05-24T01 True AerisRimor/70838 01:09 "Серія вибухів."; truexakyiv/76592 01:39 "влучання ракет в районі Майдану Незалежності"
2026-05-24T02 True AerisRimor/70884 02:02 "Вибухи"; war_monitor/40088 02:04 "Дорозвідка по крилатих ракетах, четверта спроба"
2026-06-01T23 True war_monitor/40317 23:17 "Вибухи у Києві ... Загроза Балістики"; truexakyiv/77288 "уламки ракети впали на дах будинку"
2026-06-02T00 True truexakyiv/77331 00:44 "Ракети залітають в місто"; truexakyiv/77342 00:59 "Влучання ракети в Києві"
2026-06-02T04 True war_monitor/40386 04:21 "Вибухи Київ, загроза по Цирконах триває"
2026-06-14T22 True truexakyiv/78113 22:33 "Один із вибухів у місті" during ballistic attack (VA_Kyiv/18565 23:07 "масована атака балістикою")
2026-06-14T23 True truexakyiv/78150 23:13 "Удар Циркона по Києву"
2026-06-15T00 True AerisRimor/72839 00:27 "2-4 КР над Києвом Дарницький/Печерський!!"; kyiv_airdef/39138 00:31 "мінус"
2026-06-17T22 True war_monitor/40771 22:28 "Вибухи Київ. Загроза балістики триває."
2026-06-25T17 True truexakyiv/78829 17:57 "ГУЧНО." 5 min after the ballistic alarm, kyiv_nebo/24233 17:58 "Вже чисто"
2026-06-25T18 True vitaliy_klitschko/6968 18:00 "Вибухи в столиці"; kyiv_airdef/39809 "Третя ракета була типу Циркон"
2026-06-27T22 True kyiv_nebo/24267 22:58 "Зараз гепне"; truexakyiv/78970 22:59 "Гучно."
2026-06-27T23 True war_monitor/40947 23:01 "Вибухи у Києві, загроза балістики"
2026-07-01T22 True war_monitor/41066 22:55 "Вибухи в Києві. Триває загроза балістики"
2026-07-01T23 True vitaliy_klitschko/6999 23:01 "Київ під атакою балістики та БпЛА. В місті лунають вибухи"
2026-07-02T00 True kyiv_nebo/24425 00:06 "Ракети залітають в Київ"; war_monitor/41132 00:59 "Вибухи Київ"
2026-07-05T22 True war_monitor/41268 22:45 "Київ вибухи, загроза балістики"
2026-07-05T23 True truexakyiv/79659 23:12 "ВИБУХИ."; kyiv_airdef/41268 23:15 "ЦЕНТР" (p_ballistic 0.86)
2026-07-06T00 True war_monitor/41304 00:11 "Київ вибухи КР."
2026-07-07T21 True war_monitor/41353 21:54 "Вибухи Київ, загроза балістики"; vitaliy_klitschko/7041 "внаслідок влучання ракети"
2026-07-11T00 True truexakyiv/80148 00:40 "Вибухи у місті. Балістика на Київ."
2026-07-13T21 True war_monitor/41517 21:19 "Вибухи Київ. Загроза балістики"
2026-07-15T21 True war_monitor/41577 21:49 "Київ + область вибухи. Загроза Балістики"
2026-07-15T22 True war_monitor/41583 22:04 "Київ + область вибухи"; vitaliy_klitschko/7113 "уламки ракети впали"
2026-07-18T22 True truexakyiv/80569 22:36 "5 ракет над містом";
```

... ще 30 рядків

</details>

**Bash**: Write the strike hour verdicts as audit evidence

```
D=/tmp/claude-1000/-home-ye-PROJECTS-ai-school-airalers/ad9ddb95-bb15-40c9-89aa-529575ad4dfd/scratchpad/audit/label; cd /home/ye/PROJECTS/ai-school/airalers && grep -c -e "—" -e "·" $D/strike_hours.csv; .venv/bin/python -I - <<EOF
import csv
import pyarrow.parquet as pq
src = list(csv.DictReader(open("$D/strike_hours.csv", encoding="utf-8")))
cur = {f"{r['hour_utc']:%Y-%m-%dT%H}": r for r in pq.read_table("data/silver/kyiv_threat_hourly.parquet", columns=["hour_utc", "missile_strike", "corrected"]).to_pylist()}
read = {"2026-05-14T01", "2026-06-02T05", "2026-07-02T01", "2026-07-06T01", "2026-07-11T01", "2026-07-19T00", "2026-08-08T01", "2026-08-16T00",
        "2026-08-19T23", "2026-08-27T01", "2026-09-01T00", "2026-09-17T00", "2026-09-23T23", "2026-09-28T23", "2026-10-07T01"}
out = "data/verification/audit_strike_hours.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["hour_utc", "episode", "pos_in_episode", "episode_len", "in_alert", "verdict", "reason", "evidence_ids", "read_by_orchestrator", "missile_strike_now"])
    for r in src:
        h = r["hour_utc"]
        w.writerow([h, r["episode"], r["pos_in_episode"], r["episode_len"], r["in_alert"], r["verdict"], r["reason"].replace("—", "-").replace("·", ","),
                    r["evidence_ids"], h in read, cur[h]["missile_strike"]])
rows = list(csv.DictReader(open(out, encoding="utf-8")))
from collections import Counter
print(len(rows), Counter(r["verdict"] for r in rows),
... ще 68 символів
```

<details><summary>результат: 2 рядки</summary>

```
0
77 Counter({'live': 60, 'aftermath': 14, 'unclear': 2, 'drone_only': 1}) Counter({('live', 'True'): 60, ('aftermath', 'False'): 14, ('unclear', 'True'): 2, ('drone_only', 'False'): 1})
```

</details>

**Bash**: Read an existing ADR for format

```
cat docs/adr/0005-political-events-without-world.md
```

<details><summary>результат: 18 рядків</summary>

```
# ADR-0005: Політичні події лише Києва і Росії

- Статус: прийнято
- Дата: 2026-10-11

## Контекст

Клас `world` (саміти і зустрічі поза Україною) містив і події про війну (G7, NATO, Рада ЄС, зустрічі з Трампом), і сторонні (війна в Ірані, торгівля, програми першої леді). Питання Jev «чи пов'язує текст подію з війною» прибрало 210 подій разом з G7, NATO і Радою ЄС: дописи Офісу Президента часто лише анонси («провів зустріч з ... Детальніше:»). Обернене питання прибрало б 30, але межа лишалась суб'єктивною.

## Рішення

- Клас `world` прибрано (рішення користувача: «занадто важко відрізнити»). Код далі рахує його, бо він відсікає київських двійників зустрічей за кордоном, а потім відкидає (pol-v9).
- `kyiv` і `russia` без змін, рядок у рядок як у перевіреній pol-v8.

## Наслідки

- Gold втратив `world_imp_today` і `world_days_to_imp4`.
- Гіпотезу «удари приурочують до світових самітів» ця таблиця більше не перевіряє.
```

</details>

**Write**: /home/ye/PROJECTS/ai-school/airalers/docs/adr/0007-audit-before-modelling.md

```
файл: /home/ye/PROJECTS/ai-school/airalers/docs/adr/0007-audit-before-modelling.md, 1906 символів
# ADR-0007: Аудит даних перед моделюванням

- Статус: прийнято
- Дата: 2026-10-11

## Контекст

Дані зібрали агенти, які могли галюцинувати, а тест на витік круговий: він порівнює `features()` на view `ASOF` з тими самими `features()` на повних даних, тож не бачить хибного `available_at`, хибного вікна чи витоку всередині значення. Мітку ніхто не читав погодинно, лише по ночах.

## Рішення

- Перевіряти без коду модулів: усі колонки gold заново простими циклами з silver (погода й астрономія з bronze) з підкладеним витоком, який мусить ловитись (`scripts/verify/audit_recompute.py`), і читанням постів кожної години удару (`data/verification/audit_strike_hours.csv`).
- Мітка: 15 хибних годин (звіти про наслідки в останній годині атаки, реактивний дрон) задати вручну в `CORRECTIONS`. Нове правило години відкинуто: його треба було б знову перевіряти на всіх годинах, з ризиком нових помилок перед здачею.
- Сигнали: пост, чий текст точно написано пізніше за публікацію (службовий «pinned», «станом на HH:MM» пізніше за публікацію), не створює подію (`written_later()`). Прибрати всі події з редагованим першим постом відкинуто: це третина S1, а більшість правок дрібні.
- Невідоме число ракет по Україні NULL, а не 0; `rf_drones_intercepted_1d` лише дрони, як каже назва.
- Рішення ухвалив користувач 2026-10-11; дані не докачуємо, зріз лишається 2026-10-10T17:00Z.

## Наслідки

- Ціль: 151 → 138 рядків true; подій сигналів 9363 → 9361; `ua_missiles_launched_1d` має null у 1114 годинах,
... ще 406 символів
```

<details><summary>результат: 1 рядок</summary>

```
File created successfully at: /home/ye/PROJECTS/ai-school/airalers/docs/adr/0007-audit-before-modelling.md (file state is current in your context — no need to Read it back)
```

</details>

**Bash**: Find the spots to link the audit evidence

```
grep -n "Скрипти й виходи аудиту\|^Виправлено (рішення" docs/data/VERIFICATION.md | cut -c1-120; grep -n "ADR-0006\|зовнішня перевірка (не перебудовує" docs/ARCHITECTURE.md; grep -n "label_check.py          # пише" docs/HANDOFF.md
```

<details><summary>результат: 5 рядків</summary>

```
20:Оркестратор (Claude Opus) і 5 агентів, лише читання, кожен свій модуль; 
31:Виправлено (рішення користувача 2026-10-11): 15 годин мітки (`CORRECTIONS`), п
69:5. зовнішня перевірка (не перебудовує дані): `.venv/bin/python -I scripts/verify/label_check.py`; сигнали за docstring `scripts/verify/signals_check.py`.
77:- [ADR-0006](adr/0006-external-verification.md): зовнішня перевірка мітки і сигналів, виправлення мітки вручну.
64:.venv/bin/python -I scripts/verify/label_check.py          # пише data/verification/label_compare.txt
```

</details>

**Bash**: Read the current audit section of VERIFICATION

```
sed -n 20,32p docs/data/VERIFICATION.md
```

<details><summary>результат: 12 рядків</summary>

```
Оркестратор (Claude Opus) і 5 агентів, лише читання, кожен свій модуль; кожну знахідку, що змінила дані, оркестратор перевірив сам. Скрипти й виходи аудиту не в репозиторії, тут результат.

| Що | Як | Результат |
|---|---|---|
| усі 50 ознак gold | перераховано простими циклами на Python з silver (погода з bronze), без коду модулів, на всіх 3909 годинах, межі вікон окремими синтетичними випадками | 0 розбіжностей |
| `kyiv_alerts` | 561 тривогу заново розібрано з постів VA_Kyiv своїм парсером | збіг до секунди; `available_at` = час поста старту в 562 з 562 |
| `available_at` погоди, ударів по РФ | лаг прогнозу; на якій добі сайт показує кожну атаку на Київ | прогноз з випередженням 9..22 год; gold бачить атаку щонайменше через 19 год після її останньої години удару |
| мітка | прочитано пости кожної з 77 годин удару | 60 удар, 14 звіти про наслідки, 1 реактивний дрон, 2 неясні; 15 виправлено (нижче) |
| сигнали | чи може текст першого поста події бути написаним пізніше | так: 4 події S1 починались на 1.3..5.7 год раніше за свій текст; виправлено (нижче) |
| проба моделлю | логістична регресія, навчання до 2026-08-29, тест на останніх 42 днях | AUC 0.80, лише година доби і темрява 0.78: явного витоку немає, більшість сигналу дає час доби |

Виправлено (рішення користувача 2026-10-11): 15 годин мітки (`CORRECTIONS`), пости, переписані після публікації, не створюють подій сигналів, `ua_missiles_launched_1d` NULL замість 0 у днях без числа ракет, `rf_drones_intercepted_1d` лише дрони. Ціль 151 → 138 рядків true; тест на витік 7 OK.
```

</details>

**Bash**: Link the audit evidence from VERIFICATION, ARCHITECTURE and HANDOFF

```
.venv/bin/python -I - <<'EOF'
from pathlib import Path
edits = {
"docs/data/VERIFICATION.md": [
("кожну знахідку, що змінила дані, оркестратор перевірив сам. Скрипти й виходи аудиту не в репозиторії, тут результат.",
 "кожну знахідку, що змінила дані, оркестратор перевірив сам. Рішення: [ADR-0007](../adr/0007-audit-before-modelling.md). Докази в git: `scripts/verify/audit_recompute.py` з виходом `data/verification/audit_recompute.txt` і `data/verification/audit_strike_hours.csv` (вердикт і пост-доказ для кожної з 77 годин удару; `read_by_orchestrator` позначає 15 виправлених, які оркестратор прочитав сам). Проміжні скрипти агентів не збережено, від них лише висновки нижче."),
("| усі 50 ознак gold | перераховано простими циклами на Python з silver (погода з bronze), без коду модулів, на всіх 3909 годинах, межі вікон окремими синтетичними випадками | 0 розбіжностей |",
 "| усі 50 ознак gold і ціль | перераховано простими циклами на Python з silver (погода й астрономія з bronze), без коду модулів, на всіх 3909 годинах (`audit_recompute.py`); підкладений витік на 1 год скрипт мусить ловити; межі вікон агент перевірив ще й синтетичними випадками | 0 розбіжностей у 51 колонці; підкладений витік змінює 528 і 576 рядків |"),
("Ціль 151 → 138 рядків true; тест на витік 7 OK.",
 "Ціль 151 → 138 рядків true; тест на витік 7 OK.\n\n- Повторити: `.venv/bin/python -I scripts/verify/audit_recompute.py` (пише `data/verification/audit_recompute.txt`, `AUDIT RECOMPUTE PASS`), після кожної
... ще 1728 символів
```

<details><summary>результат: 4 рядки</summary>

```
ok
12:| докази | `data/verification/` | результати зовнішньої перевірки мітки і сигналів (у git) | [VERIFICATION.md](data/VERIFICATION.md) |
31:scripts/verify/                    зовнішня перевірка мітки і сигналів, Workflow агентів, промпти еталонів
69:5. зовнішня перевірка (не перебудовує дані): `.venv/bin/python -I scripts/verify/label_check.py`; сигнали за docstring `scripts/verify/signals_check.py`; незалежний перерахунок усього gold: `.venv/bin/python -I scripts/verify/audit_recompute.py`.
```

</details>

**Bash**: Finish ARCHITECTURE links, check banned characters, rerun checks

```
sed -i '12s/| результати зовнішньої перевірки мітки і сигналів (у git) |/| результати зовнішньої перевірки мітки і сигналів і аудиту перед моделюванням (у git) |/; 31s/зовнішня перевірка мітки і сигналів, Workflow агентів, промпти еталонів/зовнішня перевірка мітки і сигналів, Workflow агентів, промпти еталонів, аудит gold/' docs/ARCHITECTURE.md && sed -n '12p;31p' docs/ARCHITECTURE.md && git diff -U0 | grep "^+" | grep -c -e "·" -e "—"; grep -c -e "·" -e "—" scripts/verify/audit_recompute.py docs/adr/0007-audit-before-modelling.md data/verification/audit_strike_hours.csv data/verification/audit_recompute.txt; .venv/bin/python -I scripts/verify/audit_recompute.py | tail -2; .venv/bin/python -I -m unittest discover -s tests 2>&1 | grep -E "^(OK|FAILED)"
```

<details><summary>результат: 10 рядків</summary>

```
| докази | `data/verification/` | результати зовнішньої перевірки мітки і сигналів і аудиту перед моделюванням (у git) | [VERIFICATION.md](data/VERIFICATION.md) |
scripts/verify/                    зовнішня перевірка мітки і сигналів, Workflow агентів, промпти еталонів, аудит gold
0
scripts/verify/audit_recompute.py:0
data/verification/audit_strike_hours.csv:0
docs/adr/0007-audit-before-modelling.md:0
data/verification/audit_recompute.txt:0
planted leak, rows that differ from gold (must be > 0): alerts_started_3h, alerts known 1 h late: 528, threat_prev_1h, hour flags known 1 h early: 576
AUDIT RECOMPUTE PASS
OK
```

</details>

**Bash**: Commit the audit evidence and the docs

```
git add scripts/verify/audit_recompute.py data/verification/audit_recompute.txt data/verification/audit_strike_hours.csv && git commit -q -m "Add the audit evidence: an independent recompute of gold and the strike hour verdicts

audit_recompute.py recomputes all 51 gold columns by plain loops without
the project modules (0 mismatches) and must catch a planted 1 h leak;
audit_strike_hours.csv holds the verdict and the deciding post of each of
the 77 strike hours read in the audit, the evidence for CORRECTIONS.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git add docs && git commit -q -m "Add ADR-0007 on the audit before modelling and link its evidence

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git status --short && git log --oneline -9
```

<details><summary>результат: 9 рядків</summary>

```
4993513 Add ADR-0007 on the audit before modelling and link its evidence
3607a20 Add the audit evidence: an independent recompute of gold and the strike hour verdicts
ae36f42 Record the audit before modelling and clean stale statements from the docs
024645e Rebuild gold after the audit fixes of the label, signals and RF strikes
4c4d0bb Keep unknown missile launches as NULL and count only drones intercepted
d1a041a Leave posts rewritten after publication out of the signal events
5f35ff0 Correct 15 strike hours that only report damage after the missiles
6ea2cd9 Drop the temp folder note from the handoff: the old agent files are deleted
8ab163c Shorten the five longest docs and fix the statements that were stale
```

</details>

### Claude, 13:17

Аудит задокументовано в репозиторії разом з доказами, які можна перезапустити. Докачку даних не робимо, зріз лишається 2026-10-10T17Z.

**Що тепер є в репозиторії:**
- **`docs/data/VERIFICATION.md`**, розділ «Аудит перед моделюванням»: що перевіряли, як, з яким результатом і що виправили.
- **`docs/adr/0007-audit-before-modelling.md`**: рішення аудиту і від чого відмовились. Відкинуто нове правило мітки, бо перед здачею воно ризикує новими помилками. Відкинуто й видалення всіх редагованих постів, бо це третина сигналів S1.
- **`scripts/verify/audit_recompute.py`**: незалежний перерахунок усіх 51 колонки gold простими циклами, без коду модулів. Результат: 0 розбіжностей. Скрипт сам підкладає витік на 1 год і ловить його в 528 і 576 рядках. Тож це перевірка, що не кругова, на відміну від старого тесту.
- **`data/verification/audit_strike_hours.csv`**: вердикт і пост-доказ для кожної з 77 годин удару. Це доказ для 15 виправлень у мітці; колонка `read_by_orchestrator` позначає 15 годин, які я прочитав сам.
- **`data/verification/audit_recompute.txt`**: вихід скрипта перерахунку.

Посилання на аудит додано в ARCHITECTURE і HANDOFF. Тест на витік 7 OK, усе в 2 нових комітах, без push.

Проміжні скрипти агентів (~2900 рядків) я в репозиторій не клав: це засмітило б його. Вони лишились у scratchpad, а в документах є їхні висновки.
