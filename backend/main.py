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

# Import route modules
from document_routes import router as document_router
from query_routes import router as query_router

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

# Include routers
app.include_router(document_router)
app.include_router(query_router)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Alberta Perspectives RAG API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and deployment verification."""
    try:
        # Basic environment variables check
        required_vars = ["GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.warning(f"Missing environment variables: {missing_vars}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "message": f"Missing required environment variables: {missing_vars}"
                }
            )
        
        return {
            "status": "healthy",
            "message": "All systems operational",
            "environment": os.getenv("ENVIRONMENT", "unknown")
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}"
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    ) 