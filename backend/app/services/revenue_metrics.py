"""Deterministic Revenue Metrics Engine for RecoverAI.

Calculates the three-tier revenue metrics:
1. Gross Revenue at Risk
2. Potentially Recoverable Revenue (eligible AND probability >= threshold)
3. Revenue Recovered (actual observed recovered amounts)
4. Expected Recovery Value (sum of amount * probability)
5. Recovery Rate (%)

Uses Decimal arithmetic for precise monetary calculations.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.eligibility import EligibilityGate
from app.services.recovery_scorer import RecoveryScorer


class RevenueMetricsSummary(BaseModel):
    gross_revenue_at_risk: float
    potentially_recoverable_revenue: float
    revenue_recovered: float
    recovery_rate: float
    total_expected_recovery_value: float
    total_payments_analyzed: int
    eligible_cases_count: int
    potentially_recoverable_cases_count: int
    mode: str = "simulation"


class RevenueMetricsService:
    """Service to compute three-tier revenue metrics deterministically."""

    @classmethod
    def calculate_metrics(
        cls,
        payments: Sequence[dict | object],
        customer_map: Optional[dict[int, dict | object]] = None,
        observed_outcomes: Optional[Sequence[dict | object]] = None,
        recovery_prob_threshold: Optional[float] = None,
    ) -> RevenueMetricsSummary:
        """Calculate complete 3-tier metrics over a sequence of payments."""
        if recovery_prob_threshold is None:
            recovery_prob_threshold = settings.recovery_probability_threshold

        def get_val(obj, key, default=None):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        gross_at_risk = Decimal("0.00")
        potentially_recoverable = Decimal("0.00")
        total_erv = Decimal("0.00")
        eligible_count = 0
        pot_rec_count = 0

        for p in payments:
            status = (get_val(p, "status") or "").lower()
            amt_dec = Decimal(str(get_val(p, "amount", 0.0) or "0.0"))

            if status == "failed" and amt_dec > Decimal("0.00"):
                gross_at_risk += amt_dec

                cust_id = get_val(p, "customer_id")
                cust = customer_map.get(cust_id) if customer_map else None

                # 1. Eligibility Check
                elig = EligibilityGate.evaluate(payment=p, customer=cust)
                if elig.eligible:
                    eligible_count += 1
                    # 2. Recovery Scoring
                    score = RecoveryScorer.calculate_score(payment=p, customer=cust)

                    # Expected Recovery Value added
                    total_erv += Decimal(str(score.expected_recovery_value))

                    # 3. Potentially Recoverable: Eligible AND probability >= threshold
                    if score.recovery_probability >= recovery_prob_threshold:
                        potentially_recoverable += amt_dec
                        pot_rec_count += 1

        # Revenue Recovered from observed outcomes
        rev_recovered = Decimal("0.00")
        if observed_outcomes:
            for outcome in observed_outcomes:
                is_success = bool(get_val(outcome, "successful", False))
                if is_success:
                    rec_amt = Decimal(str(get_val(outcome, "amount_recovered", 0.0) or "0.0"))
                    if rec_amt > Decimal("0.00"):
                        rev_recovered += rec_amt

        # Recovery Rate (%)
        if potentially_recoverable > Decimal("0.00"):
            rate_dec = (rev_recovered / potentially_recoverable * Decimal("100.0")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            recovery_rate = float(rate_dec)
        else:
            recovery_rate = 0.0

        return RevenueMetricsSummary(
            gross_revenue_at_risk=float(gross_at_risk.quantize(Decimal("0.01"))),
            potentially_recoverable_revenue=float(potentially_recoverable.quantize(Decimal("0.01"))),
            revenue_recovered=float(rev_recovered.quantize(Decimal("0.01"))),
            recovery_rate=recovery_rate,
            total_expected_recovery_value=float(total_erv.quantize(Decimal("0.01"))),
            total_payments_analyzed=len(payments),
            eligible_cases_count=eligible_count,
            potentially_recoverable_cases_count=pot_rec_count,
            mode=settings.recovery_mode,
        )
