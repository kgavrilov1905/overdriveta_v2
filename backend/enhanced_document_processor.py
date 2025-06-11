"""
Enhanced document processor with validation, cleaning, and deduplication
Provides comprehensive document processing with security checks and data quality improvements.
"""

import hashlib
import logging
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from document_processor import DocumentProcessor
from security_middleware import input_validator

logger = logging.getLogger(__name__)

class EnhancedDocumentProcessor:
    """Enhanced document processor with validation and quality controls."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.base_processor = DocumentProcessor(chunk_size, chunk_overlap)
        self.min_chunk_length = 50  # Minimum meaningful chunk length
        self.max_chunk_length = 5000  # Maximum chunk length for processing
        
        # Content quality patterns
        self.noise_patterns = [
            r'^\s*\d+\s*$',  # Page numbers only
            r'^\s*[a-zA-Z]\.\s*$',  # Single letters (bullets)
            r'^\s*[-•]\s*$',  # Empty bullet points
            r'^\s*©.*$',  # Copyright notices
            r'^\s*\(?\d+\)?\s*$',  # Numbers in parentheses
            r'^\s*\.+\s*$',  # Dots only
            r'^\s*Page\s+\d+.*$',  # Page headers
        ]
        
        # Sensitive content detection
        self.sensitive_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card pattern
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email pattern
        ]
    
    def process_document_enhanced(self, file_path: str, file_name: str) -> Dict[str, Any]:
        """
        Process document with enhanced validation and cleaning.
        
        Args:
            file_path: Path to the document file
            file_name: Original filename
            
        Returns:
            Enhanced processing results with quality metrics
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting enhanced processing for: {file_name}")
            
            # Step 1: Basic document processing
            base_result = self.base_processor.process_document(file_path, file_name)
            
            # Step 2: Enhanced validation and preprocessing
            validation_result = self._validate_document_content(base_result)
            
            if not validation_result["valid"]:
                logger.error(f"Document validation failed: {validation_result['errors']}")
                raise ValueError(f"Document validation failed: {'; '.join(validation_result['errors'])}")
            
            # Step 3: Clean and enhance chunks
            enhanced_chunks = self._clean_and_enhance_chunks(base_result["chunks"])
            
            # Step 4: Calculate document fingerprint for deduplication
            content_fingerprint = self._calculate_document_fingerprint(enhanced_chunks)
            
            # Step 5: Quality assessment
            quality_metrics = self._assess_content_quality(enhanced_chunks)
            
            # Step 6: Prepare enhanced result
            enhanced_result = {
                "document": {
                    **base_result["document"],
                    "content_fingerprint": content_fingerprint,
                    "quality_metrics": quality_metrics,
                    "processing_metadata": {
                        "processor_version": "enhanced_v1.0",
                        "processing_time": time.time() - start_time,
                        "validation_passed": True,
                        "chunks_cleaned": len(enhanced_chunks),
                        "chunks_filtered": len(base_result["chunks"]) - len(enhanced_chunks)
                    }
                },
                "chunks": enhanced_chunks,
                "validation": validation_result,
                "quality": quality_metrics
            }
            
            logger.info(f"Enhanced processing completed: {file_name} - "
                       f"{len(enhanced_chunks)} chunks, quality score: {quality_metrics['overall_score']:.2f}")
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Enhanced document processing failed: {str(e)}")
            raise
    
    def _validate_document_content(self, base_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate document content for quality and security."""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "security_issues": []
        }
        
        document = base_result["document"]
        chunks = base_result["chunks"]
        
        # Check document metadata
        if not document.get("title") or len(document["title"].strip()) < 3:
            validation["warnings"].append("Document title is missing or too short")
        
        if document.get("page_count", 0) <= 0:
            validation["errors"].append("Document appears to have no content pages")
            validation["valid"] = False
        
        # Check chunks quality
        if not chunks or len(chunks) == 0:
            validation["errors"].append("No text chunks could be extracted from document")
            validation["valid"] = False
            return validation
        
        # Content validation
        total_content_length = sum(len(chunk.get("content", "")) for chunk in chunks)
        if total_content_length < 100:
            validation["errors"].append("Document content is too short (minimum 100 characters)")
            validation["valid"] = False
        
        # Security checks
        security_issues = self._detect_sensitive_content(chunks)
        if security_issues:
            validation["security_issues"] = security_issues
            validation["warnings"].append(f"Found {len(security_issues)} potential security issues")
        
        # Language detection (basic)
        if not self._is_primarily_english_content(chunks):
            validation["warnings"].append("Document may not be primarily in English")
        
        return validation
    
    def _clean_and_enhance_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean and enhance document chunks."""
        enhanced_chunks = []
        
        for i, chunk in enumerate(chunks):
            try:
                content = chunk.get("content", "")
                
                # Skip empty or too-short chunks
                if not content or len(content.strip()) < self.min_chunk_length:
                    continue
                
                # Clean the content
                cleaned_content = self._clean_chunk_content(content)
                
                # Skip if content became too short after cleaning
                if len(cleaned_content.strip()) < self.min_chunk_length:
                    continue
                
                # Skip noise-only chunks
                if self._is_noise_chunk(cleaned_content):
                    continue
                
                # Enhance chunk metadata
                enhanced_chunk = {
                    **chunk,
                    "content": cleaned_content,
                    "content_hash": hashlib.sha256(cleaned_content.encode()).hexdigest()[:16],
                    "quality_score": self._calculate_chunk_quality(cleaned_content),
                    "word_count": len(cleaned_content.split()),
                    "char_count": len(cleaned_content),
                    "sentence_count": len(re.findall(r'[.!?]+', cleaned_content)),
                    "enhanced": True
                }
                
                enhanced_chunks.append(enhanced_chunk)
                
            except Exception as e:
                logger.warning(f"Failed to process chunk {i}: {str(e)}")
                continue
        
        return enhanced_chunks
    
    def _clean_chunk_content(self, content: str) -> str:
        """Clean individual chunk content."""
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', content)
        
        # Remove control characters
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)
        
        # Fix common OCR errors
        cleaned = self._fix_ocr_errors(cleaned)
        
        # Normalize punctuation
        cleaned = re.sub(r'["""]', '"', cleaned)
        cleaned = re.sub(r'[''']', "'", cleaned)
        cleaned = re.sub(r'–', '-', cleaned)
        cleaned = re.sub(r'—', '--', cleaned)
        
        # Remove excessive punctuation
        cleaned = re.sub(r'\.{3,}', '...', cleaned)
        cleaned = re.sub(r'[!]{2,}', '!', cleaned)
        cleaned = re.sub(r'[?]{2,}', '?', cleaned)
        
        return cleaned.strip()
    
    def _fix_ocr_errors(self, text: str) -> str:
        """Fix common OCR errors in text."""
        # Common OCR substitutions
        ocr_fixes = {
            r'\bl\b': 'I',  # lowercase l to uppercase I
            r'\b0\b': 'O',  # zero to O in words
            r'\brn\b': 'm',  # rn to m
            r'\bvv\b': 'w',  # vv to w
            r'\bc1\b': 'cl', # c1 to cl
        }
        
        fixed_text = text
        for pattern, replacement in ocr_fixes.items():
            fixed_text = re.sub(pattern, replacement, fixed_text)
        
        return fixed_text
    
    def _is_noise_chunk(self, content: str) -> bool:
        """Check if chunk contains only noise/irrelevant content."""
        content_clean = content.strip().lower()
        
        # Check against noise patterns
        for pattern in self.noise_patterns:
            if re.match(pattern, content_clean):
                return True
        
        # Check content characteristics
        words = content_clean.split()
        
        # Too few words
        if len(words) < 5:
            return True
        
        # Too many repeated characters
        if any(char * 5 in content_clean for char in 'abcdefghijklmnopqrstuvwxyz'):
            return True
        
        # Mostly numbers or symbols
        non_alpha_ratio = sum(1 for char in content_clean if not char.isalpha()) / len(content_clean)
        if non_alpha_ratio > 0.7:
            return True
        
        return False
    
    def _calculate_chunk_quality(self, content: str) -> float:
        """Calculate quality score for a chunk (0-1)."""
        score = 0.5  # Base score
        
        words = content.split()
        
        # Length factors
        if 20 <= len(words) <= 200:
            score += 0.2
        elif len(words) < 5:
            score -= 0.3
        
        # Sentence structure
        sentences = re.findall(r'[.!?]+', content)
        if len(sentences) > 0:
            avg_sentence_length = len(words) / len(sentences)
            if 5 <= avg_sentence_length <= 25:
                score += 0.1
        
        # Capitalization (indicates proper formatting)
        capital_ratio = sum(1 for char in content if char.isupper()) / len(content)
        if 0.02 <= capital_ratio <= 0.1:
            score += 0.1
        
        # Information density (avoid repetitive content)
        unique_words = len(set(word.lower() for word in words))
        if len(words) > 0:
            uniqueness_ratio = unique_words / len(words)
            if uniqueness_ratio > 0.6:
                score += 0.1
        
        return min(score, 1.0)
    
    def _detect_sensitive_content(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect potentially sensitive content in chunks."""
        sensitive_findings = []
        
        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            
            for pattern_name, pattern in [
                ("SSN", self.sensitive_patterns[0]),
                ("Credit Card", self.sensitive_patterns[1]),
                ("Email", self.sensitive_patterns[2])
            ]:
                matches = re.findall(pattern, content)
                if matches:
                    sensitive_findings.append({
                        "chunk_index": i,
                        "type": pattern_name,
                        "matches_count": len(matches),
                        "content_preview": content[:100] + "..." if len(content) > 100 else content
                    })
        
        return sensitive_findings
    
    def _is_primarily_english_content(self, chunks: List[Dict[str, Any]]) -> bool:
        """Basic check if content is primarily in English."""
        total_words = 0
        english_indicators = 0
        
        # Common English words for detection
        common_english = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'about', 'as', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'can', 'could'
        }
        
        for chunk in chunks:
            content = chunk.get("content", "").lower()
            words = re.findall(r'\b[a-z]+\b', content)
            total_words += len(words)
            
            for word in words:
                if word in common_english:
                    english_indicators += 1
        
        if total_words == 0:
            return False
        
        english_ratio = english_indicators / total_words
        return english_ratio > 0.05  # At least 5% common English words
    
    def _calculate_document_fingerprint(self, chunks: List[Dict[str, Any]]) -> str:
        """Calculate unique fingerprint for document deduplication."""
        # Combine key content elements
        content_parts = []
        
        for chunk in chunks[:10]:  # Use first 10 chunks for fingerprint
            content = chunk.get("content", "").strip()
            if content:
                # Normalize content for fingerprinting
                normalized = re.sub(r'\s+', ' ', content.lower())
                normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
                content_parts.append(normalized)
        
        combined_content = ' '.join(content_parts)
        
        # Create hash
        return hashlib.sha256(combined_content.encode()).hexdigest()
    
    def _assess_content_quality(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess overall content quality."""
        if not chunks:
            return {
                "overall_score": 0.0,
                "total_chunks": 0,
                "avg_chunk_quality": 0.0,
                "total_words": 0,
                "readability": "poor"
            }
        
        chunk_scores = [chunk.get("quality_score", 0.5) for chunk in chunks]
        avg_quality = sum(chunk_scores) / len(chunk_scores)
        
        total_words = sum(chunk.get("word_count", 0) for chunk in chunks)
        total_sentences = sum(chunk.get("sentence_count", 0) for chunk in chunks)
        
        # Calculate readability estimate
        if total_sentences > 0:
            avg_sentence_length = total_words / total_sentences
            if avg_sentence_length < 10:
                readability = "easy"
            elif avg_sentence_length < 20:
                readability = "moderate"
            else:
                readability = "complex"
        else:
            readability = "poor"
        
        # Overall score combines multiple factors
        overall_score = (
            avg_quality * 0.6 +
            min(len(chunks) / 20, 1.0) * 0.2 +  # Reasonable chunk count
            min(total_words / 1000, 1.0) * 0.2   # Reasonable word count
        )
        
        return {
            "overall_score": overall_score,
            "total_chunks": len(chunks),
            "avg_chunk_quality": avg_quality,
            "total_words": total_words,
            "total_sentences": total_sentences,
            "avg_sentence_length": total_sentences and total_words / total_sentences or 0,
            "readability": readability,
            "content_density": "high" if total_words / len(chunks) > 100 else "low"
        }

async def check_document_duplication(file_name: str, content: bytes, db_manager) -> Optional[Dict[str, Any]]:
    """
    Check if document already exists based on filename and content hash.
    
    Args:
        file_name: Original filename
        content: File content bytes
        db_manager: Database manager instance
        
    Returns:
        Existing document info if duplicate found, None otherwise
    """
    try:
        # Calculate content hash
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Check by filename first (quick check)
        existing_by_name = await db_manager.find_document_by_filename(file_name)
        
        if existing_by_name:
            logger.info(f"Found existing document with same filename: {file_name}")
            return existing_by_name
        
        # Check by content hash (more thorough)
        existing_by_hash = await db_manager.find_document_by_content_hash(content_hash)
        
        if existing_by_hash:
            logger.info(f"Found existing document with same content hash: {content_hash[:16]}...")
            return existing_by_hash
        
        return None
        
    except Exception as e:
        logger.warning(f"Error checking document duplication: {str(e)}")
        return None

# Global enhanced processor instance
enhanced_document_processor = EnhancedDocumentProcessor() 