#!/usr/bin/env python3
"""
Script to create and populate the dsRAG knowledge base with company reports.

This script focuses only on the RAG part of the pipeline:
1. Initialize the knowledge base
2. Add all company report MD files
3. Verify the knowledge base is properly populated
"""

import sys
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import PipelineConfig
# Import using dynamic import to handle numbered folder names
rag_utils = __import__('02_RAG_and_knowledgebase.DS_RAG_utils', fromlist=['KnowledgeBaseManager'])
KnowledgeBaseManager = rag_utils.KnowledgeBaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_knowledge_base():
    """Create and populate the dsRAG knowledge base with company reports."""
    
    try:
        # Load configuration
        logger.info("=" * 80)
        logger.info("CREATING DS-RAG KNOWLEDGE BASE")
        logger.info("=" * 80)
        
        logger.info("Loading configuration...")
        config = PipelineConfig.from_settings_file("settings.config")
        config.validate()
        
        logger.info(f"Company data directory: {config.company_data_dir}")
        logger.info(f"KB storage directory: {config.kb_storage_dir}")
        
        # Check how many MD files we have
        md_files = list(config.company_data_dir.glob("*.md"))
        logger.info(f"Found {len(md_files)} MD files in company data directory")
        
        if len(md_files) == 0:
            logger.error("No MD files found in company data directory!")
            return False
        
        # Show the files we're about to process
        logger.info("\nCompany report files to be added:")
        for i, file_path in enumerate(md_files[:10]):  # Show first 10
            logger.info(f"  {i+1}. {file_path.name}")
        if len(md_files) > 10:
            logger.info(f"  ... and {len(md_files) - 10} more files")
        
        # Initialize knowledge base manager
        logger.info(f"\nInitializing knowledge base manager...")
        logger.info(f"  KB ID: analyst_report_kb")
        logger.info(f"  Storage: {config.kb_storage_dir}")
        logger.info(f"  Model: {config.embedding_model}")
        logger.info(f"  Chunk size: {config.chunk_size}")
        logger.info(f"  Semantic sectioning: {config.use_semantic_sectioning}")
        
        kb_manager = KnowledgeBaseManager(
            kb_id="analyst_report_kb",
            storage_directory=config.kb_storage_dir,
            llm_model=config.embedding_model,
            use_reranker=True,
            chunk_size=config.chunk_size,
            use_semantic_sectioning=config.use_semantic_sectioning,
        )
        
        # Add all MD files to knowledge base
        logger.info(f"\nAdding {len(md_files)} MD files to knowledge base...")
        logger.info("This may take a few minutes as documents are processed and embedded...")
        
        doc_ids = kb_manager.add_documents_from_directory(
            directory=config.company_data_dir,
            file_pattern="*.md"
        )
        
        logger.info(f"\n✓ Successfully added {len(doc_ids)} documents to knowledge base")
        
        # Verify the knowledge base
        logger.info("\n" + "="*60)
        logger.info("KNOWLEDGE BASE CREATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total MD files found: {len(md_files)}")
        logger.info(f"Total documents added: {len(doc_ids)}")
        
        if len(doc_ids) != len(md_files):
            logger.warning(f"⚠️  Mismatch: {len(md_files)} files found but {len(doc_ids)} documents added")
            logger.warning("Some files may have failed to process")
        else:
            logger.info("✓ All files successfully processed")
        
        # Test the knowledge base with a sample query
        logger.info(f"\nTesting knowledge base with sample queries...")
        
        test_queries = [
            "AMD revenue financial results",
            "quarterly earnings performance",
            "market share competition"
        ]
        
        for query in test_queries:
            logger.info(f"\nQuery: '{query}'")
            results = kb_manager.query(query, top_k=3)
            
            if results:
                logger.info(f"  ✓ Found {len(results)} results")
                for i, result in enumerate(results):
                    doc_id = result.get('doc_id', 'Unknown')
                    score = result.get('score', 'N/A')
                    logger.info(f"    {i+1}. {doc_id} (score: {score})")
            else:
                logger.warning(f"  ⚠️  No results found")
        
        # Show knowledge base info
        kb_info = kb_manager.get_knowledge_base_info()
        logger.info(f"\nKnowledge Base Information:")
        logger.info(f"  KB ID: {kb_info['kb_id']}")
        logger.info(f"  Storage: {kb_info['storage_directory']}")
        logger.info(f"  Model: {kb_info['llm_model']}")
        logger.info(f"  Chunk size: {kb_info['chunk_size']}")
        logger.info(f"  Reranker: {kb_info['use_reranker']}")
        logger.info(f"  Semantic sectioning: {kb_info['use_semantic_sectioning']}")
        
        logger.info("\n" + "="*80)
        logger.info("✓ KNOWLEDGE BASE CREATION COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        logger.info(f"The knowledge base is now ready for use in the analysis pipeline.")
        logger.info(f"All {len(doc_ids)} company reports have been processed and embedded.")
        logger.info("="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"Knowledge base creation failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = create_knowledge_base()
    if success:
        print("\n🎉 Knowledge base creation completed successfully!")
        print("You can now run the full analysis pipeline with the populated knowledge base.")
    else:
        print("\n❌ Knowledge base creation failed. Check the logs above for details.")
    
    sys.exit(0 if success else 1)
