"""
Enhanced LLM service with safety configuration and advanced prompting
Handles AI model initialization, safety settings, and response generation for Alberta economic research.
"""

import logging
import google.generativeai as genai
from typing import Dict, Any, List, Optional
import time
import re

from config import settings
from security_middleware import input_validator, db_connection_manager

logger = logging.getLogger(__name__)

class LLMService:
    """Enhanced LLM service with safety and advanced prompting capabilities."""
    
    def __init__(self):
        self.model = None
        self.safety_settings = None
        self.generation_config = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Gemini model with safety configuration."""
        try:
            if not settings.gemini_api_key:
                logger.error("GEMINI_API_KEY not found in environment variables")
                return
            
            # Validate API key
            if not input_validator.validate_api_key(settings.gemini_api_key):
                logger.error("Invalid Gemini API key format")
                return
            
            # Configure the API
            genai.configure(api_key=settings.gemini_api_key)
            
            # Safety settings for production use
            self.safety_settings = [
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
            
            # Generation configuration for consistent, high-quality responses
            self.generation_config = {
                "temperature": 0.3,      # Lower temperature for more consistent responses
                "top_p": 0.8,           # Focused sampling
                "top_k": 40,            # Limited vocabulary diversity
                "max_output_tokens": 2048,  # Reasonable response length
                "candidate_count": 1     # Single response
            }
            
            # Initialize the model
            self.model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",  # Latest Gemini model
                safety_settings=self.safety_settings,
                generation_config=self.generation_config
            )
            
            logger.info("LLM service initialized successfully with safety settings")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {str(e)}")
            self.model = None
    
    def generate_response(self, query: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate enhanced response using advanced prompting techniques.
        
        Args:
            query: User's question
            search_results: Relevant document chunks from vector search
            
        Returns:
            Response with answer, sources, and confidence metrics
        """
        if not self.model:
            logger.error("LLM model not initialized")
            return self._create_error_response("AI service not available")
        
        try:
            # Sanitize and validate query
            sanitized_query = input_validator.sanitize_query(query)
            
            # Build enhanced context from search results
            context = self._build_enhanced_context(search_results)
            
            # Create advanced prompt
            prompt = self._create_advanced_prompt(sanitized_query, context)
            
            # Generate response with retry logic
            response = self._generate_with_retry(prompt)
            
            if not response:
                return self._create_error_response("Failed to generate response")
            
            # Process and validate response
            processed_response = self._process_response(response, search_results)
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return self._create_error_response(f"Response generation failed: {str(e)}")
    
    def _build_enhanced_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Build rich context from search results with metadata."""
        if not search_results:
            return "No relevant documents found."
        
        context_parts = []
        
        # Group results by document for better organization
        doc_groups = {}
        for result in search_results:
            doc_name = result.get('document_name', 'Unknown Document')
            if doc_name not in doc_groups:
                doc_groups[doc_name] = []
            doc_groups[doc_name].append(result)
        
        # Build context with document organization
        for doc_name, results in doc_groups.items():
            context_parts.append(f"\n=== From {doc_name} ===")
            
            for result in results:
                page_info = f" (Page {result.get('page_number', 'N/A')})" if result.get('page_number') else ""
                similarity = result.get('similarity_score', 0)
                
                context_parts.append(
                    f"\n[Relevance: {similarity:.0%}]{page_info}\n"
                    f"{result.get('content', '').strip()}\n"
                )
        
        return "\n".join(context_parts)
    
    def _create_advanced_prompt(self, query: str, context: str) -> str:
        """Create an advanced prompt with specific instructions for Alberta economic research."""
        
        prompt = f"""You are an expert assistant specializing in Alberta economic research and policy analysis. You have access to official documents from Alberta Perspectives and related economic research.

**CONTEXT DOCUMENTS:**
{context}

**USER QUESTION:**
{query}

**INSTRUCTIONS:**
1. **Accuracy First**: Base your response ONLY on the provided documents. Do not add external information.

2. **Structure**: Organize your response with clear headers and bullet points:
   - Use **bold headers** for main topics (e.g., **Tax Reduction**, **Economic Diversification**)
   - Use bullet points for specific facts and details
   - Keep each bullet point concise (1-2 sentences)

3. **Source Attribution**: Reference specific documents but don't include technical citations in the main text.

4. **Confidence**: Only include information you can directly support from the documents.

5. **Alberta Focus**: Emphasize information specific to Alberta's economic context.

