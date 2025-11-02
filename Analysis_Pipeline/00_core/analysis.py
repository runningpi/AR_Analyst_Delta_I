"""
Analysis and reporting utilities for evaluation results.

This module provides utilities for analyzing evaluation results,
generating statistics, and creating reports.
"""

import logging
from typing import Dict, List, Any, Optional
from collections import Counter
import pandas as pd

from .models.evaluation import EvaluationLabel

logger = logging.getLogger(__name__)


class EvaluationAnalyzer:
    """Analyze evaluation results and generate statistics."""
    
    def __init__(self, evaluations_dict: Dict[str, List[Dict[str, Any]]]):
        """
        Initialize the analyzer with evaluation results.
        
        Args:
            evaluations_dict: Dictionary mapping sections to evaluation results
        """
        self.evaluations_dict = evaluations_dict
        self.df = self._create_dataframe()
        logger.info(f"EvaluationAnalyzer initialized with {len(self.df)} total evaluations")
    
    def _create_dataframe(self) -> pd.DataFrame:
        """
        Create a pandas DataFrame from evaluation results.
        
        Returns:
            DataFrame with columns: section, sentence, source, sentence_type, source_confidence, sentence_type_confidence, evaluation, reason, evidence
        """
        rows = []
        
        for section, evals in self.evaluations_dict.items():
            for eval_item in evals:
                rows.append({
                    "section": section,
                    "sentence": eval_item.get("sentence", ""),
                    "source": eval_item.get("source", ""),
                    "sentence_type": eval_item.get("sentence_type", ""),
                    "source_confidence": float(eval_item.get("source_confidence", 0.5)),
                    "sentence_type_confidence": float(eval_item.get("sentence_type_confidence", 0.5)),
                    "evaluation": eval_item.get("evaluation", ""),
                    "reason": eval_item.get("reason", ""),
                    "evidence_count": len(eval_item.get("evidence", [])),
                })
        
        # Ensure DataFrame has all expected columns even when empty
        expected_columns = [
            "section", "sentence", "source", "sentence_type",
            "source_confidence", "sentence_type_confidence",
            "evaluation", "reason", "evidence_count"
        ]
        
        df = pd.DataFrame(rows)
        
        # Add missing columns if DataFrame is empty
        if df.empty:
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = pd.Series(dtype='object' if col in ["section", "sentence", "source", "sentence_type", "evaluation", "reason"] else 'float64')
        
        return df
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """
        Get overall statistics.
        
        Returns:
            Dictionary with overall statistics
        """
        total = len(self.df)
        
        # Handle empty DataFrame
        if total == 0 or self.df.empty:
            logger.warning("No evaluations found - returning empty statistics")
            return {
                "total_sentences": 0,
                "by_evaluation": {},
                "by_source": {},
                "by_sentence_type": {},
                "by_section": {},
                "confidence_stats": {
                    "source_confidence": {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0},
                    "sentence_type_confidence": {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0},
                },
            }
        
        # Check if required columns exist before accessing them
        # Count by evaluation label
        eval_counts = {}
        if "evaluation" in self.df.columns:
            eval_counts = self.df["evaluation"].value_counts().to_dict()
        
        # Count by source
        source_counts = {}
        if "source" in self.df.columns:
            source_counts = self.df["source"].value_counts().to_dict()
        
        # Count by sentence type
        sentence_type_counts = {}
        if "sentence_type" in self.df.columns:
            sentence_type_counts = self.df["sentence_type"].value_counts().to_dict()
        
        # Count by section
        section_counts = {}
        if "section" in self.df.columns:
            section_counts = self.df["section"].value_counts().to_dict()
        
        # Confidence statistics
        confidence_stats = {}
        if "source_confidence" in self.df.columns and not self.df["source_confidence"].isna().all():
            confidence_stats["source_confidence"] = {
                "mean": float(self.df["source_confidence"].mean()),
                "std": float(self.df["source_confidence"].std()),
                "min": float(self.df["source_confidence"].min()),
                "max": float(self.df["source_confidence"].max()),
            }
        else:
            confidence_stats["source_confidence"] = {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
        
        if "sentence_type_confidence" in self.df.columns and not self.df["sentence_type_confidence"].isna().all():
            confidence_stats["sentence_type_confidence"] = {
                "mean": float(self.df["sentence_type_confidence"].mean()),
                "std": float(self.df["sentence_type_confidence"].std()),
                "min": float(self.df["sentence_type_confidence"].min()),
                "max": float(self.df["sentence_type_confidence"].max()),
            }
        else:
            confidence_stats["sentence_type_confidence"] = {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
        
        stats = {
            "total_sentences": total,
            "by_evaluation": eval_counts,
            "by_source": source_counts,
            "by_sentence_type": sentence_type_counts,
            "by_section": section_counts,
            "confidence_stats": confidence_stats,
        }
        
        logger.info(f"Generated overall stats for {total} sentences")
        return stats
    
    def get_section_breakdown(self) -> pd.DataFrame:
        """
        Get evaluation breakdown by section.
        
        Returns:
            DataFrame with sections as rows, evaluation labels as columns
        """
        if self.df.empty or "section" not in self.df.columns or "evaluation" not in self.df.columns:
            logger.warning("Cannot generate section breakdown - empty DataFrame or missing columns")
            return pd.DataFrame()
        
        breakdown = pd.crosstab(
            self.df["section"],
            self.df["evaluation"],
            margins=False,
        )
        
        # Calculate percentages
        row_sums = breakdown.sum(axis=1)
        percentages = breakdown.div(row_sums, axis=0).mul(100).round(1)
        
        # Combine counts and percentages
        formatted = breakdown.astype(str) + " (" + percentages.astype(str) + "%)"
        
        return formatted
    
    def get_source_breakdown(self) -> pd.DataFrame:
        """
        Get evaluation breakdown by source type.
        
        Returns:
            DataFrame with sources as rows, evaluation labels as columns
        """
        if self.df.empty or "source" not in self.df.columns or "evaluation" not in self.df.columns:
            logger.warning("Cannot generate source breakdown - empty DataFrame or missing columns")
            return pd.DataFrame()
        
        # Filter to relevant sources
        relevant_sources = [
            "primary",
            "secondary",
            "tertiary_interpretive"
        ]
        df_filtered = self.df[self.df["source"].isin(relevant_sources)]
        
        if df_filtered.empty:
            logger.warning("No relevant sources found for breakdown")
            return pd.DataFrame()
        
        breakdown = pd.crosstab(
            df_filtered["source"],
            df_filtered["evaluation"],
            margins=False,
        )
        
        # Calculate percentages
        row_sums = breakdown.sum(axis=1)
        percentages = breakdown.div(row_sums, axis=0).mul(100).round(1)
        
        # Combine counts and percentages
        formatted = breakdown.astype(str) + " (" + percentages.astype(str) + "%)"
        
        return formatted
    
    def get_source_distribution_by_section(self) -> pd.DataFrame:
        """
        Get source distribution by section.
        
        Returns:
            DataFrame with sections as rows, sources as columns
        """
        if self.df.empty or "source" not in self.df.columns or "section" not in self.df.columns:
            logger.warning("Cannot generate source distribution - empty DataFrame or missing columns")
            return pd.DataFrame()
        
        # Filter to relevant sources
        relevant_sources = [
            "primary",
            "secondary",
            "tertiary_interpretive"
        ]
        df_filtered = self.df[self.df["source"].isin(relevant_sources)]
        
        if df_filtered.empty:
            logger.warning("No relevant sources found for distribution")
            return pd.DataFrame()
        
        distribution = pd.crosstab(
            df_filtered["section"],
            df_filtered["source"],
            margins=False,
        )
        
        # Calculate percentages
        row_sums = distribution.sum(axis=1)
        percentages = distribution.div(row_sums, axis=0).mul(100).round(1)
        
        # Combine counts and percentages
        formatted = distribution.astype(str) + " (" + percentages.astype(str) + "%)"
        
        return formatted
    
    def get_sentence_type_breakdown(self) -> pd.DataFrame:
        """
        Get evaluation breakdown by sentence type (quantitative/qualitative).
        
        Returns:
            DataFrame with sentence types as rows, evaluation labels as columns
        """
        if self.df.empty or "sentence_type" not in self.df.columns or "evaluation" not in self.df.columns:
            logger.warning("Cannot generate sentence type breakdown - empty DataFrame or missing columns")
            return pd.DataFrame()
        
        breakdown = pd.crosstab(
            self.df["sentence_type"],
            self.df["evaluation"],
            margins=False,
        )
        
        # Calculate percentages
        row_sums = breakdown.sum(axis=1)
        percentages = breakdown.div(row_sums, axis=0).mul(100).round(1)
        
        # Combine counts and percentages
        formatted = breakdown.astype(str) + " (" + percentages.astype(str) + "%)"
        
        return formatted
    
    def get_sentence_type_distribution_by_section(self) -> pd.DataFrame:
        """
        Get sentence type distribution by section.
        
        Returns:
            DataFrame with sections as rows, sentence types as columns
        """
        distribution = pd.crosstab(
            self.df["section"],
            self.df["sentence_type"],
            margins=False,
        )
        
        # Calculate percentages
        row_sums = distribution.sum(axis=1)
        percentages = distribution.div(row_sums, axis=0).mul(100).round(1)
        
        # Combine counts and percentages
        formatted = distribution.astype(str) + " (" + percentages.astype(str) + "%)"
        
        return formatted
    
    def search_sentences(
        self,
        section: Optional[str] = None,
        evaluation: Optional[str] = None,
        source: Optional[str] = None,
        sentence_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Search for sentences matching criteria.
        
        Args:
            section: Filter by section name
            evaluation: Filter by evaluation label
            source: Filter by source type
            sentence_type: Filter by sentence type (quantitative/qualitative)
            limit: Limit number of results
            
        Returns:
            DataFrame with matching sentences
        """
        if self.df.empty:
            logger.warning("Cannot search - empty DataFrame")
            return pd.DataFrame()
        
        df = self.df.copy()
        
        # Apply filters (check column exists before filtering)
        if section is not None and "section" in df.columns:
            df = df[df["section"].str.lower() == section.lower()]
        
        if evaluation is not None and "evaluation" in df.columns:
            df = df[df["evaluation"].str.lower() == evaluation.lower()]
        
        if source is not None and "source" in df.columns:
            df = df[df["source"].str.lower() == source.lower()]
        
        if sentence_type is not None and "sentence_type" in df.columns:
            df = df[df["sentence_type"].str.lower() == sentence_type.lower()]
        
        # Limit results
        if limit is not None:
            df = df.head(limit)
        
        # Select relevant columns (only if they exist)
        expected_cols = ["section", "source", "sentence_type", "source_confidence", "sentence_type_confidence", "sentence", "evaluation"]
        available_cols = [col for col in expected_cols if col in df.columns]
        
        if not available_cols:
            logger.warning("No expected columns found in DataFrame")
            return pd.DataFrame()
        
        result = df[available_cols].reset_index(drop=True)
        
        logger.info(f"Search found {len(result)} matching sentences")
        return result
    
    def get_confidence_analysis(self) -> Dict[str, Any]:
        """
        Get confidence score analysis by source and sentence type.
        
        Returns:
            Dictionary with confidence analysis
        """
        if self.df.empty:
            logger.warning("Cannot generate confidence analysis - empty DataFrame")
            return {
                "by_source": {},
                "by_sentence_type": {},
                "overall": {
                    "source_confidence": {"mean": 0.0, "std": 0.0, "median": 0.0},
                    "sentence_type_confidence": {"mean": 0.0, "std": 0.0, "median": 0.0},
                }
            }
        
        analysis = {
            "by_source": {},
            "by_sentence_type": {},
            "overall": {
                "source_confidence": {
                    "mean": float(self.df["source_confidence"].mean()) if "source_confidence" in self.df.columns and not self.df["source_confidence"].isna().all() else 0.0,
                    "std": float(self.df["source_confidence"].std()) if "source_confidence" in self.df.columns and not self.df["source_confidence"].isna().all() else 0.0,
                    "median": float(self.df["source_confidence"].median()) if "source_confidence" in self.df.columns and not self.df["source_confidence"].isna().all() else 0.0,
                },
                "sentence_type_confidence": {
                    "mean": float(self.df["sentence_type_confidence"].mean()) if "sentence_type_confidence" in self.df.columns and not self.df["sentence_type_confidence"].isna().all() else 0.0,
                    "std": float(self.df["sentence_type_confidence"].std()) if "sentence_type_confidence" in self.df.columns and not self.df["sentence_type_confidence"].isna().all() else 0.0,
                    "median": float(self.df["sentence_type_confidence"].median()) if "sentence_type_confidence" in self.df.columns and not self.df["sentence_type_confidence"].isna().all() else 0.0,
                }
            }
        }
        
        # Confidence by source
        if "source" in self.df.columns:
            for source in self.df["source"].unique():
                source_df = self.df[self.df["source"] == source]
                analysis["by_source"][source] = {
                    "source_confidence": {
                        "mean": float(source_df["source_confidence"].mean()) if "source_confidence" in source_df.columns and not source_df["source_confidence"].isna().all() else 0.0,
                        "std": float(source_df["source_confidence"].std()) if "source_confidence" in source_df.columns and not source_df["source_confidence"].isna().all() else 0.0,
                        "count": len(source_df)
                    },
                    "sentence_type_confidence": {
                        "mean": float(source_df["sentence_type_confidence"].mean()) if "sentence_type_confidence" in source_df.columns and not source_df["sentence_type_confidence"].isna().all() else 0.0,
                        "std": float(source_df["sentence_type_confidence"].std()) if "sentence_type_confidence" in source_df.columns and not source_df["sentence_type_confidence"].isna().all() else 0.0,
                    }
                }
        
        # Confidence by sentence type
        if "sentence_type" in self.df.columns:
            for sentence_type in self.df["sentence_type"].unique():
                type_df = self.df[self.df["sentence_type"] == sentence_type]
                analysis["by_sentence_type"][sentence_type] = {
                    "source_confidence": {
                        "mean": float(type_df["source_confidence"].mean()) if "source_confidence" in type_df.columns and not type_df["source_confidence"].isna().all() else 0.0,
                        "std": float(type_df["source_confidence"].std()) if "source_confidence" in type_df.columns and not type_df["source_confidence"].isna().all() else 0.0,
                        "count": len(type_df)
                    },
                    "sentence_type_confidence": {
                        "mean": float(type_df["sentence_type_confidence"].mean()) if "sentence_type_confidence" in type_df.columns and not type_df["sentence_type_confidence"].isna().all() else 0.0,
                        "std": float(type_df["sentence_type_confidence"].std()) if "sentence_type_confidence" in type_df.columns and not type_df["sentence_type_confidence"].isna().all() else 0.0,
                    }
                }
        
        return analysis
    
    def get_coverage_summary(self) -> Dict[str, Any]:
        """
        Get coverage summary showing what's supported vs not supported.
        
        Returns:
            Dictionary with coverage statistics
        """
        total = len(self.df)
        
        # Handle empty DataFrame
        if total == 0 or self.df.empty or "evaluation" not in self.df.columns:
            logger.warning("Cannot generate coverage summary - empty DataFrame or missing evaluation column")
            return {
                "total_sentences": 0,
                "covered": 0,
                "covered_percentage": 0.0,
                "not_covered": 0,
                "not_covered_percentage": 0.0,
                "contradicted": 0,
                "contradicted_percentage": 0.0,
                "breakdown": {
                    "Supported": 0,
                    "Partially Supported": 0,
                    "Not Supported": 0,
                    "Contradicted": 0,
                    "No Evidence": 0,
                }
            }
        
        # Group evaluations
        supported = len(self.df[self.df["evaluation"] == "Supported"])
        partially_supported = len(self.df[self.df["evaluation"] == "Partially Supported"])
        not_supported = len(self.df[self.df["evaluation"] == "Not Supported"])
        contradicted = len(self.df[self.df["evaluation"] == "Contradicted"])
        no_evidence = len(self.df[self.df["evaluation"] == "No Evidence"])
        
        # Calculate coverage percentage
        covered = supported + partially_supported
        not_covered = not_supported + no_evidence
        
        summary = {
            "total_sentences": total,
            "covered": covered,
            "covered_percentage": round(covered / total * 100, 1) if total > 0 else 0,
            "not_covered": not_covered,
            "not_covered_percentage": round(not_covered / total * 100, 1) if total > 0 else 0,
            "contradicted": contradicted,
            "contradicted_percentage": round(contradicted / total * 100, 1) if total > 0 else 0,
            "breakdown": {
                "Supported": supported,
                "Partially Supported": partially_supported,
                "Not Supported": not_supported,
                "Contradicted": contradicted,
                "No Evidence": no_evidence,
            }
        }
        
        logger.info(f"Coverage: {covered}/{total} ({summary['covered_percentage']}%) covered")
        return summary


class ReportGenerator:
    """Generate human-readable reports from analysis."""
    
    def __init__(self, analyzer: EvaluationAnalyzer):
        """
        Initialize report generator.
        
        Args:
            analyzer: EvaluationAnalyzer instance
        """
        self.analyzer = analyzer
    
    def generate_text_report(self) -> str:
        """
        Generate a text report summarizing the analysis.
        
        Returns:
            Text report as string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("AR ANALYST DELTA I - EVALUATION REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Overall statistics
        stats = self.analyzer.get_overall_stats()
        lines.append("OVERALL STATISTICS")
        lines.append("-" * 80)
        lines.append(f"Total Sentences: {stats['total_sentences']}")
        lines.append("")
        
        # Coverage summary
        coverage = self.analyzer.get_coverage_summary()
        lines.append("COVERAGE SUMMARY")
        lines.append("-" * 80)
        covered = coverage.get('covered', 0)
        covered_percentage = coverage.get('covered_percentage', 0.0)
        not_covered = coverage.get('not_covered', 0)
        not_covered_percentage = coverage.get('not_covered_percentage', 0.0)
        contradicted = coverage.get('contradicted', 0)
        contradicted_percentage = coverage.get('contradicted_percentage', 0.0)
        
        lines.append(f"Covered: {covered} ({covered_percentage}%)")
        lines.append(f"Not Covered: {not_covered} ({not_covered_percentage}%)")
        lines.append(f"Contradicted: {contradicted} ({contradicted_percentage}%)")
        lines.append("")
        
        lines.append("Breakdown:")
        breakdown = coverage.get('breakdown', {})
        for label, count in breakdown.items():
            percentage = round(count / stats['total_sentences'] * 100, 1) if stats['total_sentences'] > 0 else 0.0
            lines.append(f"  - {label}: {count} ({percentage}%)")
        lines.append("")
        
        # By source
        lines.append("BY SOURCE TYPE")
        lines.append("-" * 80)
        by_source = stats.get('by_source', {})
        for source, count in by_source.items():
            percentage = round(count / stats['total_sentences'] * 100, 1) if stats['total_sentences'] > 0 else 0.0
            lines.append(f"  - {source}: {count} ({percentage}%)")
        if not by_source:
            lines.append("  (No data available)")
        lines.append("")
        
        # By sentence type
        lines.append("BY SENTENCE TYPE")
        lines.append("-" * 80)
        by_sentence_type = stats.get('by_sentence_type', {})
        for sentence_type, count in by_sentence_type.items():
            percentage = round(count / stats['total_sentences'] * 100, 1) if stats['total_sentences'] > 0 else 0.0
            lines.append(f"  - {sentence_type}: {count} ({percentage}%)")
        if not by_sentence_type:
            lines.append("  (No data available)")
        lines.append("")
        
        # Confidence statistics
        lines.append("CONFIDENCE STATISTICS")
        lines.append("-" * 80)
        conf_stats = stats.get('confidence_stats', {})
        if conf_stats:
            source_conf = conf_stats.get('source_confidence', {})
            type_conf = conf_stats.get('sentence_type_confidence', {})
            
            lines.append("Source Classification Confidence:")
            lines.append(f"  - Mean: {source_conf.get('mean', 0):.3f}")
            lines.append(f"  - Std Dev: {source_conf.get('std', 0):.3f}")
            lines.append(f"  - Range: {source_conf.get('min', 0):.3f} - {source_conf.get('max', 0):.3f}")
            lines.append("")
            
            lines.append("Sentence Type Classification Confidence:")
            lines.append(f"  - Mean: {type_conf.get('mean', 0):.3f}")
            lines.append(f"  - Std Dev: {type_conf.get('std', 0):.3f}")
            lines.append(f"  - Range: {type_conf.get('min', 0):.3f} - {type_conf.get('max', 0):.3f}")
            lines.append("")
        else:
            lines.append("  No confidence statistics available")
            lines.append("")
        
        # By section
        lines.append("BY SECTION")
        lines.append("-" * 80)
        by_section = stats.get('by_section', {})
        for section, count in by_section.items():
            percentage = round(count / stats['total_sentences'] * 100, 1) if stats['total_sentences'] > 0 else 0.0
            lines.append(f"  - {section}: {count} ({percentage}%)")
        if not by_section:
            lines.append("  (No data available)")
        lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def save_report(self, output_path: str) -> None:
        """
        Save text report to file.
        
        Args:
            output_path: Path to save report
        """
        report = self.generate_text_report()
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        logger.info(f"Saved report to: {output_path}")

