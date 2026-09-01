"""Unit tests for database seeding script."""

import json
import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts")
sys.path.insert(0, scripts_dir)

from app.core.database import Base
from app.models.models import Customer, Order, Payment
from generate_dataset import generate_dataset, save_dataset
from seed_database import seed_database


class TestDatabaseSeeding:
    """Test database seeding and data integrity."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Generate a small test dataset in a temporary directory."""
        dir_path = str(tmp_path / "synthetic")
        customers, orders, payments, ground_truth, metadata = generate_dataset(
            num_customers=50,
            num_transactions=80,
            seed=42,
        )
        save_dataset(dir_path, customers, orders, payments, ground_truth, metadata)
        return dir_path

    def test_seed_database_populates_tables(self, temp_data_dir, db):
        """Test that seed_database populates customers, orders, and payments."""
        seed_database(data_dir=temp_data_dir, reset=True)

        customers_count = db.query(Customer).count()
        orders_count = db.query(Order).count()
        payments_count = db.query(Payment).count()

        assert customers_count == 50
        assert orders_count == 80
        assert payments_count == 80

    def test_ground_truth_not_in_database(self, temp_data_dir, db):
        """Verify ground truth is NOT stored in customer/payment tables."""
        seed_database(data_dir=temp_data_dir, reset=True)

        # Check Payment model columns
        from sqlalchemy import inspect
        mapper = inspect(Payment)
        col_names = [c.key for c in mapper.column_attrs]
        assert "true_best_action" not in col_names
        assert "true_recoverable" not in col_names
        assert "true_recovery_outcome" not in col_names
        assert "true_amount_recovered" not in col_names

    def test_seed_reset_produces_consistent_state(self, temp_data_dir, db):
        """Test that running with --reset produces clean and identical state."""
        seed_database(data_dir=temp_data_dir, reset=True)
        first_cust = db.query(Customer).first()
        first_cust_name = first_cust.name

        # Re-seed with reset
        seed_database(data_dir=temp_data_dir, reset=True)
        second_cust = db.query(Customer).first()

        assert db.query(Customer).count() == 50
        assert second_cust.name == first_cust_name
