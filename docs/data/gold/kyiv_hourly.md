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

Зріз це остання година t, яку приймає `features()` кожного модуля: 2026-10-10T17:00:00Z. Код (`find_cutoff`) шукає її діленням навпіл між T0 і поточною годиною: модуль приймає t до кінця своїх даних, тож прийняті години йдуть префіксом. На годині 2026-10-10T18:00:00Z відмовляють два модулі (`ValueError`):

- `alerts`: дані VA_Kyiv закінчуються 2026-10-10T17:11:31Z (ключ `data_until` у Parquet `kyiv_alerts`);
- `threat_hourly`: `label_end` 2026-10-10T17:11:14Z, остання допустима година `floor_hour(label_end)` = 2026-10-10T17:00:00Z.

Інші шість модулів цю годину приймають. Рядків 3909 = годин від T0 до зрізу включно, `t_utc` унікальні й безперервні (крок 1 год). T0 і зріз записані в метаданих Parquet (`t0_utc`, `cutoff_utc`). Дані silver починаються з FETCH_FROM = 2026-04-16T21:00Z, тож вікна до 14 діб повні вже в T0.

## Колонки

Тип це тип у Parquet. День `d` (колонки `hol_*`, `*_imp_today`, `*_days_to_imp4`) це київський календарний день t (`Europe/Kyiv`). Повні означення і час доступності: документи silver у таблиці вище.

