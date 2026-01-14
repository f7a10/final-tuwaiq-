# ==========================================
# Chat API Routes - Enhanced with Better Prompts & RAG
# ==========================================

import re
from fastapi import APIRouter
from pydantic import BaseModel
from openai import OpenAI

import sys
from backend.app.config import OPENROUTER_API_KEY, PROJECT_ROOT

# Ensure cad_compliance_rag is in path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from cad_compliance_rag.src.retrieval import retrieve_evidence
except ImportError as e:
    print(f"Warning: Could not import retrieval module: {e}")
    retrieve_evidence = None

router = APIRouter(prefix="/api", tags=["chat"])

# ==========================================
# Room Types for Keyword Extraction
# ==========================================
ROOM_TYPES_AR = {
    "غرفة نوم": "Bedroom",
    "مطبخ": "Kitchen",
    "حمام": "Bathroom",
    "دورة مياه": "Bathroom",
    "صالة": "Living Room",
    "غرفة معيشة": "Living Room",
    "مجلس": "Majlis",
    "غرفة طعام": "Dining Room",
    "مدخل": "Entrance",
    "ممر": "Corridor",
    "درج": "Stairs",
    "سلم": "Stairs",
    "شرفة": "Balcony",
    "بلكونة": "Balcony",
}

COMPLIANCE_KEYWORDS_AR = [
    "مساحة", "الحد الأدنى", "أقل", "متطلبات", "كود", "مخالفة", 
    "تهوية", "إضاءة", "نافذة", "ارتفاع", "عرض", "طول", "أبعاد"
]


class ChatRequest(BaseModel):
    message: str
    task_id: str = None


class ChatResponse(BaseModel):
    reply: str


def extract_keywords(message: str) -> dict:
    """
    Extract intelligent keywords from user message for better RAG retrieval.
    Returns structured query with keywords, room types, and boost terms.
    """
    keywords = []
    room_type = None
    boost_keywords = []
    must_include = []
    
    message_lower = message.lower()
    
    # 1. Extract room types
    for ar_name, en_name in ROOM_TYPES_AR.items():
        if ar_name in message:
            room_type = en_name
            keywords.append(ar_name)
            must_include.append(ar_name)
            break
    
    # 2. Extract compliance-related keywords for boosting
    for kw in COMPLIANCE_KEYWORDS_AR:
        if kw in message:
            boost_keywords.append(kw)
            keywords.append(kw)
    
    # 3. Extract numbers (dimensions, areas)
    numbers = re.findall(r'\d+\.?\d*', message)
    for num in numbers:
        keywords.append(num)
    
    # 4. Add the full message as a keyword too
    keywords.append(message)
    
    return {
        "keywords": keywords,
        "room_type": room_type,
        "boost_keywords": boost_keywords,
        "must_include_any_keywords": must_include,
        "doc": "__ALL__"
    }


def format_context_with_citations(results: list) -> str:
    """Format RAG results with clear citations for the LLM."""
    if not results:
        return "لا تتوفر معلومات محددة من كود البناء."
    
    formatted_chunks = []
    for i, r in enumerate(results, 1):
        doc = r.get('doc', 'SBC')
        section = r.get('section', 'N/A')
        quote = r.get('quote', '')
        
        # Create citation reference
        citation = f"[{doc} - {section}]"
        formatted_chunks.append(f"=== المرجع {i} {citation} ===\n{quote}")
    
    return "\n\n".join(formatted_chunks)


@router.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """Chat with AI about Saudi Building Code - Enhanced with structured prompts."""
    try:
        print(f"Chat request: {request.message[:50]}...")
        
        # 1. Enhanced RAG Retrieval with smart keyword extraction
        context_text = ""
        sources_available = False
        
        if retrieve_evidence:
            try:
                # Build intelligent query from user message
                evidence_query = extract_keywords(request.message)
                print(f"RAG Query: {evidence_query}")
                
                results = retrieve_evidence(evidence_query, top_k=5)
                
                if results:
                    context_text = format_context_with_citations(results)
                    sources_available = True
                    print(f"Retrieved {len(results)} context chunks with scores")
            except Exception as e:
                print(f"Retrieval failed: {e}")

        # Create OpenRouter client
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        
        # Enhanced System Prompt with Structured Guidance
        system_prompt = f"""# هويتك
أنت "عماد" (Emad)، مستشار هندسي ذكي متخصص في كود البناء السعودي السكني (SBC 1101) واشتراطات البناء السكني.

# مهمتك الأساسية
الإجابة عن أسئلة المستخدمين حول متطلبات كود البناء السعودي بدقة عالية مع الاستشهاد بالمصادر.

# قواعد الاستجابة (اتبعها بدقة):

## 1. عند توفر معلومات من الكود:
- أجب بناءً على المعلومات المتوفرة فقط
- اذكر المرجع بوضوح: [المصدر: SBC1101، القسم: X.X]
- لا تختلق معلومات غير موجودة في السياق

## 2. عند عدم توفر معلومات كافية:
- ابدأ بـ: "لم أجد معلومات محددة في قاعدة البيانات حول هذا الموضوع..."
- يمكنك تقديم إرشادات عامة مع التنويه بذلك

## 3. عند السؤال عن مخالفات:
- اشرح سبب المخالفة بوضوح
- اذكر المتطلب الصحيح من الكود
- قدم اقتراحاً للحل أو التصحيح

## 4. تنسيق الإجابة:
- استخدم فقرات قصيرة (2-3 فقرات كحد أقصى)
- استخدم الترقيم عند تعداد النقاط
- كن مختصراً ومفيداً

# المعلومات المتوفرة من كود البناء:
{"=" * 40}
{context_text if context_text else "لا تتوفر معلومات محددة لهذا الاستعلام."}
{"=" * 40}

# ملاحظة هامة:
{"تتوفر مراجع من الكود أعلاه - استخدمها للإجابة واذكر المصدر." if sources_available else "لا تتوفر مراجع محددة - أجب بشكل عام مع التنويه بذلك."}
"""

        # Try multiple models with increased token limit
        models = ["x-ai/grok-2-1212", "openai/gpt-4o-mini", "google/gemini-flash-1.5"]
        
        for model_id in models:
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": request.message}
                    ],
                    max_tokens=700,
                    temperature=0.3  # Lower temperature for more factual responses
                )
                
                reply = response.choices[0].message.content.strip()
                print(f"Chat reply from {model_id}: {reply[:50]}...")
                return {"reply": reply}
                
            except Exception as model_error:
                print(f"Chat {model_id} Error: {model_error}")
                continue
        
        # All models failed - return fallback
        return {"reply": "عذراً، لم أتمكن من معالجة طلبك الآن. يرجى المحاولة مرة أخرى."}
        
    except Exception as e:
        print(f"Chat error: {e}")
        return {"reply": f"حدث خطأ: {str(e)}"}
