"""Typed Loader and Schema Validator for Hidden Evaluation Ground Truth."""

import json
import os
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class GroundTruthRecord(BaseModel):
    payment_id: int
    true_best_action: str
    true_recoverable: bool
    true_recovery_outcome: str
    true_amount_recovered: float
    true_optimal_channel: Optional[str] = None
    true_root_cause: Optional[str] = None

    @field_validator("true_best_action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = {"retry", "message", "escalate", "stop"}
        if v not in allowed:
            raise ValueError(f"Invalid true_best_action '{v}'. Allowed: {allowed}")
        return v

    @field_validator("true_recovery_outcome")
    @classmethod
    def validate_outcome(cls, v: str) -> str:
        allowed = {"recovered", "failed", "escalated", "stopped"}
        if v not in allowed:
            raise ValueError(f"Invalid true_recovery_outcome '{v}'. Allowed: {allowed}")
        return v

    @field_validator("true_amount_recovered")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError(f"true_amount_recovered cannot be negative: {v}")
        return v


class GroundTruthLoader:
    """Loads and validates evaluation-only ground truth benchmark."""

    @classmethod
    def load(cls, filepath: Optional[str] = None) -> dict[int, GroundTruthRecord]:
        """Load ground truth JSON and return map from payment_id to GroundTruthRecord."""
        path = filepath or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "synthetic", "ground_truth.json")
        )

        if not os.path.exists(path):
            raise FileNotFoundError(f"Evaluation ground truth file not found at: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        records: dict[int, GroundTruthRecord] = {}

        if isinstance(raw_data, dict):
            for k, val in raw_data.items():
                # Extract numeric payment ID from key (e.g. "pay_0000006" -> 6)
                if isinstance(k, str) and k.startswith("pay_"):
                    pid = int(re.sub(r"[^0-9]", "", k))
                elif isinstance(k, int) or (isinstance(k, str) and k.isdigit()):
                    pid = int(k)
                else:
                    continue

                item = dict(val)
                item["payment_id"] = pid
                rec = GroundTruthRecord.model_validate(item)
                records[pid] = rec

        elif isinstance(raw_data, list):
            for idx, item in enumerate(raw_data):
                try:
                    rec = GroundTruthRecord.model_validate(item)
                    records[rec.payment_id] = rec
                except Exception as e:
                    raise ValueError(f"Malformed ground truth record at index {idx}: {str(e)}")
        else:
            raise ValueError(f"Expected ground truth to be a JSON object or array, got {type(raw_data).__name__}")

        return records
