# AGENTS.md — инструкция для агентов

Операционный справочник для работы с проектом. Продукт и планы — ROADMAP.md,
состояние на текущий момент — CONTEXT.md (читать в начале сессии, обновлять в конце).

## Что это

MCP-сервер (Python, stdio, mcp) «ComboPizzaSushiMCP»: комбо-подборщик по 7 сетям
доставки Воронежа (la_pizza, pizza_kuba, ninja_food, sushi_time, sushi_darom,
anti_sushi, dodo). 13 MCP-инструментов: list_chains, parse_menu, best_combo,
compare, status, verify_chain, check_price, diff_menu, check_config, health_check,
chain_info, help, favorites.

## Запуск и тесты

- Сервер: `.venv\Scripts\python.exe combo_mcp\server.py`
- Автотесты: `.venv\Scripts\python.exe scripts\autotest.py` (exit 0 = зелёная база).
  ОБЯЗАТЕЛЬНО прогнать после любых изменений кода.
- Smoke MCP-протокола: `.venv\Scripts\python.exe scripts\smoke_test.py`
- Selftest: `.venv\Scripts\python.exe scripts\selftest.py`
- Эталоны: `scripts\gen_expected.py` пересоздаёт tests/expected.json —
  обновлять только осознанным коммитом (сверка с real-данными).
- Очистка кэша: `scripts\clear_cache.py`

ВАЖНО про Windows PowerShell 5.1:
- Консоль портит UTF-8 (mojibake) — вывод кириллицы читать через файлы, не через консоль.
- `&&` не работает — цепочки через `; if ($?) { ... }`.
- Не менять каталог внутри команды — использовать параметр workdir.
- `rg` может отсутствовать — для поиска по содержимому использовать grep-инструмент.

## Структура

