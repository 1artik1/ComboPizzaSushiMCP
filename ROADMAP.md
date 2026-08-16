# ROADMAP

## Сделано

- [x] Репозиторий: git-инициализация, remote (github.com/1artik1/ComboPizzaSushiMCP), ветка main
- [x] 7 сетей доставки Воронежа: la_pizza, pizza_kuba, ninja_food, sushi_time, sushi_darom, anti_sushi, dodo
- [x] Веса ninja_food с карточек товаров (OFFERS → DISPLAY_PROPERTIES), ретраи против рейт-лимита
- [x] best_combo: persons (1 напиток на персону во всех вариациях) + variations (по умолчанию 3)
- [x] Порядок вариаций: Оптимум → Без повторов → Макс. вес → доп. стратегии (variations > 3)
- [x] Детекция напитков: категория (napitki/Напитки/drinks) + эвристика по названию (RU/EN),
      без ложных срабатываний (ГУАНТАНАМО, Мини Колада, Фреш)
- [x] health_check — 10-й MCP-инструмент (HTTP, парсинг, кол-во позиций; refresh=false — по кэшу)
- [x] Автотесты scripts/autotest.py без record-режима:
      эталоны комбо (tests/expected.json), инварианты данных, контрольные блюда, связка с health_check
- [x] README, ROADMAP, smoke_test на 10 инструментов, selftest на новый формат

## В плане

- [ ] Веса pizza_kuba: у 40/44 позиций нет веса (комбо строится из 4 чизкейков) —
      нужен парсинг карточек товаров (как у ninja_food) или ручные эталоны
- [ ] ninja_food: ~26 позиций без веса из-за рейт-лимита сайта — увеличение ретраев/воркеров,
      очередь с паузами
- [ ] GUI: добавить persons/variations в la_pizza_app.py
- [ ] Обработка эмодзи в названиях (sushi_darom: 🌶) — уже ок, но проверить в GUI
- [ ] compare: учитывать persons при подсчёте комбо
- [ ] Доводка drinks.py: эвристика под новые сети (квас, айран, энергетики в других регионах)
- [ ] Приватные настройки: вынести TTL/таймауты в config\chains_config.json
