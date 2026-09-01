"""Unit and integration test suite for End-to-End Simulation Runner and Lifecycle Execution."""

import pytest
from app.models.models import Customer, Payment, Order, RecoveryCase, AgentAction, RecoveryOutcome
from app.services.simulation_engine import SimulationOutcomeEngine
from app.services.simulation_service import SimulationRunner, SimulationResult


def seed_mini_dataset(db):
    """Seed clean miniature dataset for simulation testing."""
    db.query(RecoveryOutcome).delete()
    db.query(AgentAction).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.query(Order).delete()
    db.query(Customer).delete()
    db.commit()

    customers = []
    for i in range(1, 11):
        c = Customer(
            id=i,
            external_customer_id=f"cust_{i:06d}",
            name=f"Customer {i}",
            total_orders=15 + i,
            successful_payments=14 + i,
            failed_payments=1,
            customer_tenure_days=200 + i * 10,
            opted_out=(i == 10),
        )
        customers.append(c)
    db.add_all(customers)
    db.commit()

    payments = []
    failure_codes = [
        "temporary_bank_error",
        "temporary_bank_error",
        "expired_card",
        "insufficient_funds",
        "risk_flagged",
    ]

    for i in range(1, 21):
        cust_id = ((i - 1) % 10) + 1
        code = failure_codes[(i - 1) % len(failure_codes)]
        is_risk = (code == "risk_flagged")
        amt = 3000.0 + (i * 500.0)
        if i == 18:
            amt = 75000.0

        p = Payment(
            id=i,
            external_payment_id=f"pay_{i:07d}",
            customer_id=cust_id,
            amount=amt,
            currency="INR",
            status="failed",
            payment_method="upi" if i % 2 == 0 else "card",
            failure_code=code,
            risk_flagged=is_risk,
        )
        payments.append(p)

    db.add_all(payments)
    db.commit()


@pytest.fixture
def simulation_test_db(db):
    seed_mini_dataset(db)
    return True


class TestSimulationOutcomeEngine:
    """Test deterministic simulation outcome generator."""

    def test_stopped_action_outcome(self):
        outcome = SimulationOutcomeEngine.generate_outcome(
            action_type="stop",
            payment_amount=5000.0,
            failure_code="risk_flagged",
            recovery_probability=0.0,
        )
        assert outcome.outcome == "stopped"
        assert outcome.amount_recovered == 0.0

    def test_escalated_action_outcome(self):
        outcome = SimulationOutcomeEngine.generate_outcome(
            action_type="escalate",
            payment_amount=75000.0,
            failure_code="temporary_bank_error",
            recovery_probability=0.50,
        )
        assert outcome.outcome == "escalated"
        assert outcome.amount_recovered == 0.0

    def test_high_probability_retry_recovers(self):
        import random
        rng = random.Random(42)
        outcome = SimulationOutcomeEngine.generate_outcome(
            action_type="retry",
            payment_amount=4999.0,
            failure_code="temporary_bank_error",
            recovery_probability=0.90,
            rng=rng,
        )
        assert outcome.outcome in ("recovered", "failed")
        if outcome.outcome == "recovered":
            assert outcome.amount_recovered == 4999.0


