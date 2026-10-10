# kyiv_threat_hourly

Мітка ракетного удару по місту Київ за годинами: пости 7 каналів, оцінки Jev, правило години, ознаки і ціль для gold. Таблиці silver `kyiv_threat_hourly` і `kyiv_threat_posts`, модуль `src/airalerts/silver/threat_hourly.py`. Правила: [PARSING.md](../../PARSING.md) розділ 2, [JEV.md](../../JEV.md). Рівні даних і контракт: [ARCHITECTURE.md](../../ARCHITECTURE.md).

## Що це

Один рядок `kyiv_threat_hourly` = одна година h (UTC) і чотири мітки за постами 7 київських каналів у [h, h+1 год). `missile_strike` = true, якщо ракети (балістичні, крилаті, гіперзвукові) вибухали над містом Київ, були збиті над ним, впали на нього уламками або влучили в нього. Самі дрони не рахуються, Київщина поза містом не рахується, попередження саме по собі не рахується: воно в окремих мітках `missile_threat` (ракети летять на Київ або загроза ракет), `drone_threat` (дрони летять на Київ чи вибухають у ньому), `ballistic` (балістика йде на Київ). Рядки є для кожної години від 2026-04-16T21:00Z (`FETCH_FROM`) до останньої повної години, без пропусків.

Один рядок `kyiv_threat_posts` = один пост, що пішов до Jev, з чотирма ймовірностями.

## Bronze

Вхід: `data/silver/tg_posts.parquet` (шматок S2) і 7 каналів: VA_Kyiv, vitaliy_klitschko, truexakyiv, war_monitor, AerisRimor, kyiv_nebo, kyiv_airdef. Їхній bronze `data/bronze/telegram/<канал>.jsonl` модуль читає лише через `airalerts.telegram.load`, щоб узяти `fetched_at`. S3b нічого не завантажувала і Jev не викликала: усі відповіді взяті з кешу Jev `data/silver/_jev_cache/kyiv_threat_hourly/`, який наповнила команда `classify`. Як забрано канали: [tg_posts.md](tg_posts.md).

- Кінець даних мітки `label_end()`: для кожного з 7 каналів береться `fetched_at` найновішого поста в bronze, далі найраніший з семи. Мітити можна лише години h з h + 1 год <= `label_end`. Рахується в коді з bronze, числа в коді немає. Зараз `label_end()` = 2026-10-10T17:11:14Z, остання година мітки 2026-10-10T16:00:00Z (Перевірка, команди 1 і 3). Його ж пише `build` у метадані Parquet (ключ `label_end`).
- Префільтр у коді: пост іде до Jev, якщо він з 7 каналів, текст не порожній і є хоч один клас `rx_classes` (PARSING 2) або канал у `KYIV_ONLY`. Години без таких постів отримують усі мітки false без виклику Jev. Скільки постів: сума `n_posts` 101974, з них до Jev (`n_posts_jev`) 98453, годин без жодного поста для Jev 508 (Перевірка, команда 3).
- Кеш Jev: 5467 файлів, $5.8547 (Перевірка, команда 2). Чинна розбивка потребує 5095 запитів (команда 8); решта кешу це запити, яких чинний код не будує (за S3a: проміжні розбивки пілота).

## Класифікатор Jev

- Запит на годину h: `state` = `{"posts": [...]}`, пости після префільтру з [h-1 год, h+1 год) у порядку часу, кожен `{id: канал/post_id, channel, minute: хвилина публікації двома цифрами, hour: "previous" або "this", text}`. Пости з часом >= h+1 год у state не потрапляють ніколи (витік). Попередня година дає лише контекст.
- Питання лише про пости години h, чотири `noul` на пост: `strike_<i>` (вибухи, збиття, уламки чи влучання ракет у місті Київ; раніші пости це контекст типу зброї), `threat_<i>` (ракети летять на Київ або загроза ракет), `drone_<i>`, `ballistic_<i>`; `<i>` це номер поста серед постів години h. Тексти питань англійською з `criteria` true і false лежать у `_Q` модуля; версія `PROMPT_VERSION` = `kyiv_threat_hourly-v1`, модель `jev.MODEL` = `jev-1.13.0`.
- Година, де запит завеликий (понад 60 постів або понад ліміт токенів), ділиться на кілька запитів з тим самим state. Запит до `MAX_REQUEST_TOKENS` = 54000 оціночних токенів, state до `MAX_STATE_TOKENS` = 26000 (Jev дозволяє 64k і 32k). Якщо state більший, спершу відкидаються найстаріші пости попередньої години (режим `dropped`); якщо пости години самі більші за ліміт, година ріжеться за часом на вікна, кожне з найближчими ранішими постами як контекстом (режим `windowed`). Оцінка токенів: `STATE_CHARS_PER_TOKEN` = 1.6 і `QUESTION_CHARS_PER_TOKEN` = 3.5; оцінка 3 символи на токен для кирилиці хибна і дала HTTP 400 `max_tokens_exceeded`.
- `classify` шле всі запити діапазону через `ask_many` (тег `kyiv_threat_hourly`, до 8 потоків) і відновлюється через кеш Jev: повторний запуск не коштує нічого. `build` Jev не викликає.

## Правило години

