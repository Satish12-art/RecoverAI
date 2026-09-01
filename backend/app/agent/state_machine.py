"""State machine transition validator for RecoverAI."""

from app.agent.state import AgentStep, TerminalState

ALLOWED_TRANSITIONS = {
    AgentStep.DETECTED: {AgentStep.ELIGIBILITY_CHECK, AgentStep.TERMINAL},
    AgentStep.ELIGIBILITY_CHECK: {AgentStep.CONTEXT_LOADING, AgentStep.TERMINAL},
    AgentStep.CONTEXT_LOADING: {AgentStep.SCORING, AgentStep.TERMINAL},
    AgentStep.SCORING: {AgentStep.DIAGNOSING, AgentStep.TERMINAL},
    AgentStep.DIAGNOSING: {AgentStep.DECISION_PENDING, AgentStep.TERMINAL},
    AgentStep.DECISION_PENDING: {AgentStep.POLICY_CHECK, AgentStep.TERMINAL},
    AgentStep.POLICY_CHECK: {AgentStep.ACTION_EXECUTION, AgentStep.TERMINAL},
    AgentStep.ACTION_EXECUTION: {AgentStep.OBSERVING_RESULT, AgentStep.TERMINAL},
    AgentStep.OBSERVING_RESULT: {AgentStep.TERMINAL},
    AgentStep.TERMINAL: set(),
}


def is_valid_transition(from_step: AgentStep, to_step: AgentStep) -> bool:
    """Validate that state machine step transition is explicitly allowed."""
    return to_step in ALLOWED_TRANSITIONS.get(from_step, set())