| колонка | тип | джерело | означення |
|---|---|---|---|
| `t_utc` | timestamp[us] | вхід | початок години t, UTC |
| `hour_kyiv` | int32 | `t_utc` | година доби за Києвом, 0..23 |
| `dow_kyiv` | int32 | `t_utc` | день тижня за Києвом, 0 = понеділок .. 6 = неділя |
| `alert_active` | bool | `kyiv_alerts` | є тривога зі `start_utc < t`, що триває (кінець порожній або `end_utc >= t`) |
| `alert_active_min` | double | `kyiv_alerts` | хвилин від початку активної тривоги до t; 0, якщо активної немає |
| `alerts_started_3h` | int64 | `kyiv_alerts` | число `start_utc` у `[t - 3 год, t)` |
| `alerts_started_6h` | int64 | `kyiv_alerts` | те саме для `[t - 6 год, t)` |
| `alerts_started_24h` | int64 | `kyiv_alerts` | те саме для `[t - 24 год, t)` |
| `alert_minutes_24h` | double | `kyiv_alerts` | хвилин під тривогою у `[t - 24 год, t)`; тривога без відомого кінця рахується до t |
| `alerts_7d` | int64 | `kyiv_alerts` | число `start_utc` у `[t - 7 діб, t)` |
| `alerts_14d` | int64 | `kyiv_alerts` | число `start_utc` у `[t - 14 діб, t)` |
| `hours_since_alert_end` | double | `kyiv_alerts` | 0, якщо `alert_active`; інакше годин від найпізнішого `end_utc < t` до t |
| `threat_prev_1h` | bool | `kyiv_threat_hourly` | `missile_threat` години `[t - 1 год, t)` |
| `threat_hours_6h` | int64 | `kyiv_threat_hourly` | число годин з `missile_threat` у `[t - 6 год, t)`, 0..6 |
| `threat_hours_24h` | int64 | `kyiv_threat_hourly` | те саме у `[t - 24 год, t)`, 0..24 |
| `ballistic_hours_3h` | int64 | `kyiv_threat_hourly` | число годин з `ballistic` у `[t - 3 год, t)`, 0..3 |
| `ballistic_hours_6h` | int64 | `kyiv_threat_hourly` | те саме у `[t - 6 год, t)`, 0..6 |
| `ballistic_hours_24h` | int64 | `kyiv_threat_hourly` | те саме у `[t - 24 год, t)`, 0..24 |
| `drone_threat_prev_1h` | bool | `kyiv_threat_hourly` | `drone_threat` години `[t - 1 год, t)` |
| `strikes_7d` | int64 | `kyiv_threat_hourly` | число годин з `missile_strike` у `[t - 168 год, t)`, 0..168 |
| `strikes_14d` | int64 | `kyiv_threat_hourly` | те саме у `[t - 336 год, t)`, 0..336 |
| `hours_since_strike` | double | `kyiv_threat_hourly` | годин від кінця останньої години з `missile_strike` до t (0, коли це година `[t - 1 год, t)`); 336, коли за 336 год такої немає |
| `s1_takeoff_6h` | int32 | `prep_signal_events` | події S1 (takeoff або relocation) з `available_at` у `[t - 6 год, t)` |
| `s1_takeoff_24h` | int32 | `prep_signal_events` | те саме у `[t - 24 год, t)` |
| `hours_since_s1` | double | `prep_signal_events` | годин від останньої події S1 з `available_at < t` до t; 336, коли такої немає, не більше 336 |
| `s2_mig31k_airborne` | int32 | `prep_signal_events` | 1, якщо є подія S2 airborne з `available_at` у `[t - 3 год, t)` і після неї до t немає S2 all_clear; інакше 0 |
| `s4_drone_waves_6h` | int32 | `prep_signal_events` | події S4 launch з `available_at` у `[t - 6 год, t)` |
| `wx_cloud_mean_3h` | double | `weather_runs` | середнє `cloud_cover_pct` годин `t`, `t + 1 год`, `t + 2 год`, % |
| `wx_precip_sum_3h` | double | `weather_runs` | сума `precipitation_mm` тих трьох годин, мм |
| `wx_wind_max_3h` | double | `weather_runs` | максимум `wind_speed_10m_kmh`, км/год |
| `wx_visibility_min_3h` | double | `weather_runs` | мінімум `visibility_m`, м |
| `dark_share_3h` | double | `astro_hourly` | середнє `dark_civil_frac` годин `t`, `t + 1 год`, `t + 2 год`: частка вікна `[t, t + 3 год)` з цивільною темрявою |
| `moon_illum` | double | `astro_hourly` | `moon_illum` години t |
| `hol_rf_symb_today` | double | `calendar_dates` | максимум `symbolism` дат групи RF дня d; 0, якщо немає |
| `hol_ua_symb_today` | double | `calendar_dates` | те саме для групи UA |
| `hol_high_tomorrow` | bool | `calendar_dates` | наступний день має дату `high` будь-якої групи |
| `hol_days_to_next_high` | int32 | `calendar_dates` | цілих днів від d до найближчої дати `high`: 0 сьогодні; не більше 14 (14 і коли такої немає) |
| `kyiv_imp_today` | int32 | `political_events` | найбільший `importance` (0..5) подій класу `kyiv` з `event_date <= d <= end_date` і `available_at < t` (для події з Вікіпедії її остання версія, відома до t); 0, якщо подій немає. Класу `world` немає (рішення користувача 2026-10-11) |
| `russia_imp_today` | int32 | `political_events` | те саме для класу `russia` |
| `kyiv_days_to_imp4` | int32 | `political_events` | цілих днів від d до найближчої події класу `kyiv` з `importance >= 4`, `end_date >= d`, `available_at < t`; 0, якщо вона сьогодні або триває; не більше 14 (14 і коли такої немає) |
| `russia_days_to_imp4` | int32 | `political_events` | те саме для класу `russia` |
| `rf_points_1d` | int32 | `strike_points` | точок ударів по Росії (без окупованих територій України) найновішого відомого дня: `available_at` у `[t - 24 год, t)`; день d відомий з d + 30 год |
| `rf_points_3d` | int32 | `strike_points` | те саме за три найновіші відомі дні: `[t - 72 год, t)` |
| `rf_regions_3d` | int32 | `strike_points` | різних регіонів Росії серед цих точок за три дні |
| `rf_energy_1d` | int32 | `strike_points` | точок, чий опис цілі називає НПЗ, нафто- чи паливну базу, енергомережу, електростанцію, підстанцію, газовий об'єкт, за день |
| `rf_energy_3d` | int32 | `strike_points` | те саме за три дні |
| `rf_moscow_3d` | int32 | `strike_points` | 1, якщо за три дні є точка в Москві чи Московській області |
| `rf_drones_intercepted_1d` | int32 | `strike_days` | дронів (без ракет), яких МО РФ заявило збитими за найновіший відомий день |
| `ua_missiles_launched_1d` | int32 | `strike_days` | ракет, запущених по Україні за найновіший відомий день (Повітряні сили, верх діапазону); null, коли сайт не має числа ракет для цього дня |
| `ua_drones_launched_1d` | int32 | `strike_days` | дронів, запущених по Україні за той самий день |
| `hours_since_rf_energy` | double | `strike_points` | годин від `available_at` останньої точки енергетики до t; не більше 336 |
| `y_strike_3h` | bool | `kyiv_threat_hourly` | ціль: див. нижче |

