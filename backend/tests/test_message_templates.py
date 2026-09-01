"""Unit tests for RecoverAI Approved Message Templates and Safety Validator."""

import pytest
from app.policies.message_templates import (
    TemplateId,
    APPROVED_TEMPLATES,
    MessagePersonalizationContract,
    MessageTemplateEngine,
)


class TestMessageTemplates:
    """Test approved message template rendering and safety boundaries."""

    def test_all_approved_templates_exist(self):
        assert TemplateId.PAYMENT_RETRY in APPROVED_TEMPLATES
        assert TemplateId.PAYMENT_UPDATE in APPROVED_TEMPLATES
        assert TemplateId.PAYMENT_RECOVERY in APPROVED_TEMPLATES

    def test_render_payment_retry_template(self):
        contract = MessagePersonalizationContract(
            template_id=TemplateId.PAYMENT_RETRY,
            customer_name="Rahul Sharma",
            amount="4,999.00",
            currency="INR",
            payment_reference="pay_0000001",
            personalized_note="We have preserved your reserved item.",
        )
        rendered = MessageTemplateEngine.render(contract)

        assert "Rahul Sharma" in rendered.body
        assert "INR 4,999.00" in rendered.body
        assert "pay_0000001" in rendered.body
        assert "We have preserved your reserved item." in rendered.body
        assert "pay_0000001" in rendered.subject

    def test_render_payment_update_template(self):
        contract = MessagePersonalizationContract(
            template_id=TemplateId.PAYMENT_UPDATE,
            customer_name="Priya Patel",
            amount="8,999.00",
            currency="INR",
            payment_reference="pay_0000002",
        )
        rendered = MessageTemplateEngine.render(contract)

        assert "Priya Patel" in rendered.body
        assert "INR 8,999.00" in rendered.body
        assert "pay_0000002" in rendered.body

    def test_render_payment_recovery_template(self):
        contract = MessagePersonalizationContract(
            template_id=TemplateId.PAYMENT_RECOVERY,
            customer_name="Vikram Malhotra",
            amount="1,200.00",
            currency="INR",
            payment_reference="pay_0000003",
        )
        rendered = MessageTemplateEngine.render(contract)

        assert "Vikram Malhotra" in rendered.body
        assert "INR 1,200.00" in rendered.body
        assert "pay_0000003" in rendered.body

    def test_prohibit_sensitive_credential_requests(self):
        """Security check: Reject notes requesting CVV, OTP, passwords, or PINs."""
        sensitive_phrases = [
            "Please reply with your CVV to complete payment.",
            "Send us your OTP code.",
            "Provide your netbanking password.",
            "Enter your ATM PIN here.",
            "Reply with your credit card number.",
        ]

        for phrase in sensitive_phrases:
            contract = MessagePersonalizationContract(
                template_id=TemplateId.PAYMENT_RETRY,
                customer_name="User",
                amount="1000",
                payment_reference="pay_1",
                personalized_note=phrase,
            )
            with pytest.raises(ValueError, match="Prohibited content detected"):
                MessageTemplateEngine.render(contract)

    def test_prohibit_discounts_and_promotions(self):
        """Security check: Reject notes inventing discounts or waivers."""
        discount_phrases = [
            "We offer a 20% discount on this payment.",
            "We will waive your shipping fee.",
            "Get free delivery now.",
        ]

        for phrase in discount_phrases:
            contract = MessagePersonalizationContract(
                template_id=TemplateId.PAYMENT_RETRY,
                customer_name="User",
                amount="1000",
                payment_reference="pay_1",
                personalized_note=phrase,
            )
            with pytest.raises(ValueError, match="Prohibited content detected"):
                MessageTemplateEngine.render(contract)

    def test_prohibit_threats(self):
        """Security check: Reject threatening language."""
        threat_phrases = [
            "Legal action will be taken if unpaid.",
            "Police will be notified immediately.",
            "We will issue an arrest notice.",
        ]

        for phrase in threat_phrases:
            contract = MessagePersonalizationContract(
                template_id=TemplateId.PAYMENT_RETRY,
                customer_name="User",
                amount="1000",
                payment_reference="pay_1",
                personalized_note=phrase,
            )
            with pytest.raises(ValueError, match="Prohibited content detected"):
                MessageTemplateEngine.render(contract)

    def test_prohibit_arbitrary_external_urls(self):
        """Security check: Reject arbitrary phishing/external links."""
        url_phrases = [
            "Click https://phishing-site.com/pay to complete.",
            "Visit http://recover-funds-fast.net now.",
        ]

        for phrase in url_phrases:
            contract = MessagePersonalizationContract(
                template_id=TemplateId.PAYMENT_RETRY,
                customer_name="User",
                amount="1000",
                payment_reference="pay_1",
                personalized_note=phrase,
            )
            with pytest.raises(ValueError, match="Arbitrary external URLs"):
                MessageTemplateEngine.render(contract)

    def test_enforce_personalized_note_max_length(self):
        long_note = "A" * 250
        contract = MessagePersonalizationContract(
            template_id=TemplateId.PAYMENT_RETRY,
            customer_name="User",
            amount="1000",
            payment_reference="pay_1",
            personalized_note=long_note,
        )
        with pytest.raises(ValueError, match="exceeds maximum length"):
            MessageTemplateEngine.render(contract)

    def test_deterministic_rendering(self):
        contract = MessagePersonalizationContract(
            template_id=TemplateId.PAYMENT_RETRY,
            customer_name="Sameer",
            amount="3,500.00",
            payment_reference="pay_12345",
            personalized_note="Your order is currently held.",
        )
        res1 = MessageTemplateEngine.render(contract)
        res2 = MessageTemplateEngine.render(contract)

        assert res1.body == res2.body
        assert res1.subject == res2.subject
