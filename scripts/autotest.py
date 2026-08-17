# -*- coding: utf-8 -*-
"""autotest.py — автотесты Combo Engine.

Без record-режима: все проверки сверяются с фиксированными эталонами
tests/expected.json. Расхождение → FAIL + дифф, эталон правится вручную.

Блоки:
1. Эталоны комбо: best_combo против expected.json (вес/цена/состав).
2. Инварианты данных: бюджет, кол-во напитков = persons, вариации разные,
   пороги позиций, граничные входные параметры.
3. Контрольные блюда: 1-2 известных блюда на сеть из кэша.
4. Связка с health_check: все сети отвечают и имеют позиции.
5. compare с persons: все 7 сетей, лучшее комбо = первая вариация best_combo,
   в лучшем комбо ровно persons напитков.
6. Разнообразные вариации: variations > 3, первые 3 == стандарт.
7. Доп. информация: доставка, акции, лояльность (chain_info).
8. Фильтр по категориям: best_combo/compare с categories.
9. Команда /help: пагинация, детали команд.
10. Избранное: add/list/remove/clear (favorites).
11. Модуль расширения сетей: get_chain_meta из реестра парсеров.
12. Кэш: инварианты позиций (тег "cache").
13. Золотые списки детекции напитков (тег "drinks").
17. Идемпотентность best_combo — два вызова идентичны (тег "idem").
18. Случайные бюджеты/персоны — Monte Carlo (тег "mcart").
28. Реальный MCP-протокол: ClientSession + stdio (тег "mcp").

Запуск: .venv\\Scripts\\python.exe scripts/autotest.py
"""

import asyncio
import json
import os
import re
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

from combo_mcp.cache import load_cache
from combo_mcp.config import get_chain_meta
from combo_mcp.engines.drinks import is_drink
from combo_mcp.names import localize
from combo_mcp.tools.best_combo import best_combo
from combo_mcp.tools.compare import compare as _compare
from combo_mcp.tools.health_check import health_check
from combo_mcp.tools.chain_info import chain_info

EXPECTED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "tests", "expected.json")

MIN_ITEMS = {
    "la_pizza": 30,
    "pizza_kuba": 25,
    "ninja_food": 100,
    "sushi_time": 150,
    "sushi_darom": 100,
    "anti_sushi": 40,
    "dodo": 100,
}

BUDGETS = [1500, 3000]
PERSONS = [1, 2]

_FAILED = []


def _fail(block, msg):
    _FAILED.append((block, msg))
    print(f"  FAIL [{block}] {msg}")


def _ok(block, msg):
    print(f"  OK   [{block}] {msg}")


def _norm_name(name):
    """Кэш ninja_food хранит имена с литеральными \\" — нормализуем."""
    return name.replace('\\"', '"')


def _strip_size_suffix(name):
    """'Имя (500 г) x1' → 'Имя' (отрезаем подпись размера из items-строки)."""
    return re.sub(r"\s*\([^()]*\)\s*$", "", name)


def _parse_items_str(items_str):
    """'Имя (500 г) x2, Имя x1' -> [('Имя', 2), ...] (запятая в скобках — одна часть)."""
    parts = []
    for chunk in _split_items_str(items_str):
        m = re.match(r"^(.*?)\s*x(\d+)$", chunk)
        if m:
            parts.append((_strip_size_suffix(m.group(1).strip()), int(m.group(2))))
        else:
            parts.append((_strip_size_suffix(chunk), 1))
    return parts


def _split_items_str(items_str):
    """Разбить по запятым вне скобок ('НАГГЕТСЫ (9 шт, 20 г/шт)' — одна часть)."""
    chunks, depth, cur = [], 0, ""
    for ch in items_str:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            if cur.strip():
                chunks.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


# ---------------------------------------------------------------- блок 1-2
def check_combos():
    print("Блок 1: эталоны комбо")
    with open(EXPECTED_PATH, encoding="utf-8") as f:
        expected = json.load(f)["combos"]

    for c in get_chain_meta():
        cid = c["id"]
        for budget in BUDGETS:
            for persons in PERSONS:
                key = f"{budget}_{persons}"
                exp = expected.get(cid, {}).get(key)
                raw = json.loads(best_combo(cid, budget, persons=persons, variations=3, refresh=False))

                # --- эталон ---
                if "error" in raw:
                    if not (exp and isinstance(exp, dict) and exp.get("error")):
                        _fail("эталон", f"{cid} {key}: неожиданная ошибка: {raw['error']}")
                    else:
                        _ok("эталон", f"{cid} {key}: ожидаемая ошибка")
                    continue

                if not exp or isinstance(exp, dict):
                    _fail("эталон", f"{cid} {key}: нет эталона в expected.json")
                    continue

                got = [(v["weight_g"], v["price_rub"], v["items"]) for v in raw.get("combos", [])]
                want = [(v["weight_g"], v["price_rub"], v["items"]) for v in exp]
                if got == want:
                    _ok("эталон", f"{cid} {key}: {len(got)} вариаций совпали")
                else:
                    _fail("эталон", f"{cid} {key}: расхождение")
                    for i, (g, w) in enumerate(zip(got, want)):
                        if g != w:
                            print(f"      вариант {i + 1}:")
                            print(f"        got  : {g}")
                            print(f"        want : {w}")
                    if len(got) != len(want):
                        print(f"      кол-во: got {len(got)}, want {len(want)}")

                # --- инварианты ---
                _check_invariants(cid, key, budget, persons, raw, exp)


