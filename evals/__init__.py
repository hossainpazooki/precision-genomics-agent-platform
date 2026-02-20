"""Evaluation framework for genomics agent validation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalResult:
    """Result of a single evaluation check."""

    name: str
    passed: bool
    score: float
    threshold: float
    details: dict = field(default_factory=dict)
