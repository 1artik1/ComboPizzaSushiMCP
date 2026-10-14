# ROADMAP

## Сделано

- [x] Репозиторий: git-инициализация, remote (github.com/1artik1/ComboPizzaSushiMCP), ветка main
- [x] 7 сетей доставки Воронежа: la_pizza, pizza_kuba, ninja_food, sushi_time, sushi_darom, anti_sushi, dodo
- [x] Веса ninja_food с карточек товаров (OFFERS → DISPLAY_PROPERTIES), ретраи против рейт-лимита
- [x] best_combo: persons (1 напиток на персону во всех вариациях) + variations (по умолчанию 3)
- [x] Порядок вариаций: Оптимум → Без повторов → Макс. вес → доп. стратегии (variations > 3)
- [x] Детекция напитков: категория (napitki/Напитки/drinks) + эвристика по названию (RU/EN),
      без ложных срабатываний (ГУАНТАНАМО, Мини Колада, Фреш)
- [x] Фикс подстрок в напитках: \bcola\b (chocolate ≠ cola), \bморс\b (Морской ≠ морс);
      добавлены бренды/типы додо (Dobry, Nectar, BonaAqua, lemon-lime, kiwi-grapes, fruit drink)
- [x] health_check — 10-й MCP-инструмент (HTTP, парсинг, кол-во позиций; refresh=false — по кэшу)
- [x] Автотесты scripts/autotest.py без record-режима:
      эталоны комбо (tests/expected.json), инварианты данных, контрольные блюда, связка с health_check
- [x] README, ROADMAP, smoke_test на 10 инструментов, selftest на новый формат
- [x] pizza_kuba: веса из названий размеров API ("33см (1кг)", "41см (1.5кг)", "150 г", "1 литр") —
      32/44 позиций с весом (пиццы, напитки, десерты); без веса — поштучные закуски и соусы
- [x] Справочник расчётных весов config/estimated_weights.json: ~90 позиций без веса
      (закуски "N шт", соусы, напитки) получили вес с полем source; weight_source:
      site | size_name | reference | none; применяется в best_combo/check_price/verify_chain/status
- [x] ninja_food: адаптивный рейт-гейт (общая пауза между запросами растёт при неудачах,
      спадает при успехах) вместо фиксированных пауз
- [x] GUI удалён из проекта (gui/la_pizza_app.py), остался archive/la_pizza_app_root_backup.py
- [x] Локализация названий (config/translations.json, додо — русские названия,
      бренды оставлены: Dobry, Rich, Pulpy, BonaAqua); в выборке комбо — вес единицы:
      «Пицца Пепперони Фреш (370 г) x2», «НАГГЕТСЫ (9 шт, 20 г/шт) x1»
- [x] compare: параметр persons (как best_combo — persons напитков в лучшем комбо),
      справочник весов и русские названия в ответе; автотест-блок 5 (compare == первая
      вариация best_combo, напитки = min(persons, доступных))
- [x] CONTEXT.md — чекпоинт состояния проекта для быстрого старта новой сессии
- [x] chain_info — 11-й MCP-инструмент: доставка/акции/лояльность по 7 сетям;
      ленивый дневной рефреш (extra_refresh_at "HH:MM" в chains_config.json), stale-if-error
- [x] find_promos: читаемые заголовки акций (последняя строка с «!», чистка предлогов)
- [x] drinks.py: тоник/швепс/газировка/байкал/фраппе — без регресса (ложные не вернулись)
- [x] TTL/таймауты в chains_config.json: http_timeout + menu_ttl_minutes
      (best_combo/parse_menu перепарсивают устаревший кэш; ninja_food 180 мин, dodo 240)
