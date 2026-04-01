import requests
import json
import os
from typing import Dict, Any, Optional

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def analyze_hardware(hardware_name: str, is_cpu: bool = True, language: str = "TR") -> Dict[str, Any]:
    """
    Analyzes hardware using AI backend.
    
    Args:
        hardware_name: Name of the hardware component
        is_cpu: True for CPU, False for GPU
        language: Response language (default: TR)
    
    Returns:
        Dict with analysis results or error
    """
    try:
        url = f"{BACKEND_URL}/api/analyze"
        payload = {
            "hardware_name": hardware_name,
            "is_cpu": is_cpu,
            "language": language
        }
        
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Sunucu Hatası ({response.status_code}): {response.text}"}
            
    except requests.exceptions.Timeout:
        return {"error": "⏳ Sunucu yanıt vermiyor. Lütfen backend'in çalıştığından emin olun."}
    except requests.exceptions.ConnectionError:
        return {"error": f"❌ Backend'e bağlanılamadı ({BACKEND_URL}). Backend çalışıyor mu?"}
    except Exception as e:
        return {"error": f"Beklenmeyen Hata: {str(e)}"}


def general_chat(user_message: str, system_context: str = "", language: str = "TR") -> str:
    """
    General chat with AI assistant.
    
    Args:
        user_message: User's question
        system_context: Optional system context
        language: Response language (default: TR)
    
    Returns:
        AI response string
    """
    try:
        url = f"{BACKEND_URL}/api/chat"
        payload = {
            "user_message": user_message,
            "system_context": system_context,
            "language": language
        }
        
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            return response.json().get("response", "Boş cevap döndü.")
        else:
            return f"❌ Sunucu Hatası ({response.status_code}): {response.text}"
            
    except requests.exceptions.Timeout:
        return "⏳ Sunucu yanıt vermiyor. Backend çalışıyor mu?"
    except requests.exceptions.ConnectionError:
        return f"❌ Backend'e bağlanılamadı ({BACKEND_URL})."
    except Exception as e:
        return f"❌ Beklenmeyen Hata: {str(e)}"


def check_backend_health() -> Dict[str, Any]:
    """
    Checks if backend is running and healthy.
    
    Returns:
        Dict with health status
    """
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"status": "error", "detail": f"Status code: {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "detail": f"Backend'e bağlanılamadı ({BACKEND_URL})"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
