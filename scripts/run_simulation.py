#!/usr/bin/env python3
"""RecoverAI — End-to-End Batch Simulation Runner.

Runs deterministic recovery simulations across failed payments without moving real funds.
Usage:
    python scripts/run_simulation.py --limit 100 --seed 42
    python scripts/run_simulation.py --all --seed 42
"""

import argparse
import os
import sys

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.database import SessionLocal, init_db
from app.services.simulation_service import SimulationRunner


def main():
    parser = argparse.ArgumentParser(description="RecoverAI End-to-End Simulation Runner")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed (default: 42)")
    parser.add_argument("--limit", type=int, default=100, help="Number of failed payments to simulate (default: 100)")
    parser.add_argument("--all", action="store_true", help="Process all failed payments in the database")
    parser.add_argument("--mode", type=str, default="mock", choices=["mock", "real"], help="Simulation mode (default: mock)")
    parser.add_argument("--reset", action="store_true", help="Reset and re-seed database before running simulation")
    parser.add_argument("--verbose", action="store_true", help="Print verbose step output for each case")

    args = parser.parse_args()

    init_db()
    db = SessionLocal()

    try:
        print("=" * 60)
        print("🚀 RECOVERAI — END-TO-END SIMULATION RUNNER")
        print("=" * 60)
        print(f"Seed: {args.seed} | Mode: {args.mode.upper()} | Limit: {'ALL' if args.all else args.limit}")
        print("Running simulation...")

        result = SimulationRunner.run(
            db=db,
            seed=args.seed,
            limit=args.limit if not args.all else None,
            all_payments=args.all,
            mode=args.mode,
            verbose=args.verbose,
        )

        avg_ms = (result.duration_seconds / result.payments_processed * 1000) if result.payments_processed > 0 else 0

        print("\n" + "=" * 60)
        print("RECOVERAI SIMULATION REPORT")
        print("=" * 60)
        print(f"Payments processed: {result.payments_processed}")
        print()
        print("Eligibility:")
        print(f"  Eligible: {result.eligible_count}")
        print(f"  Stopped:  {result.stopped_count}")
        print(f"  Ignored:  0")
        print()
        print("AI Recommendations:")
        print(f"  Retry:     {result.ai_recommendations.get('retry', 0)}")
        print(f"  Message:   {result.ai_recommendations.get('message', 0)}")
        print(f"  Escalate:  {result.ai_recommendations.get('escalate', 0)}")
        print(f"  Stop:      {result.ai_recommendations.get('stop', 0)}")
        print()
        print("Policy Decisions:")
        print(f"  Approved:  {result.policy_decisions.get('APPROVE', 0)}")
        print(f"  Escalated: {result.policy_decisions.get('ESCALATE', 0)}")
        print(f"  Stopped:   {result.policy_decisions.get('STOP', 0)}")
        print(f"  Rejected:  {result.policy_decisions.get('REJECT', 0)}")
        print()
        print("Actions Executed:")
        print(f"  Retries:           {result.ai_recommendations.get('retry', 0) if result.policy_decisions.get('APPROVE', 0) > 0 else 0}")
        print(f"  Messages:          {result.ai_recommendations.get('message', 0) if result.policy_decisions.get('APPROVE', 0) > 0 else 0}")
        print(f"  Human Escalations: {result.escalated_count}")
        print()
        print("Outcomes Observed:")
        print(f"  Recovered: {result.recovered_cases}")
        print(f"  Failed:    {result.failed_cases}")
        print(f"  Escalated: {result.escalated_count}")
        print(f"  Stopped:   {result.stopped_count}")
        print()
        print("Revenue Metrics (This Batch):")
        print(f"  Batch Gross Risk:               ₹{result.batch_gross_revenue_at_risk:,.2f}")
        print(f"  Batch Revenue Recovered:        ₹{result.batch_revenue_recovered:,.2f}")
        print(f"  Batch Recovery Rate:            {result.batch_recovery_rate:.2f}%")
        print()
        print("Cumulative Database Metrics:")
        print(f"  Total Gross Revenue at Risk:    ₹{result.gross_revenue_at_risk:,.2f}")
        print(f"  Potentially Recoverable:        ₹{result.potentially_recoverable_revenue:,.2f}")
        print(f"  Expected Recovery Value:        ₹{result.expected_recovery_value:,.2f}")
        print(f"  Cumulative Revenue Recovered:   ₹{result.cumulative_revenue_recovered:,.2f}")
        print()
        print("Performance:")
        print(f"  Duration:  {result.duration_seconds:.3f} seconds")
        print(f"  Avg case:  {avg_ms:.2f} ms")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()
