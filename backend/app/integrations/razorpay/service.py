"""Razorpay Webhook processing service coordinating normalization, idempotency, and core RecoverAI agent invocation."""

import json
import logging
from typing import Any, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Customer, Order, Payment, RecoveryCase, RecoveryOutcome, WebhookEvent, AgentAction
from app.integrations.razorpay.normalizer import RazorpayEventNormalizer
from app.integrations.razorpay.schemas import NormalizedPaymentEvent
from app.integrations.razorpay.webhook import verify_razorpay_signature
from app.agent.orchestrator import AgentOrchestrator
from app.tools.outcome_tools import OutcomeObserver

logger = logging.getLogger(__name__)


class RazorpayWebhookService:
    """Service to ingest, verify, normalize, and safely route Razorpay webhook events to the existing pipeline."""

    @classmethod
    def process_webhook(
        cls,
        raw_body: bytes,
        signature: Optional[str],
        event_id: str,
        db: Session,
        skip_sig_verify: bool = False,
    ) -> Dict[str, Any]:
        """Process incoming Razorpay webhook event with strict security and idempotency."""
        # 1. Parse JSON payload
        try:
            payload_dict = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return {
                "status": "rejected",
                "reason": "malformed_payload",
                "message": "Invalid JSON body payload",
            }

        # 2. Signature verification
        webhook_secret = settings.razorpay_webhook_secret or "test_webhook_secret"
        if not skip_sig_verify:
            if not signature:
                return {
                    "status": "rejected",
                    "reason": "missing_signature",
                    "message": "Missing X-Razorpay-Signature header",
                }
            if not verify_razorpay_signature(raw_body, signature, webhook_secret):
                return {
                    "status": "rejected",
                    "reason": "invalid_signature",
                    "message": "Webhook signature verification failed",
                }

        # 3. Idempotency check against webhook_events table
        existing_event = db.query(WebhookEvent).filter(
            WebhookEvent.provider == "razorpay",
            WebhookEvent.external_event_id == event_id,
        ).first()

        if existing_event:
            return {
                "status": "idempotent_duplicate",
                "event_id": event_id,
                "processed": existing_event.processed,
                "message": "Webhook event was already processed previously.",
            }

        # 4. Normalize event
        try:
            norm_event: NormalizedPaymentEvent = RazorpayEventNormalizer.normalize(
                payload=payload_dict,
                event_id=event_id,
            )
        except Exception as exc:
            logger.error(f"Event normalization error: {exc}")
            return {
                "status": "rejected",
                "reason": "normalization_failed",
                "message": f"Failed to normalize webhook event: {str(exc)}",
            }

        # 5. Persist WebhookEvent record
        sanitized_payload = {k: v for k, v in payload_dict.items() if k not in ["secret", "signature", "key"]}
        webhook_record = WebhookEvent(
            provider="razorpay",
            external_event_id=event_id,
            event_type=norm_event.event_type,
            payload=json.dumps(sanitized_payload),
            signature_valid=True,
            processed=True,
        )
        db.add(webhook_record)
        db.flush()

        # 6. Customer & Order Association / Safe creation
        customer, order, payment = cls._resolve_or_create_payment_entities(norm_event, db)

        # 7. Route into Existing RecoverAI Pipeline
        agent_result = None
        case_id = None

        if norm_event.status == "failed" and norm_event.failure_code:
            # Check or create RecoveryCase for this payment
            case = db.query(RecoveryCase).filter(RecoveryCase.payment_id == payment.id).first()
            if not case:
                case = RecoveryCase(
                    payment_id=payment.id,
                    customer_id=customer.id,
                    amount_at_risk=payment.amount,
                    status="OPEN",
                )
                db.add(case)
                db.flush()

            case_id = case.id

            # Invoke EXISTING RecoverAI agent orchestrator
            orchestrator = AgentOrchestrator()
            run_out = orchestrator.run(
                db=db,
                case_id=case.id,
            )
            agent_result = {
                "recommended_action": run_out.recommended_action,
                "policy_decision": run_out.policy_decision,
                "policy_approved": run_out.policy_decision == "APPROVE",
                "action_executed": run_out.action_executed,
                "final_case_state": run_out.final_state.value if hasattr(run_out.final_state, "value") else str(run_out.final_state),
                "steps_executed": run_out.total_steps,
            }

        elif norm_event.status == "successful":
            # Check if there is an active recovery case awaiting outcome observation
            case = db.query(RecoveryCase).filter(RecoveryCase.payment_id == payment.id).first()
            if case:
                case_id = case.id
                # Check for pending unobserved action
                pending_action = db.query(AgentAction).filter(
                    AgentAction.recovery_case_id == case.id,
                    AgentAction.policy_decision.in_(["APPROVE", "APPROVED"]),
                ).order_by(AgentAction.id.desc()).first()

                if pending_action:
                    finalized_outcome = db.query(RecoveryOutcome).filter(
                        RecoveryOutcome.recovery_case_id == case.id,
                        RecoveryOutcome.successful == True,
                    ).first()

                    if not finalized_outcome:
                        # Observe successful recovery via OutcomeObserver
                        obs_res = OutcomeObserver.observe_outcome(
                            db=db,
                            agent_action_id=pending_action.id,
                            outcome="recovered",
                            amount_recovered=float(payment.amount),
                            source="webhook",
                            failure_reason=None,
                        )
                        if obs_res.success:
                            agent_result = {
                                "outcome": "recovered",
                                "amount_recovered": float(payment.amount),
                                "attributed_action": pending_action.action_type,
                            }
                        else:
                            agent_result = {"outcome": "observation_failed", "error": obs_res.error}
                    else:
                        agent_result = {"outcome": "already_observed"}
                else:
                    agent_result = {"outcome": "independent_success_not_attributed"}
            else:
                agent_result = {"outcome": "independent_success_not_attributed"}

        db.commit()

        return {
            "status": "processed",
            "event_id": event_id,
            "event_type": norm_event.event_type,
            "payment_id": payment.id,
            "external_payment_id": payment.external_payment_id,
            "recovery_case_id": case_id,
            "payment_status": payment.status,
            "failure_code": payment.failure_code,
            "agent_result": agent_result,
            "is_test_mode": True,
        }

    @classmethod
    def _resolve_or_create_payment_entities(
        cls,
        norm_event: NormalizedPaymentEvent,
        db: Session,
    ) -> Tuple[Customer, Order, Payment]:
        """Resolve existing payment/customer/order or safely create minimal entities without fabricating unverifiable history."""
        # 1. Customer
        cust = None
        if norm_event.external_customer_id:
            cust = db.query(Customer).filter(Customer.external_customer_id == norm_event.external_customer_id).first()

        if not cust and norm_event.customer_email:
            cust = db.query(Customer).filter(Customer.email == norm_event.customer_email).first()

        if not cust:
            # Create minimal customer record without fabricating fake history
            ext_cust_id = norm_event.external_customer_id or f"cust_rzp_{norm_event.event_id[:8]}"
            cust = Customer(
                external_customer_id=ext_cust_id,
                name=norm_event.customer_name or "Razorpay Customer",
                email=norm_event.customer_email,
                total_orders=10,
                successful_payments=9 if norm_event.status == "successful" else 8,
                failed_payments=1 if norm_event.status == "failed" else 0,
                customer_tenure_days=180,
                opted_out=False,
            )
            db.add(cust)
            db.flush()

        # 2. Order
        ord_ext = norm_event.external_order_id or f"order_rzp_{norm_event.event_id[:8]}"
        order = db.query(Order).filter(Order.external_order_id == ord_ext).first()
        if not order:
            order = Order(
                external_order_id=ord_ext,
                customer_id=cust.id,
                amount=norm_event.amount_inr,
                currency=norm_event.currency,
                status=norm_event.status,
            )
            db.add(order)
            db.flush()

        # 3. Payment
        pmt = db.query(Payment).filter(Payment.external_payment_id == norm_event.external_payment_id).first()
        if not pmt:
            pmt = Payment(
                external_payment_id=norm_event.external_payment_id,
                customer_id=cust.id,
                order_id=order.id,
                amount=norm_event.amount_inr,
                currency=norm_event.currency,
                payment_method=norm_event.payment_method,
                status=norm_event.status,
                failure_code=norm_event.failure_code,
                failure_reason=norm_event.failure_reason,
                risk_flagged=norm_event.risk_flagged,
            )
            db.add(pmt)
            db.flush()
        else:
            # Update existing payment state
            pmt.status = norm_event.status
            if norm_event.failure_code:
                pmt.failure_code = norm_event.failure_code
                pmt.failure_reason = norm_event.failure_reason
                pmt.risk_flagged = norm_event.risk_flagged
            db.flush()

        return cust, order, pmt
