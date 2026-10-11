# weather_runs

Silver, клас «погода»: `data/silver/weather_runs.parquet`, будівник `src/airalerts/silver/weather.py`. Правила рівнів: [ARCHITECTURE.md](../../ARCHITECTURE.md), джерело: [PARSING.md](../PARSING.md) розділ 3.

## Що це

Один рядок = прогноз ECMWF IFS для центру Києва на одну годину `valid_utc` з одного прогону `run_utc` (прогони кожні 6 год, у прогоні 168 годин). Ключ (`run_utc`, `valid_utc`) унікальний.

## Bronze

- `data/bronze/weather/openmeteo_single_runs/ecmwf_ifs_<YYYYMMDDTHH>.json`: відповідь як є, файл на прогін (681 файл).
- `data/bronze/weather/ecmwf_ifs_runs.csv`: рядок на пару (прогін, година), 114 408 рядків = 168 x 681.
- `data/bronze/weather/ecmwf_ifs_missing_runs.csv`: прогони з HTTP 400 (`run_utc, http_status, reason, checked_at_utc`), 1 рядок: 2026-06-10T12:00.
- Джерело: Open-Meteo Single Runs API, `models=ecmwf_ifs`, `timezone=UTC`, координати 50.4501, 30.5234 (вузол сітки 50.439365, 30.476192, висота 155 м). Змінні: `cloud_cover, precipitation, wind_speed_10m, wind_gusts_10m, wind_direction_10m, visibility`.
- Забір: `python3 -I scripts/bronze/wx_backfill.py` (stdlib). Прогони кожні 6 год від 2026-04-23T00:00 до найновішого, чия `last_run_availability_time` з `https://api.open-meteo.com/data/ecmwf_ifs/static/meta.json` уже в минулому (2026-10-10T06:00). Один запит за раз, пауза 1 с, браузерний User-Agent, повтор через 4, 8, 16, 32 с на HTTP 429, 5xx і помилки мережі. Забір 2026-10-10T17:37:24Z..17:50:37Z (`fetched_at_utc` у CSV).
- Докачування: прогін із файлом не забирається знову, рядки прогону в CSV не пишуться вдруге (є файл без рядків: рядки відновлюються з файлу). HTTP 400 дописує рядок у `ecmwf_ifs_missing_runs.csv`; такий прогін молодший за 48 год перепитується, старший ні.
- `python3 -I scripts/bronze/wx_fetch_run.py <тека> <прогін>...` пише той самий формат, але без захисту від дублів: не запускати на прогони, що вже є в CSV.

## Колонки

| колонка | тип | опис |
|---|---|---|
| run_utc | TIMESTAMP (UTC) | старт прогону |
| valid_utc | TIMESTAMP (UTC) | година, на яку прогноз |
| lead_h | INTEGER | `valid_utc - run_utc`, годин (0..167) |
| cloud_cover_pct | DOUBLE | хмарність, % |
| precipitation_mm | DOUBLE | опади за попередню годину, мм |
| wind_speed_10m_kmh | DOUBLE | вітер на 10 м, км/год |
| wind_gusts_10m_kmh | DOUBLE | пориви на 10 м, км/год |
| wind_direction_10m_deg | DOUBLE | напрям вітру, градуси |
| visibility_m | DOUBLE | видимість, м (модельна) |
| available_at | TIMESTAMP (UTC) | `run_utc + 8 год` |

Порожня клітинка bronze = NULL. Дублі за ключем прибирає `main()` (лишає рядок з меншим `fetched_at_utc`): у цьому запуску 0.

## Час доступності

`available_at = run_utc + 8 год`. За `meta.json` прогін 2026-10-10T06:00 був готовий о 12:22:53Z, затримка 6.38 год; 8 год це запас. Це правило, а не час забору: `fetched_at_utc` у bronze лише час бекфілу. Перед моментом t відомі рядки з `available_at < t`: `ASOF["weather_runs"] = SELECT * FROM weather_runs WHERE available_at < {t}`.

## Ознаки для gold

`features(con, t_table)` повертає `t_utc` першою колонкою і рівно один рядок на `t_utc` (t це повна година UTC). Для t беремо прогони з `available_at < t`. Для кожної години v з {t, t+1 год, t+2 год} і кожної змінної беремо значення найновішого такого прогону; порожнє значення береться зі старшого прогону, який його має. Далі по трьох годинах:

| колонка | визначення | одиниця |
|---|---|---|
| wx_cloud_mean_3h | середнє `cloud_cover_pct` | % |
| wx_precip_sum_3h | сума `precipitation_mm` | мм |
| wx_wind_max_3h | максимум `wind_speed_10m_kmh` | км/год |
| wx_visibility_min_3h | мінімум `visibility_m` | м |

NULL, якщо для однієї з трьох годин значення немає в жодному відомому прогоні. Порядок додавання фіксований, тож результат не залежить від порядку рядків.

## Як перебудувати

```bash
python3 -I scripts/bronze/wx_backfill.py          # bronze: докачує лише відсутні прогони, друкує звіт
.venv/bin/python -I -m airalerts.silver.weather   # silver: data/silver/weather_runs.parquet з нуля
```

Пробний запуск без запису в `data/bronze`: `--out <тека> --from 2026-06-10T00:00 --to 2026-06-10T18:00`; `--dry-run` лише друкує план.

## Перевірка

