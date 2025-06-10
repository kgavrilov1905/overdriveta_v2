"""
LLM service for Alberta Perspectives RAG API
Handles response generation using Google Gemini 2.0 Flash.
"""

import logging
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import time
from config import settings

logger = logging.getLogger(__name__)

class LLMService:
    """Handles response generation using Google Gemini 2.0 Flash."""
    
    def __init__(self):
        self.model_name = "gemini-2.0-flash-exp"
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
        self._configure_genai()
        self._initialize_model()
    
    def _configure_genai(self):
        """Configure Google Generative AI with API key."""
        try:
            genai.configure(api_key=settings.gemini_api_key)
            logger.info("Google Generative AI configured successfully for LLM")
        except Exception as e:
            logger.error(f"Failed to configure Google Generative AI for LLM: {str(e)}")
            raise
    
    def _initialize_model(self):
        """Initialize the Gemini model with configuration."""
        try:
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=0.8,
                top_k=40
            )
            
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
            
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            logger.info(f"Initialized {self.model_name} successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
            raise
    
    def create_rag_prompt(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """
        Create a prompt for RAG response generation.
        
        Args:
            query: User query
            context_chunks: Retrieved context chunks with metadata
            
        Returns:
            Formatted prompt for the LLM
        """
        # Create context section from retrieved chunks
        context_sections = []
        for i, chunk in enumerate(context_chunks, 1):
            source_info = f"Source: {chunk.get('document_name', 'Unknown')}"
            if chunk.get('page_number'):
                source_info += f" (Page {chunk['page_number']})"
            
            context_sections.append(f"""
Context {i}:
{chunk['content']}
{source_info}
Relevance Score: {chunk.get('similarity_score', 0):.3f}
""")
        
        context_text = "\n".join(context_sections)
        
        # Create the complete prompt
        prompt = f"""You are an AI assistant specialized in Alberta economic research and business insights. You help users understand economic data, business trends, and policy information.

RESPONSE FORMAT REQUIREMENTS:
- Use structured responses with clear bullet points when listing multiple items
- Format lists with proper bullet points (•)
- Use clear paragraph breaks between different topics
- Include subheadings when appropriate
- Make responses scannable and easy to read

INFORMATION SOURCES:
1. PRIMARY: Use the provided Alberta Perspectives research context when available
2. FALLBACK: If the context doesn't have sufficient information, supplement with your general knowledge about Alberta's economy, but clearly distinguish between sourced and general information

GUIDELINES:
- Always prioritize information from the provided context first
- When using context, cite sources with document names and page numbers
- If context is insufficient, provide helpful general information about Alberta's economy
- Use bullet points for lists and multiple items
- Structure responses with clear paragraphs
- Be comprehensive but organized

CONTEXT INFORMATION:
{context_text}

USER QUESTION: {query}

RESPONSE:
Please provide a well-structured answer. Use bullet points for lists, clear paragraphs, and cite sources when using the provided context. If the context doesn't cover the topic sufficiently, supplement with general knowledge about Alberta's economy while noting the difference."""

        return prompt
    
    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a response using the RAG pipeline.
        
        Args:
            query: User query
            context_chunks: Retrieved context chunks
            
        Returns:
            Generated response with metadata
        """
        start_time = time.time()
        
        try:
            if not context_chunks:
                return self._generate_fallback_response(query, start_time)
            
            # Create the prompt
            prompt = self.create_rag_prompt(query, context_chunks)
            
            logger.info(f"Generating response for query: '{query[:50]}...' with {len(context_chunks)} context chunks")
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            if not response.text:
                logger.warning("Model generated empty response")
                return self._generate_fallback_response(query, start_time)
            
            # Calculate confidence based on context quality
            confidence_score = self._calculate_confidence(context_chunks, response.text)
            
            # Prepare sources information
            sources = self._format_sources(context_chunks)
            
            processing_time = time.time() - start_time
            
            result = {
                "response": response.text.strip(),
                "sources": sources,
                "confidence_score": confidence_score,
                "processing_time": processing_time,
                "model_used": self.model_name,
                "context_chunks_used": len(context_chunks),
                "prompt_tokens": len(prompt.split()),  # Approximate
                "response_tokens": len(response.text.split()),  # Approximate
            }
            
            logger.info(f"Response generated successfully in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            return self._generate_error_response(query, str(e), start_time)
    
    def _generate_fallback_response(self, query: str, start_time: float) -> Dict[str, Any]:
        """Generate a fallback response using general knowledge when no context is available."""
        
        try:
            # Create a fallback prompt for general knowledge about Alberta
            fallback_prompt = f"""You are an AI assistant with knowledge about Alberta's economy and business environment. 

The user asked: {query}

While I don't have specific Alberta Perspectives research documents to reference for this question, I can provide general information about Alberta's economy and business environment.

RESPONSE FORMAT:
- Use bullet points for lists
- Structure with clear paragraphs
- Be helpful and informative
- Note that this is general knowledge, not from specific research documents

Please provide a helpful response using your general knowledge about Alberta's economy, business climate, and related topics."""

            response = self.model.generate_content(fallback_prompt)
            
            fallback_text = response.text.strip() if response.text else "I apologize, but I couldn't generate a response for your question."
            
            # Add a note about the source
            fallback_text += "\n\n*Note: This response is based on general knowledge about Alberta's economy, as no specific research documents were found for your query.*"
            
        except Exception as e:
            logger.error(f"Failed to generate fallback response: {str(e)}")
            fallback_text = "I apologize, but I encountered an error while trying to answer your question. Please try again or rephrase your query."

        return {
            "response": fallback_text,
            "sources": [],
            "confidence_score": 0.3,  # Higher confidence since we're providing useful info
            "processing_time": time.time() - start_time,
            "model_used": self.model_name,
            "context_chunks_used": 0,
            "is_fallback": True
        }
    
    def _generate_error_response(self, query: str, error: str, start_time: float) -> Dict[str, Any]:
        """Generate an error response."""
        error_text = """I'm sorry, but I encountered an error while processing your request. Please try again in a moment, or rephrase your question.

If the problem persists, please contact support."""

        return {
            "response": error_text,
            "sources": [],
            "confidence_score": 0.0,
            "processing_time": time.time() - start_time,
            "model_used": self.model_name,
            "context_chunks_used": 0,
            "error": error,
            "is_error": True
        }
    
    def _calculate_confidence(self, context_chunks: List[Dict[str, Any]], response_text: str) -> float:
        """
        Calculate confidence score based on context quality and response characteristics.
        
        Args:
            context_chunks: Retrieved context chunks
            response_text: Generated response
            
        Returns:
            Confidence score between 0 and 1
        """
        if not context_chunks:
            return 0.1
        
        # Base confidence from similarity scores
        avg_similarity = sum(chunk.get('similarity_score', 0) for chunk in context_chunks) / len(context_chunks)
        
        # Adjust based on number of sources
        source_factor = min(len(context_chunks) / 3, 1.0)  # Optimal around 3 sources
        
        # Adjust based on response length (longer responses often indicate more comprehensive answers)
        response_length_factor = min(len(response_text.split()) / 100, 1.0)
        
        # Check if response contains citations (indicates use of provided context)
        citation_factor = 1.0 if any(chunk.get('document_name', '') in response_text for chunk in context_chunks) else 0.8
        
        confidence = (avg_similarity * 0.4 + 
                     source_factor * 0.3 + 
                     response_length_factor * 0.2 + 
                     citation_factor * 0.1)
        
        return min(confidence, 1.0)
    
    def _format_sources(self, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format source information for the response."""
        sources = []
        seen_documents = set()
        
        for chunk in context_chunks:
            doc_name = chunk.get('document_name', 'Unknown Document')
            
            # Create unique source entry per document
            source_key = f"{doc_name}_{chunk.get('page_number', 'unknown')}"
            
            if source_key not in seen_documents:
                source_info = {
                    "document_name": doc_name,
                    "page_number": chunk.get('page_number'),
                    "similarity_score": chunk.get('similarity_score', 0),
                    "content_preview": chunk.get('content', '')[:200] + "..." if len(chunk.get('content', '')) > 200 else chunk.get('content', '')
                }
                sources.append(source_info)
                seen_documents.add(source_key)
        
        # Sort by similarity score
        sources.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return sources
    
    async def test_connection(self) -> bool:
        """
        Test the connection to Gemini 2.0 Flash.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            test_prompt = "Hello, this is a test message. Please respond with 'Test successful'."
            response = self.model.generate_content(test_prompt)
            
            if response.text and "test" in response.text.lower():
                logger.info("LLM service connection test successful")
                return True
            else:
                logger.error("LLM service connection test failed: Unexpected response")
                return False
                
        except Exception as e:
            logger.error(f"LLM service connection test failed: {str(e)}")
            return False

# Global LLM service instance
llm_service = LLMService() 