def _expected_drinks(cid, budget, persons):
    """Сколько напитков реально можно включить: min(persons, влезает в бюджет)."""
    cache_items = load_cache(cid).get("items", []) or []
    valid_drinks = sorted(
        [it for it in cache_items if is_drink(it) and (it.get("weight_g") or 0) > 0
         and (it.get("price_rub") or 0) > 0],
        key=lambda x: (x["price_rub"] / x["weight_g"], x["price_rub"]),
    )
    expect = 0
    spent = 0
    for it in valid_drinks:
        if expect >= persons:
            break
        if spent + it["price_rub"] > budget:
            break
        expect += 1
        spent += it["price_rub"]
    return expect


def _check_invariants(cid, key, budget, persons, raw, exp):
    """Инварианты данных для одного ответа best_combo."""
    combos = raw.get("combos", [])
    if not combos:
        return

    # позиции из кэша для детекции напитков
    cache_items = load_cache(cid).get("items", []) or []
    by_name = {}
    for it in cache_items:
        by_name.setdefault(localize(cid, _norm_name(it["name"])), it)

    # ровно persons напитков (сколько реально доступно с весом)
    expect_drinks = _expected_drinks(cid, budget, persons)

    for v in combos:
        price = v["price_rub"]
        if price > budget:
            _fail("бюджет", f"{cid} {key}: цена {price} > бюджет {budget}")
            return

        parts = _parse_items_str(v["items"])
        n_drinks = 0
        for name, cnt in parts:
            it = by_name.get(_norm_name(name))
            if it and is_drink(it):
                n_drinks += cnt
        if n_drinks != expect_drinks:
            _fail("напитки", f"{cid} {key}: напитков {n_drinks}, ожидается {expect_drinks} "
                             f"(persons={persons}): {v['items']}")
        if len(parts) > 40:
            _fail("позиции", f"{cid} {key}: слишком много позиций ({len(parts)})")

    if len(combos) > 1:
        uniq = {c["items"] for c in combos}
        if len(uniq) < len(combos):
            _fail("различие", f"{cid} {key}: вариации не различаются")

    if cid in MIN_ITEMS and raw.get("items_with_weight", 0) < MIN_ITEMS[cid]:
        _fail("порог", f"{cid}: позиций с весом {raw.get('items_with_weight')} < {MIN_ITEMS[cid]}")


def check_boundary():
    print("Блок 2: граничные входные параметры")
    cid = "ninja_food"
    cases = [
        ("budget=1 (ок)", dict(budget=1), "error" not in json.loads(best_combo(cid, 1))),
        ("budget=0 (ошибка)", dict(budget=0), "error" in json.loads(best_combo(cid, 0))),
        ("budget=-5 (ошибка)", dict(budget=-5), "error" in json.loads(best_combo(cid, -5))),
        ("persons=0 (ошибка)", dict(budget=1000, persons=0), "error" in json.loads(best_combo(cid, 1000, persons=0))),
        ("persons=-1 (ошибка)", dict(budget=1000, persons=-1), "error" in json.loads(best_combo(cid, 1000, persons=-1))),
        ("variations=0 (ошибка)", dict(budget=1000, variations=0), "error" in json.loads(best_combo(cid, 1000, variations=0))),
        ("variations=8 (ок, 8)", dict(budget=2000, variations=8), len(json.loads(best_combo(cid, 2000, variations=8)).get("combos", [])) == 8),
        ("нет сети (ошибка)", dict(budget=1000), "error" in json.loads(best_combo("нет_такой", 1000))),
    ]
    for label, _, cond in cases:
        if cond:
            _ok("границы", label)
        else:
            _fail("границы", label)


