#!/usr/bin/env python3
"""
build_saudi_db.py - Build Saudi Building Code RAG Vector Database
Processes sbc1101Final.pdf and creates embeddings for RAG queries
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def build_saudi_rag_database():
    """Build the Saudi Building Code vector database."""
    
    print("=" * 60)
    print("🇸🇦 Saudi Building Code (SBC 1101) RAG Database Builder")
    print("=" * 60)
    
    # Configuration
    PDF_PATH = PROJECT_ROOT / "sbc_rag_sys" / "data" / "pdfs" / "sbc1101Final.pdf"
    DB_PATH = PROJECT_ROOT / "saudi_sbc_db"
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # Check PDF exists
    if not PDF_PATH.exists():
        print(f"❌ PDF not found at: {PDF_PATH}")
        return False
    
    print(f"📄 PDF Path: {PDF_PATH}")
    print(f"💾 DB Path: {DB_PATH}")
    
    try:
        # Import required libraries
        print("\n📦 Loading libraries...")
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_community.vectorstores import Chroma
        
        # Step 1: Load PDF
        print("\n📖 Step 1: Loading PDF...")
        loader = PyPDFLoader(str(PDF_PATH))
        documents = loader.load()
        print(f"   ✓ Loaded {len(documents)} pages")
        
        # Step 2: Split into chunks
        print("\n✂️ Step 2: Splitting into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ".", "،", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        print(f"   ✓ Created {len(chunks)} chunks")
        
        # Step 3: Create embeddings
        print("\n🧠 Step 3: Creating embeddings (this may take a while)...")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Step 4: Create/Update Vector Store
        print("\n💾 Step 4: Saving to vector database...")
        
        # Remove old DB if exists
        if DB_PATH.exists():
            import shutil
            shutil.rmtree(DB_PATH)
            print("   ✓ Removed old database")
        
        # Create new vector store
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=str(DB_PATH)
        )
        
        print(f"   ✓ Created vector database with {len(chunks)} documents")
        
        # Test query
        print("\n🧪 Step 5: Testing with sample query...")
        test_query = "ما هي متطلبات مساحة المطبخ؟"
        results = vectorstore.similarity_search(test_query, k=2)
        print(f"   Query: {test_query}")
        if results:
            print(f"   ✓ Found {len(results)} relevant documents")
            print(f"   Sample: {results[0].page_content[:200]}...")
        
        print("\n" + "=" * 60)
        print("✅ Saudi Building Code RAG database built successfully!")
        print(f"📁 Database location: {DB_PATH}")
        print("=" * 60)
        
        return True
        
    except ImportError as e:
        print(f"\n❌ Missing required library: {e}")
        print("\nPlease install required packages:")
        print("pip install langchain langchain-community pypdf chromadb sentence-transformers")
        return False
    except Exception as e:
        print(f"\n❌ Error building database: {e}")
        import traceback
        traceback.print_exc()
        return False


def query_saudi_code(query: str, k: int = 3) -> dict:
    """
    Query the Saudi Building Code database.
    
    Args:
        query: The question to ask
        k: Number of results to return
        
    Returns:
        Dict with 'answer' and 'sources'
    """
    DB_PATH = PROJECT_ROOT / "saudi_sbc_db"
    
    if not DB_PATH.exists():
        return {
            "answer": "قاعدة بيانات الكود السعودي غير متوفرة. الرجاء تشغيل build_saudi_db.py أولاً.",
            "sources": [],
            "success": False
        }
    
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_community.vectorstores import Chroma
        
        # Load embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Load vector store
        vectorstore = Chroma(
            persist_directory=str(DB_PATH),
            embedding_function=embeddings
        )
        
        # Search
        results = vectorstore.similarity_search(query, k=k)
        
        if not results:
            return {
                "answer": "لم يتم العثور على معلومات ذات صلة في كود البناء السعودي.",
                "sources": [],
                "success": True
            }
        
        # Combine results
        context = "\n\n".join([doc.page_content for doc in results])
        sources = [
            {
                "page": doc.metadata.get("page", "N/A"),
                "content": doc.page_content[:200] + "..."
            }
            for doc in results
        ]
        
        return {
            "answer": f"وفقاً لكود البناء السعودي (SBC 1101):\n\n{context[:1000]}",
            "sources": sources,
            "success": True
        }
        
    except Exception as e:
        return {
            "answer": f"خطأ في الاستعلام: {str(e)}",
            "sources": [],
            "success": False
        }


# Simple compliance checker using Saudi Code
def check_sbc_compliance(room_type: str, area_m2: float, min_dim: float) -> dict:
    """
    Check room compliance against Saudi Building Code.
    
    Args:
        room_type: Type of room (Kitchen, Bedroom, etc.)
        area_m2: Room area in square meters
        min_dim: Minimum dimension in meters
        
    Returns:
        Compliance result with SBC reference
    """
    
    # SBC 1101 Requirements (simplified)
    SBC_REQUIREMENTS = {
        "Kitchen": {
            "min_area": 4.5,
            "min_dim": 1.8,
            "code_ref": "SBC 1101 - البند 501.2"
        },
        "Bedroom": {
            "min_area": 9.0,
            "min_dim": 2.7,
            "code_ref": "SBC 1101 - البند 502.1"
        },
        "Bathroom": {
            "min_area": 2.5,
            "min_dim": 1.2,
            "code_ref": "SBC 1101 - البند 503.1"
        },
        "Living Room": {
            "min_area": 12.0,
            "min_dim": 3.0,
            "code_ref": "SBC 1101 - البند 504.1"
        },
        "Majlis": {
            "min_area": 14.0,
            "min_dim": 3.0,
            "code_ref": "SBC 1101 - البند 505.1"
        },
        "Dining Room": {
            "min_area": 9.0,
            "min_dim": 2.7,
            "code_ref": "SBC 1101 - البند 506.1"
        }
    }
    
    # Get requirements for room type
    req = SBC_REQUIREMENTS.get(room_type, {
        "min_area": 4.0,
        "min_dim": 1.5,
        "code_ref": "SBC 1101 - متطلبات عامة"
    })
    
    violations = []
    
    # Check area
    if area_m2 < req["min_area"]:
        violations.append(
            f"المساحة ({area_m2:.1f}م²) أقل من الحد الأدنى ({req['min_area']}م²)"
        )
    
    # Check minimum dimension
    if min_dim < req["min_dim"]:
        violations.append(
            f"أقل بُعد ({min_dim:.1f}م) أقل من الحد الأدنى ({req['min_dim']}م)"
        )
    
    is_compliant = len(violations) == 0
    
    if is_compliant:
        reason = f"مطابق لمتطلبات {req['code_ref']}"
    else:
        reason = f"مخالف - {req['code_ref']}: " + " | ".join(violations)
    
    return {
        "is_compliant": is_compliant,
        "reason": reason,
        "code_reference": req["code_ref"],
        "violations": violations
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Saudi Building Code RAG Database Builder")
    parser.add_argument("--build", action="store_true", help="Build the database")
    parser.add_argument("--query", type=str, help="Query to test")
    
    args = parser.parse_args()
    
    if args.build:
        build_saudi_rag_database()
    elif args.query:
        result = query_saudi_code(args.query)
        print(f"\n📋 Query: {args.query}")
        print(f"\n📖 Answer:\n{result['answer']}")
    else:
        # Default: build the database
        build_saudi_rag_database()
