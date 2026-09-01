"""Dashboard API endpoints connected to deterministic revenue engine."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Payment, Customer, RecoveryOutcome
from app.schemas.schemas import DashboardResponse
from app.services.revenue_metrics import RevenueMetricsService

router = APIRouter()


@router.get("", response_model=DashboardResponse)
@router.get("/", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """Get aggregated three-tier dashboard metrics."""
    payments = db.query(Payment).all()
    customers = db.query(Customer).all()
    customer_map = {c.id: c for c in customers}
    outcomes = db.query(RecoveryOutcome).all()

    summary = RevenueMetricsService.calculate_metrics(
        payments=payments,
        customer_map=customer_map,
        observed_outcomes=outcomes,
    )

    return DashboardResponse(
        gross_revenue_at_risk=summary.gross_revenue_at_risk,
        potentially_recoverable_revenue=summary.potentially_recoverable_revenue,
        revenue_recovered=summary.revenue_recovered,
        recovery_rate=summary.recovery_rate,
        total_expected_recovery_value=summary.total_expected_recovery_value,
        cases_processed=summary.eligible_cases_count,
        mode=settings.recovery_mode,
        last_updated=datetime.now(timezone.utc),
    )