Година `missile_strike` = true, коли є хоч один пост-доказ: оригінальний пост (`originals`), що йде після ракетної тривоги (`fresh`) і має `p_strike` >= 0.7 (`RULE["strike"]` у коді, ключ `one`). Інших умов немає.

Фільтри:

- `fresh`: за 90 хв до поста (`FRESH_MINUTES`; годину h-1 теж читаємо, вікно не сягає раніше за її початок; сам пост враховується) пости з `p_threat` >= 0.8 (`THREAT_GATE`) прийшли щонайменше з 3 різних каналів із 7 (`THREAT_CHANNELS`). Або пост сам і тривога, і звіт про удар: `p_threat` >= 0.8 і `p_strike` >= 0.7 (`SELF_STRIKE`), як "Ракета на Київ." truexakyiv/82393 у 2026-08-16T06 (0.91 і 0.72, команда 10). Фільтр прибирає звіти про наслідки через години після атаки, загальні попередження одного каналу і години лише з дронами. Правила A і B з PARSING 2 цього не вміють.
- `originals`: репости (`forwarded_from` не порожнє) не рахуються. КМВА репостить зведення президента, ДСНС і ДТЕК; такі пости давали хибні години.

Інші три мітки (`missile_threat`, `drone_threat`, `ballistic`): правило іншого виду, без фільтрів `fresh` і `originals` (репост попередження AerisRimor з kpszsu може бути єдиним джерелом у 7 каналах). Година true, коли є пост з ймовірністю >= 0.8 (`one`), або пост офіційного каналу (VA_Kyiv, vitaliy_klitschko) >= 0.5 (`official`), або оригінальні пости щонайменше 2 різних каналів, у кожного >= 0.5 (`two`). Перевірено на трьох відомих подіях; години загрози без удару читав перевіряльник S3b (пропущених ударів не знайшов) і я (можливі пропуски описані в Пастках). Сумнівні прапори `missile_threat` дають повідомлення про готовність носіїв, а не політ ракет (kyiv_airdef/40030 і kyiv_airdef/40035 мають `p_threat` 0.93 і 0.87, команда 10; години 2026-06-29T18 і 2026-06-30T11).

Чому так. Пілот S3a: 93 години (`pilot_hours()`, зерно 20261010): 3 відомі події, 20 годин з найбільшою кількістю постів `rx_evidence`, 30 випадкових годин з постами, 20 випадкових годин, де правило A або B істинне, 20 межових (10 з `rx_evidence`, але без A і B, 10 з постом `missile_threat` і постом про вибух чи уламки, але без `rx_evidence`). Тексти і ймовірності прочитав будівельник S3a: по 24 годинах поставив мітку, 4 лишив непевними (мітки це його судження, а не еталон):

- удар (6): 2026-06-02T01, 2026-06-15T00, 2026-08-16T06, 2026-10-07T00, 2026-10-07T01, 2026-10-10T11 (за словами "влучання ракети", "Ракета на Київ", "Гучно" на тлі балістики, вибухи в Києві);
- не удар (18): 2026-05-14T10, 2026-05-24T09, 2026-06-02T09, 2026-08-19T09, 2026-08-20T09 (наслідки нічної атаки, лічильники постраждалих), 2026-05-24T07, 2026-06-10T09, 2026-07-08T03, 2026-08-08T07 (репост зведення, "нічна атака"), 2026-08-18T16, 2026-09-01T07, 2026-09-01T08, 2026-09-09T07, 2026-09-15T13, 2026-09-28T04, 2026-09-28T17, 2026-10-01T19, 2026-10-04T14 (уламки БпЛА, шахед, дрон);
- непевні (4): 2026-06-14T22, 2026-09-27T18, 2026-09-27T19, 2026-10-07T14 (уламки, у тексті Кличка БпЛА або тип зброї не названо).

Перша версія правила S3a (гейт: один пост з `p_threat` >= 0.5 за 90 хв; година true при посту `p_strike` >= 0.7, або посту КМВА чи Кличка >= 0.5, або двох каналах >= 0.5) правильно розділила ці 24 години, але перевірка S3b прочитала випадкові години удару і знайшла явно хибні:

- лише дрони: 2026-09-22T14 (гейт відкрив kyiv_airdef/63399 "Бандеролі не спостерігаються. З Брянської зайшов четвертий реактив", `p_threat` 0.52; пости "Гучно!", "Падає на Муромець", "Впав" мають `p_strike` 0.53-0.57) і 2026-09-30T19 (гейт відкрив AerisRimor/89074 "3 реактивних з Чернігівської області на Київщину", 0.52; ракетних слів немає);
- звіти про наслідки: 2026-05-24T08 (truexakyiv/76702 "Пошкоджена будівля МЗС України", `p_strike` 0.71; гейт відкрив truexakyiv/76696, коментар про час підльоту "Цирконів", `p_threat` 0.76) і 2026-08-20T05 (vitaliy_klitschko/7269 "пошкодження зафіксовані у трьох районах міста", 0.61; гейт відкрило нічне зведення war_monitor/42822, 0.67). Числа: команда 10.

Причина одна: гейт 0.5 від одного поста пропускає заперечення, реактивні дрони, коментарі і зведення. Тому гейт став: `p_threat` >= 0.8 від 3 різних каналів за 90 хв (або сам пост це тривога і звіт). Умови `official` і `two` для удару прибрано, лишилась одна: з новим гейтом `official` додав би хибну годину 2026-07-13T22 (vitaliy_klitschko/7095 "виявили вирву біля будівлі школи" о 22:34, `p_strike` 0.56, за 77 хв після тривоги в 7 каналах; команди 10 і 11), а всі прочитані години удару проходять і за однією умовою `one` (selftest, команда 4). Поріг 3 каналів і 0.8 підібрано за прочитаними годинами, не за еталоном.

