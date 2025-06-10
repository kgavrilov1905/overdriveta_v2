"""
RAG service for Alberta Perspectives RAG API
Orchestrates the complete RAG pipeline: query processing, vector search, and response generation.
"""

import logging
import time
from typing import Dict, Any, List, Optional

from models import QueryRequest, QueryResponse, SearchResult
from embedding_service import embedding_service
from llm_service import llm_service
from database import db_manager
from config import settings

logger = logging.getLogger(__name__)

class RAGService:
    """Main RAG service that orchestrates the complete pipeline."""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.db_manager = db_manager
        self.default_similarity_threshold = settings.similarity_threshold
        self.default_max_results = settings.max_results
    
    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """
        Process a user query through the complete RAG pipeline.
        
        Args:
            request: Query request with user input and parameters
            
        Returns:
            Complete query response with generated answer and sources
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing query: '{request.query[:100]}...'")
            
            # Step 1: Generate query embedding
            query_embedding = await self._generate_query_embedding(request.query)
            
            # Step 2: Perform vector similarity search
            search_results = await self._perform_similarity_search(
                query_embedding,
                request.similarity_threshold or self.default_similarity_threshold,
                request.max_results or self.default_max_results
            )
            
            # Step 3: Generate response using LLM
            llm_response = await self._generate_llm_response(request.query, search_results)
            
            # Step 4: Create final response
            processing_time = time.time() - start_time
            
            response = QueryResponse(
                query=request.query,
                response=llm_response["response"],
                sources=llm_response["sources"],
                processing_time=processing_time,
                confidence_score=llm_response.get("confidence_score")
            )
            
            logger.info(f"Query processed successfully in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process query: {str(e)}")
            # Return error response
            processing_time = time.time() - start_time
            return QueryResponse(
                query=request.query,
                response=f"I apologize, but I encountered an error while processing your request: {str(e)}",
                sources=[],
                processing_time=processing_time,
                confidence_score=0.0
            )
    
    async def _generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for the user query."""
        try:
            logger.debug(f"Generating embedding for query: '{query[:50]}...'")
            embedding = self.embedding_service.generate_query_embedding(query)
            logger.debug(f"Query embedding generated: {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {str(e)}")
            raise
    
    async def _perform_similarity_search(self, query_embedding: List[float], threshold: float, max_results: int) -> List[Dict[str, Any]]:
        """Perform vector similarity search in the database."""
        try:
            logger.debug(f"Performing similarity search with threshold {threshold}, max_results {max_results}")
            
            results = await self.db_manager.similarity_search(
                query_embedding=query_embedding,
                limit=max_results,
                threshold=threshold
            )
            
            logger.info(f"Similarity search returned {len(results)} results")
            
            # Log search results for debugging
            for i, result in enumerate(results[:3]):  # Log first 3 results
                logger.debug(f"Result {i+1}: {result.get('document_name', 'Unknown')} "
                           f"(Page {result.get('page_number', 'N/A')}) "
                           f"- Score: {result.get('similarity_score', 0):.3f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to perform similarity search: {str(e)}")
            return []
    
    async def _generate_llm_response(self, query: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate response using the LLM service."""
        try:
            logger.debug(f"Generating LLM response with {len(search_results)} search results")
            
            response = self.llm_service.generate_response(query, search_results)
            
            logger.debug(f"LLM response generated: {len(response.get('response', ''))} characters")
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate LLM response: {str(e)}")
            # Return fallback response
            return {
                "response": "I apologize, but I encountered an error while generating a response. Please try again.",
                "sources": [],
                "confidence_score": 0.0,
                "error": str(e)
            }
    
    async def get_search_results_only(self, query: str, max_results: int = 5, threshold: float = 0.75) -> List[SearchResult]:
        """
        Get only the search results without LLM generation (for debugging/testing).
        
        Args:
            query: User query
            max_results: Maximum number of results
            threshold: Similarity threshold
            
        Returns:
            List of search results
        """
        try:
            # Generate query embedding
            query_embedding = await self._generate_query_embedding(query)
            
            # Perform search
            raw_results = await self._perform_similarity_search(query_embedding, threshold, max_results)
            
            # Convert to SearchResult models
            search_results = []
            for result in raw_results:
                search_result = SearchResult(
                    chunk_id=result.get('chunk_id'),
                    document_id=result.get('document_id'),
                    content=result.get('content', ''),
                    similarity_score=result.get('similarity_score', 0.0),
                    document_name=result.get('document_name', 'Unknown'),
                    page_number=result.get('page_number'),
                    metadata=result.get('metadata', {})
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to get search results: {str(e)}")
            return []
    
    async def test_pipeline(self, test_query: str = "What are the main economic priorities for Alberta?") -> Dict[str, Any]:
        """
        Test the complete RAG pipeline with a sample query.
        
        Args:
            test_query: Query to test with
            
        Returns:
            Test results with performance metrics
        """
        start_time = time.time()
        
        try:
            logger.info(f"Testing RAG pipeline with query: '{test_query}'")
            
            # Test embedding generation
            embedding_start = time.time()
            query_embedding = await self._generate_query_embedding(test_query)
            embedding_time = time.time() - embedding_start
            
            # Test similarity search
            search_start = time.time()
            search_results = await self._perform_similarity_search(query_embedding, 0.75, 5)
            search_time = time.time() - search_start
            
            # Test LLM response generation
            llm_start = time.time()
            llm_response = await self._generate_llm_response(test_query, search_results)
            llm_time = time.time() - llm_start
            
            total_time = time.time() - start_time
            
            test_results = {
                "status": "success",
                "query": test_query,
                "timing": {
                    "embedding_generation": embedding_time,
                    "similarity_search": search_time,
                    "llm_response": llm_time,
                    "total_time": total_time
                },
                "results": {
                    "embedding_dimensions": len(query_embedding),
                    "search_results_count": len(search_results),
                    "response_length": len(llm_response.get("response", "")),
                    "confidence_score": llm_response.get("confidence_score", 0),
                    "sources_count": len(llm_response.get("sources", []))
                },
                "sample_response": llm_response.get("response", "")[:200] + "..." if len(llm_response.get("response", "")) > 200 else llm_response.get("response", "")
            }
            
            logger.info(f"RAG pipeline test completed successfully in {total_time:.2f}s")
            return test_results
            
        except Exception as e:
            logger.error(f"RAG pipeline test failed: {str(e)}")
            return {
                "status": "error",
                "query": test_query,
                "error": str(e),
                "total_time": time.time() - start_time
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get status of all RAG system components.
        
        Returns:
            System status information
        """
        try:
            status = {
                "overall_status": "unknown",
                "components": {},
                "database": {},
                "timestamp": time.time()
            }
            
            # Test embedding service
            try:
                embedding_test = await self.embedding_service.test_connection()
                status["components"]["embedding_service"] = "healthy" if embedding_test else "unhealthy"
            except Exception as e:
                status["components"]["embedding_service"] = f"error: {str(e)}"
            
            # Test LLM service
            try:
                llm_test = await self.llm_service.test_connection()
                status["components"]["llm_service"] = "healthy" if llm_test else "unhealthy"
            except Exception as e:
                status["components"]["llm_service"] = f"error: {str(e)}"
            
            # Test database connection
            try:
                db_test = await self.db_manager.test_connection()
                status["components"]["database"] = "healthy" if db_test else "unhealthy"
                
                # Get database statistics
                documents = await self.db_manager.list_documents(limit=1000)
                status["database"]["documents_count"] = len(documents)
                
                # Count total chunks and embeddings (would need new methods)
                status["database"]["last_updated"] = max([doc.get('created_at', '') for doc in documents]) if documents else None
                
            except Exception as e:
                status["components"]["database"] = f"error: {str(e)}"
                status["database"]["documents_count"] = 0
            
            # Determine overall status
            component_statuses = list(status["components"].values())
            if all(s == "healthy" for s in component_statuses):
                status["overall_status"] = "healthy"
            elif any("error" in str(s) for s in component_statuses):
                status["overall_status"] = "error"
            else:
                status["overall_status"] = "degraded"
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get system status: {str(e)}")
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": time.time()
            }

# Global RAG service instance
rag_service = RAGService() 