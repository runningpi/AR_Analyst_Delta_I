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
            DataFrame with columns: section, sentence, source, sentence_type, content_relevance, source_confidence, sentence_type_confidence, content_relevance_confidence, evaluation, reason, evidence
        """
        rows = []
        
        for section, evals in self.evaluations_dict.items():
            for eval_item in evals:
                rows.append({
                    "section": section,
                    "sentence": eval_item.get("sentence", ""),
                    "claim_type": eval_item.get("claim_type", "hypothesis"),
                    "subject_scope": eval_item.get("subject_scope", "company"),
                    "sentence_type": eval_item.get("sentence_type", ""),
                    "content_relevance": eval_item.get("content_relevance", "company_relevant"),
                    "claim_type_confidence": float(eval_item.get("claim_type_confidence", 0.5)),
                    "subject_scope_confidence": float(eval_item.get("subject_scope_confidence", 0.5)),
                    "sentence_type_confidence": float(eval_item.get("sentence_type_confidence", 0.5)),
                    "content_relevance_confidence": float(eval_item.get("content_relevance_confidence", 0.5)),
                    "evaluation": eval_item.get("evaluation", ""),
                    "reason": eval_item.get("reason", ""),
                    "evidence_count": len(eval_item.get("evidence", [])),
                })
        
        # Ensure DataFrame has all expected columns even when empty
        expected_columns = [
            "section", "sentence", "claim_type", "subject_scope", "sentence_type", "content_relevance",
            "claim_type_confidence", "subject_scope_confidence", "sentence_type_confidence", "content_relevance_confidence",
            "evaluation", "reason", "evidence_count"
        ]
        
        df = pd.DataFrame(rows)
        
        # Add missing columns if DataFrame is empty
        if df.empty:
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = pd.Series(dtype='object' if col in ["section", "sentence", "claim_type", "subject_scope", "sentence_type", "content_relevance", "evaluation", "reason"] else 'float64')
        
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
                "by_claim_type": {},
                "by_subject_scope": {},
                "by_sentence_type": {},
                "by_section": {},
                "confidence_stats": {
                    "claim_type_confidence": {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0},
                    "subject_scope_confidence": {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0},
                    "sentence_type_confidence": {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0},
                },
            }
        
        # Check if required columns exist before accessing them
        # Count by evaluation label
        eval_counts = {}
        if "evaluation" in self.df.columns:
            eval_counts = self.df["evaluation"].value_counts().to_dict()
        
        # Count by claim_type
        claim_type_counts = {}
        if "claim_type" in self.df.columns:
            claim_type_counts = self.df["claim_type"].value_counts().to_dict()
        
        # Count by subject_scope
        subject_scope_counts = {}
        if "subject_scope" in self.df.columns:
            subject_scope_counts = self.df["subject_scope"].value_counts().to_dict()
        
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
        if "claim_type_confidence" in self.df.columns and not self.df["claim_type_confidence"].isna().all():
            confidence_stats["claim_type_confidence"] = {
                "mean": float(self.df["claim_type_confidence"].mean()),
                "std": float(self.df["claim_type_confidence"].std()),
                "min": float(self.df["claim_type_confidence"].min()),
                "max": float(self.df["claim_type_confidence"].max()),
            }
        else:
            confidence_stats["claim_type_confidence"] = {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
        
        if "subject_scope_confidence" in self.df.columns and not self.df["subject_scope_confidence"].isna().all():
            confidence_stats["subject_scope_confidence"] = {
                "mean": float(self.df["subject_scope_confidence"].mean()),
                "std": float(self.df["subject_scope_confidence"].std()),
                "min": float(self.df["subject_scope_confidence"].min()),
                "max": float(self.df["subject_scope_confidence"].max()),
            }
        else:
            confidence_stats["subject_scope_confidence"] = {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
        
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
            "by_claim_type": claim_type_counts,
            "by_subject_scope": subject_scope_counts,
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
        Only counts company_relevant snippets (excludes template_boilerplate).
        
        Returns:
            Dictionary with coverage statistics
        """
        # Filter to only company_relevant snippets for statistics
        if "content_relevance" in self.df.columns:
            df_relevant = self.df[self.df["content_relevance"] == "company_relevant"].copy()
        else:
            # Fallback: assume all are company_relevant if column doesn't exist
            df_relevant = self.df.copy()
            logger.warning("content_relevance column not found - assuming all snippets are company_relevant")
        
        total = len(df_relevant)
        total_all = len(self.df)  # Total including template_boilerplate
        
        # Handle empty DataFrame
        if total == 0 or df_relevant.empty or "evaluation" not in df_relevant.columns:
            logger.warning("Cannot generate coverage summary - empty DataFrame or missing evaluation column")
            return {
                "total_sentences": total,
                "total_sentences_all": total_all,
                "total_template_boilerplate": total_all - total,
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
        
        # Group evaluations (only for company_relevant snippets)
        supported = len(df_relevant[df_relevant["evaluation"] == "Supported"])
        partially_supported = len(df_relevant[df_relevant["evaluation"] == "Partially Supported"])
        not_supported = len(df_relevant[df_relevant["evaluation"] == "Not Supported"])
        contradicted = len(df_relevant[df_relevant["evaluation"] == "Contradicted"])
        no_evidence = len(df_relevant[df_relevant["evaluation"] == "No Evidence"])
        
        # Calculate coverage percentage
        covered = supported + partially_supported
        not_covered = not_supported + no_evidence
        
        template_count = total_all - total
        
        # Get coverage by claim type and subject scope
        coverage_by_claim_type = self.get_coverage_by_claim_type()
        coverage_by_subject_scope = self.get_coverage_by_subject_scope()
        
        # Get coverage by section, claim_type and subject_scope
        coverage_by_section_claim_subject = self.get_coverage_by_section_and_claim_subject()
        
        summary = {
            "total_sentences": total,  # Only company_relevant
            "total_sentences_all": total_all,  # All snippets (relevant + template)
            "total_template_boilerplate": template_count,
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
            },
            "coverage_by_claim_type": coverage_by_claim_type,
            "coverage_by_subject_scope": coverage_by_subject_scope,
            "coverage_by_section_and_claim_subject": coverage_by_section_claim_subject
        }
        
        logger.info(f"Coverage (company_relevant only): {covered}/{total} ({summary['covered_percentage']}%) covered")
        if template_count > 0:
            logger.info(f"Excluded {template_count} template_boilerplate snippets from statistics")
        return summary
    
    def get_coverage_by_claim_type(self) -> Dict[str, Dict[str, Any]]:
        """
        Get coverage summary broken down by claim type (assertion, hypothesis).
        Only counts company_relevant snippets (excludes template_boilerplate).
        
        Returns:
            Dictionary mapping claim types to their coverage statistics
        """
        # Filter to only company_relevant snippets
        if "content_relevance" in self.df.columns:
            df_relevant = self.df[self.df["content_relevance"] == "company_relevant"].copy()
        else:
            df_relevant = self.df.copy()
            logger.warning("content_relevance column not found - assuming all snippets are company_relevant")
        
        if df_relevant.empty or "claim_type" not in df_relevant.columns or "evaluation" not in df_relevant.columns:
            logger.warning("Cannot generate coverage by claim_type - empty DataFrame or missing columns")
            return {}
        
        # Claim types to analyze
        claim_types = ["assertion", "hypothesis"]
        
        coverage_by_claim_type = {}
        
        for claim_type in claim_types:
            # Filter by claim type
            df_claim = df_relevant[df_relevant["claim_type"] == claim_type].copy()
            
            total_claim = len(df_claim)
            
            if total_claim == 0:
                continue
            
            # Calculate statistics for this claim type
            supported = len(df_claim[df_claim["evaluation"] == "Supported"])
            partially_supported = len(df_claim[df_claim["evaluation"] == "Partially Supported"])
            not_supported = len(df_claim[df_claim["evaluation"] == "Not Supported"])
            contradicted = len(df_claim[df_claim["evaluation"] == "Contradicted"])
            no_evidence = len(df_claim[df_claim["evaluation"] == "No Evidence"])
            
            covered = supported + partially_supported
            not_covered = not_supported + no_evidence
            
            coverage_by_claim_type[claim_type] = {
                "total_sentences": total_claim,
                "covered": covered,
                "covered_percentage": round(covered / total_claim * 100, 1) if total_claim > 0 else 0.0,
                "not_covered": not_covered,
                "not_covered_percentage": round(not_covered / total_claim * 100, 1) if total_claim > 0 else 0.0,
                "contradicted": contradicted,
                "contradicted_percentage": round(contradicted / total_claim * 100, 1) if total_claim > 0 else 0.0,
                "breakdown": {
                    "Supported": supported,
                    "Partially Supported": partially_supported,
                    "Not Supported": not_supported,
                    "Contradicted": contradicted,
                    "No Evidence": no_evidence,
                }
            }
        
        return coverage_by_claim_type
    
    def get_coverage_by_subject_scope(self) -> Dict[str, Dict[str, Any]]:
        """
        Get coverage summary broken down by subject scope (company, market, other).
        Only counts company_relevant snippets (excludes template_boilerplate).
        
        Returns:
            Dictionary mapping subject scopes to their coverage statistics
        """
        # Filter to only company_relevant snippets
        if "content_relevance" in self.df.columns:
            df_relevant = self.df[self.df["content_relevance"] == "company_relevant"].copy()
        else:
            df_relevant = self.df.copy()
            logger.warning("content_relevance column not found - assuming all snippets are company_relevant")
        
        if df_relevant.empty or "subject_scope" not in df_relevant.columns or "evaluation" not in df_relevant.columns:
            logger.warning("Cannot generate coverage by subject_scope - empty DataFrame or missing columns")
            return {}
        
        # Subject scopes to analyze
        subject_scopes = ["company", "market", "other"]
        
        coverage_by_subject_scope = {}
        
        for subject_scope in subject_scopes:
            # Filter by subject scope
            df_scope = df_relevant[df_relevant["subject_scope"] == subject_scope].copy()
            
            total_scope = len(df_scope)
            
            if total_scope == 0:
                continue
            
            # Calculate statistics for this subject scope
            supported = len(df_scope[df_scope["evaluation"] == "Supported"])
            partially_supported = len(df_scope[df_scope["evaluation"] == "Partially Supported"])
            not_supported = len(df_scope[df_scope["evaluation"] == "Not Supported"])
            contradicted = len(df_scope[df_scope["evaluation"] == "Contradicted"])
            no_evidence = len(df_scope[df_scope["evaluation"] == "No Evidence"])
            
            covered = supported + partially_supported
            not_covered = not_supported + no_evidence
            
            coverage_by_subject_scope[subject_scope] = {
                "total_sentences": total_scope,
                "covered": covered,
                "covered_percentage": round(covered / total_scope * 100, 1) if total_scope > 0 else 0.0,
                "not_covered": not_covered,
                "not_covered_percentage": round(not_covered / total_scope * 100, 1) if total_scope > 0 else 0.0,
                "contradicted": contradicted,
                "contradicted_percentage": round(contradicted / total_scope * 100, 1) if total_scope > 0 else 0.0,
                "breakdown": {
                    "Supported": supported,
                    "Partially Supported": partially_supported,
                    "Not Supported": not_supported,
                    "Contradicted": contradicted,
                    "No Evidence": no_evidence,
                }
            }
        
        return coverage_by_subject_scope
    
    # Keep old function name for backwards compatibility, but redirect to claim_type
    def get_coverage_by_source(self) -> Dict[str, Dict[str, Any]]:
        """Backwards compatibility: redirects to get_coverage_by_claim_type."""
        return self.get_coverage_by_claim_type()
    
    def get_coverage_by_section_and_claim_subject(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Get coverage summary broken down by section, claim_type and subject_scope.
        Only counts company_relevant snippets (excludes template_boilerplate).
        
        Returns:
            Dictionary mapping section names to dictionaries with claim_type/subject_scope and coverage statistics
            Structure: {section_name: {"claim_type": {...}, "subject_scope": {...}, "_overall": {...}}}
        """
        # Filter to only company_relevant snippets
        if "content_relevance" in self.df.columns:
            df_relevant = self.df[self.df["content_relevance"] == "company_relevant"].copy()
        else:
            df_relevant = self.df.copy()
            logger.warning("content_relevance column not found - assuming all snippets are company_relevant")
        
        if df_relevant.empty or "section" not in df_relevant.columns or "claim_type" not in df_relevant.columns or "subject_scope" not in df_relevant.columns or "evaluation" not in df_relevant.columns:
            logger.warning("Cannot generate coverage by section and claim/subject - empty DataFrame or missing columns")
            return {}
        
        # Get unique sections
        sections = df_relevant["section"].unique()
        
        result = {}
        
        for section_name in sections:
            df_section = df_relevant[df_relevant["section"] == section_name].copy()
            
            section_data = {}
            
            # Coverage by claim_type
            for claim_type in ["assertion", "hypothesis"]:
                df_claim = df_section[df_section["claim_type"] == claim_type].copy()
                total_claim = len(df_claim)
                if total_claim > 0:
                    supported = len(df_claim[df_claim["evaluation"] == "Supported"])
                    partially_supported = len(df_claim[df_claim["evaluation"] == "Partially Supported"])
                    not_supported = len(df_claim[df_claim["evaluation"] == "Not Supported"])
                    contradicted = len(df_claim[df_claim["evaluation"] == "Contradicted"])
                    no_evidence = len(df_claim[df_claim["evaluation"] == "No Evidence"])
                    covered = supported + partially_supported
                    not_covered = not_supported + no_evidence
                    
                    section_data[f"claim_{claim_type}"] = {
                        "total_sentences": total_claim,
                        "covered": covered,
                        "covered_percentage": round(covered / total_claim * 100, 1) if total_claim > 0 else 0.0,
                        "not_covered": not_covered,
                        "not_covered_percentage": round(not_covered / total_claim * 100, 1) if total_claim > 0 else 0.0,
                        "contradicted": contradicted,
                        "contradicted_percentage": round(contradicted / total_claim * 100, 1) if total_claim > 0 else 0.0,
                    }
            
            # Coverage by subject_scope
            for subject_scope in ["company", "market", "other"]:
                df_scope = df_section[df_section["subject_scope"] == subject_scope].copy()
                total_scope = len(df_scope)
                if total_scope > 0:
                    supported = len(df_scope[df_scope["evaluation"] == "Supported"])
                    partially_supported = len(df_scope[df_scope["evaluation"] == "Partially Supported"])
                    not_supported = len(df_scope[df_scope["evaluation"] == "Not Supported"])
                    contradicted = len(df_scope[df_scope["evaluation"] == "Contradicted"])
                    no_evidence = len(df_scope[df_scope["evaluation"] == "No Evidence"])
                    covered = supported + partially_supported
                    not_covered = not_supported + no_evidence
                    
                    section_data[f"subject_{subject_scope}"] = {
                        "total_sentences": total_scope,
                        "covered": covered,
                        "covered_percentage": round(covered / total_scope * 100, 1) if total_scope > 0 else 0.0,
                        "not_covered": not_covered,
                        "not_covered_percentage": round(not_covered / total_scope * 100, 1) if total_scope > 0 else 0.0,
                        "contradicted": contradicted,
                        "contradicted_percentage": round(contradicted / total_scope * 100, 1) if total_scope > 0 else 0.0,
                    }
            
            if section_data or len(df_section) > 0:
                # Add overall section statistics
                total_section = len(df_section)
                supported_total = len(df_section[df_section["evaluation"] == "Supported"])
                partially_supported_total = len(df_section[df_section["evaluation"] == "Partially Supported"])
                not_supported_total = len(df_section[df_section["evaluation"] == "Not Supported"])
                contradicted_total = len(df_section[df_section["evaluation"] == "Contradicted"])
                no_evidence_total = len(df_section[df_section["evaluation"] == "No Evidence"])
                
                covered_total = supported_total + partially_supported_total
                not_covered_total = not_supported_total + no_evidence_total
                
                # Distribution counts for this section
                claim_type_counts = {}
                for claim_type in ["assertion", "hypothesis"]:
                    claim_type_counts[claim_type] = len(df_section[df_section["claim_type"] == claim_type])
                
                subject_scope_counts = {}
                for subject_scope in ["company", "market", "other"]:
                    subject_scope_counts[subject_scope] = len(df_section[df_section["subject_scope"] == subject_scope])
                
                section_data["_overall"] = {
                    "total_sentences": total_section,
                    "covered": covered_total,
                    "covered_percentage": round(covered_total / total_section * 100, 1) if total_section > 0 else 0.0,
                    "not_covered": not_covered_total,
                    "not_covered_percentage": round(not_covered_total / total_section * 100, 1) if total_section > 0 else 0.0,
                    "contradicted": contradicted_total,
                    "contradicted_percentage": round(contradicted_total / total_section * 100, 1) if total_section > 0 else 0.0,
                    "claim_type_distribution": claim_type_counts,
                    "subject_scope_distribution": subject_scope_counts,
                    "breakdown": {
                        "Supported": supported_total,
                        "Partially Supported": partially_supported_total,
                        "Not Supported": not_supported_total,
                        "Contradicted": contradicted_total,
                        "No Evidence": no_evidence_total,
                    }
                }
                
                result[section_name] = section_data
        
        return result
    
    # Keep old function name for backwards compatibility
    def get_coverage_by_section_and_source(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Backwards compatibility: redirects to get_coverage_by_section_and_claim_subject."""
        return self.get_coverage_by_section_and_claim_subject()


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
        
        # Coverage summary (includes template count info)
        coverage = self.analyzer.get_coverage_summary()
        total_all = coverage.get('total_sentences_all', stats['total_sentences'])
        total_relevant = coverage.get('total_sentences', 0)
        total_template = coverage.get('total_template_boilerplate', 0)
        
        lines.append(f"Total Sentences (all): {total_all}")
        if total_template > 0:
            lines.append(f"  - Company Relevant: {total_relevant}")
            lines.append(f"  - Template/Boilerplate (excluded): {total_template}")
        else:
            lines.append(f"Total Sentences (company_relevant): {total_relevant}")
        lines.append("")
        
        # Coverage summary (only for company_relevant)
        lines.append("COVERAGE SUMMARY (Company Relevant Only)")
        lines.append("-" * 80)
        covered = coverage.get('covered', 0)
        covered_percentage = coverage.get('covered_percentage', 0.0)
        not_covered = coverage.get('not_covered', 0)
        not_covered_percentage = coverage.get('not_covered_percentage', 0.0)
        contradicted = coverage.get('contradicted', 0)
        contradicted_percentage = coverage.get('contradicted_percentage', 0.0)
        
        lines.append(f"Total Sentences: {total_relevant}")
        lines.append(f"Covered: {covered} ({covered_percentage}%)")
        lines.append(f"Not Covered: {not_covered} ({not_covered_percentage}%)")
        lines.append(f"Contradicted: {contradicted} ({contradicted_percentage}%)")
        lines.append("")
        
        lines.append("Breakdown:")
        breakdown = coverage.get('breakdown', {})
        for label, count in breakdown.items():
            percentage = round(count / total_relevant * 100, 1) if total_relevant > 0 else 0.0
            lines.append(f"  - {label}: {count} ({percentage}%)")
        lines.append("")
        
        # Coverage by source type
        lines.append("COVERAGE BY SOURCE TYPE (Company Relevant Only)")
        lines.append("-" * 80)
        coverage_by_source = self.analyzer.get_coverage_by_source()
        
        if coverage_by_source:
            for source_type in ["primary", "secondary", "tertiary_interpretive"]:
                if source_type in coverage_by_source:
                    source_data = coverage_by_source[source_type]
                    source_total = source_data.get('total_sentences', 0)
                    source_covered = source_data.get('covered', 0)
                    source_covered_pct = source_data.get('covered_percentage', 0.0)
                    source_not_covered = source_data.get('not_covered', 0)
                    source_not_covered_pct = source_data.get('not_covered_percentage', 0.0)
                    source_contradicted = source_data.get('contradicted', 0)
                    source_contradicted_pct = source_data.get('contradicted_percentage', 0.0)
                    
                    lines.append(f"\n{source_type.upper()}:")
                    lines.append(f"  Total Sentences: {source_total}")
                    lines.append(f"  Covered: {source_covered} ({source_covered_pct}%)")
                    lines.append(f"  Not Covered: {source_not_covered} ({source_not_covered_pct}%)")
                    lines.append(f"  Contradicted: {source_contradicted} ({source_contradicted_pct}%)")
                    
                    source_breakdown = source_data.get('breakdown', {})
                    if source_breakdown:
                        lines.append("  Breakdown:")
                        for label, count in source_breakdown.items():
                            pct = round(count / source_total * 100, 1) if source_total > 0 else 0.0
                            lines.append(f"    - {label}: {count} ({pct}%)")
        else:
            lines.append("  (No data available)")
        lines.append("")
        
        # Coverage by section and source
        lines.append("COVERAGE BY SECTION AND SOURCE (Company Relevant Only)")
        lines.append("-" * 80)
        coverage_by_section_source = coverage.get('coverage_by_section_and_source', {})
        
        if coverage_by_section_source:
            for section_name in sorted(coverage_by_section_source.keys()):
                section_data = coverage_by_section_source[section_name]
                overall = section_data.get("_overall", {})
                
                lines.append(f"\n{section_name}:")
                lines.append(f"  Total Sentences: {overall.get('total_sentences', 0)}")
                lines.append(f"  Covered: {overall.get('covered', 0)} ({overall.get('covered_percentage', 0.0)}%)")
                lines.append(f"  Not Covered: {overall.get('not_covered', 0)} ({overall.get('not_covered_percentage', 0.0)}%)")
                lines.append(f"  Contradicted: {overall.get('contradicted', 0)} ({overall.get('contradicted_percentage', 0.0)}%)")
                
                # Source distribution
                source_dist = overall.get('source_distribution', {})
                if source_dist:
                    lines.append("  Source Distribution:")
                    for source_type in ["primary", "secondary", "tertiary_interpretive"]:
                        if source_type in source_dist:
                            count = source_dist[source_type]
                            total = overall.get('total_sentences', 1)
                            pct = round(count / total * 100, 1) if total > 0 else 0.0
                            lines.append(f"    - {source_type}: {count} ({pct}%)")
                
                # Coverage by source type within section
                lines.append("  Coverage by Source Type:")
                for source_type in ["primary", "secondary", "tertiary_interpretive"]:
                    if source_type in section_data:
                        source_info = section_data[source_type]
                        source_total = source_info.get('total_sentences', 0)
                        source_covered = source_info.get('covered', 0)
                        source_covered_pct = source_info.get('covered_percentage', 0.0)
                        source_contradicted = source_info.get('contradicted', 0)
                        source_contradicted_pct = source_info.get('contradicted_percentage', 0.0)
                        
                        lines.append(f"    {source_type.upper()}:")
                        lines.append(f"      Total: {source_total}")
                        lines.append(f"      Covered: {source_covered} ({source_covered_pct}%)")
                        lines.append(f"      Contradicted: {source_contradicted} ({source_contradicted_pct}%)")
        else:
            lines.append("  (No data available)")
        lines.append("")
        
        # By source (distribution only)
        lines.append("SOURCE TYPE DISTRIBUTION")
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