Перевірка після правки: `selftest` (команда 4) перевіряє 10 прочитаних годин удару (6 з S3a, 4 з перевірки S3b) і 37 прочитаних годин без удару (18 S3a, 6 хибних годин попередньої версії, 10 годин загрози без удару, 3 прочитані при правці: нічне зведення, вирва після атаки, БпЛА); списки `READ_TRUE` і `READ_FALSE` у коді. Усі стоять на своїх місцях. Сім годин з `missile_strike` без A і B (2026-06-25T17, 2026-06-27T22, 2026-06-27T23, 2026-07-01T22, 2026-07-30T00, 2026-08-08T01, 2026-09-01T00) я прочитав у файлі `report --out`: за текстами це вибухи чи влучання в Києві після тривоги балістики чи крилатих ракет. Це моє читання, не еталон.

Пілот на 93 годинах (команда 9): фільтр `fresh` прибирає години наслідків і дронів: правило `any>=0.5` без нього позначає 35 годин пілота, з ним 26. Фільтр `originals` на цих годинах уже нічого не додає (26 проти 26), але лишений: КМВА репостить зведення. Правила A і B PARSING 2 позначають ударом 16 з 18 прочитаних годин "не удар" (розділ DISAGREEMENTS команди `pilot`). Таблиця кандидатів і відомі події: Перевірка, команда 9.

Повний діапазон (команда 5 Перевірки): 77 годин з `missile_strike` з 4244; A або B істинні в 367 годинах (70 збігаються з міткою, 297 без мітки), 7 годин мітки без A і B. Файл з 30 найбільшими розбіжностями і текстами пише `report --out`; що в ньому видно, див. Пастки.

## Колонки

`kyiv_threat_posts` (рядок = пост, що пішов до Jev):

| колонка | тип | опис |
|---|---|---|
| `channel` | VARCHAR | канал |
| `post_id` | BIGINT | id поста в каналі |
| `published_at` | TIMESTAMP (UTC) | час публікації |
| `hour_utc` | TIMESTAMP (UTC) | година h, якій належить пост |
| `p_strike` | DOUBLE | ймовірність "так": пост повідомляє про вибухи, збиття, уламки чи влучання ракет у місті Київ |
| `p_threat` | DOUBLE | ймовірність "так": ракети летять на Київ або загроза ракет для Києва |
| `p_drone` | DOUBLE | ймовірність "так": дрони летять на Київ чи вибухають у ньому |
| `p_ballistic` | DOUBLE | ймовірність "так": балістика йде на Київ |
| `jev_model` | VARCHAR | модель Jev (`jev-1.13.0`) |
| `prompt_version` | VARCHAR | версія питань (`kyiv_threat_hourly-v1`) |
| `available_at` | TIMESTAMP (UTC) | кінець години поста: `hour_utc` + 1 год |

`kyiv_threat_hourly` (рядок = година h):

| колонка | тип | опис |
|---|---|---|
| `hour_utc` | TIMESTAMP (UTC) | початок години h |
| `n_posts` | BIGINT | усі пости 7 каналів у [h, h+1 год) з `tg_posts` |
| `n_posts_jev` | BIGINT | пости, що пройшли префільтр і пішли до Jev (рядки `kyiv_threat_posts` цієї години) |
| `missile_strike` | BOOLEAN | мітка за правилом години |
| `missile_threat` | BOOLEAN | ракети летять на Київ або загроза ракет |
| `drone_threat` | BOOLEAN | дрони летять на Київ чи вибухають у ньому |
| `ballistic` | BOOLEAN | балістика йде на Київ |
| `p_strike_max` | DOUBLE | найбільше `p_strike` серед постів години; null, коли `n_posts_jev` = 0 |
| `first_strike_at` | TIMESTAMP (UTC) | `published_at` найранішого поста з `evidence`; null, коли `missile_strike` = false |
| `evidence` | VARCHAR[] | `канал/post_id` постів, що рахуються правилом (пройшли `fresh` і `originals`) і мають `p_strike` >= 0.5, у порядку часу; порожній, коли `missile_strike` = false |
| `rx_rule_a` | BOOLEAN | правило A PARSING 2: пост КМВА чи Кличка з `rx_evidence`, за 90 хв до нього пост `missile_threat` (`regex_rules()`, лише довідка) |
| `rx_rule_b` | BOOLEAN | правило B PARSING 2: оригінальні пости `rx_evidence` двох різних моніторингових каналів у межах 30 хв, за 90 хв до раннішого з них є пост `missile_threat` (лише довідка) |
| `jev_model` | VARCHAR | модель Jev |
| `prompt_version` | VARCHAR | версія питань |
| `available_at` | TIMESTAMP (UTC) | `hour_utc` + 1 год |

Метадані Parquet обох файлів: `label_end`, `jev_model`, `prompt_version`. У `kyiv_threat_posts` немає `is_original`: репост видно в `tg_posts` (`forwarded_from`, `is_original`), з'єднання за `channel` і `post_id`.

