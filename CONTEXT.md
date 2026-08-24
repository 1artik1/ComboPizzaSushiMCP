# CONTEXT.md — чекпоинт состояния проекта

Обновлять в конце каждой сессии. Новая сессия начинается с чтения этого файла + ROADMAP.md.

## Что это

MCP-сервер (Python, stdio, mcp) «ComboPizzaSushiMCP»: комбо-подборщик по 9 сетям
доставки Воронежа (la_pizza, pizza_kuba, ninja_food, sushi_time, sushi_darom,
anti_sushi, dodo, magnit, pyaterochka). 15 MCP-инструментов: list_chains, parse_menu, best_combo,
compare, status, verify_chain, check_price, diff_menu, check_config, health_check,
chain_info, help, favorites, search_products, list_categories.

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
- Доп. информация (chain_info, 11-й инструмент): доставка/акции/лояльность.
  Парсеры: base.parse_extra() (дефолт {}), extra_utils.py (fetch_text/clean_text/
  find_promos/ocr_image/render_text), 7 парсеров реализуют parse_extra()
  (sushi_darom — Next data API `_next/data/{buildId}/index.json?tenant=sushidarom&subdomain=voronezh`,
  pageProps.banners/promotions на ТОП-уровне; dodo — Playwright /voronezh + /bonusactions).
  Срез `cache/extra_<cid>.json` {fetched_at, extra, last_error, stale}; обновление
  раз в день в момент `extra_refresh_at` (корневой ключ chains_config.json, по
  умолчанию "11:00", валидация в check_config); ленивый механизм: до HH:MM отдаём
  срез без сети, первый вызов после HH:MM — перепарсинг; ошибка → stale-if-error.
  Формат: delivery{min_order_rub,cost_rub,free_from_rub,time_minutes,conditions,source},
  loyalty{program,details,source}, promotions[{title,conditions,valid_until,source}].
  OCR (Tesseract) установлен, но почти не нужен — акции всех сетей текстовые.
- LSP-варнинги в проекте — ложные (mcp.server.mcpserver import, reconfigure,
  .get на None в autotest.py, BS4 AttributeValue, pytesseract/playwright import) — не чинить.
- Кэш ninja хранит имена с литеральными `\"` — нормализация `_norm_name` в autotest.py.

- Категории комбо (12-я фича): combo_mcp/categories.py — группы pizza/rolls/sushi/sets/
  noodles/snacks/desserts/drinks/sauces/other; маппинг сырых категорий каждой сети →
  группа (dodo — десерты/напитки по имени); categories в best_combo/compare (русские
  слова + группы: «пицца», «pizza», «напитки», «соки»...); напитки добавляются ТОЛЬКО
  если группа drinks в списке (иначе persons не влияет); ошибка с перечнем доступных
  групп, если выбранной нет в меню. anti_sushi: +подкаталоги (пицца/фьюжен/соусы/
  комбо/спецпредложения), дедупликация по имени, 87 позиций (было 52); напитков на
  сайте нет (/catalog/drinks/ → 404). sushi_darom/la_pizza напитков нет на сайтах.
  dodo: напитки 40, десерты 12, пицца 108. Автотест блок 8.
- Команда /help (12-й инструмент): help.py — справочник 13 команд (name/args/description/
  example), пагинация 10 на страницу через action="next"/"back" (память _help_page,
  пустой action сбрасывает на стр. 1),
  детали команды через command="best_combo"; ответ {page, total_pages, commands, hint}.
  Блок 9.
- list_chains: available=True, если в кэше сети есть позиции; при refresh=true — по
результату live-парсинга (был баг: без refresh всегда False).
- Избранное (13-й инструмент): favorites.py — action="add" (chain_id + items JSON-массив
[{name,count,price_rub,weight_g}], снимок с итогами, label автогенерация, id
int(time*1000)+счётчик) / "list" (пагинация 10/стр, query="next"/"back"/номер страницы,
память _fav_page) / "remove" (query: id или подстрока label/имени) / "clear".
Хранение: cache/favorites.json (атомарно: tempfile + os.replace). Блок 10.
- Поиск продуктов (14-й инструмент, прокачан в сессию 2026-08-24): search_products.py —
  универсальный поиск для нейросети: query первым, по умолчанию ВСЕ enabled-сети
  одним вызовом (stores="all" / csv / старый chain_id=). Матчинг — engines/textmatch.py
  (нормализация ё→е/регистр/пунктуация, токены, Левенштейн ≤1 для токенов ≥5 симв.,
  бонус категории +0.3; фраза 3.0 > все токены 1.5 > доля×0.5). Фильтры: categories=
  (группы через resolve_categories, fallback — подстрока сырой категории), min/max_price,
  in_stock; sort: relevance|price_asc|price_desc; limit. Данные — всегда fetch_items
  (TTL-кэш, stale-if-error); серверная ветка из тула убрана (методы search()/get_categories()
  в парсерах остались для list_categories). magnit menu_ttl_minutes=10080 (неделя).
  Ответ: {query, stores_searched, total, results[{chain_id, chain_name, name, price_rub,
  weight_g, category, group, in_stock, score}], chains_errors{}, stale} — ошибка одной
  сети не роняет ответ. Блоки 28/29 обновлены (юнит textmatch, мультистор, фильтры,
  ошибки, обратная совместимость chain_id).
