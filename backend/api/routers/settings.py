from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.config import ConfigManager

router = APIRouter(prefix="/settings", tags=["Settings"])

class APIKeyUpdate(BaseModel):
    key_name: str
    key_value: str

class ModelSelection(BaseModel):
    model_id: str

# Available models from OpenRouter (curated list of quality models)
AVAILABLE_MODELS = [
    {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet 4", "provider": "Anthropic", "description": "Latest Claude model, excellent for complex tasks"},
    {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "Anthropic", "description": "Fast and capable, great balance of speed and quality"},
    {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "provider": "Anthropic", "description": "Fastest Claude model, ideal for simple tasks"},
    {"id": "anthropic/claude-haiku-4.5", "name": "Claude Haiku 4.5", "provider": "Anthropic", "description": "Latest Haiku, optimized for speed and low cost"},
    {"id": "anthropic/claude-opus-4.5", "name": "Claude Opus 4.5", "provider": "Anthropic", "description": "Newest Opus with top-tier reasoning and quality"},
    {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "OpenAI", "description": "OpenAI's flagship multimodal model"},
    {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "OpenAI", "description": "Smaller, faster, more affordable GPT-4o"},
    {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash", "provider": "Google", "description": "Google's fast and efficient model"},
    {"id": "google/gemini-pro-1.5", "name": "Gemini Pro 1.5", "provider": "Google", "description": "Advanced reasoning with long context"},
    {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "provider": "Meta", "description": "Open-source powerhouse, great for general tasks"},
    {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat", "provider": "DeepSeek", "description": "Cost-effective with strong performance"},
    {"id": "qwen/qwen-2.5-72b-instruct", "name": "Qwen 2.5 72B", "provider": "Alibaba", "description": "Strong multilingual capabilities"},
]

@router.get("/keys")
def get_key_status():
    """Returns which keys are configured (without revealing values)."""
    cm = ConfigManager()
    # Check for common keys
    keys = ["OPENROUTER_API_KEY"]
    status = []
    for k in keys:
        val = cm.get_api_key(k)
        status.append({
            "name": k,
            "configured": bool(val)
        })
    return status

@router.post("/keys")
def set_api_key(payload: APIKeyUpdate):
    """Securely updates an API key in the .env file."""
    try:
        cm = ConfigManager()
        cm.set_api_key(payload.key_name, payload.key_value)
        return {"status": "success", "message": f"Updated {payload.key_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
def get_available_models():
    """Returns the list of available models for selection."""
    return AVAILABLE_MODELS

@router.get("/model")
def get_selected_model():
    """Returns the currently selected model."""
    cm = ConfigManager()
    selected = cm.get_selected_model()
    return {"model_id": selected}

@router.post("/model")
def set_selected_model(payload: ModelSelection):
    """Sets the selected model for LLM operations."""
    # Validate model exists in our list
    valid_ids = [m["id"] for m in AVAILABLE_MODELS]
    if payload.model_id not in valid_ids:
        raise HTTPException(status_code=400, detail=f"Invalid model: {payload.model_id}")
    
    cm = ConfigManager()
    cm.set_selected_model(payload.model_id)
    return {"status": "success", "model_id": payload.model_id}

@router.get("/ats-prompts")
def get_ats_prompts():
    """Retrieves custom ATS prompts."""
    cm = ConfigManager()
    return cm.get_ats_prompts()

@router.post("/ats-prompts")
def set_ats_prompts(prompts: dict):
    """Updates custom ATS prompts."""
    try:
        cm = ConfigManager()
        cm.set_ats_prompts(prompts)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
