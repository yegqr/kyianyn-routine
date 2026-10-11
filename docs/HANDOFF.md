# Хендоф: дані для прогнозу удару по Києву

Стан на 2026-10-11 близько 10:10Z. Гілка `data-layers`, віддаленого репозиторію немає, нічого не запушено. Етап даних завершено і пройшов аудит перед моделюванням (нижче). Далі: моделювання. Здача завдання KSE: 2026-10-12 23:59 за Києвом ([ASSIGNMENT.md](ASSIGNMENT.md)).

Читати в такому порядку: цей файл, [ARCHITECTURE.md](ARCHITECTURE.md) (рівні, контракт, як запустити), [VERIFICATION.md](data/VERIFICATION.md) (чому даним можна довіряти, аудит), [kyiv_hourly.md](data/gold/kyiv_hourly.md) (колонки gold), [HISTORY.md](HISTORY.md) (як дійшли і від чого відмовились), [adr/](adr/).

## Що є

| Рівень | Що | Де | У git |
|---|---|---|---|
| bronze | 17 Telegram-каналів з 2026-04-16T21:00Z (163 042 пости), прогони ECMWF, астрономія, дати, Kremlin, Вікіпедія, знімок dronestrikemap; журнал `data/bronze/MANIFEST.md` | `data/bronze/`, 175 МБ | лише MANIFEST |
| silver | 11 таблиць, по документу на кожну | `data/silver/*.parquet`, `docs/data/silver/` | ні |
| кеш Jev | кожна відповідь Jev; без нього перебудова мітки й оцінок коштує гроші і дає трохи інші числа | `data/silver/_jev_cache/` (34 073 виклики, $8.97) | ні, не видаляти |
| gold | `kyiv_hourly`: 3909 годин 2026-04-30T21:00Z..2026-10-10T17:00Z, 52 колонки (`t_utc`, 50 ознак, ціль), `y_strike_3h` true 138 з 3906 (3.5%); null лише в 3 останніх цілях і в `ua_missiles_launched_1d` (1114 годин без числа ракет) | `data/gold/kyiv_hourly.parquet` | так |
| докази | зовнішня перевірка мітки і сигналів | `data/verification/`, `scripts/verify/` | так |

## Аудит 2026-10-11

Оркестратор і 5 агентів лише з читанням перевірили gold і silver заново, не довіряючи документам. Деталі й числа: [VERIFICATION.md](data/VERIFICATION.md), розділ «Аудит перед моделюванням»; рішення: [ADR-0007](adr/0007-audit-before-modelling.md); докази: `data/verification/audit_*`.

- Агрегація правильна: усі 50 ознак gold перераховано простими циклами з silver (погоду з bronze) на всіх 3909 годинах, 0 розбіжностей; 561 тривогу заново розібрано з постів КМВА, збіг до секунди.
- Витоку часу немає в тривогах, погоді, астрономії, датах, ударах по РФ (gold бачить атаку щонайменше через 19 год після її кінця). Проба логістичною регресією на останніх 42 днях: AUC 0.80, лише година і темрява 0.78.
- Знайдено і виправлено (рішення користувача):
  - мітка: 15 з 77 годин удару хибні (14 разів остання година атаки лише зі звітами про наслідки, 1 реактивний дрон), тепер у `CORRECTIONS`; годин удару 62, ціль 151 → 138;
  - витік у сигналах S1: переписані після публікації пости (нічне «Зведення» AerisRimor, службові «pinned») починали події на 1.3..5.7 год раніше; тепер `written_later()` їх не пускає;
  - `ua_missiles_launched_1d` NULL замість 0 у днях без числа ракет; `rf_drones_intercepted_1d` лише дрони;
  - документи: застарілі й хибні твердження виправлено.

## Для моделювання

