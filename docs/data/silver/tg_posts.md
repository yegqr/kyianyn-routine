# tg_posts

Усі пости Telegram усіх каналів в одній таблиці з класами за regex. Модуль `src/airalerts/silver/telegram_posts.py`, regex у `src/airalerts/silver/telegram_rx.py`, файл `data/silver/tg_posts.parquet`. Правила: [PARSING.md](../../PARSING.md) розділи 0.1, 2, 7. Рівні даних і контракт: [ARCHITECTURE.md](../../ARCHITECTURE.md).

## Що це

Один рядок = один пост одного каналу, ключ `(channel, post_id)`. Дані з `FETCH_FROM` = 2026-04-16T21:00:00Z (`src/airalerts/paths.py`: T0 мінус 14 діб, щоб вікна 14 діб були повні з T0). Рядки відсортовано за `published_at`, `channel`, `post_id`. Таблиця вхід для мітки удару (`kyiv_threat_hourly`, шматок S3) і сигналів (`prep_signal_events`, шматок S4). Власних ознак для gold вона не дає (`features()` немає), `ASOF` є.

## Bronze

| Файл | Що | Як забрано |
|---|---|---|
| `data/bronze/telegram/<channel>.jsonl` | 18 каналів зі списку `ROLES` у модулі: рядок на пост, формат PARSING 0.1 | `scripts/bronze/tg_fetch.py`, черги `tg_backfill.sh A`, `B`, `C`; kyiv_airdef, AerisRimor, StrategicaviationT, kyiv_nebo, kpszsu, monitorwarr, vanek_nikolaev качали паралельними частинами і злили `tg_fetch.py merge`; раніше скачані канали розширили до `FETCH_FROM` (range mode); `UkraineAlarmSignal` це латка для `kyiv_alerts` (`scripts/bronze/etryvoga_patch.py`) |
| `data/bronze/telegram/logs/A.log`, `B.log`, `C.log` | рядок `<час> done <канал>`, коли канал докачано | ті самі черги |

Читання: `airalerts.telegram.load` (перший збережений рядок кожного `post_id`, дублів немає). Якщо файл дописують і останній рядок обірвано, модуль чекає 2 с і читає знову (до 6 спроб).

Канал повний, якщо в одному з трьох логів є рядок `done <канал>`, що закінчується назвою каналу (рядок із приміткою після назви не рахується). Повні 17 каналів, `UkraineAlarmSignal` ні. Таблицю це не змінює: перебудова бере все, що є у файлах. Ознака повноти потрібна для друку і для ключів метаданих Parquet `channels_complete`, `channels_incomplete`, `built_at`. `UkraineAlarmSignal` покриває лише години біля відбою без старту, у логах його немає, тож він завжди «не повний».

Канали і `channel_role`:

| channel_role | канали |
|---|---|
| kyiv_official | VA_Kyiv, vitaliy_klitschko |
| kyiv_monitor | truexakyiv, AerisRimor, kyiv_nebo, kyiv_airdef |
| monitor_ua | war_monitor, kpszsu, StrategicaviationT, monitorwarr, vanek_nikolaev |
| rf_official | mod_russia, mos_sobyanin, favt_info (з 2026-10-11 жодна таблиця їх не читає, лишились як частина корпусу) |
| ua_official | GeneralStaffZSU (так само не читається), OP_UA, V_Zelenskiy_official |
| alert_feed | UkraineAlarmSignal |

Файл каналу, якого немає в `ROLES`, зупиняє збірку з повідомленням.

## Колонки

| колонка | тип | опис |
|---|---|---|
| `channel` | VARCHAR | канал без @ |
| `post_id` | BIGINT | id поста в каналі |
| `published_at` | TIMESTAMP (UTC) | час публікації з t.me/s |
| `text` | VARCHAR | текст без HTML; `''` для поста лише з медіа; цитати відповіді в ньому немає (PARSING 0.1) |
| `edited` | BOOLEAN | пост змінено після публікації |
| `forwarded_from` | VARCHAR | джерело репосту або NULL |
| `is_original` | BOOLEAN | `forwarded_from IS NULL` |
| `views` | BIGINT | перегляди на момент забору: `6.83K` це 6830, `1.2M` це 1200000, `55` це 55, NULL лишається NULL; будь-який інший вигляд зупиняє збірку |
| `url` | VARCHAR | `https://t.me/<channel>/<post_id>` |
| `channel_role` | VARCHAR | таблиця вище |
| `rx_classes` | VARCHAR[] | класи PARSING 2 у порядку словника: missile_threat, drone_threat, toward_kyiv, explosion, air_defense, debris, impact_damage, all_clear |
| `rx_kyiv_city` | BOOLEAN | друге значення `classify`: `KYIV_CITY` збігається, або канал із `KYIV_ONLY`, текст не порожній і `OBLAST` не збігається |
| `rx_evidence` | BOOLEAN | третє значення `classify`: `rx_kyiv_city` і є клас explosion, debris або impact_damage |
| `rx_signals` | VARCHAR[] | сигнали S1..S5 PARSING 7, чий основний вираз збігається, у порядку S1..S5 |
| `available_at` | TIMESTAMP (UTC) | рівно `published_at` |

