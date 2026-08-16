#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""La Pizza - vygodnoe combo. Raschet optimal'nyh naborov pizz."""

import sys
import re
import json
import time
import threading
import tkinter as tk
from tkinter import messagebox
from collections import Counter

import requests

# ---------------------------------------------------------------------------
# HTTP / parsing
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CATALOGS = [
    "/catalog/picci-41-sm-33-sm-i-21-sm",
    "/catalog/bolshie-picci-50-i-45-sm",
    "/catalog/rimskie-picci",
]

COMBO_IDS = {
    "102895237": 3000,
    "102893220": 2000,
}


def fetch(url, timeout=10):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def extract_weight(html):
    """Extract weight in grams from HTML or JSON."""
    # 1. Product page: <span>1050 г</span>
    m = re.search(r'<span[^>]*>\s*(\d+)\s*[г\u0413\u20ac]\s*</span>', html)
    if m:
        return int(m.group(1))
    # 2. Catalog: <div class="text-sm text-gray-400">1050 г</div>
    m = re.search(r'<div[^>]*text-gray[^>]*>\s*(\d+)\s*[г\u0413\u20ac]\s*</div>', html)
    if m:
        return int(m.group(1))
    # 3. Fallback: near h1
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if h1:
        h1_idx = h1.start()
        window = html[max(0, h1_idx):min(len(html), h1_idx + 800)]
        m = re.search(r'(\d+)\s*[г\u0413\u20ac]', window)
        if m:
            return int(m.group(1))
    # 4. Fallback: extract from JSON script tag
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    for s in scripts:
        if len(s) > 5000:
            m = re.search(r',"(\u041d\u0430\u0442\u0443\u0440\u0430\u043b\u044c\u043d\u044b\u0435[^"]+)",\s*(?:\d+),\s*null,\s*"(\d+)"', s)
            if not m:
                m = re.search(r',"(\u041d\u0430\u0442\u0443\u0440\u0430\u043b\u044c\u043d\u044b\u0439[^"]+)",\s*(?:\d+),\s*null,\s*"(\d+)"', s)
            if m:
                return int(m.group(2))
    return 0


def extract_price(html):
    """Extract price in rubles from HTML."""
    # 1. Product page: near "Добавить" button
    add_idx = html.find("\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c")
    if add_idx > 0:
        window = html[add_idx:add_idx + 500]
        m = re.search(r'(\d+(?:\s\d+)*)\s*[₽\u20bd]', window)
        if m:
            return int(m.group(1).replace(' ', '').replace('\u00a0', ''))
    # 2. Catalog: <div class="leading-none! whitespace-nowrap lg:text-xl text-lg"> -> "от 450 ₽"
    m = re.search(r'<div[^>]*text-lg[^>]*>(.*?)</div>', html, re.DOTALL)
    if m:
        div_text = m.group(1)
        div_text = re.sub(r'\s*\u043e\u0442\s*', '', div_text)
        m2 = re.search(r'(\d+(?:\s\d+)*)\s*[₽\u20bd]', div_text)
        if m2:
            return int(m2.group(1).replace(' ', '').replace('\u00a0', ''))
    # 3. Fallback: near h1
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if h1:
        h1_idx = h1.start()
        window = html[max(0, h1_idx):min(len(html), h1_idx + 1500)]
        m = re.search(r'(\d+(?:\s\d+)*)\s*[₽\u20bd]', window)
        if m:
            return int(m.group(1).replace(' ', '').replace('\u00a0', ''))
    return 0


def extract_name(html):
    """Extract product name from h1."""
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if m:
        return re.sub(r'\s+', ' ', m.group(1)).strip()
    return ""