Числа нижче це стан на 2026-10-10T18:36Z: найновіший прогін 2026-10-10T06:00, а прогін 12:00 за `meta.json` ще не вийшов. Коли `wx_backfill.py` додасть нові прогони, кількість файлів і рядків зросте.

Bronze (`python3 -I scripts/bronze/wx_backfill.py`, звіт у кінці):

- прогонів у діапазоні 682 (2026-04-23T00:00..2026-10-10T06:00); HTTP 400: 1 (2026-06-10T12:00); файлів 681 = 682 - 1 (множини збігаються); рядків CSV 114 408 = 168 x 681, прогонів з іншою кількістю рядків немає; помилок і повторів немає;
- другий запуск: `to fetch 0`, `fetched this run: 0`.

Silver (`.venv/bin/python -I -m airalerts.silver.weather`): `weather_runs: 114408 rows, 681 runs 2026-04-23 00:00:00..2026-10-10 06:00:00, duplicates dropped 0`; `valid_utc` від 2026-04-23T00:00 до 2026-10-17T05:00; ключ унікальний (114 408 різних пар); `available_at = run_utc + 8 год` у всіх рядках, збігається з `available_at_utc` у CSV.

Ознаки на кожну годину від 2026-04-30T21:00Z до 2026-10-10T17:00Z:

```bash
.venv/bin/python -I - <<'PY'
import pyarrow.compute as pc
from airalerts.db import connect
from airalerts.paths import SILVER
from airalerts.silver import weather
con = connect()
con.execute(f"CREATE VIEW weather_runs AS SELECT * FROM read_parquet('{SILVER}/weather_runs.parquet')")
con.execute("CREATE TABLE tt AS SELECT t AS t_utc FROM generate_series(TIMESTAMP '2026-04-30 21:00:00', TIMESTAMP '2026-10-10 17:00:00', INTERVAL 1 HOUR) g(t)")
t = weather.features(con, "tt")
print(t.num_rows, t.column_names)
for c in t.column_names[1:]:
    print(c, "nulls", t[c].null_count, "min", pc.min(t[c]).as_py(), "max", pc.max(t[c]).as_py())
PY
```

Результат: 3909 рядків, 0 NULL у всіх колонках; `wx_cloud_mean_3h` 0.0..100.0, `wx_precip_sum_3h` 0.0..15.2, `wx_wind_max_3h` 0.6..25.8, `wx_visibility_min_3h` 240.0..54920.0.

Решта перевірок (окремий скрипт поза репозиторієм, усі пройшли):

- 60 випадкових t: ознаки збігаються (різниця 0.0) з незалежним перерахунком на чистому Python за означенням (найновіший відомий прогін, порожнє зі старшого);
- 3 випадкових t (2026-05-11T13:00, 2026-10-05T23:00, 2026-06-06T02:00): `features()` на таблиці з `ASOF` (відомо рядків 12 264, 111 216 і 29 400 з 114 408) дає ті самі значення, що повний розрахунок.

## Пастки

- Порожнє лишається NULL у silver, заповнює його лише `features()`. NULL у 114 408 рядках: хмарність 7938, опади 8881, вітер 8323, пориви 8881, напрям 8323, видимість 8296. На `lead_h` 0 опади і пориви порожні в усіх 681 прогонах.
- Звичайний прогін: 00 і 12 UTC мають усі змінні до `lead_h` 167, 06 і 18 UTC до `lead_h` 144 (23 порожні години в кінці); опади і пориви з `lead_h` 1. Так виглядають 675 з 681 прогонів.
- Шість прогонів мають прогалини вже в джерелі: свіжий запит до API 2026-10-10 дає для кожного з них ті самі `hourly` і `hourly_units`, що сирий файл у bronze. Решта змінних цих прогонів звичайна.

| прогін | порожні змінні |
|---|---|
| 2026-06-11T00:00 | усі шість: значення лише до `lead_h` 72 |
| 2026-06-22T18:00 | вітер і напрям: усі 168 годин |
| 2026-06-23T00:00 | опади, вітер, пориви, напрям, видимість: усі 168 годин (є лише хмарність) |
| 2026-08-26T12:00 | опади і видимість: лише до `lead_h` 72 |
| 2026-09-18T18:00 | вітер і напрям: лише до `lead_h` 72 |
| 2026-09-19T00:00 | пориви і видимість: лише до `lead_h` 72 |

- Зі старшого прогону береться мало: з 11 727 пар (t, година) на змінну хмарність 0, опади 18, вітер 36, видимість 18. Усі 72 випадки йдуть від двох прогонів без цілої змінної: 2026-06-22T18:00 (вітер) і 2026-06-23T00:00 (опади, вітер, видимість). Найбільший `lead_h` взятої клітинки 28 (вітер), для решти змінних 22, тож прогалини після `lead_h` 72 до ознак не доходять.
- Вік найновішого прогону в момент t від 9 до 20 год; 20 год після пропущеного 2026-06-10T12:00.
- Опади це сума за попередню годину, тож години t, t+1, t+2 покривають інтервал (t - 1 год, t + 2 год].
- Це вузол моделі, не станція; видимість модельна; вітер у км/год.
- Ознаки не NULL аж до t = 2026-10-16T21:00Z (прогноз наперед за останнім прогоном). Gold мусить сам обмежити t датою зрізу даних.
- Open-Meteo безкоштовний лише для некомерційного використання, дані CC BY 4.0 (PARSING розділ 3).
