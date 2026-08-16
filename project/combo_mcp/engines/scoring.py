# -*- coding: utf-8 -*-
"""scoring.py — стратегии оценки комбо.

Пока одна стратегия — вес. Интерфейс для добавления новых стратегий.
"""

import config


def _get_strategy():
    """Get scoring strategy name from config. Default: 'weight'."""
    # Для простоты — всегда 'weight'
    return "weight"


def score_weight(items):
    """Score = weight (higher is better)."""
    return items


def apply(items, strategy=None):
    """Apply scoring strategy to items. Returns sorted items list."""
    if strategy is None:
        strategy = _get_strategy()
    if strategy == "weight":
        return score_weight(items)
    # Future strategies can be added here
    return score_weight(items)
