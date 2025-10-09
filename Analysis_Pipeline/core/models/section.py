"""Section and document models."""

from typing import List, Dict
from pydantic import BaseModel, Field


class Section(BaseModel):
    """A section of the analyst report."""
    
    name: str = Field(..., description="Section name/title")
    sentences: List[str] = Field(default_factory=list, description="List of sentences in this section")
    
    def add_sentence(self, sentence: str) -> None:
        """Add a sentence to this section."""
        self.sentences.append(sentence)
    
    def sentence_count(self) -> int:
        """Get number of sentences in this section."""
        return len(self.sentences)


class AnalystReport(BaseModel):
    """Complete analyst report with sections."""
    
    doc_id: str = Field(..., description="Document identifier")
    sections: Dict[str, Section] = Field(default_factory=dict, description="Sections keyed by name")
    
    def add_section(self, section_name: str, sentences: List[str]) -> None:
        """Add a section with sentences."""
        self.sections[section_name] = Section(name=section_name, sentences=sentences)
    
    def get_section(self, section_name: str) -> Section:
        """Get a section by name."""
        return self.sections.get(section_name)
    
    def total_sentences(self) -> int:
        """Get total number of sentences across all sections."""
        return sum(section.sentence_count() for section in self.sections.values())
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to dictionary format for JSON serialization."""
        return {
            section_name: section.sentences
            for section_name, section in self.sections.items()
        }

