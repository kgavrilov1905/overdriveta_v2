"""
Query processing routes for Alberta Perspectives RAG API
Handles chat queries, search testing, and system monitoring endpoints.
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from models import QueryRequest, QueryResponse, SearchResult
from rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

@router.post("/", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a user query through the RAG pipeline.
    
    Args:
        request: Query request with user input and optional parameters
        
    Returns:
        Generated response with sources and metadata
    """
    try:
        logger.info(f"Received query request: '{request.query[:100]}...'")
        
        if not request.query.strip():
            raise HTTPException(
                status_code=400,
                detail="Query cannot be empty"
            )
        
        response = await rag_service.process_query(request)
        
        logger.info(f"Query processed successfully, confidence: {response.confidence_score:.3f}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )

@router.get("/search")
async def search_documents(
    q: str = Query(..., description="Search query"),
    max_results: int = Query(5, ge=1, le=20, description="Maximum number of results"),
    threshold: float = Query(0.75, ge=0.0, le=1.0, description="Similarity threshold")
):
    """
    Search documents without LLM response generation (for testing/debugging).
    
    Args:
        q: Search query
        max_results: Maximum number of results to return
        threshold: Minimum similarity threshold
        
    Returns:
        Search results with similarity scores
    """
    try:
        logger.info(f"Performing search: '{q[:100]}...'")
        
        if not q.strip():
            raise HTTPException(
                status_code=400,
                detail="Search query cannot be empty"
            )
        
        search_results = await rag_service.get_search_results_only(
            query=q,
            max_results=max_results,
            threshold=threshold
        )
        
        logger.info(f"Search completed: {len(search_results)} results found")
        
        return {
            "query": q,
            "results": search_results,
            "total_results": len(search_results),
            "parameters": {
                "max_results": max_results,
                "threshold": threshold
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@router.post("/test")
async def test_rag_pipeline(
    test_query: str = Query("What are the main economic priorities for Alberta?", description="Test query")
):
    """
    Test the complete RAG pipeline with a sample query.
    
    Args:
        test_query: Query to test the pipeline with
        
    Returns:
        Test results with performance metrics
    """
    try:
        logger.info(f"Testing RAG pipeline with query: '{test_query}'")
        
        test_results = await rag_service.test_pipeline(test_query)
        
        logger.info(f"Pipeline test completed with status: {test_results.get('status', 'unknown')}")
        return test_results
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline test failed: {str(e)}"
        )

@router.get("/status")
async def get_system_status():
    """
    Get the status of all RAG system components.
    
    Returns:
        System status information including component health and database statistics
    """
    try:
        logger.info("Getting system status")
        
        status = await rag_service.get_system_status()
        
        # Determine HTTP status code based on overall status
        if status.get("overall_status") == "healthy":
            status_code = 200
        elif status.get("overall_status") == "degraded":
            status_code = 207  # Multi-status
        else:
            status_code = 503  # Service unavailable
        
        return JSONResponse(
            status_code=status_code,
            content=status
        )
        
    except Exception as e:
        logger.error(f"Failed to get system status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system status: {str(e)}"
        )

@router.get("/examples")
async def get_example_queries():
    """
    Get example queries that work well with the Alberta Perspectives data.
    
    Returns:
        List of example queries with descriptions
    """
    examples = [
        {
            "query": "What are the main economic priorities for Alberta?",
            "description": "General question about Alberta's economic focus areas",
            "category": "Economic Policy"
        },
        {
            "query": "What are the current hiring trends in Alberta?",
            "description": "Information about employment and hiring patterns",
            "category": "Employment"
        },
        {
            "query": "What skills training programs are available?",
            "description": "Training and development opportunities for workers",
            "category": "Skills Development"
        },
        {
            "query": "What are the main challenges facing Alberta businesses?",
            "description": "Business challenges and obstacles",
            "category": "Business Challenges"
        },
        {
            "query": "How is red tape affecting Alberta businesses?",
            "description": "Regulatory burden and compliance issues",
            "category": "Regulatory Environment"
        },
        {
            "query": "What sectors are growing in Alberta?",
            "description": "Information about expanding industries and sectors",
            "category": "Economic Growth"
        },
        {
            "query": "What are the labour market trends?",
            "description": "Workforce demographics and employment statistics",
            "category": "Labour Market"
        },
        {
            "query": "What support is available for small businesses?",
            "description": "Programs and resources for small business development",
            "category": "Business Support"
        }
    ]
    
    return {
        "examples": examples,
        "instructions": "Try these example queries to explore the Alberta Perspectives economic research data. You can also create your own queries related to Alberta's economy, business conditions, employment, and policy priorities."
    }

# Health check endpoint specific to query functionality
@router.get("/health")
async def query_health_check():
    """
    Health check specific to query processing functionality.
    
    Returns:
        Health status of query processing components
    """
    try:
        # Quick health check of core components
        health_status = {
            "status": "healthy",
            "components": {
                "rag_service": "checking...",
                "embedding_service": "checking...",
                "llm_service": "checking...",
                "database": "checking..."
            }
        }
        
        # Test basic functionality
        try:
            # Test a simple query to verify the pipeline
            test_request = QueryRequest(
                query="test query", 
                max_results=1, 
                similarity_threshold=0.9
            )
            
            # This should work even without data in the database
            response = await rag_service.process_query(test_request)
            
            health_status["components"]["rag_service"] = "healthy"
            health_status["last_test_response_time"] = response.processing_time
            
        except Exception as e:
            health_status["components"]["rag_service"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Query health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        ) 