- Категории (15-й инструмент): list_categories.py — серверные категории для
magnit/pyaterochka (иерархия с children), fallback — из кэша меню (группировка
по category, count desc). Результат: {source, total, categories[]}.
Блок 9 (pag 2), блок 29.
- Модуль расширения сетей: метаданные сети (id/name/city/url/description) и маппинг
  категорий category_map — в классе парсера (ChainParser.category_map = {}); категории
  из класса (categories.py через get_chain_class, fallback-эвристики ролл/суши для
  sushi_darom/anti_sushi, dodo — по имени); авто-регистрация парсеров в chains/__init__.py
  (pkgutil.iter_modules, пропуск _* и extra_utils, ошибки логируются); get_chain_meta()
  собирается из реестра (жёсткий список в config.py удалён); scripts/new_chain.py
  генерирует парсер + запись в chains_config.json + чек-лист; _template.py обновлён.
  Блок 11.

## Состояние на 2026-08-24

- git: ветка main, remote github.com/1artik1/ComboPizzaSushiMCP.
- Опубликовано: fd87d5f «разнообразные вариации», 063fa5a chain_info (11-й),
  1f7f326 todo/акции/weights, 9588787 категорийный фильтр, bd1c6fd help+favorites+
  модуль расширения сетей (13 инструментов, автотест 11/11 OK).
- ВАЖНО: проект ПЕРЕЕХАЛ на E:\GlobalProjects\TestOpen (2026-08-17, вместе с
  .venv и .git). Рабочий стол освобождён (TestOpen/PythonVGTY/Projects → E:\GlobalProjects).
  Запускать и opencode, и все скрипты теперь из нового пути. PLAYWRIGHT_BROWSERS_PATH
  в opencode.json обновлён. Если видите старые пути C:\Users\1artik1\Desktop\TestOpen —
  они из temp-скриптов прошлых сессий, не использовать.
- Опубликовано fd87d5f «разнообразные вариации (variations>3)» (seed в ответе,
  dp.py: int(time.time()*1000)); notify.js: звук на question.v2.asked (нужен рестарт opencode).
- Сделано: блок «доп. информация» — extra_utils.py, parse_extra() в 7 парсерах
  (la_pizza/pizza_kuba/ninja_food/sushi_time/anti_sushi — HTML, sushi_darom — Next
  data API (buildId из HTML, pageProps на топ-уровне!), dodo — Playwright fetch_text
  в playwright_client.py), extra_cache.py (ленивый дневной рефреш по extra_refresh_at,
  stale-if-error), tools/chain_info.py (11-й инструмент, зарегистрирован в server.py),
  check_config валидирует extra_refresh_at "HH:MM", autotest блок 7. Автотест: 7/7
  блоков зелёные. Срезы в cache/extra_*.json.
- Данные на 2026-08-17: la_pizza — мин 650₽, 09:00–23:00, акция самовывоза −100₽;
  pizza_kuba — бесплатно в зоне, 4 акции; ninja_food — зоны от 849₽, «Путь Ниндзя»,
  8 промокодов; sushi_time — 5 зон, «Таймы» 3%, 4 акции; sushi_darom — 10:00–22:00,
  ~90 мин, платная зона 99₽ (600–999₽), 16 акций с датами; anti_sushi — 10:00–24:00,
  бонусные рубли 3/5/10%, 15 акций; dodo — 36 мин/4.88, 7 акций + кешбэк 5%.
- Сделано (после chain_info): категорийный фильтр (categories.py, best_combo/compare
  + параметр categories, блок 8 автотеста), TTL меню в конфиге (http_timeout/
  menu_ttl_minutes + load_items_with_ttl), find_promos (читаемые заголовки акций),
  drinks.py (тоник/газировка/байкал/фраппе), pizza_kuba веса из описаний (site).
  anti_sushi: 87 позиций (+пицца и подкаталоги). Автотест: 8/8 блоков зелёные.
- Сделано (третий раунд): /help (12-й инструмент, пагинация next/back, детали команды),
  избранное favorites (13-й инструмент, cache/favorites.json), модуль расширения сетей
  (category_map в классах, авто-регистрация pkgutil, get_chain_meta из реестра,
  scripts/new_chain.py генератор). Автотест: 11/11 блоков зелёные.
