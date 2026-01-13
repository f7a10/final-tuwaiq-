# ==========================================
# Chat API Routes
# ==========================================

from fastapi import APIRouter
from pydantic import BaseModel
from openai import OpenAI

from backend.app.config import OPENROUTER_API_KEY

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    task_id: str = None


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """Chat with AI about Saudi Building Code."""
    try:
        print(f"💬 Chat request: {request.message[:50]}...")
        
        # Create OpenRouter client
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        
        # System prompt for Saudi Building Code expert
        system_prompt = """أنت "عماد"، مساعد ذكاء اصطناعي متخصص في كود البناء السعودي السكني (SBC 1101).

مهمتك:
- الإجابة عن أسئلة المستخدمين حول متطلبات كود البناء
- شرح أسباب المخالفات في المخططات
- تقديم حلول ومقترحات لتصحيح المخالفات

قواعد مهمة تعرفها:
- غرف النوم: الحد الأدنى 9 م²، أقل بُعد 2.7 م
- المطابخ: الحد الأدنى 4.5 م²، أقل بُعد 1.8 م
- دورات المياه: الحد الأدنى 2.5 م²، أقل بُعد 1.2 م
- غرف المعيشة: الحد الأدنى 12 م²، أقل بُعد 3.0 م
- المجلس: الحد الأدنى 14 م²، أقل بُعد 3.0 م
- غرفة الطعام: الحد الأدنى 10 م²، أقل بُعد 3.0 م
- الغرف المسكونة تحتاج نوافذ للتهوية والإضاءة الطبيعية

أجب باللغة العربية بشكل موجز ومفيد."""

        # Try multiple models
        models = ["x-ai/grok-2-1212", "openai/gpt-4o-mini", "google/gemini-flash-1.5"]
        
        for model_id in models:
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": request.message}
                    ],
                    max_tokens=500
                )
                
                reply = response.choices[0].message.content.strip()
                print(f"✓ Chat reply from {model_id}: {reply[:50]}...")
                return {"reply": reply}
                
            except Exception as model_error:
                print(f"⚠️ Chat {model_id} Error: {model_error}")
                continue
        
        # All models failed - return fallback
        return {"reply": "عذراً، لم أتمكن من معالجة طلبك الآن. يرجى المحاولة مرة أخرى."}
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return {"reply": f"حدث خطأ: {str(e)}"}
