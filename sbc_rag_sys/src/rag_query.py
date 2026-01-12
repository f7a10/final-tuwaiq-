"""
RAG Query System
Retrieves relevant documents and generates answers using Mistral AI
"""

import os
import sys
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from mistralai import Mistral

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from src.prompts import get_rag_prompt


class SBCRagSystem:
    """RAG system for Saudi Building Code queries"""
    
    def __init__(self):
        """Initialize RAG system components"""
        print("Initializing RAG system...")
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            host=Config.QDRANT_HOST,
            port=Config.QDRANT_PORT
        )
        
        # Initialize Mistral client
        self.mistral_client = Mistral(api_key=Config.MISTRAL_API_KEY)
        
        self.collection_name = Config.QDRANT_COLLECTION_NAME
        self.model = Config.MISTRAL_MODEL
        
        print("✓ RAG system initialized")
    
    def create_query_embedding(self, query: str):
        """Create embedding for query"""
        return self.embedding_model.encode(query, convert_to_numpy=True)
    
    def retrieve_documents(
        self, 
        query: str, 
        top_k: int = 5,
        score_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Retrieve relevant documents from Qdrant
        
        Args:
            query: User query
            top_k: Number of documents to retrieve
            score_threshold: Minimum similarity score
            
        Returns:
            List of relevant documents with metadata
        """
        # Create query embedding
        query_embedding = self.create_query_embedding(query)
        
        # Search in Qdrant
        search_results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=top_k,
            score_threshold=score_threshold
        )
        
        # Format results
        documents = []
        for result in search_results:
            documents.append({
                "text": result.payload["text"],
                "document": result.payload["document"],
                "chunk_index": result.payload["chunk_index"],
                "score": result.score,
                "source": result.payload.get("source", "")
            })
        
        return documents
    
    def format_context(self, documents: List[Dict]) -> str:
        """Format retrieved documents into context string"""
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            context_parts.append(
                f"[مقتطف {i} من {doc['document']}]\n"
                f"{doc['text']}\n"
            )
        
        return "\n".join(context_parts)
    
    def generate_answer(
        self, 
        query: str, 
        context: str,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate answer using Mistral AI
        
        Args:
            query: User question
            context: Retrieved context
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated answer
        """
        # Create prompt
        prompt = get_rag_prompt(context, query)
        
        # Call Mistral API
        response = self.mistral_client.chat.complete(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def query(
        self, 
        question: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
        temperature: float = 0.3,
        return_sources: bool = True
    ) -> Dict:
        """
        Full RAG query pipeline
        
        Args:
            question: User question
            top_k: Number of documents to retrieve
            score_threshold: Minimum similarity score
            temperature: Sampling temperature for generation
            return_sources: Whether to return source documents
            
        Returns:
            Dictionary with answer and optional sources
        """
        print(f"\nQuestion: {question}")
        print("Retrieving relevant documents...")
        
        # Retrieve documents
        documents = self.retrieve_documents(
            query=question,
            top_k=top_k,
            score_threshold=score_threshold
        )
        
        if not documents:
            return {
                "answer": "عذراً، لم أجد معلومات ذات صلة في وثائق كود البناء السعودي المتاحة. يرجى إعادة صياغة السؤال أو التأكد من أن السؤال يتعلق بكود البناء السعودي.",
                "sources": [],
                "success": False
            }
        
        print(f"✓ Found {len(documents)} relevant documents")
        
        # Format context
        context = self.format_context(documents)
        
        # Generate answer
        print("Generating answer...")
        answer = self.generate_answer(
            query=question,
            context=context,
            temperature=temperature
        )
        
        print("✓ Answer generated")
        
        result = {
            "answer": answer,
            "success": True
        }
        
        if return_sources:
            result["sources"] = documents
        
        return result
    
    def interactive_mode(self):
        """Run interactive query mode"""
        print("\n" + "="*60)
        print("نظام الاستعلام عن كود البناء السعودي")
        print("Saudi Building Code RAG System")
        print("="*60)
        print("\nاكتب سؤالك أو 'exit' للخروج / Type your question or 'exit' to quit\n")
        
        while True:
            try:
                question = input("\n🔍 السؤال / Question: ").strip()
                
                if question.lower() in ['exit', 'quit', 'خروج']:
                    print("\nشكراً لاستخدامك النظام / Thank you for using the system!")
                    break
                
                if not question:
                    continue
                
                # Query the system
                result = self.query(question)
                
                # Display answer
                print("\n" + "="*60)
                print("📝 الإجابة / Answer:")
                print("="*60)
                print(result["answer"])
                
                # Display sources
                if result.get("sources"):
                    print("\n" + "-"*60)
                    print("📚 المصادر / Sources:")
                    print("-"*60)
                    for i, source in enumerate(result["sources"], 1):
                        print(f"\n{i}. {source['document']} (درجة الصلة: {source['score']:.3f})")
                        print(f"   {source['text'][:200]}...")
                
                print("\n" + "="*60)
                
            except KeyboardInterrupt:
                print("\n\nتم إيقاف النظام / System interrupted")
                break
            except Exception as e:
                print(f"\n❌ خطأ / Error: {str(e)}")


def main():
    """Main query function"""
    # Validate config
    Config.validate()
    
    # Initialize RAG system
    rag = SBCRagSystem()
    
    # Run interactive mode
    rag.interactive_mode()


if __name__ == "__main__":
    main()

def query_sbc(room_type, area, min_dim=0, window_exists=False):
    """
    Check compliance with Saudi Building Code (SBC 1101)
    Returns text/JSON result as requested.
    """
    room_type = room_type.lower()
    is_compliant = True
    reason = "مطابق لاشتراطات كود البناء السعودي السكني (SBC 1101)"
    
    # Requirements (Area m2, Min Dimension m, Code Section)
    requirements = {
        "bedroom": {"area": 9.0, "dim": 2.7, "code": "SBC 1101 - 502.1"},
        "kitchen": {"area": 4.5, "dim": 1.8, "code": "SBC 1101 - 501.2"},
        "dining room": {"area": 10.0, "dim": 3.0, "code": "SBC 1101 - 503.1"},
        "living room": {"area": 12.0, "dim": 3.0, "code": "SBC 1101 - 504.1"},
        "majlis": {"area": 14.0, "dim": 3.0, "code": "SBC 1101 - 505.1"},
        "bathroom": {"area": 2.5, "dim": 1.2, "code": "SBC 1101 - 506.1"},
    }

    # Normalize keys
    key_map = {
        "master bedroom": "bedroom",
        "guest room": "bedroom",
        "washroom": "bathroom",
        "toilet": "bathroom",
        "open plan kitchen/living": "living room" # Treat as living room for now
    }
    
    target_key = key_map.get(room_type, room_type)
    
    if target_key in requirements:
        req = requirements[target_key]
        violations = []
        
        if area < req["area"]:
            violations.append(f"المساحة {area}م² أقل من الحد الأدنى {req['area']}م²")
            
        if min_dim > 0 and min_dim < req["dim"]:
             violations.append(f"يوجد بُعد {min_dim}م أقل من الحد الأدنى {req['dim']}م")
        
        # Window check for habitable rooms
        if target_key in ["bedroom", "living room", "majlis"] and not window_exists:
             violations.append("يجب توفر نافذة للتهوية والإضاءة الطبيعية (SBC 1101 - 1201)")

        if violations:
            is_compliant = False
            reason = f"مخالف - {req['code']}: " + " و ".join(violations)

    return {
        "is_compliant": is_compliant,
        "reason": reason,
        "score": 100 if is_compliant else 0
    }
