"""Economic Regret Evaluator for RecoverAI."""

import math
from typing import Optional
from pydantic import BaseModel


class RegretReport(BaseModel):
    total_regret: float
    average_regret: float
    median_regret: float
    p95_regret: float
    total_cases_evaluated: int
    zero_regret_case_count: int
    zero_regret_rate: float


def _calc_median(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


def _calc_p95(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * 0.95
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[int(f)] * (c - k)
    d1 = sorted_vals[int(c)] * (k - f)
    return d0 + d1


class RegretCalculator:
    """Calculates economic regret compared to optimal achievable utility."""

    @classmethod
    def evaluate(
        cls,
        actual_amounts_recovered: list[float],
        optimal_amounts_achievable: list[float],
    ) -> RegretReport:
        """Calculate total, mean, median, and P95 regret."""
        n = len(actual_amounts_recovered)
        if n == 0 or len(optimal_amounts_achievable) != n:
            raise ValueError("Input lists must be non-empty and of equal length.")

        regrets = [
            max(0.0, round(opt - act, 2))
            for act, opt in zip(actual_amounts_recovered, optimal_amounts_achievable)
        ]

        total_regret = round(float(sum(regrets)), 2)
        avg_regret = round(total_regret / n, 2)
        median_regret = round(float(_calc_median(regrets)), 2)
        p95_regret = round(float(_calc_p95(regrets)), 2)

        zero_regret_count = sum(1 for r in regrets if r <= 0.01)
        zero_regret_rate = round((zero_regret_count / n) * 100.0, 2)

        return RegretReport(
            total_regret=total_regret,
            average_regret=avg_regret,
            median_regret=median_regret,
            p95_regret=p95_regret,
            total_cases_evaluated=n,
            zero_regret_case_count=zero_regret_count,
            zero_regret_rate=zero_regret_rate,
        )
