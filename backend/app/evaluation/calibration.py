"""Probability Calibration, Brier Score, and Expected Calibration Error (ECE) Calculator."""

from typing import Optional
from pydantic import BaseModel, Field


class CalibrationBin(BaseModel):
    bin_range: str
    case_count: int
    avg_predicted_probability: float
    actual_recovery_rate: float
    calibration_error: float


class CalibrationReport(BaseModel):
    bins: list[CalibrationBin]
    brier_score: float
    expected_calibration_error: float
    total_evaluated: int


class CalibrationCalculator:
    """Evaluates the statistical calibration of recovery probability scores."""

    @classmethod
    def evaluate(
        cls,
        predicted_probabilities: list[float],
        actual_outcomes: list[bool],
        num_bins: int = 10,
    ) -> CalibrationReport:
        """Calculate bin-level calibration, Brier Score, and ECE."""
        n = len(predicted_probabilities)
        if n == 0 or len(actual_outcomes) != n:
            raise ValueError("Input lists must be non-empty and of equal length.")

        # 1. Brier Score = (1/N) * sum((prob - actual)^2)
        brier_sum = sum(
            (p - (1.0 if y else 0.0)) ** 2
            for p, y in zip(predicted_probabilities, actual_outcomes)
        )
        brier_score = round(brier_sum / n, 4)

        # 2. Binning
        bins: list[CalibrationBin] = []
        bin_width = 1.0 / num_bins
        weighted_ece_sum = 0.0

        for i in range(num_bins):
            lower = i * bin_width
            upper = (i + 1) * bin_width

            # Filter items in [lower, upper) or [lower, upper] for the last bin
            bin_indices = [
                idx
                for idx, p in enumerate(predicted_probabilities)
                if (lower <= p < upper) or (i == num_bins - 1 and lower <= p <= upper)
            ]
            count = len(bin_indices)

            if count > 0:
                avg_prob = sum(predicted_probabilities[idx] for idx in bin_indices) / count
                actual_rate = sum(1.0 if actual_outcomes[idx] else 0.0 for idx in bin_indices) / count
                cal_error = abs(avg_prob - actual_rate)
                weighted_ece_sum += (count / n) * cal_error
            else:
                avg_prob = (lower + upper) / 2.0
                actual_rate = 0.0
                cal_error = 0.0

            bins.append(
                CalibrationBin(
                    bin_range=f"{lower:.1f}–{upper:.1f}",
                    case_count=count,
                    avg_predicted_probability=round(avg_prob, 4),
                    actual_recovery_rate=round(actual_rate, 4),
                    calibration_error=round(cal_error, 4),
                )
            )

        ece = round(weighted_ece_sum, 4)

        return CalibrationReport(
            bins=bins,
            brier_score=brier_score,
            expected_calibration_error=ece,
            total_evaluated=n,
        )
