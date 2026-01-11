import os
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from contextlib import asynccontextmanager

# Routers
from api.routers import feeds, jobs, profile
from api.services.logs_service import manager, LogService # We need to create this service

# Legacy imports being adapted
from src.main import run_auto_apply
from dotenv import load_dotenv

load_dotenv()

# --- Service State ---
class ServiceState:
    is_running = False
    stop_event = None

service_state = ServiceState()

# --- Application ---
app = FastAPI(title="AutoApply API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(feeds.router)
app.include_router(jobs.router)
app.include_router(profile.router)

# Static Files
if not os.path.exists("data"):
    os.makedirs("data")
app.mount("/data", StaticFiles(directory="data"), name="data")

# --- Specialized Endpoints (Upload, Control, Websockets) ---

@app.post("/upload-template", tags=["Settings"])
async def upload_template(file: UploadFile = File(...)):
    if not file.filename.endswith(".tex"):
         raise HTTPException(status_code=400, detail="Only .tex files allowed")
    
    save_path = "data/resume_base.tex"
    content = await file.read()
    
    if b"\\VAR{skills_list}" not in content:
        raise HTTPException(status_code=400, detail="Template must contain \\VAR{skills_list}")

    with open(save_path, "wb") as f:
        f.write(content)
    
    return {"status": "uploaded", "filename": file.filename}

@app.post("/start", tags=["Control"])
async def start_automation(continuous: bool = False):
    if service_state.is_running:
        return {"status": "already_running"}
    
    service_state.is_running = True
    service_state.stop_event = asyncio.Event()

    def log_callback(msg):
        print(f"[LOG] {msg}")
        asyncio.create_task(manager.broadcast(msg))

    asyncio.create_task(background_runner(log_callback, continuous))
    return {"status": "started", "continuous": continuous}

@app.post("/stop", tags=["Control"])
def stop_automation():
    if not service_state.is_running:
        return {"status": "not_running"}
    
    service_state.is_running = False
    if service_state.stop_event:
        service_state.stop_event.set()
    
    return {"status": "stopping"}

# Background Runner Wrapper
async def background_runner(log_callback, continuous):
    try:
        await run_auto_apply(log_callback, continuous=continuous, stop_event=service_state.stop_event)
    except Exception as e:
        log_callback(f"CRITICAL ERROR: {e}")
    finally:
        service_state.is_running = False
        log_callback("Automation Service Stopped.")

# Websocket endpoint
from fastapi import WebSocket, WebSocketDisconnect
@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