- 138 рядків true це 35 атак (серій поспіль); у 33 рядках удар був і в останні 3 години (атака вже йде). Метрики рахувати окремо для початку атаки, інакше продовження атак їх роздує.
- За останні 28 днів 7 атак, 23 рядки true: тест на свіжому періоді дуже шумний, довірчі інтервали bootstrap по днях обов'язкові.
- Більшість сигналу дає час доби: 118 з 138 позитивів о 22..05 за Києвом. Бейзлайн з години і темряви обов'язковий поряд з наївним.
- `ua_missiles_launched_1d` має null (28.5% годин): заповнити в моделі або додати ознаку «невідомо», не 0.
- Майже сталі ознаки: `kyiv_days_to_imp4` (14 у 99.3% годин), `rf_moscow_3d` (1 у 87%), `hol_high_tomorrow`; ударні дрони є в 94% годин.
- Три останні рядки мають ціль null: для навчання відкинути.
- Дані закінчуються 2026-10-10T17:00Z; завдання хоче найсвіжіші дані, тож перед здачею можна докачати bronze і перебудувати (Telegram, Jev для нових годин: потрібен відкритий vault).

## Залишковий ризик витоку

| Таблиця | `available_at` | Залишковий ризик всередині значення |
|---|---|---|
| `kyiv_alerts` | старт тривоги | малий; тривога 391 склеєна з кількох (VA_Kyiv пропустив відбій), так її бачили в реальному часі |
| `kyiv_threat_hourly` | кінець години h | текст постів в останній версії (41% постів-доказів редаговано); 154 пости з пізнішим часом у тексті змінюють лише один прапорець до T0; `CORRECTIONS` задано після події |
| `prep_signal_events` | перший пост події | правки без «станом на HH:MM» датувати не можна; пачки S4 у Jev містять пізніші пости (50 з 8821 подій) |
| `weather_runs` | час прогону + 8 год | малий |
| `astro_hourly`, `calendar_dates` | відомо наперед | малий |
| `political_events` | час оголошення; Kremlin + 24 год | набір подій Вікіпедії з найновішої ревізії (втрата, а не знання майбутнього); Telegram у версії на час забору |
| `strike_points`, `strike_days` | день d + 30 год | сайт без історії змін; другий знімок через годину змінив лише одну точку дня 2026-10-10 |

Команди перевірок (жодна не пише дані, крім позначених):

```
.venv/bin/python -I -m unittest discover -s tests -v
.venv/bin/python -I -m airalerts.silver.alerts check
.venv/bin/python -I -m airalerts.silver.telegram_posts check
.venv/bin/python -I -m airalerts.silver.threat_hourly selftest
mkdir -p /tmp/s4 && .venv/bin/python -I -m airalerts.silver.signals check /tmp/s4
.venv/bin/python -I -m airalerts.silver.rf_strikes checks
.venv/bin/python -I -m airalerts.silver.rf_strikes features-check
.venv/bin/python -I -m airalerts.silver.calendar_dates --report
.venv/bin/python -I -m airalerts.silver.political_events wiki-check
.venv/bin/python -I -m airalerts.silver.political_events features-check
.venv/bin/python -I scripts/verify/label_check.py          # пише data/verification/label_compare.txt
.venv/bin/python -I scripts/verify/audit_recompute.py      # пише data/verification/audit_recompute.txt
```

## Відкрито

- Реактивні дрони («Герань-3/5») і «Бандероль» не удар за рішенням користувача; восени це щонайменше 4-6 днів атак на Київ.
- Можливі пропущені години удару: 2026-09-17T04, 2026-09-27T23 (аудит, не еталон).
- `tg_posts` містить канали, яких жодна таблиця більше не читає (`mod_russia`, `mos_sobyanin`, `favt_info`, `GeneralStaffZSU`): частина корпусу, лишено.

## Як відтворити з нуля

[ARCHITECTURE.md](ARCHITECTURE.md), «Як запустити»: bronze збирачами (`scripts/bronze/`), silver модулями в указаному порядку (Jev з кешу безкоштовно; без кешу потрібен відкритий vault з ключем `typesafe-general`), gold, база DuckDB, тест. Зовнішня перевірка: `scripts/verify/` (агенти Claude Code через Workflow і промпти в `label_reference_briefs.md`).
