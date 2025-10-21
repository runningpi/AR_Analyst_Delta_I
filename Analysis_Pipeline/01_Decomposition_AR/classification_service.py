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
    
    SYSTEM_PROMPT = """Classify each of the following sentences into TWO categories:

1. SOURCE TYPE (choose exactly one):
   - primary: Derived from company disclosures (official data, management quotes, Current stock market price and market value of the company)
   - secondary: Derived from market trends, third-party data, or inference  
   - tertiary_interpretive: Analyst reasoning, synthesis, or speculation
   - other: Everything which is not part of the other categories

2. CONTENT TYPE (choose exactly one):
   - quantitative: Includes numbers, percentages, growth rates, EPS, margins, or price targets
   - qualitative: Descriptive statements, management assessments, strategic opinions

For each classification, also provide a confidence score from 0.0 to 1.0, where:
- 1.0 = Very confident (clear, unambiguous classification)
- 0.8-0.9 = Confident (mostly clear with minor ambiguity)
- 0.6-0.7 = Somewhat confident (some ambiguity but leaning toward classification)
- 0.4-0.5 = Uncertain (significant ambiguity)
- 0.0-0.3 = Very uncertain (highly ambiguous)

Return only valid JSON in the format:
{ "results": [ {"source":"primary", "sentence_type":"quantitative", "source_confidence":0.9, "sentence_type_confidence":0.8}, {"source":"secondary", "sentence_type":"qualitative", "source_confidence":0.7, "sentence_type_confidence":0.9}, ... ] }

Do not rewrite or repeat the sentences. Only return the labels and confidence scores.
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
    
    def classify_batch(self, sentences: List[str]) -> List[Dict[str, Any]]:
        """
        Classify a batch of sentences.
        
        Args:
            sentences: List of sentences to classify
            
        Returns:
            List of classification dictionaries with 'source', 'sentence_type', and confidence scores
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
            predictions = []
            for item in parsed.get("results", []):
                predictions.append({
                    "source": item.get("source", "tertiary_interpretive"),
                    "sentence_type": item.get("sentence_type", "qualitative"),
                    "source_confidence": float(item.get("source_confidence", 0.5)),
                    "sentence_type_confidence": float(item.get("sentence_type_confidence", 0.5))
                })
            
        except Exception as e:
            logger.warning(f"Classification failed: {e}. Defaulting to 'tertiary_interpretive'/'qualitative' with low confidence")
            predictions = []
        
        # Ensure we have one label per sentence
        if len(predictions) < len(sentences):
            predictions += [{"source": "tertiary_interpretive", "sentence_type": "qualitative", "source_confidence": 0.3, "sentence_type_confidence": 0.3}] * (len(sentences) - len(predictions))
        elif len(predictions) > len(sentences):
            predictions = predictions[:len(sentences)]
        
        return predictions
    
    def classify_sentences(
        self,
        sentences_by_section: Dict[str, List[str]]
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Classify all sentences in sections.
        
        Args:
            sentences_by_section: Dictionary mapping section names to sentence lists
            
        Returns:
            Dictionary mapping section names to lists of classified sentence dicts
        """
        logger.info(f"Starting classification for {len(sentences_by_section)} sections")
        
        classified = {}
        total_sentences = 0
        
        for section_name, sentences in sentences_by_section.items():
            # Filter out empty sentences
            sentences = [s.strip() for s in sentences if s and s.strip()]
            classified[section_name] = []
            
            logger.info(f"Classifying {len(sentences)} sentences in section: {section_name}")
            
            # Process in batches
            for batch in self._batched(sentences, self.batch_size):
                classifications = self.classify_batch(batch)
                
                # Pair each sentence with its classification
                for sentence, classification in zip(batch, classifications):
                    classified[section_name].append({
                        "sentence": sentence,
                        "source": classification["source"],
                        "sentence_type": classification["sentence_type"],
                        "source_confidence": classification["source_confidence"],
                        "sentence_type_confidence": classification["sentence_type_confidence"],
                    })
                    total_sentences += 1
            
            logger.debug(f"Completed classification for section: {section_name}")
        
        logger.info(f"Classification complete. Total sentences classified: {total_sentences}")
        return classified
    
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

