"""
Sentence classification service using GPT.

This service classifies sentences into categories:
- primary: Derived from company disclosures (official data, management quotes)
- secondary: Derived from market trends, third-party data, or inference
- tertiary_interpretive: Analyst reasoning, synthesis, or speculation
- other: Everything which is not part of the other categories

And by content type:
- quantitative: Includes numbers, percentages, growth rates, EPS, margins, or price targets
- qualitative: Descriptive statements, management assessments, strategic opinions
"""

import json
import logging
from typing import List, Dict, Any
from itertools import islice
from openai import OpenAI

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Import with proper module path
core_models = __import__('00_core.models.sentence', fromlist=['SentenceSource', 'SentenceType', 'ClassifiedSentence'])
SentenceSource = core_models.SentenceSource
SentenceType = core_models.SentenceType
ClassifiedSentence = core_models.ClassifiedSentence

logger = logging.getLogger(__name__)


class ClassificationService:
    """Service for classifying sentences using GPT."""
    
    SYSTEM_PROMPT = """Extract knowledge snippets from the following sentences and classify each snippet.

For each sentence, break it down into individual knowledge snippets (atomic pieces of information) and classify each snippet.

Example:
Input: "Das Unternehmen verkauft Graphikkarten und hat im letzten Jahr den Verkauf der Karten um 50% gesteigert"
Output snippets:
- "AMD verkauft Graphikkarten"
- "Der Verkauf der Graphikkarten von AMD wurde von 2023 auf 2024 um 50% gesteigert"

For each snippet, classify into TWO categories:

1. SOURCE TYPE (choose exactly one):
   - primary: Derived from company disclosures (official data, management quotes, current stock market price and market value of the company)
   - secondary: Derived from market trends, third-party data, or inference  
   - tertiary_interpretive: Analyst reasoning, synthesis, or speculation
   - other: Everything which is not part of the other categories

2. CONTENT TYPE (choose exactly one):
   - quantitative: Includes numbers, percentages, growth rates, EPS, margins, or price targets
   - qualitative: Descriptive statements, management assessments, strategic opinions

For each snippet classification, also provide a confidence score from 0.0 to 1.0, where:
- 1.0 = Very confident (clear, unambiguous classification)
- 0.8-0.9 = Confident (mostly clear with minor ambiguity)
- 0.6-0.7 = Somewhat confident (some ambiguity but leaning toward classification)
- 0.4-0.5 = Uncertain (significant ambiguity)
- 0.0-0.3 = Very uncertain (highly ambiguous)

Return only valid JSON in the format:
{ "snippets": [ {"snippet":"AMD verkauft Graphikkarten", "source":"primary", "sentence_type":"qualitative", "source_confidence":0.9, "sentence_type_confidence":0.8}, {"snippet":"Der Verkauf der Graphikkarten von AMD wurde von 2023 auf 2024 um 50% gesteigert", "source":"primary", "sentence_type":"quantitative", "source_confidence":0.9, "sentence_type_confidence":0.9}, ... ] }

Extract all meaningful knowledge snippets from each sentence. Each snippet should be a complete, standalone piece of information.
"""
    
    def __init__(self, model: str = "gpt-4o-mini", batch_size: int = 10):
        """
        Initialize the classification service.
        
        Args:
            model: OpenAI model to use
            batch_size: Number of sentences to classify per API call
        """
        self.client = OpenAI()
        self.model = model
        self.batch_size = batch_size
        logger.info(f"ClassificationService initialized with model={model}, batch_size={batch_size}")
    
    @staticmethod
    def _batched(sequence: List, n: int):
        """
        Batch a sequence into chunks of size n.
        
        Args:
            sequence: Sequence to batch
            n: Batch size
            
        Yields:
            Batches of size n
        """
        it = iter(sequence)
        while True:
            chunk = list(islice(it, n))
            if not chunk:
                break
            yield chunk
    
    @staticmethod
    def _extract_json(text: str) -> dict:
        """
        Extract JSON from LLM response, handling markdown code blocks.
        
        Args:
            text: Response text that may contain JSON
            
        Returns:
            Parsed JSON dict
        """
        text = text.strip()
        
        # Remove markdown code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```") and lines[-1].startswith("```"):
                text = "\n".join(lines[1:-1]).strip()
        
        # Find first {...} region
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end+1]
        
        return json.loads(text)
    
    def extract_snippets_batch(self, sentences: List[str]) -> List[Dict[str, Any]]:
        """
        Extract knowledge snippets from a batch of sentences and classify each snippet.
        
        Args:
            sentences: List of sentences to extract snippets from
            
        Returns:
            List of snippet dictionaries with 'snippet', 'source', 'sentence_type', and confidence scores
        """
        user_prompt = f"Sentences:\n{json.dumps(sentences, ensure_ascii=False)}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            
            raw_response = response.choices[0].message.content.strip()
            parsed = self._extract_json(raw_response)
            snippets = []
            for item in parsed.get("snippets", []):
                snippets.append({
                    "snippet": item.get("snippet", ""),
                    "source": item.get("source", "tertiary_interpretive"),
                    "sentence_type": item.get("sentence_type", "qualitative"),
                    "source_confidence": float(item.get("source_confidence", 0.5)),
                    "sentence_type_confidence": float(item.get("sentence_type_confidence", 0.5))
                })
            
        except Exception as e:
            logger.warning(f"Snippet extraction failed: {e}. Returning empty snippets list")
            snippets = []
        
        return snippets
    
    def extract_snippets_from_sentences(
        self,
        sentences_by_section: Dict[str, List[str]]
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Extract knowledge snippets from all sentences in sections and classify each snippet.
        
        Args:
            sentences_by_section: Dictionary mapping section names to sentence lists
            
        Returns:
            Dictionary mapping section names to lists of classified snippet dicts
        """
        logger.info(f"Starting snippet extraction for {len(sentences_by_section)} sections")
        
        snippets_by_section = {}
        total_snippets = 0
        
        for section_name, sentences in sentences_by_section.items():
            # Filter out empty sentences
            sentences = [s.strip() for s in sentences if s and s.strip()]
            snippets_by_section[section_name] = []
            
            logger.info(f"Extracting snippets from {len(sentences)} sentences in section: {section_name}")
            
            # Process in batches
            for batch in self._batched(sentences, self.batch_size):
                snippets = self.extract_snippets_batch(batch)
                
                # Add all snippets from this batch
                for snippet_data in snippets:
                    if snippet_data.get("snippet", "").strip():  # Only add non-empty snippets
                        snippets_by_section[section_name].append({
                            "snippet": snippet_data["snippet"],
                            "source": snippet_data["source"],
                            "sentence_type": snippet_data["sentence_type"],
                            "source_confidence": snippet_data["source_confidence"],
                            "sentence_type_confidence": snippet_data["sentence_type_confidence"],
                        })
                        total_snippets += 1
            
            logger.debug(f"Completed snippet extraction for section: {section_name}")
        
        logger.info(f"Snippet extraction complete. Total snippets extracted: {total_snippets}")
        return snippets_by_section
    
    def classify_to_models(
        self,
        sentences_by_section: Dict[str, List[str]]
    ) -> List[ClassifiedSentence]:
        """
        Classify sentences and return as ClassifiedSentence models.
        
        Args:
            sentences_by_section: Dictionary mapping section names to sentence lists
            
        Returns:
            List of ClassifiedSentence objects
        """
        classified_dict = self.classify_sentences(sentences_by_section)
        
        models = []
        for section_name, items in classified_dict.items():
            for idx, item in enumerate(items):
                try:
                    source = SentenceSource(item["source"])
                except ValueError:
                    source = SentenceSource.OTHER
                
                try:
                    sentence_type = SentenceType(item["sentence_type"])
                except ValueError:
                    sentence_type = SentenceType.QUALITATIVE
                
                # Get confidence scores with defaults
                source_confidence = float(item.get("source_confidence", 0.5))
                sentence_type_confidence = float(item.get("sentence_type_confidence", 0.5))
                
                model = ClassifiedSentence(
                    text=item["sentence"],
                    section=section_name,
                    index=idx,
                    source=source,
                    sentence_type=sentence_type,
                    source_confidence=source_confidence,
                    sentence_type_confidence=sentence_type_confidence,
                )
                models.append(model)
        
        return models

