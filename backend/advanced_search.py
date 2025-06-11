"""
Advanced Search System for Alberta Perspectives RAG
Provides faceted search, filtering, query expansion, and enhanced search capabilities.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import asyncio

from database import db_manager
from embedding_service import embedding_service
from models import SearchResult

logger = logging.getLogger(__name__)

class AdvancedSearchService:
    """Advanced search with faceted filtering and query enhancement."""
    
    def __init__(self):
        self.query_expansion_terms = {
            # Economic terms
            "economy": ["economic", "gdp", "growth", "development", "prosperity"],
            "business": ["industry", "commercial", "enterprise", "company", "corporation"],
            "employment": ["jobs", "workforce", "hiring", "career", "unemployment"],
            "investment": ["funding", "capital", "finance", "venture", "equity"],
            "policy": ["regulation", "government", "legislation", "law", "governance"],
            "trade": ["export", "import", "commerce", "international", "global"],
            "innovation": ["technology", "research", "development", "startup", "tech"],
            "infrastructure": ["transportation", "utilities", "energy", "construction"]
        }
        
        self.search_filters = {
            "document_type": ["pdf", "pptx", "docx"],
            "date_range": ["last_week", "last_month", "last_quarter", "last_year"],
            "confidence_level": ["high", "medium", "low"],
            "content_category": list(self.query_expansion_terms.keys()),
            "page_range": ["1-10", "11-50", "51-100", "100+"]
        }
    
    async def advanced_search(self, 
                            query: str,
                            filters: Dict[str, Any] = None,
                            search_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform advanced search with filtering and faceting.
        
        Args:
            query: Search query
            filters: Search filters (document_type, date_range, etc.)
            search_options: Search configuration options
            
        Returns:
            Enhanced search results with facets and metadata
        """
        try:
            # Set defaults
            filters = filters or {}
            search_options = search_options or {}
            
            # Parse search options
            max_results = search_options.get('max_results', 20)
            similarity_threshold = search_options.get('similarity_threshold', 0.7)
            enable_query_expansion = search_options.get('query_expansion', True)
            enable_faceting = search_options.get('faceting', True)
            search_mode = search_options.get('mode', 'hybrid')  # semantic, keyword, hybrid
            
            logger.info(f"Advanced search: '{query[:100]}...' with filters: {filters}")
            
            # Expand query if enabled
            expanded_query = await self._expand_query(query) if enable_query_expansion else query
            
            # Perform different search modes
            if search_mode == 'semantic':
                results = await self._semantic_search(expanded_query, max_results, similarity_threshold)
            elif search_mode == 'keyword':
                results = await self._keyword_search(expanded_query, max_results)
            else:  # hybrid
                results = await self._hybrid_search(expanded_query, max_results, similarity_threshold)
            
            # Apply filters
            filtered_results = await self._apply_filters(results, filters)
            
            # Generate facets
            facets = await self._generate_facets(filtered_results) if enable_faceting else {}
            
            # Enhance results with metadata
            enhanced_results = await self._enhance_search_results(filtered_results)
            
            # Calculate search statistics
            search_stats = self._calculate_search_stats(query, enhanced_results, filters)
            
            return {
                "query": query,
                "expanded_query": expanded_query if enable_query_expansion else None,
                "results": enhanced_results,
                "facets": facets,
                "statistics": search_stats,
                "filters_applied": filters,
                "search_options": search_options,
                "total_results": len(enhanced_results),
                "search_time": search_stats.get('search_time', 0)
            }
            
        except Exception as e:
            logger.error(f"Advanced search failed: {str(e)}")
            return {
                "query": query,
                "results": [],
                "error": str(e),
                "total_results": 0
            }
    
    async def get_search_suggestions(self, partial_query: str) -> List[Dict[str, Any]]:
        """Get search suggestions based on partial query."""
        try:
            suggestions = []
            partial_lower = partial_query.lower()
            
            # Query completion suggestions
            completion_suggestions = self._get_query_completions(partial_lower)
            suggestions.extend(completion_suggestions)
            
            # Related term suggestions
            related_suggestions = self._get_related_terms(partial_lower)
            suggestions.extend(related_suggestions)
            
            # Popular query suggestions (would come from analytics)
            popular_suggestions = await self._get_popular_queries(partial_lower)
            suggestions.extend(popular_suggestions)
            
            # Remove duplicates and limit
            unique_suggestions = []
            seen = set()
            for suggestion in suggestions:
                if suggestion['text'] not in seen:
                    unique_suggestions.append(suggestion)
                    seen.add(suggestion['text'])
            
            return unique_suggestions[:10]  # Top 10 suggestions
            
        except Exception as e:
            logger.error(f"Failed to get search suggestions: {str(e)}")
            return []
    
    async def faceted_search(self, base_query: str, selected_facets: Dict[str, List[str]]) -> Dict[str, Any]:
        """Perform faceted search with dynamic filtering."""
        try:
            # Start with base search
            base_results = await self.advanced_search(
                base_query, 
                search_options={'faceting': True, 'max_results': 100}
            )
            
            # Apply facet filters
            filtered_results = base_results['results']
            
            for facet_type, facet_values in selected_facets.items():
                filtered_results = self._filter_by_facet(filtered_results, facet_type, facet_values)
            
            # Regenerate facets for remaining results
            updated_facets = await self._generate_facets(filtered_results)
            
            return {
                "query": base_query,
                "results": filtered_results,
                "facets": updated_facets,
                "selected_facets": selected_facets,
                "total_results": len(filtered_results)
            }
            
        except Exception as e:
            logger.error(f"Faceted search failed: {str(e)}")
            return {"error": str(e), "results": []}
    
    async def _expand_query(self, query: str) -> str:
        """Expand query with related terms."""
        query_words = query.lower().split()
        expanded_terms = []
        
        for word in query_words:
            expanded_terms.append(word)
            
            # Find related terms
            for key, related in self.query_expansion_terms.items():
                if word in related or word == key:
                    # Add related terms (limit to avoid query explosion)
                    expanded_terms.extend(related[:2])
                    break
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in expanded_terms:
            if term not in seen:
                unique_terms.append(term)
                seen.add(term)
        
        return " ".join(unique_terms)
    
    async def _semantic_search(self, query: str, max_results: int, threshold: float) -> List[Dict[str, Any]]:
        """Perform semantic search using embeddings."""
        try:
            # Generate query embedding
            query_embedding = embedding_service.generate_query_embedding(query)
            
            # Perform similarity search
            results = await db_manager.similarity_search(
                query_embedding=query_embedding,
                limit=max_results,
                threshold=threshold
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            return []
    
    async def _keyword_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Perform keyword-based search."""
        try:
            # This would implement full-text search in the database
            # For now, we'll use a simple content matching approach
            
            search_terms = query.lower().split()
            results = await db_manager.text_search(search_terms, max_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {str(e)}")
            return []
    
    async def _hybrid_search(self, query: str, max_results: int, threshold: float) -> List[Dict[str, Any]]:
        """Perform hybrid search combining semantic and keyword search."""
        try:
            # Get semantic results
            semantic_results = await self._semantic_search(query, max_results // 2, threshold)
            
            # Get keyword results
            keyword_results = await self._keyword_search(query, max_results // 2)
            
            # Merge and deduplicate results
            combined_results = self._merge_search_results(semantic_results, keyword_results)
            
            # Re-rank based on combined scores
            ranked_results = self._rerank_hybrid_results(combined_results, query)
            
            return ranked_results[:max_results]
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            return []
    
    async def _apply_filters(self, results: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply search filters to results."""
        if not filters:
            return results
        
        filtered_results = results.copy()
        
        # Document type filter
        if 'document_type' in filters:
            doc_types = filters['document_type']
            if not isinstance(doc_types, list):
                doc_types = [doc_types]
            
            filtered_results = [
                r for r in filtered_results 
                if self._get_document_type(r.get('document_name', '')) in doc_types
            ]
        
        # Date range filter
        if 'date_range' in filters:
            date_range = filters['date_range']
            filtered_results = await self._filter_by_date_range(filtered_results, date_range)
        
        # Confidence level filter
        if 'confidence_level' in filters:
            confidence_level = filters['confidence_level']
            filtered_results = self._filter_by_confidence(filtered_results, confidence_level)
        
        # Page range filter
        if 'page_range' in filters:
            page_range = filters['page_range']
            filtered_results = self._filter_by_page_range(filtered_results, page_range)
        
        # Content category filter
        if 'content_category' in filters:
            categories = filters['content_category']
            filtered_results = self._filter_by_content_category(filtered_results, categories)
        
        return filtered_results
    
    async def _generate_facets(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate facets from search results."""
        facets = {}
        
        if not results:
            return facets
        
        # Document type facets
        doc_types = defaultdict(int)
        for result in results:
            doc_type = self._get_document_type(result.get('document_name', ''))
            doc_types[doc_type] += 1
        
        facets['document_type'] = [
            {"value": doc_type, "count": count, "label": doc_type.upper()}
            for doc_type, count in sorted(doc_types.items())
        ]
        
        # Confidence level facets
        confidence_levels = defaultdict(int)
        for result in results:
            confidence = result.get('similarity_score', 0)
            if confidence >= 0.8:
                level = "high"
            elif confidence >= 0.6:
                level = "medium"
            else:
                level = "low"
            confidence_levels[level] += 1
        
        facets['confidence_level'] = [
            {"value": level, "count": count, "label": level.title()}
            for level, count in sorted(confidence_levels.items())
        ]
        
        # Page range facets
        page_ranges = defaultdict(int)
        for result in results:
            page_num = result.get('page_number', 0)
            if page_num <= 10:
                range_key = "1-10"
            elif page_num <= 50:
                range_key = "11-50"
            elif page_num <= 100:
                range_key = "51-100"
            else:
                range_key = "100+"
            page_ranges[range_key] += 1
        
        facets['page_range'] = [
            {"value": range_key, "count": count, "label": f"Pages {range_key}"}
            for range_key, count in [("1-10", page_ranges["1-10"]), 
                                   ("11-50", page_ranges["11-50"]),
                                   ("51-100", page_ranges["51-100"]), 
                                   ("100+", page_ranges["100+"])]
            if count > 0
        ]
        
        # Content category facets (based on document content analysis)
        categories = await self._analyze_content_categories(results)
        facets['content_category'] = [
            {"value": category, "count": count, "label": category.replace('_', ' ').title()}
            for category, count in sorted(categories.items())
        ]
        
        return facets
    
    async def _enhance_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance search results with additional metadata."""
        enhanced_results = []
        
        for result in results:
            enhanced_result = result.copy()
            
            # Add search metadata
            enhanced_result['search_metadata'] = {
                'relevance_score': result.get('similarity_score', 0),
                'document_type': self._get_document_type(result.get('document_name', '')),
                'content_length': len(result.get('content', '')),
                'word_count': len(result.get('content', '').split()),
                'has_tables': self._detect_tables(result.get('content', '')),
                'has_numbers': self._detect_numbers(result.get('content', '')),
                'reading_time': self._estimate_reading_time(result.get('content', ''))
            }
            
            # Add content preview
            content = result.get('content', '')
            enhanced_result['content_preview'] = content[:300] + "..." if len(content) > 300 else content
            
            # Add highlights (simplified keyword highlighting)
            enhanced_result['highlights'] = self._generate_highlights(content, "")  # Would use actual search query
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def _calculate_search_stats(self, query: str, results: List[Dict[str, Any]], filters: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate search statistics."""
        return {
            "query_length": len(query.split()),
            "total_results": len(results),
            "avg_relevance": sum(r.get('search_metadata', {}).get('relevance_score', 0) for r in results) / max(len(results), 1),
            "filters_applied": len(filters),
            "search_time": 0.0,  # Would be calculated from actual timing
            "result_types": self._count_result_types(results)
        }
    
    def _get_document_type(self, filename: str) -> str:
        """Extract document type from filename."""
        if not filename:
            return "unknown"
        
        extension = filename.lower().split('.')[-1] if '.' in filename else ""
        return extension if extension in ['pdf', 'pptx', 'docx', 'txt'] else "unknown"
    
    def _get_query_completions(self, partial_query: str) -> List[Dict[str, Any]]:
        """Get query completion suggestions."""
        completions = []
        
        # Common Alberta economic queries
        common_queries = [
            "What are the main economic priorities for Alberta?",
            "How is Alberta supporting small businesses?",
            "What are the employment trends in Alberta?",
            "What trade opportunities exist for Alberta?",
            "How is Alberta promoting innovation?",
            "What infrastructure projects are planned?",
            "What are the key policy changes affecting business?",
            "How is Alberta diversifying its economy?"
        ]
        
        for query in common_queries:
            if partial_query in query.lower():
                completions.append({
                    "text": query,
                    "type": "completion",
                    "category": "common_query"
                })
        
        return completions[:5]
    
    def _get_related_terms(self, partial_query: str) -> List[Dict[str, Any]]:
        """Get related term suggestions."""
        related = []
        
        for key, terms in self.query_expansion_terms.items():
            if partial_query in key or any(partial_query in term for term in terms):
                for term in terms[:3]:  # Top 3 related terms
                    related.append({
                        "text": term,
                        "type": "related_term",
                        "category": key
                    })
        
        return related
    
    async def _get_popular_queries(self, partial_query: str) -> List[Dict[str, Any]]:
        """Get popular query suggestions (would integrate with analytics)."""
        # Placeholder - would integrate with actual query analytics
        return []
    
    def _merge_search_results(self, semantic_results: List, keyword_results: List) -> List[Dict[str, Any]]:
        """Merge and deduplicate search results from different methods."""
        merged = {}
        
        # Add semantic results
        for result in semantic_results:
            key = self._get_result_key(result)
            merged[key] = {
                **result,
                'semantic_score': result.get('similarity_score', 0),
                'keyword_score': 0,
                'search_methods': ['semantic']
            }
        
        # Add keyword results
        for result in keyword_results:
            key = self._get_result_key(result)
            if key in merged:
                merged[key]['keyword_score'] = result.get('similarity_score', 0)
                merged[key]['search_methods'].append('keyword')
            else:
                merged[key] = {
                    **result,
                    'semantic_score': 0,
                    'keyword_score': result.get('similarity_score', 0),
                    'search_methods': ['keyword']
                }
        
        return list(merged.values())
    
    def _rerank_hybrid_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Re-rank hybrid search results."""
        for result in results:
            semantic_score = result.get('semantic_score', 0)
            keyword_score = result.get('keyword_score', 0)
            
            # Weighted combination (favor semantic for Alberta economic content)
            combined_score = semantic_score * 0.7 + keyword_score * 0.3
            
            # Boost for multiple search methods
            if len(result.get('search_methods', [])) > 1:
                combined_score *= 1.1
            
            result['similarity_score'] = combined_score
        
        return sorted(results, key=lambda x: x.get('similarity_score', 0), reverse=True)
    
    def _get_result_key(self, result: Dict[str, Any]) -> str:
        """Generate unique key for result deduplication."""
        return f"{result.get('document_id', '')}_{result.get('chunk_id', '')}"
    
    # Additional helper methods for filtering and analysis
    def _detect_tables(self, content: str) -> bool:
        """Detect if content contains tables."""
        table_indicators = ['\t', '|', 'table', 'row', 'column']
        return any(indicator in content.lower() for indicator in table_indicators)
    
    def _detect_numbers(self, content: str) -> bool:
        """Detect if content contains numerical data."""
        return bool(re.search(r'\d+[%$,.]|\d+\.\d+', content))
    
    def _estimate_reading_time(self, content: str) -> int:
        """Estimate reading time in minutes (average 200 words per minute)."""
        word_count = len(content.split())
        return max(1, word_count // 200)
    
    def _generate_highlights(self, content: str, query: str) -> List[str]:
        """Generate content highlights for search terms."""
        # Simplified highlighting - would be more sophisticated in practice
        if not query:
            return []
        
        highlights = []
        words = query.lower().split()
        
        for word in words:
            if word in content.lower():
                # Find context around the word
                start = max(0, content.lower().find(word) - 50)
                end = min(len(content), start + 150)
                highlight = content[start:end]
                highlights.append(f"...{highlight}...")
        
        return highlights[:3]  # Max 3 highlights
    
    def _count_result_types(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count results by type."""
        types = defaultdict(int)
        for result in results:
            doc_type = result.get('search_metadata', {}).get('document_type', 'unknown')
            types[doc_type] += 1
        return dict(types)

# Global advanced search service instance
advanced_search_service = AdvancedSearchService() 