`rx_*` рахуються один раз на різний текст усередині каналу. Вираз `KYIV` (слово Київ) і уточнення сигналів (`S1_TAKEOFF`, `S1_COUNT`, `S2_TAKEOFF`, `S2_CLEAR`, `S3_NONE`, `S3_COUNT`, `S4_LAUNCH_PLACE`, `S4_COUNT`) у таблиці не збережено: їх застосовує споживач до `text` із `telegram_rx`.

## Час доступності

`available_at = published_at`: пост відомий із моменту публікації. `ASOF["tg_posts"]` це типове `SELECT * FROM tg_posts WHERE available_at < {t}`. Два поля вже «з майбутнього»: `views` це лічильник на момент забору (2026-10-10), а `text` поста з `edited = true` міг отримати доповнення після `published_at` (PARSING 0.1). Для мітки це не витік, для ознак обидва поля брати не можна.

## Ознаки для gold

Немає: `features()` у модулі не визначено. Споживачі читають таблицю і підключають вирази:

```python
from airalerts.silver.telegram_rx import CLASSES, classify, SIGNALS, KYIV, signals
```

`telegram_rx.py` тримає дослівні копії блоків PARSING.md: python-блок розділу 2 (`K`, `CLASSES`, `KYIV_CITY`, `OBLAST`, `KYIV_ONLY`, `classify`) і вирази розділу 7 (`S1`..`S5`, `KYIV`, лічильники `S1_COUNT` і `S4_COUNT`). Тепер це єдине джерело виразів. `SIGNALS` це словник S1..S5, `signals(text)` повертає список сигналів тексту.

## Як перебудувати

```
choom -n 500 -- .venv/bin/python -I -m airalerts.silver.telegram_posts          # уся таблиця з усіх data/bronze/telegram/*.jsonl
choom -n 500 -- .venv/bin/python -I -m airalerts.silver.telegram_posts check    # самоперевірка, у кінці ALL OK
```

Збірка кожного разу робить усю таблицю заново, тому після докачки каналів досить запустити обидві команди ще раз. Збірка друкує рядок на канал (рядки, перший і останній `published_at`, мінімальний і максимальний `post_id`, `complete`) і підсумок. Збірка триває десятки секунд процесорного часу, `check` кілька секунд; при зайнятих ядрах довше, тож запускати у фоні. Після злиття частин каналу в `logs/*.log` має з'явитися рядок `done <канал>`, інакше канал лишиться «не повним».

## Перевірка

Стан: bronze після останньої докачки. Останній рядок `done` у логах, `grep -h ' done ' data/bronze/telegram/logs/*.log | sort | tail -1`: `2026-10-10T20:11:16Z done kpszsu`. Таблицю перебудовано з цих файлів, час збірки лежить у ключі Parquet `built_at`. Підсумок збірки: `tg_posts: 163042 rows (sum of unique post_id per channel 163042), 18 channels with files, 17 complete`. Числа нижче не змінюються, доки файли bronze не змінено.

1. Канали, `check` розділ 1: рядки, перший і останній `published_at`, мінімальний і максимальний `post_id`, найбільший розрив id (різниця між сусідніми `post_id` каналу, 1 означає, що дірок немає; `check` друкує його як `max_gap`):

