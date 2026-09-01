"""Analytics API endpoints with deterministic revenue metrics."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Payment, Customer, RecoveryOutcome
from app.services.revenue_metrics import RevenueMetricsService, RevenueMetricsSummary

router = APIRouter()


@router.get("/summary", response_model=RevenueMetricsSummary)
def get_analytics_summary(db: Session = Depends(get_db)):
    """Three-tier revenue metrics summary."""
    payments = db.query(Payment).all()
    customers = db.query(Customer).all()
    customer_map = {c.id: c for c in customers}
    outcomes = db.query(RecoveryOutcome).all()

    return RevenueMetricsService.calculate_metrics(
        payments=payments,
        customer_map=customer_map,
        observed_outcomes=outcomes,
    )


@router.get("/revenue")
def get_analytics_revenue(db: Session = Depends(get_db)):
    """Alias for three-tier revenue analytics."""
    return get_analytics_summary(db=db)


@router.get("/failure-breakdown")
def get_failure_breakdown(db: Session = Depends(get_db)):
    """Failures by category."""
    failed_pmts = db.query(Payment).filter(Payment.status == "failed").all()
    breakdown = {}
    total_amount_by_code = {}

    for p in failed_pmts:
        code = p.failure_code or "unknown"
        breakdown[code] = breakdown.get(code, 0) + 1
        total_amount_by_code[code] = round(total_amount_by_code.get(code, 0.0) + p.amount, 2)

    return {
        "total_failures": len(failed_pmts),
        "count_by_code": breakdown,
        "amount_by_code": total_amount_by_code,
    }


@router.get("/recovery-by-action")
def get_recovery_by_action():
    """Recovery success rate by action type (Phase 7+)."""
    return {"detail": "Will be populated once recovery actions and outcomes exist in Phase 7+"}


@router.get("/escalation")
def get_escalation_metrics():
    """Escalation metrics (Phase 7+)."""
    return {"detail": "Will be populated once agent escalation decisions exist in Phase 6+"}


@router.get("/baseline-comparison")
def get_baseline_comparison():
    """Naive Retry Baseline vs RecoverAI comparison (Phase 8+)."""
    return {"detail": "Will be populated in Phase 8 evaluation"}