- [x] pizza_kuba: фактические веса закусок из описаний («150 гр.») — 3 позиции site
- [x] Фильтр комбо по категориям: categories в best_combo/compare (русские слова + группы
      pizza/rolls/sushi/sets/noodles/snacks/desserts/drinks/sauces/other);
      combo_mcp/categories.py (маппинг сырых категорий → группа, dodo — по имени десертов);
      напитки ТОЛЬКО если группа drinks в списке; ошибка с перечнем доступных групп сети;
      ревизия полноты меню: anti_sushi + подкаталоги (пицца/фьюжен/соусы/комбо/спецпредложения,
      дедупликация, 87 позиций), sushi_time напитки уже парсились (кэш обновлён),
      sushi_darom/la_pizza/anti_sushi напитков на сайтах нет; автотест блок 8
- [x] Команда /help (12-й инструмент): справочник 13 команд (имя/аргументы/описание/пример),
      пагинация 10 на страницу (next/back по памяти), детали команды /help <имя>; блок 9
- [x] Избранное (13-й инструмент): favorites add/list/remove/clear, cache/favorites.json
      (снимок комбо: позиции/вес/цена/₽100г, автогенерация label), пагинация list; блок 10
- [x] Модуль расширения сетей: ChainParser.category_map (категории в классе парсера),
      авто-регистрация парсеров (pkgutil, без правок __init__), get_chain_meta из реестра
      (класс = источник правды), scripts/new_chain.py (генератор: файл + конфиг + чек-лист),
      обновлены _template.py и README; блок 11
- [x] Фикс /help: пустой action сбрасывает _help_page на стр. 1 (был баг: повторный
      вызов показывал последнюю открытую страницу)
- [x] Фикс list_chains: available=True по кэшу (есть позиции), при refresh=true — по
      live-парсингу (был баг: без refresh всегда False)
- [x] Автотесты 12-13, 17-18, 28: инварианты кэша (name/price/weight/category/in_stock),
      золотые списки детекции напитков (16 поз + 15 нег), идемпотентность best_combo,
      Monte Carlo бюджетов (seed 42, 15 итераций на la_pizza+dodo), реальный MCP-протокол
      (13 инструментов + 5 быстрых вызовов); итого 16 блоков, все зелёные
- [x] Промо в комбо: config/promos.json (рукописные правила из акций chain_info —
      fixed/percent/cashback, scope order/pickup, min_order, per_item, once, stackable),
      combo_mcp/promos.py (apply_promos: фильтры, несуммируемость, promo_price),
      параметр promos=order|pickup|all в best_combo (promo_price/promo_saved в вариациях,
      promos_applied в ответе; кешбэк не меняет цену); блок 19 автотеста; итого 17 блоков
- [x] AGENTS.md — операционный справочник для агентов (запуск, структура, конвенции
      данных, ложные LSP-варнинги, git, делегирование)
- [x] Этап 1 «фундамент»: params.py (строковые параметры MCP), shared.py fetch_items
      (TTL + stale-if-error + причина ошибки), атомарный save_cache, clear_cache не
      трогает favorites/extra_*, verify_chain дедуп, weights кэш по mtime, удалён
      мёртвый scoring.py, убран глобальный socket.setdefaulttimeout; блок 28 со
      строковыми параметрами через реальный MCP
- [x] Этап 2 «реестр/логирование»: tools/meta.py — единый TOOLS_META (help генерирует
      из него, server.py регистрирует из него, version 1.1.0); logs.py → logs/server.log
- [x] Этап 3 «алгоритмы»: per-item промо-скидки встраиваются в цены ДО расчёта комбо
      (fixed-правила, price_rub=max(price-disc,1); order/pickup — постобработкой);
      solve_optimum_with_drinks — напитки оптимизируются ВНУТРИ DP (вес еды — целевое
      измерение, ровно persons напитков; пул топ-40 по вкусу + топ-15 по г/₽ + все
      напитки; кап 40 состояний на число напитков; быстрый путь для меню без вкуса);
      _limit_pool в solve_optimum (топ-40 вкус + топ-15 г/₽); split_items_str не режет
      запятую-десятичную («Кола 0,33л г/л»); refresh list_chains/health_check —
      параллельно (4 воркера); эталоны пересозданы (изменились только ninja_food и
      pizza_kuba — совместная оптимизация напитков)
