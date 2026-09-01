"""Unit tests for RecoverAI Synthetic Dataset Generator."""

import json
import os
import sys
import pytest

# Ensure scripts directory is on sys.path
scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts")
sys.path.insert(0, scripts_dir)

from generate_dataset import generate_dataset, evaluate_ground_truth, generate_customers, generate_amount


class TestReproducibility:
    """Test that dataset generation is strictly deterministic by seed."""

    def test_same_seed_produces_identical_dataset(self):
        c1, o1, p1, gt1, m1 = generate_dataset(num_customers=500, num_transactions=600, seed=42)
        c2, o2, p2, gt2, m2 = generate_dataset(num_customers=500, num_transactions=600, seed=42)

        assert c1 == c2
        assert o1 == o2
        assert p1 == p2
        assert gt1 == gt2
        assert m1["customer_count"] == m2["customer_count"]

    def test_different_seeds_produce_different_datasets(self):
        c1, _, p1, _, _ = generate_dataset(num_customers=100, num_transactions=100, seed=42)
        c2, _, p2, _, _ = generate_dataset(num_customers=100, num_transactions=100, seed=999)

        assert c1[0]["name"] != c2[0]["name"] or p1[0]["amount"] != p2[0]["amount"]


class TestCustomerDistributions:
    """Test customer profiles and statistical distributions."""

    def test_profile_tier_proportions(self):
        customers, _, _, _, m = generate_dataset(num_customers=3000, num_transactions=1000, seed=42)
        dist = m["customer_profile_distribution"]

        # High-quality should be ~50% (allow 45-55%)
        assert 45.0 <= dist["HIGH_QUALITY"] <= 55.0
        # Medium-quality should be ~35% (allow 30-40%)
        assert 30.0 <= dist["MEDIUM_QUALITY"] <= 40.0
        # Risky should be ~15% (allow 10-20%)
        assert 10.0 <= dist["RISKY"] <= 20.0

    def test_customer_internal_consistency(self):
        customers, _, _, _, _ = generate_dataset(num_customers=1000, num_transactions=500, seed=42)

        for c in customers:
            assert c["total_orders"] >= 1
            assert c["successful_payments"] >= 1
            assert c["successful_payments"] <= c["total_orders"]
            assert c["successful_payments"] + c["failed_payments"] == c["total_orders"]
            assert c["average_order_value"] > 0
            assert c["customer_tenure_days"] > 0
            assert isinstance(c["opted_out"], bool)

            if c["profile_tier"] == "HIGH_QUALITY":
                assert c["chargeback_count"] == 0
                assert c["customer_tenure_days"] >= 180
            elif c["profile_tier"] == "RISKY":
                assert c["customer_tenure_days"] <= 120


class TestPaymentFailureAndAmountDistributions:
    """Test payment failure codes and amount ranges."""

    def test_failure_code_distributions(self):
        _, _, _, _, m = generate_dataset(num_customers=4000, num_transactions=5000, seed=42)
        f_dist = m["failure_distribution"]

        # temporary_bank_error: ~30% (allow 23-37%)
        assert 23.0 <= f_dist["temporary_bank_error"] <= 37.0
        # network_error: ~15% (allow 10-20%)
        assert 10.0 <= f_dist["network_error"] <= 20.0
        # insufficient_funds: ~20% (allow 15-27%)
        assert 15.0 <= f_dist["insufficient_funds"] <= 27.0
        # expired_card: ~15% (allow 10-20%)
        assert 10.0 <= f_dist["expired_card"] <= 20.0
        # authentication_failure: ~12% (allow 8-16%)
        assert 8.0 <= f_dist["authentication_failure"] <= 16.0
        # risk_flagged: ~5% (allow 2-9%)
        assert 2.0 <= f_dist["risk_flagged"] <= 9.0
        # unknown_failure: ~3% (allow 1-7%)
        assert 1.0 <= f_dist["unknown_failure"] <= 7.0

    def test_amount_distribution(self):
        _, _, _, _, m = generate_dataset(num_customers=2000, num_transactions=4000, seed=42)
        amt_dist = m["amount_distribution"]

        # 200-2000: ~40% (allow 35-46%)
        assert 35.0 <= amt_dist["200-2000"] <= 46.0
        # 2001-10000: ~35% (allow 30-40%)
        assert 30.0 <= amt_dist["2001-10000"] <= 40.0
        # 10001-50000: ~20% (allow 15-25%)
        assert 15.0 <= amt_dist["10001-50000"] <= 25.0
        # 50001-150000: ~5% (allow 2-8%)
        assert 2.0 <= amt_dist["50001-150000"] <= 8.0


class TestReferentialIntegrity:
    """Test relational integrity between customers, orders, and payments."""

    def test_all_foreign_keys_valid(self):
        customers, orders, payments, _, _ = generate_dataset(num_customers=500, num_transactions=800, seed=42)
        cust_ids = {c["id"] for c in customers}
        order_ids = {o["id"] for o in orders}

        for o in orders:
            assert o["customer_id"] in cust_ids
            assert o["amount"] > 0
            assert o["status"] in ("paid", "failed", "pending")

        for p in payments:
            assert p["customer_id"] in cust_ids
            assert p["order_id"] in order_ids
            assert p["amount"] > 0
            assert p["status"] in ("paid", "failed")

            if p["status"] == "failed":
                assert p["failure_code"] is not None
                assert p["failure_reason"] is not None
            else:
                assert p["failure_code"] is None
                assert p["risk_flagged"] is False


