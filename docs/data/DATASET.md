# Набір даних: заморожена версія

Ця версія даних, на якій навчено й оцінено всі моделі в `reports/`. Зріз: **2026-10-10T17:00Z** (остання година t, яку приймає кожен модуль silver; див. [kyiv_hourly.md](gold/kyiv_hourly.md), розділ «Зріз»). Таблиці gold лежать у git, silver і bronze ні. Як дані зібрано: [PARSING.md](PARSING.md); чому їм можна довіряти: [VERIFICATION.md](VERIFICATION.md); рівні й контракт: [ARCHITECTURE.md](../ARCHITECTURE.md).

## Таблиці gold

Розробка це рядки, чия ціль уже відома на початок тесту 2026-08-29T09:00Z (12:00 за Києвом, [ADR-0008](../adr/0008-time-split.md)): t + 3 год ≤ початок тесту для погодинних таблиць, t + 10 год для нічної. Частку цілі тут пораховано лише на розробці; тест сюди не входить.

| Таблиця | Епоха | Рядки | Колонки | Період (t_utc) | Ціль | Частка цілі на розробці | Опис |
|---|---|---|---|---|---|---|---|
| `kyiv_hourly` | 1, удари | 3909 годин | 52 | 2026-04-30T21:00Z .. 2026-10-10T17:00Z | `y_strike_3h`: ракетний удар по Києву в [t, t + 3 год); null у 3 останніх рядках | 107 з 2890 (3.7%) | [kyiv_hourly.md](gold/kyiv_hourly.md) |
| `kyiv_nightly` | 2, ночі | 159 ночей | 63 | 2026-05-04T19:00Z .. 2026-10-09T19:00Z (ночі 2026-05-04 .. 2026-10-09, рішення о 22:00 за Києвом) | `y_night`: ракетний удар по Києву з 22:00 D до 08:00 D+1 | 23 з 117 (19.7%) | [kyiv_nightly.md](gold/kyiv_nightly.md) |
| `kyiv_quiet` | 3, спокій | 3909 годин | 70 | 2026-04-30T21:00Z .. 2026-10-10T17:00Z | `y_busy_3h`: дрони, ракетна загроза або удар в одній з годин t, t + 1, t + 2; null у 3 останніх рядках | 975 з 2890 (33.7%); на годинах «зараз тихо» (`quiet_now`) 650 з 2387 (27.2%) | [kyiv_quiet.md](gold/kyiv_quiet.md) |

У `kyiv_quiet` є ще дві частини цілі для моделей з двома «головами»: `y_drone_3h` 526 з 2890 (18.2%), `y_missile_3h` 664 з 2890 (23.0%) на розробці.

Контрольні суми файлів (`sha256sum data/gold/*.parquet`, 2026-10-11):

```
3e2a420b207ccdd07e4700057990734a6b371c9ff90ba03b8bf0f8d634e049eb  data/gold/kyiv_hourly.parquet
f04ecde7e03cc340b4de03f2244cb762ab3dd8e5978c77e14ad7a6c062d9f065  data/gold/kyiv_nightly.parquet
fd71ec155a222f078ebd0ce6b5227414fef1b3bcb1122917fc69eef7936c76ac  data/gold/kyiv_quiet.parquet
```

Рядки, колонки, період і частки пораховано прямо з цих файлів (`pyarrow`, рядки з t + H ≤ 2026-08-29T09:00Z, без null у цілі):

```
.venv/bin/python -I -c "
import pyarrow.parquet as pq; from datetime import datetime, timedelta
T = datetime(2026, 8, 29, 9)
for name, y, h in (('kyiv_hourly', 'y_strike_3h', 3), ('kyiv_nightly', 'y_night', 10), ('kyiv_quiet', 'y_busy_3h', 3)):
    t = pq.read_table(f'data/gold/{name}.parquet')
    d = [v for v, s in zip(t[y].to_pylist(), t['t_utc'].to_pylist()) if v is not None and s.replace(tzinfo=None) + timedelta(hours=h) <= T]
    print(name, t.num_rows, t.num_columns, sum(d), len(d))"
```

## Таблиці silver

11 таблиць у `data/silver/*.parquet` (не в git); кожна має `available_at`, коли рядок став відомим.