- [x] Сессия 2026-08-24 (ветка ShopExtended): продуктовые магазины + shop-тулы.
  combo_mcp/chains/magnit.py — прямой webgate-API magnit.ru (requests, без браузера;
  цены в копейках → рубли, вес из weighted/имени, категории/поиск/пагинация).
  combo_mcp/chains/pyaterochka.py — Playwright-парсер 5ka.ru (запросы к
  5d.5ka.ru из контекста страницы); API закрыт анти-ботом → enabled=false.
  Новые MCP-тулы (14-й и 15-й, итого 15): search_products и
  list_categories. Сессия 2026-08-24 (продолжение): search_products прокачан
  до универсального поиска для нейросети — query первым, все enabled-сети одним
  вызовом (stores=/chain_id=), умный матчинг engines/textmatch.py (ё→е, регистр,
  токены, опечатки ≤1 буквы, бонус категории), фильтры categories=/min_price=/
  max_price=/in_stock=, sort relevance|price_asc|price_desc; источник — всегда
  TTL-кэш (magnit menu_ttl_minutes=10080 — неделя); серверная ветка из тула
  убрана. server.py 1.3.0. Блоки 28/29 обновлены (юнит textmatch, мультистор,
  фильтры, ошибки). Все тесты exit 0.
  combo_mcp/chains/base.py — search()/get_categories() + has_server_search.
  compare.py + health_check.py — get_enabled_chain_ids() (disabled-сети
  исключены). autotest.py — блоки 9/28/29 обновлены, get_enabled_chain_ids(),
  динамический подсчёт сетей; smoke_test.py — 15 тулов. tests/expected.json —
  пересоздан gen_expected.py (magnit/pyaterochka добавлены + live data drift).
  - [x] Сессия 2026-09-04 (merge origin/ShopExtended в merge/shop-stores): ревью ветки
  и переосмысление shop-интеграции. kind-разделение: 7 ресторанов kind=combo,
  magnit/pyaterochka kind=store; магазины НЕ участвуют в parse_menu/best_combo/compare.
  Новые тулы store_search/store_categories (только kind=store, нативный parser.search()/
  get_categories() — живые цены, без fallback по меню); search_products/list_categories
  из ветки удалены. config.py: get_chain_kind/get_combo_chain_ids/get_store_chain_ids.
  Отключённый магазин → явная ошибка enabled=false; ресторан в store-туле → kind=combo.
  autotest: циклы по _combo_meta(), блок 11 — 9 парсеров, новый блок 30 (store), эталоны
  и блоки 1..28 остались main-версии (persons и структура expected.json — как в main).
  Доки обновлены (README/AGENTS/CONTEXT). Тесты после merge: autotest/smoke/selftest.
  Решение о влитии в main — на усмотрение пользователя (коммит по явному запросу).
- [x] Сессия 2026-10-14 (фикс «CI красный через день»): CI перестал гонять живые
  сайты в гейте. Детерминированные снимки `tests/fixtures/` (меню + доп.данные
  7 combo-сетей), офлайн-режим (`COMBO_OFFLINE=1`, каталог кэша через
  `COMBO_CACHE_DIR`) — сеть запрещена, данные только из снимка. `autotest.py --offline`
  = гейт (ci.yml на push/PR + nightly job `gate`); живой прогон — отдельная
  негейтящая job `monitor` (summary + артефакт `live-report`). Эталоны пересозданы
  `gen_expected.py --fixtures` (контрольные блюда anti_sushi: Лакомка убрана с
  сайта → По-кушение/Хитяра). Починен краш `load_cache(...).get` при пустом кэше
  (`_cache_items`). Офлайн-прогон autotest: 0 FAIL.

## В плане

### План 2026-08-18: persons-упрощение, сквозной топ-N, категории, защита от дурака

Блок 1. Выпилить persons (согласовано):
- [x] Убрать параметр persons из API (best_combo/compare/meta.py) и dp.py
      (select_drinks/_combo_variants/_extra_variant/calculate_combos/_exclude_variants/
      _random_variants); фиксированный target = 1 напиток на комбо (TARGET_DRINKS);
      цикл персон (0, persons+1, max(persons*2,2)) → фикс (0, 2, 3); новая инварианта:
      «ровно 1 напиток в основных вариациях, если есть напитки с весом»
