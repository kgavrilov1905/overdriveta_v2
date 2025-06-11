"""
Real-time Analytics Dashboard for Alberta Perspectives RAG
Provides comprehensive business intelligence, query tracking, and performance monitoring.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass, asdict

from database import db_manager

logger = logging.getLogger(__name__)

@dataclass
class QueryAnalytics:
    """Query analytics data structure."""
    query_id: str
    query_text: str
    timestamp: float
    response_time: float
    confidence_score: float
    sources_count: int
    user_ip: str
    query_category: str
    query_complexity: float
    success: bool
    error_message: Optional[str] = None

@dataclass
class DocumentAnalytics:
    """Document analytics data structure."""
    document_id: str
    filename: str
    upload_date: float
    file_size: int
    chunk_count: int
    query_count: int
    last_accessed: Optional[float] = None
    quality_score: float = 0.0

class AnalyticsDashboard:
    """Real-time analytics dashboard with business intelligence."""
    
    def __init__(self):
        self.query_log: List[QueryAnalytics] = []
        self.document_stats: Dict[str, DocumentAnalytics] = {}
        self.real_time_metrics = {
            "active_users": set(),
            "queries_per_minute": defaultdict(int),
            "error_rate": 0.0,
            "avg_response_time": 0.0,
            "last_updated": time.time()
        }
        self.max_log_size = 10000  # Keep last 10k queries in memory
        
    def log_query(self, query_data: Dict[str, Any]):
        """Log a query for analytics tracking."""
        try:
            analytics = QueryAnalytics(
                query_id=query_data.get('query_id', f"q_{int(time.time())}_{len(self.query_log)}"),
                query_text=query_data.get('query', '')[:200],  # Truncate long queries
                timestamp=time.time(),
                response_time=query_data.get('processing_time', 0.0),
                confidence_score=query_data.get('confidence_score', 0.0),
                sources_count=len(query_data.get('sources', [])),
                user_ip=query_data.get('user_ip', 'unknown'),
                query_category=self._categorize_query(query_data.get('query', '')),
                query_complexity=self._calculate_query_complexity(query_data.get('query', '')),
                success=not query_data.get('error', False),
                error_message=query_data.get('error_message')
            )
            
            self.query_log.append(analytics)
            
            # Maintain log size
            if len(self.query_log) > self.max_log_size:
                self.query_log = self.query_log[-self.max_log_size:]
            
            # Update real-time metrics
            self._update_real_time_metrics(analytics)
            
            logger.debug(f"Logged query analytics: {analytics.query_id}")
            
        except Exception as e:
            logger.error(f"Failed to log query analytics: {str(e)}")
    
    def log_document_access(self, document_id: str, query_data: Dict[str, Any]):
        """Log document access for usage analytics."""
        try:
            if document_id in self.document_stats:
                self.document_stats[document_id].query_count += 1
                self.document_stats[document_id].last_accessed = time.time()
            
        except Exception as e:
            logger.error(f"Failed to log document access: {str(e)}")
    
    async def get_dashboard_data(self, time_range: str = "24h") -> Dict[str, Any]:
        """Get comprehensive dashboard data for the specified time range."""
        try:
            # Calculate time range
            end_time = time.time()
            if time_range == "1h":
                start_time = end_time - 3600
            elif time_range == "24h":
                start_time = end_time - 86400
            elif time_range == "7d":
                start_time = end_time - 604800
            elif time_range == "30d":
                start_time = end_time - 2592000
            else:
                start_time = end_time - 86400  # Default to 24h
            
            # Filter queries by time range
            filtered_queries = [q for q in self.query_log if q.timestamp >= start_time]
            
            dashboard_data = {
                "time_range": time_range,
                "generated_at": datetime.now().isoformat(),
                "overview": await self._get_overview_metrics(filtered_queries),
                "query_analytics": await self._get_query_analytics(filtered_queries),
                "performance_metrics": await self._get_performance_metrics(filtered_queries),
                "user_behavior": await self._get_user_behavior(filtered_queries),
                "content_insights": await self._get_content_insights(filtered_queries),
                "business_metrics": await self._get_business_metrics(filtered_queries),
                "real_time": self.real_time_metrics.copy(),
                "alerts": await self._get_system_alerts(filtered_queries)
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to generate dashboard data: {str(e)}")
            return {"error": "Dashboard generation failed", "timestamp": datetime.now().isoformat()}
    
    async def _get_overview_metrics(self, queries: List[QueryAnalytics]) -> Dict[str, Any]:
        """Get high-level overview metrics."""
        if not queries:
            return {
                "total_queries": 0,
                "unique_users": 0,
                "avg_response_time": 0.0,
                "success_rate": 0.0,
                "avg_confidence": 0.0
            }
        
        successful_queries = [q for q in queries if q.success]
        unique_users = len(set(q.user_ip for q in queries))
        
        return {
            "total_queries": len(queries),
            "unique_users": unique_users,
            "avg_response_time": sum(q.response_time for q in queries) / len(queries),
            "success_rate": len(successful_queries) / len(queries),
            "avg_confidence": sum(q.confidence_score for q in successful_queries) / max(len(successful_queries), 1),
            "queries_per_user": len(queries) / max(unique_users, 1)
        }
    
    async def _get_query_analytics(self, queries: List[QueryAnalytics]) -> Dict[str, Any]:
        """Get detailed query analytics."""
        if not queries:
            return {}
        
        # Query categories
        categories = Counter(q.query_category for q in queries)
        
        # Query complexity distribution
        complexity_ranges = {
            "simple": len([q for q in queries if q.query_complexity < 0.3]),
            "moderate": len([q for q in queries if 0.3 <= q.query_complexity < 0.7]),
            "complex": len([q for q in queries if q.query_complexity >= 0.7])
        }
        
        # Hourly distribution
        hourly_distribution = defaultdict(int)
        for query in queries:
            hour = datetime.fromtimestamp(query.timestamp).hour
            hourly_distribution[hour] += 1
        
        # Top queries by confidence
        top_queries = sorted(
            [q for q in queries if q.success],
            key=lambda x: x.confidence_score,
            reverse=True
        )[:10]
        
        # Most common query patterns
        query_patterns = self._analyze_query_patterns([q.query_text for q in queries])
        
        return {
            "categories": dict(categories),
            "complexity_distribution": complexity_ranges,
            "hourly_distribution": dict(hourly_distribution),
            "top_performing_queries": [
                {
                    "query": q.query_text[:100],
                    "confidence": q.confidence_score,
                    "response_time": q.response_time,
                    "sources": q.sources_count
                }
                for q in top_queries
            ],
            "common_patterns": query_patterns,
            "total_unique_queries": len(set(q.query_text.lower() for q in queries))
        }
    
    async def _get_performance_metrics(self, queries: List[QueryAnalytics]) -> Dict[str, Any]:
        """Get performance metrics."""
        if not queries:
            return {}
        
        response_times = [q.response_time for q in queries]
        confidence_scores = [q.confidence_score for q in queries if q.success]
        
        # Response time percentiles
        response_times.sort()
        n = len(response_times)
        
        percentiles = {
            "p50": response_times[n//2] if n > 0 else 0,
            "p90": response_times[int(n*0.9)] if n > 0 else 0,
            "p95": response_times[int(n*0.95)] if n > 0 else 0,
            "p99": response_times[int(n*0.99)] if n > 0 else 0
        }
        
        # Error analysis
        errors = [q for q in queries if not q.success]
        error_types = Counter(q.error_message for q in errors if q.error_message)
        
        return {
            "response_time_stats": {
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "avg": sum(response_times) / len(response_times) if response_times else 0,
                "percentiles": percentiles
            },
            "confidence_stats": {
                "min": min(confidence_scores) if confidence_scores else 0,
                "max": max(confidence_scores) if confidence_scores else 0,
                "avg": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            },
            "error_analysis": {
                "error_rate": len(errors) / len(queries),
                "error_types": dict(error_types),
                "total_errors": len(errors)
            },
            "sources_stats": {
                "avg_sources_per_query": sum(q.sources_count for q in queries) / len(queries),
                "max_sources": max(q.sources_count for q in queries) if queries else 0
            }
        }
    
    async def _get_user_behavior(self, queries: List[QueryAnalytics]) -> Dict[str, Any]:
        """Analyze user behavior patterns."""
        if not queries:
            return {}
        
        # User query patterns
        user_queries = defaultdict(list)
        for query in queries:
            user_queries[query.user_ip].append(query)
        
        # Session analysis
        sessions = []
        for user_ip, user_query_list in user_queries.items():
            user_query_list.sort(key=lambda x: x.timestamp)
            
            session_data = {
                "user_ip": user_ip,
                "query_count": len(user_query_list),
                "session_duration": user_query_list[-1].timestamp - user_query_list[0].timestamp if len(user_query_list) > 1 else 0,
                "avg_response_time": sum(q.response_time for q in user_query_list) / len(user_query_list),
                "success_rate": len([q for q in user_query_list if q.success]) / len(user_query_list)
            }
            sessions.append(session_data)
        
        # User engagement levels
        engagement_levels = {
            "single_query": len([s for s in sessions if s["query_count"] == 1]),
            "light_usage": len([s for s in sessions if 2 <= s["query_count"] <= 5]),
            "moderate_usage": len([s for s in sessions if 6 <= s["query_count"] <= 15]),
            "heavy_usage": len([s for s in sessions if s["query_count"] > 15])
        }
        
        return {
            "total_sessions": len(sessions),
            "engagement_levels": engagement_levels,
            "avg_queries_per_session": sum(s["query_count"] for s in sessions) / len(sessions) if sessions else 0,
            "avg_session_duration": sum(s["session_duration"] for s in sessions) / len(sessions) if sessions else 0,
            "power_users": [s for s in sessions if s["query_count"] > 10][:5]  # Top 5 power users
        }
    
    async def _get_content_insights(self, queries: List[QueryAnalytics]) -> Dict[str, Any]:
        """Get insights about content usage and effectiveness."""
        try:
            # Most accessed documents (would need to track document access)
            document_access = await self._get_document_access_stats()
            
            # Query topic analysis
            topic_distribution = Counter(q.query_category for q in queries)
            
            # Content gaps (queries with low confidence)
            low_confidence_queries = [q for q in queries if q.confidence_score < 0.5 and q.success]
            content_gaps = Counter(q.query_category for q in low_confidence_queries)
            
            return {
                "document_access": document_access,
                "topic_distribution": dict(topic_distribution),
                "content_gaps": dict(content_gaps),
                "low_confidence_rate": len(low_confidence_queries) / len(queries) if queries else 0,
                "improvement_opportunities": self._identify_content_improvements(queries)
            }
            
        except Exception as e:
            logger.warning(f"Error getting content insights: {str(e)}")
            return {}
    
    async def _get_business_metrics(self, queries: List[QueryAnalytics]) -> Dict[str, Any]:
        """Get business value metrics."""
        if not queries:
            return {}
        
        # Time savings estimation (assuming 30 minutes per manual research query)
        time_saved_hours = len([q for q in queries if q.success]) * 0.5
        
        # Research efficiency
        successful_queries = [q for q in queries if q.success]
        high_confidence_queries = [q for q in successful_queries if q.confidence_score > 0.7]
        
        # Cost analysis (rough estimates)
        estimated_cost_per_query = 0.05  # $0.05 per query estimate
        total_cost = len(queries) * estimated_cost_per_query
        cost_per_successful_query = total_cost / max(len(successful_queries), 1)
        
        return {
            "time_savings": {
                "total_hours_saved": time_saved_hours,
                "value_at_50_per_hour": time_saved_hours * 50,
                "queries_processed": len(successful_queries)
            },
            "research_efficiency": {
                "success_rate": len(successful_queries) / len(queries),
                "high_confidence_rate": len(high_confidence_queries) / max(len(successful_queries), 1),
                "avg_sources_per_query": sum(q.sources_count for q in successful_queries) / max(len(successful_queries), 1)
            },
            "cost_analysis": {
                "total_estimated_cost": total_cost,
                "cost_per_query": estimated_cost_per_query,
                "cost_per_successful_query": cost_per_successful_query,
                "roi_estimate": (time_saved_hours * 50) / max(total_cost, 0.01)
            }
        }
    
    async def _get_system_alerts(self, queries: List[QueryAnalytics]) -> List[Dict[str, Any]]:
        """Get system alerts and recommendations."""
        alerts = []
        
        if not queries:
            return alerts
        
        # High error rate alert
        error_rate = len([q for q in queries if not q.success]) / len(queries)
        if error_rate > 0.1:  # >10% error rate
            alerts.append({
                "type": "warning",
                "title": "High Error Rate",
                "message": f"Error rate is {error_rate:.1%}, above the 10% threshold",
                "severity": "high" if error_rate > 0.2 else "medium"
            })
        
        # Slow response time alert
        avg_response_time = sum(q.response_time for q in queries) / len(queries)
        if avg_response_time > 5.0:  # >5 seconds
            alerts.append({
                "type": "warning",
                "title": "Slow Response Times",
                "message": f"Average response time is {avg_response_time:.1f}s, above the 5s threshold",
                "severity": "medium"
            })
        
        # Low confidence alert
        successful_queries = [q for q in queries if q.success]
        if successful_queries:
            avg_confidence = sum(q.confidence_score for q in successful_queries) / len(successful_queries)
            if avg_confidence < 0.6:  # <60% confidence
                alerts.append({
                    "type": "info",
                    "title": "Low Confidence Scores",
                    "message": f"Average confidence is {avg_confidence:.1%}, consider content review",
                    "severity": "low"
                })
        
        # Usage spike alert
        if len(queries) > 1000:  # High query volume
            alerts.append({
                "type": "info",
                "title": "High Usage Volume",
                "message": f"Processed {len(queries)} queries in selected time period",
                "severity": "low"
            })
        
        return alerts
    
    def _categorize_query(self, query: str) -> str:
        """Categorize query by business topic."""
        query_lower = query.lower()
        
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
        
        word_count = len(query.split())
        if word_count > 10:
            score += 0.3
        
        if any(word in query.lower() for word in ["how", "why", "what", "where", "when"]):
            score += 0.2
        
        if query.count("and") + query.count("or") > 1:
            score += 0.3
        
        technical_terms = ["gdp", "inflation", "employment rate", "investment", "policy"]
        if any(term in query.lower() for term in technical_terms):
            score += 0.2
        
        return min(score, 1.0)
    
    def _update_real_time_metrics(self, analytics: QueryAnalytics):
        """Update real-time metrics."""
        current_minute = int(time.time() // 60)
        
        # Update active users (last 5 minutes)
        self.real_time_metrics["active_users"].add(analytics.user_ip)
        
        # Clean old active users (older than 5 minutes)
        cutoff_time = time.time() - 300
        recent_queries = [q for q in self.query_log if q.timestamp > cutoff_time]
        self.real_time_metrics["active_users"] = set(q.user_ip for q in recent_queries)
        
        # Update queries per minute
        self.real_time_metrics["queries_per_minute"][current_minute] += 1
        
        # Clean old minute data (keep last 60 minutes)
        cutoff_minute = current_minute - 60
        for minute in list(self.real_time_metrics["queries_per_minute"].keys()):
            if minute < cutoff_minute:
                del self.real_time_metrics["queries_per_minute"][minute]
        
        # Update rolling averages
        recent_queries = [q for q in self.query_log if q.timestamp > time.time() - 3600]  # Last hour
        if recent_queries:
            self.real_time_metrics["error_rate"] = len([q for q in recent_queries if not q.success]) / len(recent_queries)
            self.real_time_metrics["avg_response_time"] = sum(q.response_time for q in recent_queries) / len(recent_queries)
        
        self.real_time_metrics["last_updated"] = time.time()
    
    def _analyze_query_patterns(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Analyze common query patterns."""
        # Simple pattern analysis
        word_frequency = Counter()
        for query in queries:
            words = query.lower().split()
            word_frequency.update(words)
        
        # Remove common stop words
        stop_words = {"what", "is", "are", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by"}
        meaningful_words = {word: count for word, count in word_frequency.items() 
                          if word not in stop_words and len(word) > 2}
        
        # Get top patterns
        top_words = sorted(meaningful_words.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return [{"pattern": word, "frequency": count} for word, count in top_words]
    
    async def _get_document_access_stats(self) -> Dict[str, Any]:
        """Get document access statistics."""
        try:
            # This would integrate with actual document access tracking
            return {
                "most_accessed": [],
                "least_accessed": [],
                "total_documents": 0,
                "avg_access_per_document": 0
            }
        except Exception:
            return {}
    
    def _identify_content_improvements(self, queries: List[QueryAnalytics]) -> List[str]:
        """Identify content improvement opportunities."""
        improvements = []
        
        # Analyze low-confidence queries
        low_confidence = [q for q in queries if q.confidence_score < 0.5 and q.success]
        if len(low_confidence) > len(queries) * 0.2:  # >20% low confidence
            improvements.append("Consider adding more content for frequently asked topics")
        
        # Analyze failed queries
        failed_queries = [q for q in queries if not q.success]
        if len(failed_queries) > len(queries) * 0.1:  # >10% failures
            improvements.append("Investigate common query failure patterns")
        
        # Analyze query categories with low confidence
        category_confidence = defaultdict(list)
        for query in queries:
            if query.success:
                category_confidence[query.query_category].append(query.confidence_score)
        
        for category, scores in category_confidence.items():
            if scores and sum(scores) / len(scores) < 0.6:
                improvements.append(f"Consider improving content coverage for {category} topics")
        
        return improvements

# Global analytics dashboard instance
analytics_dashboard = AnalyticsDashboard() 