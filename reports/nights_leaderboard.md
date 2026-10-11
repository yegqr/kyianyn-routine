# Нічне питання: чи йти спати в коридор

Згенеровано `.venv/bin/python -I -m airalerts.modeling.nights`, не редагувати вручну. Рішення о 22:00 за Києвом; ціль: ракетний удар по Києву з 22:00 до 08:00 ([ADR-0010](../docs/adr/0010-night-question.md)). Поділ як у погодинних моделей ([ADR-0008](../docs/adr/0008-time-split.md)). Лише розробка: тест відкриває `final`, один раз.

Як читати:

- **BSS**: на скільки прогноз кращий за «завжди частка ракетних ночей, відома на початок тижня». 0 це той самий рівень, більше 0 краще.
- **ROC AUC**: шанс, що ракетна ніч отримає вищий прогноз за тиху; 0.5 це монетка.
- **Поріг** (задано до запуску моделей): найвищий, за якого модель ще попереджає про 80% ракетних ночей розробки. Від нього: атак попереджено, зайвих ночей у коридорі, частка справжніх попереджень.
- **Вердикт**: різниця BSS з `naive_7n` (частка ракетних ночей за останні 7) на тих самих ночах, 95% інтервал bootstrap по ночах, 1000 повторів.
- **Фіналіст** (★, правило задано до запуску): найкращий BSS на розробці; модель з меншою кількістю ознак, якщо вона гірша менш ніж на 0.01.

Фіналіст за правилом: ★ `refractory`.

## Моделі

- `clim_recent`: recent attack rate: 28-night share pulled to the fit share from 2026-05-13 (10 nights)
- `gaussian_nb`: Gaussian naive Bayes, var_smoothing 1, 7 features chosen by meaning, fit from 2026-05-13
- `hazard_table`: smoothed attack share by nights since the last attack (all fit nights), scaled to the recent level
- `knn`: share of attacks among the 25 nearest nights on 7 scaled features, fit from 2026-05-13
- `lgbm_tiny`: LightGBM, 100 trees of depth 2, 7 features chosen by meaning, fit from 2026-05-13
- `logit_2`: L2 logistic regression on the pause after an attack: attack last night, nights since attack (cap 14)
- `logit_5`: logit_2 plus three evening signals: strategic aviation takeoffs 24 h, threat hours 6 h, alerts 3 h
- `logit_all_l1`: negative control: L1 logistic regression on every column of the nightly table
- `naive_7n`: share of attack nights among the 7 nights before
- `naive_bayes`: categorical naive Bayes: nights since attack in 5 buckets, strategic aviation takeoff in the last 6 h
- `random_forest`: random forest, 500 trees of depth 3, at least 10 nights per leaf, 7 features chosen by meaning, fit from 2026-05-13
- `refractory` ★: Jeffreys rate after an attack night, else the recent rate of nights not after one
- `renewal_nb`: renewal model: negative binomial gaps between attack nights, hazard of the current gap

## Розробка, walk-forward: 56 ночей, 16 з атакою

| модель | ознак | BSS | ROC AUC | PR AUC | поріг | атак попереджено | зайвих ночей у коридорі | частка справжніх | ΔBSS з naive_7n | вердикт |
|---|---|---|---|---|---|---|---|---|---|---|
| `refractory` | 2 | 0.159 [0.013, 0.245] | 0.614 [0.466, 0.755] | 0.333 [0.212, 0.535] | 0.253 | 13/16 | 22/40 | 0.37 | 0.236 [0.102, 0.405] | краще |
| `naive_bayes` | 2 | 0.128 [-0.004, 0.234] | 0.677 [0.523, 0.816] | 0.441 [0.264, 0.676] | 0.176 | 13/16 | 19/40 | 0.41 | 0.206 [0.061, 0.395] | краще |
| `hazard_table` | 2 | 0.122 [-0.072, 0.270] | 0.672 [0.525, 0.810] | 0.437 [0.248, 0.662] | 0.191 | 13/16 | 21/40 | 0.38 | 0.200 [0.029, 0.395] | краще |
| `logit_5` | 5 | 0.118 [-0.020, 0.234] | 0.669 [0.498, 0.820] | 0.446 [0.263, 0.725] | 0.172 | 13/16 | 22/40 | 0.37 | 0.196 [0.025, 0.404] | краще |
| `logit_2` | 2 | 0.103 [0.013, 0.165] | 0.638 [0.492, 0.780] | 0.396 [0.231, 0.616] | 0.216 | 13/16 | 22/40 | 0.37 | 0.181 [0.042, 0.371] | краще |
| `renewal_nb` | 1 | 0.097 [-0.058, 0.204] | 0.590 [0.423, 0.742] | 0.332 [0.209, 0.565] | 0.275 | 13/16 | 22/40 | 0.37 | 0.175 [0.000, 0.376] | краще |
| `random_forest` | 7 | 0.055 [-0.020, 0.122] | 0.609 [0.442, 0.770] | 0.382 [0.222, 0.630] | 0.137 | 13/16 | 23/40 | 0.36 | 0.133 [-0.005, 0.326] | не розрізнити |
| `lgbm_tiny` | 7 | 0.044 [-0.077, 0.163] | 0.620 [0.441, 0.792] | 0.397 [0.234, 0.682] | 0.095 | 13/16 | 21/40 | 0.38 | 0.122 [-0.032, 0.333] | не розрізнити |
| `clim_recent` | 1 | 0.041 [-0.057, 0.091] | 0.370 [0.213, 0.533] | 0.233 [0.147, 0.384] | 0.202 | 13/16 | 36/40 | 0.27 | 0.119 [0.015, 0.260] | краще |
| `logit_all_l1` | 60 | 0.024 [-0.000, 0.037] | 0.402 [0.249, 0.550] | 0.244 [0.154, 0.398] | 0.175 | 13/16 | 36/40 | 0.27 | 0.102 [-0.020, 0.291] | не розрізнити |
| `knn` | 7 | -0.002 [-0.070, 0.070] | 0.596 [0.404, 0.775] | 0.378 [0.219, 0.621] | 0.040 | 15/16 | 39/40 | 0.28 | 0.076 [-0.100, 0.324] | не розрізнити |
| `gaussian_nb` | 7 | -0.026 [-0.058, 0.011] | 0.548 [0.352, 0.740] | 0.487 [0.255, 0.719] | 0.111 | 13/16 | 34/40 | 0.28 | 0.052 [-0.106, 0.291] | не розрізнити |
| `naive_7n` | 1 | -0.078 [-0.290, 0.052] | 0.316 [0.199, 0.427] | 0.257 [0.157, 0.380] | 0.143 | 16/16 | 40/40 | 0.29 |  | опорна |
