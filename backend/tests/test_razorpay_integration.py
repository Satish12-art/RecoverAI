"""Unit and integration tests for Phase 10 Razorpay Test-Mode Integration."""

import json
import uuid
import hmac
import hashlib
import pytest
from app.core.config import settings
from app.models.models import Customer, Order, Payment, RecoveryCase, WebhookEvent, AgentAction, RecoveryOutcome
from app.integrations.razorpay.webhook import verify_razorpay_signature
from app.integrations.razorpay.normalizer import RazorpayEventNormalizer
from app.integrations.razorpay.client import RazorpayTestClient
from app.integrations.razorpay.service import RazorpayWebhookService
from app.policies.message_templates import MessageTemplateEngine, TemplateId


def _generate_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


class TestRazorpaySecurityAndSignature:
    """Test webhook signature verification and secret protection."""

    def test_valid_signature_passes(self):
        secret = "test_secret_123"
        body = b'{"event": "payment.failed"}'
        sig = _generate_signature(body, secret)
        assert verify_razorpay_signature(body, sig, secret) is True

    def test_invalid_signature_fails(self):
        secret = "test_secret_123"
        body = b'{"event": "payment.failed"}'
        assert verify_razorpay_signature(body, "invalid_sig_hex", secret) is False

    def test_missing_signature_fails(self):
        secret = "test_secret_123"
        body = b'{"event": "payment.failed"}'
        assert verify_razorpay_signature(body, None, secret) is False

    def test_missing_secret_fails(self):
        body = b'{"event": "payment.failed"}'
        assert verify_razorpay_signature(body, "some_sig", "") is False

    def test_secrets_not_exposed_in_client(self):
        # Client link generation returns only public URLs and identifiers
        link = RazorpayTestClient.generate_payment_update_link(
            payment_id="pay_test_001",
            amount_inr=4999.0,
            customer_email="customer@example.com",
        )
        assert link.is_test_mode is True
        assert "rzp.io" in link.short_url
        assert "secret" not in link.model_dump()
        assert "key_secret" not in link.model_dump()

    def test_sensitive_credentials_not_in_payload_record(self, db):
        secret = settings.razorpay_webhook_secret or "test_webhook_secret"
        event_id = f"evt_sens_{uuid.uuid4().hex[:8]}"
        payload = {
            "event": "payment.failed",
            "secret": "leaked_secret_key",
            "key": "leaked_api_key",
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_sens_{uuid.uuid4().hex[:8]}",
                        "amount": 200000,
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_reason": "network_error",
                    }
                }
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        sig = _generate_signature(raw_body, secret)
        RazorpayWebhookService.process_webhook(raw_body, sig, event_id, db)

        webhook_rec = db.query(WebhookEvent).filter(WebhookEvent.external_event_id == event_id).first()
        assert webhook_rec is not None
        assert "leaked_secret_key" not in webhook_rec.payload


class TestRazorpayNormalization:
    """Test event mapping from Razorpay error payload to RecoverAI canonical schema."""

    def test_failed_bank_error_normalization(self):
        raw = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_001",
                        "amount": 499900,  # ₹4,999.00
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_reason": "temporary_bank_error",
                        "error_description": "Issuing bank communication timeout.",
                        "email": "user@example.com",
                    }
                }
            },
        }
        norm = RazorpayEventNormalizer.normalize(raw, "evt_001")
        assert norm.event_id == "evt_001"
        assert norm.amount_inr == 4999.00
        assert norm.status == "failed"
        assert norm.failure_code == "temporary_bank_error"
        assert norm.risk_flagged is False
        assert norm.is_test_mode is True

    def test_risk_flagged_error_normalization(self):
        raw = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_002",
                        "amount": 120000,
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_code": "GATEWAY_ERROR",
                        "error_reason": "fraud_risk_detected",
                        "error_description": "Card blacklisted due to suspicious velocity.",
                        "email": "badactor@example.com",
                    }
                }
            },
        }
        norm = RazorpayEventNormalizer.normalize(raw, "evt_002")
        assert norm.failure_code == "risk_flagged"
        assert norm.risk_flagged is True

    def test_expired_card_error_normalization(self):
        raw = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_002b",
                        "amount": 150000,
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_code": "CARD_EXPIRED",
                        "error_reason": "card_expired",
                        "error_description": "Card has reached validity expiry.",
                        "email": "cardholder@example.com",
                    }
                }
            },
        }
        norm = RazorpayEventNormalizer.normalize(raw, "evt_002b")
        assert norm.failure_code == "expired_card"

    def test_captured_payment_normalization(self):
        raw = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_003",
                        "amount": 250000,
                        "currency": "INR",
                        "status": "captured",
                        "method": "upi",
                        "email": "good@example.com",
                    }
                }
            },
        }
        norm = RazorpayEventNormalizer.normalize(raw, "evt_003")
        assert norm.status == "successful"
        assert norm.failure_code is None

    def test_unknown_event_normalization(self):
        raw = {
            "event": "refund.created",
            "payload": {
                "refund": {
                    "entity": {
                        "id": "rfnd_test_001",
                        "amount": 50000,
                        "status": "processed",
                    }
                }
            },
        }
        norm = RazorpayEventNormalizer.normalize(raw, "evt_004")
        assert norm.event_type == "refund.created"
        assert norm.failure_code is None