## Час доступності

Мітка години h бачить пости лише до h+1 год, тож рядок години відомий з h+1 год: `available_at` = `hour_utc` + 1 год. Те саме для поста: ймовірності поста використали пости до кінця його години. Контекст попередньої години дозволений, наступної ніколи (JEV.md, розділ Витік). Для постів з `edited` див. [tg_posts.md](tg_posts.md): текст відредагованого поста міг змінитися пізніше.

`ASOF` цього модуля бере `available_at <= {t}`, а не загальне `< {t}`: пости години h мають `published_at` < h+1 год, тож у момент t = h+1 год година відома повністю, і `features()` її читає. Загальне `<` сховало б годину, що закінчується рівно в t, а всі t погодинні. Тест витоку gold має брати цей `ASOF`.

## Ознаки для gold

`features(con, t_table)` (`con` бачить view `kyiv_threat_hourly`; `t_table` має колонку `t_utc`) повертає `pyarrow.Table`: `t_utc` першою, далі 10 колонок, рівно один рядок на кожен `t_utc`. Бере лише години h з h + 1 год <= t (`available_at` <= t). Вікна рахуються цілими годинами до `floor_hour(t)`: для t на годині це рівно N годин перед t. Нулів (null) немає: година, якої немає в таблиці, не має міток. Дані від FETCH_FROM (T0 мінус 14 діб), тож 14-добові вікна повні з T0 (2026-04-30T21:00Z).

| колонка | тип | означення |
|---|---|---|
| `threat_prev_1h` | BOOLEAN | `missile_threat` години [t-1 год, t) |
| `threat_hours_6h` | BIGINT | число годин з `missile_threat` у [t-6 год, t), 0..6 |
| `threat_hours_24h` | BIGINT | те саме у [t-24 год, t), 0..24 |
| `ballistic_hours_3h` | BIGINT | число годин з `ballistic` у [t-3 год, t), 0..3 |
| `ballistic_hours_6h` | BIGINT | те саме у [t-6 год, t), 0..6 |
| `ballistic_hours_24h` | BIGINT | те саме у [t-24 год, t), 0..24 |
| `drone_threat_prev_1h` | BOOLEAN | `drone_threat` години [t-1 год, t) |
| `strikes_7d` | BIGINT | число годин з `missile_strike` у [t-168 год, t), 0..168 |
| `strikes_14d` | BIGINT | те саме у [t-336 год, t), 0..336 |
| `hours_since_strike` | DOUBLE | годин від кінця останньої години з `missile_strike` до t: 0, коли це година [t-1 год, t); 336 (стеля), коли в 336 годинах до t такої години немає |

`t_utc` пізніше за `floor_hour(label_end)` (кінець останньої мітченої години, зараз 2026-10-10T17:00Z) дає `ValueError`: пізніших годин у таблиці немає, ознаки мовчки вважали б їх спокійними. `label_end` береться з метаданих Parquet.

`labels(con, t_table, horizon_h=3)` повертає `t_utc` і `y_strike_3h` (BOOLEAN): true, коли хоч одна година з [t, t+3 год) має `missile_strike`. Null, коли t + 3 год пізніше за `label_end` (або t раніше за першу годину таблиці): зараз це t = 2026-10-10T15:00Z, 16:00Z, 17:00Z. Частка true на t від T0 з міткою: 0.0387 (151 з 3906, команда 4 Перевірки).

## Як перебудувати

```bash
M="choom -n 500 -- .venv/bin/python -I -m airalerts.silver.threat_hourly"
$M classify [--from ISO] [--to ISO] [--workers N]   # усі запити діапазону до Jev; --from вкл., --to викл.; без аргументів від FETCH_FROM до останньої години мітки; платить лише за нові запити
$M build          # те саме, що $M без команди і main(): обидві таблиці silver з кешу Jev, без викликів Jev
$M report --out FILE   # матриці збігу з A і B, місячні підрахунки, 30 найбільших розбіжностей з текстами у FILE
$M selftest       # таблиці, прочитані години, features() і labels() на кожній годині від T0, ASOF на 3 випадкових t
$M check          # тест витоку запитів до Jev (S3a), без Jev
$M pilot          # пілот S3a: таблиця, кандидати, відомі події, приклади, розбіжності з A і B
$M stats [--from ISO] [--to ISO]   # розмір і оцінка вартості діапазону, без Jev
$M calibrate      # символів на токен за кешем Jev
$M label_end      # кінець даних мітки
```

Порядок після нових даних: перебудувати `tg_posts`, `classify`, `build`. Якщо `label_end` зрушив, а `classify` ще не пройшов, `build` не пише нічого і виходить з повідомленням `blocked` та списком годин, для яких немає запиту в кеші; під час `build` функція виклику API в `jev.py` замінена на таку, що кидає виняток, тож викликів Jev немає. Правило години (поріг, число каналів) змінює лише `build`: ймовірності постів у кеші ті самі.

## Перевірка

Усі команди з кореня репозиторію. Виводи нижче отримані двома повними прогонами, які дали однаковий результат (час виконання в виводі не друкується).

1. Кінець даних мітки:

```bash
.venv/bin/python -I -c "from airalerts.silver.threat_hourly import label_end; print(label_end())"
```

```text
2026-10-10T17:11:14Z
```

2. Побудова з кешу без нових викликів Jev: витрати до, `build`, витрати після (однакові: кеш не змінився):