- [x] gen_expected.py: ключи {budget}_{persons} → {budget}; регенерировать expected.json
      осознанным шагом (diff-сверка)
- [x] autotest: блоки 1/4/4b/5/8/17/18/19/28 без persons (persons=0/-1-тесты → бюджетные
      budget=0/-1/abc); MC — persons фикс; smoke_test/selftest без persons
- [x] Доки: AGENTS.md, CONTEXT.md, README.md, ROADMAP.md
- [x] Побочно: mcart dodo/budget650 — _expected_drinks применяет справочник весов
      (BonaAqua без веса на сайте) и continue вместо break; ninja_food — отбрасывать
      позиции без цены (парсер фильтрует price<=0)

Блок 2. Сквозной топ-N в best_combo (согласовано):
- [x] chain_id: "" → все сети; список через запятую → только эти сети; валидация каждого
      id (trim) против get_chain_meta; single-chain — прежнее поведение (эталоны целы)
- [x] sort_by: price_per_100g | weight | price (default price_per_100g, словарь parse_menu),
      только в cross-chain режиме
- [x] Кандидаты: стратегии сети + padding топ-K позиций по метрике (добирает до variations
      при схлопывании стратегий — кейс «10 напитков»); ответ {mode, chains, skipped_chains,
      combos: [{rank, chain_id, name, ...}]}; refresh → 4 воркера; promos per-chain
- [x] Автотест блок 20 «cross-chain» (режимы, сортировки, ошибки, _pad_candidates)
- [x] Замечание: sushi_darom при variations>3 + budget≥5000 — 329с (перебор pareto-состояний
      в solve_optimum, без капа 40 как в _solve_dp_drinks). Исправлено: reachability + кап 40
      в _solve_optimum_pareto + лишние повторы _combo_variants в calculate_combos удалены
      (variations=6, budget=5000: 217с → 89с, качество сохранено — кап 40 не меняет оптимум;
      cap<40 ломает оптимум anti_sushi/sushi_time при budget=3000, поэтому глобальный кап не снижали)

Блок 3. Категории (из очереди, согласовано):
- [x] parse_menu: фильтр по группам (resolve_categories) + fallback на сырую категорию;
      chain_id в _filter_sort
- [x] Новая группа combo: categories.py (ALL_GROUPS + синоним «комбо»); la_pizza «комбо»,
      ninja_food «nabory», anti_sushi «Комбо» → combo; sushi_darom «Наборы» остаются sets
      (это ролл-сеты); categories=sets = чистые ролл-сеты
- [x] Автотест (блок 8 расширен): группа combo, маппинги сетей, sets без наборов

Блок 4. Защита от дурака (согласовано, капы 100k/50/500):
- [x] Капы: MAX_BUDGET=100000 (DP аллоцирует budget+1), MAX_VARIATIONS=50, MAX_LIMIT=500
      (parse_menu) — явные ошибки с лимитом (params.py, to_int получил maximum)
- [x] categories/sort_by не распознаны → явная ошибка с перечнем доступных (не молча [])
      (best_combo/compare: ошибка со списком ALL_GROUPS; parse_menu — fallback + sort_by ошибка)
- [x] chain_id trim везде (best_combo/_resolve_chain_ids, parse_menu, verify_chain,
      diff_menu, chain_info, check_price); favorites: валидация chain_id по списку,
      label ≤ 200, мусор/отрицательные в price/weight → ошибка; check_price item_name
      обязателен; единый формат ошибок {"error": ...}
- [x] Новый блок тестов 29 «защита от дурака»: budget=0/-5/abc/1e9/100001,
      variations=0/-1/abc/51, categories=фуфо (best_combo/compare), limit>500/abc,
      sort_by=бред, chain_id с пробелами/неизвестная, favorites мусор
      (сеть/price/weight/label>200/count=0), check_price/diff_menu/verify_chain,
      unknown tool через MCP — error без краша/зависания (тег "robust")