- `combo_mcp\server.py` — точка входа, регистрация 13 тулов
- `combo_mcp\tools\` — 1 файл = 1 MCP-инструмент; описание/примеры — tools/meta.py
- `combo_mcp\chains\` — 1 файл = 1 сеть, класс-парсер с декоратором `@chain("id")`;
  авто-регистрация через pkgutil (chains/__init__.py, пропуск `_*` и extra_utils)
- `combo_mcp\engines\` — dp.py (комбо-алгоритмы), drinks.py (детекция напитков),
  taste.py (ингредиенты)
- `combo_mcp\cache.py` — дисковый кэш cache/<chain>.json (fetched_at, items, prev_items);
  save_cache атомарный (tempfile+os.replace); clear_cache НЕ трогает favorites.json/extra_*;
  `extra_cache.py` — cache/extra_<chain>.json (доставка/акции/лояльность, дневной рефреш)
- `combo_mcp\params.py` — конвертация строковых параметров MCP (to_bool/to_int/to_float)
  + капы защиты от дурака: MAX_BUDGET=100000, MAX_VARIATIONS=50, MAX_LIMIT=500
- `combo_mcp\shared.py` — fetch_items (TTL + stale-if-error + причина ошибки),
  split_items_str/build_items_list (промо-поля base_price_rub/discount_rub)
- `combo_mcp\logs.py` — файловый логер logs/server.log (log_error)
- `combo_mcp\tools\meta.py` — единый реестр TOOLS_META (описания/примеры всех тулов);
  help генерируется из него, server.py регистрирует из него
- `combo_mcp\weights.py` — справочник весов config/estimated_weights.json
- `combo_mcp\promos.py` — промо-правила config/promos.json
- `combo_mcp\categories.py` — маппинг категорий → группы (pizza/rolls/sushi/
  sets/combo/...); combo — наборы/комбо (la_pizza, ninja_food, anti_sushi),
  sets — чистые ролл-сеты
- `config\` — chains_config.json (сети, таймауты, TTL), translations.json (додо)
- `scripts\` — рабочие скрипты (autotest, smoke_test, selftest, gen_expected,
  clear_cache, ci_smoke, new_chain); temp-файлы не держать

## Конвенции данных (не нарушать без согласования)

- Позиция: `{name, price_rub, weight_g, category, description, in_stock, ...}`
- `weight_source`: site | size_name (pizza_kuba) | reference (справочник) | none.
  Позиции без веса (>0) в комбо НЕ включаются (мерч, палочки — намеренно).
- Детекция напитков: drinks.py (категория + эвристика RU/EN). Ложные срабатывания
  (ГУАНТАНАМО, «тан», Мини Колада, «Фреш», Pepperoni Fresh) — регрессия запрещена.
- Локализация: в кэше имена ОРИГИНАЛЬНЫЕ; перевод только в выводе (names.py localize,
  dp.format_combo, best_combo ставит _local_name/_size_label); детекция по _orig_name.
- best_combo: ровно 1 напиток (TARGET_DRINKS=1) во всех вариациях (variations>=1);
  порядок вариаций: Оптимум → Без повторов → Макс. вес → доп. стратегии.
- Оптимум (dp.solve_optimum_with_drinks): напитки оптимизируются ВНУТРИ DP
  (ровно target напитков, вес еды — целевое измерение, вес напитков НЕ в счёте —
  иначе DP «набирает» тяжёлые напитки). Пул: топ-40 еды по вкусу + топ-15 по г/₽
  + ВСЕ напитки; кап 40 состояний на значение числа напитков. Если у сети НЕТ еды
  с вкусом >0 (например, dodo — описания пустые) — быстрый путь: дешёвые напитки
  + жадный максимум веса (эквивалент DP по целевой функции).
- Имена с запятой («Кола 0,33л г/л»): split_items_str НЕ режет запятую-десятичную
  (между цифрами) — разделитель только «запятая + пробел» (shared.py и autotest.py).
- Параметры MCP приходят СТРОКАМИ — любые числа/були конвертировать через
  combo_mcp/params.py, никогда не сравнивать строку с int напрямую.
- Промо: config/promos.json (fixed/percent/cashback, scope order/pickup/delivery,
  min_order, per_item, once, stackable); кешбэк не меняет цену. per-item fixed-скидки
  встраиваются в цены ДО расчёта комбо (best_combo: _base_price/_promo_discount,
  price_rub = max(price-disc, 1)), order/pickup-правила — постобработкой
  (apply_promos → promo_price/promo_saved).
- refresh list_chains/health_check — параллельно (ThreadPoolExecutor, 4 воркера);
  сети независимы (свои сессии requests, свои кэш-файлы).
- Категории: категории группы drinks — напитки добавляются только если группа
  drinks в списке categories.

## Тесты

- Автотест — блоки 1..28 (эталоны комбо, инварианты, напитки, категории, help,
  favorites, идемпотентность, Monte Carlo, реальный MCP-протокол). Все зелёные = OK.
- Блок 28 вызывает тулы через ClientSession/stdio — параметры строками.
- Эталоны tests/expected.json пересоздавать через scripts/gen_expected.py
  (НЕ вручную), только при осознанном изменении алгоритма/данных.

## Todo-дисциплина (обязательно)

- Задача из 3+ шагов — сразу завести todo-список (todowrite) и держать его
  актуальным ВЕСЬ процесс: перед началом шага — in_progress (ровно один),
  после фактического завершения — completed сразу, не «в конце».
- Проверки (autotest/smoke/compile) отмечать completed только после реального
  зелёного прогона (exit 0), а не по факту написания кода.
- Перед итоговым ответом пользователю — свериться с todo: не должно остаться
  незакрытых пунктов без объяснения (блокер → пункт остаётся in_progress +
  комментарий). Забытый незакрытый пункт = задача не доделана.

## Известные ложные LSP-варнинги (не чинить)

mcp.server.mcpserver import, reconfigure, `.get` на None в autotest.py,
BS4 AttributeValue, pytesseract/playwright import.

## Git

- Ветка main, remote github.com/1artik1/ComboPizzaSushiMCP.
- Коммитить ТОЛЬКО по явному запросу пользователя. Стиль: короткое русское
  описание сути («фикс refresh-параметров в MCP-тулах»).
- Старт сессии: `git fetch origin; git log HEAD..origin/main --oneline; git status --short`.
  При наличии чужих коммитов — ВСЕГДА спросить пользователя (не вливать/откатывать).

## Добавление сети/инструмента

- Сеть: `python scripts\new_chain.py <id> "Название" <url>` → класс-парсер
  (parse(), category_map, опционально parse_extra()) + запись в chains_config.json.
- Инструмент: файл в combo_mcp\tools\ + запись в tools/meta.py;
  server.py регистрирует тул из реестра.

## Делегирование субагентам

- explore — разведка кода/данных (не пишет код)
- qwen3coder_code — реализация по готовому ТЗ (правки, рефакторинг, анализ логов)
- qwen3coder_research — исследование кода + веб, возвращает выжимку с источниками

НЕ делегировать: обновление эталонов expected.json, решения о данных/бизнес-логике
(что напиток, какой вес честный), публикация (коммит/пуш).

## Обновление документации

- CONTEXT.md — чекпоинт состояния, обновлять В КОНЦЕ каждой сессии.
- ROADMAP.md — сделано/в плане/на будущее; отмечать выполненные пункты.
- README.md — пользовательская справка (запуск, инструменты, данные).