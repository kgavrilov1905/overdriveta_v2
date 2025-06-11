"""
Advanced Document Deduplication System
Prevents duplicate documents and provides intelligent merge capabilities for Alberta Perspectives RAG.
"""

import hashlib
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher
import asyncio
from datetime import datetime

from database import db_manager
from embedding_service import embedding_service

logger = logging.getLogger(__name__)

class DocumentDeduplicationService:
    """Advanced document deduplication with multiple detection methods."""
    
    def __init__(self):
        self.similarity_threshold = 0.85  # 85% similarity threshold
        self.content_hash_threshold = 0.95  # Content hash similarity
        self.semantic_threshold = 0.90  # Semantic similarity threshold
    
    async def check_for_duplicates(self, file_name: str, file_content: bytes, 
                                   extracted_text: str = None) -> Dict[str, Any]:
        """
        Comprehensive duplicate detection using multiple methods.
        
        Args:
            file_name: Original filename
            file_content: Raw file bytes
            extracted_text: Extracted text content (optional)
            
        Returns:
            Duplicate detection results with recommendations
        """
        try:
            logger.info(f"Starting duplicate detection for: {file_name}")
            
            results = {
                "is_duplicate": False,
                "confidence": 0.0,
                "duplicate_type": None,
                "existing_document": None,
                "recommendations": [],
                "similar_documents": [],
                "action": "proceed"  # proceed, skip, merge, replace
            }
            
            # Method 1: Exact content hash match
            exact_match = await self._check_exact_content_match(file_content)
            if exact_match:
                results.update({
                    "is_duplicate": True,
                    "confidence": 1.0,
                    "duplicate_type": "exact_content",
                    "existing_document": exact_match,
                    "action": "skip",
                    "recommendations": [
                        f"Identical document already exists: {exact_match['file_name']}",
                        "Recommend skipping upload to save storage and processing costs"
                    ]
                })
                return results
            
            # Method 2: Filename similarity
            filename_matches = await self._check_filename_similarity(file_name)
            
            # Method 3: Content hash similarity (for slightly modified files)
            content_matches = await self._check_content_similarity(file_content)
            
            # Method 4: Semantic similarity (if text provided)
            semantic_matches = []
            if extracted_text:
                semantic_matches = await self._check_semantic_similarity(extracted_text)
            
            # Analyze all matches and determine best action
            all_matches = self._consolidate_matches(filename_matches, content_matches, semantic_matches)
            
            if all_matches:
                best_match = max(all_matches, key=lambda x: x['similarity_score'])
                
                if best_match['similarity_score'] >= self.similarity_threshold:
                    results.update({
                        "is_duplicate": True,
                        "confidence": best_match['similarity_score'],
                        "duplicate_type": best_match['match_type'],
                        "existing_document": best_match,
                        "similar_documents": all_matches[:5],  # Top 5 similar docs
                        "action": self._determine_action(best_match),
                        "recommendations": self._generate_recommendations(best_match, all_matches)
                    })
                else:
                    # Similar but not duplicate
                    results.update({
                        "similar_documents": all_matches[:3],  # Top 3 similar docs
                        "recommendations": [
                            "Similar documents found - consider organizing in same category",
                            "Review existing content before uploading to avoid redundancy"
                        ]
                    })
            
            logger.info(f"Duplicate detection completed: {file_name} - "
                       f"Duplicate: {results['is_duplicate']}, Action: {results['action']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Duplicate detection failed for {file_name}: {str(e)}")
            return {
                "is_duplicate": False,
                "confidence": 0.0,
                "error": str(e),
                "action": "proceed",
                "recommendations": ["Duplicate detection failed - proceeding with upload"]
            }
    
    async def _check_exact_content_match(self, file_content: bytes) -> Optional[Dict[str, Any]]:
        """Check for exact content hash match."""
        try:
            content_hash = hashlib.sha256(file_content).hexdigest()
            
            # Query database for exact hash match
            existing_doc = await db_manager.find_document_by_content_hash(content_hash)
            
            if existing_doc:
                logger.info(f"Found exact content match: {existing_doc.get('file_name')}")
                return {
                    **existing_doc,
                    "match_type": "exact_content",
                    "similarity_score": 1.0
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error checking exact content match: {str(e)}")
            return None
    
    async def _check_filename_similarity(self, file_name: str) -> List[Dict[str, Any]]:
        """Check for similar filenames."""
        try:
            # Get all existing document filenames
            existing_docs = await db_manager.get_all_document_filenames()
            
            similar_docs = []
            
            for doc in existing_docs:
                existing_name = doc.get('file_name', '')
                similarity = self._calculate_filename_similarity(file_name, existing_name)
                
                if similarity >= 0.7:  # 70% filename similarity
                    similar_docs.append({
                        **doc,
                        "match_type": "filename",
                        "similarity_score": similarity,
                        "similarity_reason": self._explain_filename_similarity(file_name, existing_name)
                    })
            
            # Sort by similarity
            similar_docs.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return similar_docs[:10]  # Top 10 matches
            
        except Exception as e:
            logger.warning(f"Error checking filename similarity: {str(e)}")
            return []
    
    async def _check_content_similarity(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Check for content hash similarity (fuzzy matching)."""
        try:
            # Create content fingerprint (first and last 1KB + file size)
            content_fingerprint = self._create_content_fingerprint(file_content)
            
            # Get existing document fingerprints
            existing_docs = await db_manager.get_documents_with_metadata()
            
            similar_docs = []
            
            for doc in existing_docs:
                doc_metadata = doc.get('metadata', {})
                existing_fingerprint = doc_metadata.get('content_fingerprint')
                
                if existing_fingerprint:
                    similarity = self._compare_content_fingerprints(content_fingerprint, existing_fingerprint)
                    
                    if similarity >= 0.8:  # 80% content similarity
                        similar_docs.append({
                            **doc,
                            "match_type": "content_hash",
                            "similarity_score": similarity,
                            "similarity_reason": f"Content fingerprint similarity: {similarity:.2%}"
                        })
            
            similar_docs.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_docs[:10]
            
        except Exception as e:
            logger.warning(f"Error checking content similarity: {str(e)}")
            return []
    
    async def _check_semantic_similarity(self, extracted_text: str) -> List[Dict[str, Any]]:
        """Check for semantic similarity using embeddings."""
        try:
            # Generate embedding for the new document
            text_sample = extracted_text[:2000]  # First 2000 characters
            new_embedding = embedding_service.generate_query_embedding(text_sample)
            
            # Get similar documents using vector search
            similar_docs = await db_manager.similarity_search(
                query_embedding=new_embedding,
                limit=10,
                threshold=0.85
            )
            
            semantic_matches = []
            
            for doc in similar_docs:
                # Group by document to get document-level similarity
                doc_id = doc.get('document_id')
                if doc_id:
                    doc_info = await db_manager.get_document_by_id(doc_id)
                    if doc_info:
                        semantic_matches.append({
                            **doc_info,
                            "match_type": "semantic",
                            "similarity_score": doc.get('similarity_score', 0),
                            "similarity_reason": f"Semantic content similarity: {doc.get('similarity_score', 0):.2%}"
                        })
            
            # Remove duplicates and sort
            unique_matches = {doc['id']: doc for doc in semantic_matches}.values()
            sorted_matches = sorted(unique_matches, key=lambda x: x['similarity_score'], reverse=True)
            
            return list(sorted_matches)[:5]  # Top 5 semantic matches
            
        except Exception as e:
            logger.warning(f"Error checking semantic similarity: {str(e)}")
            return []
    
    def _calculate_filename_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two filenames."""
        # Normalize filenames
        norm1 = self._normalize_filename(name1)
        norm2 = self._normalize_filename(name2)
        
        # Basic string similarity
        basic_similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Boost similarity for same base name
        base1 = norm1.split('.')[0]
        base2 = norm2.split('.')[0]
        
        if base1 == base2:
            return 0.95  # Very high similarity for same base name
        
        # Check for version patterns (v1, v2, etc.)
        version_pattern = r'(.+?)[-_\s]*v?\d+[-_\s]*(.*)$'
        match1 = re.match(version_pattern, norm1, re.IGNORECASE)
        match2 = re.match(version_pattern, norm2, re.IGNORECASE)
        
        if match1 and match2:
            base_sim = SequenceMatcher(None, match1.group(1), match2.group(1)).ratio()
            if base_sim > 0.8:
                return min(0.9, basic_similarity + 0.2)  # Boost for version variants
        
        return basic_similarity
    
    def _normalize_filename(self, filename: str) -> str:
        """Normalize filename for comparison."""
        # Remove extension and convert to lowercase
        name = filename.lower()
        if '.' in name:
            name = name.rsplit('.', 1)[0]
        
        # Replace common separators with spaces
        name = re.sub(r'[-_]+', ' ', name)
        
        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def _explain_filename_similarity(self, name1: str, name2: str) -> str:
        """Explain why two filenames are similar."""
        norm1 = self._normalize_filename(name1)
        norm2 = self._normalize_filename(name2)
        
        if norm1 == norm2:
            return "Identical base filenames"
        
        # Check for version differences
        if re.sub(r'v?\d+', '', norm1) == re.sub(r'v?\d+', '', norm2):
            return "Same document, different version"
        
        # Check for date differences
        date_pattern = r'\d{4}[-_]\d{2}[-_]\d{2}|\d{2}[-_]\d{2}[-_]\d{4}'
        if (re.sub(date_pattern, '', norm1) == re.sub(date_pattern, '', norm2)):
            return "Same document, different date"
        
        return "Similar filename structure"
    
    def _create_content_fingerprint(self, content: bytes) -> str:
        """Create a fingerprint for content comparison."""
        size = len(content)
        
        # Use first 1KB, last 1KB, and file size
        start_hash = hashlib.md5(content[:1024]).hexdigest()[:8]
        end_hash = hashlib.md5(content[-1024:]).hexdigest()[:8] if size > 1024 else start_hash
        
        return f"{start_hash}_{end_hash}_{size}"
    
    def _compare_content_fingerprints(self, fp1: str, fp2: str) -> float:
        """Compare two content fingerprints."""
        parts1 = fp1.split('_')
        parts2 = fp2.split('_')
        
        if len(parts1) != 3 or len(parts2) != 3:
            return 0.0
        
        start_sim = 1.0 if parts1[0] == parts2[0] else 0.0
        end_sim = 1.0 if parts1[1] == parts2[1] else 0.0
        
        # Size similarity
        size1, size2 = int(parts1[2]), int(parts2[2])
        size_diff = abs(size1 - size2) / max(size1, size2)
        size_sim = max(0.0, 1.0 - size_diff)
        
        # Weighted average
        return (start_sim * 0.4 + end_sim * 0.4 + size_sim * 0.2)
    
    def _consolidate_matches(self, filename_matches: List, content_matches: List, 
                           semantic_matches: List) -> List[Dict[str, Any]]:
        """Consolidate matches from different methods."""
        all_matches = {}
        
        # Add all matches, keeping the highest similarity score for each document
        for match_list in [filename_matches, content_matches, semantic_matches]:
            for match in match_list:
                doc_id = match.get('id')
                if doc_id:
                    existing = all_matches.get(doc_id)
                    if not existing or match['similarity_score'] > existing['similarity_score']:
                        all_matches[doc_id] = match
        
        return list(all_matches.values())
    
    def _determine_action(self, best_match: Dict[str, Any]) -> str:
        """Determine recommended action based on best match."""
        similarity = best_match['similarity_score']
        match_type = best_match['match_type']
        
        if similarity >= 0.95:
            return "skip"  # Very high similarity - skip upload
        elif similarity >= 0.90:
            if match_type == "semantic":
                return "merge"  # Similar content - consider merging
            else:
                return "replace"  # Likely updated version
        elif similarity >= 0.85:
            return "review"  # Manual review recommended
        else:
            return "proceed"  # Proceed with upload
    
    def _generate_recommendations(self, best_match: Dict[str, Any], 
                                all_matches: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        similarity = best_match['similarity_score']
        match_type = best_match['match_type']
        
        if similarity >= 0.95:
            recommendations.append(f"⚠️  Near-identical document found: {best_match.get('file_name')}")
            recommendations.append("💡 Recommend skipping upload to save storage costs")
            
        elif similarity >= 0.90:
            recommendations.append(f"📄 Very similar document exists: {best_match.get('file_name')}")
            if match_type == "filename":
                recommendations.append("💡 This may be an updated version - consider replacing the old document")
            elif match_type == "semantic":
                recommendations.append("💡 Similar content detected - review for potential consolidation")
                
        elif similarity >= 0.85:
            recommendations.append(f"🔍 Similar document found: {best_match.get('file_name')}")
            recommendations.append("💡 Manual review recommended before uploading")
        
        if len(all_matches) > 1:
            recommendations.append(f"📊 Found {len(all_matches)} similar documents total")
            recommendations.append("💡 Consider organizing related documents in collections")
        
        return recommendations
    
    async def merge_similar_documents(self, primary_doc_id: str, 
                                    secondary_doc_ids: List[str]) -> Dict[str, Any]:
        """Merge similar documents into a single entry."""
        try:
            logger.info(f"Merging documents: primary={primary_doc_id}, secondary={secondary_doc_ids}")
            
            # Get all documents
            primary_doc = await db_manager.get_document_by_id(primary_doc_id)
            secondary_docs = []
            
            for doc_id in secondary_doc_ids:
                doc = await db_manager.get_document_by_id(doc_id)
                if doc:
                    secondary_docs.append(doc)
            
            # Create merged metadata
            merged_metadata = {
                "merged_from": secondary_doc_ids,
                "merge_date": datetime.now().isoformat(),
                "original_filenames": [doc.get('file_name') for doc in secondary_docs],
                "merge_reason": "duplicate_detection",
                "total_merged_documents": len(secondary_docs) + 1
            }
            
            # Update primary document with merge information
            await db_manager.update_document_metadata(primary_doc_id, merged_metadata)
            
            # Mark secondary documents as merged (don't delete, for audit trail)
            for doc_id in secondary_doc_ids:
                await db_manager.update_document_status(doc_id, "merged")
                await db_manager.update_document_metadata(doc_id, {
                    "merged_into": primary_doc_id,
                    "merge_date": datetime.now().isoformat()
                })
            
            logger.info(f"Successfully merged {len(secondary_docs)} documents into {primary_doc_id}")
            
            return {
                "success": True,
                "primary_document": primary_doc_id,
                "merged_documents": secondary_doc_ids,
                "total_documents_affected": len(secondary_docs) + 1
            }
            
        except Exception as e:
            logger.error(f"Failed to merge documents: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# Global deduplication service instance
deduplication_service = DocumentDeduplicationService() 