class TestRazorpayWebhookServiceLifecycle:
    """Test full webhook processing, idempotency, case creation, and agent invocation."""

    def test_malformed_payload_rejected(self, db):
        res = RazorpayWebhookService.process_webhook(
            raw_body=b'not valid json',
            signature="any_sig",
            event_id="evt_malformed",
            db=db,
            skip_sig_verify=True,
        )
        assert res["status"] == "rejected"
        assert res["reason"] == "malformed_payload"

    def test_failed_webhook_creates_case_and_triggers_agent(self, db):
        secret = settings.razorpay_webhook_secret or "test_webhook_secret"
        event_id = f"evt_test_{uuid.uuid4().hex[:8]}"
        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_test_{uuid.uuid4().hex[:8]}",
                        "amount": 499900,  # ₹4,999.00
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_reason": "temporary_bank_error",
                        "error_description": "Bank timeout",
                        "email": "customer.test@example.com",
                        "notes": {"customer_name": "Test User"},
                    }
                }
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        sig = _generate_signature(raw_body, secret)

        res = RazorpayWebhookService.process_webhook(
            raw_body=raw_body,
            signature=sig,
            event_id=event_id,
            db=db,
        )

        assert res["status"] == "processed"
        assert res["failure_code"] == "temporary_bank_error"
        assert res["recovery_case_id"] is not None
        assert res["agent_result"] is not None
        assert res["agent_result"]["policy_approved"] is True
        assert res["agent_result"]["action_executed"] is True

        # Verify WebhookEvent stored
        webhook_rec = db.query(WebhookEvent).filter(WebhookEvent.external_event_id == event_id).first()
        assert webhook_rec is not None
        assert webhook_rec.processed is True

        # Verify RecoveryCase exists
        case = db.query(RecoveryCase).filter(RecoveryCase.id == res["recovery_case_id"]).first()
        assert case is not None
        assert case.status == "RECOVERING"

    def test_duplicate_recovery_case_not_created_for_same_payment(self, db):
        secret = settings.razorpay_webhook_secret or "test_webhook_secret"
        pmt_id = f"pay_same_{uuid.uuid4().hex[:8]}"
        
        # Delivery 1
        ev1 = f"evt_1_{uuid.uuid4().hex[:8]}"
        p1 = {"event": "payment.failed", "payload": {"payment": {"entity": {"id": pmt_id, "amount": 300000, "status": "failed", "error_code": "BAD_REQUEST_ERROR", "error_reason": "temporary_bank_error"}}}}
        raw1 = json.dumps(p1).encode("utf-8")
        res1 = RazorpayWebhookService.process_webhook(raw1, _generate_signature(raw1, secret), ev1, db)
        case_id1 = res1["recovery_case_id"]

        # Delivery 2 (different webhook event ID for same payment ID)
        ev2 = f"evt_2_{uuid.uuid4().hex[:8]}"
        p2 = {"event": "payment.failed", "payload": {"payment": {"entity": {"id": pmt_id, "amount": 300000, "status": "failed", "error_code": "BAD_REQUEST_ERROR", "error_reason": "temporary_bank_error"}}}}
        raw2 = json.dumps(p2).encode("utf-8")
        res2 = RazorpayWebhookService.process_webhook(raw2, _generate_signature(raw2, secret), ev2, db)
        case_id2 = res2["recovery_case_id"]

        assert case_id1 == case_id2
        # Exactly one recovery case in DB for this payment
        count = db.query(RecoveryCase).filter(RecoveryCase.payment_id == res1["payment_id"]).count()
        assert count == 1

    def test_idempotent_duplicate_webhook_does_not_reprocess(self, db):
        secret = settings.razorpay_webhook_secret or "test_webhook_secret"
        event_id = f"evt_dup_{uuid.uuid4().hex[:8]}"
        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_dup_{uuid.uuid4().hex[:8]}",
                        "amount": 299900,
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_reason": "expired_card",
                        "error_description": "Card expired",
                        "email": "dup@example.com",
                    }
                }
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        sig = _generate_signature(raw_body, secret)

        # First delivery
        res1 = RazorpayWebhookService.process_webhook(raw_body, sig, event_id, db)
        assert res1["status"] == "processed"

        # Second delivery (Duplicate)
        res2 = RazorpayWebhookService.process_webhook(raw_body, sig, event_id, db)
        assert res2["status"] == "idempotent_duplicate"

        # Verify exactly 1 webhook_events row
        count = db.query(WebhookEvent).filter(WebhookEvent.external_event_id == event_id).count()
        assert count == 1

    def test_successful_webhook_updates_payment_without_false_attribution(self, db):
        secret = settings.razorpay_webhook_secret or "test_webhook_secret"
        event_id = f"evt_succ_{uuid.uuid4().hex[:8]}"
        pmt_id = f"pay_succ_{uuid.uuid4().hex[:8]}"
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": pmt_id,
                        "amount": 150000,
                        "currency": "INR",
                        "status": "captured",
                        "method": "upi",
                        "email": "independent@example.com",
                    }
                }
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        sig = _generate_signature(raw_body, secret)

        res = RazorpayWebhookService.process_webhook(raw_body, sig, event_id, db)
        assert res["status"] == "processed"
        assert res["payment_status"] == "successful"
        # Independent success without active agent action is not attributed to RecoverAI
        assert res["agent_result"]["outcome"] == "independent_success_not_attributed"

    def test_successful_webhook_observes_active_recovery_outcome(self, db):
        # 1. First inject failed payment and agent retry
        secret = settings.razorpay_webhook_secret or "test_webhook_secret"
        fail_event_id = f"evt_f_{uuid.uuid4().hex[:8]}"
        pmt_id = f"pay_linked_{uuid.uuid4().hex[:8]}"
        fail_payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": pmt_id,
                        "amount": 499900,
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_reason": "temporary_bank_error",
                        "email": "linked@example.com",
                    }
                }
            },
        }
        res_fail = RazorpayWebhookService.process_webhook(
            json.dumps(fail_payload).encode("utf-8"),
            _generate_signature(json.dumps(fail_payload).encode("utf-8"), secret),
            fail_event_id,
            db,
        )
        case_id = res_fail["recovery_case_id"]
        assert case_id is not None

        # 2. Later, webhook arrives confirming payment was captured
        succ_event_id = f"evt_s_{uuid.uuid4().hex[:8]}"
        succ_payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": pmt_id,
                        "amount": 499900,
                        "currency": "INR",
                        "status": "captured",
                        "method": "card",
                        "email": "linked@example.com",
                    }
                }
            },
        }
        res_succ = RazorpayWebhookService.process_webhook(
            json.dumps(succ_payload).encode("utf-8"),
            _generate_signature(json.dumps(succ_payload).encode("utf-8"), secret),
            succ_event_id,
            db,
        )
        assert res_succ["status"] == "processed"
        assert res_succ["agent_result"]["outcome"] == "recovered"
        assert res_succ["agent_result"]["amount_recovered"] == 4999.0

        # Verify outcome in DB
        outcome = db.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == case_id).first()
        assert outcome is not None
        assert outcome.successful is True
        assert outcome.amount_recovered == 4999.0

    def test_message_template_enforcement_with_razorpay_link(self):
        from app.policies.message_templates import MessagePersonalizationContract
        link_res = RazorpayTestClient.generate_payment_update_link("pay_123", 4999.0)
        contract = MessagePersonalizationContract(
            template_id=TemplateId.PAYMENT_UPDATE,
            customer_name="John Doe",
            amount="4,999.00",
            currency="INR",
            payment_reference="ORD_12345",
            personalized_note="Please update your card details.",
        )
        msg = MessageTemplateEngine.render(contract)
        assert msg is not None
        assert "John Doe" in msg.body
        assert "4,999.00" in msg.body


