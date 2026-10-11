# tg_posts

Усі пости Telegram усіх каналів в одній таблиці з класами за regex. Модуль `src/airalerts/silver/telegram_posts.py`, regex у `src/airalerts/silver/telegram_rx.py`, файл `data/silver/tg_posts.parquet`. Правила: [PARSING.md](../../PARSING.md) розділи 0.1, 2, 7. Рівні даних і контракт: [ARCHITECTURE.md](../../ARCHITECTURE.md).

## Що це

Один рядок = один пост одного каналу, ключ `(channel, post_id)`. Дані з `FETCH_FROM` = 2026-04-16T21:00:00Z (`src/airalerts/paths.py`: T0 мінус 14 діб, щоб вікна 14 діб були повні з T0). Рядки відсортовано за `published_at`, `channel`, `post_id`. Таблиця вхід для `kyiv_threat_hourly` і `prep_signal_events`. Власних ознак для gold вона не дає (`features()` немає), `ASOF` є.

## Bronze

| Файл | Що | Як забрано |
|---|---|---|
| `data/bronze/telegram/<channel>.jsonl` | 18 каналів зі списку `ROLES` у модулі: рядок на пост, формат PARSING 0.1 | `scripts/bronze/tg_fetch.py`, черги `tg_backfill.sh A`, `B`, `C`; великі канали качали паралельними частинами і зливали `tg_fetch.py merge`; `UkraineAlarmSignal` це латка для `kyiv_alerts` (`scripts/bronze/etryvoga_patch.py`) |
| `data/bronze/telegram/logs/A.log`, `B.log`, `C.log` | рядок `<час> done <канал>`, коли канал докачано | ті самі черги |

Читання: `airalerts.telegram.load` (перший збережений рядок кожного `post_id`, дублів немає). Якщо файл дописують і останній рядок обірвано, модуль чекає 2 с і читає знову (до 6 спроб). Файл каналу, якого немає в `ROLES`, зупиняє збірку з повідомленням.

Канал повний, якщо в одному з логів є рядок `done <канал>` без нічого після назви. Повні 17 каналів. `UkraineAlarmSignal` не повний: у логах його немає, він покриває лише години біля відбою без старту. Повнота не змінює таблицю (перебудова бере все, що є у файлах), вона лише друкується і лежить у ключах метаданих Parquet `channels_complete`, `channels_incomplete`, `built_at`.

Канали, `channel_role` і рядків у таблиці (разом 163042):

| channel_role | канали |
|---|---|
| kyiv_official | VA_Kyiv 2762, vitaliy_klitschko 840 |
| kyiv_monitor | truexakyiv 13787, AerisRimor 22729, kyiv_nebo 8215, kyiv_airdef 45341 |
| monitor_ua | war_monitor 8361, kpszsu 24792, StrategicaviationT 12786, monitorwarr 6748, vanek_nikolaev 3112 |
| rf_official | mod_russia 4028, mos_sobyanin 1233, favt_info 3970 (жодна таблиця їх не читає, лишились як частина корпусу) |
| ua_official | GeneralStaffZSU 2009 (так само не читається), OP_UA 808, V_Zelenskiy_official 1341 |
| alert_feed | UkraineAlarmSignal 180 |

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

`telegram_rx.py` тримає дослівні копії блоків PARSING.md: python-блок розділу 2 (`K`, `CLASSES`, `KYIV_CITY`, `OBLAST`, `KYIV_ONLY`, `classify`) і вирази розділу 7 (`S1`..`S5`, `KYIV`, лічильники `S1_COUNT` і `S4_COUNT`). Це єдине джерело виразів. `SIGNALS` це словник S1..S5, `signals(text)` повертає список сигналів тексту.

## Як перебудувати

```
choom -n 500 -- .venv/bin/python -I -m airalerts.silver.telegram_posts          # уся таблиця з усіх data/bronze/telegram/*.jsonl
choom -n 500 -- .venv/bin/python -I -m airalerts.silver.telegram_posts check    # самоперевірка, у кінці ALL OK
```

