"""
Sentence classification service using GPT.

This service classifies sentences into categories:
- corporate_information
- market_information  
- analyst_interpretation
- other
"""

import json
import logging
from typing import List, Dict
from itertools import islice
from openai import OpenAI

from core.models.sentence import SentenceSource, ClassifiedSentence

logger = logging.getLogger(__name__)


class ClassificationService:
    """Service for classifying sentences using GPT."""
    
    SYSTEM_PROMPT = """Classify each of the following sentences into exactly one label:
corporate_information, market_information, analyst_interpretation, or other.

corporate_information = statements that describe the company itself, such as financial results, 
products, strategies, management changes, the company's valuation, or official guidance

market_information = statements that describe competitors, industry developments, general market trends, or macro context

analyst_interpretation = statements that reflect judgments, evaluations, forecasts, or conclusions drawn by analysts

other = statements that do not fit into any of the above categories

Return only valid JSON in the format:
{ "results": [ {"source":"corporate_information"}, {"source":"market_information"}, ... ] }

Do not rewrite or repeat the sentences. Only return the labels.
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
    
    def classify_batch(self, sentences: List[str]) -> List[str]:
        """
        Classify a batch of sentences.
        
        Args:
            sentences: List of sentences to classify
            
        Returns:
            List of source labels (same length as input)
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
            predictions = [
                item.get("source", "analyst_interpretation") 
                for item in parsed.get("results", [])
            ]
            
        except Exception as e:
            logger.warning(f"Classification failed: {e}. Defaulting to 'analyst_interpretation'")
            predictions = []
        
        # Ensure we have one label per sentence
        if len(predictions) < len(sentences):
            predictions += ["analyst_interpretation"] * (len(sentences) - len(predictions))
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
                labels = self.classify_batch(batch)
                
                # Pair each sentence with its classification
                for sentence, label in zip(batch, labels):
                    classified[section_name].append({
                        "sentence": sentence,
                        "source": label,
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
                
                model = ClassifiedSentence(
                    text=item["sentence"],
                    section=section_name,
                    index=idx,
                    source=source,
                )
                models.append(model)
        
        return models

