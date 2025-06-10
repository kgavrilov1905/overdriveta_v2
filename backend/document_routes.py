"""
Document processing routes for Alberta Perspectives RAG API
Handles document upload, processing, and management endpoints.
"""

import logging
import os
import tempfile
import time
from typing import Dict, Any, List
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from models import DocumentProcessingResponse, ErrorResponse
from document_processor import DocumentProcessor
from embedding_service import embedding_service
from database import db_manager
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Initialize document processor
document_processor = DocumentProcessor(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap
)

@router.post("/upload", response_model=DocumentProcessingResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload and process a document.
    
    Args:
        file: PDF file to upload and process
        background_tasks: FastAPI background tasks for async processing
        
    Returns:
        Document processing response with status
    """
    start_time = time.time()
    
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.pptx', '.ppt']
        file_extension = '.' + file.filename.lower().split('.')[-1]
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF and PowerPoint files are supported. Allowed extensions: {', '.join(allowed_extensions)}"
            )
        
        # Validate file size (max 50MB)
        if hasattr(file, 'size') and file.size > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File size must be less than 50MB"
            )
        
        logger.info(f"Starting document upload: {file.filename}")
        
        # Save file temporarily
        temp_file_path = None
        try:
            # Use appropriate file extension for temp file
            file_suffix = file_extension if file_extension in ['.pdf', '.pptx', '.ppt'] else '.tmp'
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
                file_size = len(content)
            
            # Create document record in database
            document_data = {
                "file_name": file.filename,
                "content_type": file.content_type or "application/pdf",
                "file_size": file_size,
                "processing_status": "uploaded"
            }
            
            document_id = await db_manager.insert_document(document_data)
            
            # Start background processing
            background_tasks.add_task(
                process_document_background,
                document_id,
                temp_file_path,
                file.filename
            )
            
            processing_time = time.time() - start_time
            
            response = DocumentProcessingResponse(
                document_id=document_id,
                file_name=file.filename,
                chunks_created=0,  # Will be updated after processing
                embeddings_generated=0,  # Will be updated after processing
                processing_time=processing_time,
                status="processing"
            )
            
            logger.info(f"Document upload completed: {document_id}")
            return response
            
        except Exception as e:
            # Clean up temp file on error
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Document upload failed: {str(e)}"
        )

async def process_document_background(document_id: str, file_path: str, file_name: str):
    """
    Background task to process document: extract text, create chunks, and generate embeddings.
    
    Args:
        document_id: Database document ID
        file_path: Path to the temporary file
        file_name: Original filename
    """
    try:
        logger.info(f"Starting background processing for document {document_id}")
        
        # Update status to processing
        await db_manager.update_document_status(document_id, "processing")
        
        # Process document
        processed_data = document_processor.process_document(file_path, file_name)
        
        # Update document metadata
        document_update = {
            "title": processed_data["document"]["title"],
            "page_count": processed_data["document"]["page_count"],
            "metadata": processed_data["document"]["metadata"]
        }
        
        # Insert chunks into database
        chunks_data = []
        for chunk in processed_data["chunks"]:
            chunk_data = {
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "page_number": chunk.get("page_number"),
                "token_count": chunk.get("word_count"),  # Approximate
                "metadata": {
                    "char_count": chunk["char_count"],
                    "word_count": chunk["word_count"],
                    "sentence_count": chunk.get("sentence_count", 0),
                    "content_hash": chunk.get("content_hash")
                }
            }
            chunks_data.append(chunk_data)
        
        chunk_ids = await db_manager.insert_chunks(chunks_data)
        logger.info(f"Inserted {len(chunk_ids)} chunks for document {document_id}")
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(processed_data['chunks'])} chunks")
        processed_chunks = embedding_service.process_chunks_for_embedding(processed_data["chunks"])
        
        # Insert embeddings into database
        embeddings_data = []
        for i, (chunk_id, processed_chunk) in enumerate(zip(chunk_ids, processed_chunks)):
            embedding_data = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "embedding": processed_chunk["embedding"],
                "model_name": processed_chunk["embedding_model"]
            }
            embeddings_data.append(embedding_data)
        
        embedding_ids = await db_manager.insert_embeddings(embeddings_data)
        logger.info(f"Inserted {len(embedding_ids)} embeddings for document {document_id}")
        
        # Update document status to completed
        await db_manager.update_document_status(document_id, "completed")
        
        logger.info(f"Document processing completed successfully: {document_id}")
        
    except Exception as e:
        logger.error(f"Background processing failed for document {document_id}: {str(e)}")
        await db_manager.update_document_status(document_id, "failed")
        
    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")

@router.get("/{document_id}")
async def get_document(document_id: str):
    """
    Get document details and processing status.
    
    Args:
        document_id: Document ID
        
    Returns:
        Document information and status
    """
    try:
        document = await db_manager.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
        
        # Get chunk count
        chunks = await db_manager.get_chunks_by_document(document_id)
        
        response = {
            **document,
            "chunks_count": len(chunks)
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document: {str(e)}"
        )

@router.get("/")
async def list_documents():
    """
    List all documents with their processing status.
    
    Returns:
        List of documents
    """
    try:
        # This would be implemented with pagination in a production system
        documents = await db_manager.list_documents()  # We'll implement this method
        return {"documents": documents}
        
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(e)}"
        )

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and all associated data.
    
    Args:
        document_id: Document ID to delete
        
    Returns:
        Success message
    """
    try:
        document = await db_manager.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
        
        # Delete document (cascading deletes will handle chunks and embeddings)
        await db_manager.delete_document(document_id)
        
        return {"message": f"Document {document_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )

@router.post("/process-samples")
async def process_sample_documents(background_tasks: BackgroundTasks):
    """
    Process all sample documents from the samples directory.
    
    Returns:
        List of processing jobs started
    """
    try:
        samples_dir = "../samples"
        if not os.path.exists(samples_dir):
            raise HTTPException(
                status_code=404,
                detail="Samples directory not found"
            )
        
        pdf_files = [f for f in os.listdir(samples_dir) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            raise HTTPException(
                status_code=404,
                detail="No PDF files found in samples directory"
            )
        
        processing_jobs = []
        
        for pdf_file in pdf_files:
            file_path = os.path.join(samples_dir, pdf_file)
            file_size = os.path.getsize(file_path)
            
            # Create document record
            document_data = {
                "file_name": pdf_file,
                "content_type": "application/pdf",
                "file_size": file_size,
                "processing_status": "uploaded"
            }
            
            document_id = await db_manager.insert_document(document_data)
            
            # Start background processing
            background_tasks.add_task(
                process_sample_document_background,
                document_id,
                file_path,
                pdf_file
            )
            
            processing_jobs.append({
                "document_id": document_id,
                "file_name": pdf_file,
                "status": "processing"
            })
        
        return {
            "message": f"Started processing {len(processing_jobs)} sample documents",
            "jobs": processing_jobs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process sample documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process sample documents: {str(e)}"
        )

async def process_sample_document_background(document_id: str, file_path: str, file_name: str):
    """
    Background task to process sample documents (similar to upload processing but without temp file cleanup).
    """
    try:
        logger.info(f"Starting sample document processing for {document_id}")
        
        # Update status to processing
        await db_manager.update_document_status(document_id, "processing")
        
        # Process document
        processed_data = document_processor.process_document(file_path, file_name)
        
        # Insert chunks into database
        chunks_data = []
        for chunk in processed_data["chunks"]:
            chunk_data = {
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "page_number": chunk.get("page_number"),
                "token_count": chunk.get("word_count"),
                "metadata": {
                    "char_count": chunk["char_count"],
                    "word_count": chunk["word_count"],
                    "sentence_count": chunk.get("sentence_count", 0),
                    "content_hash": chunk.get("content_hash")
                }
            }
            chunks_data.append(chunk_data)
        
        chunk_ids = await db_manager.insert_chunks(chunks_data)
        
        # Generate embeddings
        processed_chunks = embedding_service.process_chunks_for_embedding(processed_data["chunks"])
        
        # Insert embeddings into database
        embeddings_data = []
        for i, (chunk_id, processed_chunk) in enumerate(zip(chunk_ids, processed_chunks)):
            embedding_data = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "embedding": processed_chunk["embedding"],
                "model_name": processed_chunk["embedding_model"]
            }
            embeddings_data.append(embedding_data)
        
        await db_manager.insert_embeddings(embeddings_data)
        
        # Update document status to completed
        await db_manager.update_document_status(document_id, "completed")
        
        logger.info(f"Sample document processing completed: {document_id}")
        
    except Exception as e:
        logger.error(f"Sample document processing failed for {document_id}: {str(e)}")
        await db_manager.update_document_status(document_id, "failed") 