| channel | рядків | перший `published_at` | останній `published_at` | min `post_id` | max `post_id` | найбільший розрив id |
|---|---|---|---|---|---|---|
| AerisRimor | 22729 | 2026-04-16T22:13:16Z | 2026-10-10T19:36:49Z | 66957 | 89914 | 8 |
| GeneralStaffZSU | 2009 | 2026-04-17T04:00:12Z | 2026-10-10T12:01:01Z | 37387 | 42558 | 14 |
| OP_UA | 808 | 2026-04-17T11:30:23Z | 2026-10-10T15:03:01Z | 18520 | 20206 | 10 |
| StrategicaviationT | 12786 | 2026-04-17T05:48:30Z | 2026-10-10T19:37:24Z | 29798 | 43816 | 10 |
| UkraineAlarmSignal | 180 | 2026-10-10T07:58:27Z | 2026-10-10T11:50:44Z | 651169 | 651348 | 1 |
| VA_Kyiv | 2762 | 2026-04-17T05:59:01Z | 2026-10-10T17:11:31Z | 17740 | 21677 | 20 |
| V_Zelenskiy_official | 1341 | 2026-04-17T10:59:55Z | 2026-10-10T16:54:31Z | 18706 | 21312 | 10 |
| favt_info | 3970 | 2026-04-16T21:17:59Z | 2026-10-10T14:10:19Z | 4573 | 8585 | 5 |
| kpszsu | 24792 | 2026-04-16T21:12:38Z | 2026-10-10T18:47:27Z | 60156 | 84988 | 3 |
| kyiv_airdef | 45341 | 2026-04-17T16:51:57Z | 2026-10-10T16:59:33Z | 32927 | 79205 | 28 |
| kyiv_nebo | 8215 | 2026-04-17T16:51:31Z | 2026-10-10T18:13:59Z | 22699 | 31126 | 6 |
| mod_russia | 4028 | 2026-04-16T22:02:48Z | 2026-10-10T15:51:01Z | 62721 | 68090 | 11 |
| monitorwarr | 6748 | 2026-04-16T23:03:30Z | 2026-10-10T19:33:49Z | 35448 | 42282 | 8 |
| mos_sobyanin | 1233 | 2026-04-17T08:00:14Z | 2026-10-10T12:30:44Z | 19384 | 22076 | 10 |
| truexakyiv | 13787 | 2026-04-17T02:17:55Z | 2026-10-10T17:34:47Z | 74075 | 92605 | 31 |
| vanek_nikolaev | 3112 | 2026-04-16T22:26:03Z | 2026-10-09T20:16:48Z | 40113 | 43331 | 10 |
| vitaliy_klitschko | 840 | 2026-04-18T09:15:59Z | 2026-10-10T16:28:10Z | 6488 | 7828 | 10 |
| war_monitor | 8361 | 2026-04-16T21:01:15Z | 2026-10-10T11:36:43Z | 39003 | 47552 | 10 |

   `UkraineAlarmSignal` не повний за задумом (латка для `kyiv_alerts`), решта 17 каналів повні. `check` читає bronze заново простим `json` і порівнює з таблицею: рядків усього 163042 = сума унікальних `post_id` каналів; для 17 повних каналів рядків рівно стільки, скільки унікальних `post_id` у файлі, для `UkraineAlarmSignal` не більше (180 з 180); усі значення (`published_at`, `text`, `edited`, `forwarded_from`, `url`, `views`, `is_original`) збігаються з bronze, 0 розбіжностей.
2. Розриви id. Розрив понад 30 один: truexakyiv 79219 -> 79250 (різниця 31, з 2026-07-01T21:29:45Z до 2026-07-01T22:58:28Z). Це не збій пагінації, а видалені id: обидва пости збережено з однієї відповіді t.me/s (однакове `fetched_at`), тож 30 id між ними сторінка не показала. Команда `grep -E '"post_id": (79219|79250),' data/bronze/telegram/truexakyiv.jsonl | grep -o '"fetched_at": "[^"]*"'` дає двічі `"fetched_at": "2026-10-10T18:38:45Z"`. У truexakyiv є й інші розриви від 20, тож цей не вирізняється. `check` тримає цей розрив у множині `EXPLAINED_GAPS` і падає на кожному іншому розриві понад 30.
3. Початок діапазону. Перші пости kyiv_airdef і kyiv_nebo (2026-04-17T16:51Z, «МіГ» і «МіГ у повітрі») і vitaliy_klitschko (2026-04-18T09:15Z) пізніші за `FETCH_FROM`. Перша тривога в `kyiv_alerts` починається о 2026-04-17T16:54:40Z: `.venv/bin/python -I -c 'import pyarrow.parquet as pq, pyarrow.compute as pc; print(pc.min(pq.read_table("data/silver/kyiv_alerts.parquet", columns=["start_utc"])["start_utc"]))'` друкує `2026-04-17 16:54:40`, а ці два перші пости з'явилися за кілька хвилин до неї: київські монітори мовчали, поки тривог не було. Сторінку t.me/s перед першим постом напряму не перевіряли.
4. Контрольні пости: усі 17 постів PARSING 0.1 (по одному на канал) і 6 постів PARSING 2 є з правильним часом, `PEND` немає. Списки: `CONTROL_01` і `CONTROL_2` у модулі. `check` друкує PEND для поста каналу без файлу чи з недосяжним діапазоном і FAIL, якщо пост має бути, а його немає.
5. Класи: kyiv_airdef/75885 має missile_threat (і toward_kyiv); vitaliy_klitschko/7775 має impact_damage, `rx_kyiv_city` і `rx_evidence` true; VA_Kyiv/21514 має missile_threat; AerisRimor/89451 (текст «Пролунали вибухи.») має explosion, `rx_kyiv_city` і `rx_evidence` true. Окрім рядка таблиці `check` викликає `classify('AerisRimor', 'Пролунали вибухи.')` і отримує `['explosion']`, true, true.
6. Сигнали на добі 2026-10-09 UTC (постів / S1 / S2 / S3 / S4 / S5 / KYIV), `check` розділ 3. Це числа для PARSING 7: вони рахуються на збереженому тексті, у якому немає цитати відповіді (PARSING 0.1). Ті самі числа лежать у `EXPECT_DAY` модуля, `check` падає, якщо вони змінилися.

