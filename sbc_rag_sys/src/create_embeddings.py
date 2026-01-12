"""
Document Chunking and Embedding Creation
Processes extracted text and stores embeddings in Qdrant
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config


class DocumentEmbedder:
    """Create embeddings and store in Qdrant"""
    
    def __init__(self):
        """Initialize embedder and Qdrant client"""
        print("Initializing embedding model...")
        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        
        print(f"Connecting to Qdrant at {Config.QDRANT_HOST}:{Config.QDRANT_PORT}...")
        self.qdrant_client = QdrantClient(
            host=Config.QDRANT_HOST,
            port=Config.QDRANT_PORT
        )
        
        self.collection_name = Config.QDRANT_COLLECTION_NAME
        self._setup_collection()
    
    def _setup_collection(self):
        """Create or recreate Qdrant collection"""
        # Check if collection exists
        collections = self.qdrant_client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if self.collection_name in collection_names:
            print(f"Collection '{self.collection_name}' already exists. Recreating...")
            self.qdrant_client.delete_collection(self.collection_name)
        
        # Create collection
        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.embedding_dim,
                distance=Distance.COSINE
            )
        )
        print(f"✓ Collection '{self.collection_name}' created")
    
    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Number of overlapping characters
            
        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or Config.CHUNK_SIZE
        overlap = overlap or Config.CHUNK_OVERLAP
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # If paragraph itself is too large, split it
            if len(para) > chunk_size:
                # Split by sentences (basic Arabic sentence splitting)
                sentences = para.replace('。', '.').split('.')
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) < chunk_size:
                        current_chunk += sentence + ". "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + ". "
            else:
                # Add paragraph to current chunk
                if len(current_chunk) + len(para) < chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Add overlap
        overlapped_chunks = []
        for i, chunk in enumerate(chunks):
            if i > 0 and overlap > 0:
                # Add overlap from previous chunk
                prev_overlap = chunks[i-1][-overlap:]
                chunk = prev_overlap + " " + chunk
            overlapped_chunks.append(chunk)
        
        return overlapped_chunks
    
    def create_embedding(self, text: str):
        """Create embedding for text"""
        return self.embedding_model.encode(text, convert_to_numpy=True)
    
    def process_document(self, file_path: str) -> List[Dict]:
        """
        Process a single document: chunk, embed, and prepare for storage
        
        Args:
            file_path: Path to the text file
            
        Returns:
            List of document chunks with embeddings
        """
        # Read document
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Chunk document
        chunks = self.chunk_text(text)
        
        # Create embeddings
        doc_name = Path(file_path).stem
        processed_chunks = []
        
        for i, chunk in enumerate(chunks):
            embedding = self.create_embedding(chunk)
            processed_chunks.append({
                "id": str(uuid.uuid4()),
                "text": chunk,
                "embedding": embedding,
                "metadata": {
                    "document": doc_name,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "source": file_path
                }
            })
        
        return processed_chunks
    
    def store_embeddings(self, chunks: List[Dict]):
        """Store embeddings in Qdrant"""
        points = []
        
        for chunk in chunks:
            point = PointStruct(
                id=chunk["id"],
                vector=chunk["embedding"].tolist(),
                payload={
                    "text": chunk["text"],
                    "document": chunk["metadata"]["document"],
                    "chunk_index": chunk["metadata"]["chunk_index"],
                    "total_chunks": chunk["metadata"]["total_chunks"],
                    "source": chunk["metadata"]["source"]
                }
            )
            points.append(point)
        
        # Upload in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
    
    def process_directory(self, input_dir: str):
        """
        Process all text files in directory
        
        Args:
            input_dir: Directory containing extracted text files
        """
        # Get all text files
        text_files = list(Path(input_dir).glob("*.txt"))
        text_files = [f for f in text_files if f.name != "extraction_summary.txt"]
        
        if not text_files:
            print(f"No text files found in {input_dir}")
            return
        
        total_chunks = 0
        
        # Process each file
        for file_path in tqdm(text_files, desc="Processing documents"):
            print(f"\nProcessing: {file_path.name}")
            
            # Process document
            chunks = self.process_document(str(file_path))
            print(f"  Created {len(chunks)} chunks")
            
            # Store embeddings
            self.store_embeddings(chunks)
            print(f"  ✓ Stored in Qdrant")
            
            total_chunks += len(chunks)
        
        # Print summary
        print(f"\n{'='*50}")
        print(f"Embedding complete!")
        print(f"Total documents: {len(text_files)}")
        print(f"Total chunks: {total_chunks}")
        print(f"Collection: {self.collection_name}")
        print(f"{'='*50}")


def main():
    """Main embedding function"""
    # Validate config
    Config.validate()
    
    # Check if extracted files exist
    if not os.path.exists(Config.EXTRACTED_DIR):
        print(f"Error: Extracted directory not found: {Config.EXTRACTED_DIR}")
        print("Please run extract_pdf.py first")
        return
    
    # Initialize embedder
    embedder = DocumentEmbedder()
    
    # Process documents
    embedder.process_directory(Config.EXTRACTED_DIR)


if __name__ == "__main__":
    main()