def extract_description(html):
    """Extract ingredients description from the page.
    
    Tries multiple strategies in order:
    a) HTML div with class 'prose' (for обычные pizzas)
    b) JSON pattern: "Натуральный...", price, null, "weight" (for гигант pizzas)
    c) og:description meta tag
    """
    # Method A: HTML div with "prose" class (for обычные pizzas)
    m = re.search(r'class="prose[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    if m:
        desc = m.group(1).strip()
        desc = re.sub(r'<[^>]+>', '', desc)
        desc = desc.replace('\u003Cbr\u002F>', '').replace('\u003Cbr>', '').replace('\n', ' ').strip()
        if len(desc) > 10:
            return desc

    # Method B: JSON pattern - "Натуральный...", price, null, "weight"
    for m in re.finditer('"Натуральный', html):
        start = m.start()
        quote_start = start + 1
        quote_end = quote_start
        while quote_end < len(html):
            if html[quote_end] == '"' and (quote_end == quote_start or html[quote_end - 1] != '\\'):
                break
            quote_end += 1
        if quote_end < len(html):
            desc = html[quote_start + 1:quote_end]
            after = html[quote_end:].strip()
            if re.match(r',\s*\d+,\s*null,\s*\d+', after):
                desc = desc.replace('\u003Cbr\u002F>', '').replace('\u003Cbr>', '').replace('\n', ' ').strip()
                if len(desc) > 10:
                    return desc

    # Method C: og:description
    m = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html)
    if m:
        return m.group(1)

    return ""


def parse_product_page(product_url):
    """Parse a single product page and return dict or None."""
    html = fetch(product_url)
    if html is None:
        return None
    name = extract_name(html)
    weight = extract_weight(html)
    price = extract_price(html)
    description = extract_description(html)
    if not name:
        return None
    return {
        "name": name,
        "weight_g": weight,
        "price_rub": price,
        "description": description,
        "category": "обычная",
        "product_url": product_url,
    }


def parse_catalog(catalog_url):
    """Parse catalog: collect unique product links."""
    html = fetch(catalog_url)
    if html is None:
        return []
    links = re.findall(r'href="(/product/\d+)"', html)
    return list(set(links))


def scrape_all_products():
    """Scrape all products from catalogs + combo pages."""
    products = []
    skipped = []
    cat_links = {}
    for cat_url in CATALOGS:
        full_url = "https://la-pizza.pro" + cat_url
        links = parse_catalog(full_url)
        for link in links:
            cat_links[link] = cat_url
    for pid, default_weight in COMBO_IDS.items():
        cat_links[f"/product/{pid}"] = "/catalog/combo"
    for link in sorted(cat_links.keys()):
        product_url = "https://la-pizza.pro" + link
        cat = cat_links[link]
        if "picci-41" in cat:
            category = "обычная"
        elif "bolshie" in cat:
            category = "гигант"
        elif "rimskie" in cat:
            category = "римская"
        elif "combo" in cat:
            category = "комбо"
        else:
            category = "обычная"
        prod = parse_product_page(product_url)
        if prod is None:
            skipped.append(link)
            continue
        prod["category"] = category
        if category == "комбо" and prod["weight_g"] == 0:
            pid = link.replace("/product/", "")
            prod["weight_g"] = COMBO_IDS.get(pid, 0)
        products.append(prod)
    return products, skipped


# ---------------------------------------------------------------------------
# Vkusnost' (taste count)
# ---------------------------------------------------------------------------

INGREDIENTS = {
    "курочка", "курица", "курицы", "курицу",
    "ветчина", "ветчины", "ветчину",
    "карбонад", "карбонада", "карбонаду",
    "карбонат", "карбоната",
    "пепперони", "пепперонии",
    "колбаски", "колбасок", "колбаскам", "колбасках",
    "охотничьи колбаски", "охотничьих колбасок",
    "сервелат", "сервелата", "сервелату",
    "бекон", "бекана", "беконе",
    "говядина", "говядины", "говятину",
    "фарш", "фарша",
    "грибы", "грибов", "грибах", "грибами",
    "моцарелла", "моцареллы", "моцареллу",
    "чеддер", "чеддера",
    "пармезан", "пармезана",
    "гауда", "гауды",
    "брынза", "брынзы",
    "эдэм", "эдэма",
    "ананасы", "ананаса", "ананасам",
    "перец", "перца", "перце", "перцах",
    "помидоры", "помидор", "помидорам", "помидорах",
    "огурчики", "огурцов", "огурчиков",
    "лук", "лука", "луку",
    "маслины", "маслин",
    "халапеньо", "халапеньо",
    "базилик", "базилика",
    "петрушка", "петрушки", "петрушку",
    "салат", "салата", "салате",
    "черри", "черри",
}