### Открытые пункты (ранее)

- [ ] dodo: мерч без веса (брелоки, игрушки, книги) — исключается из комбо намеренно
- [ ] pizza_kuba: закуски «10 шт» без граммов (креветка, сырные шарики, луковые,
      наггетсы) — остаются на справочных весах, пока сайт не даст граммы
- [ ] Приватные настройки: вынести остальные пороги (аномалии веса, мин. вес в комбо)
      в config\chains_config.json
- [ ] sushi_darom / la_pizza: напитков на сайтах нет — «пицца+напитки» там не работает,
      в ответе best_combo категории с перечнем доступных групп
- [ ] anti_sushi: категория «Напитки» на сайте удалена (/catalog/drinks/ → 404) —
      фильтр drinks для Антисуши вернёт ошибку с доступными группами
- [ ] Тест «Оптимум = максимум веса в бюджете»: для каждой сети на сетке бюджетов
      вес первой вариации >= веса остальных (замена выкинутой из блока 18 проверки
      ₽/100г — она неинвариантна из-за рюкзачной природы алгоритма; dp.py максимизирует
      суммарный вес, а не минимальный ₽/100г)
      ВАЖНО: после этапа 3 вес первой вариации считается по ЕДЕ (вес напитков не
      входит в целевую функцию), поэтому сравнение весов вариаций корректно только
      между вариациями одного вызова
- [ ] Мониторинг парсеров: алерты при деградации (ntfy/Telegram) на базе ночного CI
      + история health_check. Живой прогон уже не гейтит (job `monitor` ночного CI
      пишет summary + артефакт live-report); остаётся внешний алерт.
- [ ] pyaterochka (5ka.ru): обход анти-бота (капча «разверни картинку» не проходится
      headless-браузером) — варианты: ручной проход капчи с сохранением cookies,
      мобильный API X5, либо оставить выключенной

## На будущее (пока не делаем)

### Burger King (id `burgerking`) — burgerkingrus.ru

