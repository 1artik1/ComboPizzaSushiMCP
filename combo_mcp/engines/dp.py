# -*- coding: utf-8 -*-
"""dp.py — solve_max_weight_single, solve_max_weight_double, _pareto_dominates,
_pareto_filter, format_combo, solve_optimum, _solve_optimum_pareto, calculate_combos.

Перенос 1:1 из combo_engine.py.
"""

import random
import time
from collections import Counter
from combo_mcp.engines.taste import count_ingredients
from combo_mcp.engines.drinks import is_drink


def solve_max_weight_single(items, budget):
    """Each item at most 1x. Max weight within budget."""
    dp = [(-1, []) for _ in range(budget + 1)]
    dp[0] = (0, [])
    for i, item in enumerate(items):
        cost = item["price_rub"]
        w = item["weight_g"]
        if cost > budget or cost == 0:
            continue
        for j in range(budget, cost - 1, -1):
            prev_weight, prev_indices = dp[j - cost]
            if prev_weight >= 0:
                new_weight = prev_weight + w
                if new_weight > dp[j][0]:
                    dp[j] = (new_weight, prev_indices + [i])
    best_w = 0
    best_indices = []
    for j in range(budget + 1):
        w, indices = dp[j]
        if w > best_w:
            best_w = w
            best_indices = indices
    return best_indices, best_w


def solve_max_weight_double(items, budget):
    """Each item up to 2x. Max weight within budget.

    DP stores full history in states: dp[j] = (weight, history),
    where history is a list of (item_idx, copies) pairs.
    """
    # dp[j] = (weight, history) where history = [(idx, copies), ...]
    dp = [(-1, [])] * (budget + 1)
    dp[0] = (0, [])

    for i, item in enumerate(items):
        cost = item["price_rub"]
        w = item["weight_g"]
        if cost <= 0 or cost > budget:
            continue
        for _ in range(2):
            for j in range(budget, cost - 1, -1):
                prev_w, prev_hist = dp[j - cost]
                if prev_w >= 0:
                    new_w = prev_w + w
                    if new_w > dp[j][0]:
                        new_hist = list(prev_hist) + [(i, 1)]
                        dp[j] = (new_w, new_hist)

    best_j = 0
    for j in range(budget + 1):
        if dp[j][0] > dp[best_j][0]:
            best_j = j

    _, hist = dp[best_j]
    # Build counts from history
    counts = Counter()
    for idx, cnt in hist:
        counts[idx] += cnt
    final = [(idx, cnt) for idx, cnt in counts.items()]
    total_weight = dp[best_j][0]
    return final, total_weight, best_j


def _pareto_dominates(a, b):
    """Return True if tuple a dominates tuple b.
    a dominates b if a has >= weight AND >= taste_sum AND <= count,
    with at least one strict improvement.
    (Fewer items is better because score = weight * (taste_sum / count).)
    """
    return (a[0] >= b[0] and a[1] >= b[1] and a[2] <= b[2]
            and (a[0] > b[0] or a[1] > b[1] or a[2] < b[2]))


def _pareto_filter(states):
    """Remove dominated states from a list of (weight, taste_sum, count, history) tuples."""
    if not states:
        return []
    # Sort by weight desc, then taste_sum desc, then count asc
    states = sorted(states, key=lambda x: (-x[0], -x[1], x[2]))
    result = []
    for s in states:
        dominated = False
        for r in result:
            if _pareto_dominates(r, s):
                dominated = True
                break
        if not dominated:
            result.append(s)
    return result


def format_combo(items, indices, budget):
    """Format combo string."""
    total_weight = 0
    total_price = 0
    parts = []
    for item_idx, count in indices:
        item = items[item_idx]
        total_weight += item["weight_g"] * count
        total_price += item["price_rub"] * count
        label = item.get("_size_label", "")
        display_name = item.get("_local_name") or item["name"]
        name = f"{display_name} ({label})" if label else display_name
        if count == 1:
            parts.append(f"{name} x1")
        else:
            parts.append(f"{name} x{count}")
    price_per_100 = total_price / total_weight * 100 if total_weight > 0 else 0
    line = f"{total_weight} g | {total_price} rub | {price_per_100:.1f} rub/100g | {', '.join(parts)}"
    return line


