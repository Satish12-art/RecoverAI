#!/usr/bin/env python3
"""RecoverAI Revenue Engine Benchmark Script.

Executes the full deterministic revenue pipeline over all 8,000 payments:
Payment -> Eligibility -> Risk Engine -> Recovery Scorer -> Expected Recovery Value -> Revenue Metrics.

Measures throughput, performance, and produces statistical summaries.
"""

import os
import sys
import time

# Add backend directory to sys.path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal
from app.models.models import Payment, Customer, RecoveryOutcome
from app.services.eligibility import EligibilityGate, EligibilityDecision
from app.services.risk_engine import RevenueRiskEngine
from app.services.recovery_scorer import RecoveryScorer
from app.services.revenue_metrics import RevenueMetricsService


def run_benchmark():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("RECOVERAI REVENUE ENGINE BENCHMARK")
        print("=" * 60)

        payments = db.query(Payment).all()
        customers = db.query(Customer).all()
        customer_map = {c.id: c for c in customers}
        outcomes = db.query(RecoveryOutcome).all()

        total_pmts = len(payments)
        print(f"Loaded {total_pmts:,} payments and {len(customers):,} customers from database.")
        print("Running full deterministic revenue pipeline...")

        start_time = time.perf_counter()

        # Step-by-step pipeline execution
        eligible_count = 0
        stopped_count = 0
        ignored_count = 0

        probabilities = []
        confidences = []
        expected_values = []

        for p in payments:
            cust = customer_map.get(p.customer_id)

            # 1. Eligibility
            elig = EligibilityGate.evaluate(payment=p, customer=cust)
            if elig.decision == EligibilityDecision.PROCEED:
                eligible_count += 1
            elif elig.decision == EligibilityDecision.STOP:
                stopped_count += 1
            elif elig.decision == EligibilityDecision.IGNORE:
                ignored_count += 1

            # 2. Risk Assessment
            risk = RevenueRiskEngine.assess_payment(payment=p)

            # 3. Recovery Scoring
            score = RecoveryScorer.calculate_score(payment=p, customer=cust)
            probabilities.append(score.recovery_probability)
            confidences.append(score.scorer_confidence)
            expected_values.append(score.expected_recovery_value)

        # 4. Three-tier metrics calculation
        summary = RevenueMetricsService.calculate_metrics(
            payments=payments,
            customer_map=customer_map,
            observed_outcomes=outcomes,
        )

        elapsed_time = time.perf_counter() - start_time
        avg_time_ms = (elapsed_time / total_pmts) * 1000.0 if total_pmts > 0 else 0.0

        print()
        print("ELIGIBILITY RESULTS")
        print(f"  Total processed: {total_pmts:,}")
        print(f"  Eligible (Proceed): {eligible_count:,} ({(eligible_count/total_pmts)*100:.1f}%)")
        print(f"  Stopped:            {stopped_count:,} ({(stopped_count/total_pmts)*100:.1f}%)")
        print(f"  Ignored:            {ignored_count:,} ({(ignored_count/total_pmts)*100:.1f}%)")

        print()
        print("SCORING DISTRIBUTIONS")
        print(f"  Min Probability: {min(probabilities):.2f}")
        print(f"  Max Probability: {max(probabilities):.2f}")
        print(f"  Avg Probability: {sum(probabilities)/len(probabilities):.2f}")
        print(f"  Min Confidence:  {min(confidences):.2f}")
        print(f"  Max Confidence:  {max(confidences):.2f}")
        print(f"  Avg Confidence:  {sum(confidences)/len(confidences):.2f}")

        print()
        print("THREE-TIER REVENUE METRICS")
        print(f"  Gross Revenue at Risk:          ₹{summary.gross_revenue_at_risk:,.2f}")
        print(f"  Potentially Recoverable:        ₹{summary.potentially_recoverable_revenue:,.2f}")
        print(f"  Revenue Recovered (Observed):   ₹{summary.revenue_recovered:,.2f}")
        print(f"  Recovery Rate:                  {summary.recovery_rate:.2f}%")
        print(f"  Total Expected Recovery Value:  ₹{summary.total_expected_recovery_value:,.2f}")
        print(f"  Potentially Recoverable Cases:  {summary.potentially_recoverable_cases_count:,}")

        print()
        print("PERFORMANCE & THROUGHPUT")
        print(f"  Total pipeline execution time: {elapsed_time:.4f} seconds")
        print(f"  Average time per payment:      {avg_time_ms:.4f} ms ({total_pmts/elapsed_time:,.0f} payments/sec)")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    run_benchmark()