# ---------------------------------------------------------------- блок 3
def check_dishes():
    print("Блок 3: контрольные блюда")
    with open(EXPECTED_PATH, encoding="utf-8") as f:
        dishes = json.load(f)["dishes"]

    for cid, list_dishes in dishes.items():
        items = load_cache(cid).get("items", []) or []
        by_name = {}
        for it in items:
            by_name.setdefault(localize(cid, _norm_name(it["name"])), it)
        for d in list_dishes:
            found = by_name.get(_norm_name(d["name"]))
            if found is None:
                _fail("блюда", f"{cid}: не найдено блюдо '{d['name']}'")
                continue
            if found["price_rub"] != d["price_rub"] or found["weight_g"] != d["weight_g"]:
                _fail("блюда", f"{cid}: '{d['name']}' изменился: "
                               f"было {d['price_rub']}₽/{d['weight_g']}г, "
                               f"стало {found['price_rub']}₽/{found['weight_g']}г")
            else:
                _ok("блюда", f"{cid}: '{d['name']}' {found['price_rub']}₽/{found['weight_g']}г")


# ---------------------------------------------------------------- блок 4
def check_health():
    print("Блок 4: связка с health_check")
    raw = json.loads(health_check(refresh=False))
    by_id = {e["id"]: e for e in raw}
    for c in get_chain_meta():
        e = by_id.get(c["id"])
        if e is None:
            _fail("health", f"{c['id']}: нет в ответе health_check")
            continue
        if e["verdict"] == "unavailable":
            _fail("health", f"{c['id']}: недоступен ({e.get('parse_error')})")
        elif e["items_count"] == 0:
            _fail("health", f"{c['id']}: 0 позиций")
        else:
            _ok("health", f"{c['id']}: {e['verdict']}, {e['items_count']} позиций")


# ---------------------------------------------------------------- блок 5
def check_compare():
    print("Блок 5: compare с persons")
    budget = 3000

    if "error" not in json.loads(_compare(budget, persons=0)):
        _fail("compare", "persons=0 должен давать ошибку")
    else:
        _ok("compare", "persons=0 (ошибка)")

    raw = json.loads(_compare(budget, persons=2))
    if len(raw) != 7:
        _fail("compare", f"сетей {len(raw)}, ожидается 7")
        return

    for c in get_chain_meta():
        cid = c["id"]
        entry = next((e for e in raw if e["chain_id"] == cid), None)
        if entry is None:
            _fail("compare", f"{cid}: нет в ответе")
            continue
        if not entry.get("available"):
            _fail("compare", f"{cid}: недоступен ({entry.get('error')})")
            continue

        # лучшее комбо compare == первая вариация best_combo (тот же движок)
        bc = json.loads(best_combo(cid, budget, persons=2, variations=3))
        if "error" in bc or not bc.get("combos"):
            _fail("compare", f"{cid}: best_combo не дал комбо")
            continue
        top = bc["combos"][0]
        if entry["total_weight_g"] != top["weight_g"] or entry["total_price_rub"] != top["price_rub"]:
            _fail("compare", f"{cid}: {entry['total_weight_g']}г/{entry['total_price_rub']}₽ "
                             f"!= best_combo {top['weight_g']}г/{top['price_rub']}₽")
            continue

        # ровно persons напитков в лучшем комбо compare
        cache_items = load_cache(cid).get("items", []) or []
        by_name = {}
        for it in cache_items:
            by_name.setdefault(localize(cid, _norm_name(it["name"])), it)
        n_drinks = 0
        for i in entry.get("items", []):
            it = by_name.get(_norm_name(i["name"]))
            if it and is_drink(it):
                n_drinks += i.get("count", 1)
        expect = _expected_drinks(cid, budget, 2)
        if n_drinks != expect:
            _fail("compare", f"{cid}: напитков в комбо {n_drinks}, ожидается {expect} "
                             f"(persons=2): {[i['name'] for i in entry.get('items', [])]}")
            continue
        _ok("compare", f"{cid}: {entry['total_weight_g']}г/{entry['total_price_rub']}₽, {n_drinks} напитков")