def solve_optimum(items, budget):
    """Exclude items with taste=0. Maximize weight * avg_taste.

    Uses Pareto-optimal DP. Items without valid weight_g are excluded.
    For large item sets, only top-N items by taste are used to avoid
    O(n * budget * states) explosion.
    """
    # Filter: must have valid weight_g > 0 AND taste > 0
    filtered = []
    for idx, item in enumerate(items):
        w = item.get("weight_g")
        if w is None or w <= 0:
            continue
        taste = item.get("_taste", 0)
        if taste > 0:
            filtered.append((idx, item))

    if not filtered:
        # Fallback: use solve_max_weight_double with all valid-weight items
        valid = [i for i, it in enumerate(items) if it.get("weight_g") and it["weight_g"] > 0]
        if not valid:
            return [], 0, 0
        valid_items = [items[i] for i in valid]
        indices, weight, cost = solve_max_weight_double(valid_items, budget)
        # Map back to original indices (indices are into valid_items, need original item indices)
        if indices:
            final = [(valid[i], cnt) for i, cnt in indices]
        else:
            final = []
        return final, weight, cost

    # Limit to top 40 items by taste to keep DP tractable
    filtered.sort(key=lambda x: x[1].get("_taste", 0), reverse=True)
    filtered = filtered[:40]

    return _solve_optimum_pareto(items, budget, filtered)


def _solve_optimum_pareto(items, budget, filtered):
    """Pareto-optimal DP for solve_optimum.

    For each cost c, store all non-dominated (weight, taste_sum, count) tuples.
    Domination: a dominates b if a has >= weight AND >= taste_sum AND <= count,
    with at least one strict improvement.
    """
    # dp[c] = list of Pareto-optimal (weight, taste_sum, count, history)
    dp = {0: [(0, 0, 0, [])]}

    for fi, (orig_idx, item) in enumerate(filtered):
        cost = item["price_rub"]
        w = item["weight_g"]
        t = item["_taste"]
        if cost <= 0 or cost > budget:
            continue
        for copies in range(1, 3):
            item_cost = cost * copies
            item_w = w * copies
            item_t = t * copies
            item_cnt = copies
            # Collect new states to add
            new_states = []
            for c in range(budget + 1 - item_cost):
                if c not in dp:
                    continue
                for state in dp[c]:
                    old_w, old_ts, old_cnt, hist = state
                    new_hist = hist + [(orig_idx, copies)]
                    new_w = old_w + item_w
                    new_ts = old_ts + item_t
                    new_cnt = old_cnt + item_cnt
                    new_states.append((new_w, new_ts, new_cnt, new_hist, c + item_cost))
            # Merge new states into dp
            for new_w, new_ts, new_cnt, new_hist, target_c in new_states:
                if target_c not in dp:
                    dp[target_c] = []
                dp[target_c].append((new_w, new_ts, new_cnt, new_hist))
                # Pareto-filter at this cost
                dp[target_c] = _pareto_filter(dp[target_c])

    # Find best score across all costs <= budget
    best_score = 0
    best_state = None
    for c in range(budget + 1):
        if c not in dp:
            continue
        for state in dp[c]:
            w, ts, cnt, hist = state
            if cnt == 0:
                continue
            score = w * (ts / cnt)
            if score > best_score or (score == best_score and w > (best_state[0] if best_state else 0)):
                best_score = score
                best_state = state

    if best_state is None:
        return solve_max_weight_double(items, budget)

    _, _, _, hist = best_state
    # Build counts from history, respecting the count in each (idx, cnt) pair
    counts = Counter()
    for idx, cnt in hist:
        counts[idx] += cnt
    total_weight = best_state[0]
    total_cost = 0
    for idx, cnt in counts.items():
        total_cost += items[idx]["price_rub"] * cnt
    final = [(idx, cnt) for idx, cnt in counts.items()]
    return final, total_weight, total_cost


