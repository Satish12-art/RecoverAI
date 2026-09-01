"""Revenue Comparison and Uplift Evaluator."""

from pydantic import BaseModel


class RevenueComparisonReport(BaseModel):
    recoverai_revenue: float
    baseline_revenue: float
    ground_truth_revenue: float
    absolute_uplift: float
    percentage_uplift: float
    ground_truth_revenue_capture_rate: float


class RevenueEvaluator:
    """Evaluates comparative revenue generation and uplift."""

    @classmethod
    def evaluate(
        cls,
        recoverai_revenue: float,
        baseline_revenue: float,
        ground_truth_revenue: float,
    ) -> RevenueComparisonReport:
        """Compute absolute/percentage uplift and ground truth revenue capture rate."""
        rec_rev = round(float(recoverai_revenue), 2)
        base_rev = round(float(baseline_revenue), 2)
        gt_rev = round(float(ground_truth_revenue), 2)

        abs_uplift = round(rec_rev - base_rev, 2)
        pct_uplift = round(((rec_rev - base_rev) / base_rev * 100.0) if base_rev > 0 else 0.0, 2)
        capture_rate = round(((rec_rev / gt_rev) * 100.0) if gt_rev > 0 else 0.0, 2)

        return RevenueComparisonReport(
            recoverai_revenue=rec_rev,
            baseline_revenue=base_rev,
            ground_truth_revenue=gt_rev,
            absolute_uplift=abs_uplift,
            percentage_uplift=pct_uplift,
            ground_truth_revenue_capture_rate=capture_rate,
        )
