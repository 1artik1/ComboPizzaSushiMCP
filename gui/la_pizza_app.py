#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""La Pizza - vygodnoe combo. Raschet optimal'nyh naborov pizz.

Перенесён из корня в gui\\ без изменений логики.
Импорты — из combo_mcp.engines.
"""

import sys
import os
import re
import json
import time
import threading
import tkinter as tk
from tkinter import messagebox
from collections import Counter

# Add project dir to path
_project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from combo_mcp.engines.taste import count_ingredients
from combo_mcp.engines.dp import (
    solve_max_weight_single,
    solve_max_weight_double,
    solve_optimum,
    _solve_optimum_pareto,
    _pareto_filter,
    _pareto_dominates,
    format_combo,
    calculate_combos,
)

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
        r = __import__("requests").get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def extract_weight(html):
    """Extract weight in grams from HTML or JSON."""
    m = re.search(r'<span[^>]*>\s*(\d+)\s*[г\u0413\u20ac]\s*</span>', html)
    if m:
        return int(m.group(1))
    m = re.search(r'<div[^>]*text-gray[^>]*>\s*(\d+)\s*[г\u0413\u20ac]\s*</div>', html)
    if m:
        return int(m.group(1))
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if h1:
        h1_idx = h1.start()
        window = html[max(0, h1_idx):min(len(html), h1_idx + 800)]
        m = re.search(r'(\d+)\s*[г\u0413\u20ac]', window)
        if m:
            return int(m.group(1))
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    for s in scripts:
        if len(s) > 5000:
            m = re.search(r',"(\u041d\u0430\u0442\u0443\u0440\u0430\u043b\u044c\u043d\u044b\u0435[^"]+)",\s*(?:\d+),\s*null,\s*"(\d+)"', s)
            if not m:
                m = re.search(r',"(\u041d\u0430\u0442\u0443\u0440\u0430\u0442\u044c\u043d\u044b\u0439[^"]+)",\s*(?:\d+),\s*null,\s*"(\d+)"', s)
            if m:
                return int(m.group(2))
    return 0


def extract_price(html):
    """Extract price in rubles from HTML."""
    add_idx = html.find("\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c")
    if add_idx > 0:
        window = html[add_idx:add_idx + 500]
        m = re.search(r'(\d+(?:\s\d+)*)\s*[₽\u20bd]', window)
        if m:
            return int(m.group(1).replace(' ', '').replace('\u00a0', ''))
    m = re.search(r'<div[^>]*text-lg[^>]*>(.*?)</div>', html, re.DOTALL)
    if m:
        div_text = m.group(1)
        div_text = re.sub(r'\s*\u043e\u0442\s*', '', div_text)
        m2 = re.search(r'(\d+(?:\s\d+)*)\s*[₽\u20bd]', div_text)
        if m2:
            return int(m2.group(1).replace(' ', '').replace('\u00a0', ''))
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if h1:
        h1_idx = h1.start()
        window = html[max(0, h1_idx):min(len(html), h1_idx + 1500)]
        m = re.search(r'(\d+(?:\s\d+)*)\s*[₽\u20bd]', window)
        if m:
            return int(m.group(1).replace(' ', '').replace('\u00a0', ''))
    return 0


def extract_name(html):
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if m:
        return re.sub(r'\s+', ' ', m.group(1)).strip()
    return ""


def extract_description(html):
    m = re.search(r'class="prose[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    if m:
        desc = m.group(1).strip()
        desc = re.sub(r'<[^>]+>', '', desc)
        desc = desc.replace('\u003Cbr\u002F>', '').replace('\u003Cbr>', '').replace('\n', ' ').strip()
        if len(desc) > 10:
            return desc
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
    m = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html)
    if m:
        return m.group(1)
    return ""


def parse_product_page(product_url):
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
    html = fetch(catalog_url)
    if html is None:
        return []
    links = re.findall(r'href="(/product/\d+)"', html)
    return list(set(links))


def scrape_all_products():
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

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "selftest_output.txt")
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


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        budget = int(sys.argv[sys.argv.index("--selftest") + 1]) if len(sys.argv) > 2 else 3000
        selftest(budget)
    else:
        root = tk.Tk()
        app = LaPizzaApp(root)
        root.mainloop()
