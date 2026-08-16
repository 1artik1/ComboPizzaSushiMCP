# Combo Engine MCP Server

Расчёт выгодных комбо по сетям доставки Воронежа. MCP-сервер + GUI-приложение + библиотека парсеров.
Всё изолировано в venv: зависимости и браузер Playwright лежат внутри `.venv\` (система не затрагивается).

## Структура
```

├── combo_mcp\          # пакет MCP-сервера
│   ├── server.py       # точка входа (stdio)
│   ├── config.py       # конфиг сетей (config\chains_config.json)
│   ├── cache.py        # дисковый кэш + stale-if-error
│   ├── http_client.py  # requests-обёртка (UA, ретраи, куки)
│   ├── playwright_client.py  # ленивый браузер
│   ├── engines\        # dp.py (комбо), taste.py (вкусность)
│   ├── chains\         # 1 файл = 1 сеть (@chain("id"))
│   └── tools\          # 1 файл = 1 инструмент MCP
├── gui\la_pizza_app.py # GUI-приложение Ла Пицца
├── scripts\selftest.py # регресс-проверка всех сетей
├── config\chains_config.json
├── cache\              # создаётся автоматически
└── archive\            # старые файлы + референсы разведки (recon\)
```

## Запуск
```powershell
# MCP-сервер (регистрируется opencode через opencode.json)
.\.venv\Scripts\python.exe combo_mcp\server.py

# Selftest: все сети + эталоны Ла Пиццы (3000₽ → 5100/2800, 4400/2950, 4850/3000)
.\.venv\Scripts\python.exe scripts\selftest.py

# GUI-приложение Ла Пицца
.\.venv\Scripts\python.exe gui\la_pizza_app.py

# Очистка кэша
.\.venv\Scripts\python.exe scripts\clear_cache.py
```

## Инструменты MCP (9)
- `list_chains()` — сети и их доступность
- `parse_menu(chain_id, category=, min_weight=, sort_by=, limit=, refresh=)` — меню
- `best_combo(chain_id, budget, refresh=)` — 3 варианта комбо (макс.вес / оптимум / без повторов)
- `compare(budget)` — все сети по выгодности (₽/100г)
- `status()` — конфиг, возраст кэша, ошибки
- `verify_chain(chain_id)` — качество данных (веса, дубликаты, аномалии)
- `check_price(chain_id, item_name, expected_price=)` — сверка цены позиции
- `diff_menu(chain_id)` — изменения меню с прошлой загрузки
- `check_config()` — валидация конфига и доступность ссылок

## Конфиг сетей
`config\chains_config.json` — per-chain: `url`, `enabled`, `ttl_minutes`, `headers`, `cookies`.
Смена URL/куки не требует правки кода.

## Добавление новой сети
1. Скопировать `combo_mcp\chains\_template.py` → `combo_mcp\chains\my_chain.py`
2. Реализовать класс с методом `parse()` (возвращает список позиций:
   `{name, weight_g, price_rub, is_from_price, description, category, product_url, in_stock, extra}`)
3. Указать `url` в `chains_config.json` — сервер подхватит автоматически при старте.

## Добавление нового инструмента
Положить файл с функцией-хендлером в `combo_mcp\tools\` и зарегистрировать декоратором
(см. существующие инструменты) — `server.py` не трогается.

## Правила данных
- Вес — только реальный из сайта (иначе `weight_g: None`, позиция исключается из расчёта комбо).
- Недоступные сети честно помечаются в `list_chains`/`compare` с причиной.