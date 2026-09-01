"""Deterministic Simulation Outcome Engine for RecoverAI.

Generates realistic simulated post-action outcomes based strictly on observable context
and deterministic recovery probability.
Isolated from evaluation benchmarks.
"""

import random
from typing import Optional
from pydantic import BaseModel


class SimulatedOutcome(BaseModel):
    outcome: str  # "recovered" | "failed" | "escalated" | "stopped" | "timed_out"
    amount_recovered: float
    failure_reason: Optional[str] = None
    simulated_latency_ms: int = 150


class SimulationOutcomeEngine:
    """Simulates realistic post-action results without evaluation benchmark leakage."""

    @classmethod
    def generate_outcome(
        cls,
        action_type: str,
        payment_amount: float,
        failure_code: Optional[str],
        recovery_probability: float,
        customer_tenure_days: int = 100,
        historical_success_rate: float = 0.90,
        rng: Optional[random.Random] = None,
    ) -> SimulatedOutcome:
        """Deterministically simulate the real-world outcome of an executed recovery action."""
        r = rng or random.Random()
        action = (action_type or "").strip().lower()

        # 1. Terminal non-financial actions
        if action == "stop":
            return SimulatedOutcome(
                outcome="stopped",
                amount_recovered=0.0,
                failure_reason="Action was stopped by policy or customer opt-out.",
                simulated_latency_ms=10,
            )

        if action == "escalate":
            return SimulatedOutcome(
                outcome="escalated",
                amount_recovered=0.0,
                failure_reason="Assigned to merchant ops for human review.",
                simulated_latency_ms=50,
            )

        # 2. Financial recovery actions (retry or message)
        # Probability of success is bounded and driven by deterministic recovery_probability
        # with contextual adjustments for failure types
        base_prob = max(0.05, min(0.95, recovery_probability))

        # Contextual adjustment: transient network issues recover at slightly higher rates on retry
        if action == "retry":
            if failure_code in ("temporary_bank_error", "network_error", "bank_timeout"):
                adjusted_prob = min(0.96, base_prob * 1.05)
            else:
                adjusted_prob = base_prob * 0.90
        elif action == "message":
            if failure_code in ("expired_card", "invalid_card", "authentication_failed"):
                adjusted_prob = min(0.92, base_prob * 1.02)
            else:
                adjusted_prob = base_prob * 0.85
        else:
            adjusted_prob = base_prob

        # Roll against random generator
        roll = r.random()

        if roll < adjusted_prob:
            # Successfully recovered full transaction amount
            return SimulatedOutcome(
                outcome="recovered",
                amount_recovered=round(float(payment_amount), 2),
                failure_reason=None,
                simulated_latency_ms=r.randint(100, 350),
            )
        elif roll < (adjusted_prob + 0.05):
            # Timed out
            return SimulatedOutcome(
                outcome="failed",
                amount_recovered=0.0,
                failure_reason="Transaction timed out during simulation.",
                simulated_latency_ms=r.randint(400, 800),
            )
        else:
            # Failed
            return SimulatedOutcome(
                outcome="failed",
                amount_recovered=0.0,
                failure_reason=f"Recovery attempt failed to complete ({failure_code or 'payment_declined'}).",
                simulated_latency_ms=r.randint(150, 450),
            )