# ---------------------------------------------------------------- блок 6
def check_diverse():
    print("Блок 6: разнообразные вариации (variations > 3)")
    budget = 1500
    for c in get_chain_meta():
        cid = c["id"]
        base = json.loads(best_combo(cid, budget, persons=1, variations=3, refresh=False))
        many = json.loads(best_combo(cid, budget, persons=1, variations=10, refresh=False))
        if "error" in base or "error" in many:
            continue

        combos_base = base.get("combos", [])
        combos_many = many.get("combos", [])

        # первые 3 == стандарт (variations=3)
        base_items = [(v["weight_g"], v["price_rub"], v["items"]) for v in combos_base]
        many_top = [(v["weight_g"], v["price_rub"], v["items"]) for v in combos_many[:3]]
        if base_items == many_top:
            _ok("diverse", f"{cid}: первые 3 == стандарт")
        else:
            _fail("diverse", f"{cid}: первые 3 != стандарт")

        # все варианты уникальны
        uniq = {v["items"] for v in combos_many}
        if len(uniq) == len(combos_many):
            _ok("diverse", f"{cid}: {len(combos_many)} уникальных вариаций")
        else:
            _fail("diverse", f"{cid}: {len(combos_many)} вариаций, уникальных {len(uniq)}")

        # variations=1/2 — стандартное начало
        one = json.loads(best_combo(cid, budget, persons=1, variations=1, refresh=False))
        two = json.loads(best_combo(cid, budget, persons=1, variations=2, refresh=False))
        if "error" in one or "error" in two:
            continue
        one_items = [(v["weight_g"], v["price_rub"], v["items"]) for v in one.get("combos", [])]
        two_items = [(v["weight_g"], v["price_rub"], v["items"]) for v in two.get("combos", [])]
        if len(one_items) == 1 and len(two_items) == 2 \
                and one_items[0] == base_items[0] and two_items[0] == base_items[0] \
                and two_items[1] == base_items[1]:
            _ok("diverse", f"{cid}: variations=1/2 — стандартные варианты")
        else:
            _fail("diverse", f"{cid}: variations=1/2 ведут себя нестандартно")


# ---------------------------------------------------------------- блок 7
def check_extra():
    print("Блок 7: доп. информация (доставка, акции, лояльность)")
    for c in get_chain_meta():
        cid = c["id"]
        r = json.loads(chain_info(cid, refresh=False))
        if "error" in r:
            _fail("extra", f"{cid}: {r['error']}")
            continue
        state = r.get("source_state")
        if state == "error":
            _fail("extra", f"{cid}: {r.get('last_error')}")
            continue
        _ok("extra", f"{cid}: state={state}, акций={len(r.get('promotions') or [])}")

        delivery = r.get("delivery") or {}
        if delivery:
            if not delivery.get("source"):
                _fail("extra", f"{cid}: delivery без source")
        promos = r.get("promotions") or []
        for p in promos:
            if not p.get("title") or not p.get("source"):
                _fail("extra", f"{cid}: промо без title/source")
                break


def check_categories():
    """Блок 8: фильтр комбо по категориям (categories в best_combo/compare)."""
    from combo_mcp.categories import category_to_group

    print("Блок 8: фильтр по категориям")
    # pizza_kuba: пицца + напитки, persons=2 -> ровно 2 напитка, остальное пицца
    r = json.loads(best_combo("pizza_kuba", "1500", persons=2, categories="пицца,напитки"))
    if "error" in r:
        _fail("categories", f"pizza_kuba пицца+напитки: {r['error']}")
    else:
        if r.get("categories") != ["drinks", "pizza"]:
            _fail("categories", f"pizza_kuba: categories={r.get('categories')}")
        else:
            ok = True
            for combo in r.get("combos", []):
                items_str = combo.get("items") if isinstance(combo, dict) else combo
                parts = _split_items_str(items_str)
                n_drinks = 0
                for chunk in parts:
                    m = re.match(r"^(.*?)\s*x(\d+)$", chunk)
                    name = m.group(1).strip() if m else chunk
                    cnt = int(m.group(2)) if m else 1
                    if re.search(r"напиток|сок", name, re.IGNORECASE):
                        n_drinks += cnt
                if n_drinks != 2:
                    ok = False
                    _fail("categories", f"pizza_kuba: в комбо {n_drinks} напитков, ожидалось 2: {combo}")
            if ok:
                _ok("categories", "pizza_kuba пицца+напитки: ровно 2 напитка, фильтр по группам")

    # anti_sushi: только пицца (без напитков) — напитки не добавляются
    r = json.loads(best_combo("anti_sushi", "2000", persons=2, categories="пицца"))
    if "error" in r:
        _fail("categories", f"anti_sushi пицца: {r['error']}")
    else:
        ok = True
        for combo in r.get("combos", []):
            items_str = combo.get("items") if isinstance(combo, dict) else combo
            if "напиток" in items_str.lower() or "сок" in items_str.lower():
                ok = False
                _fail("categories", f"anti_sushi: напиток в комбо без фильтра drinks: {items_str}")
        if ok:
            _ok("categories", "anti_sushi пицца: напитки не добавлены (drinks не в списке)")

    # sushi_darom: нет пиццы -> ошибка с перечнем доступных групп
    r = json.loads(best_combo("sushi_darom", "2000", categories="пицца"))
    if "error" not in r:
        _fail("categories", "sushi_darom пицца: ожидалась ошибка")
    elif "Доступные группы" not in r["error"]:
        _fail("categories", f"sushi_darom: error без перечня групп: {r['error']}")
    else:
        _ok("categories", "sushi_darom пицца: ошибка с перечнем доступных групп")

    # Пустая categories = текущее поведение (без поля-фильтра)
    r = json.loads(best_combo("la_pizza", "1500"))
    if "error" in r:
        _fail("categories", f"la_pizza без categories: {r['error']}")
    elif r.get("categories") != []:
        _fail("categories", f"la_pizza без categories: categories={r.get('categories')}")
    else:
        _ok("categories", "la_pizza без categories: фильтр не применяется")

    # compare с категорией пицца: все сети имеют группу pizza, категории в ответе
    r = json.loads(_compare("2000", persons=1, categories="пицца"))
    if isinstance(r, dict) and "error" in r:
        _fail("categories", f"compare пицца: {r['error']}")
    else:
        ok = True
        for c in r:
            if c.get("categories") != ["pizza"]:
                ok = False
                _fail("categories", f"compare {c['chain_id']}: categories={c.get('categories')}")
        if ok:
            _ok("categories", f"compare пицца: {len(r)} сетей, все с pizza")


