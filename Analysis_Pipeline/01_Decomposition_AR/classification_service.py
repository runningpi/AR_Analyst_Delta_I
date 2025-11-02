"""
Sentence classification service using GPT.

This service classifies sentences into categories:
- claim_type: assertion (verifiable statement) or hypothesis (non-verifiable statement)
- subject_scope: company (about a specific firm), market (about industry/sector), or other (macroeconomic/unrelated)
- sentence_type: quantitative (includes numbers) or qualitative (descriptive statements)
- content_relevance: company_relevant or template_boilerplate

And by information source (determined algorithmically by detecting markdown table tags):
- text: Information comes from regular text/paragraphs in the analyst paper
- table: Information comes from a table in the analyst paper (detected via <table>, <tr>, <td> tags)
"""

import json
import logging
import time
from typing import List, Dict, Any
from itertools import islice
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from openai import RateLimitError, APIError

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    # Fallback if tqdm is not available
    def tqdm(iterable, *args, **kwargs):
        return iterable

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Import with proper module path
core_models = __import__('00_core.models.sentence', fromlist=['ClaimType', 'SubjectScope', 'SentenceType', 'ContentRelevance', 'InformationSource', 'ClassifiedSentence'])
ClaimType = core_models.ClaimType
SubjectScope = core_models.SubjectScope
SentenceType = core_models.SentenceType
ContentRelevance = core_models.ContentRelevance
InformationSource = core_models.InformationSource
ClassifiedSentence = core_models.ClassifiedSentence

logger = logging.getLogger(__name__)


