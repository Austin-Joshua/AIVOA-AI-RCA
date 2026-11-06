from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models.audit import User
from app.services.groq_service import groq_service
from app.core.config import settings

router = APIRouter()

@router.get("/ai")
async def get_ai_config(current_user: User = Depends(get_current_user)):
    """
    Returns active AI LLM provider status and model name.
    Strictly requires authentication. Never exposes API keys.
    """
    return {
        "provider": "Groq",
        "model": groq_service.model,
        "is_configured": groq_service.is_available(),
        "autodiscover": getattr(settings, "GROQ_MODEL_AUTODISCOVER", False)
    }