| channel | постів / S1 / S2 / S3 / S4 / S5 / KYIV |
|---|---|
| war_monitor | 37/0/0/0/30/0/28 |
| kpszsu | 455/0/0/0/382/0/104 |
| AerisRimor | 105/0/0/0/39/0/1 |
| StrategicaviationT | 116/3/1/0/14/0/1 |
| monitorwarr | 97/0/0/0/61/0/35 |
| vanek_nikolaev | 1/0/0/0/0/0/0 |
| kyiv_airdef | 791/0/0/0/17/0/1 |

   Раніше PARSING 7 (git: `docs/PARSING.md` у HEAD до цього оновлення) мав ті самі кількості постів і ті самі S1, S2, S3, S5, але S4 відрізнявся у 6 каналах з 7, KYIV у 3. У п'яти каналах давні S4 вищі за таблицю, що узгоджується з цитатою відповіді, якої в збереженому тексті немає; у StrategicaviationT вони нижчі (5 проти 14), чого цитата не пояснює. Причину не встановлено; еталон це таблиця вище.
7. Перегляди, `check` друкує сирий вигляд і значення таблиці: `GeneralStaffZSU/37672` `'8.97K'` це 8970; `V_Zelenskiy_official/18768` `'2.22M'` це 2220000; `VA_Kyiv/21675` `'1'` це 1; `GeneralStaffZSU/42097` NULL лишається NULL; `6.83K`, `1.2M`, `55` і NULL дають 6830, 1200000, 55 і NULL.
8. `ASOF` на 3 випадкових годинах (seed 20261010, від T0 до останнього поста): 2026-06-09T16:00:00Z це 29294 рядки, 2026-06-29T15:00:00Z це 39343, 2026-08-21T20:00:00Z це 76851. Кожне число збігається з незалежним підрахунком `available_at < t` у pyarrow, і жоден `published_at` не пізніший за t.
9. Інваріанти: `available_at = published_at`; `channel_role`, `rx_classes`, `rx_signals`, `rx_kyiv_city`, `rx_evidence` ніколи не NULL; `rx_evidence` true лише коли `rx_kyiv_city` true. Кінець виводу `check`: `ALL OK`.

## Пастки

- `rx_signals` рахується для кожного поста кожного каналу, а сигнали визначено лише для 7 каналів PARSING 7 (`signals.py` бере 6 з них, без vanek_nikolaev). У `mod_russia` чи `GeneralStaffZSU` «Кинджал» або «Калібр» означає інше; споживач S4 мусить фільтрувати за каналом.
- Для правил «2 незалежні канали» брати лише `is_original` (репости: КМВА репостить Кличка, AerisRimor репостить kpszsu).
- `rx_kyiv_city` для каналів `KYIV_ONLY` true майже для кожного непорожнього поста без слів `OBLAST` (реклама теж); справжній доказ це `rx_evidence`.
- `views` і текст постів з `edited` описано в розділі про час доступності.
- Цитату відповіді в `text` не збережено (PARSING 0.1). Числа S4 і KYIV, які хтось порахував з живої сторінки, можуть відрізнятися від таблиці (Перевірка, п. 6).
- Збірка завжди повна: не склеювати таблицю з іншою. Якщо канал докачують знову, запустити обидві команди розділу «Як перебудувати».
- Початок діапазону каналу може бути пізніше за `FETCH_FROM`, якщо канал мовчав (Перевірка, п. 3). Дірки в нумерації id є в кожному з 17 повних каналів (колонка `max_gap`) і за PARSING 0.1 не означають втрати: альбоми і видалені пости.
- `UkraineAlarmSignal` не повна стрічка eTryvoga, а кілька годин біля відбою без старту; рахувати за ним тривоги не можна.
- Пост без тексту (лише медіа) має порожній `text`, порожні `rx_classes` і `rx_signals`, `rx_kyiv_city` false.
- Кількість постів може відрізнятися від PARSING на 1-2 % через видалення; на добі 2026-10-09 розбіжності по постах немає (усі 7 каналів сигналів).