Збірка щоразу робить усю таблицю заново (не склеювати з іншою), тому після докачки каналів досить запустити обидві команди ще раз. Вона друкує рядок на канал (рядки, перший і останній `published_at`, мінімальний і максимальний `post_id`, `complete`) і підсумок. Збірка триває десятки секунд процесорного часу, `check` кілька секунд; при зайнятих ядрах довше, тож запускати у фоні. Після злиття частин каналу в `logs/*.log` має з'явитися рядок `done <канал>`, інакше канал лишиться «не повним».

## Перевірка

Стан: bronze після останньої докачки. Останній рядок `done`, `grep -h ' done ' data/bronze/telegram/logs/*.log | sort | tail -1`: `2026-10-10T20:11:16Z done kpszsu`. Підсумок збірки: `tg_posts: 163042 rows (sum of unique post_id per channel 163042), 18 channels with files, 17 complete`. Час збірки лежить у ключі Parquet `built_at`. Числа нижче не змінюються, доки файли bronze не змінено.

1. Канали, `check` розділ 1. Перший `published_at` 17 повних каналів від 2026-04-16T21:01:15Z (war_monitor) до 2026-04-18T09:15:59Z (vitaliy_klitschko), у `UkraineAlarmSignal` від 2026-10-10T07:58:27Z. Останній: найраніший vanek_nikolaev 2026-10-09T20:16:48Z, далі war_monitor 2026-10-10T11:36:43Z, найпізніший StrategicaviationT 2026-10-10T19:37:24Z. `check` читає bronze заново простим `json` і порівнює з таблицею: рядків усього 163042 = сума унікальних `post_id` каналів; для 17 повних каналів рядків рівно стільки, скільки унікальних `post_id` у файлі, для `UkraineAlarmSignal` не більше (180 з 180); усі значення (`published_at`, `text`, `edited`, `forwarded_from`, `url`, `views`, `is_original`) збігаються з bronze, 0 розбіжностей.
2. Розриви id (різниця між сусідніми `post_id` каналу, 1 означає, що дірок немає; `check` друкує `max_gap`): у 17 повних каналів від 3 (kpszsu) до 31 (truexakyiv), у `UkraineAlarmSignal` 1. Розрив понад 30 один: truexakyiv 79219 -> 79250 (з 2026-07-01T21:29:45Z до 2026-07-01T22:58:28Z). Це видалені id, а не збій пагінації: обидва пости збережено з однієї відповіді t.me/s. `grep -E '"post_id": (79219|79250),' data/bronze/telegram/truexakyiv.jsonl | grep -o '"fetched_at": "[^"]*"'` дає двічі `"fetched_at": "2026-10-10T18:38:45Z"`. `check` тримає цей розрив у множині `EXPLAINED_GAPS` і падає на кожному іншому розриві понад 30.
3. Початок діапазону. Перші пости kyiv_airdef і kyiv_nebo (2026-04-17T16:51Z, «МіГ» і «МіГ у повітрі») і vitaliy_klitschko (2026-04-18T09:15Z) пізніші за `FETCH_FROM`. Перша тривога в `kyiv_alerts` о 2026-04-17T16:54:40Z: `.venv/bin/python -I -c 'import pyarrow.parquet as pq, pyarrow.compute as pc; print(pc.min(pq.read_table("data/silver/kyiv_alerts.parquet", columns=["start_utc"])["start_utc"]))'` друкує `2026-04-17 16:54:40`. Київські монітори мовчали, поки тривог не було.
4. Контрольні пости: усі 17 постів PARSING 0.1 (по одному на канал) і 6 постів PARSING 2 є з правильним часом, `PEND` немає. Списки: `CONTROL_01` і `CONTROL_2` у модулі. `check` друкує PEND для поста каналу без файлу чи з недосяжним діапазоном і FAIL, якщо пост має бути, а його немає.
5. Класи: kyiv_airdef/75885 має missile_threat (і toward_kyiv); vitaliy_klitschko/7775 має impact_damage, `rx_kyiv_city` і `rx_evidence` true; VA_Kyiv/21514 має missile_threat; AerisRimor/89451 (текст «Пролунали вибухи.») має explosion, `rx_kyiv_city` і `rx_evidence` true. Окрім рядка таблиці `check` викликає `classify('AerisRimor', 'Пролунали вибухи.')` і отримує `['explosion']`, true, true.
6. Сигнали на добі 2026-10-09 UTC (постів / S1 / S2 / S3 / S4 / S5 / KYIV), `check` розділ 3. Рахуються на збереженому тексті без цитати відповіді (PARSING 0.1); ті самі числа лежать у `EXPECT_DAY` модуля, `check` падає, якщо вони змінилися. Ними замінено старі числа PARSING 7: [HISTORY.md](../../HISTORY.md), запис 2026-10-10T21:15Z.
   war_monitor 37/0/0/0/30/0/28; kpszsu 455/0/0/0/382/0/104; AerisRimor 105/0/0/0/39/0/1; StrategicaviationT 116/3/1/0/14/0/1; monitorwarr 97/0/0/0/61/0/35; vanek_nikolaev 1/0/0/0/0/0/0; kyiv_airdef 791/0/0/0/17/0/1.
