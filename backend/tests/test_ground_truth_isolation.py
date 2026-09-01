"""Test to guarantee strict isolation of hidden ground truth from Phase 3, 4, 5, 6, & 7 services."""

import inspect
import os
import pytest

from app.services.eligibility import EligibilityGate
from app.services.risk_engine import RevenueRiskEngine
from app.services.recovery_scorer import RecoveryScorer
from app.services.revenue_metrics import RevenueMetricsService
from app.policies.policy_engine import PolicyEngine
from app.policies.message_templates import MessageTemplateEngine
from app.tools.read_tools import ReadTools
from app.tools.recovery_tools import RecoveryTools
from app.tools.outcome_tools import OutcomeObserver
from app.agent.orchestrator import AgentOrchestrator
from app.agent.llm_client import MockLLMClient, RealLLMClient
from app.agent.diagnoser import PaymentDiagnoser
from app.agent.decision import RecoveryDecisionEngine
from app.services.simulation_engine import SimulationOutcomeEngine
from app.services.simulation_service import SimulationRunner


class TestGroundTruthIsolation:
    """Verify that Phase 3, 4, 5, 6, and 7 services operate strictly on observable data and do not access ground truth."""

    def test_services_do_not_import_ground_truth_module(self):
        """Verify no service, policy, tool, agent, or simulation module imports ground_truth."""
        modules_to_check = (
            EligibilityGate,
            RevenueRiskEngine,
            RecoveryScorer,
            RevenueMetricsService,
            PolicyEngine,
            MessageTemplateEngine,
            ReadTools,
            RecoveryTools,
            OutcomeObserver,
            AgentOrchestrator,
            MockLLMClient,
            RealLLMClient,
            PaymentDiagnoser,
            RecoveryDecisionEngine,
            SimulationOutcomeEngine,
            SimulationRunner,
        )
        for service_cls in modules_to_check:
            module = inspect.getmodule(service_cls)
            source = inspect.getsource(module)

            assert "ground_truth" not in source.lower()
            assert "true_best_action" not in source
            assert "true_recoverable" not in source
            assert "true_recovery_outcome" not in source
            assert "true_amount_recovered" not in source