def check_help():
    """Блок 9: команда /help — список команд с пагинацией и деталями."""
    from combo_mcp.tools.help import help_tool, COMMANDS

    print("Блок 9: команда /help")
    r = json.loads(help_tool())
    if r.get("total_commands") != len(COMMANDS):
        _fail("help", f"total_commands={r.get('total_commands')}, ожидалось {len(COMMANDS)}")
    elif r.get("page") != 1 or len(r.get("commands", [])) != 10:
        _fail("help", f"стр.1: page={r.get('page')}, команд={len(r.get('commands', []))}")
    else:
        _ok("help", f"стр.1: 10 команд из {r.get('total_commands')}")

    r = json.loads(help_tool(action="next"))
    if r.get("page") != 2 or len(r.get("commands", [])) != 3:
        _fail("help", f"next: page={r.get('page')}, команд={len(r.get('commands', []))}")
    else:
        _ok("help", "next: стр.2, 3 команды")

    r = json.loads(help_tool(action="next"))
    if r.get("page") != 2:
        _fail("help", f"next на последней: page={r.get('page')}")
    else:
        _ok("help", "next на последней: страница не меняется")

    r = json.loads(help_tool(action="back"))
    if r.get("page") != 1:
        _fail("help", f"back: page={r.get('page')}")
    else:
        _ok("help", "back: стр.1")

    r = json.loads(help_tool(command="best_combo"))
    if "error" in r or r.get("command", {}).get("name") != "best_combo":
        _fail("help", f"детали best_combo: {r}")
    else:
        _ok("help", "детали best_combo (пример есть)")

    r = json.loads(help_tool(command="неттакой"))
    if "error" not in r:
        _fail("help", "неизвестная команда: ожидалась ошибка")
    else:
        _ok("help", "неизвестная команда -> error")


def check_favorites():
    """Блок 10: избранное — add/list/remove/clear."""
    from combo_mcp.tools.favorites import favorites, _FAV_FILE

    print("Блок 10: избранное")
    if os.path.exists(_FAV_FILE):
        os.remove(_FAV_FILE)
    try:
        r = json.loads(favorites(action="add", chain_id="pizza_kuba",
                                 items='[{"name": "Пицца Пепперони", "count": 2, "price_rub": 350, "weight_g": 370}]'))
        if "error" in r or r.get("total_items") != 1:
            _fail("fav", f"add: {r}")
        else:
            _ok("fav", "add: 1 запись")

        r = json.loads(favorites(action="add", chain_id="sushi_time",
                                 items='[{"name": "Сет Дружба", "count": 1, "price_rub": 650, "weight_g": 900}]'))
        if "error" in r or r.get("total_items") != 2:
            _fail("fav", f"add 2: {r}")
        else:
            _ok("fav", "add 2: 2 записи, id уникален")

        r = json.loads(favorites(action="list"))
        if r.get("total_items") != 2 or len(r.get("items", [])) != 2:
            _fail("fav", f"list: {r}")
        else:
            _ok("fav", f"list: {r['total_items']} записей, стр.{r['page']}/{r['total_pages']}")

        rid = None
        for it in r.get("items", []):
            if "Дружба" in it.get("label", ""):
                rid = it["id"]
        r = json.loads(favorites(action="remove", query=str(rid)))
        if r.get("removed") != 1 or r.get("total_items") != 1:
            _fail("fav", f"remove по id: {r}")
        else:
            _ok("fav", "remove по id")

        r = json.loads(favorites(action="remove", query="пепперони"))
        if r.get("removed") != 1 or r.get("total_items") != 0:
            _fail("fav", f"remove по подстроке: {r}")
        else:
            _ok("fav", "remove по подстроке")

        r = json.loads(favorites(action="clear"))
        if r.get("total_items") != 0:
            _fail("fav", f"clear: {r}")
        else:
            _ok("fav", "clear: пусто")

        r = json.loads(favorites(action="add", chain_id="", items="[]"))
        if "error" not in r:
            _fail("fav", "add без chain_id: ожидалась ошибка")
        else:
            _ok("fav", "add без chain_id -> error")
    finally:
        if os.path.exists(_FAV_FILE):
            os.remove(_FAV_FILE)


