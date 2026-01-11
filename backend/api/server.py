import os
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from contextlib import asynccontextmanager

# Routers
from api.routers import feeds, jobs, profile, drafts
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
app = FastAPI(
    title="AutoApply API", 
    version="2.0.0",
    description="Draft-first job application preparation. This API never submits applications."
)

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
app.include_router(drafts.router)

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
        
    # Update profile
    from src.profile_manager import ProfileManager
    pm = ProfileManager()
    profile = pm.get_profile()
    profile["custom_template_filename"] = file.filename
    pm.save_profile(profile)
    
    return {"status": "uploaded", "filename": file.filename}

@app.post("/upload-resume", tags=["Settings"])
async def upload_resume(file: UploadFile = File(...)):
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".tex")):
         raise HTTPException(status_code=400, detail="Only .pdf or .tex files allowed")
    
    # Preserve extension
    ext = ".tex" if file.filename.endswith(".tex") else ".pdf"
    save_path = f"data/uploaded_resume{ext}"
    content = await file.read()
    
    with open(save_path, "wb") as f:
        f.write(content)
        
    # Update profile with path
    from src.profile_manager import ProfileManager
    pm = ProfileManager()
    profile = pm.get_profile()
    profile["uploaded_resume_path"] = os.path.abspath(save_path)
    profile["uploaded_resume_filename"] = file.filename
    # Default to enabling it upon upload ONLY if it is a specific resume type
    # For now we enable it, but JobApplicationService handles fallback if PDF is missing.
    # Note: If .tex is uploaded, we can't use it directly for application "resume_path" unless we compile it.
    # The user asked for "profile creation using tex", so we focus on parsing.
    # If they want to use it for applications, they really should upload PDF.
    # But let's allow saving it.
    profile["use_uploaded_resume"] = True
    pm.save_profile(profile)
    
    return {"status": "uploaded", "filename": file.filename, "path": save_path}

@app.post("/parse-resume", tags=["Settings"])
async def parse_resume(source: str = "resume"):
    # Retrieve file path based on source
    from src.profile_manager import ProfileManager
    pm = ProfileManager()
    profile = pm.get_profile()
    
    file_path = None
    
    if source == "template":
        # Check for template
        potential_path = "data/resume_base.tex"
        if os.path.exists(potential_path):
            file_path = potential_path
        else:
            raise HTTPException(status_code=400, detail="No custom LaTeX template found (data/resume_base.tex).")
    else:
        # Default to resume
        file_path = profile.get("uploaded_resume_path")
        if not file_path or not os.path.exists(file_path):
             raise HTTPException(status_code=400, detail="No uploaded resume found. Please upload one first.")

    # Parse with ResumeParser
    try:
        from src.resume_parser import ResumeParser
        parser = ResumeParser()
        return await parser.parse_file(file_path)
    except Exception as e:
        print(f"Resume Parsing Error: {e}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")

@app.post("/start", tags=["Control"])
async def start_automation(continuous: bool = False):

    if service_state.is_running:
        return {"status": "already_running"}
        
    # Validation: If using generated resume, template must exist
    from src.profile_manager import ProfileManager
    pm = ProfileManager()
    profile = pm.get_profile()
    
    use_uploaded = profile.get("use_uploaded_resume", False)
    template_path = "data/resume_base.tex"
    
    if not use_uploaded and not os.path.exists(template_path):
        raise HTTPException(status_code=400, detail="Cannot start: 'Use uploaded resume' is unchecked, but no custom LaTeX template found. Please upload a template or enable uploaded resume.")

    service_state.is_running = True
    service_state.stop_event = asyncio.Event()

    def log_callback(msg):
        print(f"[LOG] {msg}")
        asyncio.create_task(manager.broadcast(msg))

    asyncio.create_task(background_runner(log_callback, continuous))
    return {
        "status": "started", 
        "continuous": continuous,
        "note": "Draft-first mode: Applications will be prepared but NOT submitted. Check /drafts for results."
    }

@app.get("/status", tags=["Control"])
def get_status():
    return {"running": service_state.is_running}

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
