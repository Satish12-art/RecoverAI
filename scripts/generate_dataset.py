#!/usr/bin/env python3
"""RecoverAI Synthetic Dataset Generator.

Generates realistic, reproducible synthetic customer profiles, orders, payments,
and context-dependent ground truth outcomes for evaluation.

Usage:
    python scripts/generate_dataset.py --seed 42
    python scripts/generate_dataset.py --seed 42 --validate
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone

# Target counts
DEFAULT_NUM_CUSTOMERS = 7000
DEFAULT_NUM_TRANSACTIONS = 8000

# Failure distributions
FAILURE_CODE_WEIGHTS = [
    ("temporary_bank_error", 0.30),
    ("network_error", 0.15),
    ("insufficient_funds", 0.20),
    ("expired_card", 0.15),
    ("authentication_failure", 0.12),
    ("risk_flagged", 0.05),
    ("unknown_failure", 0.03),
]

FAILURE_REASONS = {
    "temporary_bank_error": [
        "Bank server timeout during authorization",
        "Issuer bank gateway unavailable",
        "Intermittent switch failure at issuing bank",
        "Bank network congested",
    ],
    "network_error": [
        "Network connection lost during transaction processing",
        "Payment gateway communication timeout",
        "Socket connection reset by peer",
        "Packet dropped at payment switch",
    ],
    "insufficient_funds": [
        "Account has insufficient balance",
        "Credit limit exceeded",
        "Debit card account balance below transaction value",
    ],
    "expired_card": [
        "Card expired before transaction date",
        "Card expiry date mismatch",
        "Card validity period ended",
    ],
    "authentication_failure": [
        "3D Secure OTP verification timed out",
        "Customer entered incorrect OTP twice",
        "Biometric authentication failed at device level",
        "Customer aborted 3DS authentication",
    ],
    "risk_flagged": [
        "High risk fraud score detected by gateway",
        "Velocity limit breached - multiple rapid attempts",
        "Card reported compromised or lost",
        "Geographic IP mismatch with card origin",
    ],
    "unknown_failure": [
        "Unmapped response code from processing bank",
        "Internal acquirer error",
        "Generic system error",
    ],
}

PAYMENT_METHODS = ["upi", "card", "netbanking", "wallet"]
PAYMENT_METHOD_WEIGHTS = [0.55, 0.30, 0.10, 0.05]

INDIAN_FIRST_NAMES = [
    "Aarav", "Aditi", "Amit", "Ananya", "Arjun", "Deepak", "Divya", "Gaurav",
    "Ishaan", "Kavita", "Manish", "Neha", "Pooja", "Pranav", "Priya", "Rahul",
    "Rajesh", "Ritu", "Rohan", "Sachin", "Sameer", "Sanjay", "Shreya", "Sneha",
    "Suresh", "Tanvi", "Varun", "Vikas", "Vikram", "Zoya",
]

INDIAN_LAST_NAMES = [
    "Agarwal", "Bose", "Chawla", "Deshmukh", "Gupta", "Iyer", "Joshi", "Kapoor",
    "Kumar", "Mehta", "Mishra", "Mukherjee", "Nair", "Patel", "Pillai", "Rao",
    "Reddy", "Roy", "Sen", "Sharma", "Singh", "Srivastava", "Verma", "Yadav",
]


def generate_amount(rng: random.Random) -> float:
    """Generate realistic transaction amount according to target distribution.
    
    ₹200 – ₹2,000       40%
    ₹2,001 – ₹10,000    35%
    ₹10,001 – ₹50,000   20%
    ₹50,001 – ₹150,000   5%
    """
    tier = rng.choices(
        population=[1, 2, 3, 4],
        weights=[0.40, 0.35, 0.20, 0.05],
        k=1,
    )[0]

    if tier == 1:
        # ₹200 – ₹2,000
        val = rng.uniform(200.0, 2000.0)
    elif tier == 2:
        # ₹2,001 – ₹10,000
        val = rng.uniform(2001.0, 10000.0)
    elif tier == 3:
        # ₹10,001 – ₹50,000
        val = rng.uniform(10001.0, 50000.0)
    else:
        # ₹50,001 – ₹150,000
        val = rng.uniform(50001.0, 150000.0)

    # Make amounts realistic (e.g. ₹4,999.00 or ₹1,249.50)
    if rng.random() < 0.4:
        # 99 ending
        val = float(int(val // 100) * 100 - 1) if val > 100 else val
    return round(val, 2)


def generate_customers(num_customers: int, rng: random.Random) -> list[dict]:
    """Generate realistic customer base with 3 distinct behavior profiles."""
    customers = []
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    for i in range(1, num_customers + 1):
        ext_id = f"cust_{i:06d}"
        first_name = rng.choice(INDIAN_FIRST_NAMES)
        last_name = rng.choice(INDIAN_LAST_NAMES)
        name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}{i % 1000}@example.com"

        # Customer profile selection
        profile_tier = rng.choices(
            population=["HIGH_QUALITY", "MEDIUM_QUALITY", "RISKY"],
            weights=[0.50, 0.35, 0.15],
            k=1,
        )[0]

        if profile_tier == "HIGH_QUALITY":
            total_orders = rng.randint(10, 30)
            success_rate = rng.uniform(0.90, 0.98)
            successful_payments = int(round(total_orders * success_rate))
            successful_payments = max(1, min(successful_payments, total_orders))
            failed_payments = total_orders - successful_payments
            refund_count = rng.choices([0, 1], weights=[0.85, 0.15], k=1)[0]
            chargeback_count = 0
            avg_order_val = round(rng.uniform(1500.0, 8500.0), 2)
            tenure_days = rng.randint(180, 1000)
            opted_out = rng.random() < 0.01  # 1% opt out

        elif profile_tier == "MEDIUM_QUALITY":
            total_orders = rng.randint(4, 12)
            success_rate = rng.uniform(0.70, 0.85)
            successful_payments = int(round(total_orders * success_rate))
            successful_payments = max(1, min(successful_payments, total_orders))
            failed_payments = total_orders - successful_payments
            refund_count = rng.choices([0, 1, 2], weights=[0.60, 0.30, 0.10], k=1)[0]
            chargeback_count = rng.choices([0, 1], weights=[0.90, 0.10], k=1)[0]
            avg_order_val = round(rng.uniform(800.0, 5000.0), 2)
            tenure_days = rng.randint(60, 300)
            opted_out = rng.random() < 0.03  # 3% opt out

        else:  # RISKY
            total_orders = rng.randint(2, 8)
            success_rate = rng.uniform(0.40, 0.65)
            successful_payments = int(round(total_orders * success_rate))
            successful_payments = max(1, min(successful_payments, total_orders))
            failed_payments = total_orders - successful_payments
            refund_count = rng.choices([1, 2, 3], weights=[0.40, 0.40, 0.20], k=1)[0]
            chargeback_count = rng.choices([1, 2, 3], weights=[0.60, 0.30, 0.10], k=1)[0]
            avg_order_val = round(rng.uniform(500.0, 3500.0), 2)
            tenure_days = rng.randint(10, 120)
            opted_out = rng.random() < 0.08  # 8% opt out

        created_dt = base_time - timedelta(days=tenure_days)

        customers.append({
            "id": i,
            "external_customer_id": ext_id,
            "name": name,
            "email": email,
            "profile_tier": profile_tier,
            "total_orders": total_orders,
            "successful_payments": successful_payments,
            "failed_payments": failed_payments,
            "refund_count": refund_count,
            "chargeback_count": chargeback_count,
            "average_order_value": avg_order_val,
            "customer_tenure_days": tenure_days,
            "opted_out": opted_out,
            "created_at": created_dt.isoformat(),
            "updated_at": created_dt.isoformat(),
        })

    return customers


def evaluate_ground_truth(
    customer: dict,
    payment_amount: float,
    failure_code: str,
    risk_flagged: bool,
    payment_method: str,
    previous_recovery_attempts: int,
    rng: random.Random,
) -> dict:
    """Multi-feature decision function that computes hidden ground truth.
    
    The same failure code produces different best actions depending on context.
    Features considered:
      - customer_quality_score (derived from profile, tenure, chargebacks, success rate)
      - payment_success_rate (historical)
      - chargeback_count
      - failure_code
      - transaction_amount
      - customer_tenure_days
      - previous_recovery_attempts
      - risk_flagged
      - payment_method
    """
    # 1. Hard safety rules first
    if risk_flagged or failure_code == "risk_flagged":
        return {
            "true_recoverable": False,
            "true_best_action": "stop",
            "true_recovery_outcome": "stopped",
            "true_amount_recovered": 0.0,
        }

    if customer.get("opted_out", False):
        return {
            "true_recoverable": False,
            "true_best_action": "stop",
            "true_recovery_outcome": "stopped",
            "true_amount_recovered": 0.0,
        }

    if previous_recovery_attempts >= 2:
        return {
            "true_recoverable": False,
            "true_best_action": "escalate",
            "true_recovery_outcome": "escalated",
            "true_amount_recovered": 0.0,
        }

    # 2. Contextual scoring factors
    total_pmts = max(1, customer["successful_payments"] + customer["failed_payments"])
    historical_success_rate = customer["successful_payments"] / total_pmts
    has_chargebacks = customer["chargeback_count"] > 0
    is_high_value = payment_amount > 50000.0
    profile = customer.get("profile_tier", "MEDIUM_QUALITY")
    tenure = customer.get("customer_tenure_days", 30)

    # 3. Context-dependent best action logic
    if is_high_value:
        # High value transactions require human review
        best_action = "escalate"
        recoverable = (historical_success_rate >= 0.80 and not has_chargebacks)
        if recoverable and rng.random() < 0.70:
            outcome = "recovered"
            amount_rec = payment_amount
        else:
            outcome = "escalated"
            amount_rec = 0.0

    elif failure_code in ("temporary_bank_error", "network_error"):
        if profile == "RISKY" and (has_chargebacks or historical_success_rate < 0.50):
            # Risky customer with repeated issues -> Escalate rather than auto-retry
            best_action = "escalate"
            recoverable = False
            outcome = "failed" if rng.random() < 0.70 else "escalated"
            amount_rec = 0.0
        elif previous_recovery_attempts == 1 and historical_success_rate < 0.75:
            # Second failure for borderline customer -> message instead of second blind retry
            best_action = "message"
            recoverable = True
            if rng.random() < 0.65:
                outcome = "recovered"
                amount_rec = payment_amount
            else:
                outcome = "failed"
                amount_rec = 0.0
        else:
            # High/medium quality with transient failure -> Retry
            best_action = "retry"
            recoverable = True
            # Base recovery rate for transient retry
            base_p = 0.90 if profile == "HIGH_QUALITY" else 0.75
            if rng.random() < base_p:
                outcome = "recovered"
                amount_rec = payment_amount
            else:
                outcome = "failed"
                amount_rec = 0.0

    elif failure_code == "insufficient_funds":
        if profile == "RISKY" and has_chargebacks:
            # Chronic non-payer with chargebacks -> Stop
            best_action = "stop"
            recoverable = False
            outcome = "stopped"
            amount_rec = 0.0
        elif profile == "HIGH_QUALITY" or (profile == "MEDIUM_QUALITY" and not has_chargebacks):
            # Valued customer who simply needs a reminder/link to top up -> Message
            best_action = "message"
            recoverable = True
            success_p = 0.65 if profile == "HIGH_QUALITY" else 0.45
            if rng.random() < success_p:
                outcome = "recovered"
                amount_rec = payment_amount
            else:
                outcome = "failed"
                amount_rec = 0.0
        else:
            best_action = "escalate"
            recoverable = False
            outcome = "escalated"
            amount_rec = 0.0

    elif failure_code == "expired_card":
        if tenure > 90 and historical_success_rate >= 0.70:
            # Established customer updating card -> Message
            best_action = "message"
            recoverable = True
            success_p = 0.70 if profile == "HIGH_QUALITY" else 0.50
            if rng.random() < success_p:
                outcome = "recovered"
                amount_rec = payment_amount
            else:
                outcome = "failed"
                amount_rec = 0.0
        else:
            # Brand new or low success customer -> Escalate
            best_action = "escalate"
            recoverable = False
            outcome = "escalated"
            amount_rec = 0.0

    elif failure_code == "authentication_failure":
        if profile == "HIGH_QUALITY" and previous_recovery_attempts == 0 and payment_amount < 10000:
            # High quality customer who had a single OTP timeout -> Message
            best_action = "message"
            recoverable = True
            if rng.random() < 0.55:
                outcome = "recovered"
                amount_rec = payment_amount
            else:
                outcome = "failed"
                amount_rec = 0.0
        else:
            # Multiple auth failures or risky profile -> Escalate
            best_action = "escalate"
            recoverable = False
            outcome = "escalated"
            amount_rec = 0.0

    else:  # unknown_failure
        best_action = "escalate"
        recoverable = False
        outcome = "escalated"
        amount_rec = 0.0

    return {
        "true_recoverable": recoverable,
        "true_best_action": best_action,
        "true_recovery_outcome": outcome,
        "true_amount_recovered": amount_rec,
    }


def generate_dataset(
    num_customers: int = DEFAULT_NUM_CUSTOMERS,
    num_transactions: int = DEFAULT_NUM_TRANSACTIONS,
    seed: int = 42,
) -> tuple[list[dict], list[dict], list[dict], dict, dict]:
    """Generate complete dataset with customers, orders, payments, ground truth, and metadata."""
    rng = random.Random(seed)

    # 1. Generate Customers
    customers = generate_customers(num_customers, rng)
    customer_map = {c["id"]: c for c in customers}

    # 2. Generate Orders and Payments
    orders = []
    payments = []
    ground_truth = {}

    start_date = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Failures vs Success breakdown: ~30-35% failed payments to provide ample recovery cases (~2,400 - 2,800 failures)
    failure_codes, failure_weights = zip(*FAILURE_CODE_WEIGHTS)

    for i in range(1, num_transactions + 1):
        order_ext_id = f"ord_{i:07d}"
        payment_ext_id = f"pay_{i:07d}"

        # Select a customer (weighted slightly toward active customers)
        cust_id = rng.randint(1, num_customers)
        cust = customer_map[cust_id]

        amount = generate_amount(rng)
        pmt_method = rng.choices(PAYMENT_METHODS, weights=PAYMENT_METHOD_WEIGHTS, k=1)[0]
        created_dt = start_date + timedelta(
            days=rng.randint(0, 50),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
            seconds=rng.randint(0, 59),
        )

        # Decide if this transaction is failed
        # Risky customers fail more often (50%), High-quality rarely fail (15%), Medium fail (30%)
        p_tier = cust["profile_tier"]
        fail_p = 0.15 if p_tier == "HIGH_QUALITY" else (0.30 if p_tier == "MEDIUM_QUALITY" else 0.50)
        is_failed = rng.random() < fail_p

        if is_failed:
            failure_code = rng.choices(failure_codes, weights=failure_weights, k=1)[0]
            failure_reason = rng.choice(FAILURE_REASONS[failure_code])
            risk_flagged = (failure_code == "risk_flagged") or (cust["chargeback_count"] > 1 and rng.random() < 0.20)
            payment_status = "failed"
            order_status = "failed"
            prev_attempts = rng.choices([0, 1, 2], weights=[0.75, 0.20, 0.05], k=1)[0]

            # Generate hidden ground truth for failed payment
            gt_record = evaluate_ground_truth(
                customer=cust,
                payment_amount=amount,
                failure_code=failure_code,
                risk_flagged=risk_flagged,
                payment_method=pmt_method,
                previous_recovery_attempts=prev_attempts,
                rng=rng,
            )
            ground_truth[payment_ext_id] = gt_record
        else:
            failure_code = None
            failure_reason = None
            risk_flagged = False
            payment_status = "paid"
            order_status = "paid"
            prev_attempts = 0

        # Create Order
        orders.append({
            "id": i,
            "external_order_id": order_ext_id,
            "customer_id": cust_id,
            "amount": amount,
            "currency": "INR",
            "status": order_status,
            "created_at": created_dt.isoformat(),
            "updated_at": created_dt.isoformat(),
        })

        # Create Payment
        payments.append({
            "id": i,
            "external_payment_id": payment_ext_id,
            "external_order_id": order_ext_id,
            "customer_id": cust_id,
            "order_id": i,
            "amount": amount,
            "currency": "INR",
            "status": payment_status,
            "payment_method": pmt_method,
            "failure_code": failure_code,
            "failure_reason": failure_reason,
            "risk_flagged": risk_flagged,
            "previous_recovery_attempts": prev_attempts,
            "created_at": created_dt.isoformat(),
            "updated_at": created_dt.isoformat(),
        })

    # 3. Calculate Metadata Distributions
    failed_payments = [p for p in payments if p["status"] == "failed"]
    successful_payments = [p for p in payments if p["status"] == "paid"]

    profile_counts = {"HIGH_QUALITY": 0, "MEDIUM_QUALITY": 0, "RISKY": 0}
    for c in customers:
        profile_counts[c["profile_tier"]] += 1

    failure_counts = {code: 0 for code, _ in FAILURE_CODE_WEIGHTS}
    for p in failed_payments:
        if p["failure_code"] in failure_counts:
            failure_counts[p["failure_code"]] += 1

    amount_tier_counts = {"200-2000": 0, "2001-10000": 0, "10001-50000": 0, "50001-150000": 0}
    for p in payments:
        amt = p["amount"]
        if amt <= 2000:
            amount_tier_counts["200-2000"] += 1
        elif amt <= 10000:
            amount_tier_counts["2001-10000"] += 1
        elif amt <= 50000:
            amount_tier_counts["10001-50000"] += 1
        else:
            amount_tier_counts["50001-150000"] += 1

    gt_action_counts = {"retry": 0, "message": 0, "escalate": 0, "stop": 0}
    for gt in ground_truth.values():
        gt_action_counts[gt["true_best_action"]] += 1

    metadata = {
        "seed": seed,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_count": len(customers),
        "order_count": len(orders),
        "payment_count": len(payments),
        "failed_payment_count": len(failed_payments),
        "successful_payment_count": len(successful_payments),
        "customer_profile_distribution": {
            k: round(v / len(customers) * 100, 2) for k, v in profile_counts.items()
        },
        "failure_distribution": {
            k: round(v / max(1, len(failed_payments)) * 100, 2) for k, v in failure_counts.items()
        },
        "amount_distribution": {
            k: round(v / len(payments) * 100, 2) for k, v in amount_tier_counts.items()
        },
        "ground_truth_action_distribution": {
            k: round(v / max(1, len(ground_truth)) * 100, 2) for k, v in gt_action_counts.items()
        },
    }

    return customers, orders, payments, ground_truth, metadata


def save_dataset(
    output_dir: str,
    customers: list[dict],
    orders: list[dict],
    payments: list[dict],
    ground_truth: dict,
    metadata: dict,
):
    """Save dataset files to synthetic data directory."""
    os.makedirs(output_dir, exist_ok=True)

    # Note: Strip internal 'profile_tier' helper field from customers json to match DB schema exactly
    cleaned_customers = []
    for c in customers:
        item = dict(c)
        item.pop("profile_tier", None)
        cleaned_customers.append(item)

    # Note: Strip internal 'previous_recovery_attempts' helper from payments json to match DB schema
    cleaned_payments = []
    for p in payments:
        item = dict(p)
        item.pop("previous_recovery_attempts", None)
        cleaned_payments.append(item)

    with open(os.path.join(output_dir, "customers.json"), "w", encoding="utf-8") as f:
        json.dump(cleaned_customers, f, indent=2)

    with open(os.path.join(output_dir, "orders.json"), "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2)

    with open(os.path.join(output_dir, "payments.json"), "w", encoding="utf-8") as f:
        json.dump(cleaned_payments, f, indent=2)

    with open(os.path.join(output_dir, "ground_truth.json"), "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    with open(os.path.join(output_dir, "dataset_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def validate_dataset(
    customers: list[dict],
    orders: list[dict],
    payments: list[dict],
    ground_truth: dict,
    metadata: dict,
    seed: int,
) -> bool:
    """Validate referential integrity, reproducibility, and context dependence."""
    print("=" * 60)
    print("RECOVERAI DATASET VALIDATION")
    print("=" * 60)
    print(f"Customers:           {len(customers):,}")
    print(f"Orders:              {len(orders):,}")
    print(f"Payments:            {len(payments):,}")
    print(f"Failed payments:     {metadata['failed_payment_count']:,}")
    print(f"Successful payments: {metadata['successful_payment_count']:,}")
    print()

    print("Customer profiles:")
    for k, v in metadata["customer_profile_distribution"].items():
        print(f"  {k:16s}: {v:5.1f}%")
    print()

    print("Failure distribution:")
    for k, v in metadata["failure_distribution"].items():
        print(f"  {k:24s}: {v:5.1f}%")
    print()

    print("Amount distribution:")
    for k, v in metadata["amount_distribution"].items():
        print(f"  {k:20s}: {v:5.1f}%")
    print()

    print("Ground truth action distribution:")
    for k, v in metadata["ground_truth_action_distribution"].items():
        print(f"  {k:12s}: {v:5.1f}%")
    print()

    # 1. Referential integrity
    cust_ids = {c["id"] for c in customers}
    order_ids = {o["id"] for o in orders}
    ref_pass = True

    for o in orders:
        if o["customer_id"] not in cust_ids:
            ref_pass = False
            break

    for p in payments:
        if p["customer_id"] not in cust_ids or p["order_id"] not in order_ids:
            ref_pass = False
            break

    # 2. Reproducibility test
    c2, o2, p2, gt2, _ = generate_dataset(len(customers), len(payments), seed)
    repro_pass = (
        len(c2) == len(customers)
        and c2[0]["name"] == customers[0]["name"]
        and p2[0]["amount"] == payments[0]["amount"]
        and len(gt2) == len(ground_truth)
    )

    # 3. Context dependence test
    # Check that temporary_bank_error produced multiple distinct actions
    temp_actions = set()
    for p in payments:
        if p.get("failure_code") == "temporary_bank_error":
            gt = ground_truth.get(p["external_payment_id"])
            if gt:
                temp_actions.add(gt["true_best_action"])

    context_dep_pass = len(temp_actions) > 1

    print("Validation:")
    print(f"  Referential integrity: {'PASS' if ref_pass else 'FAIL'}")
    print(f"  Reproducibility:       {'PASS' if repro_pass else 'FAIL'}")
    print(f"  Context dependence:    {'PASS' if context_dep_pass else 'FAIL'} (Actions for bank_error: {sorted(list(temp_actions))})")
    print("=" * 60)

    return ref_pass and repro_pass and context_dep_pass


def main():
    parser = argparse.ArgumentParser(description="Generate RecoverAI Synthetic Dataset")
    parser.add_argument("--customers", type=int, default=DEFAULT_NUM_CUSTOMERS, help="Number of customers")
    parser.add_argument("--transactions", type=int, default=DEFAULT_NUM_TRANSACTIONS, help="Number of transactions")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output-dir", type=str, default="data/synthetic", help="Output directory")
    parser.add_argument("--validate", action="store_true", help="Print dataset validation summary")

    args = parser.parse_args()

    # Determine absolute path to output dir if relative
    if not os.path.isabs(args.output_dir):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(root_dir, args.output_dir)
    else:
        output_dir = args.output_dir

    print(f"Generating synthetic dataset: {args.customers:,} customers, {args.transactions:,} transactions (seed={args.seed})...")
    customers, orders, payments, ground_truth, metadata = generate_dataset(
        num_customers=args.customers,
        num_transactions=args.transactions,
        seed=args.seed,
    )

    save_dataset(output_dir, customers, orders, payments, ground_truth, metadata)
    print(f"Saved dataset files to: {output_dir}")

    if args.validate:
        valid = validate_dataset(customers, orders, payments, ground_truth, metadata, args.seed)
        if not valid:
            sys.exit(1)


if __name__ == "__main__":
    main()