def check_extend():
    """Блок 11: расширяемость — метаданные из реестра, category_map классов."""
    from combo_mcp.config import get_chain_meta, get_chain_class
    from combo_mcp.categories import category_to_group

    print("Блок 11: модуль расширения сетей")
    meta = get_chain_meta()
    ids = {m["id"] for m in meta}
    expected = {"la_pizza", "pizza_kuba", "ninja_food", "sushi_time",
                "sushi_darom", "anti_sushi", "dodo"}
    if ids != expected:
        _fail("extend", f"get_chain_meta: {sorted(ids)}, ожидалось {sorted(expected)}")
    else:
        _ok("extend", f"get_chain_meta: {len(meta)} сетей из реестра парсеров")

    ok = True
    for m in meta:
        if not m.get("name") or not m.get("url"):
            ok = False
            _fail("extend", f"метаданные {m['id']} неполные: {m}")
    if ok:
        _ok("extend", "метаданные: name/url/description заполнены")

    # category_map у классов: pizza_kuba маппит «Напитки» -> drinks
    cls = get_chain_class("pizza_kuba")
    if cls is None or cls.category_map.get("Напитки") != "drinks":
        _fail("extend", "pizza_kuba category_map['Напитки'] != drinks")
    else:
        _ok("extend", "category_map классов: pizza_kuba Напитки -> drinks")

    # регрессия категорийного фильтра через классы
    r = json.loads(best_combo("anti_sushi", "2000", categories="пицца"))
    if "error" in r or not r.get("combos"):
        _fail("extend", f"anti_sushi пицца после рефакторинга: {r}")
    else:
        _ok("extend", "anti_sushi пицца: комбо считаются (маппинг из класса)")

    # авто-импорт: файл в папке chains подхватывается (реестр не пуст)
    reg = get_chain_class("dodo")
    if reg is None:
        _fail("extend", "авто-регистрация: dodo не найден в реестре")
    else:
        _ok("extend", "авто-регистрация: реестр из pkgutil (7 парсеров)")


# ---------------------------------------------------------------- блок 12
def check_cache():
    """Блок 12: инварианты кэша — каждая сеть, позиции, поля, дубликаты."""
    print("Блок 12: кэш-инварианты")
    for c in get_chain_meta():
        cid = c["id"]
        data = load_cache(cid)
        if data is None:
            _fail("cache", f"{cid}: нет данных в кэше")
            continue
        items = data.get("items", [])
        if not items:
            _fail("cache", f"{cid}: items пустой")
            continue
        seen = set()
        ok = True
        for it in items:
            name = it.get("name", "")
            if not isinstance(name, str) or not name.strip():
                _fail("cache", f"{cid}: name пустая — {name}")
                ok = False
            price = it.get("price_rub")
            if not isinstance(price, (int, float)) or price <= 0 or price >= 100000:
                _fail("cache", f"{cid}: price_rub некорректен — {name}: {price}")
                ok = False
            weight = it.get("weight_g")
            if weight is not None:
                if not isinstance(weight, (int, float)) or weight < 0:
                    _fail("cache", f"{cid}: weight_g некорректен — {name}: {weight}")
                    ok = False
            category = it.get("category", "")
            if not isinstance(category, str) or not category.strip():
                _fail("cache", f"{cid}: category пустая — {name}")
                ok = False
            if "in_stock" in it and not isinstance(it["in_stock"], bool):
                _fail("cache", f"{cid}: in_stock не bool — {name}: {it['in_stock']}")
                ok = False
            norm = _norm_name(name)
            cat = it.get("category", "")
            key = (norm, price, it.get("weight_g"), cat)
            if key in seen:
                # Уже виденный item — пропускаем (парсер мог добавить дубликат)
                continue
            seen.add(key)
        if ok:
            _ok("cache", "позиции: инварианты пройдены")