- Сделано (блок 12 — cache): инварианты кэша per-chain (name не пустая, price>0,
  weight>=0, category не пустая, in_stock bool); дедуп по (norm_name, price, weight,
  category) — дубликаты из парсера с одинаковым ключом пропускаются (continue).
- Сделано (блок 13 — drinks): золотые списки (16 поз-напиток + 15 не-напиток) +
  реальная проверка категории cache (drinks.py: is_drink + _DRINK_CATEGORIES).
- Сделано (блок 17 — idem): best_combo idempotency для pizza_kuba и dodo (2 вызова
  → одинаковые вариации).
- Сделано (блок 18 — mcart): Monte Carlo random.seed(42), бюджеты 500-5050,
  persons 1-3 (la_pizza + dodo); подсчёт напитков через _expected_drinks (не хардкод),
  убран price_per_100g (алгоритмический порядок вариаций меняется).
- Сделано (блок 28 — mcp): реальный MCP-протокол через asyncio.run() + ClientSession
  + stdio_client; проверка 13 инструментов + 5 quick-tools; добавлен import asyncio.
- Открыто: OCR (Tesseract) установлен, но используется мало; проверка качества
  акций anti_sushi (заголовки с мусором из меню); sushi_darom/la_pizza/anti_sushi —
  напитков на сайтах нет (фильтр drinks вернёт ошибку с доступными группами).
- Сессия 2026-08-17 (не закоммичено): фикс help.py — пустой action сбрасывает
  _help_page на 1 (был баг: «заново» показывал последнюю страницу); фикс
  list_chains.py — available=True по кэшу (был баг: без refresh всегда False),
  описания обновлены в help.py/server.py/README. Автотест 11/11 OK.
- Сделано (сессия 2026-08-17, не закоммичено): 5 новых блоков автотеста (12-cache,
  13-drinks, 17-idem, 18-mcart, 28-mcp), итого 16 блоков; все OK, exit 0.
  Блок 12: дубликаты из парсера dodo (Nectar Dobry Multifruit) с одинаковым ключом
  (имя, цена, вес, категория) пропускаются (continue).
- Сделано (сессия 2026-08-17, этап 1 «фундамент», не закоммичено): CI —
  .github/workflows/ci.yml (push: compileall + ci_smoke без сети) и nightly.yml
  (06:00 UTC: health_check refresh=true + autotest + артефакт cache/) — это и
  мониторинг парсеров; scripts/ вычищен от 62 temp-файлов (остались 6 рабочих);
  ROADMAP: +пункт «тест Оптимум = макс. вес» и секция «На будущее» (Telegram-бот,
  история цен/тренды — признаны переизбытком, diff_menu закрывает диффы).
- Сделано (сессия 2026-08-17, этап 2 «промо в комбо», не закоммичено):
  config/promos.json — рукописные правила акций из chain_info для 7 сетей
  (la_pizza −100 самовывоз; pizza_kuba −100/пицца самовывоз, 7% доставка от 5000;
  ninja_food SALE −15% самовывоз, SAM67 −20%, NEWMP 20% от 1299 once;
  sushi_time −250 от 1100 once; dodo 20% первый заказ once + кешбэк 5%;
  anti_sushi РОЛЛ25 −25% пн-чт; sushi_darom — пусто). combo_mcp/promos.py
  (apply_promos: scope/mode, min_order, days, items/per_item, stackable —
  лучшая несуммируемая + все суммируемые, cashback не меняет цену).
  best_combo +параметр promos=order|pickup|all (promo_price/promo_saved в каждой
  вариации, promos_applied в ответе). Автотест блок 19 (11 проверок), итого
  17 блоков OK. Эталоны ninja_food пересозданы (gen_expected.py): сайт обновил
  меню — «Курочка темпура хот» получила вес 315 г вместо справочного «8 шт,
  45 г/шт», «Мисо суп с курицей» заменил «Краб темпура» (1475 вместо 1495);
  остальные 6 сетей идентичны эталонам.