- [ ] Подключить сеть Burger King. Разведка проведена (2026-09-08), каркас подходит
      (Playwright-паттерн как у pyaterochka), реализация отложена. Техническая карта:
      - URL: меню отдаётся на КОРНЕ https://burgerkingrus.ru/ (путь /menu → 404!).
        city="Воронеж", kind=combo, needs_playwright=True.
      - Анти-бот ServicePipe (servicepipe.tech): JS-challenge + cookies spid/spsc/
        burgerking_ab_id; чистый HTTP не проходит даже на API-хосте — curl/powershell
        к orderapp.burgerkingrus.ru/gateway/menu-composition/api/v8/menu/group вернул
        523 (TLS-фингерпринт). В headless-браузере (Чром, UA обычный) challenge
        проходится чисто → паттерн _open_page как в combo_mcp/chains/pyaterochka.py
        (проверка капчи → ChainUnavailable; затем ждать появления `__NUXT_DATA__`).
      - Каталог — Nuxt.js SSR: весь каталог в `<script id="__NUXT_DATA__">` (~1.2 МБ,
        flatted-кодировка, резолвер по индексам). Внутри:
        `{badges, categories, combos, dishes, groups, keys}`.
        Позиция (dishes): `{id, name, price (КОПЕЙКИ: 61999 = 619,99 ₽;
        price_rub = round(коп/100)), price_without_combo, show_price_without_combo,
        image, categories[]}`. `keys.prices_key` — токен цен для API композиции.
        Маппинг категорий НЕ в карточке напрямую: у диша поле `categories` = список
        id категорий, а `categories` в payload = массив объектов `{id, name, ...}` —
        брать name категории («Бургеры», «Комбо», ...), затем category_map →
        группы. Цены/меню федеральные единые (не зависят от города/ресторана).
      - Весов в каталоге НЕТ (по ключам weight/kcal/foodValue — ноль). Вес добирается
        поштучно: `POST orderapp.burgerkingrus.ru/gateway/menu-composition/api/v8/menu/group`,
        body `{"params":{"id":<dish_id>,"type":"stay","source":"web","keys":{"prices_key":<pk>}}}`,
        заголовки: content-type/accept json, x-burgerking-platform: web_mobile, referer.
        Ответ: `result.group.dishes[].composition.unit.amount` — вес в г/мл
        (Ангус 4 Сыра = 337 г; unit.name = «г» или «мл»), плюс
        `composition.kcals/proteins/fats/carbs` (amount/per_100), `main_info.price`,
        `composition.description`. Вызовы из контекста страницы — `page.evaluate(fetch(...))`,
        батчами Promise.all по 10–16 (N+1 ≈ 150–250 POST на первый парсинг, далее
        дисковый кэш TTL 120 мин). Питьевые мл ≈ г (weight_source="site").
        Готовые комбо — это обычные позиции категории «Комбо» (как продукты, не
        составлять из частей вручную).
      - Категории сайта: Новинки, Комбо, Соусы (подкатегории), Бургеры (Премиум/
        Говядина/Курица и рыба/Острые), Вкусы Воппера, Дети любят, Роллы (Воппер Ролл),
        Картофель и закуски, Напитки и десерты (Холодные/Горячие напитки, Пиво,
        Молочные коктейли, Десерты), Купоны.
      - Решения (согласованы при разведке): веса ТОЛЬКО через API композиции
        (не справочник); новая группа `burgers` в categories.py (ALL_GROUPS + синонимы
        «бург», «burger», «воппер»); Бургеры→burgers, Картофель и закуски→snacks,
        Комбо→combo, Напитки и десерты→drinks, Соусы→sauces, Роллы→rolls,
        Дети любят→snacks, Новинки/Вкусы Воппера/Купоны→other.
      - Файлы: combo_mcp/chains/burgerking.py (новый), categories.py (группа burgers),
        config/chains_config.json (entry kind=combo, enabled=true, menu_ttl_minutes=120),
        tests/expected.json перегенерить gen_expected.py осознанным шагом; в autotest
        для burgerking допускать ChainUnavailable (анти-бот) без красного CI.
        parse_extra (доставка/купоны) на первом этапе НЕ делать.
      - Риски: ServicePipe меняет куки/капчу во времени (pyaterochka с тем же анти-ботом
        лежит выключенной) — лечится TTL + stale-if-error; первый парсинг медленный;
        «Роллы» BK попадут в группу rolls (отдельная сеть, не смешивается);
        Пиво в «Напитках» — решить при имплементации (исключать из комбо или нет).

### Telegram-бот

- [ ] Обёртка над 15 инструментами (комбо по запросу, избранное, алерты)
- [ ] История цен: накопление снапшотов меню в SQLite по расписанию → тренды
      (графики «цена растёт/падает» за недели). Сейчас закрыто диффом на месте:
      diff_menu показывает изменения между двумя загрузками. Тренды — накопление
      таких изменений во времени; для личного проекта признано переизбытком, к
      боту вернуться, если понадобятся аналитика и уведомления о снижении цен

## Субагент-делегирование

Задачи можно (и нужно) делегировать субагентам:

- **explore** — разведка кода/данных: «где лежит X», «как устроено Y», сбор контекста.
  Не пишет код.
- **qwen3coder_code** — реализация по готовому ТЗ: точечные правки, рефакторинг,
  поиск и обработка данных, анализ логов. Возвращает выжимку.
- **qwen3coder_research** — исследование кодовой базы + веб (SearXNG): источники,
  документация, поиск причин. Не редактирует и не планирует.

НЕ делегируется:
- Обновление эталонов tests/expected.json (нужен контроль согласованности с real-данными)
- Решения о данных и бизнес-логике (что считать напитком, какой вес считать честным)
- Публикация (коммит, пуш, проверка remote)

## Проверка контрибьютора (в начале каждой сессии)

```powershell
git fetch origin
git log HEAD..origin/main --oneline
git status --short
```

Если есть чужие коммиты: `git diff HEAD..origin/main`, прогнать scripts/autotest.py,
всегда спросить у пользователя, что делать (не вливать и не откатывать самостоятельно).