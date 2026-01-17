from fastapi import APIRouter, HTTPException, Request, Body
from pydantic import BaseModel
from src.config import ConfigManager
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["Settings"])

class APIKeyUpdate(BaseModel):
    key_name: str
    key_value: str

class ModelSelection(BaseModel):
    model_id: str

class PlanUpdate(BaseModel):
    plan_type: str

class FreeConfig(BaseModel):
    sdk: str
    model: str
    api_key: str

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
    {"id": "xiaomi/mimo-v2-flash:free", "name": "Mimo V2 Flash", "provider": "Xiaomi", "description": "Fast and efficient model"},
    {"id": "mistralai/devstral-2512:free", "name": "DevStral 2512", "provider": "Mistral", "description": "Fast and efficient model"},
    {"id": "tngtech/deepseek-r1t2-chimera:free", "name": "DeepSeek R1T2 Chimera", "provider": "DeepSeek", "description": "Fast and efficient model"},
    {"id": "openai/gpt-oss-120b:free", "name": "GPT-120B OSS", "provider": "OpenAI", "description": "OpenAI's flagship multimodal model"}
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

@router.get("/plan")
def get_plan():
    """Returns the current plan type."""
    cm = ConfigManager()
    return {"plan_type": cm.get_plan_type()}

@router.post("/plan")
def set_plan(payload: PlanUpdate):
    """Sets the current plan type."""
    if payload.plan_type not in ["paid", "free"]:
        raise HTTPException(status_code=400, detail="Invalid plan type")
    cm = ConfigManager()
    cm.set_plan_type(payload.plan_type)
    return {"status": "success", "plan_type": payload.plan_type}

@router.get("/free-configs")
def get_free_configs():
    """Returns the list of model configurations for the free plan."""
    cm = ConfigManager()
    configs = cm.get_free_configs()
    # Mask API keys for security
    masked_configs = []
    for c in configs:
        masked = c.copy()
        if masked.get("api_key"):
            key = masked["api_key"]
            if len(key) > 8:
                masked["api_key"] = key[:4] + "..." + key[-4:]
            else:
                masked["api_key"] = "****"
        masked_configs.append(masked)
    return masked_configs

@router.post("/free-configs")
async def add_free_config(payload: dict = Body(...)):
    """Adds a new model configuration to the free plan."""
    import traceback
    
    logger.info(f"Received payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Validate required fields
        sdk = payload.get("sdk")
        model = payload.get("model")
        api_key = payload.get("api_key")
        
        if not sdk or not model or not api_key:
            logger.error(f"Missing required fields. sdk={sdk}, model={model}, api_key={'present' if api_key else 'missing'}")
            raise HTTPException(status_code=400, detail="Missing required fields: sdk, model, api_key")
        
        logger.info(f"Parsed config: sdk={sdk}, model={model}, api_key={'***' if api_key else 'None'}")
        cm = ConfigManager()
        cm.add_free_config(sdk, model, api_key)
        logger.info("Free config added successfully")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding free config: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/free-configs/{index}")
def remove_free_config(index: int):
    """Removes a model configuration from the free plan."""
    cm = ConfigManager()
    if cm.remove_free_config(index):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Configuration not found")

@router.get("/llm-options")
def get_llm_options():
    """Returns the list of supported SDKs and models for the free plan."""
    import json
    import os
    # Priority: root data directory (mapped in Docker), then backend/data
    options_file = "data/llm_options.json"
    if not os.path.exists(options_file):
        options_file = "backend/data/llm_options.json"
        
    if os.path.exists(options_file):
        with open(options_file, 'r') as f:
            return json.load(f)
    return {"sdks": []}