- Сделано (сессия 2026-08-17, этапы 1–3 «баги→надёжность→алгоритмы» + AGENTS.md,
  НЕ закоммичено). AGENTS.md создан (операционка: запуск, структура, конвенции,
  ложные LSP, git, делегирование). Этап 1 «баги/фундамент»: params.py
  (to_bool/to_int/to_float — все параметры MCP строками), shared.py
  (fetch_items: TTL + stale-if-error + причина ошибки; split_items_str/
  build_items_list), save_cache атомарный (tempfile+os.replace), clear_cache
  НЕ трогает favorites.json/extra_*, verify_chain дедуп, weights.py кэш по mtime,
  удалён мёртвый engines/scoring.py, убран глобальный socket.setdefaulttimeout,
  autotest блок 28 расширен строковыми параметрами через MCP. Этап 2
  «реестр/логирование»: tools/meta.py (единый TOOLS_META — help генерирует из
  него, server.py регистрирует из него, version 1.1.0), logs.py (logs/server.log,
  log_error в shared.fetch_items и extra_cache). Этап 3 «алгоритмы»:
  promos.py per_item_discounts — fixed-скидки встраиваются в цены ДО расчёта
  (best_combo: _base_price/_promo_discount, price_rub=max(price-disc,1)),
  order/pickup — постобработкой; dp.solve_optimum_with_drinks — совместная
  оптимизация напитков в DP (измерение числа напитков, вес еды — целевое,
  вес напитков НЕ в счёте — иначе DP набирает тяжёлые латте; пул топ-40 еды
  по вкусу + топ-15 по г/₽ + ВСЕ напитки; кап 40 состояний на значение числа
  напитков; батч-парето вместо per-state pfilt — был квадрат; быстрый путь для
  меню без вкуса (dodo): дешёвые напитки + жадный максимум веса — 78с → 0.35с);
  _limit_pool в solve_optimum (топ-40 по вкусу + топ-15 по г/₽); split_items_str
  НЕ режет запятую-десятичную («Кола 0,33л г/л» — был баг: позиции с price=None
  в items_list); refresh list_chains/health_check — параллельно (ThreadPoolExecutor,
  4 воркера, 7 сетей за 67.6с). Эталоны пересозданы (gen_expected.py): изменились
  только ninja_food и pizza_kuba (совместная оптимизация напитков — больше
  утилизация бюджета, ровно persons напитков), dodo/la_pizza/anti_sushi/
  sushi_time/sushi_darom идентичны. Автотест 17 блоков + smoke: exit 0, зелёные.
- Сделано (сессия 2026-08-24): Magnit + Pyaterochka интегрированы.
  combo_mcp/chains/magnit.py — прямой API (прайсы в копейках, вес в граммах,
  категории, поиск, пагинация, парсинг веса).
  combo_mcp/chains/pyaterochka.py — Playwright-парсер (прайсы в рублях),
  исправлен `with pw as p:` для Playwright 1.62.0 (binding Playwright object).
  combo_mcp/playwright_client.py — get_playwright() возвращает sync_playwright().
  config/chains_config.json: magnit enabled, pyaterochka disabled (X5 Group 403).
  combo_mcp/chains/base.py — добавлены search()/get_categories() абстрактные методы.
  combo_mcp/tools/compare.py — get_enabled_chain_ids() вместо get_chain_meta()
  (исключает disabled chains из сравнения).
  combo_mcp/tools/health_check.py — get_enabled_chain_ids() вместо get_chain_meta().
  scripts/autotest.py — get_enabled_chain_ids() для блоков 1-13 (кроме блока 11
  registry check), динамический подсчёт цепей, skip для цепей без expected.json.
  tests/expected.json — обновлён через gen_expected.py (live data drift:
  dodo, ninja_food, sushi_darom). Autotest: 155/155 OK, exit 0.
  Pyaterochka: API X5 Group стабильно 403 (anti-bot/Cloudflare), disabled.

- Сделано (сессия 2026-08-24, расширение shop-сетей):
  combo_mcp/chains/base.py — добавлен атрибут has_server_search=False.
  combo_mcp/chains/magnit.py и pyaterochka.py — has_server_search=True,
  переопределены search() и get_categories().
  combo_mcp/tools/search_products.py — серверный поиск (magnit/pyaterochka)
  или по меню (fallback), сортировка по цене (price_rub asc), limit=/refresh=.
  combo_mcp/tools/list_categories.py — серверные категории (magnit/pyaterochka)
  или из меню (fallback), иерархия с children.
  combo_mcp/tools/meta.py — записи для search_products/list_categories.
  combo_mcp/server.py — регистрация 15 инструментов, версия 1.2.0,
  docstring обновлён. scripts/autotest.py — блок 9 (pag 2: 5 команд),
  блок 28 (15 инструментов, тесты новых тулов, query "Пепперони"),
  блок 29 check_shop_tools(). scripts/smoke_test.py — счётчик 15.
  Все тесты: autotest exit 0, smoke exit 0, selftest exit 0.
  Help: 15 команд → 2 страницы (10/5).

## Порядок старта сессии

1. `git fetch origin; git log HEAD..origin/main --oneline; git status --short`
   (проверка коммитов контрибьютора — см. ROADMAP.md «Проверка контрибьютора».
   ВАЖНО: при наличии чужих коммитов — ВСЕГДА спрашивать пользователя, что делать,
   не вливать и не откатывать самостоятельно.)
2. `scripts/autotest.py` — убедиться, что база зелёная.
3. Дальше — по задачам пользователя.