## Ціль

`y_strike_3h` = true, якщо хоч одна година з `[t, t + 3 год)` має `missile_strike` у `kyiv_threat_hourly`. Це єдина колонка, що дивиться вперед, і її рахує лише `labels()`. Null, коли t + 3 год пізніше за `label_end`: три останні рядки, 2026-10-10T15:00Z, 16:00Z, 17:00Z.

Рядків з міткою 3906: true 138, false 3768, база 138/3906 = 0.0353. Годин `missile_strike` у `kyiv_threat_hourly` від T0 62 (з 3908 годин таблиці від T0), з них 17 виправлено вручну (`CORRECTIONS`, [kyiv_threat_hourly.md](../silver/kyiv_threat_hourly.md)). Перша така година 2026-05-14T00:00Z, до T0 жодної. 138 рядків true дають 35 серій поспіль (атак); у 33 з них удар був і в останні 3 години (атака вже йде), тож прогноз початку атаки варто оцінювати окремо.

## Null

Null у двох колонках: `y_strike_3h` 3 з 3909 (частка 0.000767) і `ua_missiles_launched_1d` 1114 (0.284983: сайт не має числа ракет для 55 днів; модель має заповнити це сама, 0 тут означав би «ракет не було»). В інших 50 колонках null немає, зокрема в `wx_*`, `dark_share_3h` і `moon_illum`. Частки по колонках друкує `report` (блок `null share per column`).

## Як перебудувати

```
# спершу silver у порядку з ARCHITECTURE.md; gold читає їх такими, які вони є
choom -n 500 -- .venv/bin/python -I -m airalerts.gold.kyiv_hourly   # збірка data/gold/kyiv_hourly.parquet і звіт, кілька секунд
.venv/bin/python -I -m airalerts.gold.kyiv_hourly report            # лише звіт про наявний файл
.venv/bin/python -I -m airalerts.db                                 # view над silver і gold у data/airalerts.duckdb
choom -n 500 -- .venv/bin/python -I -m unittest discover -s tests -v   # тест на витік
```

Збірка одна команда і дає ту саму таблицю, якщо silver не змінився. Зміна будь-якої таблиці silver (наприклад, нова збірка `political_events`) робить gold застарілим: перезапустити збірку, потім `airalerts.db`, потім тест. Тест 02 ловить такий випадок.

## Тест на витік

`tests/test_no_leakage.py`, stdlib `unittest`, 7 тестів:

1. форма: перші колонки `t_utc`, `hour_kyiv`, `dow_kyiv`, далі колонки `features()` модулів у порядку модулів, остання `y_strike_3h`; години від T0 до зрізу безперервні й унікальні;
2. gold не старший за таблиці silver, які читають модулі (час зміни файлів);
3. 50 випадкових t (seed 20261011): для кожного t нове з'єднання DuckDB, на ньому лише view з `ASOF` усіх модулів для цього t (таблиці, якими їх знали перед t); `features()` кожного модуля на цих view порівняно з рядком gold, точна рівність без допуску; тест вимагає, щоб `ASOF` щось ховали;
4. `hour_kyiv` і `dow_kyiv` усіх рядків проти `zoneinfo` (`Europe/Kyiv`);
5. ціль перерахована з `kyiv_threat_hourly` (`missile_strike` у `[t, t + 3 год)`, null за `label_end`) і збігається з виходом `labels()`;
6. жодна колонка ознак не дорівнює `y_strike_3h` чи її запереченню;
7. `labels()` не викликає жодна `features()`: статично (імена в коді `features()` і функцій того ж модуля, на які вона посилається) і динамічно (`labels` замінено на заглушку, що падає).

Результат: 7 тестів OK. У тесті 3 порівняно 2400 значень (50 t, 8 модулів, 48 колонок ознак), різниць 0.

Команда `.venv/bin/python -I -m unittest tests/test_no_leakage.py` падає на імпорті (`ModuleNotFoundError: No module named 'tests'`): `-I` прибирає поточну теку з `sys.path`. Працюють `discover -s tests` (вище), `.venv/bin/python -I tests/test_no_leakage.py` і та сама команда без `-I`.

