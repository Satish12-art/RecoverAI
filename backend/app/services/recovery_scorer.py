"""Deterministic Recovery Scorer for RecoverAI.

Calculates recovery probability and scorer confidence independently
using observable customer history, transaction context, failure codes, and risk signals.
Computes Expected Recovery Value using safe monetary arithmetic.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Sequence
from pydantic import BaseModel, Field


class ScoringFactor(BaseModel):
    feature: str
    impact: str  # "positive", "negative", "neutral"
    description: str


class RecoveryScore(BaseModel):
    recovery_probability: float = Field(ge=0.0, le=1.0)
    scorer_confidence: float = Field(ge=0.0, le=1.0)
    expected_recovery_value: float = Field(ge=0.0)
    factors: list[ScoringFactor] = []


class RecoveryScorer:
    """Deterministic Recovery Scoring Model."""

    # Base recovery probabilities by failure category
    BASE_PROBABILITIES = {
        "temporary_bank_error": 0.88,
        "network_error": 0.82,
        "expired_card": 0.65,
        "insufficient_funds": 0.48,
        "authentication_failure": 0.35,
        "unknown_failure": 0.20,
        "risk_flagged": 0.02,
    }

    @classmethod
    def calculate_score(
        cls,
        payment: dict | object,
        customer: Optional[dict | object] = None,
        previous_recovery_attempts: int = 0,
    ) -> RecoveryScore:
        """Calculate deterministic recovery probability, scorer confidence, and expected recovery value."""
        def get_val(obj, key, default=None):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        factors: list[ScoringFactor] = []

        # 1. Hard Safety Rules Check
        risk_flagged = bool(get_val(payment, "risk_flagged", False))
        failure_code = (get_val(payment, "failure_code") or "unknown_failure").lower()
        amount = float(get_val(payment, "amount", 0.0) or 0.0)
        payment_method = (get_val(payment, "payment_method") or "unknown").lower()
        opted_out = bool(get_val(customer, "opted_out", False))

        if risk_flagged or failure_code == "risk_flagged":
            factors.append(ScoringFactor(
                feature="risk_flagged",
                impact="negative",
                description="Payment flagged with fraud/risk indicator."
            ))
            return RecoveryScore(
                recovery_probability=0.0,
                scorer_confidence=0.99,
                expected_recovery_value=0.0,
                factors=factors,
            )

        if opted_out:
            factors.append(ScoringFactor(
                feature="customer_opted_out",
                impact="negative",
                description="Customer has opted out of communications."
            ))
            return RecoveryScore(
                recovery_probability=0.0,
                scorer_confidence=0.95,
                expected_recovery_value=0.0,
                factors=factors,
            )

        # 2. Base Probability from failure code
        base_p = cls.BASE_PROBABILITIES.get(failure_code, 0.25)
        prob = base_p

        factors.append(ScoringFactor(
            feature="failure_code",
            impact="positive" if base_p >= 0.60 else "negative",
            description=f"Base recovery propensity for '{failure_code}' is {base_p:.2f}."
        ))

        # 3. Customer History Adjustments
        succ_pmts = int(get_val(customer, "successful_payments", 0) or 0)
        failed_pmts = int(get_val(customer, "failed_payments", 0) or 0)
        chargebacks = int(get_val(customer, "chargeback_count", 0) or 0)
        tenure_days = int(get_val(customer, "customer_tenure_days", 0) or 0)
        total_pmts = succ_pmts + failed_pmts

        if total_pmts > 0:
            success_rate = succ_pmts / total_pmts
            if success_rate >= 0.90:
                prob += 0.08
                factors.append(ScoringFactor(
                    feature="historical_success_rate",
                    impact="positive",
                    description=f"High historical payment success rate ({success_rate:.0%})."
                ))
            elif success_rate < 0.60:
                prob -= 0.15
                factors.append(ScoringFactor(
                    feature="historical_success_rate",
                    impact="negative",
                    description=f"Poor historical payment success rate ({success_rate:.0%})."
                ))

        if chargebacks > 0:
            prob -= min(0.30, chargebacks * 0.15)
            factors.append(ScoringFactor(
                feature="chargeback_history",
                impact="negative",
                description=f"Customer has {chargebacks} prior chargeback(s)."
            ))

        if tenure_days >= 180:
            prob += 0.05
            factors.append(ScoringFactor(
                feature="customer_tenure",
                impact="positive",
                description=f"Established customer with {tenure_days} days tenure."
            ))
        elif tenure_days < 30:
            prob -= 0.05
            factors.append(ScoringFactor(
                feature="customer_tenure",
                impact="negative",
                description="New customer with limited payment history."
            ))

        # 4. Amount Adjustments
        if amount > 50000.0:
            prob -= 0.12
            factors.append(ScoringFactor(
                feature="transaction_amount",
                impact="negative",
                description="High-value transaction reduces automatic recovery likelihood."
            ))
        elif amount <= 2000.0:
            prob += 0.04
            factors.append(ScoringFactor(
                feature="transaction_amount",
                impact="positive",
                description="Low-value transaction facilitates frictionless retry."
            ))

        # 5. Payment Method Adjustments
        if payment_method == "upi":
            prob += 0.03
            factors.append(ScoringFactor(
                feature="payment_method",
                impact="positive",
                description="UPI payment rails offer high immediate re-attempt success."
            ))

        # 6. Previous Recovery Attempts Penalty
        if previous_recovery_attempts == 1:
            prob -= 0.15
            factors.append(ScoringFactor(
                feature="previous_recovery_attempts",
                impact="negative",
                description="1 prior recovery attempt already executed."
            ))
        elif previous_recovery_attempts >= 2:
            prob -= 0.35
            factors.append(ScoringFactor(
                feature="previous_recovery_attempts",
                impact="negative",
                description=f"{previous_recovery_attempts} prior recovery attempts executed."
            ))

        # Clamp probability strictly to [0.0, 1.0]
        final_prob = max(0.0, min(1.0, round(prob, 2)))

        # 7. Independent Scorer Confidence Calculation
        # Confidence reflects feature richness and volume of observed signals
        conf = 0.50  # baseline confidence

        if total_pmts >= 10:
            conf += 0.25
        elif total_pmts >= 3:
            conf += 0.15
        elif total_pmts == 0:
            conf -= 0.15

        if tenure_days >= 90:
            conf += 0.15
        elif tenure_days < 15:
            conf -= 0.10

        if failure_code in cls.BASE_PROBABILITIES:
            conf += 0.10

        final_conf = max(0.0, min(1.0, round(conf, 2)))

        # 8. Expected Recovery Value using Decimal monetary calculation
        dec_amount = Decimal(str(round(amount, 2)))
        dec_prob = Decimal(str(final_prob))
        dec_erv = (dec_amount * dec_prob).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        erv_float = float(dec_erv)

        return RecoveryScore(
            recovery_probability=final_prob,
            scorer_confidence=final_conf,
            expected_recovery_value=erv_float,
            factors=factors,
        )