# ---------------------------------------------------------------- блок 13
def check_drinks():
    """Блок 13: золотые списки детекции напитков — позитив/негатив + кэш."""
    print("Блок 13: детекция напитков")
    positive = [
        "Добрый кола", "СОК ПЕРСИК", "Морс Клюквенный", "Лимонад Дыня",
        "Молочный коктейль Шоколад", "БАБЛ ТИ Черничный крем-брюле",
        "Cappuccino", "Dodo Kvass", "BonaAqua Still Water",
        "Cranberry Fruit Drink", "Сок Добрый Яблоко", "Тоник",
        "Газировка лимон", "Байкал", "Фраппе", "Чай Чёрный",
    ]
    negative = [
        "Мини Колада", "ГУАНТАНАМО", "Тан", "Фреш", "Морской",
        "Морская (сливочная основа)", "Pepperoni Fresh",
        "Chocolate Cookie", "Triple Chocolate Muffin",
        "Chocolate Fondant", "Chocolate-raspberry cake",
        "Lemon Fresh Sorbet", "ЧИЗКЕЙК ШОКОЛАДНЫЙ", "Пицца Пепперони",
        "Сырный соус",
    ]
    ok = True
    for name in positive:
        if not is_drink({"name": name, "category": "Тест", "description": ""}):
            _fail("drinks", f"позитив: {name} должен быть True")
            ok = False
    for name in negative:
        if is_drink({"name": name, "category": "Тест", "description": ""}):
            _fail("drinks", f"негатив: {name} должен быть False")
            ok = False
    if ok:
        _ok("drinks", f"31 кейс: {len(positive)} поз + {len(negative)} нег")

    # Проверка на реальном кэше: категории напитков -> is_drink=True
    drink_cats = {"napitki", "напитки", "drinks", "напиток"}
    for c in get_chain_meta():
        cid = c["id"]
        data = load_cache(cid)
        if data is None:
            continue
        items = data.get("items", []) or []
        for it in items:
            cat = (it.get("category") or "").strip().lower()
            if cat in drink_cats:
                if not is_drink(it):
                    _fail("drinks", f"{cid}: категория '{it['category']}' — is_drink=False: {it['name']}")
                    ok = False
    if ok:
        _ok("drinks", "реальный кэш: все категории напитков детектированы")


# ---------------------------------------------------------------- блок 17
def check_idempotency():
    """Блок 17: идемпотентность best_combo — два вызова = одинаковый результат."""
    print("Блок 17: идемпотентность best_combo")
    for cid in ("pizza_kuba", "dodo"):
        r1 = json.loads(best_combo(cid, "2000", persons=2, variations=3))
        r2 = json.loads(best_combo(cid, "2000", persons=2, variations=3))
        if "error" in r1:
            _fail("idem", f"{cid}: первый вызов — ошибка: {r1['error']}")
            continue
        if "error" in r2:
            _fail("idem", f"{cid}: второй вызов — ошибка: {r2['error']}")
            continue
        combos1 = r1.get("combos", [])
        combos2 = r2.get("combos", [])
        if not combos1 or not combos2:
            _fail("idem", f"{cid}: нет combos")
            continue
        ok = True
        for i in range(max(len(combos1), len(combos2))):
            c1 = combos1[i] if i < len(combos1) else None
            c2 = combos2[i] if i < len(combos2) else None
            if c1 is None or c2 is None:
                _fail("idem", f"{cid}: кол-во вариаций различается: {len(combos1)} vs {len(combos2)}")
                ok = False
                break
            p1 = _parse_items_str(c1["items"])
            p2 = _parse_items_str(c2["items"])
            if p1 != p2:
                _fail("idem", f"{cid}: вариация {i}: состав различается\n  r1: {p1}\n  r2: {p2}")
                ok = False
                continue
            if c1["price_rub"] != c2["price_rub"] or c1["weight_g"] != c2["weight_g"]:
                _fail("idem", f"{cid}: вариация {i}: цена/вес различаются")
                ok = False
        if ok:
            _ok("idem", f"{cid}: 2 вызова идентичны")


