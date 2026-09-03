# Combo Engine MCP Server

Расчёт выгодных комбо по сетям доставки Воронежа. Это MCP-сервер + библиотека
парсеров: подбирает набор еды под бюджет, сравнивает сети по выгодности,
следит за ценами и меню.

Все зависимости и браузер Playwright изолированы внутри `.venv\` — системное
окружение не затрагивается.

Смысл и сценарии каждой команды — в [COMMANDS.md](COMMANDS.md).

## Сети

7 служб доставки Воронежа: **Ла Пицца**, **Пицца Куба**, **Ниндзя Фуд**,
**Сушитайм**, **Суши Даром**, **Антисуши**, **Додо Пицца**.

## Как это работает

- Сервер получает меню сетей (парсинг сайтов/API, с кэшированием и защитой
  от сбоев — «stale-if-error»).
- По запросу строит **комбо** под бюджет: по умолчанию 3 варианта —
  Оптимум (вес + вкус, 1 напиток) → Без повторов → Макс. вес.
- Поддерживает категории, промо-скидки, сравнение сетей, мониторинг цен и меню.

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
├── COMMANDS.md         # для чего нужна каждая команда (смысл и сценарии)
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

# Smoke-тест реального MCP-протокола (10 инструментов)
.\.venv\Scripts\python.exe scripts\smoke_test.py

# Очистка кэша
.\.venv\Scripts\python.exe scripts\clear_cache.py
```

## Инструменты MCP (13)

### Подбор и сравнение

- **`best_combo(chain_id, budget, variations=3, refresh=, categories=, promos=, sort_by=)`**
  варианты комбо под бюджет.
  - по умолчанию 3 вариации в порядке: **Оптимум** (максимум веса еды в бюджете
    + вкус, напиток оптимизируется внутри подбора) → **Без повторов** (макс. вес,
    каждый продукт по 1 шт) → **Макс. вес** (чистый максимум веса);
    при `variations>3` — ещё доп. стратегии
  - 1 напиток в каждой вариации (если есть напитки с весом, влезающие в бюджет)
  - `chain_id` — одна сеть (обычный режим), пустая строка («все сети») или список
    через запятую («dodo, ninja_food») — сквозной топ-N: кандидаты сетей
    сортируются метрикой и отбирается топ `variations` (`mode=all/multi`)
  - `sort_by=` — `price_per_100g` (по умолчанию), `weight`, `price`
    (только в cross-chain режиме)
  - `categories=` — фильтр по категориям: `pizza/rolls/sushi/sets/combo/noodles/
    snacks/desserts/drinks/sauces/other` + русские слова («пицца», «напитки»…).
    `combo` — наборы/комбо-предложения, `sets` — чистые ролл-сеты; напитки — только
    если группа `drinks` в списке
  - `promos=` — применить промо-скидки: `order` / `pickup` / `all`
  - `refresh=true` — реальный прогон парсера, иначе ответ по кэшу

- **`compare(budget, categories=)`** — лучшее комбо каждой сети на бюджет,
  отсортировано по выгодности (₽/100г).

### Меню и контент

- **`parse_menu(chain_id, category=, min_weight=, sort_by=, limit=, refresh=)`**
  меню сети с фильтрами и сортировкой (limit не более 500).

### Контроль цен и меню

- **`check_price(chain_id, item_name, expected_price=)`** — свежая проверка цены
  позиции (реальный парсинг).
- **`diff_menu(chain_id)`** — изменения меню с прошлой загрузки.
- **`chain_info(chain_id, refresh=)`** — доставка, акции, лояльность сети.

### Состояние и качество данных

- **`list_chains(refresh=)`** — сети: id, название, город, `available`, описание.
- **`status()`** — конфиг, возраст кэша, ошибки.
- **`verify_chain(chain_id)`** — качество данных сети: веса, дубликаты, аномалии.
- **`check_config()`** — валидация `chains_config.json`.
- **`health_check(refresh=False)`** — HTTP + парсинг + кол-во позиций по всем сетям
  (по кэшу или live).

### Служебные

- **`help(action=, command=)`** — справочник команд: список с пагинацией
  (`/help next`, `/help back`), детали одной команды (`/help best_combo`).
- **`favorites(action=, chain_id=, label=, items=, query=)`** — избранное:
  сохранить (`add`), показать (`list`), удалить (`remove`), очистить (`clear`).
  Хранение: `cache/favorites.json`.

### Параметры и защита от дурака

Числовые параметры передаются **строками** и валидируются. Капы: `budget` ≤ 100000,
`variations` ≤ 50, `limit` ≤ 500 — иначе явная ошибка `{"error": ...}`.
Нераспознанные `categories`/`sort_by`/`chain_id` — ошибка с перечнем доступных
значений, а не молча пустой ответ. Мусор в числовых параметрах (`abc`, `0`,
отрицательные) не роняет сервер — возвращается корректная ошибка.

## Автотесты

`tests\expected.json` — фиксированные эталоны (комбо по сетям/бюджетам,
контрольные блюда). Без record-режима: `scripts\autotest.py` сверяет фактический
результат с эталоном, расхождение → FAIL + дифф. Эталон обновляется только
осознанным коммитом.

## CI (GitHub Actions)

- `.github\workflows\ci.yml` — на каждый push: компиляция + быстрый smoke без сети
  (сервер стартует, 13 инструментов зарегистрированы, JSON-ответы).
  Запуск вручную: `scripts\ci_smoke.py`.
- `.github\workflows\nightly.yml` — ежедневно в 06:00 UTC: живой парсинг всех сетей
  (`health_check refresh=true`) + полный автотест (16 блоков). Это мониторинг
  парсеров: упавшая сеть или регрессия → красный статус + артефакт с отчётом
  (`cache/`).

## Конфиг сетей

`config\chains_config.json` — per-chain: `url`, `enabled`, `ttl_minutes`, `headers`,
`cookies`. Смена URL/куки не требует правки кода.

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

Положить файл с функцией-хендлером в `combo_mcp\tools\` и зарегистрировать
декоратором (см. существующие инструменты) — `server.py` не трогается.

## Правила данных

- Вес позиции: с сайта/API (`weight_source` `site`), из названия размера
  (`size_name`, pizza_kuba), из справочника `config\estimated_weights.json`
  (`reference`, поле `source` — откуда взят вес) или отсутствует (`none`).
- Позиции без веса исключаются из расчёта комбо (мерч, палочки — намеренно).
- Недоступные сети честно помечаются в `list_chains`/`compare` с причиной.
