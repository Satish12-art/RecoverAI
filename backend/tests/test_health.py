"""Tests for health and config endpoints, and database table creation."""

from app.models.models import (
    Customer,
    Order,
    Payment,
    RecoveryCase,
    AgentAction,
    RecoveryOutcome,
    WebhookEvent,
)


class TestHealthEndpoint:
    """Test GET /api/health."""

    def test_health_returns_ok(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert data["mode"] == "simulation"
        assert data["demo_mode"] is True

    def test_health_response_shape(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert set(data.keys()) == {"status", "version", "mode", "demo_mode"}


class TestConfigEndpoint:
    """Test GET /api/config."""

    def test_config_returns_thresholds(self, client):
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert data["recovery_mode"] == "simulation"
        assert data["recovery_probability_threshold"] == 0.60
        assert data["scorer_confidence_threshold"] == 0.70
        assert data["auto_recovery_amount_limit"] == 50000.0
        assert data["max_retries"] == 2

    def test_config_no_secrets_exposed(self, client):
        response = client.get("/api/config")
        data = response.json()
        # Secrets must never appear in config endpoint
        assert "gemini_api_key" not in data
        assert "razorpay_key_secret" not in data
        assert "database_url" not in data


class TestDatabaseTables:
    """Test that all 7 tables are created correctly."""

    def test_customer_table_exists(self, db):
        # Should not raise
        db.query(Customer).count()

    def test_order_table_exists(self, db):
        db.query(Order).count()

    def test_payment_table_exists(self, db):
        db.query(Payment).count()

    def test_recovery_case_table_exists(self, db):
        db.query(RecoveryCase).count()

    def test_agent_action_table_exists(self, db):
        db.query(AgentAction).count()

    def test_recovery_outcome_table_exists(self, db):
        db.query(RecoveryOutcome).count()

    def test_webhook_event_table_exists(self, db):
        db.query(WebhookEvent).count()

    def test_create_customer(self, db):
        customer = Customer(
            external_customer_id="test_cust_001",
            name="Test User",
            email="test@example.com",
            total_orders=5,
            successful_payments=4,
            failed_payments=1,
            average_order_value=2500.0,
            customer_tenure_days=180,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        assert customer.id is not None
        assert customer.opted_out is False

        # Cleanup
        db.delete(customer)
        db.commit()

    def test_recovery_outcome_has_new_fields(self, db):
        """Verify v2.1 fields: outcome_status, outcome_source, action_executed_at, outcome_observed_at."""
        # Just verify the columns exist via inspection
        from sqlalchemy import inspect
        mapper = inspect(RecoveryOutcome)
        column_names = [c.key for c in mapper.column_attrs]
        assert "outcome_status" in column_names
        assert "outcome_source" in column_names
        assert "action_executed_at" in column_names
        assert "outcome_observed_at" in column_names
        assert "agent_action_id" in column_names
        assert "simulated" in column_names

    def test_recovery_case_has_scorer_confidence(self, db):
        """Verify v2.1: scorer_confidence is separate from recovery_probability."""
        from sqlalchemy import inspect
        mapper = inspect(RecoveryCase)
        column_names = [c.key for c in mapper.column_attrs]
        assert "recovery_probability" in column_names
        assert "scorer_confidence" in column_names
        assert "expected_recovery_value" in column_names
        assert "retry_count" in column_names


class TestDashboardEndpoint:
    """Test GET /api/dashboard."""

    def test_dashboard_returns_metrics(self, client):
        response = client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "gross_revenue_at_risk" in data
        assert "potentially_recoverable_revenue" in data
        assert "revenue_recovered" in data
        assert "recovery_rate" in data
        assert "total_expected_recovery_value" in data
        assert "cases_processed" in data
        assert data["mode"] == "simulation"


class TestStubEndpoints:
    """Test that all stub endpoints return valid responses."""

    def test_cases_list(self, client):
        response = client.get("/api/cases")
        assert response.status_code == 200

    def test_payments_list(self, client):
        response = client.get("/api/payments")
        assert response.status_code == 200

    def test_analytics_summary(self, client):
        response = client.get("/api/analytics/summary")
        assert response.status_code == 200

    def test_audit_list(self, client):
        response = client.get("/api/audit")
        assert response.status_code == 200

    def test_baseline_comparison(self, client):
        response = client.get("/api/analytics/baseline-comparison")
        assert response.status_code == 200
