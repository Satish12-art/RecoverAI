"""RecoverAI Evaluation Framework Package."""

from app.evaluation.ground_truth_loader import GroundTruthLoader, GroundTruthRecord
from app.evaluation.baseline import NaiveRetryBaseline, BaselineDecision
from app.evaluation.metrics import (
    PerClassMetrics,
    ActionClassificationMetrics,
    RecoverabilityClassificationMetrics,
    MetricsCalculator,
)
from app.evaluation.calibration import CalibrationBin, CalibrationReport, CalibrationCalculator
from app.evaluation.regret import RegretReport, RegretCalculator
from app.evaluation.revenue import RevenueComparisonReport, RevenueEvaluator
from app.evaluation.safety import SafetyMetricsReport, SafetyEvaluator
from app.evaluation.evaluator import EvaluationOrchestrator, EvaluationReport, EfficiencyMetrics

__all__ = [
    "GroundTruthLoader",
    "GroundTruthRecord",
    "NaiveRetryBaseline",
    "BaselineDecision",
    "PerClassMetrics",
    "ActionClassificationMetrics",
    "RecoverabilityClassificationMetrics",
    "MetricsCalculator",
    "CalibrationBin",
    "CalibrationReport",
    "CalibrationCalculator",
    "RegretReport",
    "RegretCalculator",
    "RevenueComparisonReport",
    "RevenueEvaluator",
    "SafetyMetricsReport",
    "SafetyEvaluator",
    "EvaluationOrchestrator",
    "EvaluationReport",
    "EfficiencyMetrics",
]
