"""
Text management utilities for loading, saving, and managing extracted text.

This module provides utilities for managing text data throughout the pipeline,
including JSON I/O and text format conversions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class TextManager:
    """Manage text data loading, saving, and conversions."""
    
    @staticmethod
    def save_json(data: Any, output_path: Path, indent: int = 2) -> None:
        """
        Save data to JSON file.
        
        Args:
            data: Data to save
            output_path: Path to output file
            indent: JSON indentation (default: 2)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        
        logger.info(f"Saved JSON to: {output_path}")
    
    @staticmethod
    def load_json(input_path: Path) -> Any:
        """
        Load data from JSON file.
        
        Args:
            input_path: Path to input file
            
        Returns:
            Loaded data
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not input_path.exists():
            raise FileNotFoundError(f"JSON file not found: {input_path}")
        
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"Loaded JSON from: {input_path}")
        return data
    
    @staticmethod
    def export_sections_to_json(
        sections_dict: Dict[str, List[str]], 
        output_path: Path
    ) -> None:
        """
        Export sections dictionary to JSON file.
        
        Args:
            sections_dict: Dictionary mapping section names to sentence lists
            output_path: Path to output file
        """
        TextManager.save_json(sections_dict, output_path)
        
        total_sentences = sum(len(sentences) for sentences in sections_dict.values())
        logger.info(
            f"Exported {len(sections_dict)} sections with "
            f"{total_sentences} total sentences to {output_path}"
        )
    
    @staticmethod
    def load_sections_from_json(input_path: Path) -> Dict[str, List[str]]:
        """
        Load sections dictionary from JSON file.
        
        Args:
            input_path: Path to input file
            
        Returns:
            Dictionary mapping section names to sentence lists
        """
        data = TextManager.load_json(input_path)
        
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data)}")
        
        return data
    
    @staticmethod
    def flatten_sections(
        sections_dict: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Flatten sections dictionary into list of sentence records.
        
        Args:
            sections_dict: Dictionary mapping section names to sentence lists
            
        Returns:
            List of records with 'section', 'index', and 'sentence' keys
        """
        flattened = []
        
        for section_name, sentences in sections_dict.items():
            for idx, sentence in enumerate(sentences):
                flattened.append({
                    "section": section_name,
                    "index": idx,
                    "sentence": sentence.strip(),
                })
        
        return flattened
    
    @staticmethod
    def unflatten_to_sections(
        flattened_records: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Convert flattened records back to sections dictionary.
        
        Args:
            flattened_records: List of sentence records
            
        Returns:
            Dictionary mapping section names to sentence lists
        """
        sections = {}
        
        for record in flattened_records:
            section_name = record.get("section", "unknown")
            sentence = record.get("sentence", "")
            
            if section_name not in sections:
                sections[section_name] = []
            
            sections[section_name].append(sentence)
        
        return sections


class ClassificationManager(TextManager):
    """Manage classified sentence data."""
    
    @staticmethod
    def save_classified_sentences(
        classified_data: Dict[str, List[Dict[str, str]]],
        output_path: Path
    ) -> None:
        """
        Save classified sentences to JSON.
        
        Args:
            classified_data: Dictionary mapping sections to classified sentences
            output_path: Path to output file
        """
        TextManager.save_json(classified_data, output_path)
        
        total_sentences = sum(len(items) for items in classified_data.values())
        logger.info(f"Saved {total_sentences} classified sentences to {output_path}")
    
    @staticmethod
    def load_classified_sentences(
        input_path: Path
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Load classified sentences from JSON.
        
        Args:
            input_path: Path to input file
            
        Returns:
            Dictionary mapping sections to classified sentences
        """
        return TextManager.load_json(input_path)


class EvaluationManager(TextManager):
    """Manage evaluation results data."""
    
    @staticmethod
    def save_evaluations(
        evaluations: Dict[str, List[Dict[str, Any]]],
        output_path: Path
    ) -> None:
        """
        Save evaluation results to JSON.
        
        Args:
            evaluations: Dictionary mapping sections to evaluation results
            output_path: Path to output file
        """
        TextManager.save_json(evaluations, output_path)
        
        total_evals = sum(len(items) for items in evaluations.values())
        logger.info(f"Saved {total_evals} evaluations to {output_path}")
    
    @staticmethod
    def load_evaluations(
        input_path: Path
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load evaluation results from JSON.
        
        Args:
            input_path: Path to input file
            
        Returns:
            Dictionary mapping sections to evaluation results
        """
        return TextManager.load_json(input_path)