```bash
.venv/bin/python -I -m airalerts.jev kyiv_threat_hourly
M="choom -n 500 -- .venv/bin/python -I -m airalerts.silver.threat_hourly"
$M build
.venv/bin/python -I -m airalerts.jev kyiv_threat_hourly
```

```text
{'calls': 5467, 'input_tokens': 139396902, 'usd': 5.8547}
label_end 2026-10-10T17:11:14Z; 4244 hours; answers of 98453 posts read from the Jev cache
{'kyiv_threat_posts rows': 98453, 'kyiv_threat_hourly rows': 4244, 'first_hour': '2026-04-16T21:00:00Z', 'last_hour': '2026-10-10T16:00:00Z', 'label_end': '2026-10-10T17:11:14Z', 'strike_hours': 77, 'threat_hours': 425}
{'calls': 5467, 'input_tokens': 139396902, 'usd': 5.8547}
```

3. Розміри таблиць (годин, перша, остання, сума `n_posts`, сума `n_posts_jev`, годин без постів для Jev; потім постів, каналів, перший і останній `published_at`):

```bash
.venv/bin/python -I -c '
from airalerts.db import connect, register_layers
con = register_layers(connect())
print(con.execute("SELECT COUNT(*), MIN(hour_utc), MAX(hour_utc), SUM(n_posts), SUM(n_posts_jev), COUNT(*) FILTER (WHERE n_posts_jev = 0) FROM kyiv_threat_hourly").fetchall())
print(con.execute("SELECT COUNT(*), COUNT(DISTINCT channel), MIN(published_at), MAX(published_at) FROM kyiv_threat_posts").fetchall())
'
```

```text
[(4244, datetime.datetime(2026, 4, 16, 21, 0), datetime.datetime(2026, 10, 10, 16, 0), 101974, 98453, 508)]
[(98453, 7, datetime.datetime(2026, 4, 16, 21, 1, 15), datetime.datetime(2026, 10, 10, 16, 59, 56))]
```

4. Самотест: структура таблиць, година на рядок без пропусків, відомі години удару (2026-10-07T00, 01 і 2026-10-10T11), 10 прочитаних годин удару і 37 прочитаних годин без удару, `features()` і `labels()` на кожній годині від T0 до останнього можливого t проти простих циклів, помилка після останнього t, `ASOF` на 3 випадкових t (результати збігаються з повним розрахунком), частка `y_strike_3h`:

```bash
$M selftest
```

```text
ok   label_end in the Parquet metadata is label_end() of bronze: 2026-10-10T17:11:14Z
ok   one row per hour, no gaps: 4244 rows from 2026-04-16T21:00:00Z to 2026-10-10T16:00:00Z
ok   first hour is FETCH_FROM, last hour ends at or before label_end
ok   available_at = hour_utc + 1 h; post hour = floor(published_at)
ok   n_posts_jev = posts of the hour in kyiv_threat_posts: 98453 posts
ok   posts unique by (channel, post_id)
ok   jev_model and prompt_version: jev-1.13.0 kyiv_threat_hourly-v1
ok   evidence and first_strike_at exist exactly for strike hours, first_strike_at inside the hour
ok   known strike hours are missile_strike: 2026-10-07T00:00:00Z, 2026-10-07T01:00:00Z, 2026-10-10T11:00:00Z
     2026-10-07T00:00:00Z first_strike_at 2026-10-07 00:14:30 evidence 11 posts, first ['truexakyiv/91761', 'AerisRimor/89414']
     2026-10-07T01:00:00Z first_strike_at 2026-10-07 01:19:42 evidence 1 posts, first ['VA_Kyiv/21516']
     2026-10-10T11:00:00Z first_strike_at 2026-10-10 11:00:27 evidence 16 posts, first ['war_monitor/47542', 'kyiv_airdef/78777']
ok   hand-read strike hours are missile_strike: 10 hours
ok   hand-read hours without a strike are not missile_strike: 37 hours
ok   features: t_utc first, columns as documented, one row per t: 3909 rows, t from 2026-04-30T21:00:00Z to 2026-10-10T17:00:00Z
ok   features: no nulls: none
ok   features equal the plain loops on every t: 3909 t, 0 differ []
ok   labels: t_utc first, y_strike_3h equals the plain loops
ok   labels: null only when t + 3 h is after label_end: 3 null: 2026-10-10T15:00:00Z, 2026-10-10T16:00:00Z, 2026-10-10T17:00:00Z
base rate of y_strike_3h = 0.0387 (151 of 3906 t with a label; 3909 t in all)
     t_utc 2026-10-10 18:00:00 is after the hour after the last labelled hour 2026-10-10T17:00:00Z (label_end 2026-10-10T17:11:14Z)
ok   features() raises ValueError for t = 2026-10-10T18:00:00Z
ok   ASOF t=2026-06-09T16:00:00Z: features equal True; hourly rows 1291 of 4244, posts 15957 of 98453
ok   ASOF t=2026-06-29T15:00:00Z: features equal True; hourly rows 1770 of 4244, posts 20548 of 98453
ok   ASOF t=2026-08-21T20:00:00Z: features equal True; hourly rows 3047 of 4244, posts 39411 of 98453
ALL OK
```