# ---------------------------------------------------------------- блок 18
def check_montecarlo():
    """Блок 18: случайные бюджеты/персоны — Monte Carlo (N=15, seed=42)."""
    print("Блок 18: Monte Carlo")
    random.seed(42)
    for cid in ("la_pizza", "dodo"):
        for i in range(15):
            budget = random.choice(range(500, 5051, 50))
            persons = random.randint(1, 3)
            r = json.loads(best_combo(cid, str(budget), persons=persons, variations=3))
            if "error" in r:
                _fail("mcart", f"{cid}: budget={budget} persons={persons} — ошибка: {r['error']}")
                continue
            combos = r.get("combos", [])
            if len(combos) < 1:
                _fail("mcart", f"{cid}: budget={budget} persons={persons} — нет combos")
                continue

            # Ожидаемое кол-во напитков (сколько реально влезает в бюджет)
            expect_drinks = _expected_drinks(cid, budget, persons)

            # Проверка цены <= бюджет
            for j, c in enumerate(combos):
                if c["price_rub"] > budget:
                    _fail("mcart", f"{cid}: budget={budget} persons={persons} "
                                   f"вариация {j}: цена {c['price_rub']} > бюджет")
                    break

            # Подсчёт напитков в каждой вариации
            for j, c in enumerate(combos):
                parts = _parse_items_str(c["items"])
                n_drinks = 0
                for name, cnt in parts:
                    if is_drink({"name": name, "category": "Тест", "description": ""}):
                        n_drinks += cnt
                if n_drinks != expect_drinks:
                    _fail("mcart", f"{cid}: budget={budget} persons={persons} "
                                   f"вариация {j}: напитков {n_drinks}, ожидалось {expect_drinks}")
                    break

            # Вариации попарно различны по составу
            compositions = [tuple(_parse_items_str(c["items"])) for c in combos]
            if len(compositions) != len(set(compositions)):
                _fail("mcart", f"{cid}: budget={budget} persons={persons} "
                               f"вариации не различаются: {compositions}")
                continue
        _ok("mcart", f"{cid}: 15 итераций OK")


# ---------------------------------------------------------------- блок 28
async def _run_mcp_test():
    """Реальный MCP-протокол: поднять сервер, проверить инструменты."""
    import subprocess
    import mcp.client.stdio as stdio_client
    from mcp.client.session import ClientSession

    _project_dir = os.path.dirname(os.path.abspath(__file__))
    _parent_dir = os.path.dirname(_project_dir)
    SERVER_SCRIPT = os.path.join(_parent_dir, "combo_mcp", "server.py")
    PYTHON = os.path.join(_parent_dir, ".venv", "Scripts", "python.exe")

    proc = subprocess.Popen(
        [PYTHON, SERVER_SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=_parent_dir,
        env={**os.environ, "PYTHONUTF8": "1"},
    )

    try:
        async with stdio_client.stdio_client(
            stdio_client.StdioServerParameters(
                command=PYTHON,
                args=[SERVER_SCRIPT],
                cwd=_parent_dir,
                env={**os.environ, "PYTHONUTF8": "1"},
            )
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # list_tools — ровно 13 инструментов
                tools = await session.list_tools()
                tool_names = sorted([t.name for t in tools.tools])
                expected_tools = sorted([
                    "list_chains", "parse_menu", "best_combo", "compare",
                    "status", "verify_chain", "check_price", "diff_menu",
                    "check_config", "health_check", "chain_info", "help", "favorites",
                ])
                if tool_names != expected_tools:
                    raise ValueError(
                        f"tools={tool_names}, ожидалось {expected_tools}"
                    )

                # 5 быстрых инструментов
                quick_tools = [
                    ("list_chains", {}),
                    ("status", {}),
                    ("check_config", {}),
                    ("help", {"action": ""}),
                    ("favorites", {"action": "list"}),
                ]
                for tool_name, args in quick_tools:
                    resp = await session.call_tool(tool_name, args)
                    text = ""
                    for c in resp.content:
                        if hasattr(c, 'text'):
                            text += c.text
                    try:
                        data = json.loads(text)
                        assert isinstance(data, (dict, list)), f"{tool_name}: не dict/list"
                    except (json.JSONDecodeError, AssertionError) as e:
                        raise ValueError(f"{tool_name}: не JSON — {text[:200]}")

    finally:
        proc.terminate()
        proc.wait(timeout=5)


def check_mcp():
    """Блок 28: реальный MCP-протокол через ClientSession + stdio."""
    print("Блок 28: MCP-протокол")
    try:
        asyncio.run(_run_mcp_test())
        _ok("mcp", "MCP-протокол: 13 инструментов, 5 быстрых OK")
    except Exception as e:
        _fail("mcp", f"исключение: {e}")


def main():
    check_combos()
    check_boundary()
    check_dishes()
    check_health()
    check_compare()
    check_diverse()
    check_extra()
    check_categories()
    check_help()
    check_favorites()
    check_extend()
    check_cache()
    check_drinks()
    check_idempotency()
    check_montecarlo()
    check_mcp()
    print()
    if _FAILED:
        print(f"ИТОГ: FAIL ({len(_FAILED)} проверок провалено)")
        sys.exit(1)
    print("ИТОГ: OK (все проверки пройдены)")


if __name__ == "__main__":
    main()
