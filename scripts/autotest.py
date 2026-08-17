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

Запуск: .venv\\Scripts\\python.exe scripts/autotest.py
"""

import json
import os
import re
import sys

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


def main():
    check_combos()
    check_boundary()
    check_dishes()
    check_health()
    check_compare()
    check_diverse()
    check_extra()
    print()
    if _FAILED:
        print(f"ИТОГ: FAIL ({len(_FAILED)} проверок провалено)")
        sys.exit(1)
    print("ИТОГ: OK (все проверки пройдены)")


if __name__ == "__main__":
    main()