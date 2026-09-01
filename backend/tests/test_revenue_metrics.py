"""Unit tests for Three-Tier Revenue Metrics Service and API endpoints."""

from decimal import Decimal
import pytest
from app.models.models import Payment, Customer, RecoveryOutcome
from app.services.revenue_metrics import RevenueMetricsService


class TestRevenueMetricsService:
    """Test 3-tier metrics aggregation and threshold-gated recoverable revenue."""

    def test_three_tier_metrics_calculation(self):
        payments = [
            # High quality, transient failure -> prob ~0.90 -> Eligible & Potentially Recoverable
            {"id": 101, "customer_id": 101, "status": "failed", "amount": 5000.0, "failure_code": "temporary_bank_error"},
            # Medium quality, insufficient funds -> prob ~0.48 -> Eligible, but below 0.60 threshold (NOT potentially recoverable)
            {"id": 102, "customer_id": 102, "status": "failed", "amount": 2000.0, "failure_code": "insufficient_funds"},
            # Risk flagged -> NOT eligible -> STOP
            {"id": 103, "customer_id": 103, "status": "failed", "amount": 10000.0, "failure_code": "risk_flagged", "risk_flagged": True},
            # Paid payment -> Not at risk
            {"id": 104, "customer_id": 104, "status": "paid", "amount": 3000.0},
        ]
        customers = {
            101: {"successful_payments": 20, "failed_payments": 1, "customer_tenure_days": 300},
            102: {"successful_payments": 5, "failed_payments": 2, "customer_tenure_days": 100},
            103: {"successful_payments": 1, "failed_payments": 5, "chargeback_count": 2},
            104: {"successful_payments": 10, "failed_payments": 0},
        }

        # Simulated observed recovery outcomes: Case 1 recovered ₹5,000
        outcomes = [
            {"successful": True, "amount_recovered": 5000.0},
        ]

        metrics = RevenueMetricsService.calculate_metrics(
            payments=payments,
            customer_map=customers,
            observed_outcomes=outcomes,
            recovery_prob_threshold=0.60,
        )

        # Gross at risk: 5000 + 2000 + 10000 = 17000.00
        assert metrics.gross_revenue_at_risk == 17000.00

        # Eligible cases: Case 1 (5000) and Case 2 (2000) = 2 cases
        assert metrics.eligible_cases_count == 2

        # Potentially recoverable: Only Case 1 (probability >= 0.60) = 5000.00
        assert metrics.potentially_recoverable_revenue == 5000.00
        assert metrics.potentially_recoverable_cases_count == 1

        # Revenue recovered: 5000.00
        assert metrics.revenue_recovered == 5000.00

        # Recovery rate: (5000 / 5000) * 100 = 100.0%
        assert metrics.recovery_rate == 100.0

    def test_zero_potentially_recoverable_rate_does_not_divide_by_zero(self):
        payments = [
            {"id": 1, "customer_id": 1, "status": "failed", "amount": 2000.0, "failure_code": "insufficient_funds"},
        ]
        customers = {
            1: {"successful_payments": 1, "failed_payments": 5, "chargeback_count": 1, "customer_tenure_days": 10}
        }
        metrics = RevenueMetricsService.calculate_metrics(
            payments=payments,
            customer_map=customers,
            observed_outcomes=[],
            recovery_prob_threshold=0.60,
        )

        assert metrics.potentially_recoverable_revenue == 0.0
        assert metrics.recovery_rate == 0.0

    def test_fresh_seeded_dataset_has_zero_recovered_without_actions(self, db):
        """Verify on actual database that revenue_recovered is initially 0.0."""
        payments = db.query(Payment).all()
        customers = db.query(Customer).all()
        customer_map = {c.id: c for c in customers}
        outcomes = db.query(RecoveryOutcome).all()

        metrics = RevenueMetricsService.calculate_metrics(
            payments=payments,
            customer_map=customer_map,
            observed_outcomes=outcomes,
        )

        assert metrics.gross_revenue_at_risk > 0.0
        assert metrics.potentially_recoverable_revenue > 0.0
        assert metrics.revenue_recovered == 0.0
        assert metrics.recovery_rate == 0.0


class TestRevenueApiEndpoints:
    """Test API integration for revenue engine endpoints."""

    def test_get_payment_score_endpoint(self, client):
        response = client.get("/api/payments/1/score")
        assert response.status_code == 200
        data = response.json()
        assert "recovery_probability" in data
        assert "scorer_confidence" in data
        assert "expected_recovery_value" in data
        assert "factors" in data

    def test_get_payment_eligibility_endpoint(self, client):
        response = client.get("/api/payments/1/eligibility")
        assert response.status_code == 200
        data = response.json()
        assert "eligible" in data
        assert "decision" in data
        assert "reason" in data

    def test_get_payment_recovery_analysis_endpoint(self, client):
        response = client.get("/api/payments/1/recovery-analysis")
        assert response.status_code == 200
        data = response.json()
        assert "payment" in data
        assert "eligibility" in data
        assert "scoring" in data

    def test_get_analytics_summary_endpoint(self, client):
        response = client.get("/api/analytics/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["gross_revenue_at_risk"] > 0
        assert data["potentially_recoverable_revenue"] > 0
        assert data["revenue_recovered"] == 0
        assert data["recovery_rate"] == 0

    def test_get_failure_breakdown_endpoint(self, client):
        response = client.get("/api/analytics/failure-breakdown")
        assert response.status_code == 200
        data = response.json()
        assert data["total_failures"] > 0
        assert "count_by_code" in data
        assert "temporary_bank_error" in data["count_by_code"]
