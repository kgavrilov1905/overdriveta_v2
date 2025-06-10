"""
Data models for Alberta Perspectives RAG API
Defines Pydantic models for API requests/responses and database schemas.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid

# Request Models

class QueryRequest(BaseModel):
    """Request model for user queries."""
    query: str = Field(..., min_length=1, max_length=1000, description="User query text")
    max_results: Optional[int] = Field(5, ge=1, le=20, description="Maximum number of results to return")
    similarity_threshold: Optional[float] = Field(0.75, ge=0.0, le=1.0, description="Minimum similarity threshold")
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()

class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""
    file_name: str = Field(..., description="Name of the file being uploaded")
    content_type: str = Field(..., description="MIME type of the file")
    
# Response Models

class QueryResponse(BaseModel):
    """Response model for user queries."""
    query: str = Field(..., description="Original user query")
    response: str = Field(..., description="Generated response from the RAG system")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Source documents used for the response")
    processing_time: float = Field(..., description="Time taken to process the query in seconds")
    confidence_score: Optional[float] = Field(None, description="Confidence score of the response")

class DocumentProcessingResponse(BaseModel):
    """Response model for document processing."""
    document_id: str = Field(..., description="Unique identifier for the processed document")
    file_name: str = Field(..., description="Name of the processed file")
    chunks_created: int = Field(..., description="Number of text chunks created")
    embeddings_generated: int = Field(..., description="Number of embeddings generated")
    processing_time: float = Field(..., description="Time taken to process the document in seconds")
    status: str = Field(..., description="Processing status")

class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Health status")
    message: str = Field(..., description="Health status message")
    environment: Optional[str] = Field(None, description="Current environment")

# Database Models

class DocumentModel(BaseModel):
    """Database model for documents."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique document identifier")
    file_name: str = Field(..., description="Original file name")
    title: Optional[str] = Field(None, description="Document title extracted from content")
    content_type: str = Field(..., description="MIME type of the document")
    file_size: int = Field(..., description="File size in bytes")
    page_count: Optional[int] = Field(None, description="Number of pages in the document")
    upload_date: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
    processing_status: str = Field("pending", description="Processing status")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional document metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ChunkModel(BaseModel):
    """Database model for text chunks."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document identifier")
    chunk_index: int = Field(..., description="Index of the chunk within the document")
    content: str = Field(..., description="Text content of the chunk")
    page_number: Optional[int] = Field(None, description="Page number where the chunk originates")
    start_char: Optional[int] = Field(None, description="Starting character position in the document")
    end_char: Optional[int] = Field(None, description="Ending character position in the document")
    token_count: Optional[int] = Field(None, description="Number of tokens in the chunk")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional chunk metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class EmbeddingModel(BaseModel):
    """Database model for embeddings."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique embedding identifier")
    chunk_id: str = Field(..., description="Associated chunk identifier")
    document_id: str = Field(..., description="Parent document identifier")
    embedding: List[float] = Field(..., description="Vector embedding")
    model_name: str = Field("text-embedding-004", description="Embedding model used")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Search Models

class SearchResult(BaseModel):
    """Model for search results."""
    chunk_id: str = Field(..., description="Chunk identifier")
    document_id: str = Field(..., description="Document identifier")
    content: str = Field(..., description="Chunk content")
    similarity_score: float = Field(..., description="Similarity score")
    document_name: str = Field(..., description="Source document name")
    page_number: Optional[int] = Field(None, description="Page number")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

# Error Models

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 