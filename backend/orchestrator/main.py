import os
import sys
import json
import uuid
import sqlite3
import hashlib
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Adjust Python Path to find backend shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.shared.types import IntentObject, NormalizedLog, AnalysisResult, FinalReport
from backend.shared.utils import get_logger, get_config

logger = get_logger("Orchestrator")

app = FastAPI(title="Sentinel Forge - Orchestrator Service")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "sentinel_forge.db"

# PostgreSQL Configuration variables
AUTH_DB_TYPE = get_config("AUTH_DB_TYPE", "sqlite")
PG_HOST = get_config("POSTGRES_HOST", "")
PG_PORT = get_config("POSTGRES_PORT", "5432")
PG_DB = get_config("POSTGRES_DB", "sentinel_forge_auth")
PG_USER = get_config("POSTGRES_USER", "postgres")
PG_PASSWORD = get_config("POSTGRES_PASSWORD", "")
PG_SSLMODE = get_config("POSTGRES_SSLMODE", "prefer")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS agent_runs (
            id TEXT PRIMARY KEY,
            prompt TEXT NOT NULL,
            log_format TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS agent_steps (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            agent_name TEXT NOT NULL,
            input_payload TEXT,
            output_payload TEXT,
            status TEXT NOT NULL,
            duration_ms INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES agent_runs(id)
        )
    """)
    conn.commit()
    conn.close()

def init_auth_db():
    if AUTH_DB_TYPE == "postgresql" or PG_HOST:
        logger.info(f"Attempting connection to PostgreSQL auth database: {PG_HOST}:{PG_PORT}/{PG_DB}")
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASSWORD,
                sslmode=PG_SSLMODE
            )
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            conn.close()
            logger.info("PostgreSQL auth database initialized successfully.")
            return "postgresql"
        except Exception as e:
            logger.warning(f"PostgreSQL auth connection failed: {e}. Falling back to SQLite for auth.")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    logger.info("SQLite auth database initialized successfully.")
    return "sqlite"

# Initialize databases immediately
init_db()
active_auth_db = init_auth_db()
logger.info("Orchestrator DBs initialized.")

# Hashing Helpers
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    db_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ":" + db_hash.hex()

def verify_password(password: str, hashed: str) -> bool:
    try:
        salt_hex, hash_hex = hashed.split(":")
        salt = bytes.fromhex(salt_hex)
        db_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return db_hash.hex() == hash_hex
    except Exception:
        return False

# Database User CRUD
def db_create_user(username: str, email: str, password_hash: str) -> bool:
    if active_auth_db == "postgresql":
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASSWORD,
                sslmode=PG_SSLMODE
            )
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, password_hash)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"PostgreSQL create user error: {e}")
            raise HTTPException(status_code=500, detail=f"Database write failure: {e}")
    else:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Username or email already exists.")
        except Exception as e:
            logger.error(f"SQLite create user error: {e}")
            raise HTTPException(status_code=500, detail=f"Database write failure: {e}")

def db_get_user(username: str) -> Optional[Dict[str, Any]]:
    if active_auth_db == "postgresql":
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASSWORD,
                sslmode=PG_SSLMODE
            )
            c = conn.cursor()
            c.execute("SELECT username, email, password_hash FROM users WHERE username = %s", (username,))
            row = c.fetchone()
            conn.close()
            if row:
                return {"username": row[0], "email": row[1], "password_hash": row[2]}
            return None
        except Exception as e:
            logger.error(f"PostgreSQL get user error: {e}")
            return None
    else:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT username, email, password_hash FROM users WHERE username = ?", (username,))
            row = c.fetchone()
            conn.close()
            if row:
                return {"username": row[0], "email": row[1], "password_hash": row[2]}
            return None
        except Exception as e:
            logger.error(f"SQLite get user error: {e}")
            return None

# Auth Schemas
class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Sentinel Forge Central Orchestrator",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "Sentinel Forge Central Orchestrator",
        "version": "1.0.0"
    }

# Auth Routes
@app.post("/auth/signup")
async def signup(req: SignupRequest):
    if not req.username or not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Missing fields.")
    password_h = hash_password(req.password)
    db_create_user(req.username, req.email, password_h)
    return {"message": "User registered successfully.", "token": f"token_{req.username}"}

@app.post("/auth/login")
async def login(req: LoginRequest):
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Missing username or password.")
    if req.username == "admin" and req.password == "admin":
        return {"message": "Success", "username": "admin", "email": "admin@sentinelforge.ai", "token": "token_admin"}
    user = db_get_user(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    return {"message": "Success", "username": req.username, "email": user["email"], "token": f"token_{req.username}"}

@app.get("/auth/profile")
def get_user_profile(username: str):
    if username == "admin":
        return {"username": "admin", "email": "admin@sentinelforge.ai"}
    user = db_get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": user["username"], "email": user["email"]}

# Endpoint base URLs mapping (allow overriding via env vars for Docker Compose integration)
INTENT_URL = get_config("INTENT_SERVICE_URL", "http://localhost:8001")
DATA_URL = get_config("DATA_SERVICE_URL", "http://localhost:8002")
ANALYSIS_URL = get_config("ANALYSIS_SERVICE_URL", "http://localhost:8003")
REPORT_URL = get_config("REPORT_SERVICE_URL", "http://localhost:8004")
RESPONSE_URL = get_config("RESPONSE_SERVICE_URL", "http://localhost:8005")

class OrchestratorRequest(BaseModel):
    prompt: str
    logs_raw: str
    log_format: str = "Syslog"
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None

def save_run(run_id: str, prompt: str, log_format: str, status: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO agent_runs (id, prompt, log_format, status, updated_at) VALUES (?, ?, ?, ?, ?)",
        (run_id, prompt, log_format, status, datetime.utcnow())
    )
    conn.commit()
    conn.close()

def save_step(step_id: str, run_id: str, agent_name: str, input_p: str, output_p: str, status: str, duration: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO agent_steps (id, run_id, agent_name, input_payload, output_payload, status, duration_ms) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (step_id, run_id, agent_name, input_p, output_p, status, duration)
    )
    conn.commit()
    conn.close()

async def run_orchestration_pipeline(run_id: str, request: OrchestratorRequest):
    """Executes all agent steps sequentially, yielding JSON SSE events."""
    async def sse_event(event_type: str, data: Dict[str, Any]):
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    # 1. Pipeline Start
    save_run(run_id, request.prompt, request.log_format, "RUNNING")
    yield await sse_event("pipeline_started", {"run_id": run_id, "timestamp": datetime.utcnow().isoformat()})
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # ---- STEP 1: Intent Agent ----
        intent_step_id = uuid.uuid4().hex[:8]
        yield await sse_event("intent_started", {"step_id": intent_step_id})
        start_time = datetime.utcnow()
        
        intent_obj = None
        try:
            intent_payload = {
                "prompt": request.prompt,
                "provider": request.provider,
                "model": request.model,
                "api_key": request.api_key,
                "api_base_url": request.api_base_url
            }
            resp = await client.post(f"{INTENT_URL}/analyze-intent", json=intent_payload)
            resp.raise_for_status()
            intent_obj = resp.json()
            
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            save_step(intent_step_id, run_id, "INTENT", json.dumps(intent_payload), json.dumps(intent_obj), "COMPLETED", duration)
            yield await sse_event("intent_completed", {"step_id": intent_step_id, "output": intent_obj, "duration_ms": duration})
        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            save_step(intent_step_id, run_id, "INTENT", request.prompt, str(e), "FAILED", duration)
            save_run(run_id, request.prompt, request.log_format, "FAILED")
            yield await sse_event("pipeline_failed", {"agent": "INTENT", "error": str(e)})
            return

        # ---- STEP 2: Data Agent ----
        data_step_id = uuid.uuid4().hex[:8]
        yield await sse_event("data_started", {"step_id": data_step_id})
        start_time = datetime.utcnow()
        
        data_obj = None
        try:
            data_payload = {
                "intent": intent_obj,
                "logs_raw": request.logs_raw,
                "log_format": request.log_format
            }
            resp = await client.post(f"{DATA_URL}/process-data", json=data_payload)
            resp.raise_for_status()
            data_obj = resp.json()
            
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            save_step(data_step_id, run_id, "DATA", json.dumps(data_payload), json.dumps(data_obj), "COMPLETED", duration)
            yield await sse_event("data_completed", {"step_id": data_step_id, "output": data_obj, "duration_ms": duration})
        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            save_step(data_step_id, run_id, "DATA", json.dumps(intent_obj), str(e), "FAILED", duration)
            save_run(run_id, request.prompt, request.log_format, "FAILED")
            yield await sse_event("pipeline_failed", {"agent": "DATA", "error": str(e)})
            return

        # ---- STEP 3: Analysis Agent ----
        analysis_step_id = uuid.uuid4().hex[:8]
        yield await sse_event("analysis_started", {"step_id": analysis_step_id})
        start_time = datetime.utcnow()
        
        analysis_obj = None
        try:
            analysis_payload = {
                "intent": intent_obj,
                "logs": data_obj["logs_normalized"],
                "metrics": data_obj["metrics"],
                "provider": request.provider,
                "model": request.model,
                "api_key": request.api_key,
                "api_base_url": request.api_base_url
            }
            resp = await client.post(f"{ANALYSIS_URL}/analyze-metrics", json=analysis_payload)
            resp.raise_for_status()
            analysis_obj = resp.json()
            
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            save_step(analysis_step_id, run_id, "ANALYSIS", json.dumps(analysis_payload), json.dumps(analysis_obj), "COMPLETED", duration)
            yield await sse_event("analysis_completed", {"step_id": analysis_step_id, "output": analysis_obj, "duration_ms": duration})
        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            save_step(analysis_step_id, run_id, "ANALYSIS", json.dumps(data_obj), str(e), "FAILED", duration)
            save_run(run_id, request.prompt, request.log_format, "FAILED")
            yield await sse_event("pipeline_failed", {"agent": "ANALYSIS", "error": str(e)})
            return

        # ---- STEP 4: Response Agent ----
        response_step_id = uuid.uuid4().hex[:8]
        yield await sse_event("response_started", {"step_id": response_step_id})
        start_time = datetime.utcnow()
        
        response_obj = None
        try:
            response_payload = {
                "analysis_result": analysis_obj,
                "metrics": data_obj.get("metrics"),
                "provider": request.provider,
                "model": request.model,
                "api_key": request.api_key,
                "api_base_url": request.api_base_url
            }
            resp = await client.post(f"{RESPONSE_URL}/mitigate-incident", json=response_payload)
            resp.raise_for_status()
            response_obj = resp.json()
            
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            save_step(response_step_id, run_id, "RESPONSE", json.dumps(response_payload), json.dumps(response_obj), "COMPLETED", duration)
            yield await sse_event("response_completed", {"step_id": response_step_id, "output": response_obj, "duration_ms": duration})
        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            save_step(response_step_id, run_id, "RESPONSE", json.dumps(analysis_obj), str(e), "FAILED", duration)
            save_run(run_id, request.prompt, request.log_format, "FAILED")
            yield await sse_event("pipeline_failed", {"agent": "RESPONSE", "error": str(e)})
            return

        # ---- STEP 5: Report Agent ----
        report_step_id = uuid.uuid4().hex[:8]
        yield await sse_event("report_started", {"step_id": report_step_id})
        start_time = datetime.utcnow()
        
        report_obj = None
        try:
            report_payload = {
                "intent": intent_obj,
                "analysis_result": analysis_obj,
                "mitigation_actions": response_obj.get("mitigation_actions", []),
                "metrics": data_obj.get("metrics"),
                "provider": request.provider,
                "model": request.model,
                "api_key": request.api_key,
                "api_base_url": request.api_base_url
            }
            resp = await client.post(f"{REPORT_URL}/generate-report", json=report_payload)
            resp.raise_for_status()
            report_obj = resp.json()
            
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            save_step(report_step_id, run_id, "REPORT", json.dumps(report_payload), json.dumps(report_obj), "COMPLETED", duration)
            yield await sse_event("report_completed", {"step_id": report_step_id, "output": report_obj, "duration_ms": duration})
        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            save_step(report_step_id, run_id, "REPORT", json.dumps(analysis_obj), str(e), "FAILED", duration)
            save_run(run_id, request.prompt, request.log_format, "FAILED")
            yield await sse_event("pipeline_failed", {"agent": "REPORT", "error": str(e)})
            return

    save_run(run_id, request.prompt, request.log_format, "COMPLETED")
    yield await sse_event("pipeline_completed", {
        "run_id": run_id,
        "final_report": report_obj,
        "response_actions": response_obj,
        "timestamp": datetime.utcnow().isoformat()
    })

@app.post("/analyze")
async def analyze(request: OrchestratorRequest):
    """Start log analysis and return full result directly (non-streaming)."""
    run_id = uuid.uuid4().hex[:8]
    logger.info(f"Triggering synchronous pipeline. RunID={run_id}")
    
    # Simple runner aggregator
    results = {}
    async for event in run_orchestration_pipeline(run_id, request):
        if "pipeline_failed" in event:
            raise HTTPException(status_code=502, detail="Subagent execution in orchestration pipeline failed.")
        if "pipeline_completed" in event:
            # Extract data
            data_line = [line for line in event.splitlines() if line.startswith("data: ")][0]
            results = json.loads(data_line[6:])
            
    return results

@app.post("/analyze/stream")
async def analyze_stream(request: OrchestratorRequest):
    """Start log analysis and stream detailed agent steps via Server-Sent Events (SSE)."""
    run_id = uuid.uuid4().hex[:8]
    logger.info(f"Triggering streaming pipeline. RunID={run_id}")
    return StreamingResponse(
        run_orchestration_pipeline(run_id, request),
        media_type="text/event-stream"
    )

@app.get("/runs")
def get_runs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM agent_runs ORDER BY created_at DESC")
    runs = [dict(row) for row in c.fetchall()]
    conn.close()
    return runs

@app.get("/runs/{run_id}")
def get_run_details(run_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,))
    run = c.fetchone()
    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail="Run not found")
        
    c.execute("SELECT * FROM agent_steps WHERE run_id = ? ORDER BY created_at ASC", (run_id,))
    steps = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return {
        "run": dict(run),
        "steps": steps
    }

@app.get("/simulator/logs")
def get_simulator_logs(
    scenario: str = "Normal System Activity", 
    format: str = "Syslog", 
    rate: int = 5, 
    duration: int = 10,
    ip: Optional[str] = None,
    user: Optional[str] = None
):
    from backend.orchestrator.simulator import generate_log_batch
    custom_params = {}
    if ip:
        custom_params["ip"] = ip
    if user:
        custom_params["user"] = user
        
    logs = generate_log_batch(scenario, format, rate, duration, custom_params)
    return "\n".join(logs)

@app.get("/live-logs")
def get_live_logs():
    import random
    ips = ["192.168.1.105", "10.0.0.12", "192.168.1.44", "172.16.4.8"]
    selected_ip = random.choice(ips)
    messages = [
        f"Jun 13 00:20:15 auth-server sshd[521]: Failed password for root from {selected_ip} port 51300 ssh2",
        f"Jun 13 00:20:18 gateway nginx: {selected_ip} - - [13/Jun/2026:00:20:18 +0000] \"GET /admin/settings HTTP/1.1\" 401 102",
        f"Jun 13 00:20:20 host-monitor systemd[1]: Service docker.service entered active state.",
        f"Jun 13 00:20:25 db-server postgres[881]: WARNING: connection timeout for user read_only from {selected_ip}"
    ]
    # Return 3 random log entries joined by newlines
    return "\n".join(random.sample(messages, 3))

class ModelListRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None

@app.post("/list-models")
async def list_models(request: ModelListRequest):
    provider = request.provider.lower()
    api_key = request.api_key
    base_url = request.api_base_url
    
    # Establish defaults
    if not base_url:
        if provider == "openai":
            base_url = "https://api.openai.com/v1"
        elif provider == "groq":
            base_url = "https://api.groq.com/openai/v1"
        elif provider == "ollama":
            base_url = "http://localhost:11434/v1"
        elif provider == "anthropic":
            base_url = "https://api.anthropic.com/v1"
        elif provider == "gemini":
            base_url = "https://generativelanguage.googleapis.com"
        elif provider == "custom":
            base_url = "http://localhost:1234/v1"
            
    models = []
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if provider == "gemini":
                if not api_key:
                    raise HTTPException(status_code=400, detail="Gemini API Key is required.")
                url = f"{base_url.rstrip('/')}/v1beta/models?key={api_key}"
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                if "models" in data:
                    models = [m["name"].replace("models/", "") for m in data["models"]]
            elif provider == "anthropic":
                models = [
                    "claude-3-5-sonnet-20241022",
                    "claude-3-5-sonnet-20240620",
                    "claude-3-5-haiku-20241022",
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307"
                ]
            else:
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                
                clean_url = base_url.rstrip("/")
                
                # Try standard /models
                try:
                    resp = await client.get(f"{clean_url}/models", headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, dict) and "data" in data:
                            models = [m["id"] for m in data["data"] if "id" in m]
                        elif isinstance(data, list):
                            models = [m.get("id") or m.get("name") if isinstance(m, dict) else m for m in data]
                except Exception:
                    pass
                
                # Try /model if empty
                if not models:
                    try:
                        resp = await client.get(f"{clean_url}/model", headers=headers)
                        if resp.status_code == 200:
                            data = resp.json()
                            if isinstance(data, list):
                                models = [m.get("id") or m.get("name") if isinstance(m, dict) else m for m in data]
                            elif isinstance(data, dict):
                                if "id" in data:
                                    models = [data["id"]]
                                elif "model" in data:
                                    models = [data["model"]]
                    except Exception:
                        pass
                
                # Try Ollama specific /api/tags if the above failed
                if not models:
                    try:
                        root_url = clean_url.replace("/v1", "")
                        resp = await client.get(f"{root_url}/api/tags")
                        if resp.status_code == 200:
                            data = resp.json()
                            if "models" in data:
                                models = [m["name"] for m in data["models"]]
                    except Exception:
                        pass
                        
        return {"models": models}
        
    except Exception as e:
        logger.error(f"Error fetching models for {provider}: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch models: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