SOUL = {
    "соус", "соуса", "соусам", "соусах", "соусе", "соусы",
    "тесто", "теста",
    "натуральный", "нежная", "нежный", "свежий", "свежая",
    "фирменный", "фирменные", "фирменное",
    "увеличенная", "пикантные", "пикантная",
    "кисло-сладкий", "сливочный", "томатный", "чесночный",
    "терияки", "барбекю", "бордовый", "ранч", "тар-тар",
    "бургер", "сладкий чили", "сливочный",
    "сливочный соус", "чесночный соус", "томатный соус",
    "сливочный соус", "терияки соус", "барбекю соус",
    "бордовый соус", "ранч соус", "тар-тар соус",
    "бургер соус", "сладкий чили соус",
    "сальса", "песто", "песто соус",
    "хрустящее", "тонкое",
    "увеличенная порция",
    "марина", "маринованные", "маринованный",
    "солёные", "солёные огурчики",
    "болгарский",
}


def count_ingredients(description):
    """Count unique ingredient items in description."""
    if not description:
        return 0
    text = description.lower()
    found = set()
    multi_keywords = [
        "охотничьи колбаски", "болгарский перец", "помидоры черри",
        "сладкий чили", "чесночный соус", "сливочный соус",
        "томатный соус", "терияки соус", "барбекю соус",
        "ранч соус", "тар-тар соус", "бургер соус",
        "огурчики", "колбаски",
    ]
    for kw in multi_keywords:
        if kw in text:
            if "колбаски" in kw:
                found.add("колбаски")
            elif "перец" in kw:
                found.add("перец")
            elif "помидор" in kw:
                found.add("помидоры")
            elif "огурчик" in kw:
                found.add("огурчики")
    for ing in INGREDIENTS:
        if ing in text:
            found.add(ing)
    for s in SOUL:
        found.discard(s)
    return len(found)


# ---------------------------------------------------------------------------
# Optimizaciya (ryukzak)
# ---------------------------------------------------------------------------

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
    a dominates b if a has >= weight and >= taste_sum and <= count,
    and strictly greater in at least one dimension.
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
        if count == 1:
            parts.append(f"{item['name']} x1")
        else:
            parts.append(f"{item['name']} x{count}")
    price_per_100 = total_price / total_weight * 100 if total_weight > 0 else 0
    line = f"{total_weight} g | {total_price} rub | {price_per_100:.1f} rub/100g | {', '.join(parts)}"
    return line


def solve_optimum(items, budget):
    """Exclude items with taste=0. Maximize weight * avg_taste.
    
    Uses exact enumeration via itertools for small item counts,
    or Pareto-optimal DP for larger counts.
    """
    filtered = []
    for idx, item in enumerate(items):
        taste = item["_taste"]
        if taste > 0:
            filtered.append((idx, item))
    if not filtered:
        indices, weight, cost = solve_max_weight_double(items, budget)
        return indices, weight, cost

    # Exact enumeration: each item can appear 0-2 times
    # For ~40 items, this is 3^40 which is too large.
    # Use Pareto-optimal DP instead.
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


# ---------------------------------------------------------------------------
# Raschet vseh variantov
# ---------------------------------------------------------------------------

def calculate_combos(products, budget):
    """Calculate 3 combo variants."""
    for p in products:
        p["_taste"] = count_ingredients(p["description"])
    indices1, weight1, cost1 = solve_max_weight_double(products, budget)
    line1 = format_combo(products, indices1, budget)
    indices2, weight2, cost2 = solve_optimum(products, budget)
    line2 = format_combo(products, indices2, budget)
    indices3, weight3 = solve_max_weight_single(products, budget)
    line3 = format_combo(products, [(idx, 1) for idx in indices3], budget)
    return line1, line2, line3


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------


class LaPizzaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("La Pizza - vygodnoe combo")
        self.root.geometry("700x500")
        frame = tk.Frame(root, padx=10, pady=10)
        frame.pack(fill=tk.X)
        tk.Label(frame, text="Budget (rub):", font=("Arial", 11)).pack(side=tk.LEFT)
        self.entry_budget = tk.Entry(frame, width=10, font=("Arial", 11))
        self.entry_budget.insert(0, "3000")
        self.entry_budget.pack(side=tk.LEFT, padx=(10, 10))
        self.btn_parse = tk.Button(
            frame, text="Parse", font=("Arial", 11),
            command=self.on_parse, width=12,
        )
        self.btn_parse.pack(side=tk.LEFT)
        self.text_output = tk.Text(
            root, font=("Courier New", 10), width=80, height=10,
            state=tk.DISABLED,
        )
        self.text_output.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.status_var = tk.StringVar()
        tk.Label(root, textvariable=self.status_var, font=("Arial", 9), fg="gray").pack(
            padx=10, pady=(0, 5), anchor=tk.W
        )

    def on_parse(self):
        budget_str = self.entry_budget.get().strip()
        try:
            budget = int(budget_str)
        except ValueError:
            messagebox.showerror("Error", "Enter a number")
            return
        self.btn_parse.config(text="Parsing...", state=tk.DISABLED)
        self.text_output.config(state=tk.NORMAL)
        self.text_output.delete(1.0, tk.END)
        self.text_output.config(state=tk.DISABLED)
        self.status_var.set("Starting parse...")
        t = threading.Thread(target=self._parse_and_calc, args=(budget,), daemon=True)
        t.start()

    def _parse_and_calc(self, budget):
        start = time.time()
        try:
            products, skipped = scrape_all_products()
            elapsed = time.time() - start
            if not products:
                self.root.after(0, lambda: self._show_error("Could not connect to site"))
                return
            line1, line2, line3 = calculate_combos(products, budget)
            status_msg = f"Parsed {len(products)} items in {elapsed:.1f}s"
            self.root.after(0, lambda: self._show_results(line1, line2, line3, status_msg))
        except Exception as e:
            self.root.after(0, lambda: self._show_error(f"Error: {e}"))

    def _show_results(self, line1, line2, line3, status):
        self.text_output.config(state=tk.NORMAL)
        self.text_output.delete(1.0, tk.END)
        self.text_output.insert(tk.END, f"1) {line1}\n")
        self.text_output.insert(tk.END, f"2) {line2}\n")
        self.text_output.insert(tk.END, f"3) {line3}\n")
        self.text_output.config(state=tk.DISABLED)
        self.status_var.set(status)
        self.btn_parse.config(text="Parse", state=tk.NORMAL)

    def _show_error(self, msg):
        self.text_output.config(state=tk.NORMAL)
        self.text_output.delete(1.0, tk.END)
        self.text_output.insert(tk.END, msg + "\n")
        self.text_output.config(state=tk.DISABLED)
        self.status_var.set("")
        self.btn_parse.config(text="Parse", state=tk.NORMAL)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def selftest(budget):
    print(f"\n=== Self-test, budget={budget} ===\n")
    start = time.time()
    products, skipped = scrape_all_products()
    elapsed = time.time() - start
    print(f"Parsed {len(products)} items in {elapsed:.1f}s")
    if skipped:
        print(f"Skipped: {skipped}")
    for p in products:
        taste = count_ingredients(p["description"])
        print(f"  {p['name']} | {p['weight_g']}g | {p['price_rub']}rub | taste={taste} | {p['category']}")
    line1, line2, line3 = calculate_combos(products, budget)
    print(f"\n1) {line1}")
    print(f"2) {line2}")
    print(f"3) {line3}")
    print("\nOK")

    # Bug 3 fix: write UTF-8 output to file
    out_path = r"C:\Users\1artik1\Desktop\TestOpen\selftest_output.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"=== Self-test, budget={budget} ===\n\n")
        f.write(f"Parsed {len(products)} items in {elapsed:.1f}s\n")
        if skipped:
            f.write(f"Skipped: {skipped}\n")
        for p in products:
            taste = count_ingredients(p["description"])
            f.write(f"  {p['name']} | {p['weight_g']}g | {p['price_rub']}rub | taste={taste} | {p['category']}\n")
        f.write(f"\n1) {line1}\n")
        f.write(f"2) {line2}\n")
        f.write(f"3) {line3}\n")
        f.write("\nOK\n")
    print(f"\nUTF-8 output saved to {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        budget = int(sys.argv[sys.argv.index("--selftest") + 1]) if len(sys.argv) > 2 else 3000
        selftest(budget)
    else:
        root = tk.Tk()
        app = LaPizzaApp(root)
        root.mainloop()