7. Перегляди, `check` друкує сирий вигляд і значення таблиці: `GeneralStaffZSU/37672` `'8.97K'` це 8970; `V_Zelenskiy_official/18768` `'2.22M'` це 2220000; `VA_Kyiv/21675` `'1'` це 1; `GeneralStaffZSU/42097` NULL лишається NULL.
8. `ASOF` на 3 випадкових годинах (seed 20261010, від T0 до останнього поста): 2026-06-09T16:00:00Z це 29294 рядки, 2026-06-29T15:00:00Z це 39343, 2026-08-21T20:00:00Z це 76851. Кожне число збігається з незалежним підрахунком `available_at < t` у pyarrow, і жоден `published_at` не пізніший за t.
9. Інваріанти: `available_at = published_at`; `channel_role`, `rx_classes`, `rx_signals`, `rx_kyiv_city`, `rx_evidence` ніколи не NULL; `rx_evidence` true лише коли `rx_kyiv_city` true. Кінець виводу `check`: `ALL OK`.

## Пастки

- `rx_signals` рахується для кожного поста кожного каналу, а сигнали визначено лише для 7 каналів PARSING 7 (`signals.py` бере 6 з них, без vanek_nikolaev). У `mod_russia` чи `GeneralStaffZSU` «Кинджал» або «Калібр» означає інше; споживач S4 мусить фільтрувати за каналом.
- Для правил «2 незалежні канали» брати лише `is_original` (репости: КМВА репостить Кличка, AerisRimor репостить kpszsu).
- `rx_kyiv_city` для каналів `KYIV_ONLY` true майже для кожного непорожнього поста без слів `OBLAST` (реклама теж); справжній доказ це `rx_evidence`.
- `views` і текст постів з `edited` не брати в ознаки (розділ «Час доступності»).
- Цитату відповіді в `text` не збережено (PARSING 0.1): числа S4 і KYIV, пораховані з живої сторінки, можуть відрізнятися від таблиці (Перевірка, п. 6).
- Початок діапазону каналу може бути пізніше за `FETCH_FROM`, якщо канал мовчав (Перевірка, п. 3). Дірки в нумерації id є в кожному з 17 повних каналів і за PARSING 0.1 не означають втрати: альбоми і видалені пости.
- `UkraineAlarmSignal` не повна стрічка eTryvoga, а кілька годин біля відбою без старту; рахувати за ним тривоги не можна.
- Пост без тексту (лише медіа) має порожній `text`, порожні `rx_classes` і `rx_signals`, `rx_kyiv_city` false.