| Таблиця | Що | Опис |
|---|---|---|
| `kyiv_alerts` | тривоги по місту Київ як інтервали, з постів КМВА | [kyiv_alerts.md](silver/kyiv_alerts.md) |
| `tg_posts` | усі пости 17 Telegram-каналів в одній таблиці, з класами за regex | [tg_posts.md](silver/tg_posts.md) |
| `kyiv_threat_hourly` | мітки загроз і ракетного удару по Києву за годинами: пости 7 каналів, оцінки Jev, правило години | [kyiv_threat_hourly.md](silver/kyiv_threat_hourly.md) |
| `kyiv_threat_posts` | відповідь Jev на кожен пост, що пройшов префільтр | [kyiv_threat_hourly.md](silver/kyiv_threat_hourly.md) |
| `prep_signal_events` | події підготовки удару: стратегічна авіація (S1), МіГ-31К (S2), хвилі ударних дронів (S4) | [prep_signal_events.md](silver/prep_signal_events.md) |
| `strike_points`, `strike_days` | удари по Росії і запуски по Україні з dronestrikemap.com: точки і підсумки дня | [rf_strikes.md](silver/rf_strikes.md) |
| `weather_runs` | прогони прогнозу ECMWF IFS для центру Києва, з часом видачі | [weather_runs.md](silver/weather_runs.md) |
| `astro_hourly` | сонце і місяць над Києвом погодинно | [astro_hourly.md](silver/astro_hourly.md) |
| `calendar_dates` | символічні дати Росії і України з оцінкою Jev | [calendar_dates.md](silver/calendar_dates.md) |
| `political_events` | політичні події Києва і Росії (візити, саміти, зустрічі, переговори) | [political_events.md](silver/political_events.md) |

Кеш відповідей Jev лежить у `data/silver/_jev_cache/`: без нього перебудова мітки коштує гроші і дає трохи інші числа ([HANDOFF.md](../HANDOFF.md)).

## Відомі вади даних

- **Тривога 391 склеєна.** VA_Kyiv пропустив відбій, тож у даних вона триває 1057 хв, тобто 17.6 год (2026-09-17T18:57Z .. 2026-09-18T12:34Z, [kyiv_alerts.md](silver/kyiv_alerts.md)). Так її бачили і в реальному часі, тому не виправлено; прогноз весь цей час каже «зараз неспокійно» ([forecast.md](../quiet/forecast.md)).
- **Дронова мітка правильна приблизно у 80%.** Агент прочитав пости 50 годин розробки: з 25 «дронових» годин правильні 20; хибні це переважно звіти про наслідки і дрони в області без тривоги в Києві ([ADR-0011](../adr/0011-quiet-hours.md)). Висновки про дронову частину `y_busy_3h` слабші за ракетну.
- **Мітку удару виправлено вручну.** Список `CORRECTIONS` у `src/airalerts/silver/threat_hourly.py`: спершу зовнішня перевірка знайшла одну пропущену і одну зайву годину, потім аудит 15 хибних з 77 годин удару; годин удару стало 62, `y_strike_3h` true 151 → 138 ([kyiv_threat_hourly.md](silver/kyiv_threat_hourly.md), [ADR-0006](../adr/0006-external-verification.md), [ADR-0007](../adr/0007-audit-before-modelling.md)). Виправлення зроблено після подій, у живому продукті їх не буде.
- **Вікіпедія в найновішій ревізії.** Набір політичних подій береться з останньої ревізії сторінок: 18 подій, що були на сторінці, але зникли до неї, у таблиці немає ([political_events.md](silver/political_events.md)). Це втрата, а не знання майбутнього.
- `ua_missiles_launched_1d` порожнє (null) у 1114 годинах, де число ракет невідоме ([HANDOFF.md](../HANDOFF.md)).

## Як перебудувати

Повний шлях від bronze: [ARCHITECTURE.md](../ARCHITECTURE.md), «Як запустити», пункти 1..3. Лише gold з наявного silver:

```
.venv/bin/python -I -m airalerts.gold.kyiv_hourly
.venv/bin/python -I -m airalerts.gold.kyiv_nightly
.venv/bin/python -I -m airalerts.gold.kyiv_quiet
.venv/bin/python -I -m airalerts.db
sha256sum data/gold/*.parquet        # має збігтися з сумами вище
choom -n 500 -- .venv/bin/python -I -m unittest discover -s tests
```

## Правило оновлення

Ця версія заморожена: усі числа в `reports/` і в описах моделей належать саме їй. Тест (з 2026-08-29) уже відкрито, тож нових рішень на ньому не приймають.

Будь-яке оновлення даних (нові години після зрізу, нові виправлення мітки, новий прогін Jev, нові канали) створює нову версію з новими контрольними сумами. Якщо на новій версії щось обирають (модель, ознаки, поріг), чесна оцінка потребує **нового тесту**: годин після 2026-10-10T17:00Z, яких не бачила жодна модель, з межею, заданою до оцінки. Старі числа тесту тоді лишаються за старою версією.