5. Звіт: матриці збігу `missile_strike` з A, B і (A або B), місячні підрахунки годин (місяць UTC), розбіжності. Клітинки: обидва, лише мітка, лише правило, жодне:

```bash
$M report --out FILE
```

```text
label_end 2026-10-10T17:11:14Z
confusion of missile_strike with the regex rules, all hours, 4244 hours; cells: both | strike only | rule only | neither
  rx_rule_a: 62 | 15 | 270 | 3897
  rx_rule_b: 51 | 26 | 59 | 4108
  A or B: 70 | 7 | 297 | 3870
confusion of missile_strike with the regex rules, hours from T0 2026-04-30T21:00:00Z, 3908 hours; cells: both | strike only | rule only | neither
  rx_rule_a: 62 | 15 | 268 | 3563
  rx_rule_b: 51 | 26 | 58 | 3773
  A or B: 70 | 7 | 294 | 3537
monthly counts of hours (UTC month): month | hours | missile_strike | missile_threat | drone_threat | ballistic
  2026-04 | 339 | 0 | 14 | 19 | 6
  2026-05 | 744 | 8 | 64 | 62 | 34
  2026-06 | 720 | 13 | 57 | 47 | 33
  2026-07 | 744 | 23 | 84 | 65 | 60
  2026-08 | 744 | 18 | 92 | 145 | 52
  2026-09 | 720 | 11 | 89 | 359 | 39
  2026-10 | 233 | 4 | 25 | 101 | 11
  all | 4244 | 77 | 425 | 798 | 235
disagreements: 7 hours strike without A or B, 297 hours A or B without strike; 30 largest with texts written to the --out file
```

6. Тест витоку запитів до Jev (S3a; читає пости через DuckDB окремо від модуля; перевіряє, що в state немає постів з часом >= h+1 год, що години-теги правильні, що пости state це рівно пости з [h-1 год, h+1 год), що питання покривають кожен пост години h один раз і що запити не змінюються, коли прибрано всі пізніші пости; година після `label_end` відхиляється). Тут останні 3 рядки, повний вивід має рядок на кожну з 30 годин:

```bash
$M check 2>&1 | tail -n 3
```

```text
hour after label_end refused: hour 2026-10-10T17:00:00Z ends after label_end 2026-10-10T17:11:14Z
label_end 2026-10-10T17:11:14Z; 30 hours checked (20 random, 10 dropped or windowed), 81 such hours in all, 0 failures
ALL OK
```

7. `classify` на діапазоні 6 годин: усі 12 запитів у кеші, 0 нових викликів:

```bash
$M classify --from 2026-10-06T21:00:00Z --to 2026-10-07T03:00:00Z 2>&1 | tail -n 1
```

```text
done: requests 12, new calls 0; cache kyiv_threat_hourly: {'calls': 5467, 'input_tokens': 139396902, 'usd': 5.8547}
```

8. Розмір і оцінка повного діапазону (без Jev):

```bash
$M stats
```

```text
label_end 2026-10-10T17:11:14Z; hours 4244 from 2026-04-16T21:00:00Z to 2026-10-10T16:00:00Z; with prefiltered posts 3736
requests 5095; hours by mode {'full': 3654, 'dropped': 68, 'windowed': 14}; hours with more than one request 535
estimated input tokens 118956899 (largest request 50967), estimated spend $5.00; characters per token 1.62 (state) and 3.82 (questions) from 5467 cached requests
```

9. Пілот S3a (рядок про групи, правило години проти A або B, таблиця кандидатів, відомі події; повний вивід команди `pilot` ще має таблицю з 93 годин, 10 прикладів і список розбіжностей). Усе з кешу, нових викликів немає:

```bash
$M pilot > /tmp/pilot_full.txt
{ sed -n '1p' /tmp/pilot_full.txt; sed -n '/^hour rule/,/^  posts of 2026-10-07/p' /tmp/pilot_full.txt | sed '$d'; }
```

```text
pilot hours 93: random 30, border_noev 10, border_ev 10, top_ev 20, rule_ab 20, known 3
hour rule {'one': 0.7, 'fresh': True, 'originals': True}: missile_strike true 26; with A or B 44; both 26, Jev only 0, A or B only 18, neither 49
candidate strike rules: name | true | both with A or B | Jev only | A or B only
  any>=0.5 | 35 | 33 | 2 | 11
  any>=0.8 | 25 | 25 | 0 | 19
  official>=0.5 or 2ch>=0.5 | 31 | 30 | 1 | 14
  any>=0.8 or official>=0.5 or 2ch>=0.5 | 33 | 32 | 1 | 12
  fresh and any>=0.5 | 26 | 26 | 0 | 18
  fresh and any>=0.7 | 26 | 26 | 0 | 18
  fresh and any>=0.8 | 23 | 23 | 0 | 21
  fresh and (official>=0.5 or 2ch>=0.5) | 24 | 24 | 0 | 20
  fresh and (any>=0.7 or official>=0.5 or 2ch>=0.5) | 26 | 26 | 0 | 18
  fresh and (any>=0.8 or official>=0.5 or 2ch>=0.5) | 25 | 25 | 0 | 19
  fresh and (any>=0.7 or official>=0.7 or 2ch>=0.5) | 26 | 26 | 0 | 18
  fresh, originals and any>=0.7 | 26 | 26 | 0 | 18
  fresh, originals and (any>=0.7 or official>=0.5 or 2ch>=0.5) | 26 | 26 | 0 | 18
known events:
  2026-10-07T00:00:00Z missile_strike True; posts with p_strike >= 0.5: 11; earliest truexakyiv/91761 00:14:30Z p=0.51 | ВАСИЛЬКІВ! /  / Труха⚡️Київ | Надіслати новину
    earliest with p_strike >= 0.7: truexakyiv/91762 00:14:55Z p=0.82
  2026-10-07T01:00:00Z missile_strike True; posts with p_strike >= 0.5: 1; earliest VA_Kyiv/21516 01:19:42Z p=0.78 | У Дарницькому районі уламки впали на відкритій території.
    earliest with p_strike >= 0.7: VA_Kyiv/21516 01:19:42Z p=0.78
  2026-10-10T11:00:00Z missile_strike True; posts with p_strike >= 0.5: 17; earliest war_monitor/47542 11:00:27Z p=0.92 | 💥 Вибухи у Києві / Загроза балістики триває.
    earliest with p_strike >= 0.7: war_monitor/47542 11:00:27Z p=0.92
```

