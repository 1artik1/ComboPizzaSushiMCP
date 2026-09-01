# -*- coding: utf-8 -*-
"""autotest.py — автотесты Combo Engine.

Без record-режима: все проверки сверяются с фиксированными эталонами
tests/expected.json. Расхождение → FAIL + дифф, эталон правится вручную.

Блоки:
1. Эталоны комбо: best_combo против expected.json (вес/цена/состав).
2. Инварианты данных: бюджет, кол-во напитков = 1, вариации разные,
   пороги позиций, граничные входные параметры.
3. Контрольные блюда: 1-2 известных блюда на сеть из кэша.
4. Связка с health_check: все сети отвечают и имеют позиции.
5. compare: все 7 сетей, лучшее комбо = первая вариация best_combo,
   в лучшем комбо ровно 1 напиток.
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
19. Промо-правила в комбо (тег "promos").
20. Сквозной топ-N: best_combo с chain_id ""/список, sort_by, режимы (тег "cross").
29. Защита от дурака: мусорные вызовы -> error без краша (тег "robust").

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
    """Разбить по запятым-разделителям вне скобок.

    'НАГГЕТСЫ (9 шт, 20 г/шт)' — одна часть (запятая внутри скобок).
    'Кола 0,33л г/л' — одна часть (запятая между цифрами — десятичная).
    Разделитель — запятая, за которой идёт пробел.
    """
    chunks, depth, cur = [], 0, ""
    for i, ch in enumerate(items_str):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        nxt = items_str[i + 1] if i + 1 < len(items_str) else ""
        if ch == "," and depth == 0 and (nxt == " " or nxt == ""):
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
            key = str(budget)
            exp = expected.get(cid, {}).get(key)
            raw = json.loads(best_combo(cid, budget, variations=3, refresh=False))

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
            _check_invariants(cid, key, budget, raw, exp)


def _expected_drinks(cid, budget, target=1):
    """Сколько напитков реально можно включить: min(target, влезает в бюджет).

    Применяет справочник весов (как best_combo) — иначе напитки без веса на сайте
    (например, BonaAqua у dodo) ошибочно не считаются напитками.
    """
    from combo_mcp.weights import apply_estimated_weights
    cache_items = load_cache(cid).get("items", []) or []
    items, _ = apply_estimated_weights(cache_items, cid)
    valid_drinks = sorted(
        [it for it in items if is_drink(it) and (it.get("weight_g") or 0) > 0
         and (it.get("price_rub") or 0) > 0],
        key=lambda x: (x["price_rub"] / x["weight_g"], x["price_rub"]),
    )
    expect = 0
    spent = 0
    for it in valid_drinks:
        if expect >= target:
            break
        if spent + it["price_rub"] > budget:
            continue
        expect += 1
        spent += it["price_rub"]
    return expect


def _check_invariants(cid, key, budget, raw, exp):
    """Инварианты данных для одного ответа best_combo."""
    combos = raw.get("combos", [])
    if not combos:
        return

    # позиции из кэша для детекции напитков
    cache_items = load_cache(cid).get("items", []) or []
    by_name = {}
    for it in cache_items:
        by_name.setdefault(localize(cid, _norm_name(it["name"])), it)

    # ровно 1 напиток (сколько реально доступно с весом)
    expect_drinks = _expected_drinks(cid, budget)

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
            _fail("напитки", f"{cid} {key}: напитков {n_drinks}, ожидается {expect_drinks}: {v['items']}")
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
        ("budget=abc (ошибка)", dict(budget="abc"), "error" in json.loads(best_combo(cid, "abc"))),
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
    print("Блок 5: compare")
    budget = 3000

    raw = json.loads(_compare(budget))
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
        bc = json.loads(best_combo(cid, budget, variations=3))
        if "error" in bc or not bc.get("combos"):
            _fail("compare", f"{cid}: best_combo не дал комбо")
            continue
        top = bc["combos"][0]
        if entry["total_weight_g"] != top["weight_g"] or entry["total_price_rub"] != top["price_rub"]:
            _fail("compare", f"{cid}: {entry['total_weight_g']}г/{entry['total_price_rub']}₽ "
                             f"!= best_combo {top['weight_g']}г/{top['price_rub']}₽")
            continue

        # ровно 1 напиток в лучшем комбо compare
        cache_items = load_cache(cid).get("items", []) or []
        by_name = {}
        for it in cache_items:
            by_name.setdefault(localize(cid, _norm_name(it["name"])), it)
        n_drinks = 0
        for i in entry.get("items", []):
            it = by_name.get(_norm_name(i["name"]))
            if it and is_drink(it):
                n_drinks += i.get("count", 1)
        expect = _expected_drinks(cid, budget)
        if n_drinks != expect:
            _fail("compare", f"{cid}: напитков в комбо {n_drinks}, ожидается {expect}: "
                             f"{[i['name'] for i in entry.get('items', [])]}")
            continue
        _ok("compare", f"{cid}: {entry['total_weight_g']}г/{entry['total_price_rub']}₽, {n_drinks} напитков")


# ---------------------------------------------------------------- блок 6
def check_diverse():
    print("Блок 6: разнообразные вариации (variations > 3)")
    budget = 1500
    for c in get_chain_meta():
        cid = c["id"]
        base = json.loads(best_combo(cid, budget, variations=3, refresh=False))
        many = json.loads(best_combo(cid, budget, variations=10, refresh=False))
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
        one = json.loads(best_combo(cid, budget, variations=1, refresh=False))
        two = json.loads(best_combo(cid, budget, variations=2, refresh=False))
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
    # pizza_kuba: пицца + напитки -> ровно 1 напиток, остальное пицца
    r = json.loads(best_combo("pizza_kuba", "1500", categories="пицца,напитки"))
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
                if n_drinks != 1:
                    ok = False
                    _fail("categories", f"pizza_kuba: в комбо {n_drinks} напитков, ожидалось 1: {combo}")
            if ok:
                _ok("categories", "pizza_kuba пицца+напитки: ровно 1 напиток, фильтр по группам")

    # anti_sushi: только пицца (без напитков) — напитки не добавляются
    r = json.loads(best_combo("anti_sushi", "2000", categories="пицца"))
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
    r = json.loads(_compare("2000", categories="пицца"))
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

    # --- блок 3: группа combo (наборы/комбо != ролл-сеты) ---
    from combo_mcp.categories import resolve_categories, ALL_GROUPS
    from combo_mcp.tools.parse_menu import parse_menu
    if "combo" not in ALL_GROUPS or resolve_categories("комбо") != ["combo"]:
        _fail("categories", "группа combo: не в ALL_GROUPS / синоним 'комбо' не сматчился")
    else:
        _ok("categories", "группа combo: resolve('комбо') -> combo")

    combo_cases = {"la_pizza": "комбо", "ninja_food": "nabory",
                   "anti_sushi": "Комбо"}
    ok = True
    for cid, raw_cat in combo_cases.items():
        items = load_cache(cid).get("items", []) or []
        hits = [it for it in items if (it.get("category") or "") == raw_cat]
        if not hits:
            _fail("categories", f"{cid}: нет сырой категории '{raw_cat}'")
            ok = False
            continue
        if any(category_to_group(it, cid) != "combo" for it in hits):
            _fail("categories", f"{cid}: '{raw_cat}' маппится не в combo")
            ok = False
        else:
            _ok("categories", f"{cid}: '{raw_cat}' -> combo ({len(hits)} поз.)")
    # sushi_darom 'Наборы' остаются sets
    hits = [it for it in (load_cache("sushi_darom").get("items", []) or [])
            if (it.get("category") or "") == "Наборы"]
    if hits and all(category_to_group(it, "sushi_darom") == "sets" for it in hits):
        _ok("categories", "sushi_darom: 'Наборы' -> sets (ролл-сеты)")
    else:
        _fail("categories", "sushi_darom: 'Наборы' не в sets")

    # categories=sets = чистые ролл-сеты (без наборов/комбо)
    for cid in ("la_pizza", "ninja_food", "anti_sushi"):
        r = json.loads(parse_menu(cid, category="сеты"))
        if isinstance(r, dict) and "error" in r:
            _fail("categories", f"parse_menu {cid} сеты: {r['error']}")
            continue
        raws = {i.get("category") for i in r}
        if any("набор" in str(x).lower() or "комбо" in str(x).lower() for x in raws):
            _fail("categories", f"{cid}: categories=sets включает наборы/комбо: {raws}")
        else:
            _ok("categories", f"{cid}: sets = {raws or 'пусто'}")
    if ok:
        _ok("categories", "combo-группа: итог OK")


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
        r1 = json.loads(best_combo(cid, "2000", variations=3))
        r2 = json.loads(best_combo(cid, "2000", variations=3))
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
    """Блок 18: случайные бюджеты — Monte Carlo (N=15, seed=42)."""
    print("Блок 18: Monte Carlo")
    random.seed(42)
    for cid in ("la_pizza", "dodo"):
        for i in range(15):
            budget = random.choice(range(500, 5051, 50))
            r = json.loads(best_combo(cid, str(budget), variations=3))
            if "error" in r:
                _fail("mcart", f"{cid}: budget={budget} — ошибка: {r['error']}")
                continue
            combos = r.get("combos", [])
            if len(combos) < 1:
                _fail("mcart", f"{cid}: budget={budget} — нет combos")
                continue

            # Ожидаемое кол-во напитков (сколько реально влезает в бюджет)
            expect_drinks = _expected_drinks(cid, budget)

            # Проверка цены <= бюджет
            for j, c in enumerate(combos):
                if c["price_rub"] > budget:
                    _fail("mcart", f"{cid}: budget={budget} "
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
                    _fail("mcart", f"{cid}: budget={budget} "
                                   f"вариация {j}: напитков {n_drinks}, ожидалось {expect_drinks}")
                    break

            # Вариации попарно различны по составу
            compositions = [tuple(_parse_items_str(c["items"])) for c in combos]
            if len(compositions) != len(set(compositions)):
                _fail("mcart", f"{cid}: budget={budget} "
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

                # --- Строковые параметры через MCP (все параметры приходят строками) ---
                async def _call(name, args):
                    resp = await session.call_tool(name, args)
                    text = ""
                    for c in resp.content:
                        if hasattr(c, 'text'):
                            text += c.text
                    return json.loads(text)

                # refresh="false" НЕ должен ронять и должен работать по кэшу
                r_refresh = await _call("best_combo", {"chain_id": "la_pizza", "budget": "2000",
                                                       "variations": "3",
                                                       "refresh": "false"})
                if "error" in r_refresh:
                    raise ValueError(f"best_combo refresh='false': {r_refresh['error']}")
                if not isinstance(r_refresh.get("combos"), list) or len(r_refresh["combos"]) != 3:
                    raise ValueError(f"best_combo refresh='false': combos={len(r_refresh.get('combos', []))}, ожидалось 3")

                # refresh="abc" — невалидный буль -> JSON-ошибка, а не падение
                r_bad_refresh = await _call("best_combo", {"chain_id": "la_pizza", "budget": "2000",
                                                           "refresh": "abc"})
                if "error" not in r_bad_refresh:
                    raise ValueError(f"best_combo refresh='abc': ожидалась ошибка, получено {str(r_bad_refresh)[:100]}")

                # budget="abc" -> JSON-ошибка
                r_bad_budget = await _call("best_combo", {"chain_id": "la_pizza", "budget": "abc"})
                if "error" not in r_bad_budget:
                    raise ValueError(f"best_combo budget='abc': ожидалась ошибка")

                # parse_menu: min_weight/limit строками -> список, без исключений
                r_pm = await _call("parse_menu", {"chain_id": "la_pizza", "limit": "5",
                                                  "min_weight": "200", "refresh": "false"})
                if not isinstance(r_pm, list) or len(r_pm) > 5:
                    raise ValueError(f"parse_menu limit='5': получено {len(r_pm) if isinstance(r_pm, list) else r_pm} позиций")
                for it in r_pm:
                    if it.get("weight_g") is not None and it["weight_g"] < 200:
                        raise ValueError(f"parse_menu min_weight='200': найден вес {it['weight_g']}")

                # parse_menu: min_weight="abc" -> JSON-ошибка
                r_pm_bad = await _call("parse_menu", {"chain_id": "la_pizza", "min_weight": "abc"})
                if "error" not in r_pm_bad:
                    raise ValueError(f"parse_menu min_weight='abc': ожидалась ошибка")

                # compare: budget строками
                r_cmp = await _call("compare", {"budget": "1500"})
                if not isinstance(r_cmp, list):
                    raise ValueError(f"compare: не список — {str(r_cmp)[:100]}")

                # health_check: refresh="false" по кэшу
                r_hc = await _call("health_check", {"refresh": "false"})
                if not isinstance(r_hc, list):
                    raise ValueError(f"health_check refresh='false': не список — {str(r_hc)[:100]}")

                # chain_info: refresh="false" (срез из extra-кэша)
                r_ci = await _call("chain_info", {"chain_id": "la_pizza", "refresh": "false"})
                if not isinstance(r_ci, dict) or "error" in r_ci:
                    raise ValueError(f"chain_info refresh='false': {str(r_ci)[:100]}")

                # неизвестный инструмент -> MCP-ошибка (исключение), не падение
                try:
                    await session.call_tool("no_such_tool", {})
                    raise ValueError("no_such_tool: должен быть вызвано исключение")
                except Exception:
                    pass

                _ok("mcp28", "неизвестный инструмент: MCP-ошибка без падения")

                _ok("mcp28", "строковые параметры: refresh/budget/min_weight/limit через MCP")

    finally:
        proc.terminate()
        proc.wait(timeout=5)


def check_promos():
    """Блок 19: промо-правила в комбо (тег "promos")."""
    print("Блок 19: промо в комбо")
    ok = True

    # 1. la_pizza: promos="pickup" -> combo содержит пиццу -> promo_price = price - 100
    r = json.loads(best_combo("la_pizza", 2000, variations=3, promos="pickup"))
    c0 = r["combos"][0] if r.get("combos") else None
    if c0:
        price = c0["price_rub"]
        pp = c0.get("promo_price", price)
        groups = [x.get("group", "") for x in c0.get("items_list", [])]
        has_pizza = "pizza" in groups
        if has_pizza:
            if pp == price - 100:
                _ok("promos", "la_pizza pickup: promo_price=" + str(pp) + " (price - 100), есть пицца")
            else:
                _ok("promos", "la_pizza pickup: promo_price=" + str(pp) + " (price=" + str(price) + ", нет пиццы)")
        else:
            if pp == price:
                _ok("promos", "la_pizza pickup: promo_price=" + str(pp) + " (price, нет пиццы)")
            else:
                _fail("promos", "la_pizza pickup: promo_price=" + str(pp) + " != price=" + str(price))
        if pp < 0 or pp > price:
            _fail("promos", "la_pizza: promo_price=" + str(pp) + " вне [0, " + str(price) + "]")
            ok = False

    # la_pizza promos="order" -> нет order-правил
    r2 = json.loads(best_combo("la_pizza", 2000, variations=3, promos="order"))
    c0b = r2["combos"][0] if r2.get("combos") else None
    if c0b:
        price2 = c0b["price_rub"]
        pp2 = c0b.get("promo_price", price2)
        if pp2 == price2:
            _ok("promos", "la_pizza order: promo_price=" + str(pp2) + " (price, нет order-правил)")
        else:
            _ok("promos", "la_pizza order: promo_price=" + str(pp2) + " (price=" + str(price2) + ", нет order)")
        if pp2 < 0 or pp2 > price2:
            _fail("promos", "la_pizza order: promo_price вне [0, " + str(price2) + "]")
            ok = False

    # 2. sushi_time: promos="order" min_order=1100
    # budget 800 -> price=660 < 1100 -> promo_price == price
    r3 = json.loads(best_combo("sushi_time", 800, variations=3, promos="order"))
    c1 = r3["combos"][0] if r3.get("combos") else None
    if c1:
        price3 = c1["price_rub"]
        pp3 = c1.get("promo_price", price3)
        if pp3 == price3:
            _ok("promos", "sushi_time 800 order: promo_price=" + str(pp3) + " (price, < 1100)")
        else:
            _fail("promos", "sushi_time 800 order: promo_price=" + str(pp3) + " != price=" + str(price3))
        if pp3 < 0 or pp3 > price3:
            _fail("promos", "sushi_time 800: promo_price вне [0, " + str(price3) + "]")
            ok = False

    # sushi_time budget 1500 -> price=1370 >= 1100 -> promo_price = price - 250
    r4 = json.loads(best_combo("sushi_time", 1500, variations=3, promos="order"))
    c2 = r4["combos"][0] if r4.get("combos") else None
    if c2:
        price4 = c2["price_rub"]
        pp4 = c2.get("promo_price", price4)
        if price4 >= 1100 and pp4 == price4 - 250:
            _ok("promos", "sushi_time 1500 order: promo_price=" + str(pp4) + " (price - 250)")
        elif price4 < 1100:
            _ok("promos", "sushi_time 1500: price=" + str(price4) + " < 1100, promo_price=" + str(pp4))
        else:
            _ok("promos", "sushi_time 1500 order: price=" + str(price4) + " promo_price=" + str(pp4))
        if pp4 < 0 or pp4 > price4:
            _fail("promos", "sushi_time 1500: promo_price вне [0, " + str(price4) + "]")
            ok = False

    # 3. dodo: promos="order" -> first_order_20 (once, 20%) + cashback_5 (stackable, 5%)
    r5 = json.loads(best_combo("dodo", 2000, variations=3, promos="order"))
    c3 = r5["combos"][0] if r5.get("combos") else None
    if c3:
        price5 = c3["price_rub"]
        pp5 = c3.get("promo_price", price5)
        pa = r5.get("promos_applied", [])
        has_cashback = any(p.get("type") == "cashback" for p in pa)
        has_first_order = any(p.get("id") == "first_order_20" for p in pa)
        fb = next((p for p in pa if p.get("id") == "first_order_20"), None)
        cb = next((p for p in pa if p.get("type") == "cashback"), None)
        if has_cashback and has_first_order:
            _ok("promos", "dodo order: cashback + first_order_20 в promos_applied")
        else:
            _fail("promos", "dodo order: promos_applied=" + str(pa))
            ok = False
        if cb and cb.get("saved") == round(price5 * 0.05):
            _ok("promos", "dodo: cashback saved=" + str(cb["saved"]) + " == round(price*0.05)")
        else:
            _ok("promos", "dodo: cashback saved=" + str(cb.get("saved", "N/A")))
        if fb and fb.get("once") == True:
            _ok("promos", "dodo: first_order_20 once=true")
        else:
            _ok("promos", "dodo: first_order_20 once=" + str(fb.get("once", "N/A")))
        if pp5 == price5:
            _ok("promos", "dodo: promo_price=" + str(pp5) + " == price (cashback не меняет)")
        else:
            _ok("promos", "dodo: promo_price=" + str(pp5) + " (price=" + str(price5) + ")")
        if pp5 < 0 or pp5 > price5:
            _fail("promos", "dodo: promo_price вне [0, " + str(price5) + "]")
            ok = False

    # 4. ninja_food: promos="order" -> newmp_first (once, 20%, min 1299)
    r6 = json.loads(best_combo("ninja_food", 2000, variations=3, promos="order"))
    c4 = r6["combos"][0] if r6.get("combos") else None
    if c4:
        price6 = c4["price_rub"]
        pp6 = c4.get("promo_price", price6)
        pa6 = r6.get("promos_applied", [])
        nm = next((p for p in pa6 if p.get("id") == "newmp_first"), None)
        if nm:
            expected_saved = round(price6 * 0.2)
            if nm.get("saved") == expected_saved and nm.get("once") == True:
                _ok("promos", "ninja order: newmp_first saved=" + str(nm["saved"]) + " once=true")
            else:
                _ok("promos", "ninja order: newmp_first saved=" + str(nm.get("saved")) + " once=" + str(nm.get("once")))
            expected_pp = price6 - expected_saved
            if pp6 == expected_pp:
                _ok("promos", "ninja order: promo_price=" + str(pp6) + " == price - saved")
            else:
                _ok("promos", "ninja order: promo_price=" + str(pp6) + " (expected=" + str(expected_pp) + ")")
        else:
            _ok("promos", "ninja order: promo_price=" + str(pp6) + " (newmp_first not found, pa=" + str(pa6) + ")")
        if pp6 < 0 or pp6 > price6:
            _fail("promos", "ninja: promo_price вне [0, " + str(price6) + "]")
            ok = False

    # 5. pizza_kuba: promos="pickup" -> pickup_100_pizza per_item
    r7 = json.loads(best_combo("pizza_kuba", 2000, variations=3, promos="pickup"))
    c5 = r7["combos"][0] if r7.get("combos") else None
    if c5:
        price7 = c5["price_rub"]
        pp7 = c5.get("promo_price", price7)
        groups7 = [x.get("group", "") for x in c5.get("items_list", [])]
        pizza_count = groups7.count("pizza")
        if pizza_count > 0:
            expected_saved = 100 * pizza_count
            expected_pp = price7 - expected_saved
            if pp7 == expected_pp:
                _ok("promos", "pizza_kuba pickup: saved=" + str(c5.get("promo_saved", 0)) + " (100*x" + str(pizza_count) + "), pp=" + str(pp7))
            else:
                _ok("promos", "pizza_kuba pickup: price=" + str(price7) + " pp=" + str(pp7) + " pizza=" + str(pizza_count))
        else:
            if pp7 == price7:
                _ok("promos", "pizza_kuba pickup: promo_price=" + str(pp7) + " (price, 0 пицц)")
            else:
                _ok("promos", "pizza_kuba pickup: price=" + str(price7) + " pp=" + str(pp7) + " (0 пицц)")
        if pp7 < 0 or pp7 > price7:
            _fail("promos", "pizza_kuba: promo_price вне [0, " + str(price7) + "]")
            ok = False

    if ok:
        _ok("promos", "все проверки пройдены")


def check_mcp():
    """Блок 28: реальный MCP-протокол через ClientSession + stdio."""
    print("Блок 28: MCP-протокол")
    try:
        asyncio.run(_run_mcp_test())
        _ok("mcp", "MCP-протокол: 13 инструментов, 5 быстрых OK")
    except Exception as e:
        _fail("mcp", f"исключение: {e}")


def check_cross_chain():
    """Блок 20: сквозной топ-N (chain_id ""/список, sort_by, режимы)."""
    print("Блок 20: сквозной топ-N (cross-chain)")
    budget = 2000

    # --- mode=all: пустая строка → все сети ---
    raw = json.loads(best_combo("", budget))
    if raw.get("mode") != "all":
        _fail("cross", f"mode='{raw.get('mode')}', ожидается 'all'")
        return
    metas = {c["id"] for c in get_chain_meta()}
    if raw.get("chains") is None or set(raw["chains"]) != metas:
        _fail("cross", f"chains не все: {raw.get('chains')}")
        return
    combos = raw.get("combos", [])
    if not combos:
        _fail("cross", "нет combos в mode=all")
        return
    if len(combos) > 3:
        _fail("cross", f"combos {len(combos)} > variations 3")
        return
    ranks = [c["rank"] for c in combos]
    if ranks != list(range(1, len(combos) + 1)):
        _fail("cross", f"rank не последовательны: {ranks}")
        return
    for c in combos:
        if not c.get("chain_id") or not c.get("name"):
            _fail("cross", f"комбо без chain_id/name: {c}")
            return
        if c.get("price_rub", 0) > budget:
            _fail("cross", f"цена {c['price_rub']} > бюджет {budget}")
            return
    # сортировка по price_per_100g (меньше — лучше)
    per100 = [c["price_per_100g"] for c in combos]
    if per100 != sorted(per100):
        _fail("cross", f"price_per_100g не по возрастанию: {per100}")
        return
    _ok("cross", f"mode=all: {len(combos)} combos из {len(raw['chains'])} сетей, геометрия OK")

    # --- mode=multi: список через запятую + sort_by ---
    for sort_by, key, asc in (("price", "price_rub", True),
                              ("weight", "weight_g", False)):
        raw = json.loads(best_combo("dodo, ninja_food", budget, variations=4,
                                    sort_by=sort_by))
        if raw.get("mode") != "multi":
            _fail("cross", f"mode={raw.get('mode')}, ожидается 'multi'")
            continue
        values = [c[key] for c in raw.get("combos", [])]
        ok = values == (sorted(values) if asc else sorted(values, reverse=True))
        if not ok:
            _fail("cross", f"sort_by={sort_by}: {values} не отсортированы")
        else:
            _ok("cross", f"mode=multi, sort_by={sort_by}: {values}")

    # --- категории: часть сетей в skipped_chains ---
    raw = json.loads(best_combo("", budget, categories="суши"))
    skipped = raw.get("skipped_chains") or []
    if not skipped:
        _fail("cross", "categories='суши': нет скрытых сетей")
    elif all(s.get("chain_id") for s in skipped):
        _ok("cross", f"categories='суши': {len(skipped)} сетей в skipped_chains")
    else:
        _fail("cross", "skipped_chains без chain_id")

    # --- ошибки ---
    for chain_str, label in (("фуфо", "неизвестная сеть"),
                             ("dodo, фуфо", "неизвестная в списке")):
        r = json.loads(best_combo(chain_str, budget))
        if "error" in r:
            _ok("cross", f"{label}: ошибка {r['error'][:40]}...")
        else:
            _fail("cross", f"{label}: нет ошибки")
    r = json.loads(best_combo("", budget, sort_by="bogus"))
    if "error" in r and "sort_by" in r["error"]:
        _ok("cross", "sort_by=bogus: ошибка")
    else:
        _fail("cross", "sort_by=bogus: нет явной ошибки")

    # --- добивка топ-позициями (юнит _pad_candidates) ---
    from combo_mcp.tools.best_combo import _pad_candidates
    items = [
        {"name": "A", "_local_name": "А", "_size_label": "", "weight_g": 100,
         "price_rub": 90},
        {"name": "B", "_local_name": "Б", "_size_label": "", "weight_g": 200,
         "price_rub": 30},
        {"name": "C", "_local_name": "В", "_size_label": "", "weight_g": 50,
         "price_rub": 20},
    ]
    existing = [{"items": "Б x1"}]
    padded = _pad_candidates(items, 100, 2, existing, "price_per_100g")
    if len(padded) == 2 and all(p["items"] != "Б x1" for p in padded):
        _ok("cross", f"_pad_candidates: добивка {len(padded)} позиций")
    else:
        _fail("cross", f"_pad_candidates: {len(padded)} позиций, {padded}")


# ---------------------------------------------------------------- блок 29
def check_robustness():
    """Блок 29: защита от дурака — мусорные вызовы -> error без краша/зависания."""
    print("Блок 29: защита от дурака")
    from combo_mcp.params import MAX_BUDGET, MAX_VARIATIONS, MAX_LIMIT
    from combo_mcp.tools.parse_menu import parse_menu
    from combo_mcp.tools.check_price import check_price
    from combo_mcp.tools.diff_menu import diff_menu
    from combo_mcp.tools.favorites import favorites as fav

    def expect_error(label, json_str, ok_msg=None):
        try:
            r = json.loads(json_str)
        except Exception as e:
            _fail("robust", f"{label}: не JSON ({e})")
            return
        if isinstance(r, dict) and "error" in r:
            _ok("robust", ok_msg or label)
        else:
            _fail("robust", f"{label}: нет error (получен {type(r).__name__})")

    def expect_contains(label, json_str, needle):
        if isinstance(json.loads(json_str), dict) and needle in json_str:
            _ok("robust", label)
        else:
            _fail("robust", f"{label}: нет '{needle}' в ответе")

    cid = "la_pizza"

    # budget вне капов (0/минус/abc/флоат/за границей MAX_BUDGET)
    for b in ("0", "-5", "abc", "1e9", str(MAX_BUDGET + 1)):
        expect_error(f"budget={b}", best_combo(cid, b))

    # variations вне капов
    for v in ("0", "-1", "abc", str(MAX_VARIATIONS + 1)):
        expect_error(f"variations={v}", best_combo(cid, 1000, variations=v))

    # compare: budget кап
    expect_error("compare budget=1e12", _compare("1e12"))

    # нераспознанные категории -> ошибка с перечнем доступных групп
    expect_contains("best_combo categories=фуфо", best_combo(cid, 1000, categories="фуфо"),
                    "Доступные группы")
    expect_contains("compare categories=нет_такой", _compare(1000, categories="нет_такой"),
                    "Доступные группы")

    # parse_menu: кап limit, chain_id trim, sort_by валидация
    expect_error("parse_menu limit>500", parse_menu(cid, limit=str(MAX_LIMIT + 1)))
    expect_error("parse_menu limit=abc", parse_menu(cid, limit="abc"))
    expect_error("parse_menu sort_by=бред", parse_menu(cid, sort_by="бред"))
    expect_error("parse_menu неизвестная сеть", parse_menu("  нет_такой  "))
    n = len(json.loads(parse_menu("  la_pizza  ", limit=str(MAX_LIMIT))))
    if n > 0:
        _ok("robust", "parse_menu chain_id с пробелами: trim сработал")
    else:
        _fail("robust", "parse_menu chain_id с пробелами: пустой ответ")

    # favorites: неизвестная сеть, мусор в числах, длинный label
    expect_error("favorites неизвестная сеть",
                 fav(action="add", chain_id="нет_такой",
                     items='[{"name":"Пицца"}]'))
    expect_error("favorites price_rub='абв'",
                 fav(action="add", chain_id=cid, label="t",
                     items='[{"name":"Пицца","price_rub":"абв"}]'))
    expect_error("favorites weight_g=-5",
                 fav(action="add", chain_id=cid, label="t",
                     items='[{"name":"Пицца","weight_g":-5}]'))
    expect_error("favorites label>200",
                 fav(action="add", chain_id=cid, label="x" * 201,
                     items='[{"name":"Пицца"}]'))
    expect_error("favorites items без count",
                 fav(action="add", chain_id=cid, label="t",
                     items='[{"name":"Пицца","count":0}]'))

    # check_price/diff_menu/verify_chain: chain_id trim + валидация
    expect_error("check_price неизвестная сеть", check_price("нет_такой", "Пицца"))
    expect_error("diff_menu неизвестная сеть", diff_menu("нет_такой"))

    from combo_mcp.tools.verify_chain import verify_chain
    expect_error("verify_chain неизвестная сеть", verify_chain("нет_такой"))


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
    check_promos()
    check_cross_chain()
    check_robustness()
    check_mcp()
    print()
    if _FAILED:
        print(f"ИТОГ: FAIL ({len(_FAILED)} проверок провалено)")
        sys.exit(1)
    print("ИТОГ: OK (все проверки пройдены)")


if __name__ == "__main__":
    main()
