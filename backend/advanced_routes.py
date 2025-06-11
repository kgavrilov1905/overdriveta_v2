"""
Advanced API Routes for Medium Priority Features
Provides endpoints for document deduplication, analytics dashboard, and advanced search.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import json
import io

from document_deduplication import deduplication_service
from analytics_dashboard import analytics_dashboard
from advanced_search import advanced_search_service
from business_intelligence import business_intelligence
from security_middleware import input_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advanced", tags=["advanced"])

# Request models
class DuplicateCheckRequest(BaseModel):
    file_name: str
    file_size: int
    content_hash: Optional[str] = None
    extracted_text: Optional[str] = None

class AdvancedSearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = {}
    search_options: Optional[Dict[str, Any]] = {}

class MergeDocumentsRequest(BaseModel):
    primary_document_id: str
    secondary_document_ids: List[str]
    merge_reason: Optional[str] = "user_initiated"

# Analytics Routes
@router.get("/analytics/dashboard")
async def get_analytics_dashboard(
    time_range: str = Query("24h", regex="^(1h|24h|7d|30d)$", description="Time range for analytics"),
    request: Request = None
):
    """
    Get comprehensive analytics dashboard data.
    
    Args:
        time_range: Time range for analytics (1h, 24h, 7d, 30d)
        
    Returns:
        Complete dashboard data with metrics, charts, and insights
    """
    try:
        logger.info(f"Analytics dashboard requested for time range: {time_range}")
        
        dashboard_data = await analytics_dashboard.get_dashboard_data(time_range)
        
        # Add request metadata
        dashboard_data["request_metadata"] = {
            "requested_at": time.time(),
            "time_range": time_range,
            "user_ip": request.client.host if request and request.client else "unknown"
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Failed to get analytics dashboard: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate analytics dashboard"
        )

@router.get("/analytics/real-time")
async def get_real_time_metrics():
    """Get real-time system metrics."""
    try:
        metrics = analytics_dashboard.real_time_metrics.copy()
        
        # Convert set to list for JSON serialization
        if 'active_users' in metrics:
            metrics['active_users'] = len(metrics['active_users'])
        
        # Convert defaultdict to regular dict
        if 'queries_per_minute' in metrics:
            metrics['queries_per_minute'] = dict(metrics['queries_per_minute'])
        
        return {
            "real_time_metrics": metrics,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Failed to get real-time metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get real-time metrics"
        )

@router.get("/analytics/business-report")
async def generate_business_report(
    period_days: int = Query(30, ge=1, le=365, description="Report period in days"),
    format: str = Query("json", regex="^(json|csv)$", description="Report format")
):
    """
    Generate comprehensive business intelligence report.
    
    Args:
        period_days: Report period in days (1-365)
        format: Report format (json or csv)
        
    Returns:
        Business report with KPIs, insights, and recommendations
    """
    try:
        logger.info(f"Generating business report for {period_days} days")
        
        report = await business_intelligence.generate_business_report(period_days)
        
        if format == "csv":
            # Convert report to CSV format
            csv_content = _convert_report_to_csv(report)
            return StreamingResponse(
                io.StringIO(csv_content),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=business_report_{period_days}d.csv"}
            )
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate business report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate business report"
        )

# Document Deduplication Routes
@router.post("/deduplication/check")
async def check_document_duplicates(request: DuplicateCheckRequest):
    """
    Check for document duplicates before upload.
    
    Args:
        request: Document information for duplicate checking
        
    Returns:
        Duplicate detection results with recommendations
    """
    try:
        logger.info(f"Checking duplicates for: {request.file_name}")
        
        # Validate request
        validation_result = input_validator.validate_file_upload(
            request.file_name, 
            request.file_size
        )
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"File validation failed: {'; '.join(validation_result['errors'])}"
            )
        
        # Check for duplicates
        # Note: This would typically be called with actual file content
        # For this endpoint, we're working with metadata only
        duplicate_check = await deduplication_service.check_for_duplicates(
            file_name=request.file_name,
            file_content=b"",  # Would use actual content in real implementation
            extracted_text=request.extracted_text
        )
        
        return {
            "duplicate_check": duplicate_check,
            "file_info": {
                "filename": request.file_name,
                "size": request.file_size,
                "content_hash": request.content_hash
            },
            "recommendations": duplicate_check.get("recommendations", []),
            "action": duplicate_check.get("action", "proceed")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Duplicate check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Duplicate check failed"
        )

@router.post("/deduplication/merge")
async def merge_duplicate_documents(request: MergeDocumentsRequest):
    """
    Merge similar/duplicate documents into a single entry.
    
    Args:
        request: Document merge request
        
    Returns:
        Merge operation results
    """
    try:
        logger.info(f"Merging documents: {request.primary_document_id} <- {request.secondary_document_ids}")
        
        # Validate document IDs
        if not request.primary_document_id or not request.secondary_document_ids:
            raise HTTPException(
                status_code=400,
                detail="Primary document ID and secondary document IDs are required"
            )
        
        # Perform merge
        merge_result = await deduplication_service.merge_similar_documents(
            primary_doc_id=request.primary_document_id,
            secondary_doc_ids=request.secondary_document_ids
        )
        
        if merge_result.get("success"):
            return {
                "success": True,
                "message": f"Successfully merged {len(request.secondary_document_ids)} documents",
                "merge_result": merge_result,
                "primary_document": request.primary_document_id
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Merge failed: {merge_result.get('error', 'Unknown error')}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document merge failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Document merge failed"
        )

# Advanced Search Routes
@router.post("/search")
async def advanced_search(request: AdvancedSearchRequest):
    """
    Perform advanced search with filtering and faceting.
    
    Args:
        request: Advanced search request with query, filters, and options
        
    Returns:
        Enhanced search results with facets and metadata
    """
    try:
        # Validate and sanitize query
        sanitized_query = input_validator.sanitize_query(request.query)
        
        logger.info(f"Advanced search: '{sanitized_query[:100]}...' with filters: {request.filters}")
        
        # Perform advanced search
        search_results = await advanced_search_service.advanced_search(
            query=sanitized_query,
            filters=request.filters,
            search_options=request.search_options
        )
        
        # Log search for analytics
        analytics_dashboard.log_query({
            "query": sanitized_query,
            "processing_time": search_results.get("search_time", 0),
            "confidence_score": search_results.get("statistics", {}).get("avg_relevance", 0),
            "sources": search_results.get("results", []),
            "user_ip": "unknown"  # Would be extracted from request
        })
        
        return search_results
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Advanced search failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Advanced search failed"
        )

@router.get("/search/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2, description="Partial query for suggestions")
):
    """
    Get search suggestions based on partial query.
    
    Args:
        q: Partial query string
        
    Returns:
        Search suggestions and completions
    """
    try:
        # Sanitize partial query
        sanitized_partial = input_validator.sanitize_query(q)
        
        suggestions = await advanced_search_service.get_search_suggestions(sanitized_partial)
        
        return {
            "partial_query": sanitized_partial,
            "suggestions": suggestions,
            "total_suggestions": len(suggestions)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get search suggestions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get search suggestions"
        )

@router.post("/search/faceted")
async def faceted_search(
    base_query: str = Query(..., description="Base search query"),
    facets: str = Query("{}", description="Selected facets as JSON string")
):
    """
    Perform faceted search with dynamic filtering.
    
    Args:
        base_query: Base search query
        facets: Selected facets as JSON string
        
    Returns:
        Faceted search results with updated facets
    """
    try:
        # Parse facets
        try:
            selected_facets = json.loads(facets)
        except json.JSONDecodeError:
            selected_facets = {}
        
        # Sanitize query
        sanitized_query = input_validator.sanitize_query(base_query)
        
        logger.info(f"Faceted search: '{sanitized_query}' with facets: {selected_facets}")
        
        # Perform faceted search
        search_results = await advanced_search_service.faceted_search(
            base_query=sanitized_query,
            selected_facets=selected_facets
        )
        
        return search_results
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Faceted search failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Faceted search failed"
        )

# Business Intelligence Routes
@router.get("/business/insights")
async def get_business_insights():
    """Get comprehensive business insights and analytics."""
    try:
        insights = await business_intelligence.get_system_analytics()
        
        return {
            "business_insights": insights,
            "generated_at": time.time()
        }
        
    except Exception as e:
        logger.error(f"Failed to get business insights: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate business insights"
        )

@router.get("/business/query-insights")
async def get_query_insights(
    query: str = Query(..., description="Query to analyze")
):
    """Get business intelligence insights for a specific query."""
    try:
        # Sanitize query
        sanitized_query = input_validator.sanitize_query(query)
        
        insights = await business_intelligence.get_query_insights(sanitized_query)
        
        return {
            "query": sanitized_query,
            "insights": insights,
            "generated_at": time.time()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get query insights: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate query insights"
        )

# Batch Processing Routes
@router.post("/batch/process-documents")
async def batch_process_documents(
    background_tasks: BackgroundTasks,
    document_urls: List[str] = Query(..., description="List of document URLs to process")
):
    """
    Process multiple documents in batch.
    
    Args:
        document_urls: List of document URLs to process
        background_tasks: FastAPI background tasks
        
    Returns:
        Batch processing job information
    """
    try:
        if len(document_urls) > 50:  # Limit batch size
            raise HTTPException(
                status_code=400,
                detail="Batch size limited to 50 documents"
            )
        
        # Create batch job
        batch_id = f"batch_{int(time.time())}"
        
        # Start background processing
        background_tasks.add_task(
            _process_document_batch,
            batch_id,
            document_urls
        )
        
        return {
            "batch_id": batch_id,
            "status": "started",
            "document_count": len(document_urls),
            "estimated_completion": time.time() + (len(document_urls) * 30)  # 30 seconds per doc estimate
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Batch processing failed to start"
        )

@router.get("/batch/status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get status of a batch processing job."""
    try:
        # This would integrate with actual batch processing tracking
        # For now, return a placeholder response
        return {
            "batch_id": batch_id,
            "status": "processing",  # started, processing, completed, failed
            "progress": {
                "completed": 0,
                "total": 0,
                "failed": 0
            },
            "estimated_completion": time.time() + 300,  # 5 minutes
            "results": []
        }
        
    except Exception as e:
        logger.error(f"Failed to get batch status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get batch status"
        )

# Helper Functions
def _convert_report_to_csv(report: Dict[str, Any]) -> str:
    """Convert business report to CSV format."""
    csv_lines = ["Section,Metric,Value"]
    
    def flatten_dict(d: dict, prefix: str = ""):
        for key, value in d.items():
            if isinstance(value, dict):
                flatten_dict(value, f"{prefix}{key}.")
            elif isinstance(value, (int, float, str)):
                csv_lines.append(f"{prefix.rstrip('.')},{key},{value}")
    
    flatten_dict(report)
    return "\n".join(csv_lines)

async def _process_document_batch(batch_id: str, document_urls: List[str]):
    """Background task to process document batch."""
    try:
        logger.info(f"Starting batch processing: {batch_id} with {len(document_urls)} documents")
        
        # This would implement actual batch document processing
        # For now, it's a placeholder
        
        for i, url in enumerate(document_urls):
            # Simulate processing
            await asyncio.sleep(1)
            logger.info(f"Batch {batch_id}: Processed document {i+1}/{len(document_urls)}")
        
        logger.info(f"Batch processing completed: {batch_id}")
        
    except Exception as e:
        logger.error(f"Batch processing failed for {batch_id}: {str(e)}")

# Export the router
__all__ = ["router"] 