Перший пост з `p_strike` >= 0.7 о 2026-10-07T00 це truexakyiv/91762 (00:14:55Z, "Гучно!"), як вимагає перевірка: 91762 або раніше. `first_strike_at` цієї години 00:14:30Z (truexakyiv/91761 "ВАСИЛЬКІВ!", 0.51; Васильків це Київщина) ще раніший (команда 4).

10. Пости, на які посилається правило години (час UTC, `p_strike`, `p_threat`):

```bash
.venv/bin/python -I - <<'EOF'
from airalerts.db import connect, register_layers
con = register_layers(connect())
q = """SELECT channel || '/' || post_id AS post, strftime(published_at, '%Y-%m-%d %H:%M:%S') AS at,
round(p_strike, 2) AS p_strike, round(p_threat, 2) AS p_threat FROM kyiv_threat_posts
WHERE (channel, post_id) IN (('kyiv_airdef', 63399), ('truexakyiv', 76696), ('truexakyiv', 76702), ('kyiv_airdef', 40030),
('kyiv_airdef', 40035), ('vitaliy_klitschko', 7095), ('truexakyiv', 82393), ('war_monitor', 42822), ('vitaliy_klitschko', 7269),
('truexakyiv', 89897), ('AerisRimor', 89074)) ORDER BY published_at"""
for r in con.execute(q).fetchall():
    print(r)
EOF
```

```text
('truexakyiv/76696', '2026-05-24 07:15:19', 0.13, 0.76)
('truexakyiv/76702', '2026-05-24 08:00:39', 0.71, 0.07)
('kyiv_airdef/40030', '2026-06-29 18:16:52', 0.03, 0.93)
('kyiv_airdef/40035', '2026-06-30 11:18:57', 0.03, 0.87)
('vitaliy_klitschko/7095', '2026-07-13 22:34:41', 0.56, 0.05)
('truexakyiv/82393', '2026-08-16 06:50:22', 0.72, 0.91)
('war_monitor/42822', '2026-08-20 04:05:23', 0.26, 0.67)
('vitaliy_klitschko/7269', '2026-08-20 05:04:43', 0.61, 0.13)
('kyiv_airdef/63399', '2026-09-22 14:23:56', 0.06, 0.52)
('truexakyiv/89897', '2026-09-28 12:15:38', 0.56, 0.12)
('AerisRimor/89074', '2026-09-30 18:29:02', 0.04, 0.52)
```

11. Години, про які йдеться в правилі й у Пастках (мітка удару, мітка загрози, найбільше `p_strike`, `evidence`):

```bash
.venv/bin/python -I - <<'EOF'
from airalerts.db import connect, register_layers
con = register_layers(connect())
q = """SELECT strftime(hour_utc, '%Y-%m-%dT%H') AS hour, missile_strike, missile_threat, round(p_strike_max, 2) AS p_strike_max, evidence
FROM kyiv_threat_hourly WHERE strftime(hour_utc, '%Y-%m-%dT%H') IN ('2026-05-24T08', '2026-07-13T22', '2026-08-16T06', '2026-08-20T05',
'2026-08-23T18', '2026-08-27T16', '2026-09-22T14', '2026-09-28T14', '2026-09-30T00', '2026-09-30T19', '2026-10-04T07') ORDER BY hour_utc"""
for r in con.execute(q).fetchall():
    print(r)
EOF
```

```text
('2026-05-24T08', False, False, 0.71, [])
('2026-07-13T22', False, False, 0.56, [])
('2026-08-16T06', True, True, 0.83, ['truexakyiv/82393'])
('2026-08-20T05', False, False, 0.61, [])
('2026-08-23T18', False, True, 0.85, [])
('2026-08-27T16', True, True, 0.75, ['VA_Kyiv/19965', 'truexakyiv/83433'])
('2026-09-22T14', False, False, 0.57, [])
('2026-09-28T14', False, True, 0.61, [])
('2026-09-30T00', False, True, 0.68, [])
('2026-09-30T19', False, False, 0.61, [])
('2026-10-04T07', False, False, 0.74, [])
```

## Пастки

