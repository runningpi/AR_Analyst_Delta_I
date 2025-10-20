"""
Configuration management for AR Analyst Delta I Pipeline.

This module loads settings from settings.config and environment variables,
providing centralized configuration access across the pipeline.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class PipelineConfig:
    """Configuration for the AR Analysis Pipeline."""
    
    # Paths
    env_file: Path
    analyst_report_path: Path
    company_data_dir: Path
    output_dir: Path
    kb_storage_dir: Path
    
    # API Keys (from .env)
    openai_api_key: Optional[str] = None
    cohere_api_key: Optional[str] = None
    
    # Model Configuration
    classification_model: str = "gpt-4o-mini"
    evaluation_model: str = "gpt-4o-mini"
    embedding_model: str = "gpt-4o-mini"
    
    # Processing Configuration
    classification_batch_size: int = 10
    top_k_results: int = 5
    chunk_size: int = 200
    
    # DS-RAG Configuration
    use_semantic_sectioning: bool = True
    
    
    @classmethod
    def from_settings_file(cls, settings_path: str = "settings.config") -> "PipelineConfig":
        """
        Load configuration from settings.config file.
        
        Args:
            settings_path: Path to settings.config file
            
        Returns:
            PipelineConfig instance
        """
        settings_file = Path(settings_path)
        if not settings_file.exists():
            raise FileNotFoundError(f"Settings file not found: {settings_path}")
        
        # Parse settings.config
        config_dict = {}
        with open(settings_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    config_dict[key.strip()] = value.strip()
        
        # Get base directory (where settings.config is located)
        base_dir = settings_file.parent
        
        # Load environment file
        env_file = Path(config_dict.get('env_file', '.env'))
        if not env_file.is_absolute():
            env_file = base_dir / env_file
        
        # Load environment variables
        if env_file.exists():
            load_dotenv(env_file)
        else:
            print(f"Warning: .env file not found at {env_file}")
            load_dotenv()  # Try to load from current directory
        
        # Parse paths from config
        analyst_report = Path(config_dict.get('analyst_report', ''))
        if not analyst_report.is_absolute():
            analyst_report = base_dir / analyst_report
            
        company_data = Path(config_dict.get('company_data_dir', ''))
        if not company_data.is_absolute():
            company_data = base_dir / company_data
        
        # Setup directory paths
        # All outputs now go to stage-specific subdirectories
        output_dir = base_dir / "output"
        kb_storage_dir = base_dir / "RAG_and_knowledgebase" / "kb_storage"
        
        # Only create KB storage (output directories created by each stage as needed)
        kb_storage_dir.mkdir(parents=True, exist_ok=True)
        
        return cls(
            env_file=env_file,
            analyst_report_path=analyst_report,
            company_data_dir=company_data,
            output_dir=output_dir,
            kb_storage_dir=kb_storage_dir,
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            cohere_api_key=os.getenv('COHERE_API_KEY'),
        )
    
    
    def validate(self) -> None:
        """Validate configuration and raise errors if invalid."""
        if not self.analyst_report_path.exists():
            raise FileNotFoundError(f"Analyst report not found: {self.analyst_report_path}")
        
        if not self.company_data_dir.exists():
            raise FileNotFoundError(f"Company data directory not found: {self.company_data_dir}")
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        if not self.cohere_api_key:
            print("Warning: COHERE_API_KEY not found. Reranking will not be available.")
    
    
    def get_output_path(self, filename: str) -> Path:
        """Get full path for an output file."""
        return self.output_dir / filename
    
    
    def __repr__(self) -> str:
        """String representation hiding sensitive data."""
        return (
            f"PipelineConfig(\n"
            f"  analyst_report={self.analyst_report_path}\n"
            f"  company_data_dir={self.company_data_dir}\n"
            f"  output_dir={self.output_dir}\n"
            f"  kb_storage_dir={self.kb_storage_dir}\n"
            f"  openai_api_key={'***' if self.openai_api_key else None}\n"
            f"  cohere_api_key={'***' if self.cohere_api_key else None}\n"
            f")"
        )