class ClassificationService:
    """Service for classifying sentences using GPT."""
    
    SYSTEM_PROMPT = """Extract knowledge snippets from the following sentences and classify each snippet.

For each sentence, break it down into individual knowledge snippets (atomic pieces of information) and classify each snippet.

Example:
Input: “The company sells graphics cards and increased sales of the cards by 50% last year.”
Output snippets:
- “AMD sells GPUs”
- “Sales of AMD graphics cards increased by 50% from 2023 to 2024.”

For each snippet, classify into FOUR categories:

1. CLAIM TYPE (choose exactly one):
   - assertion: A verifiable statement about what is currently or was previously true. Can be checked against data, filings, or other objective evidence.
     Example: "Revenue grew 12 percent in Q3 2025 according to the 10-Q."
   - hypothesis: A non-verifiable statement about what may be true, why something happened, or what might happen. Includes forecasts, expectations, or causal reasoning.
     Example: "Management expects gross margin to improve next year."
   - other
   
2. SUBJECT SCOPE (choose exactly one):
   - company: About a specific firm (revenues, margins, products, management actions).
   - market: About an industry, sector, competitors, or demand/supply conditions.
   - other

3. CONTENT TYPE (choose exactly one):
   - quantitative: Includes numbers, percentages, growth rates, EPS, margins, or price targets
   - qualitative: Descriptive statements, management assessments, strategic opinions
   - other

4. CONTENT RELEVANCE (choose exactly one):
   - company_relevant: The snippet is part of the analyst report and has actual relationship to the company being analyzed (company-specific information, analysis, or insights)
   - template_boilerplate: The snippet is part of a template, disclaimer, legal notice, or information about the analyst company itself (not related to the analyzed company)
   - other

For each snippet classification, also provide a confidence score from 0.0 to 1.0, where:
- 1.0 = Very confident (clear, unambiguous classification)
- 0.8-0.9 = Confident (mostly clear with minor ambiguity)
- 0.6-0.7 = Somewhat confident (some ambiguity but leaning toward classification)
- 0.4-0.5 = Uncertain (significant ambiguity)
- 0.0-0.3 = Very uncertain (highly ambiguous)

Return only valid JSON in the format:
{ "snippets": [ {"snippet":"AMD sells graphics cards", "claim_type":"assertion", "subject_scope":"company", "sentence_type":"qualitative", "content_relevance":"company_relevant", "claim_type_confidence":0.9, "subject_scope_confidence":0.9, "sentence_type_confidence":0.8, "content_relevance_confidence":0.9}, {"snippet":"Sales of AMD graphics cards increased by 50% from 2023 to 2024", "claim_type":"assertion", "subject_scope":"company", "sentence_type":"quantitative", "content_relevance":"company_relevant", "claim_type_confidence":0.9, "subject_scope_confidence":0.9, "sentence_type_confidence":0.9, "content_relevance_confidence":0.9}, ... ] }

Note: If a snippet does not clearly fit into any category, use "other" as the classification.

Extract all meaningful knowledge snippets from each sentence. Each snippet should be a complete, standalone piece of information.
"""
    
    def __init__(self, model: str = "gpt-4o-mini", batch_size: int = 10, max_retries: int = 3, retry_delay: float = 2.0, max_workers: int = 5):
        """
        Initialize the classification service.
        
        Args:
            model: OpenAI model to use
            batch_size: Number of sentences to classify per API call
            max_retries: Maximum number of retries for rate limit errors
            retry_delay: Initial delay in seconds between retries (exponential backoff)
            max_workers: Maximum number of parallel requests (default: 5)
        """
        self.client = OpenAI(max_retries=0)  # Disable default retries, we handle them ourselves
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_workers = max_workers
        logger.info(f"ClassificationService initialized with model={model}, batch_size={batch_size}, max_retries={max_retries}, max_workers={max_workers}")
    
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
    def _is_table_content(text: str) -> bool:
        """
        Determine if text contains markdown table tags.
        
        Args:
            text: Text to check for table markup
            
        Returns:
            True if text contains table tags, False otherwise
        """
        if not text:
            return False
        
        # Check for common HTML/XML table tags
        table_indicators = [
            '<table>',
            '</table>',
            '<tr>',
            '</tr>',
            '<td>',
            '</td>',
            '<th>',
            '</th>',
            '<tbody>',
            '</tbody>',
            '<thead>',
            '</thead>',
        ]
        
        text_lower = text.lower()
        # Check if at least one table tag is present
        for indicator in table_indicators:
            if indicator in text_lower:
                return True
        
        return False
    
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
        
        # Check if any sentence in the batch contains table markup
        # If the batch contains table markup, snippets from it likely came from a table
        batch_contains_table = any(self._is_table_content(sentence) for sentence in sentences)
        
        # Retry logic with exponential backoff
        delay = self.retry_delay
        last_error = None
        
        for attempt in range(self.max_retries + 1):
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
                    # Determine information_source based on table detection algorithm
                    # Check both the original batch and the snippet itself for table tags
                    snippet_text = item.get("snippet", "")
                    is_table = batch_contains_table or self._is_table_content(snippet_text)
                    information_source = "table" if is_table else "text"
                    
                    snippets.append({
                        "snippet": snippet_text,
                        "claim_type": item.get("claim_type", "other"),
                        "subject_scope": item.get("subject_scope", "other"),
                        "sentence_type": item.get("sentence_type", "other"),
                        "content_relevance": item.get("content_relevance", "other"),
                        "information_source": information_source,
                        "claim_type_confidence": float(item.get("claim_type_confidence", 0.5)),
                        "subject_scope_confidence": float(item.get("subject_scope_confidence", 0.5)),
                        "sentence_type_confidence": float(item.get("sentence_type_confidence", 0.5)),
                        "content_relevance_confidence": float(item.get("content_relevance_confidence", 0.5)),
                        "information_source_confidence": 1.0 if is_table else 0.9  # High confidence for algorithm-based detection
                    })
                
                return snippets
            
            except (RateLimitError, APIError) as e:
                last_error = e
                # Check if it's a quota error (don't retry) or rate limit (retry)
                error_message = str(e).lower()
                error_type = None
                error_code = None
                
                # Try to extract error details from the exception
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_body = e.response.json() if hasattr(e.response, 'json') else {}
                        error_info = error_body.get('error', {})
                        error_type = error_info.get('type', '')
                        error_code = error_info.get('code', '')
                    except:
                        pass
                
                # Check for quota errors (don't retry)
                is_quota_error = (
                    "quota" in error_message or 
                    "insufficient_quota" in error_message or
                    error_type == "insufficient_quota" or
                    error_code == "insufficient_quota"
                )
                
                if is_quota_error:
                    logger.error(f"Quota exceeded - cannot proceed. Error: {e}")
                    logger.error("Please check your OpenAI billing and quota settings.")
                    logger.error("This is not a transient error - no retries will be attempted.")
                    snippets = []
                    return snippets
                
                # Rate limit or other transient API errors - retry with exponential backoff
                # Only retry 429 (rate limit), 500, 502, 503 (server errors)
                http_status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
                is_retryable = http_status in [429, 500, 502, 503] or isinstance(e, RateLimitError)
                
                if is_retryable and attempt < self.max_retries:
                    logger.warning(f"Rate limit/transient error hit (status: {http_status}). Retrying in {delay:.1f} seconds (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    if attempt >= self.max_retries:
                        logger.error(f"Rate limit/API error exceeded max retries ({self.max_retries}). Error: {e}")
                    else:
                        logger.warning(f"API error not retryable: {e}")
                    snippets = []
                    return snippets
            
            except Exception as e:
                last_error = e
                # For other exceptions, log and return empty
                logger.warning(f"Snippet extraction failed: {e}. Returning empty snippets list")
                snippets = []
                return snippets
        
        # If we get here, all retries failed
        logger.error(f"All retry attempts failed. Last error: {last_error}")
        return []
    
    def extract_snippets_from_sentences(
        self,
        sentences_by_section: Dict[str, List[str]]
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Extract knowledge snippets from all sentences in sections and classify each snippet.
        Processes all batches from all sections in parallel for maximum performance.
        
        Args:
            sentences_by_section: Dictionary mapping section names to sentence lists
            
        Returns:
            Dictionary mapping section names to lists of classified snippet dicts
        """
        logger.info(f"Starting snippet extraction for {len(sentences_by_section)} sections")
        
        snippets_by_section = {section: [] for section in sentences_by_section.keys()}
        total_snippets = 0
        
        # Collect all batches from all sections with their metadata
        all_batches = []
        for section_name, sentences in sentences_by_section.items():
            # Filter out empty sentences
            sentences = [s.strip() for s in sentences if s and s.strip()]
            if not sentences:
                continue
            
            logger.info(f"Preparing {len(sentences)} sentences in section: {section_name}")
            
            # Collect batches for this section
            for batch_idx, batch in enumerate(self._batched(sentences, self.batch_size)):
                all_batches.append((section_name, batch_idx, batch))
        
        logger.info(f"Processing {len(all_batches)} batches across {len(sentences_by_section)} sections")
        
        # Process all batches from all sections in parallel using a single executor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batch processing tasks
            future_to_batch = {
                executor.submit(self.extract_snippets_batch, batch): (section_name, batch_idx)
                for section_name, batch_idx, batch in all_batches
            }
            
            # Collect results as they complete, organized by section, with progress bar
            batch_results = {section: {} for section in sentences_by_section.keys()}
            with tqdm(total=len(all_batches), desc="Processing batches", unit="batch") as pbar:
                for future in as_completed(future_to_batch):
                    section_name, batch_idx = future_to_batch[future]
                    try:
                        snippets = future.result()
                        batch_results[section_name][batch_idx] = snippets
                    except Exception as e:
                        logger.error(f"Error processing batch {batch_idx} in section {section_name}: {e}")
                        batch_results[section_name][batch_idx] = []
                    finally:
                        pbar.update(1)
        
        # Process results in order for each section and add snippets
        for section_name in sentences_by_section.keys():
            if section_name not in batch_results:
                continue
            
            section_batches = batch_results[section_name]
            for batch_idx in sorted(section_batches.keys()):
                snippets = section_batches[batch_idx]
                for snippet_data in snippets:
                    if snippet_data.get("snippet", "").strip():  # Only add non-empty snippets
                        snippets_by_section[section_name].append({
                            "snippet": snippet_data["snippet"],
                            "claim_type": snippet_data["claim_type"],
                            "subject_scope": snippet_data["subject_scope"],
                            "sentence_type": snippet_data["sentence_type"],
                            "content_relevance": snippet_data["content_relevance"],
                            "information_source": snippet_data["information_source"],
                            "claim_type_confidence": snippet_data["claim_type_confidence"],
                            "subject_scope_confidence": snippet_data["subject_scope_confidence"],
                            "sentence_type_confidence": snippet_data["sentence_type_confidence"],
                            "content_relevance_confidence": snippet_data["content_relevance_confidence"],
                            "information_source_confidence": snippet_data["information_source_confidence"],
                        })
                        total_snippets += 1
            
            logger.debug(f"Completed snippet extraction for section: {section_name} ({len(snippets_by_section[section_name])} snippets)")
        
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
        # Extract snippets from sentences (snippets are the classified units)
        classified_dict = self.extract_snippets_from_sentences(sentences_by_section)
        
        models = []
        for section_name, items in classified_dict.items():
            for idx, item in enumerate(items):
                try:
                    claim_type = ClaimType(item.get("claim_type", "other"))
                except ValueError:
                    claim_type = ClaimType.OTHER
                
                try:
                    subject_scope = SubjectScope(item.get("subject_scope", "other"))
                except ValueError:
                    subject_scope = SubjectScope.OTHER
                
                try:
                    sentence_type = SentenceType(item.get("sentence_type", "other"))
                except ValueError:
                    sentence_type = SentenceType.OTHER
                
                try:
                    content_relevance = ContentRelevance(item.get("content_relevance", "other"))
                except ValueError:
                    content_relevance = ContentRelevance.OTHER
                
                try:
                    information_source = InformationSource(item.get("information_source", "text"))
                except ValueError:
                    information_source = InformationSource.TEXT
                
                # Get confidence scores with defaults
                claim_type_confidence = float(item.get("claim_type_confidence", 0.5))
                subject_scope_confidence = float(item.get("subject_scope_confidence", 0.5))
                sentence_type_confidence = float(item.get("sentence_type_confidence", 0.5))
                content_relevance_confidence = float(item.get("content_relevance_confidence", 0.5))
                information_source_confidence = float(item.get("information_source_confidence", 0.5))
                
                model = ClassifiedSentence(
                    text=item["snippet"],  # Use snippet as the text
                    section=section_name,
                    index=idx,
                    claim_type=claim_type,
                    subject_scope=subject_scope,
                    sentence_type=sentence_type,
                    content_relevance=content_relevance,
                    information_source=information_source,
                    claim_type_confidence=claim_type_confidence,
                    subject_scope_confidence=subject_scope_confidence,
                    sentence_type_confidence=sentence_type_confidence,
                    content_relevance_confidence=content_relevance_confidence,
                    information_source_confidence=information_source_confidence,
                )
                models.append(model)
        
        return models

