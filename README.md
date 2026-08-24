# Combo Engine MCP Server

Расчёт выгодных комбо по сетям доставки Воронежа (7 сетей) + продуктовые
магазины Магнит и Пятёрочка (поиск товаров и категории). MCP-сервер + библиотека парсеров.
Всё изолировано в venv: зависимости и браузер Playwright лежат внутри `.venv\` (система не затрагивается).

## Структура
```

├── combo_mcp\          # пакет MCP-сервера
│   ├── server.py       # точка входа (stdio)
│   ├── config.py       # конфиг сетей (config\chains_config.json)
│   ├── cache.py        # дисковый кэш + stale-if-error
│   ├── http_client.py  # requests-обёртка (UA, ретраи, куки)
│   ├── playwright_client.py  # ленивый браузер (фолбэк dodo)
│   ├── weights.py      # справочник расчётных весов (config\estimated_weights.json)
│   ├── engines\        # dp.py (комбо), taste.py (вкусность), drinks.py (напитки)
│   ├── chains\         # 1 файл = 1 сеть (@chain("id"))
│   └── tools\          # 1 файл = 1 инструмент MCP
├── scripts\            # selftest.py, autotest.py, smoke_test.py, gen_expected.py
├── tests\expected.json # эталоны для autotest
├── config\chains_config.json
├── config\estimated_weights.json  # веса позиций без веса на сайте (с источником)
├── cache\              # создаётся автоматически
└── archive\            # старые файлы + референсы разведки (recon\)
```

## Запуск
```powershell
# MCP-сервер (регистрируется opencode через opencode.json)
.\.venv\Scripts\python.exe combo_mcp\server.py

# Selftest: все сети + эталоны Ла Пиццы (3000₽ → 4400/2950, 4850/3000, 5100/2800)
.\.venv\Scripts\python.exe scripts\selftest.py

# Автотесты: эталоны комбо + инварианты + контрольные блюда + health_check
.\.venv\Scripts\python.exe scripts\autotest.py

# Smoke-тест реального MCP-протокола (15 инструментов)
.\.venv\Scripts\python.exe scripts\smoke_test.py

