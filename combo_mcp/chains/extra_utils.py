# -*- coding: utf-8 -*-
"""extra_utils.py — хелперы для parse_extra(): загрузка страниц, чистка текста, OCR.

Общий формат extra-данных сети:
{
  "delivery": {"min_order_rub", "cost_rub", "free_from_rub", "time_minutes",
               "conditions", "source"} | None,
  "loyalty":  {"program", "details", "source"} | None,
  "promotions": [{"title", "conditions", "valid_until", "source"}] | [],
}
"""

import os
import re
import datetime
from bs4 import BeautifulSoup
from combo_mcp import http_client

TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
_TESSDATA = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tesseract-OCR", "tessdata")


def today_str():
    """Сегодняшняя дата ISO (для полей source)."""
    return datetime.date.today().isoformat()


def source(url):
    """Пометка источника с датой проверки."""
    return f"{url} (проверено {today_str()})"


def fetch_text(url, chain_cfg=None):
    """Скачать страницу -> очищенный текст (None при ошибке)."""
    html = http_client.fetch_html(url, chain_cfg)
    return clean_text(html) if html else None


def clean_text(html):
    """HTML -> текст без script/style/noscript, сжатые переносы строк."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\n\s*\n+", "\n", soup.get_text("\n", strip=True))


def clean_promo_desc(text):
    """Очистить описание акции от служебных токенов ([br], [emoji=...])."""
    text = re.sub(r"\[br\]", " ", text)
    text = re.sub(r"\[emoji=[^\]]*\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_promos(text, max_items=12):
    """Извлечь акции с промокодами из текста.

    Ищем «Промокод: XXX» / «промокод XXX»; заголовок — последняя строка
    окна перед промокодом, содержащая «!» (иначе последняя непустая строка
    длиной >= 15), с зачисткой оборванных предлогов. Возвращает список dict
    {"title", "conditions", "promo_code"}.
    """
    out = []
    seen = set()
    pattern = re.compile(r"[Пп]ромокод[а-яё]*\s*[«»:]*\s*([A-ZА-ЯЁ0-9]{2,15})")
    for m in pattern.finditer(text):
        code = m.group(1).upper()
        if code in seen:
            continue
        seen.add(code)
        head = text[max(0, m.start() - 320):m.start()]
        title = _pick_title(head)
        out.append({
            "title": title or f"Промокод {code}",
            "conditions": f"Промокод: {code}",
            "promo_code": code,
        })
        if len(out) >= max_items:
            break
    return out


def _pick_title(head):
    """Выбрать заголовок акции из окна текста перед промокодом."""
    lines = [l.strip() for l in head.split("\n") if l.strip()]
    if not lines:
        return ""
    # последняя строка с «!» (длина >= 10) — обычно заголовок акции
    cand = ""
    for l in reversed(lines):
        if "!" in l and len(l) >= 10:
            cand = l
            break
    if not cand:
        for l in reversed(lines):
            if len(l) >= 15:
                cand = l
                break
    if not cand:
        cand = lines[-1]
    cand = re.sub(r"^[\s\-—•·]+", "", cand).strip()
    cand = re.sub(r"\s+(по|в|на|с|от|до|за)$", "", cand).strip()
    if len(cand) > 120:
        cand = cand[:120].rsplit(" ", 1)[0]
    return cand.strip()


def ocr_image(image_bytes):
    """OCR изображения (bytes) -> строка (None, если OCR недоступен)."""
    try:
        import io
        import pytesseract
        from PIL import Image
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        img = Image.open(io.BytesIO(image_bytes))
        cfg = f"--tessdata-dir {_TESSDATA}" if os.path.isdir(_TESSDATA) else ""
        return pytesseract.image_to_string(img, lang="rus", config=cfg)
    except Exception:
        return None


def render_text(url, wait_ms=4000, full_page=False):
    """Открыть страницу в Playwright и вернуть inner_text + скриншот-OCR.

    Возвращает (inner_text|None, ocr_text|None).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="ru-RU",
            )
            page = ctx.new_page()
            page.goto(url, timeout=40000, wait_until="domcontentloaded")
            page.wait_for_timeout(wait_ms)
            text = re.sub(r"\s+", " ", page.inner_text("body") or "")
            shot = page.screenshot(full_page=full_page)
            browser.close()
        return text, ocr_image(shot)
    except Exception:
        return None, None