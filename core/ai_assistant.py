import json
import os
from typing import Dict, Any, Optional
from google import genai
from google.genai import types

# API key - embedded for distribution
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyB_WSEAF9MqDamosprk8hrzaCVBVbYulT4")

def analyze_hardware(hardware_name: str, is_cpu: bool = True, language: str = "TR") -> Dict[str, Any]:
    """
    Analyzes hardware using Gemini AI directly (no backend needed).
    
    Args:
        hardware_name: Name of the hardware component
        is_cpu: True for CPU, False for GPU
        language: Response language (default: TR)
    
    Returns:
        Dict with analysis results or error
    """
    try:
        if not API_KEY:
            return {"error": "❌ API key bulunamadı. .env dosyasını kontrol edin."}
        
        client = genai.Client(api_key=API_KEY)
        
        component_type = "CPU" if is_cpu else "GPU"
        lang_text = "Türkçe" if language == "TR" else "English"
        
        prompt = f"""
        {lang_text} dilinde {component_type} analizi yap:
        
        Donanım: {hardware_name}
        
        Şunları içer:
        1. Genel Değerlendirme (2-3 cümle)
        2. Güçlü Yönler (3 madde)
        3. Zayıf Yönler (2 madde)
        4. Kullanım Senaryoları (oyun, iş, vb.)
        5. Fiyat/Performans Değerlendirmesi
        
        Kısa ve öz yaz.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        return {
            "hardware_name": hardware_name,
            "analysis": response.text,
            "component_type": component_type
        }
            
    except Exception as e:
        return {"error": f"AI Hatası: {str(e)}"}


def general_chat(user_message: str, system_context: str = "", language: str = "TR") -> str:
    """
    General chat with AI assistant (no backend needed).
    
    Args:
        user_message: User's question
        system_context: Optional system context
        language: Response language (default: TR)
    
    Returns:
        AI response string
    """
    try:
        if not API_KEY:
            return "❌ API key bulunamadı. .env dosyasını kontrol edin."
        
        client = genai.Client(api_key=API_KEY)
        
        lang_text = "Türkçe" if language == "TR" else "English"
        
        full_prompt = f"{lang_text} dilinde cevap ver.\n\n"
        if system_context:
            full_prompt += f"Bağlam: {system_context}\n\n"
        full_prompt += f"Soru: {user_message}"
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt
        )
        return response.text
            
    except Exception as e:
        return f"❌ AI Hatası: {str(e)}"


def check_backend_health() -> Dict[str, Any]:
    """
    Checks if AI is working (no backend needed).
    
    Returns:
        Dict with health status
    """
    try:
        if not API_KEY:
            return {"status": "error", "message": "API key bulunamadı"}
        
        client = genai.Client(api_key=API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents="Test"
        )
        
        return {"status": "ok", "message": "AI çalışıyor"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
