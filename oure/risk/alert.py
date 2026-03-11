"""
OURE Risk Calculation - Alert Classifier
========================================
"""

from __future__ import annotations

from oure.core.models import RiskResult


class AlertClassifier:
    """
    Classifies a RiskResult into a warning level.
    """

    def __init__(self, red_threshold: float = 1e-3, yellow_threshold: float = 1e-5):
        self.red_threshold = red_threshold
        self.yellow_threshold = yellow_threshold

    def classify(self, result: RiskResult) -> str:
        """
        Classifies the risk result and returns a warning level string.
        """
        if result.pc >= self.red_threshold:
            return "RED"
        elif result.pc >= self.yellow_threshold:
            return "YELLOW"
        else:
            return "GREEN"
