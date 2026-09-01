"""Pytest configuration and fixtures for RecoverAI backend tests."""

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Ensure the backend directory is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Override DATABASE_URL before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_recoverai.db"
os.environ["RECOVERY_MODE"] = "simulation"
os.environ["DEMO_MODE"] = "true"
os.environ["DEBUG"] = "false"

from app.core.database import Base, get_db
from app.models.models import Customer, Payment, Order, RecoveryCase, AgentAction, RecoveryOutcome, WebhookEvent
from main import app

# Test database
TEST_DATABASE_URL = "sqlite:///./test_recoverai.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(test_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables before tests, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_recoverai.db"):
        os.remove("./test_recoverai.db")


@pytest.fixture(autouse=True)
def reset_database_per_test():
    """Clean all tables and seed baseline records before each test for complete isolation."""
    session = TestSessionLocal()
    try:
        session.query(RecoveryOutcome).delete()
        session.query(AgentAction).delete()
        session.query(RecoveryCase).delete()
        session.query(Payment).delete()
        session.query(Order).delete()
        session.query(Customer).delete()
        session.query(WebhookEvent).delete()

        # Seed standard baseline records (Customer 1, 2 and Payment 1, 2, 3)
        c1 = Customer(
            id=1,
            external_customer_id="cust_000001",
            name="Rahul Sharma",
            email="rahul@example.com",
            total_orders=20,
            successful_payments=19,
            failed_payments=1,
            customer_tenure_days=400,
            opted_out=False,
        )
        c2 = Customer(
            id=2,
            external_customer_id="cust_000002",
            name="Priya Patel",
            email="priya@example.com",
            total_orders=10,
            successful_payments=8,
            failed_payments=2,
            customer_tenure_days=150,
            opted_out=False,
        )
        session.add_all([c1, c2])
        session.commit()

        o1 = Order(id=1, external_order_id="ord_0000001", customer_id=1, amount=4999.0, status="failed")
        o2 = Order(id=2, external_order_id="ord_0000002", customer_id=2, amount=8999.0, status="failed")
        o3 = Order(id=3, external_order_id="ord_0000003", customer_id=1, amount=2000.0, status="paid")
        session.add_all([o1, o2, o3])
        session.commit()

        p1 = Payment(
            id=1,
            external_payment_id="pay_0000001",
            external_order_id="ord_0000001",
            customer_id=1,
            order_id=1,
            amount=4999.0,
            currency="INR",
            status="failed",
            payment_method="upi",
            failure_code="temporary_bank_error",
            failure_reason="Bank server timeout",
            risk_flagged=False,
        )
        p2 = Payment(
            id=2,
            external_payment_id="pay_0000002",
            external_order_id="ord_0000002",
            customer_id=2,
            order_id=2,
            amount=8999.0,
            currency="INR",
            status="failed",
            payment_method="card",
            failure_code="expired_card",
            failure_reason="Card expired",
            risk_flagged=False,
        )
        p3 = Payment(
            id=3,
            external_payment_id="pay_0000003",
            external_order_id="ord_0000003",
            customer_id=1,
            order_id=3,
            amount=2000.0,
            currency="INR",
            status="paid",
            payment_method="upi",
            risk_flagged=False,
        )
        session.add_all([p1, p2, p3])
        session.commit()

        case1 = RecoveryCase(
            id=1,
            payment_id=1,
            customer_id=1,
            amount_at_risk=4999.0,
            status="OPEN",
            retry_count=0,
        )
        case2 = RecoveryCase(
            id=2,
            payment_id=2,
            customer_id=2,
            amount_at_risk=8999.0,
            status="OPEN",
            retry_count=0,
        )
        session.add_all([case1, case2])
        session.commit()

    finally:
        session.close()


@pytest.fixture
def db():
    """Yield an isolated database session for each test."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)