# Очистка кэша
.\.venv\Scripts\python.exe scripts\clear_cache.py
```

## CI (GitHub Actions)
- `.github\workflows\ci.yml` — на каждый push: компиляция + быстрый smoke без сети
  (сервер стартует, 15 инструментов зарегистрированы, JSON-ответы).
  Запуск вручную: `scripts\ci_smoke.py`.
- `.github\workflows\nightly.yml` — ежедневно в 06:00 UTC: живой парсинг всех сетей
  (`health_check refresh=true`) + полный автотест (16 блоков). Это мониторинг парсеров:
  упавшая сеть или регрессия → красный статус + артефакт с отчётом (cache/).

## Инструменты MCP (15)
- `list_chains(refresh=)` — сети: id, название, город, available (есть данные в кэше), описание
- `parse_menu(chain_id, category=, min_weight=, sort_by=, limit=, refresh=)` — меню
- `best_combo(chain_id, budget, persons=1, variations=3, refresh=, categories=, promos=)` — варианты комбо:

  - ровно `persons` напитков в каждой вариации (по 1 на персону)
  - `categories=` — фильтр по категориям: «пицца», «pizza», «напитки», «роллы»...
    (группы: pizza/rolls/sushi/sets/noodles/snacks/desserts/drinks/sauces/other;
    напитки добавляются, только если группа drinks в списке)
  - `promos=` — применить промо-скидки к цене: `order` (скидки на заказ),
    `pickup` (скидки при самовывозе), `all`. Правила — `config\promos.json`
    (рукописные, из акций chain_info); в ответе у каждой вариации `promo_price`/
    `promo_saved` и список применённых акций в `promos_applied` (кешбэк не меняет цену)
- `compare(budget, persons=1, categories=)` — все сети по выгодности (₽/100г)
- `status()` — конфиг, возраст кэша, ошибки
- `verify_chain(chain_id)` — качество данных (веса, дубликаты, аномалии)
- `check_price(chain_id, item_name, expected_price=)` — сверка цены позиции
- `diff_menu(chain_id)` — изменения меню с прошлой загрузки
- `check_config()` — валидация конфига и доступность ссылок
- `health_check(refresh=False)` — HTTP + парсинг + кол-во позиций по всем сетям
- `chain_info(chain_id, refresh=)` — доставка, акции, лояльность сети
- `help(action=, command=)` — команда /help: список всех команд с описаниями,
  пагинация 10 на страницу (`/help next`, `/help back`), детали одной команды
  (`/help best_combo`)
- `favorites(action=, chain_id=, label=, items=, query=)` — избранное: сохранить
  понравившееся комбо (`action="add"`, items — JSON-массив позиций), показать
  список (`action="list"`, пагинация через `query="next"/"back"`), удалить
  (`action="remove"`, `query` — id или подстрока), очистить (`action="clear"`).
  Хранение: `cache/favorites.json`.
  (refresh=true — реальный прогон, иначе быстрый ответ по кэшу)
- `search_products(chain_id, query, limit=, refresh=)` — поиск товаров по названию
  в любой сети: для magnit/pyaterochka — серверный поиск API, для остальных —
  регистронезависимый поиск по меню (кэш). Результаты по цене (price_rub asc)
- `list_categories(chain_id, refresh=)` — все категории товаров сети:
  серверное дерево категорий (magnit/pyaterochka) или агрегат по меню
  ({category, count}, сортировка по числу позиций)

## Продуктовые магазины (ShopExtended)
- **magnit** — включён. Прямой webgate-API magnit.ru (requests, без браузера):
  категории `/webgate/v3/categories/store/992301`, товары/поиск `POST /webgate/v2/goods/search`
  (цены в копейках → конвертируются, вес из weighted/имени).
- **pyaterochka** — выключен (`enabled: false`). API `5d.5ka.ru` закрыт анти-ботом
  (капча при заходе не из браузера); парсер написан на Playwright (запросы из контекста
  страницы 5ka.ru), но headless-браузер стабильно получает капчу → при включении
  будет отдавать stale-кэш или ошибку «анти-бот капча».
- Для обоих магазинов работают `search_products` и `list_categories` (серверный
  путь), а также стандартные `status`/`health_check`/`check_config`. magnit
  участвует в общих тулах (parse_menu/best_combo/compare) наравне с сетями
  доставки; pyaterochka исключён из них (`enabled: false`) до обхода анти-бота.

## Автотесты
`tests\expected.json` — фиксированные эталоны (комбо по сетям/бюджетам, контрольные блюда).
Без record-режима: `scripts\autotest.py` сверяет фактический результат с эталоном,
расхождение → FAIL + дифф. Эталон обновляется только осознанным коммитом.

## Конфиг сетей
`config\chains_config.json` — per-chain: `url`, `enabled`, `ttl_minutes`, `headers`, `cookies`.
Смена URL/куки не требует правки кода.

## Добавление новой сети
1. Скопировать `combo_mcp\chains\_template.py` → `combo_mcp\chains\my_chain.py`
   (или проще: `python scripts\new_chain.py my_chain "Моя Сеть" https://example.com`)
2. Реализовать метод `parse()` (возвращает список позиций:
   `{name, weight_g, price_rub, is_from_price, description, category, product_url, in_stock, extra}`)
3. Заполнить `category_map` — маппинг категорий меню → группы комбо
   (pizza/rolls/sushi/sets/noodles/snacks/desserts/drinks/sauces/other)
4. Указать `url` в `chains_config.json` (генератор делает это сам)

Больше ничего: парсеры регистрируются автоматически (pkgutil), метаданные сети
(id/name/city/url/description) берутся из класса парсера, категории — из его
`category_map`. По желанию: `parse_extra()` (доставка/акции), веса в
`config\estimated_weights.json`, переводы в `config\translations.json`.

## Добавление нового инструмента
Положить файл с функцией-хендлером в `combo_mcp\tools\` и зарегистрировать декоратором
(см. существующие инструменты) — `server.py` не трогается.

## Правила данных
- Вес позиции: с сайта/API (weight_source `site`), из названия размера (`size_name`,
  pizza_kuba), из справочника `config\estimated_weights.json` (`reference`, поле `source` —
  откуда взят вес) или отсутствует (`none`).
- Позиции без веса исключаются из расчёта комбо (мерч, палочки — намеренно).
- Недоступные сети честно помечаются в `list_chains`/`compare` с причиной.