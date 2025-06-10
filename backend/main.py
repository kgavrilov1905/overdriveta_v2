"""
Alberta Perspectives RAG API
Main FastAPI application for processing economic research documents and providing AI-powered responses.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging

# Import route modules - TEMPORARILY COMMENTED OUT FOR DEBUGGING
# from document_routes import router as document_router
# from query_routes import router as query_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Alberta Perspectives RAG API",
    description="RAG system for economic research document processing and querying",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for frontend integration
cors_origins = os.getenv("CORS_ORIGINS", '["http://localhost:3000"]')
if isinstance(cors_origins, str):
    import json
    cors_origins = json.loads(cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins + ["https://*.vercel.app"],  # Allow all Vercel subdomains
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers - TEMPORARILY COMMENTED OUT FOR DEBUGGING
# app.include_router(document_router)
# app.include_router(query_router)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Alberta Perspectives RAG API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/debug/env")
async def debug_env():
    """Debug endpoint to see environment variables (for troubleshooting only)."""
    env_vars = {
        "GEMINI_API_KEY": "SET" if os.getenv("GEMINI_API_KEY") else "NOT SET",
        "SUPABASE_URL": "SET" if os.getenv("SUPABASE_URL") else "NOT SET", 
        "SUPABASE_KEY": "SET" if os.getenv("SUPABASE_KEY") else "NOT SET",
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "NOT SET"),
        "PORT": os.getenv("PORT", "NOT SET"),
        "RAILWAY_ENVIRONMENT": os.getenv("RAILWAY_ENVIRONMENT", "NOT SET"),
        "all_env_vars": list(os.environ.keys())[:10]  # First 10 env vars to see what's available
    }
    return env_vars

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "message": "Basic app is running",
        "environment": os.getenv("ENVIRONMENT", "unknown")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    ) 