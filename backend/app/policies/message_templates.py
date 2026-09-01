"""Approved Recovery Message Templates and Safety Validator for RecoverAI.

Defines the rigid, approved semantic structure for merchant-to-customer recovery communications.
Guarantees:
- No arbitrary payment instructions
- No invented discounts or amounts
- No credential requests (CVV, password, OTP, PIN)
- Strict placeholder validation and deterministic rendering
- Type contract for bounded LLM personalization
"""

import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TemplateId(str, Enum):
    PAYMENT_RETRY = "PAYMENT_RETRY"
    PAYMENT_UPDATE = "PAYMENT_UPDATE"
    PAYMENT_RECOVERY = "PAYMENT_RECOVERY"


class ApprovedTemplate(BaseModel):
    template_id: TemplateId
    subject: str
    body: str
    allowed_placeholders: list[str]


# ──────────────────────────────────────────────────
# Rigid Approved Templates
# ──────────────────────────────────────────────────
APPROVED_TEMPLATES: dict[TemplateId, ApprovedTemplate] = {
    TemplateId.PAYMENT_RETRY: ApprovedTemplate(
        template_id=TemplateId.PAYMENT_RETRY,
        subject="Action Required: Complete your payment for Order #{payment_reference}",
        body=(
            "Hi {customer_name}, we noticed your payment of {currency} {amount} "
            "for Order #{payment_reference} could not be processed due to a temporary network issue. "
            "{personalized_note}"
            "You can safely retry your payment anytime using your secure merchant link: #{payment_reference}."
        ),
        allowed_placeholders=["customer_name", "amount", "currency", "payment_reference", "personalized_note"],
    ),
    TemplateId.PAYMENT_UPDATE: ApprovedTemplate(
        template_id=TemplateId.PAYMENT_UPDATE,
        subject="Payment method update required for Order #{payment_reference}",
        body=(
            "Hi {customer_name}, your payment of {currency} {amount} for Order #{payment_reference} "
            "could not be completed with your current payment details. "
            "{personalized_note}"
            "Please update your payment method or select an alternative payment option to complete your order."
        ),
        allowed_placeholders=["customer_name", "amount", "currency", "payment_reference", "personalized_note"],
    ),
    TemplateId.PAYMENT_RECOVERY: ApprovedTemplate(
        template_id=TemplateId.PAYMENT_RECOVERY,
        subject="Complete your pending transaction for Order #{payment_reference}",
        body=(
            "Hi {customer_name}, we saved your order of {currency} {amount} (#{payment_reference}). "
            "{personalized_note}"
            "Click here to resume your checkout securely whenever you are ready."
        ),
        allowed_placeholders=["customer_name", "amount", "currency", "payment_reference", "personalized_note"],
    ),
}

# ──────────────────────────────────────────────────
# Prohibited Security Keywords
# ──────────────────────────────────────────────────
PROHIBITED_SECURITY_KEYWORDS = [
    "cvv",
    "pin",
    "password",
    "otp",
    "one-time password",
    "credit card number",
    "debit card number",
    "bank account number",
    "netbanking password",
    "discount",
    "waive",
    "free",
    "threat",
    "legal action",
    "arrest",
    "police",
    "already successful",
    "payment received",
]


class MessagePersonalizationContract(BaseModel):
    """Pydantic contract defining the validated payload for personalized message rendering."""
    template_id: TemplateId
    customer_name: str
    amount: str
    currency: str = "INR"
    payment_reference: str
    personalized_note: Optional[str] = ""


class RenderedMessage(BaseModel):
    template_id: TemplateId
    subject: str
    body: str
    customer_name: str
    amount: str
    currency: str
    payment_reference: str


class MessageTemplateEngine:
    """Deterministic message renderer and safety validator."""

    @classmethod
    def validate_personalized_note(cls, note: Optional[str]) -> tuple[bool, Optional[str]]:
        """Validate that a personalized note does not contain prohibited content or credentials."""
        if not note:
            return True, None

        note_lower = note.lower()

        # Check length
        if len(note) > 200:
            return False, "Personalized note exceeds maximum length of 200 characters."

        # Check prohibited security keywords
        for keyword in PROHIBITED_SECURITY_KEYWORDS:
            if re.search(rf"\b{re.escape(keyword)}\b", note_lower):
                return False, f"Prohibited content detected in note: '{keyword}'."

        # Check for unapproved external URLs (http/https)
        if re.search(r"https?://", note_lower):
            return False, "Arbitrary external URLs in personalized notes are prohibited."

        return True, None

    @classmethod
    def render(
        cls,
        contract: MessagePersonalizationContract,
    ) -> RenderedMessage:
        """Render approved message template strictly inserting validated variables."""
        template = APPROVED_TEMPLATES.get(contract.template_id)
        if not template:
            raise ValueError(f"Unknown template ID: '{contract.template_id}'.")

        # Clean personalized note
        note_str = (contract.personalized_note or "").strip()
        if note_str:
            is_valid, err = cls.validate_personalized_note(note_str)
            if not is_valid:
                raise ValueError(f"Message personalization validation failed: {err}")
            # Ensure it ends with a space if not empty
            note_str = f"{note_str} "

        # Clean and format variables
        vars_dict = {
            "customer_name": contract.customer_name.strip(),
            "amount": contract.amount.strip(),
            "currency": contract.currency.strip(),
            "payment_reference": contract.payment_reference.strip(),
            "personalized_note": note_str,
        }

        body = template.body
        subject = template.subject

        for key, val in vars_dict.items():
            body = body.replace(f"{{{key}}}", val)
            subject = subject.replace(f"{{{key}}}", val)

        # Check if any unresolved braces remain
        if re.search(r"\{[a-zA-Z0-9_]+\}", body) or re.search(r"\{[a-zA-Z0-9_]+\}", subject):
            raise ValueError("Template rendering left unresolved placeholders.")

        return RenderedMessage(
            template_id=contract.template_id,
            subject=subject,
            body=body,
            customer_name=contract.customer_name,
            amount=contract.amount,
            currency=contract.currency,
            payment_reference=contract.payment_reference,
        )
