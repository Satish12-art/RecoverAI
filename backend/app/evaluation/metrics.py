"""Classification and Confusion Matrix Metrics for Action and Recoverability."""

from typing import Any
from pydantic import BaseModel, Field


class PerClassMetrics(BaseModel):
    precision: float
    recall: float
    f1_score: float
    support: int


class ActionClassificationMetrics(BaseModel):
    confusion_matrix_raw: dict[str, dict[str, int]]
    confusion_matrix_normalized: dict[str, dict[str, float]]
    per_action: dict[str, PerClassMetrics]
    macro_precision: float
    macro_recall: float
    macro_f1: float
    weighted_f1: float
    overall_accuracy: float


class RecoverabilityClassificationMetrics(BaseModel):
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    accuracy: float


class MetricsCalculator:
    """Computes exact statistical classification metrics."""

    ACTIONS = ["retry", "message", "escalate", "stop"]

    @classmethod
    def compute_action_metrics(
        cls,
        predicted_actions: list[str],
        true_actions: list[str],
    ) -> ActionClassificationMetrics:
        """Compute 4x4 confusion matrix, precision, recall, and F1 scores."""
        n = len(predicted_actions)
        if n == 0 or len(true_actions) != n:
            raise ValueError(f"Mismatched or empty action lists: pred={len(predicted_actions)}, true={len(true_actions)}")

        # Initialize raw matrix [pred][true]
        raw_matrix: dict[str, dict[str, int]] = {
            p: {t: 0 for t in cls.ACTIONS} for p in cls.ACTIONS
        }
        for p, t in zip(predicted_actions, true_actions):
            p_norm = p.lower() if p.lower() in cls.ACTIONS else "stop"
            t_norm = t.lower() if t.lower() in cls.ACTIONS else "stop"
            raw_matrix[p_norm][t_norm] += 1

        # Normalized matrix (by true column totals)
        norm_matrix: dict[str, dict[str, float]] = {
            p: {t: 0.0 for t in cls.ACTIONS} for p in cls.ACTIONS
        }
        true_totals = {t: sum(raw_matrix[p][t] for p in cls.ACTIONS) for t in cls.ACTIONS}

        for p in cls.ACTIONS:
            for t in cls.ACTIONS:
                tot = true_totals[t]
                norm_matrix[p][t] = round((raw_matrix[p][t] / tot * 100.0) if tot > 0 else 0.0, 2)

        # Per-action precision, recall, F1
        per_action: dict[str, PerClassMetrics] = {}
        precisions = []
        recalls = []
        f1s = []
        supports = []

        total_correct = 0

        for a in cls.ACTIONS:
            tp = raw_matrix[a][a]
            total_pred = sum(raw_matrix[a][t] for t in cls.ACTIONS)
            total_true = true_totals[a]
            total_correct += tp

            prec = (tp / total_pred) if total_pred > 0 else 0.0
            rec = (tp / total_true) if total_true > 0 else 0.0
            f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

            per_action[a] = PerClassMetrics(
                precision=round(prec, 4),
                recall=round(rec, 4),
                f1_score=round(f1, 4),
                support=total_true,
            )
            precisions.append(prec)
            recalls.append(rec)
            f1s.append(f1)
            supports.append(total_true)

        macro_p = sum(precisions) / len(precisions) if precisions else 0.0
        macro_r = sum(recalls) / len(recalls) if recalls else 0.0
        macro_f1 = (2 * macro_p * macro_r / (macro_p + macro_r)) if (macro_p + macro_r) > 0 else 0.0

        total_support = sum(supports)
        weighted_f1 = (
            sum(f1 * sup for f1, sup in zip(f1s, supports)) / total_support
            if total_support > 0
            else 0.0
        )

        return ActionClassificationMetrics(
            confusion_matrix_raw=raw_matrix,
            confusion_matrix_normalized=norm_matrix,
            per_action=per_action,
            macro_precision=round(macro_p, 4),
            macro_recall=round(macro_r, 4),
            macro_f1=round(macro_f1, 4),
            weighted_f1=round(weighted_f1, 4),
            overall_accuracy=round(total_correct / n, 4),
        )

    @classmethod
    def compute_recoverability_metrics(
        cls,
        predicted_probabilities: list[float],
        true_recoverable_flags: list[bool],
        threshold: float = 0.60,
    ) -> RecoverabilityClassificationMetrics:
        """Compute binary classification metrics against true_recoverable."""
        tp = fp = tn = fn = 0

        for prob, is_true_rec in zip(predicted_probabilities, true_recoverable_flags):
            pred_rec = (prob >= threshold)
            if pred_rec and is_true_rec:
                tp += 1
            elif pred_rec and not is_true_rec:
                fp += 1
            elif not pred_rec and not is_true_rec:
                tn += 1
            else:
                fn += 1

        total = tp + fp + tn + fn
        prec = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        acc = ((tp + tn) / total) if total > 0 else 0.0

        return RecoverabilityClassificationMetrics(
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            precision=round(prec, 4),
            recall=round(rec, 4),
            f1_score=round(f1, 4),
            accuracy=round(acc, 4),
        )