- Jev дає `p_strike` не за часом події, а за тим, що пост розповідає: звіт про наслідки теж отримує 0.6-0.8 (truexakyiv/76702 "Пошкоджена будівля МЗС України", 0.71, команда 10). Це прибирає фільтр `fresh` (потрібна тривога з 3 каналів за 90 хв). Звіт про наслідки в межах 90 хв від справжньої тривоги лишається хибним доказом; приклад, який я вважаю сумнівним: 2026-08-27T16 (VA_Kyiv/19965 "фіксується падіння уламків на дах гуртожитку", 0.75; три канали попереджали про ракетну загрозу, зброя в самому пості не названа; мітка true, команда 11).
- Короткі пости ("Падає", "Впав", "Вибух", "Гучно") без типу зброї Jev оцінює `p_strike` 0.5-0.7, часто разом з високим `p_drone`. Поріг 0.7 їх відсікає, якщо в годині немає сильнішого поста; "Гучно." після тривоги балістики його має (2026-06-25T17: 0.76).
- Клас зброї не вирішено для "ракет Герань-5", "мгКР" і "Бандероль" (реактивні апарати, у постах їх називають ракетами). Попередження про них мають `p_threat` 0.57-0.74, нижче 0.8, тож години 2026-09-28T14, 2026-08-23T18 і 2026-10-04T07 мають `missile_strike` = false (команда 11); за визначенням крилаті ракети рахуються, тож це можливі пропуски. Те саме 2026-09-28T12 (truexakyiv/89897 "Влучання ракети Герань-5 у Центрі Києва", `p_strike` 0.56, команда 10).
- Можливий пропуск іншого роду: 2026-09-30T00 (A і B true, `ballistic` true; пости "Звуки вибухів які лунали в Києві" 0.68 і КМВА "внаслідок ворожого удару виникло загоряння" 0.63 нижче 0.7; команда 11). Це моє читання, не еталон.
- У 23 найбільших розбіжностях "A або B true, мітка false" (файл `report --out`) за моїм читанням майже всі це удари БпЛА по будинках ("Дрон ударив по будівлі СБУ", "БпЛА впав на багатоповерхівку", "падіння уламків БпЛА") і звіти про наслідки (2026-06-02T03, 2026-06-15T02, 2026-07-02T02, 2026-08-20T05): мітка false правильна. Сім годин "мітка true без A і B" прочитано (Правило години).
- Уламки без типу зброї ("уламки впали на дах") Jev оцінює близько 0.5; у тексті Кличка зазвичай є слово БпЛА, тоді `p_drone` високе, а `p_strike` близько 0.3-0.5. Поріг 0.7 для окремого поста відрізняє їх лише частково (годину 2026-10-07T14 лишено непевною).
- Подія з одного каналу: 2026-08-16T06 стала ударом лише через `SELF_STRIKE`: тривогу ("Ракета на Київ.", `p_threat` 0.91) дав один канал, і він же `p_strike` 0.72 (команди 10 і 11). Без цієї умови потрібні були б 3 канали.
- Перший пост-доказ може бути поза містом: 2026-10-07T00 о 00:14:30Z truexakyiv/91761 "ВАСИЛЬКІВ!" має 0.51 і стоїть першим у `evidence` та в `first_strike_at`. Година істинна й за іншими постами; `first_strike_at` це час першого поста-доказу, не гарантія, що вибух саме в місті.
- Вікно `fresh` не сягає раніше за початок години h-1: для поста в перші 30 хв години h 90 хв сягали б у годину h-2, її пости не читаються, тож тривога, що була лише в останні до 30 хв години h-2, не враховується.
- Правило обрано на 93 годинах пілота, прочитаних S3a, перевіряльником і мною; читання не еталон. Повний діапазон перевірено розбіжностями з A і B (команда 5) і читанням 30 найбільших, не еталоном.
- Ймовірності залежать від розбивки запиту: ті самі пости в іншому запиті можуть дати числа, що відрізняються на кілька сотих. Зміна `MAX_REQUEST_TOKENS`, `MAX_STATE_TOKENS`, `PROMPT_VERSION`, питань чи префільтру змінює ключі кешу: тоді `build` зупиниться з `blocked` і списком годин, потрібен новий `classify` (платний). Зміна порогів правила години ключів не змінює.
- Кеш Jev містить запити від проміжних розбивок пілота; вони не шкодять, але входять у витрати (`usage` рахує всі файли тега).
- `label_end` рахується з bronze: коли канали докачають, він зсувається, `label_hours()` росте, а `build` вимагає `classify` для нових годин. Таблиці й метадані `label_end` перебудовуються разом.
- Перша година даних (FETCH_FROM) не має контексту попередньої години, тож `fresh` для неї рахується лише за власними постами. Ознаки для t раніше за FETCH_FROM + 14 діб мали б неповні вікна; gold бере t від T0.
- `ASOF` тут `available_at <= {t}` (розділ Час доступності). Загальний шаблон `< {t}` для цих таблиць дав би інші ознаки на кожному t.
- Ліміти Jev: 64k токенів на запит, 32k на state. Якщо `classify` повертає `HTTP 400 max_tokens_exceeded`, зменшити `MAX_REQUEST_TOKENS` чи `MAX_STATE_TOKENS`: вже відповіді лишаються в кеші, але ключі нових запитів зміняться.
- Правила A і B з PARSING 2 лише довідкові: на повному діапазоні вони істинні в 367 годинах проти 77 за міткою, а 16 з 18 прочитаних годин "не удар" пілота вони позначають ударом.
