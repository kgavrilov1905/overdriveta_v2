"""
Embedding service for Alberta Perspectives RAG API
Handles embedding generation using Google's text-embedding-004 model.
"""

import logging
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import asyncio
import time
from config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Handles embedding generation using Google's text-embedding-004."""
    
    def __init__(self):
        self.model_name = "text-embedding-004"
        self.embedding_dimension = 768
        self._configure_genai()
    
    def _configure_genai(self):
        """Configure Google Generative AI with API key."""
        try:
            genai.configure(api_key=settings.gemini_api_key)
            logger.info("Google Generative AI configured successfully")
        except Exception as e:
            logger.error(f"Failed to configure Google Generative AI: {str(e)}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of float values representing the embedding
        """
        try:
            if not text.strip():
                logger.warning("Empty text provided for embedding")
                return [0.0] * self.embedding_dimension
            
            # Generate embedding using Google's text-embedding-004
            result = genai.embed_content(
                model=f"models/{self.model_name}",
                content=text,
                task_type="retrieval_document"  # Optimized for RAG retrieval
            )
            
            embedding = result['embedding']
            
            # Validate embedding dimensions
            if len(embedding) != self.embedding_dimension:
                raise ValueError(f"Expected {self.embedding_dimension} dimensions, got {len(embedding)}")
            
            logger.debug(f"Generated embedding for text of length {len(text)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embeddings
        """
        if not texts:
            return []
        
        embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        logger.info(f"Generating embeddings for {len(texts)} texts in {total_batches} batches")
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_number = (i // batch_size) + 1
            
            logger.info(f"Processing batch {batch_number}/{total_batches} ({len(batch)} texts)")
            
            try:
                batch_embeddings = []
                for text in batch:
                    embedding = self.generate_embedding(text)
                    batch_embeddings.append(embedding)
                    
                    # Small delay to avoid rate limiting
                    time.sleep(0.1)
                
                embeddings.extend(batch_embeddings)
                logger.info(f"Completed batch {batch_number}/{total_batches}")
                
                # Longer delay between batches
                if batch_number < total_batches:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Failed to process batch {batch_number}: {str(e)}")
                # Add placeholder embeddings for failed batch
                batch_embeddings = [[0.0] * self.embedding_dimension] * len(batch)
                embeddings.extend(batch_embeddings)
        
        logger.info(f"Generated {len(embeddings)} embeddings successfully")
        return embeddings
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            List of float values representing the query embedding
        """
        try:
            if not query.strip():
                raise ValueError("Query cannot be empty")
            
            # Generate embedding optimized for query
            result = genai.embed_content(
                model=f"models/{self.model_name}",
                content=query,
                task_type="retrieval_query"  # Optimized for query retrieval
            )
            
            embedding = result['embedding']
            
            # Validate embedding dimensions
            if len(embedding) != self.embedding_dimension:
                raise ValueError(f"Expected {self.embedding_dimension} dimensions, got {len(embedding)}")
            
            logger.info(f"Generated query embedding for: '{query[:50]}...'")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {str(e)}")
            raise
    
    def process_chunks_for_embedding(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process document chunks and generate embeddings.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List of chunk dictionaries with embeddings
        """
        if not chunks:
            return []
        
        logger.info(f"Processing {len(chunks)} chunks for embedding generation")
        
        try:
            # Extract text content from chunks
            texts = [chunk["content"] for chunk in chunks]
            
            # Generate embeddings
            embeddings = self.generate_embeddings_batch(texts)
            
            # Combine chunks with embeddings
            processed_chunks = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                processed_chunk = {
                    **chunk,
                    "embedding": embedding,
                    "embedding_model": self.model_name,
                    "embedding_dimension": len(embedding)
                }
                processed_chunks.append(processed_chunk)
            
            logger.info(f"Successfully processed {len(processed_chunks)} chunks with embeddings")
            return processed_chunks
            
        except Exception as e:
            logger.error(f"Failed to process chunks for embedding: {str(e)}")
            raise
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """
        Validate that an embedding has the correct format and dimensions.
        
        Args:
            embedding: Embedding to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(embedding, list):
                return False
            
            if len(embedding) != self.embedding_dimension:
                return False
            
            if not all(isinstance(x, (int, float)) for x in embedding):
                return False
            
            # Check for reasonable value ranges (embeddings are typically normalized)
            if any(abs(x) > 10 for x in embedding):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def test_connection(self) -> bool:
        """
        Test the connection to Google's embedding service.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            test_text = "This is a test sentence for embedding generation."
            embedding = self.generate_embedding(test_text)
            
            if self.validate_embedding(embedding):
                logger.info("Embedding service connection test successful")
                return True
            else:
                logger.error("Embedding service connection test failed: Invalid embedding format")
                return False
                
        except Exception as e:
            logger.error(f"Embedding service connection test failed: {str(e)}")
            return False

# Global embedding service instance
embedding_service = EmbeddingService() 