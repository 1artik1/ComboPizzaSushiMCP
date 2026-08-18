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


def _limit_pool(filtered):
    """Ограничить пул позиций для DP: топ-40 по вкусу + топ-15 по г/₽ (без пересечения).

    Дешёвые «тяжёлые» позиции (большой вес за малые деньги) не должны выпадать
    из оптимума из-за среза по вкусу.
    """
    filtered.sort(key=lambda x: x[1].get("_taste", 0), reverse=True)
    top = filtered[:40]
    top_idx = {idx for idx, _ in top}
    rest = [e for e in filtered[40:] if e[1].get("price_rub") and e[1]["price_rub"] > 0]
    rest.sort(key=lambda x: x[1]["weight_g"] / x[1]["price_rub"], reverse=True)
    return top + [e for e in rest if e[0] not in top_idx][:15]


def solve_optimum(items, budget):
    """Exclude items with taste=0. Maximize weight * avg_taste.

    Uses Pareto-optimal DP. Items without valid weight_g are excluded.
    For large item sets, the pool is limited by _limit_pool to avoid
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

    filtered = _limit_pool(filtered)

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
            # Merge new states into dp (batched: один pareto-прогон на ячейку за итерацию)
            new_by_c = {}
            for new_w, new_ts, new_cnt, new_hist, target_c in new_states:
                new_by_c.setdefault(target_c, []).append((new_w, new_ts, new_cnt, new_hist))
            for target_c, bucket in new_by_c.items():
                if target_c not in dp:
                    dp[target_c] = []
                existing = {(s[0], s[1], s[2]) for s in dp[target_c]}
                for s in bucket:
                    key = (s[0], s[1], s[2])
                    if key not in existing:
                        existing.add(key)
                        dp[target_c].append(s)
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


def solve_optimum_with_drinks(items, budget, target_drinks):
    """Совместная оптимизация еды и напитков: ровно target_drinks напитков.

    Как solve_optimum, но напитки (в т.ч. с вкусом 0 — вода) участвуют в DP,
    а число напитков — отдельное измерение состояния. Возвращает
    (final, total_weight, total_cost) по индексам исходного items.
    Пул: топ-40 еды по вкусу (только вкус>0) + топ-15 еды по г/₽ + ВСЕ напитки.
    """
    filtered_food = []
    zero_taste_food = []
    drinks_list = []
    for idx, item in enumerate(items):
        w = item.get("weight_g")
        if w is None or w <= 0:
            continue
        if is_drink(item):
            drinks_list.append((idx, item))
        elif item.get("_taste", 0) > 0:
            filtered_food.append((idx, item))
        else:
            zero_taste_food.append((idx, item))

    filtered_food.sort(key=lambda x: x[1].get("_taste", 0), reverse=True)

    # Быстрый путь: еда без вкуса (описаний нет) — задача чисто на максимум
    # веса еды: берём самые дешёвые напитки (минимум трат → максимум еды) и
    # жадный максимум веса на остаток. Эквивалентно DP по целевой функции.
    if not filtered_food:
        drink_pairs, drink_spent = select_drinks(items, target_drinks, budget)
        food = [(i, it) for i, it in enumerate(items)
                if not is_drink(it) and _valid(it)]
        food_items = [it for _, it in food]
        indices, weight, cost = solve_max_weight_double(food_items, budget - drink_spent)
        pairs = list(drink_pairs) + [(food[i][0], cnt) for i, cnt in indices]
        if not pairs:
            return [], 0, 0
        total_weight = sum(items[i]["weight_g"] * c for i, c in pairs)
        total_cost = sum(items[i]["price_rub"] * c for i, c in pairs)
        return pairs, total_weight, total_cost

    top = filtered_food[:40]
    top_idx = {idx for idx, _ in top}
    rest = [e for e in zero_taste_food + filtered_food[40:]
            if e[1].get("price_rub") and e[1]["price_rub"] > 0 and e[0] not in top_idx]
    rest.sort(key=lambda x: x[1]["weight_g"] / x[1]["price_rub"], reverse=True)
    filtered = top + rest[:15] + drinks_list

    if not filtered:
        return [], 0, 0
    return _solve_dp_drinks(items, budget, filtered, target_drinks)


def _solve_dp_drinks(items, budget, filtered, target_drinks):
    """Pareto-DP с измерением числа напитков (0..target_drinks).

    Состояние: (food_weight, taste_sum, count, drinks, history), где
    food_weight — вес ТОЛЬКО еды (напитки — обязательная добавка к комбо,
    их вес не влияет на оптимизацию, иначе DP «набирает» тяжёлые напитки).
    Доминирование: больше вес еды, больше вкус, меньше позиций, больше напитков.
    Напитки сверх target_drinks не добавляются (цель — ровно target).
    """
    dp = {0: [(0, 0, 0, 0, [])]}

    def dominates(a, b):
        return (a[0] >= b[0] and a[1] >= b[1] and a[2] <= b[2] and a[3] >= b[3]
                and (a[0] > b[0] or a[1] > b[1] or a[2] < b[2] or a[3] > b[3]))

    def pfilt(states):
        if not states:
            return []
        states = sorted(states, key=lambda x: (-x[0], -x[1], x[2], -x[3]))
        result = []
        for s in states:
            if not any(dominates(r, s) for r in result):
                result.append(s)
        return result

    for orig_idx, item in filtered:
        cost = item["price_rub"]
        w = item["weight_g"]
        t = item["_taste"]
        dr = 1 if is_drink(item) else 0
        fw = 0 if dr else w
        if cost <= 0 or cost > budget:
            continue
        for copies in range(1, 3):
            item_cost = cost * copies
            item_fw = fw * copies
            item_t = t * copies
            item_dr = dr * copies
            item_cnt = copies
            new_states = []
            for c in range(budget + 1 - item_cost):
                if c not in dp:
                    continue
                for state in dp[c]:
                    old_fw, old_ts, old_cnt, old_dr, hist = state
                    if old_dr + item_dr > target_drinks:
                        continue
                    new_states.append((old_fw + item_fw, old_ts + item_t,
                                       old_cnt + item_cnt, old_dr + item_dr,
                                       hist + [(orig_idx, copies)], c + item_cost))
            new_by_c = {}
            for nfw, nts, ncnt, ndr, nhist, target_c in new_states:
                new_by_c.setdefault(target_c, []).append((nfw, nts, ncnt, ndr, nhist))
            for target_c, bucket in new_by_c.items():
                if target_c not in dp:
                    dp[target_c] = []
                existing = {(s[0], s[1], s[2], s[3]) for s in dp[target_c]}
                for s in bucket:
                    key = (s[0], s[1], s[2], s[3])
                    if key not in existing:
                        existing.add(key)
                        dp[target_c].append(s)
                dp[target_c] = pfilt(dp[target_c])
                if len(dp[target_c]) > 40:
                    # Кап: не более 40 состояний на одно значение числа напитков,
                    # чтобы не взрываться на больших бюджетах/меню без вкуса.
                    groups = {}
                    for s in dp[target_c]:
                        groups.setdefault(s[3], []).append(s)
                    capped = []
                    for g in groups.values():
                        g.sort(key=lambda s: (-s[0], -s[1]))
                        capped.extend(g[:40])
                    dp[target_c] = capped

    # Лучший результат: сначала состояния с максимальным числом напитков
    # (в идеале ровно target_drinks), внутри — по score = food_weight * taste/count.
    best_state = None
    best_score = 0.0
    best_w = 0
    best_dr = -1
    for c in range(budget + 1):
        for state in dp.get(c, []):
            fw, ts, cnt, dr, hist = state
            if cnt == 0:
                continue
            score = fw * (ts / cnt)
            if dr > best_dr or (dr == best_dr and (
                    score > best_score or (score == best_score and fw > best_w))):
                best_dr = dr
                best_score = score
                best_w = fw
                best_state = state

    if best_state is None:
        return [], 0, 0

    fw, _, _, _, hist = best_state
    counts = Counter()
    for idx, cnt in hist:
        counts[idx] += cnt
    total_weight = sum(items[idx]["weight_g"] * cnt for idx, cnt in counts.items())
    total_cost = sum(items[idx]["price_rub"] * cnt for idx, cnt in counts.items())
    final = [(idx, cnt) for idx, cnt in counts.items()]
    return final, total_weight, total_cost


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
            # Совместная оптимизация: напитки внутри DP (ровно target напитков)
            target = min(persons, len(drinks))
            indices, w, cost = solve_optimum_with_drinks(items, budget, target)
            pairs = indices if indices else list(drink_pairs)
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
        p["_taste"] = count_ingredients(p.get("description", ""))
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
