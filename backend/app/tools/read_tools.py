"""Read-only tools for the RecoverAI Agent.

Extracts production-facing data from the database and Phase 3 deterministic services.
Does NOT modify state, does NOT call LLMs, and does NOT access ground truth.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.models import Payment, Order, Customer, RecoveryCase, RecoveryOutcome, AgentAction
from app.services.recovery_scorer import RecoveryScorer
from app.tools.tool_types import (
    ToolResult,
    PaymentInfo,
    OrderInfo,
    CustomerInfo,
    CustomerHistoryContext,
    RecoveryCaseInfo,
    RecoveryStatusInfo,
)


class ReadTools:
    """Namespace for read-only agent tools."""

    @staticmethod
    def get_payment(db: Session, payment_id: int) -> ToolResult:
        """Fetch production-facing payment record."""
        if not isinstance(payment_id, int) or payment_id <= 0:
            return ToolResult(
                success=False,
                tool_name="get_payment",
                error="Invalid payment_id parameter. Must be a positive integer.",
            )

        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return ToolResult(
                success=False,
                tool_name="get_payment",
                error=f"Payment with ID {payment_id} not found.",
            )

        info = PaymentInfo(
            id=payment.id,
            external_payment_id=payment.external_payment_id,
            external_order_id=payment.external_order_id,
            customer_id=payment.customer_id,
            order_id=payment.order_id,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            payment_method=payment.payment_method,
            failure_code=payment.failure_code,
            failure_reason=payment.failure_reason,
            risk_flagged=payment.risk_flagged,
            created_at=payment.created_at.isoformat() if payment.created_at else "",
            updated_at=payment.updated_at.isoformat() if payment.updated_at else "",
        )
        return ToolResult(success=True, tool_name="get_payment", data=info.model_dump())

    @staticmethod
    def get_order(db: Session, order_id: int) -> ToolResult:
        """Fetch production-facing order record."""
        if not isinstance(order_id, int) or order_id <= 0:
            return ToolResult(
                success=False,
                tool_name="get_order",
                error="Invalid order_id parameter. Must be a positive integer.",
            )

        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return ToolResult(
                success=False,
                tool_name="get_order",
                error=f"Order with ID {order_id} not found.",
            )

        info = OrderInfo(
            id=order.id,
            external_order_id=order.external_order_id,
            customer_id=order.customer_id,
            amount=order.amount,
            currency=order.currency,
            status=order.status,
            created_at=order.created_at.isoformat() if order.created_at else "",
            updated_at=order.updated_at.isoformat() if order.updated_at else "",
        )
        return ToolResult(success=True, tool_name="get_order", data=info.model_dump())

    @staticmethod
    def get_customer(db: Session, customer_id: int) -> ToolResult:
        """Fetch customer profile record."""
        if not isinstance(customer_id, int) or customer_id <= 0:
            return ToolResult(
                success=False,
                tool_name="get_customer",
                error="Invalid customer_id parameter. Must be a positive integer.",
            )

        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return ToolResult(
                success=False,
                tool_name="get_customer",
                error=f"Customer with ID {customer_id} not found.",
            )

        info = CustomerInfo(
            id=customer.id,
            external_customer_id=customer.external_customer_id,
            name=customer.name,
            email=customer.email,
            total_orders=customer.total_orders,
            successful_payments=customer.successful_payments,
            failed_payments=customer.failed_payments,
            refund_count=customer.refund_count,
            chargeback_count=customer.chargeback_count,
            average_order_value=customer.average_order_value,
            customer_tenure_days=customer.customer_tenure_days,
            opted_out=customer.opted_out,
            created_at=customer.created_at.isoformat() if customer.created_at else "",
        )
        return ToolResult(success=True, tool_name="get_customer", data=info.model_dump())

    @staticmethod
    def get_customer_history(db: Session, customer_id: int) -> ToolResult:
        """Fetch aggregated historical context and recovery track record for a customer."""
        if not isinstance(customer_id, int) or customer_id <= 0:
            return ToolResult(
                success=False,
                tool_name="get_customer_history",
                error="Invalid customer_id parameter. Must be a positive integer.",
            )

        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return ToolResult(
                success=False,
                tool_name="get_customer_history",
                error=f"Customer with ID {customer_id} not found.",
            )

        total_pmts = customer.successful_payments + customer.failed_payments
        success_rate = (customer.successful_payments / total_pmts) if total_pmts > 0 else 0.0

        # Prior recovery cases for this customer
        prior_cases = db.query(RecoveryCase).filter(RecoveryCase.customer_id == customer_id).all()
        prior_recovered_count = sum(1 for c in prior_cases if c.status == "RECOVERED")

        history = CustomerHistoryContext(
            customer_id=customer.id,
            total_orders=customer.total_orders,
            successful_payments=customer.successful_payments,
            failed_payments=customer.failed_payments,
            historical_success_rate=round(success_rate, 4),
            average_order_value=customer.average_order_value,
            chargeback_count=customer.chargeback_count,
            refund_count=customer.refund_count,
            customer_tenure_days=customer.customer_tenure_days,
            opted_out=customer.opted_out,
            prior_recovery_cases_count=len(prior_cases),
            prior_successful_recoveries=prior_recovered_count,
        )
        return ToolResult(success=True, tool_name="get_customer_history", data=history.model_dump())

    @staticmethod
    def calculate_recovery_score(
        db: Session,
        payment_id: int,
        previous_recovery_attempts: int = 0,
    ) -> ToolResult:
        """Calculate deterministic recovery score using Phase 3 Scorer."""
        if not isinstance(payment_id, int) or payment_id <= 0:
            return ToolResult(
                success=False,
                tool_name="calculate_recovery_score",
                error="Invalid payment_id parameter. Must be a positive integer.",
            )

        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return ToolResult(
                success=False,
                tool_name="calculate_recovery_score",
                error=f"Payment with ID {payment_id} not found.",
            )

        customer = db.query(Customer).filter(Customer.id == payment.customer_id).first()
        score = RecoveryScorer.calculate_score(
            payment=payment,
            customer=customer,
            previous_recovery_attempts=previous_recovery_attempts,
        )
        return ToolResult(
            success=True,
            tool_name="calculate_recovery_score",
            data=score.model_dump(),
        )

    @staticmethod
    def get_recovery_case(db: Session, case_id: int) -> ToolResult:
        """Fetch recovery case record."""
        if not isinstance(case_id, int) or case_id <= 0:
            return ToolResult(
                success=False,
                tool_name="get_recovery_case",
                error="Invalid case_id parameter. Must be a positive integer.",
            )

        case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
        if not case:
            return ToolResult(
                success=False,
                tool_name="get_recovery_case",
                error=f"Recovery case with ID {case_id} not found.",
            )

        info = RecoveryCaseInfo(
            id=case.id,
            payment_id=case.payment_id,
            customer_id=case.customer_id,
            amount_at_risk=case.amount_at_risk,
            expected_recovery_value=case.expected_recovery_value,
            recovery_probability=case.recovery_probability,
            scorer_confidence=case.scorer_confidence,
            recommended_action=case.recommended_action,
            actual_action=case.actual_action,
            status=case.status,
            retry_count=case.retry_count,
            escalation_reason=case.escalation_reason,
            created_at=case.created_at.isoformat() if case.created_at else "",
            updated_at=case.updated_at.isoformat() if case.updated_at else "",
        )
        return ToolResult(success=True, tool_name="get_recovery_case", data=info.model_dump())

    @staticmethod
    def get_recovery_status(db: Session, case_id: int) -> ToolResult:
        """Fetch current lifecycle status, latest action, and outcome observation status."""
        if not isinstance(case_id, int) or case_id <= 0:
            return ToolResult(
                success=False,
                tool_name="get_recovery_status",
                error="Invalid case_id parameter. Must be a positive integer.",
            )

        case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
        if not case:
            return ToolResult(
                success=False,
                tool_name="get_recovery_status",
                error=f"Recovery case with ID {case_id} not found.",
            )

        latest_outcome = (
            db.query(RecoveryOutcome)
            .filter(RecoveryOutcome.recovery_case_id == case_id)
            .order_by(RecoveryOutcome.id.desc())
            .first()
        )

        latest_action_obj = (
            db.query(AgentAction)
            .filter(AgentAction.recovery_case_id == case_id)
            .order_by(AgentAction.id.desc())
            .first()
        )

        is_recovered = bool(latest_outcome and latest_outcome.outcome_status == "observed" and latest_outcome.successful)
        amount_recovered = latest_outcome.amount_recovered if is_recovered else 0.0

        status_info = RecoveryStatusInfo(
            case_id=case.id,
            case_status=case.status,
            retry_count=case.retry_count,
            latest_action=latest_action_obj.tool_name if latest_action_obj else None,
            action_type=latest_action_obj.action_type if latest_action_obj else None,
            outcome_status=latest_outcome.outcome_status if latest_outcome else None,
            outcome_source=latest_outcome.outcome_source if latest_outcome else None,
            is_recovered=is_recovered,
            amount_recovered=amount_recovered,
            action_executed_at=latest_outcome.action_executed_at.isoformat() if (latest_outcome and latest_outcome.action_executed_at) else None,
            outcome_observed_at=latest_outcome.outcome_observed_at.isoformat() if (latest_outcome and latest_outcome.outcome_observed_at) else None,
        )
        return ToolResult(success=True, tool_name="get_recovery_status", data=status_info.model_dump())