6. **Business Relevance**: Highlight practical implications for Alberta businesses when relevant.

**RESPONSE FORMAT:**
Provide a well-structured response with clear headers and bullet points. Make it easy to scan and understand. Focus on actionable insights and specific data points from the research.

**RESPONSE:**"""

        return prompt
    
    def _generate_with_retry(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Generate response with retry logic and error handling."""
        for attempt in range(max_retries):
            try:
                logger.debug(f"Generating response (attempt {attempt + 1}/{max_retries})")
                
                response = self.model.generate_content(prompt)
                
                # Check if response was blocked by safety filters
                if response.candidates and response.candidates[0].finish_reason == "SAFETY":
                    logger.warning("Response blocked by safety filters")
                    return "I apologize, but I cannot provide a response to this query due to safety considerations. Please try rephrasing your question."
                
                # Extract text from response
                if response.text:
                    logger.debug(f"Response generated successfully: {len(response.text)} characters")
                    return response.text.strip()
                else:
                    logger.warning("Empty response received from model")
                    
            except Exception as e:
                logger.warning(f"Response generation attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Brief delay before retry
                continue
        
        return None
    
    def _process_response(self, response_text: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process and validate the generated response."""
        try:
            # Calculate confidence based on response quality and source coverage
            confidence = self._calculate_confidence(response_text, search_results)
            
            # Extract and format sources
            sources = self._format_sources(search_results)
            
            # Clean up response formatting
            cleaned_response = self._clean_response(response_text)
            
            return {
                "response": cleaned_response,
                "sources": sources,
                "confidence_score": confidence,
                "model": "gemini-2.0-flash-exp",
                "safety_filtered": False
            }
            
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            return self._create_error_response("Response processing failed")
    
    def _calculate_confidence(self, response: str, search_results: List[Dict[str, Any]]) -> float:
        """Calculate confidence score based on response quality and source relevance."""
        try:
            base_confidence = 0.7  # Base confidence
            
            # Factor 1: Response length and detail (reasonable length indicates good coverage)
            length_factor = min(len(response) / 1000, 1.0) * 0.1
            
            # Factor 2: Number of high-quality sources
            high_quality_sources = len([r for r in search_results if r.get('similarity_score', 0) > 0.8])
            source_factor = min(high_quality_sources / 3, 1.0) * 0.1
            
            # Factor 3: Specific data mentions (percentages, numbers, specific terms)
            data_mentions = len(re.findall(r'\d+%|\$[\d,]+|\d+\.\d+', response))
            data_factor = min(data_mentions / 5, 1.0) * 0.1
            
            total_confidence = base_confidence + length_factor + source_factor + data_factor
            
            return min(total_confidence, 0.95)  # Cap at 95%
            
        except Exception as e:
            logger.warning(f"Error calculating confidence: {str(e)}")
            return 0.7  # Default confidence
    
    def _format_sources(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format source information for response."""
        formatted_sources = []
        
        for result in search_results[:5]:  # Limit to top 5 sources
            source = {
                "document_name": result.get('document_name', 'Unknown Document'),
                "similarity_score": result.get('similarity_score', 0),
            }
            
            if result.get('page_number'):
                source["page_number"] = result.get('page_number')
            
            formatted_sources.append(source)
        
        return formatted_sources
    
    def _clean_response(self, response: str) -> str:
        """Clean and format the response text."""
        # Remove any unwanted formatting artifacts
        cleaned = response.strip()
        
        # Ensure proper line breaks
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Remove any remaining citation patterns that might have slipped through
        cleaned = re.sub(r'\[\d+\]', '', cleaned)
        cleaned = re.sub(r'\(\w+_\w+_\w+\.pdf[^)]*\)', '', cleaned)
        
        return cleaned.strip()
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "response": f"I apologize, but I encountered an issue while processing your request. {error_message}",
            "sources": [],
            "confidence_score": 0.0,
            "model": "gemini-2.0-flash-exp",
            "safety_filtered": False,
            "error": True
        }
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get current status of the LLM service."""
        return {
            "model_initialized": self.model is not None,
            "model_name": "gemini-2.0-flash-exp" if self.model else None,
            "safety_settings_enabled": self.safety_settings is not None,
            "api_key_configured": bool(settings.gemini_api_key),
            "api_key_valid": input_validator.validate_api_key(settings.gemini_api_key) if settings.gemini_api_key else False
        }

# Global service instance
llm_service = LLMService() 