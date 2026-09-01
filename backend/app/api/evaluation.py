"""Evaluation API endpoints serving safe aggregate benchmark metrics without raw ground truth."""

import json
import os
from fastapi import APIRouter, HTTPException

router = APIRouter()

EVAL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "evaluation")
)


def _load_eval_file(filename: str) -> dict:
    filepath = os.path.join(EVAL_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=404,
            detail=f"Evaluation artifact '{filename}' not found. Please run scripts/run_evaluation.py first.",
        )
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/summary")
def get_evaluation_summary():
    """Get complete evaluation summary with action metrics, calibration, regret, and safety."""
    return _load_eval_file("evaluation_summary.json")


@router.get("/confusion-matrix")
def get_confusion_matrix():
    """Get 4x4 action classification confusion matrix for RecoverAI and Naive Baseline."""
    return _load_eval_file("action_confusion_matrix.json")


@router.get("/calibration")
def get_calibration():
    """Get probability calibration bins, Brier score, and ECE."""
    return _load_eval_file("calibration.json")


@router.get("/revenue-comparison")
def get_revenue_comparison():
    """Get comparative revenue recovery against Naive Baseline and Ground Truth Label."""
    return _load_eval_file("revenue_comparison.json")


@router.get("/regret")
def get_regret():
    """Get economic regret distributions."""
    return _load_eval_file("regret.json")
