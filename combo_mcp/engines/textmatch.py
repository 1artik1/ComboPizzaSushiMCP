# -*- coding: utf-8 -*-
"""textmatch.py — нечёткий текстовый матчинг для поиска продукции.

normalize/tokenize — юникод-осознанная нормализация (регистр, ё→е,
пунктуация). levenshtein_within — расстояние Левенштейна с ранним выходом.
score_match — релевантность запроса к названию позиции (0.0 = не совпало).
"""


def normalize(text):
    """Нормализовать текст: lower, ё→е, пунктуация/символы → пробел.

    Буквы и цифры (кириллица+латиница, юникод-осознанно) сохраняются,
    всё остальное заменяется пробелом; повторные пробелы схлопываются.
    """
    if text is None:
        return ""
    s = str(text).lower().replace("ё", "е")
    out = []
    for ch in s:
        if ch == " " or ch.isalnum():
            out.append(ch)
        else:
            out.append(" ")
    return " ".join("".join(out).split())


def tokenize(text):
    """Разбить на токены: normalize + split, остаются токены длиной >= 2."""
    return [t for t in normalize(text).split() if len(t) >= 2]


def levenshtein_within(a, b, maxd=1):
    """True, если расстояние Левенштейна между a и b <= maxd.

    С ранним выходом: разница длин и минимум в строке DP больше maxd — False.
    """
    la, lb = len(a), len(b)
    if abs(la - lb) > maxd:
        return False
    if la == 0 or lb == 0:
        return max(la, lb) <= maxd
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        ca = a[i - 1]
        cur = [i] + [0] * lb
        best = i
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if cur[j] < best:
                best = cur[j]
        if best > maxd:
            return False
        prev = cur
    return prev[lb] <= maxd


def score_match(query, name, category=""):
    """Релевантность query к name (с бонусом категории); 0.0 = не совпало.

    Полное вхождение нормализованного запроса в имя → 3.0; иначе по токенам:
    все совпали → 1.5, часть → 0.5 * доля (округление до 0.1). Токен считается
    совпавшим, если это подстрока имени ИЛИ (len>=5) есть токен имени с
    Левенштейном <= 1. Бонус +0.3 за совпадение с категорией (при score > 0).
    """
    qn = normalize(query)
    nn = normalize(name)
    cn = normalize(category)

    q_tokens = tokenize(query)
    if not q_tokens:
        return 0.0

    if qn and qn in nn:
        score = 3.0
    else:
        n_tokens = tokenize(name)
        matched = 0
        for t in q_tokens:
            hit = t in nn
            if not hit and len(t) >= 5:
                for nt in n_tokens:
                    if levenshtein_within(t, nt, 1):
                        hit = True
                        break
            if hit:
                matched += 1
        if matched == 0:
            return 0.0
        if matched == len(q_tokens):
            score = 1.5
        else:
            score = round(0.5 * (matched / len(q_tokens)), 1)

    if cn and (qn in cn or any(t in cn for t in q_tokens)):
        score += 0.3

    return round(score, 2)
