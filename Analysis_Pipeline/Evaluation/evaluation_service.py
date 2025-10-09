"""
Re-export of EvaluationService for consistency.

This module re-exports the EvaluationService from Evaluation.evaluation_utils
to maintain consistency with other services.
"""

from Evaluation.evaluation_utils import EvaluationService

__all__ = ["EvaluationService"]

