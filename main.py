import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from starlette.staticfiles import StaticFiles
import httpx
import logging
import json

from app.config import get_settings
from app.crypto import Cryptor
from app.database import init_db
from app.routes import router as admin_router
from app.middleware import AuthMiddleware, ProxyMiddleware


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MyLinspirer Proxy")

settings = get_settings()
cryptor = Cryptor(
    key=settings.LINSPIRER_KEY.encode(),
    iv=settings.LINSPIRER_IV.encode()
)

os.makedirs("./data", exist_ok=True)
os.makedirs("./static", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)
app.add_middleware(ProxyMiddleware, cryptor=cryptor)

app.include_router(admin_router, prefix="/admin")


@app.get("/admin")
async def admin_index():
    return FileResponse("static/index.html")


@app.get("/admin/")
async def admin_indexSlash():
    return FileResponse("static/index.html")


@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("Database initialized")


@app.get("/")
async def root():
    return {"message": "MyLinspirer Proxy Server", "status": "running"}


@app.post("/public-interface.php")
async def proxy_endpoint(request: Request):
    target_url = settings.LINSPIRER_TARGET_URL
    
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.post(
                target_url,
                content=body,
                headers=headers,
                timeout=30.0,
            )
            
            return JSONResponse(
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else {},
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        except httpx.RequestError as e:
            logger.error(f"Proxy error: {e}")
            return JSONResponse(
                status_code=502,
                content={"error": f"Failed to connect to target: {str(e)}"},
            )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.LINSPIRER_HOST,
        port=settings.LINSPIRER_PORT,
        reload=True,
    )
