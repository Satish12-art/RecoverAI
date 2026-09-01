#!/usr/bin/env python3
"""RecoverAI Database Seeding Script.

Loads generated synthetic customers, orders, and payments into the database.
Ground truth remains strictly in data/synthetic/ground_truth.json (evaluation only)
and is never inserted into agent-facing database tables.

Usage:
    python scripts/seed_database.py
    python scripts/seed_database.py --reset
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Add backend directory to sys.path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal, engine, init_db, Base
from app.models.models import Customer, Order, Payment, RecoveryCase, AgentAction, RecoveryOutcome, WebhookEvent


def parse_iso(iso_str: str) -> datetime:
    """Parse ISO datetime string."""
    if not iso_str:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.utcnow()


def seed_database(data_dir: str, reset: bool = False):
    """Seed database with synthetic customers, orders, and payments."""
    print("=" * 60)
    print("RECOVERAI DATABASE SEEDER")
    print("=" * 60)

    customers_file = os.path.join(data_dir, "customers.json")
    orders_file = os.path.join(data_dir, "orders.json")
    payments_file = os.path.join(data_dir, "payments.json")

    for filepath, name in [
        (customers_file, "customers.json"),
        (orders_file, "orders.json"),
        (payments_file, "payments.json"),
    ]:
        if not os.path.exists(filepath):
            print(f"Error: Required synthetic data file '{name}' not found in {data_dir}.")
            print("Please run `python scripts/generate_dataset.py` first.")
            sys.exit(1)

    print(f"Loading data from: {data_dir}")
    with open(customers_file, "r", encoding="utf-8") as f:
        raw_customers = json.load(f)

    with open(orders_file, "r", encoding="utf-8") as f:
        raw_orders = json.load(f)

    with open(payments_file, "r", encoding="utf-8") as f:
        raw_payments = json.load(f)

    print(f"Found: {len(raw_customers):,} customers, {len(raw_orders):,} orders, {len(raw_payments):,} payments")

    db = SessionLocal()
    try:
        if reset:
            print("Reset flag set: Dropping existing tables and recreating schema...")
            Base.metadata.drop_all(bind=engine)
            init_db()
        else:
            init_db()
            # Check if database is already populated
            existing_cust = db.query(Customer).count()
            if existing_cust > 0:
                print(f"Database already contains {existing_cust:,} customers.")
                print("Use `--reset` to clear and re-seed.")
                return

        # 1. Insert Customers in bulk
        print("Inserting customers...")
        customers_to_insert = [
            Customer(
                id=c["id"],
                external_customer_id=c["external_customer_id"],
                name=c["name"],
                email=c.get("email"),
                total_orders=c.get("total_orders", 0),
                successful_payments=c.get("successful_payments", 0),
                failed_payments=c.get("failed_payments", 0),
                refund_count=c.get("refund_count", 0),
                chargeback_count=c.get("chargeback_count", 0),
                average_order_value=c.get("average_order_value", 0.0),
                customer_tenure_days=c.get("customer_tenure_days", 0),
                opted_out=c.get("opted_out", False),
                created_at=parse_iso(c.get("created_at")),
                updated_at=parse_iso(c.get("updated_at")),
            )
            for c in raw_customers
        ]
        db.bulk_save_objects(customers_to_insert)
        db.commit()
        print(f"✓ Inserted {len(customers_to_insert):,} customers.")

        # 2. Insert Orders in bulk
        print("Inserting orders...")
        orders_to_insert = [
            Order(
                id=o["id"],
                external_order_id=o["external_order_id"],
                customer_id=o["customer_id"],
                amount=o["amount"],
                currency=o.get("currency", "INR"),
                status=o["status"],
                created_at=parse_iso(o.get("created_at")),
                updated_at=parse_iso(o.get("updated_at")),
            )
            for o in raw_orders
        ]
        db.bulk_save_objects(orders_to_insert)
        db.commit()
        print(f"✓ Inserted {len(orders_to_insert):,} orders.")

        # 3. Insert Payments in bulk
        print("Inserting payments...")
        payments_to_insert = [
            Payment(
                id=p["id"],
                external_payment_id=p["external_payment_id"],
                external_order_id=p.get("external_order_id"),
                customer_id=p["customer_id"],
                order_id=p.get("order_id"),
                amount=p["amount"],
                currency=p.get("currency", "INR"),
                status=p["status"],
                payment_method=p.get("payment_method"),
                failure_code=p.get("failure_code"),
                failure_reason=p.get("failure_reason"),
                risk_flagged=p.get("risk_flagged", False),
                created_at=parse_iso(p.get("created_at")),
                updated_at=parse_iso(p.get("updated_at")),
            )
            for p in raw_payments
        ]
        db.bulk_save_objects(payments_to_insert)
        db.commit()
        print(f"✓ Inserted {len(payments_to_insert):,} payments.")

        # Verification
        cust_count = db.query(Customer).count()
        ord_count = db.query(Order).count()
        pmt_count = db.query(Payment).count()
        failed_count = db.query(Payment).filter(Payment.status == "failed").count()

        print("-" * 60)
        print("SEEDING COMPLETE & VERIFIED:")
        print(f"  Customers in DB: {cust_count:,}")
        print(f"  Orders in DB:    {ord_count:,}")
        print(f"  Payments in DB:  {pmt_count:,}")
        print(f"  Failed Payments: {failed_count:,}")
        print("=" * 60)

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Seed RecoverAI Database")
    parser.add_argument("--data-dir", type=str, default="data/synthetic", help="Directory containing synthetic JSON files")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate database schema before seeding")
    args = parser.parse_args()

    # Determine absolute path to data dir
    if not os.path.isabs(args.data_dir):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(root_dir, args.data_dir)
    else:
        data_dir = args.data_dir

    seed_database(data_dir, reset=args.reset)


if __name__ == "__main__":
    main()