## Перевірка

| команда | результат |
|---|---|
| `.venv/bin/python -I -m airalerts.gold.kyiv_hourly report` | `rows 3909, columns 52`, `hours from T0 to cutoff inclusive 3909`, `rows = hours True, unique True, continuous (every step 1 h) True`; `labelled rows 3906, true 138, false 3768, null 3`; `base rate = true / labelled = 138/3906 = 0.0353`; `strike hours ... from T0: 62 of 3908`; null у `y_strike_3h` 3 і в `ua_missiles_launched_1d` 1114; 5 випадкових рядків з усіма колонками |
| `.venv/bin/python -I -m airalerts.db` | 12 view: 11 silver і `kyiv_hourly` |
| `.venv/bin/python -I -c "from airalerts.db import connect; from airalerts.paths import DB; print(connect(DB).execute('SELECT count(*), count(*) FILTER (WHERE y_strike_3h) FROM kyiv_hourly').fetchone())"` | `(3909, 138)` |
| `.venv/bin/python -I -c "from airalerts.db import connect; from airalerts.paths import DB; print(connect(DB).execute('SELECT min(t_utc) FILTER (WHERE y_strike_3h) FROM kyiv_hourly').fetchone()[0])"` | `2026-05-13 22:00:00` |
| `choom -n 500 -- .venv/bin/python -I -m unittest discover -s tests -v` | `Ran 7 tests`, `OK`; `50 random t (seed 20261011) ... 2400 feature values compared ... differences 0` |
| `.venv/bin/python -I -m unittest tests/test_no_leakage.py` | `ModuleNotFoundError: No module named 'tests'` |
| `.venv/bin/python -I -c "from airalerts.silver import rf_strikes; print(rf_strikes.data_end())"` | `2026-10-11 08:00:00` |
| `.venv/bin/python -I -c "from airalerts.silver import political_events; print(political_events.data_end())"` | `2026-10-10 17:00:00` |
| `.venv/bin/python -I -c "import pyarrow.parquet as pq; print(pq.read_metadata('data/silver/prep_signal_events.parquet').metadata[b'data_until'].decode())"` | `2026-10-10T11:36:43Z` |
| `.venv/bin/python -I -c "from airalerts.db import connect, register_layers; print(register_layers(connect()).execute('SELECT min(hour_utc) FROM kyiv_threat_hourly WHERE missile_strike').fetchone()[0])"` | `2026-05-14 00:00:00` |

## Пастки

- Три останні рядки (2026-10-10T15:00Z, 16:00Z, 17:00Z) мають `y_strike_3h` null: для навчання їх відкинути.
- `rf_*` і `ua_*` бачать день лише через 30 год після його початку (UTC): ознака о t описує вчорашній або позавчорашній день, не останні години. `rf_strikes.data_end()` = 2026-10-11 08:00:00 (знімок dronestrikemap), пізніші t модуль відхиляє.
- Дані одного модуля закінчуються раніше за зріз, а його `features()` t не відхиляє: `prep_signal_events` має `data_until` 2026-10-10T11:36:43Z (останній пост `war_monitor`). Для t після цього `s1_*`, `s2_*`, `s4_*` не бачать постів, яких немає в silver: їх не було або bronze їх не забрав, gold цього не розрізняє. `political_events` повні до зрізу (`data_end()` = 2026-10-10 17:00:00).
- До 2026-05-14T00:00Z у `kyiv_threat_hourly` немає годин удару (до T0 теж): у рядку T0 `strikes_14d` 0 і `hours_since_strike` 336 (стеля), ціль false для всіх t до 2026-05-13T22:00Z.
- Мітки сусідніх годин перекриваються: `[t, t + 3 год)` і `[t + 1 год, t + 4 год)` мають спільні 2 години.
- `hour_kyiv`, `dow_kyiv`, `hol_*` і політичні колонки рахуються за київським часом: UTC+3 до 2026-10-25, далі UTC+2. Зріз раніший за цю дату; після неї `hour_kyiv` = година UTC + 2.
- `wx_*` це прогноз на вікно `[t, t + 3 год)` з прогонів, відомих до t (`available_at` = час прогону + 8 год), а не спостереження. `dark_share_3h` і `moon_illum` рахуються формулами.
- `data/gold/` не в `.gitignore` (на відміну від `data/silver/` і `data/airalerts.duckdb`).
