"""Unit tests for RecoverAI Revenue Risk Engine."""

from decimal import Decimal
import pytest
from app.services.risk_engine import RevenueRiskEngine, RevenueEventType


class TestRevenueRiskEngine:
    """Test Gross Revenue at Risk calculations and risk assessments."""

    def test_assess_failed_payment(self):
        payment = {
            "status": "failed",
            "amount": 4999.0,
            "failure_code": "temporary_bank_error",
            "failure_reason": "Bank server timeout",
        }
        assessment = RevenueRiskEngine.assess_payment(payment)

        assert assessment.is_at_risk is True
        assert assessment.amount_at_risk == 4999.0
        assert assessment.event_type == RevenueEventType.PAYMENT_FAILURE
        assert assessment.failure_code == "temporary_bank_error"

    def test_assess_successful_payment_not_at_risk(self):
        payment = {"status": "paid", "amount": 2500.0}
        assessment = RevenueRiskEngine.assess_payment(payment)

        assert assessment.is_at_risk is False
        assert assessment.amount_at_risk == 0.0

    def test_calculate_gross_revenue_at_risk(self):
        payments = [
            {"status": "failed", "amount": 1000.50},
            {"status": "paid", "amount": 5000.00},       # ignored
            {"status": "failed", "amount": 2999.50},
            {"status": "failed", "amount": 0.00},          # ignored
            {"status": "captured", "amount": 10000.00},   # ignored
            {"status": "failed", "amount": 500.00},
        ]
        gross = RevenueRiskEngine.calculate_gross_revenue_at_risk(payments)

        # 1000.50 + 2999.50 + 500.00 = 4500.00
        assert gross == Decimal("4500.00")
        assert isinstance(gross, Decimal)

    def test_empty_payments_returns_zero(self):
        gross = RevenueRiskEngine.calculate_gross_revenue_at_risk([])
        assert gross == Decimal("0.00")

    def test_precision_with_decimals(self):
        payments = [
            {"status": "failed", "amount": 123.456},
            {"status": "failed", "amount": 987.654},
        ]
        gross = RevenueRiskEngine.calculate_gross_revenue_at_risk(payments)
        assert gross == Decimal("1111.11")