def _valid(item):
    """Позиция пригодна для расчёта: цена и вес > 0."""
    return (item.get("weight_g") or 0) > 0 and (item.get("price_rub") or 0) > 0


def select_drinks(items, persons, budget):
    """Выбрать ровно persons напитков: самые выгодные по г/₽, сумма ≤ budget.

    Возвращает список (idx, count) пар по исходному списку items.
    Если напитков меньше persons — берутся все подходящие.
    """
    drinks = [(i, it) for i, it in enumerate(items) if _valid(it) and is_drink(it)]
    drinks.sort(key=lambda x: (x[1]["price_rub"] / x[1]["weight_g"], x[1]["price_rub"]))
    picked = []
    spent = 0
    for i, it in drinks:
        if len(picked) >= persons:
            break
        if spent + it["price_rub"] > budget:
            continue
        picked.append((i, 1))
        spent += it["price_rub"]
    return picked, spent


def _combo_variants(items, budget, persons=1):
    """Сгенерировать до 6 стратегий комбо: список строк в порядке
    Оптимум → Без повторов → Макс. вес → ... (см. _STRATEGIES).
    """
    drinks = [(i, it) for i, it in enumerate(items) if _valid(it) and is_drink(it)]
    food = [(i, it) for i, it in enumerate(items) if _valid(it) and not is_drink(it)]
    food_items = [it for _, it in food]

    drink_pairs, drink_spent = select_drinks(items, persons, budget)
    food_budget = budget - drink_spent

    variants = []

    def _build(strategy):
        pairs = list(drink_pairs)
        if strategy == "optimum":
            indices, w, cost = solve_optimum(food_items, food_budget)
            pairs += [(food[i][0], cnt) for i, cnt in indices]
        elif strategy == "no_duplicates":
            indices, w = solve_max_weight_single(food_items, food_budget)
            pairs += [(food[i][0], 1) for i in indices]
        elif strategy == "max_weight":
            indices, w, cost = solve_max_weight_double(food_items, food_budget)
            pairs += [(food[i][0], cnt) for i, cnt in indices]
        elif strategy == "fewest_items":
            # Максимум веса при минимуме позиций: жадный по весу, по 1 шт,
            # поверх persons напитков.
            cand = sorted(food, key=lambda x: (-x[1]["weight_g"], x[1]["price_rub"]))
            spent = sum(items[i]["price_rub"] * c for i, c in drink_pairs)
            for i, it in cand:
                if spent + it["price_rub"] <= budget:
                    pairs.append((i, 1))
                    spent += it["price_rub"]
        else:
            return None

        if not pairs:
            return None
        return format_combo(items, pairs, budget)

    strategies = ["optimum", "no_duplicates", "max_weight", "fewest_items"]
    for s in strategies:
        if len(variants) >= 3:
            break
        line = _build(s)
        if line and line not in variants:
            variants.append(line)
    return variants


def _extra_variant(items, budget, strategy, persons=1):
    """Дополнительные стратегии для variations > 3 (без гарантий persons)."""
    if strategy == "no_drinks_max":
        food = [(i, it) for i, it in enumerate(items) if _valid(it) and not is_drink(it)]
        indices, w, cost = solve_max_weight_double([it for _, it in food], budget)
        pairs = [(food[i][0], cnt) for i, cnt in indices]
        return format_combo(items, pairs, budget)
    if strategy == "drinks_only":
        cand = [(i, it) for i, it in enumerate(items) if _valid(it) and is_drink(it)]
        cand.sort(key=lambda x: (x[1]["price_rub"], -x[1]["weight_g"]))
        pairs = []
        spent = 0
        for i, it in cand:
            if spent + it["price_rub"] <= budget:
                pairs.append((i, 1))
                spent += it["price_rub"]
        if not pairs:
            return None
        return format_combo(items, pairs, budget)
    return None


