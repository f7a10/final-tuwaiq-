import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for SBC RAG system"""
    
    # Mistral AI Configuration
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
    
    # Qdrant Configuration
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "sbc_documents")
    
    # Embedding Configuration
    EMBEDDING_MODEL = os.getenv(
        "EMBEDDING_MODEL", 
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )
    
    # Chunk Configuration
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    # Paths
    DATA_DIR = "data"
    PDF_DIR = os.path.join(DATA_DIR, "pdfs")
    EXTRACTED_DIR = os.path.join(DATA_DIR, "extracted")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.MISTRAL_API_KEY:
            raise ValueError("MISTRAL_API_KEY is required. Please set it in .env file")
        return True
