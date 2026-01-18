
import json
import os
import uuid
from datetime import datetime, timedelta
import pytz

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
LLMS_FILE = os.path.join(DATA_DIR, "llms.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")

# Eastern Time for Reset (3:01 AM EST)
EST = pytz.timezone('US/Eastern')

def get_next_reset_time():
    now = datetime.now(EST)
    target = now.replace(hour=3, minute=1, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target.isoformat()

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def get_sdk_id_by_provider_model(llms_data, provider, model_name):
    """Finds the SDK UUID matching the provider and model."""
    # Normalization map for legacy config values
    provider_map = {
        "google": "google",
        "cerebras": "cerebras",
        "openai_compatible": "openai_compatible",
        "openrouter": "openai_compatible" # legacy might count openrouter as compatible
    }
    
    normalized_provider = provider_map.get(provider, provider)
    
    for sdk in llms_data:
        if sdk["provider"] == normalized_provider and sdk["model_name"] == model_name:
            return sdk["id"]
        
        # Fallback loose matching
        if sdk["model_name"] in model_name or model_name in sdk["model_name"]:
             if sdk["provider"] == normalized_provider:
                 return sdk["id"]
                 
    return None

def migrate():
    print("Starting configuration migration...")
    
    config = load_json(CONFIG_FILE)
    llms = load_json(LLMS_FILE)
    
    if not config or not llms:
        print("Config or LLMs file missing. Aborting.")
        return

    if "user_llm_configs" in config:
        print("Migration already appears to be done (user_llm_configs exists).")
        return

    new_configs = []
    
    # 1. Migrate Free Configs
    free_configs = config.get("free_configs", [])
    print(f"Found {len(free_configs)} free configurations.")
    
    for fc in free_configs:
        sdk = fc.get("sdk") # "google", "cerebras", etc
        model = fc.get("model")
        api_key = fc.get("api_key")
        
        sdk_id = get_sdk_id_by_provider_model(llms, sdk, model)
        
        if sdk_id:
            new_configs.append({
                "id": str(uuid.uuid4()),
                "sdk_id": sdk_id,
                "name": f"{sdk.title()} {model}",
                "api_key": api_key,
                "plan_type": "free",
                "tokens_used_today": 0,
                "last_used_at": None,
                "reset_at": get_next_reset_time()
            })
        else:
            print(f"Warning: Could not find SDK for free config: {sdk}/{model}")

    # 2. Migrate Paid Config (from .env or config)
    # Check .env for OPENROUTER_API_KEY
    paid_key = None
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            for line in f:
                if line.startswith("OPENROUTER_API_KEY="):
                    paid_key = line.strip().split("=", 1)[1].strip().strip('"')
                    break
    
    # If not in env, check config (legacy)
    if not paid_key:
         paid_key = config.get("openrouter_api_key")

    selected_model = config.get("selected_model", "anthropic/claude-3.5-sonnet")
    
    if paid_key:
        print(f"Found paid OpenRouter configuration.")
        # Default to the Claude 3.5 Sonnet SDK for the main paid key
        # Ideally we find the SDK matching 'selected_model', but if not, fallback to default paid SDK
        sdk_id = get_sdk_id_by_provider_model(llms, "openai_compatible", selected_model)
        
        # If specific model not found in our limited SDK list, map to the default Claude definition
        if not sdk_id:
             # Find the paid-only SDK (OpenRouter Claude)
             for sdk in llms:
                 if "paid" in sdk["plans_supported"] and "free" not in sdk["plans_supported"]:
                     sdk_id = sdk["id"]
                     break
        
        if sdk_id:
             new_configs.append({
                "id": str(uuid.uuid4()),
                "sdk_id": sdk_id,
                "name": "Paid Plan (OpenRouter)",
                "api_key": paid_key,
                "plan_type": "paid",
                "tokens_used_today": 0,
                "last_used_at": None,
                "reset_at": get_next_reset_time()
            })
    
    # Update Config
    config["user_llm_configs"] = new_configs
    
    # Optional cleanup handles
    # del config["free_configs"] 
    
    save_json(CONFIG_FILE, config)
    print(f"Migration complete. Added {len(new_configs)} user configurations.")

if __name__ == "__main__":
    migrate()