def calculate_combos(products, budget, persons=1, variations=3):
    """Calculate up to `variations` combo variants (persons drinks included).

    Порядок: Оптимум → Без повторов → Макс. вес → дополнительные стратегии →
    детерминированные исключения → псевдослучайные (seeded).
    Возвращает (lines, seed): seed != None, если использовалась случайная часть.
    """
    for p in products:
        p["_taste"] = count_ingredients(p["description"])
    variants = _combo_variants(products, budget, persons)
    if not variants:
        return [], None
    if variations <= 3:
        return variants[:variations], None

    # > 3: базовые 3 стандартные всегда в начале
    result = list(variants[:3])
    if len(result) >= variations:
        return result[:variations], None

    # дополнительные стратегии без persons-гарантий + варианты персон
    extra = []
    for strategy in ("no_drinks_max", "drinks_only"):
        line = _extra_variant(products, budget, strategy, persons)
        if line and line not in result and line not in extra:
            extra.append(line)
    for persons_v in (0, persons + 1, max(persons * 2, 2)):
        if len(result) + len(extra) >= variations:
            break
        for v in _combo_variants(products, budget, persons_v):
            if v not in result and v not in extra:
                extra.append(v)
    result += extra
    if len(result) >= variations:
        return result[:variations], None

    # детерминированные исключающие итерации
    for v in _exclude_variants(products, budget, persons, variations - len(result)):
        if v not in result:
            result.append(v)
    if len(result) >= variations:
        return result[:variations], None

    # псевдослучайные (seeded) — для сетей с большим каталогом добираем до variations
    seed = int(time.time() * 1000)
    for v in _random_variants(products, budget, persons, variations - len(result), seed):
        if v not in result:
            result.append(v)
    return result[:variations], seed


def _exclude_variants(items, budget, persons, limit):
    """Детерминированные вариации: исключаем позиции уже найденных комбо и решаем заново.

    Чередуем optimum → max_weight; persons напитков выбираются из того же пула.
    """
    all_valid = [(i, it) for i, it in enumerate(items) if _valid(it)]
    variants = []
    excluded = set()
    strategies = ("optimum", "max_weight")
    k = 0
    while len(variants) < limit:
        cand = [(i, it) for i, it in all_valid if i not in excluded]
        if not cand:
            break
        food = [(i, it) for i, it in cand if not is_drink(it)]
        if not food:
            break
        cand_items = [it for _, it in cand]
        drink_pairs, drink_spent = select_drinks(cand_items, persons, budget)
        drink_pairs = [(cand[i][0], 1) for i, _ in drink_pairs]
        food_budget = budget - drink_spent
        if food_budget <= 0:
            break

        strategy = strategies[k % len(strategies)]
        food_items = [it for _, it in food]
        if strategy == "optimum":
            indices, _, _ = solve_optimum(food_items, food_budget)
        else:
            indices, _, _ = solve_max_weight_double(food_items, food_budget)
        pairs = drink_pairs + [(food[i][0], cnt) for i, cnt in indices]
        if not pairs:
            break

        line = format_combo(items, pairs, budget)
        if line not in variants:
            variants.append(line)
        for idx, _ in pairs:
            excluded.add(idx)
        k += 1
    return variants


def _random_variants(items, budget, persons, limit, seed):
    """Псевдослучайные вариации: жадный набор по перемешанному порядку.

    Сначала до persons напитков, затем еда; до max_attempts перестановок.
    """
    rng = random.Random(seed)
    valid = [(i, it) for i, it in enumerate(items) if _valid(it)]
    variants = []
    seen = set()
    max_attempts = 50
    attempts = 0
    while len(variants) < limit and attempts < max_attempts:
        attempts += 1
        order = list(valid)
        rng.shuffle(order)
        drinks = [(i, it) for i, it in order if is_drink(it)]
        food = [(i, it) for i, it in order if not is_drink(it)]

        picked = []
        spent = 0
        n_drinks = 0
        for i, it in drinks:
            if n_drinks >= persons:
                break
            if spent + it["price_rub"] <= budget:
                picked.append((i, 1))
                spent += it["price_rub"]
                n_drinks += 1
        for i, it in food:
            if spent + it["price_rub"] <= budget:
                picked.append((i, 1))
                spent += it["price_rub"]

        if not picked:
            continue
        line = format_combo(items, picked, budget)
        if line not in seen:
            seen.add(line)
            variants.append(line)
    return variants