class TestGroundTruthAndContextDependence:
    """Test context-dependent ground truth decision logic."""

    def test_allowed_actions_and_outcomes(self):
        _, _, _, ground_truth, _ = generate_dataset(num_customers=1000, num_transactions=2000, seed=42)
        allowed_actions = {"retry", "message", "escalate", "stop"}
        allowed_outcomes = {"recovered", "failed", "escalated", "stopped"}

        for p_id, gt in ground_truth.items():
            assert gt["true_best_action"] in allowed_actions
            assert gt["true_recovery_outcome"] in allowed_outcomes
            assert isinstance(gt["true_recoverable"], bool)
            assert gt["true_amount_recovered"] >= 0.0

    def test_risk_flagged_always_produces_stop(self):
        """Hard safety check: risk flagged transactions must be stopped."""
        import random
        rng = random.Random(42)
        mock_customer = {
            "profile_tier": "HIGH_QUALITY",
            "successful_payments": 20,
            "failed_payments": 0,
            "chargeback_count": 0,
            "opted_out": False,
        }
        gt = evaluate_ground_truth(
            customer=mock_customer,
            payment_amount=1500.0,
            failure_code="risk_flagged",
            risk_flagged=True,
            payment_method="card",
            previous_recovery_attempts=0,
            rng=rng,
        )
        assert gt["true_best_action"] == "stop"
        assert gt["true_recoverable"] is False
        assert gt["true_amount_recovered"] == 0.0

    def test_opted_out_customer_always_produces_stop(self):
        """Hard safety check: opted out customers must be stopped."""
        import random
        rng = random.Random(42)
        mock_customer = {
            "profile_tier": "HIGH_QUALITY",
            "successful_payments": 25,
            "failed_payments": 1,
            "chargeback_count": 0,
            "opted_out": True,
        }
        gt = evaluate_ground_truth(
            customer=mock_customer,
            payment_amount=2000.0,
            failure_code="temporary_bank_error",
            risk_flagged=False,
            payment_method="upi",
            previous_recovery_attempts=0,
            rng=rng,
        )
        assert gt["true_best_action"] == "stop"
        assert gt["true_recoverable"] is False

    def test_context_dependence_temporary_bank_error(self):
        """Proof that the same failure code produces different actions based on context."""
        import random
        rng = random.Random(42)

        # Context A: High quality customer, ₹2,000, 0 attempts -> retry
        high_cust = {
            "profile_tier": "HIGH_QUALITY",
            "successful_payments": 20,
            "failed_payments": 1,
            "chargeback_count": 0,
            "customer_tenure_days": 400,
            "opted_out": False,
        }
        gt_a = evaluate_ground_truth(
            customer=high_cust,
            payment_amount=2000.0,
            failure_code="temporary_bank_error",
            risk_flagged=False,
            payment_method="upi",
            previous_recovery_attempts=0,
            rng=rng,
        )
        assert gt_a["true_best_action"] == "retry"

        # Context B: Risky customer with chargebacks -> escalate
        risky_cust = {
            "profile_tier": "RISKY",
            "successful_payments": 2,
            "failed_payments": 4,
            "chargeback_count": 2,
            "customer_tenure_days": 30,
            "opted_out": False,
        }
        gt_b = evaluate_ground_truth(
            customer=risky_cust,
            payment_amount=75000.0,
            failure_code="temporary_bank_error",
            risk_flagged=False,
            payment_method="card",
            previous_recovery_attempts=0,
            rng=rng,
        )
        assert gt_b["true_best_action"] == "escalate"

    def test_context_dependence_insufficient_funds(self):
        """Proof that insufficient_funds produces message vs stop based on customer."""
        import random
        rng = random.Random(42)

        # Context A: High quality customer -> message
        high_cust = {
            "profile_tier": "HIGH_QUALITY",
            "successful_payments": 18,
            "failed_payments": 0,
            "chargeback_count": 0,
            "customer_tenure_days": 300,
            "opted_out": False,
        }
        gt_a = evaluate_ground_truth(
            customer=high_cust,
            payment_amount=1500.0,
            failure_code="insufficient_funds",
            risk_flagged=False,
            payment_method="upi",
            previous_recovery_attempts=0,
            rng=rng,
        )
        assert gt_a["true_best_action"] == "message"

        # Context B: Risky customer with chargebacks -> stop
        risky_cust = {
            "profile_tier": "RISKY",
            "successful_payments": 2,
            "failed_payments": 3,
            "chargeback_count": 1,
            "customer_tenure_days": 20,
            "opted_out": False,
        }
        gt_b = evaluate_ground_truth(
            customer=risky_cust,
            payment_amount=5000.0,
            failure_code="insufficient_funds",
            risk_flagged=False,
            payment_method="card",
            previous_recovery_attempts=0,
            rng=rng,
        )
        assert gt_b["true_best_action"] == "stop"
