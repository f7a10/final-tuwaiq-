import os
from openai import OpenAI
from inference_sdk import InferenceHTTPClient

# --- Configuration ---
# In a real app, use os.getenv("KEY_NAME")
# For this prototype, we'll keep the provided keys or placeholders via os.getenv with fallbacks if preferred, 
# but the prompt specifically asked to use os.getenv("OPENAI_API_KEY").
# To ensure it works for the user right now without them setting env vars, I will double check the instruction.
# "Use environment variable placeholders (e.g., os.getenv("OPENAI_API_KEY")) for the keys. Do not put actual keys."
# Okay, I will strictly follow this. The user might have set them in their environment or wants to restart with env vars.

class LLMService:
    def __init__(self):
        self.ai = None
        self.rf = None
        try:
            # Note: These will be None if environment variables are not set
            bg_url = "https://openrouter.ai/api/v1"
            or_key = os.getenv("OPENROUTER_API_KEY")
            rf_key = os.getenv("ROBOFLOW_API_KEY")
            
            if or_key:
                self.ai = OpenAI(base_url=bg_url, api_key=or_key)
            else:
                print("⚠️ OPENROUTER_API_KEY not found in environment variables.")

            if rf_key:
                self.rf = InferenceHTTPClient(api_url="https://detect.roboflow.com", api_key=rf_key)
            else:
                 print("⚠️ ROBOFLOW_API_KEY not found in environment variables.")
                 
        except Exception as e:
            print(f"❌ LLM Service Connection Error: {e}")

    def get_ai_client(self):
        return self.ai

    def get_roboflow_client(self):
        return self.rf

# Singleton instance
llm_service = LLMService()
