"""Unit and integration tests for Phase 8 Evaluation Framework."""

import os
import pytest
from app.evaluation.baseline import NaiveRetryBaseline
from app.evaluation.calibration import CalibrationCalculator
from app.evaluation.evaluator import EvaluationOrchestrator
from app.evaluation.ground_truth_loader import GroundTruthLoader, GroundTruthRecord
from app.evaluation.metrics import MetricsCalculator
from app.evaluation.regret import RegretCalculator
from app.evaluation.revenue import RevenueEvaluator
from app.evaluation.safety import SafetyEvaluator
from app.models.models import Customer, Payment, Order, RecoveryCase, RecoveryOutcome, AgentAction


class TestGroundTruthLoader:
    """Test loading and validation of ground truth records."""

    def test_load_ground_truth_file(self):
        gt_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic", "ground_truth.json")
        )
        records = GroundTruthLoader.load(gt_path)
        assert len(records) > 0
        first_rec = next(iter(records.values()))
        assert first_rec.payment_id > 0
        assert first_rec.true_best_action in {"retry", "message", "escalate", "stop"}
        assert first_rec.true_recovery_outcome in {"recovered", "failed", "escalated", "stopped"}

    def test_invalid_ground_truth_record_raises(self):
        with pytest.raises(ValueError):
            GroundTruthRecord(
                payment_id=1,
                true_best_action="illegal_action",
                true_recoverable=True,
                true_recovery_outcome="recovered",
                true_amount_recovered=100.0,
            )

    def test_ground_truth_amount_bounds(self):
        gt_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic", "ground_truth.json")
        )
        records = GroundTruthLoader.load(gt_path)
        for pid, rec in records.items():
            assert rec.true_amount_recovered >= 0.0


class TestNaiveBaselineLogic:
    """Test Naive Retry Baseline decision engine."""

    def test_baseline_risk_flagged_stops(self):
        res = NaiveRetryBaseline.evaluate(
            payment_amount=1000.0,
            risk_flagged=True,
            opted_out=False,
        )
        assert res.action == "stop"

    def test_baseline_opted_out_stops(self):
        res = NaiveRetryBaseline.evaluate(
            payment_amount=1000.0,
            risk_flagged=False,
            opted_out=True,
        )
        assert res.action == "stop"

    def test_baseline_high_amount_escalates(self):
        res = NaiveRetryBaseline.evaluate(
            payment_amount=60000.0,
            risk_flagged=False,
            opted_out=False,
        )
        assert res.action == "escalate"

    def test_baseline_retry_count_limit_escalates(self):
        res = NaiveRetryBaseline.evaluate(
            payment_amount=5000.0,
            risk_flagged=False,
            opted_out=False,
            retry_count=2,
        )
        assert res.action == "escalate"

    def test_baseline_standard_payment_retries(self):
        res = NaiveRetryBaseline.evaluate(
            payment_amount=5000.0,
            risk_flagged=False,
            opted_out=False,
            retry_count=0,
        )
        assert res.action == "retry"


class TestMetricsCalculators:
    """Test mathematical calculation of precision, recall, F1, calibration, regret, and uplift."""

    def test_action_classification_metrics(self):
        preds = ["retry", "retry", "message", "escalate", "stop"]
        trues = ["retry", "message", "message", "escalate", "stop"]

        metrics = MetricsCalculator.compute_action_metrics(preds, trues)
        assert metrics.overall_accuracy == 0.80
        assert metrics.macro_precision > 0
        assert metrics.macro_recall > 0
        assert metrics.macro_f1 > 0
        assert "retry" in metrics.confusion_matrix_raw
        assert metrics.confusion_matrix_raw["retry"]["retry"] == 1
        assert metrics.confusion_matrix_raw["retry"]["message"] == 1

    def test_recoverability_classification_metrics(self):
        probs = [0.90, 0.85, 0.40, 0.10]
        actuals = [True, True, False, False]

        rec_metrics = MetricsCalculator.compute_recoverability_metrics(probs, actuals, threshold=0.60)
        assert rec_metrics.true_positives == 2
        assert rec_metrics.true_negatives == 2
        assert rec_metrics.false_positives == 0
        assert rec_metrics.false_negatives == 0
        assert rec_metrics.f1_score == 1.0

    def test_calibration_and_brier_score(self):
        probs = [0.90, 0.80, 0.20, 0.10]
        actuals = [True, True, False, False]

        cal = CalibrationCalculator.evaluate(probs, actuals, num_bins=10)
        assert len(cal.bins) == 10
        assert cal.brier_score < 0.05
        assert cal.expected_calibration_error < 0.20

    def test_regret_calculator(self):
        actuals = [5000.0, 0.0, 3000.0]
        optimals = [5000.0, 4000.0, 3000.0]

        reg = RegretCalculator.evaluate(actuals, optimals)
        assert reg.total_regret == 4000.0
        assert reg.average_regret == round(4000.0 / 3, 2)
        assert reg.zero_regret_case_count == 2
        assert reg.zero_regret_rate == round(2 / 3 * 100.0, 2)

    def test_revenue_comparison_and_uplift(self):
        rep = RevenueEvaluator.evaluate(
            recoverai_revenue=60000.0,
            baseline_revenue=40000.0,
            ground_truth_revenue=80000.0,
        )
        assert rep.absolute_uplift == 20000.0
        assert rep.percentage_uplift == 50.0
        assert rep.ground_truth_revenue_capture_rate == 75.0

    def test_safety_evaluator(self):
        traces = [
            {"failure_code": "risk_flagged", "action_executed": False, "amount": 1000, "amount_recovered": 0},
            {"failure_code": "temporary_bank_error", "action_executed": True, "amount": 4999, "amount_recovered": 4999},
        ]
        safety = SafetyEvaluator.evaluate(traces)
        assert safety.all_safety_checks_passed is True
        assert safety.risk_violations == 0
        assert safety.fabricated_outcomes == 0