class TestRazorpayApiEndpoints:
    """Test FastAPI endpoints for Razorpay integration."""

    def test_status_endpoint(self, client):
        res = client.get("/api/webhooks/razorpay/status")
        assert res.status_code == 200
        data = res.json()
        assert data["mode"] == "test_mode"
        assert data["webhook_ready"] is True
        assert "configured" in data

    def test_interactive_test_trigger_endpoint(self, client):
        payload = {
            "event_type": "payment.failed",
            "amount": 3500.0,
            "failure_code": "BAD_REQUEST_ERROR",
            "failure_reason": "temporary_bank_error",
            "customer_email": "demo.judge@example.com",
            "customer_name": "Demo Judge",
        }
        res = client.post("/api/webhooks/razorpay/test-trigger", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["trigger"] == "success"
        assert data["is_test_mode"] is True
        assert data["result"]["status"] == "processed"
        assert data["result"]["recovery_case_id"] is not None


class TestGroundTruthIsolationForRazorpay:
    """Verify that the Razorpay integration package is completely ground-truth blind."""

    def test_razorpay_package_does_not_import_ground_truth(self):
        import inspect
        import app.integrations.razorpay.service as s_mod
        import app.integrations.razorpay.normalizer as n_mod
        import app.integrations.razorpay.client as c_mod
        import app.integrations.razorpay.webhook as w_mod

        modules = [s_mod, n_mod, c_mod, w_mod]
        for m in modules:
            src = inspect.getsource(m)
            assert "ground_truth" not in src.lower()
            assert "true_best_action" not in src
            assert "true_recoverable" not in src
            assert "true_amount_recovered" not in src
