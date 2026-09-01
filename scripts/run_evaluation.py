#!/usr/bin/env python3
"""RecoverAI — Evaluation Framework and Baseline Comparison Runner.

Evaluates RecoverAI against Naive Retry Baseline and Ground Truth Benchmark.
Usage:
    python scripts/run_evaluation.py --seed 42 --limit 100
    python scripts/run_evaluation.py --seed 42 --all
"""

import argparse
import os
import sys

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.database import SessionLocal, init_db
from app.evaluation.evaluator import EvaluationOrchestrator


def main():
    parser = argparse.ArgumentParser(description="RecoverAI Evaluation Framework")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed (default: 42)")
    parser.add_argument("--limit", type=int, default=100, help="Number of cases to evaluate (default: 100)")
    parser.add_argument("--all", action="store_true", help="Evaluate all failed payments in the dataset")
    parser.add_argument("--mode", type=str, default="mock", choices=["mock", "real"], help="Evaluation mode (default: mock)")
    parser.add_argument("--verbose", action="store_true", help="Print verbose calibration and confusion matrix tables")

    args = parser.parse_args()

    init_db()
    db = SessionLocal()

    try:
        print("=" * 65)
        print("📊 RECOVERAI — EVALUATION & BENCHMARK COMPARISON")
        print("=" * 65)
        print(f"Seed: {args.seed} | Mode: {args.mode.upper()} | Cases: {'ALL' if args.all else args.limit}")
        print("Running evaluation against Ground Truth Benchmark...")

        report = EvaluationOrchestrator.run_evaluation(
            db=db,
            seed=args.seed,
            limit=args.limit if not args.all else None,
            all_payments=args.all,
            mode=args.mode,
        )

        print("\n" + "=" * 65)
        print("RECOVERAI EVALUATION REPORT")
        print("=" * 65)
        print(f"Cases evaluated: {report.cases_evaluated}")
        print()
        print("ACTION CLASSIFICATION METRICS")
        print("RecoverAI:")
        print(f"  Precision: {report.recoverai_action_metrics.macro_precision:.4f}")
        print(f"  Recall:    {report.recoverai_action_metrics.macro_recall:.4f}")
        print(f"  Macro F1:  {report.recoverai_action_metrics.macro_f1:.4f}")
        print(f"  Weighted F1: {report.recoverai_action_metrics.weighted_f1:.4f}")
        print()
        print("Naive Retry Baseline:")
        print(f"  Precision: {report.baseline_action_metrics.macro_precision:.4f}")
        print(f"  Recall:    {report.baseline_action_metrics.macro_recall:.4f}")
        print(f"  Macro F1:  {report.baseline_action_metrics.macro_f1:.4f}")
        print()
        print("RECOVERABILITY CLASSIFICATION (Prob >= 0.60 vs True Recoverable)")
        print(f"  Precision: {report.recoverability_metrics.precision:.4f}")
        print(f"  Recall:    {report.recoverability_metrics.recall:.4f}")
        print(f"  F1 Score:  {report.recoverability_metrics.f1_score:.4f}")
        print()
        print("REVENUE COMPARISON")
        print(f"  RecoverAI Revenue:              ₹{report.revenue.recoverai_revenue:,.2f}")
        print(f"  Naive Retry Revenue:            ₹{report.revenue.baseline_revenue:,.2f}")
        print(f"  Ground Truth Achievable:        ₹{report.revenue.ground_truth_revenue:,.2f}")
        print(f"  Revenue Uplift (vs Baseline):   ₹{report.revenue.absolute_uplift:,.2f} ({report.revenue.percentage_uplift:+.2f}%)")
        print(f"  Ground Truth Revenue Capture:   {report.revenue.ground_truth_revenue_capture_rate:.2f}%")
        print()
        print("PROBABILITY CALIBRATION")
        print(f"  Brier Score:                    {report.calibration.brier_score:.4f}")
        print(f"  Expected Calibration Error (ECE): {report.calibration.expected_calibration_error:.4f}")
        print()
        print("ECONOMIC REGRET")
        print(f"  Total Regret:                   ₹{report.regret.total_regret:,.2f}")
        print(f"  Average Regret:                 ₹{report.regret.average_regret:,.2f}")
        print(f"  Median Regret:                  ₹{report.regret.median_regret:,.2f}")
        print(f"  P95 Regret:                     ₹{report.regret.p95_regret:,.2f}")
        print(f"  Zero-Regret Decisions:          {report.regret.zero_regret_rate:.2f}% of cases")
        print()
        print("SAFETY COMPLIANCE")
        print(f"  Policy violations:        {report.safety.policy_violations}")
        print(f"  Risk violations:          {report.safety.risk_violations}")
        print(f"  Opt-out violations:       {report.safety.opt_out_violations}")
        print(f"  Amount-limit violations:  {report.safety.amount_limit_violations}")
        print(f"  Retry-limit violations:   {report.safety.retry_limit_violations}")
        print(f"  All Checks Passed:        {'YES' if report.safety.all_safety_checks_passed else 'NO'}")
        print()
        print("AGENT EFFICIENCY")
        print(f"  Avg LLM calls / case:     {report.efficiency.average_llm_calls_per_case:.2f}")
        print(f"  Avg agent steps / case:   {report.efficiency.average_agent_steps_per_case:.1f}")
        print(f"  Avg runtime / case:       {report.efficiency.average_runtime_ms_per_case:.2f} ms")
        print(f"  Total Evaluation Time:    {report.efficiency.total_runtime_seconds:.2f} s")
        print("=" * 65)

    finally:
        db.close()


if __name__ == "__main__":
    main()
