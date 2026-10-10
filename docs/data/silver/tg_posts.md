# tg_posts

Усі пости Telegram усіх каналів в одній таблиці з класами за regex. Модуль `src/airalerts/silver/telegram_posts.py`, regex у `src/airalerts/silver/telegram_rx.py`, файл `data/silver/tg_posts.parquet`. Правила: [PARSING.md](../../PARSING.md) розділи 0.1, 2, 7. Рівні даних і контракт: [ARCHITECTURE.md](../../ARCHITECTURE.md).

## Що це

Один рядок = один пост одного каналу, ключ `(channel, post_id)`. Рядки відсортовано за `published_at`, `channel`, `post_id`. Таблиця вхід для мітки удару (`kyiv_threat_hourly`, шматок S3) і сигналів (`prep_signal_events`, шматок S4). Власних ознак для gold вона не дає (`features()` немає), `ASOF` є.

## Bronze

| Файл | Що | Як забрано |
|---|---|---|
| `data/bronze/telegram/<channel>.jsonl` | 18 каналів зі списку `ROLES` у модулі: рядок на пост, формат PARSING 0.1 | `scripts/bronze/tg_fetch.py`, черги `tg_backfill.sh A`, `B`, `C`; kyiv_airdef добирають частинами і зливають у файл каналу; `UkraineAlarmSignal` це латка для `kyiv_alerts` (`scripts/bronze/etryvoga_patch.py`) |
| `data/bronze/telegram/logs/A.log`, `B.log`, `C.log` | рядок `<час> done <канал>`, коли канал докачано | ті самі черги |

Читання: `airalerts.telegram.load` (перший збережений рядок кожного `post_id`, дублів немає). Якщо файл дописують і останній рядок обірвано, модуль чекає 2 с і читає знову (до 6 спроб).

Канал повний, якщо в одному з трьох логів є рядок `done <канал>`. Таблицю це не змінює: перебудова бере все, що є у файлах. Ознака повноти потрібна для друку і для ключів метаданих Parquet `channels_complete`, `channels_incomplete`, `built_at`. `UkraineAlarmSignal` покриває лише години біля відбою без старту, у логах його немає, тож він завжди «не повний».

Канали і `channel_role`:

| channel_role | канали |
|---|---|
| kyiv_official | VA_Kyiv, vitaliy_klitschko |
| kyiv_monitor | truexakyiv, AerisRimor, kyiv_nebo, kyiv_airdef |
| monitor_ua | war_monitor, kpszsu, StrategicaviationT, monitorwarr, vanek_nikolaev |
| rf_official | mod_russia, mos_sobyanin, favt_info |
| ua_official | GeneralStaffZSU, OP_UA, V_Zelenskiy_official |
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
from airalerts.silver.telegram_rx import CLASSES, classify, SIGNALS, SIGNAL_CHANNELS, KYIV, signals
```

`telegram_rx.py` тримає дослівні копії блоків PARSING.md: python-блок розділу 2 (`K`, `CLASSES`, `KYIV_CITY`, `OBLAST`, `KYIV_ONLY`, `classify`) і вирази розділу 7 (`S1`..`S5`, `KYIV`, вісім уточнень). Тепер це єдине джерело виразів. `SIGNALS` це словник S1..S5, `SIGNAL_CHANNELS` це 7 каналів розділу 7, `signals(text)` повертає список сигналів тексту.

## Як перебудувати

```
choom -n 500 -- .venv/bin/python -I -m airalerts.silver.telegram_posts          # уся таблиця з усіх data/bronze/telegram/*.jsonl
choom -n 500 -- .venv/bin/python -I -m airalerts.silver.telegram_posts check    # самоперевірка, у кінці ALL OK
```

Збірка кожного разу робить усю таблицю заново, тому після докачки каналів досить запустити обидві команди ще раз. Вона друкує рядок на канал (рядки, перший і останній `published_at`, мінімальний і максимальний `post_id`, `complete`), підсумок і час роботи. Швидкість близько 0.4 мс на пост, тож 200 тис. постів це близько 80 с. Після злиття kyiv_airdef у `logs/B.log` має з'явитися рядок `done kyiv_airdef`, інакше канал лишиться «не повним».

## Перевірка

Стан даних на збірку 2026-10-10T19:13:41Z. Числа повних каналів не зміняться; решта каналів ще докачується, їхні числа дивитися у виводі команд.

1. Повні канали (є `done` у логах), команда збірки:

| channel | рядків | перший `published_at` | останній `published_at` | min `post_id` | max `post_id` |
|---|---|---|---|---|---|
| GeneralStaffZSU | 1920 | 2026-04-24T03:31:44Z | 2026-10-10T12:01:01Z | 37670 | 42558 |
| OP_UA | 766 | 2026-04-24T12:46:29Z | 2026-10-10T15:03:01Z | 18571 | 20206 |
| VA_Kyiv | 2727 | 2026-04-24T06:00:04Z | 2026-10-10T17:11:31Z | 17775 | 21677 |
| V_Zelenskiy_official | 1284 | 2026-04-24T11:08:38Z | 2026-10-10T16:54:31Z | 18767 | 21312 |
| favt_info | 3886 | 2026-04-24T09:49:11Z | 2026-10-10T14:10:19Z | 4658 | 8585 |
| mod_russia | 3907 | 2026-04-24T03:01:01Z | 2026-10-10T15:51:01Z | 62873 | 68090 |
| mos_sobyanin | 1209 | 2026-04-24T07:00:19Z | 2026-10-10T12:30:44Z | 19486 | 22076 |
| truexakyiv | 13505 | 2026-04-24T01:32:47Z | 2026-10-10T17:34:47Z | 74469 | 92605 |
| vitaliy_klitschko | 828 | 2026-04-24T06:21:33Z | 2026-10-10T16:28:10Z | 6514 | 7828 |

   `check` читає bronze заново простим `json` і порівнює з таблицею: рядків усього = сума унікальних `post_id` каналів; для повних каналів рядків рівно стільки, скільки унікальних `post_id` у файлі, для неповних не більше; усі значення (`published_at`, `text`, `edited`, `forwarded_from`, `url`, `views`, `is_original`) збігаються з bronze, 0 розбіжностей.
2. Контрольні пости PARSING 0.1 усіх 9 повних каналів є з правильним часом (VA_Kyiv/17852, vitaliy_klitschko/6552, truexakyiv/74876, mod_russia/63081, GeneralStaffZSU/37996, mos_sobyanin/19581, favt_info/4747, OP_UA/18635, V_Zelenskiy_official/18830). Контрольні пости PARSING 2: є VA_Kyiv/21514, vitaliy_klitschko/7775, vitaliy_klitschko/7822, VA_Kyiv/21658, VA_Kyiv/21659; AerisRimor/89451 чекає на файл каналу. `check` друкує PEND для постів каналів без файлу чи з недосяжним діапазоном і FAIL, якщо пост має бути, а його немає.
3. Класи: kyiv_airdef/75885 має missile_threat (і toward_kyiv); vitaliy_klitschko/7775 має impact_damage, `rx_kyiv_city` і `rx_evidence` true; VA_Kyiv/21514 має missile_threat. Для AerisRimor/89451 тексту ще немає у bronze, тож `check` викликає `classify('AerisRimor', 'Пролунали вибухи.')` і отримує `['explosion']`, true, true.
4. Сигнали на добі 2026-10-09 UTC (постів / S1 / S2 / S3 / S4 / S5 / KYIV), у дужках PARSING 7. Доба вже є у файлах трьох каналів, що докачуються:

| channel | таблиця | PARSING 7 |
|---|---|---|
| war_monitor | 37/0/0/0/30/0/28 | 37/0/0/0/32/0/28 |
| kpszsu | 455/0/0/0/382/0/104 | 455/0/0/0/398/0/113 |
| kyiv_airdef | 791/0/0/0/17/0/1 | 791/0/0/0/30/0/1 |

   Кількості постів збігаються рівно, S1, S2, S3, S5 збігаються, S4 і KYIV у таблиці нижчі. Причина не доведена; найімовірніша така: числа PARSING 7 рахували текст разом із цитатою відповіді (`js-message_reply_text`), а bronze за PARSING 0.1 цитату не містить. На живих сторінках kyiv_airdef і kpszsu цитати справді є в помітній частці постів, і додавання цитати до тексту збільшує збіги S4 і KYIV, але точно відтворити числа PARSING 7 не вдалося. Вирази скопійовано дослівно з PARSING.md, тож розбіжність не від копіювання; чим саме рахував PARSING 7, невідомо. Для AerisRimor, StrategicaviationT, monitorwarr, vanek_nikolaev файлів ще немає: `check` друкує PEND, цю перевірку повторити після докачки.
5. Перегляди, `check` друкує сирий вигляд і значення таблиці: `GeneralStaffZSU/37672` `'8.97K'` це 8970; `V_Zelenskiy_official/18768` `'2.22M'` це 2220000; `VA_Kyiv/21675` `'1'` це 1; `GeneralStaffZSU/42097` NULL лишається NULL; `6.83K`, `1.2M`, `55` і NULL дають 6830, 1200000, 55 і NULL.
6. `ASOF` на 3 випадкових годинах (seed 20261010) повертає стільки рядків, скільки дає незалежний підрахунок `available_at < t` у pyarrow, і жоден `published_at` не пізніший за t. Самі t і кількості залежать від стану bronze, тому тут їх не наведено.
7. Інваріанти: `available_at = published_at`; `channel_role`, `rx_classes`, `rx_signals`, `rx_kyiv_city`, `rx_evidence` ніколи не NULL; `rx_evidence` true лише коли `rx_kyiv_city` true. Кінець виводу `check`: `ALL OK`.

## Пастки

- `rx_signals` рахується для кожного поста кожного каналу, а сигнали визначено лише для `SIGNAL_CHANNELS` (7 каналів PARSING 7). У `mod_russia` чи `GeneralStaffZSU` «Кинджал» або «Калібр» означає інше; споживач S4 мусить фільтрувати за каналом.
- Для правил «2 незалежні канали» брати лише `is_original` (репости: КМВА репостить Кличка, AerisRimor репостить kpszsu).
- `rx_kyiv_city` для каналів `KYIV_ONLY` true майже для кожного непорожнього поста без слів `OBLAST` (реклама теж); справжній доказ це `rx_evidence`.
- `views` і текст постів з `edited` описано в розділі про час доступності.
- Цитату відповіді в `text` не збережено. Так само, ймовірно, не збережено її в числах PARSING 7: див. пункт 4 Перевірки.
- Поки канал докачується, у таблиці лише його найновіша частина (докачка іде від нових до старих); перший `published_at` у виводі показує, як далеко дійшло. Не склеювати таку таблицю з іншою: збірка завжди повна.
- `UkraineAlarmSignal` не повна стрічка eTryvoga, а кілька годин біля відбою без старту; рахувати за ним тривоги не можна.
- Пост без тексту (лише медіа) має порожній `text`, порожні `rx_classes` і `rx_signals`, `rx_kyiv_city` false.
- Кількість постів може відрізнятися від PARSING на 1-2 % через видалення; на добі 2026-10-09 розбіжності по постах немає (три канали з файлом).