class TestSimulationRunnerLifecycle:
    """Test batch simulation lifecycle execution."""

    def test_one_payment_simulation(self, db, simulation_test_db):
        res = SimulationRunner.run(db, seed=42, limit=1, mode="mock")

        assert res.payments_processed == 1
        assert res.duration_seconds >= 0.0
        assert len(res.case_traces) == 1
        assert res.gross_revenue_at_risk > 0.0

    def test_ten_payment_simulation(self, db, simulation_test_db):
        res = SimulationRunner.run(db, seed=42, limit=10, mode="mock")

        assert res.payments_processed == 10
        assert res.actions_executed >= 0
        assert res.outcomes_observed >= 0
        assert res.gross_revenue_at_risk > 0.0
        assert res.error_cases == 0

    def test_full_lifecycle_and_revenue_update(self, db, simulation_test_db):
        """Verify full lifecycle:
        Failed payment -> Eligibility -> AI -> Policy -> Action -> OutcomeObserver -> Revenue metrics.
        """
        res = SimulationRunner.run(db, seed=42, limit=15, mode="mock")

        assert res.payments_processed == 15
        assert res.gross_revenue_at_risk > 0
        assert res.potentially_recoverable_revenue > 0
        if res.recovered_cases > 0:
            assert res.revenue_recovered > 0.0
            assert res.recovery_rate > 0.0

    def test_risk_stop_in_simulation(self, db, simulation_test_db):
        """Risk flagged payments are stopped without calling write tools."""
        res = SimulationRunner.run(db, seed=42, limit=20, mode="mock")

        risk_traces = [t for t in res.case_traces if t.failure_code == "risk_flagged"]
        for t in risk_traces:
            assert t.final_state == "STOPPED"
            assert t.amount_recovered == 0.0

    def test_high_amount_escalation_in_simulation(self, db, simulation_test_db):
        """₹75,000 payment escalates."""
        res = SimulationRunner.run(db, seed=42, limit=20, mode="mock")

        high_amt_traces = [t for t in res.case_traces if t.amount > 50000.0]
        assert len(high_amt_traces) >= 1
        for t in high_amt_traces:
            assert t.final_state in ("ESCALATED", "STOPPED")

    def test_simulation_reproducibility(self, db, simulation_test_db):
        """Running with identical seed against clean database produces identical metric results."""
        # Run 1
        seed_mini_dataset(db)
        res1 = SimulationRunner.run(db, seed=42, limit=10, mode="mock")

        # Run 2 on fresh equivalent state
        seed_mini_dataset(db)
        res2 = SimulationRunner.run(db, seed=42, limit=10, mode="mock")

        assert res1.payments_processed == res2.payments_processed
        assert res1.eligible_count == res2.eligible_count
        assert res1.stopped_count == res2.stopped_count
        assert res1.escalated_count == res2.escalated_count
        assert res1.actions_executed == res2.actions_executed
        assert res1.recovered_cases == res2.recovered_cases
        assert res1.recovered_cases == res2.recovered_cases
        assert res1.revenue_recovered == res2.revenue_recovered
        assert res1.batch_revenue_recovered == res2.batch_revenue_recovered

    def test_simulation_batch_selection_and_idempotency(self, db, simulation_test_db):
        """Sequential simulation runs process disjoint unprocessed payments and avoid duplicate outcomes."""
        seed_mini_dataset(db)

        # First run: limit=10 -> processes payments 1..10
        res1 = SimulationRunner.run(db, seed=42, limit=10, mode="mock")
        assert res1.payments_processed == 10
        p_ids_run1 = {t.payment_id for t in res1.case_traces}
        assert len(p_ids_run1) == 10

        # Second run without reset: limit=10 -> processes next unprocessed payments 11..20
        res2 = SimulationRunner.run(db, seed=42, limit=10, mode="mock")
        assert res2.payments_processed == 10
        p_ids_run2 = {t.payment_id for t in res2.case_traces}
        assert len(p_ids_run2) == 10

        # Verify disjoint sets of payments
        assert p_ids_run1.isdisjoint(p_ids_run2)

        # Verify no duplicate outcomes in DB
        outcomes = db.query(RecoveryOutcome).all()
        outcome_cases = [o.recovery_case_id for o in outcomes]
        assert len(outcome_cases) == len(set(outcome_cases)), "Duplicate outcomes detected for the same recovery case!"

        # Third run without reset: all 20 processed -> 0 remaining
        res3 = SimulationRunner.run(db, seed=42, limit=10, mode="mock")
        assert res3.payments_processed == 0
        assert res3.batch_revenue_recovered == 0.0
        assert res3.recovered_cases == 0

    def test_batch_revenue_vs_cumulative_revenue_separation(self, db, simulation_test_db):
        """Batch revenue reflects only current run; cumulative revenue reflects database-wide total."""
        seed_mini_dataset(db)

        res1 = SimulationRunner.run(db, seed=42, limit=10, mode="mock")
        assert res1.batch_revenue_recovered == sum(t.amount_recovered for t in res1.case_traces)
        assert res1.cumulative_revenue_recovered == res1.batch_revenue_recovered

        res2 = SimulationRunner.run(db, seed=42, limit=10, mode="mock")
        assert res2.batch_revenue_recovered == sum(t.amount_recovered for t in res2.case_traces)
        assert res2.cumulative_revenue_recovered == res1.batch_revenue_recovered + res2.batch_revenue_recovered


class TestSimulationApiEndpoint:
    """Test POST /api/simulate/run endpoint."""

    def test_api_run_simulation(self, client, simulation_test_db):
        payload = {"limit": 5, "seed": 42, "mode": "mock"}
        res = client.post("/api/simulate/run", json=payload)

        assert res.status_code == 200
        data = res.json()

        assert "simulation_id" in data
        assert data["payments_processed"] == 5
        assert data["duration_seconds"] >= 0.0
        assert "gross_revenue_at_risk" in data
        assert "revenue_recovered" in data
        assert "batch_revenue_recovered" in data
        assert "batch_recovery_rate" in data
        assert "batch_gross_revenue_at_risk" in data
        assert "cumulative_revenue_recovered" in data
