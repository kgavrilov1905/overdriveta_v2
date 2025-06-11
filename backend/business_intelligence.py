"""
Business Intelligence module for Alberta Perspectives RAG API
Provides analytics, insights, and business value features for economic research.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import asyncio

from database import db_manager
from config import settings

logger = logging.getLogger(__name__)

class BusinessIntelligence:
    """Business intelligence and analytics for the RAG system."""
    
    def __init__(self):
        self.cache_duration = 300  # 5 minutes cache
        self._cache = {}
        self._cache_timestamps = {}
    
    async def get_system_analytics(self) -> Dict[str, Any]:
        """Get comprehensive system analytics for business insights."""
        cache_key = "system_analytics"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            analytics = {
                "usage_statistics": await self._get_usage_statistics(),
                "content_insights": await self._get_content_insights(),
                "performance_metrics": await self._get_performance_metrics(),
                "user_behavior": await self._get_user_behavior_insights(),
                "business_value": await self._calculate_business_value(),
                "generated_at": datetime.now().isoformat()
            }
            
            # Cache results
            self._cache[cache_key] = analytics
            self._cache_timestamps[cache_key] = time.time()
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to generate system analytics: {str(e)}")
            return {"error": "Analytics generation failed", "timestamp": datetime.now().isoformat()}
    
    async def _get_usage_statistics(self) -> Dict[str, Any]:
        """Get system usage statistics."""
        try:
            # Get query statistics (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            stats = {
                "total_queries_30_days": await self._count_queries_since(thirty_days_ago),
                "total_documents": await self._count_total_documents(),
                "total_document_chunks": await self._count_total_chunks(),
                "active_documents": await self._count_active_documents(),
                "average_queries_per_day": 0,
                "peak_usage_hours": await self._get_peak_usage_hours(),
                "document_utilization": await self._get_document_utilization()
            }
            
            # Calculate average queries per day
            if stats["total_queries_30_days"] > 0:
                stats["average_queries_per_day"] = stats["total_queries_30_days"] / 30
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting usage statistics: {str(e)}")
            return {}
    
    async def _get_content_insights(self) -> Dict[str, Any]:
        """Get insights about content and document quality."""
        try:
            insights = {
                "document_types": await self._analyze_document_types(),
                "content_coverage": await self._analyze_content_coverage(),
                "popular_topics": await self._identify_popular_topics(),
                "document_quality_distribution": await self._analyze_document_quality(),
                "knowledge_gaps": await self._identify_knowledge_gaps()
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating content insights: {str(e)}")
            return {}
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        try:
            metrics = {
                "average_response_time": await self._calculate_avg_response_time(),
                "average_confidence_score": await self._calculate_avg_confidence(),
                "successful_query_rate": await self._calculate_success_rate(),
                "embedding_efficiency": await self._analyze_embedding_performance(),
                "database_performance": await self._analyze_database_performance()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return {}
    
    async def _get_user_behavior_insights(self) -> Dict[str, Any]:
        """Analyze user behavior patterns."""
        try:
            behavior = {
                "common_query_patterns": await self._analyze_query_patterns(),
                "session_duration": await self._analyze_session_duration(),
                "query_complexity": await self._analyze_query_complexity(),
                "user_satisfaction_indicators": await self._analyze_satisfaction(),
                "feature_adoption": await self._analyze_feature_usage()
            }
            
            return behavior
            
        except Exception as e:
            logger.error(f"Error analyzing user behavior: {str(e)}")
            return {}
    
    async def _calculate_business_value(self) -> Dict[str, Any]:
        """Calculate business value metrics."""
        try:
            value_metrics = {
                "time_saved_estimate": await self._estimate_time_saved(),
                "research_efficiency_gain": await self._calculate_efficiency_gain(),
                "knowledge_accessibility_score": await self._calculate_accessibility(),
                "decision_support_quality": await self._assess_decision_support(),
                "cost_per_query": await self._calculate_cost_per_query(),
                "roi_indicators": await self._calculate_roi_indicators()
            }
            
            return value_metrics
            
        except Exception as e:
            logger.error(f"Error calculating business value: {str(e)}")
            return {}
    
    async def get_query_insights(self, query: str) -> Dict[str, Any]:
        """Get insights about a specific query for business intelligence."""
        try:
            insights = {
                "query_category": self._categorize_query(query),
                "complexity_score": self._calculate_query_complexity(query),
                "business_relevance": self._assess_business_relevance(query),
                "expected_document_types": self._predict_relevant_documents(query),
                "similar_queries": await self._find_similar_queries(query),
                "optimization_suggestions": self._suggest_query_optimizations(query)
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating query insights: {str(e)}")
            return {}
    
    def _categorize_query(self, query: str) -> str:
        """Categorize query by business topic."""
        query_lower = query.lower()
        
        # Business categories
        categories = {
            "economic_policy": ["policy", "regulation", "government", "tax", "incentive"],
            "employment": ["jobs", "hiring", "workforce", "employment", "skills", "training"],
            "business_environment": ["business", "industry", "market", "competition", "growth"],
            "infrastructure": ["infrastructure", "transportation", "energy", "utilities"],
            "innovation": ["technology", "innovation", "research", "development", "startup"],
            "finance": ["investment", "funding", "capital", "finance", "budget"],
            "trade": ["trade", "export", "import", "international", "global"],
            "regional": ["region", "local", "community", "rural", "urban"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in query_lower for keyword in keywords):
                return category
        
        return "general"
    
    def _calculate_query_complexity(self, query: str) -> float:
        """Calculate complexity score of a query (0-1)."""
        score = 0.0
        
        # Length factor
        word_count = len(query.split())
        if word_count > 10:
            score += 0.2
        
        # Question type complexity
        if any(word in query.lower() for word in ["how", "why", "what", "where", "when"]):
            score += 0.3
        
        # Multiple topics
        if query.count("and") + query.count("or") > 1:
            score += 0.2
        
        # Technical terms
        technical_terms = ["gdp", "inflation", "employment rate", "investment", "policy", "regulation"]
        if any(term in query.lower() for term in technical_terms):
            score += 0.3
        
        return min(score, 1.0)
    
    def _assess_business_relevance(self, query: str) -> str:
        """Assess business relevance of the query."""
        query_lower = query.lower()
        
        high_relevance_terms = [
            "business", "economy", "investment", "growth", "employment",
            "policy", "regulation", "market", "industry", "development"
        ]
        
        medium_relevance_terms = [
            "statistics", "data", "trends", "analysis", "report",
            "study", "research", "information"
        ]
        
        high_count = sum(1 for term in high_relevance_terms if term in query_lower)
        medium_count = sum(1 for term in medium_relevance_terms if term in query_lower)
        
        if high_count >= 2:
            return "high"
        elif high_count >= 1 or medium_count >= 2:
            return "medium"
        else:
            return "low"
    
    async def generate_business_report(self, period_days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive business report."""
        try:
            report = {
                "report_period": f"{period_days} days",
                "generated_at": datetime.now().isoformat(),
                "executive_summary": await self._generate_executive_summary(period_days),
                "key_metrics": await self._get_key_business_metrics(period_days),
                "content_performance": await self._analyze_content_performance(period_days),
                "user_engagement": await self._analyze_user_engagement(period_days),
                "system_efficiency": await self._analyze_system_efficiency(period_days),
                "recommendations": await self._generate_recommendations(period_days),
                "next_period_projections": await self._project_next_period(period_days)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating business report: {str(e)}")
            return {"error": "Report generation failed", "timestamp": datetime.now().isoformat()}
    
    async def _generate_executive_summary(self, period_days: int) -> Dict[str, Any]:
        """Generate executive summary for business report."""
        try:
            summary = {
                "total_queries": await self._count_queries_last_n_days(period_days),
                "unique_users": await self._count_unique_users(period_days),
                "average_satisfaction": await self._calculate_avg_satisfaction(period_days),
                "key_achievements": [],
                "areas_for_improvement": [],
                "business_impact": "positive"  # Can be enhanced with actual metrics
            }
            
            # Generate key achievements
            if summary["total_queries"] > 100:
                summary["key_achievements"].append("High query volume indicating strong user adoption")
            
            if summary["average_satisfaction"] > 0.8:
                summary["key_achievements"].append("High user satisfaction with responses")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            return {}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        return time.time() - self._cache_timestamps[cache_key] < self.cache_duration
    
    # Placeholder methods for database integration
    async def _count_queries_since(self, since_date: datetime) -> int:
        """Count queries since a specific date."""
        try:
            # This would integrate with actual query logging
            return 0  # Placeholder
        except Exception:
            return 0
    
    async def _count_total_documents(self) -> int:
        """Count total documents in the system."""
        try:
            result = await db_manager.count_documents()
            return result if result else 0
        except Exception:
            return 0
    
    async def _count_total_chunks(self) -> int:
        """Count total document chunks."""
        try:
            result = await db_manager.count_chunks()
            return result if result else 0
        except Exception:
            return 0
    
    async def _count_active_documents(self) -> int:
        """Count documents that have been queried recently."""
        try:
            # This would require query logging integration
            return 0  # Placeholder
        except Exception:
            return 0
    
    # Additional placeholder methods for comprehensive BI
    async def _get_peak_usage_hours(self) -> List[int]:
        """Get peak usage hours."""
        return [9, 10, 11, 14, 15, 16]  # Business hours placeholder
    
    async def _get_document_utilization(self) -> Dict[str, Any]:
        """Get document utilization statistics."""
        return {"most_accessed": [], "least_accessed": [], "average_queries_per_doc": 0}
    
    async def _analyze_document_types(self) -> Dict[str, int]:
        """Analyze distribution of document types."""
        return {"pdf": 0, "pptx": 0, "docx": 0}
    
    async def _analyze_content_coverage(self) -> Dict[str, Any]:
        """Analyze content coverage across topics."""
        return {"coverage_score": 0.8, "topic_distribution": {}}
    
    async def _identify_popular_topics(self) -> List[Dict[str, Any]]:
        """Identify most popular topics."""
        return []
    
    async def _analyze_document_quality(self) -> Dict[str, Any]:
        """Analyze document quality distribution."""
        return {"high_quality": 0, "medium_quality": 0, "low_quality": 0}
    
    async def _identify_knowledge_gaps(self) -> List[str]:
        """Identify gaps in knowledge base."""
        return []
    
    async def _calculate_avg_response_time(self) -> float:
        """Calculate average response time."""
        return 2.5  # Placeholder
    
    async def _calculate_avg_confidence(self) -> float:
        """Calculate average confidence score."""
        return 0.75  # Placeholder
    
    async def _calculate_success_rate(self) -> float:
        """Calculate successful query rate."""
        return 0.95  # Placeholder

# Global business intelligence instance
business_intelligence = BusinessIntelligence() 