"""Trace collector for RecoverAI Agent execution steps."""

from datetime import datetime, timezone
from typing import Any, Optional
from app.agent.state import AgentStep, StepTrace


class AgentTraceCollector:
    """Collects structured step traces without storing hidden chain-of-thought."""

    def __init__(self):
        self.traces: list[StepTrace] = []

    def log_step(
        self,
        step: AgentStep,
        status: str,
        details: Optional[dict[str, Any]] = None,
    ) -> StepTrace:
        """Record an execution step."""
        trace = StepTrace(
            step=step,
            status=status,
            details=details or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.traces.append(trace)
        return trace

    def get_traces(self) -> list[StepTrace]:
        return self.traces