class TestEvaluationConsistencyAndFairness:
    """Consistency audit tests for revenue accounting, fairness, and single contribution invariant."""

    def test_each_payment_contributes_at_most_once(self, db):
        # Clean test database
        db.query(RecoveryOutcome).delete()
        db.query(AgentAction).delete()
        db.query(RecoveryCase).delete()
        db.query(Payment).delete()
        db.query(Order).delete()
        db.query(Customer).delete()
        db.commit()

        for i in range(1, 6):
            c = Customer(id=i, external_customer_id=f"cust_{i:06d}", name=f"Customer {i}", total_orders=10, successful_payments=9, failed_payments=1, customer_tenure_days=200, opted_out=False)
            o = Order(id=i, external_order_id=f"ord_{i:06d}", customer_id=i, amount=4000.0, status="failed")
            p = Payment(id=i, external_payment_id=f"pay_{i:07d}", customer_id=i, order_id=i, amount=4000.0, currency="INR", status="failed", failure_code="temporary_bank_error", risk_flagged=False)
            db.add_all([c, o, p])
        db.commit()

        report = EvaluationOrchestrator.run_evaluation(db=db, seed=42, limit=5, mode="mock", save_artifacts=False)
        assert report.cases_evaluated == 5
        # Verify 5 distinct cases evaluated
        assert report.efficiency.total_payments_evaluated == 5

    def test_recovered_amount_cannot_exceed_payment_amount(self, db):
        db.query(RecoveryOutcome).delete()
        db.query(AgentAction).delete()
        db.query(RecoveryCase).delete()
        db.query(Payment).delete()
        db.query(Order).delete()
        db.query(Customer).delete()
        db.commit()

        c = Customer(id=1, external_customer_id="cust_000001", name="Customer 1", total_orders=10, successful_payments=9, failed_payments=1, customer_tenure_days=200, opted_out=False)
        o = Order(id=1, external_order_id="ord_000001", customer_id=1, amount=4999.0, status="failed")
        p = Payment(id=1, external_payment_id="pay_0000001", customer_id=1, order_id=1, amount=4999.0, currency="INR", status="failed", failure_code="temporary_bank_error", risk_flagged=False)
        db.add_all([c, o, p])
        db.commit()

        report = EvaluationOrchestrator.run_evaluation(db=db, seed=42, limit=1, mode="mock", save_artifacts=False)
        assert report.revenue.recoverai_revenue <= 4999.0
        assert report.revenue.baseline_revenue <= 4999.0


class TestEvaluationOrchestrator:
    """Test full evaluation pipeline and artifact generation."""

    def test_run_evaluation_mini_dataset(self, db):
        # Clean test database respecting foreign keys
        db.query(RecoveryOutcome).delete()
        db.query(AgentAction).delete()
        db.query(RecoveryCase).delete()
        db.query(Payment).delete()
        db.query(Order).delete()
        db.query(Customer).delete()
        db.commit()

        # Seed 5 test customers & payments
        for i in range(1, 6):
            c = Customer(id=i, external_customer_id=f"cust_{i:06d}", name=f"Customer {i}", total_orders=10, successful_payments=9, failed_payments=1, customer_tenure_days=200, opted_out=(i == 5))
            o = Order(id=i, external_order_id=f"ord_{i:06d}", customer_id=i, amount=4000.0, status="failed")
            p = Payment(id=i, external_payment_id=f"pay_{i:07d}", customer_id=i, order_id=i, amount=4000.0, currency="INR", status="failed", failure_code="temporary_bank_error" if i != 5 else "risk_flagged", risk_flagged=(i == 5))
            db.add_all([c, o, p])
        db.commit()

        report = EvaluationOrchestrator.run_evaluation(
            db=db,
            seed=42,
            limit=5,
            mode="mock",
            save_artifacts=True,
        )

        assert report.cases_evaluated == 5
        assert report.recoverai_action_metrics.macro_f1 >= 0.0
        assert report.baseline_action_metrics.macro_f1 >= 0.0
        assert report.safety.all_safety_checks_passed is True
        assert report.efficiency.average_llm_calls_per_case >= 0.0

        # Verify artifacts exist
        out_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "evaluation")
        )
        assert os.path.exists(os.path.join(out_dir, "evaluation_summary.json"))
        assert os.path.exists(os.path.join(out_dir, "action_confusion_matrix.json"))
        assert os.path.exists(os.path.join(out_dir, "calibration.json"))
        assert os.path.exists(os.path.join(out_dir, "revenue_comparison.json"))
        assert os.path.exists(os.path.join(out_dir, "regret.json"))
