# CONTEXT.md — чекпоинт состояния проекта

Обновлять в конце каждой сессии. Новая сессия начинается с чтения этого файла + ROADMAP.md.

## Что это

MCP-сервер (Python, stdio, mcp) «ComboPizzaSushiMCP»: комбо-подборщик по 7 сетям
доставки Воронежа (la_pizza, pizza_kuba, ninja_food, sushi_time, sushi_darom,
anti_sushi, dodo). 10 MCP-инструментов: status, verify_chain, best_combo,
check_price, health_check, compare, get_chain_info, get_chains, clear_cache, refresh_cache.

## Как запускать

- Сервер: `.venv\Scripts\python.exe combo_mcp\server.py`
- Автотесты: `.venv\Scripts\python.exe scripts\autotest.py` (exit 0 = всё зелёное)
- Smoke MCP-протокол: `.venv\Scripts\python.exe scripts\smoke_test.py`
- Эталоны: `scripts\gen_expected.py` пересоздаёт tests/expected.json
- Важно: консоль PowerShell портит UTF-8 (mojibake) — читать вывод через файлы.

## Ключевые решения

- `best_combo(chain_id, budget, persons=1, variations=3, refresh=False)` →
  JSON с `combos[]`; persons>=1, variations>=1; во всех вариациях ровно persons напитков.
- Порядок вариаций: Оптимум → Без повторов → Макс. вес → доп. стратегии
  (variations>3: fewest_items, no_drinks_max, drinks_only).
- Детекция напитков: категория + эвристика RU/EN (drinks.py). Ложные срабатывания убраны:
  ГУАНТАНАМО, «тан», Мини Колада, «Фреш», Pepperoni Fresh.
- Веса: `weight_g` у позиции. Если парсер не дал вес — справочник
  `config/estimated_weights.json` (weight_source="reference", поле source — откуда взят вес).
  `weight_source`: site | size_name (pizza_kuba из названий размеров) | reference | none.
- Позиции без веса из комбо исключаются (мерч додо, палочки — намеренно).
- Локализация: `config/translations.json` (додо), модуль names.py: localize() + item_size_label().
  В комбо имена русские (бренды как есть), у каждой позиции вес единицы:
  «Пицца Пепперони Фреш (370 г) x2», справочные закуски «(9 шт, 20 г/шт)».
  ВАЖНО: в данных (кэш) имена оригинальные — перевод только в выводе (dp.format_combo,
  best_combo ставит _local_name/_size_label; детекция напитков по _orig_name).
- Кэш: cache\, stale-if-error; ninja_food обходится с адаптивным рейт-гейтом (_RateGate).
- LSP-варнинги в проекте — ложные (mcp.server.mcpserver import, reconfigure,
  .get на None в autotest.py) — не чинить.
- Кэш ninja хранит имена с литеральными `\"` — нормализация `_norm_name` в autotest.py.

## Состояние на 2026-08-16

- git: ветка main, remote github.com/1artik1/ComboPizzaSushiMCP.
- Сделано: persons/variations, health_check (10-й инструмент), автотесты с эталонами,
  веса pizza_kuba из названий размеров, справочник estimated_weights.json (~97 позиций:
  закуски «N шт», соусы, напитки 0,5/1 л — с полем source), адаптивный рейт-гейт ninja_food
  (полный парсинг ~72 с, все 290 позиций с весом), GUI удалён, CONTEXT.md-чекпоинт,
  ROADMAP с субагент-делегированием и проверкой контрибьютора.
- Инструменты: weight_source (site|size_name|reference|none) в best_combo/verify_chain/
  check_price/status; gen_expected.py сохраняет раздел dishes.
- Открыто: compare с persons; drinks.py под новые сети; TTL в config; проверка комбо-состава
  с reference-весами (оценки, не фактические данные сайта).

## Порядок старта сессии

1. `git fetch origin; git log HEAD..origin/main --oneline; git status --short`
   (проверка коммитов контрибьютора — см. ROADMAP.md «Проверка контрибьютора»)
2. `scripts/autotest.py` — убедиться, что база зелёная.
3. Дальше — по задачам пользователя.