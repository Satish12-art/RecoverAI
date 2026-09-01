"""Tool Registry for RecoverAI.

Registers all typed read and write tools, defining their input/output schemas,
read-only status, and policy engine enforcement requirements.
"""

from typing import Optional
from app.tools.tool_types import ToolDefinition, ToolType

TOOL_REGISTRY: dict[str, ToolDefinition] = {
    # ── Read Tools (7) ──
    "get_payment": ToolDefinition(
        name="get_payment",
        description="Retrieve production-facing payment details by payment ID.",
        tool_type=ToolType.READ,
        read_only=True,
        requires_policy=False,
        input_schema={"payment_id": "int"},
        output_schema={"payment": "PaymentInfo"},
    ),
    "get_order": ToolDefinition(
        name="get_order",
        description="Retrieve order details by order ID.",
        tool_type=ToolType.READ,
        read_only=True,
        requires_policy=False,
        input_schema={"order_id": "int"},
        output_schema={"order": "OrderInfo"},
    ),
    "get_customer": ToolDefinition(
        name="get_customer",
        description="Retrieve customer profile by customer ID.",
        tool_type=ToolType.READ,
        read_only=True,
        requires_policy=False,
        input_schema={"customer_id": "int"},
        output_schema={"customer": "CustomerInfo"},
    ),
    "get_customer_history": ToolDefinition(
        name="get_customer_history",
        description="Retrieve historical payment statistics, success rates, and chargeback metrics for a customer.",
        tool_type=ToolType.READ,
        read_only=True,
        requires_policy=False,
        input_schema={"customer_id": "int"},
        output_schema={"history": "CustomerHistoryContext"},
    ),
    "calculate_recovery_score": ToolDefinition(
        name="calculate_recovery_score",
        description="Calculate deterministic recovery probability, scorer confidence, and expected recovery value.",
        tool_type=ToolType.READ,
        read_only=True,
        requires_policy=False,
        input_schema={"payment_id": "int", "previous_recovery_attempts": "int (optional)"},
        output_schema={"recovery_score": "RecoveryScore"},
    ),
    "get_recovery_case": ToolDefinition(
        name="get_recovery_case",
        description="Retrieve recovery case details and state by case ID.",
        tool_type=ToolType.READ,
        read_only=True,
        requires_policy=False,
        input_schema={"case_id": "int"},
        output_schema={"case": "RecoveryCaseInfo"},
    ),
    "get_recovery_status": ToolDefinition(
        name="get_recovery_status",
        description="Retrieve the current lifecycle status, latest action, and outcome observation status of a case.",
        tool_type=ToolType.READ,
        read_only=True,
        requires_policy=False,
        input_schema={"case_id": "int"},
        output_schema={"status": "RecoveryStatusInfo"},
    ),

    # ── Write Tools (3) — All Strictly Policy-Gated ──
    "request_payment_retry": ToolDefinition(
        name="request_payment_retry",
        description="Request a bounded simulated payment retry. Strictly gated by PolicyEngine.",
        tool_type=ToolType.WRITE,
        read_only=False,
        requires_policy=True,
        input_schema={"case_id": "int", "idempotency_key": "str (optional)"},
        output_schema={"action_executed": "bool", "outcome_status": "str", "agent_action_id": "int"},
    ),
    "send_recovery_message": ToolDefinition(
        name="send_recovery_message",
        description="Send an approved recovery message template with bounded personalization. Strictly gated by PolicyEngine.",
        tool_type=ToolType.WRITE,
        read_only=False,
        requires_policy=True,
        input_schema={"case_id": "int", "template_id": "str", "personalized_note": "str (optional)"},
        output_schema={"action_executed": "bool", "message_subject": "str", "outcome_status": "str"},
    ),
    "escalate_to_human": ToolDefinition(
        name="escalate_to_human",
        description="Escalate a complex, high-value, or low-confidence recovery case to human review.",
        tool_type=ToolType.WRITE,
        read_only=False,
        requires_policy=True,
        input_schema={"case_id": "int", "reason": "str"},
        output_schema={"escalated": "bool", "case_id": "int", "reason": "str"},
    ),
}


class ToolRegistry:
    """Tool registry helper."""

    @classmethod
    def get_tool(cls, name: str) -> Optional[ToolDefinition]:
        return TOOL_REGISTRY.get(name)

    @classmethod
    def get_all_tools(cls) -> list[ToolDefinition]:
        return list(TOOL_REGISTRY.values())

    @classmethod
    def get_read_tools(cls) -> list[ToolDefinition]:
        return [t for t in TOOL_REGISTRY.values() if t.read_only]

    @classmethod
    def get_write_tools(cls) -> list[ToolDefinition]:
        return [t for t in TOOL_REGISTRY.values() if not t.read_only]
