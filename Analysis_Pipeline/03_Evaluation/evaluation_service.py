"""
Re-export of EvaluationService for consistency.

This module re-exports the EvaluationService from evaluation_utils
to maintain consistency with other services.
"""

from 01_Evaluation.evaluation_utils import EvaluationService

__all__ = ["EvaluationService"]

