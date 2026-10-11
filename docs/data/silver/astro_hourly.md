# astro_hourly

Silver, клас «астрономія»: `data/silver/astro_hourly.parquet`, будівник `src/airalerts/silver/astro.py`. Правила рівнів: [ARCHITECTURE.md](../../ARCHITECTURE.md), джерело: [PARSING.md](../PARSING.md) розділ 4.

## Що це

Один рядок = одна година UTC для Києва (50.4501, 30.5234): висота Сонця на початку години, частка хвилин години з цивільною темрявою, освітленість і фаза Місяця на початку години.

## Bronze

- `data/bronze/astro/kyiv_astro_hourly.csv`: `hour_utc, sun_alt_deg, dark_civil, dark_nautical, moon_illum, moon_phase`, 4608 рядків від 2026-04-23T00:00:00Z до 2026-10-31T23:00:00Z.
- `data/bronze/astro/kyiv_astro_daily.csv`: 192 рядки, `date_kyiv` від 2026-04-23 до 2026-10-31 (у silver не береться).
- Рахуються локально, без мережі: `python3 -I scripts/bronze/kyiv_astro.py build data/bronze/astro` (stdlib, формули NOAA/Meeus для Сонця, Meeus розділ 48 для Місяця, формули не змінені). Період за замовчуванням 2026-04-23..2026-10-31, змінюється опціями `--from YYYY-MM-DD` і `--to YYYY-MM-DD`. Побудовано 2026-10-10T17:37:16Z; повторна побудова дає ті самі байти (`sha256sum -c` OK).

## Колонки

| колонка | тип | опис |
|---|---|---|
| hour_utc | TIMESTAMP (UTC) | початок години, ключ |
| sun_alt_deg | DOUBLE | висота центру Сонця на початку години, градуси (bronze, до 0.01) |
| dark_civil_frac | DOUBLE | частка з 60 хвилин `hour_utc + 0..59 хв` (на початку кожної хвилини), коли центр Сонця нижче -6 градусів (`kyiv_astro.sun_alt`) |
| moon_illum | DOUBLE | освітлена частка диска Місяця, 0..1, на початку години |
| moon_phase | DOUBLE | 0 новий Місяць, 0.25 перша чверть, 0.5 повня, 0.75 остання чверть |
| available_at | TIMESTAMP (UTC) | 2000-01-01 00:00:00 |

## Час доступності

`available_at = 2000-01-01 00:00:00`: усе рахується формулами і відоме наперед, тож `ASOF["astro_hourly"] = SELECT * FROM astro_hourly WHERE available_at < {t}` повертає всю таблицю для будь-якого t.

## Ознаки для gold

`features(con, t_table)` повертає `t_utc` першою колонкою і рівно один рядок на `t_utc` (t це повна година UTC):

| колонка | визначення |
|---|---|
| dark_share_3h | середнє `dark_civil_frac` по годинах t, t+1 год, t+2 год: частка хвилин вікна [t, t+3 год) з цивільною темрявою |
| moon_illum | `moon_illum` години t |

NULL, якщо таблиця не покриває ці години (t+2 год пізніше за 2026-10-31T23:00Z).

## Як перебудувати

```bash
python3 -I scripts/bronze/kyiv_astro.py build data/bronze/astro   # bronze
.venv/bin/python -I -m airalerts.silver.astro                     # silver: data/silver/astro_hourly.parquet
```

## Перевірка

- `python3 -I scripts/bronze/kyiv_astro.py day 2026-10-10` друкує рівно 5 рядків блоку з PARSING розділ 4 (`diff` порожній).
- `build` друкує `192 daily rows, 4608 hourly rows`.
- Silver: `astro_hourly: 4608 rows 2026-04-23 00:00:00..2026-10-31 23:00:00`; рядків стільки ж, скільки в bronze; `available_at` скрізь 2000-01-01.
- `dark_civil_frac`: 1469 годин = 1, 2760 годин = 0, 379 годин між 0 і 1. Немає годин, де bronze `dark_civil` = 1, а частка 0, чи `dark_civil` = 0, а частка 1.

Ознаки на кожну годину від 2026-04-30T21:00Z до 2026-10-10T17:00Z:

```bash
.venv/bin/python -I - <<'PY'
from airalerts.db import connect
from airalerts.paths import SILVER
from airalerts.silver import astro
con = connect()
con.execute(f"CREATE VIEW astro_hourly AS SELECT * FROM read_parquet('{SILVER}/astro_hourly.parquet')")
con.execute("CREATE TABLE tt AS SELECT t AS t_utc FROM generate_series(TIMESTAMP '2026-04-30 21:00:00', TIMESTAMP '2026-10-10 17:00:00', INTERVAL 1 HOUR) g(t)")
rows = astro.features(con, "tt").to_pylist()
by = {r["t_utc"].strftime("%Y-%m-%dT%H"): r for r in rows}
print(len(rows), by["2026-07-01T21"]["dark_share_3h"], by["2026-07-01T09"]["dark_share_3h"],
      min(r["moon_illum"] for r in rows), max(r["moon_illum"] for r in rows))
PY
```

Результат: `3909 1.0 0.0 0.0 1.0`: `dark_share_3h` 1.0 о 2026-07-01T21:00Z і 0.0 о 2026-07-01T09:00Z, `moon_illum` в [0, 1], NULL немає.

Решта перевірок (окремий скрипт поза репозиторієм, усі пройшли):

- 40 випадкових t: `dark_share_3h` збігається (різниця 0.0) з прямим підрахунком по 180 хвилинах вікна, `moon_illum` збігається з bronze;
- 3 випадкових t (2026-05-11T13:00, 2026-10-05T23:00, 2026-06-06T02:00): `features()` на таблиці з `ASOF` дає ті самі значення, що повний розрахунок.

## Пастки

- Темрява це цивільні сутінки (-6 градусів), не навігаційні. 379 годин біля заходу і сходу мають частку між 0 і 1.
- `sun_alt_deg` це висота на початку години (з bronze, округлена до 0.01), а `dark_civil_frac` рахується з неокругленої висоти в кожній з 60 хвилин, тому на межі сутінків вони не обов'язково узгоджені.
- Місяць лише освітленість і фаза на початку години; схід і захід Місяця не рахуються.
- `SELECT min(moon_illum)` у DuckDB 1.5.6 показує `-0.0`, хоча від'ємних нулів у даних немає (0 з 4608 у кожній числовій колонці): перевіряйте `>= 0`.
- Таблиця закінчується 2026-10-31T23:00Z; для пізніших t ознаки NULL. Продовжити: `build` з `--to`, потім `-m airalerts.silver.astro`.
- Будівник silver завантажує `scripts/bronze/kyiv_astro.py` за шляхом файлу (importlib), без копії формул.
- Усе в UTC; перехід Києва на зимовий час 2026-10-25 на годинах UTC не позначається.
