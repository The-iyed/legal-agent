"""
Enhanced Document Intelligence Service

This service provides comprehensive document analysis capabilities using Azure Document Intelligence.
It supports multiple analysis models and provides advanced document processing features.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
import json
from pathlib import Path
import re
import asyncio
from dataclasses import dataclass
from enum import Enum

from app.core.config.settings import get_settings
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError

logger = logging.getLogger(__name__)


class DocumentModel(Enum):
    """Available Azure Document Intelligence models."""
    LAYOUT = "prebuilt-layout"
    DOCUMENT = "prebuilt-document"
    READ = "prebuilt-read"
    INVOICE = "prebuilt-invoice"
    RECEIPT = "prebuilt-receipt"
    ID_DOCUMENT = "prebuilt-idDocument"
    BUSINESS_CARD = "prebuilt-businessCard"
    W2 = "prebuilt-w2"
    TAX_US_W2 = "prebuilt-tax.us.w2"
    TAX_US_1098 = "prebuilt-tax.us.1098"
    TAX_US_1098_E = "prebuilt-tax.us.1098E"
    TAX_US_1098_T = "prebuilt-tax.us.1098T"


@dataclass
class DocumentAnalysisResult:
    """Result of document analysis."""
    model_used: str
    confidence: float
    pages: int
    extracted_text: str
    key_value_pairs: Dict[str, str]
    form_fields: Dict[str, str]
    tables: List[Dict[str, Any]]
    images: List[Dict[str, Any]]
    languages: List[str]
    styles: List[Dict[str, Any]]
    paragraphs: List[Dict[str, Any]]
    lines: List[Dict[str, Any]]
    words: List[Dict[str, Any]]
    processing_time: float
    raw_result: Any


class EnhancedDocumentIntelligenceService:
    """Enhanced service for document analysis using Azure Document Intelligence."""
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure Document Intelligence client."""
        try:
            if (self.settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and 
                self.settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY):
                self._client = DocumentAnalysisClient(
                    endpoint=self.settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
                    credential=AzureKeyCredential(self.settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY)
                )
                logger.info("Enhanced Document Intelligence client initialized successfully")
            else:
                logger.warning("Azure Document Intelligence credentials not configured")
        except Exception as e:
            logger.error(f"Failed to initialize Document Intelligence client: {e}")
    
    @property
    def client(self) -> Optional[DocumentAnalysisClient]:
        """Get the Document Intelligence client."""
        return self._client
    
    async def analyze_document(
        self, 
        file_content: bytes, 
        model: DocumentModel = DocumentModel.DOCUMENT,
        features: Optional[List[str]] = None
    ) -> DocumentAnalysisResult:
        """
        Analyze a document using the specified model.
        
        Args:
            file_content: Raw file content
            model: Document analysis model to use
            features: Optional features to enable
            
        Returns:
            DocumentAnalysisResult with extracted information
        """
        if not self.client:
            raise ValueError("Document Intelligence client not initialized")
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting document analysis with model: {model.value}")
            
            # Prepare analysis options
            analysis_options = {}
            if features:
                analysis_options["features"] = features
            
            # Begin document analysis
            poller = self.client.begin_analyze_document(
                model.value, 
                file_content,
                **analysis_options
            )
            
            # Wait for completion
            result = poller.result()
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Extract information from result
            analysis_result = self._extract_analysis_result(result, model.value, processing_time)
            
            logger.info(f"Document analysis completed in {processing_time:.2f}s")
            return analysis_result
            
        except AzureError as e:
            logger.error(f"Azure Document Intelligence error: {e}")
            raise
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            raise
    
    def _extract_analysis_result(
        self, 
        result: Any, 
        model_used: str, 
        processing_time: float
    ) -> DocumentAnalysisResult:
        """Extract structured information from analysis result."""
        try:
            # Extract basic information
            pages = len(result.pages) if hasattr(result, 'pages') else 1
            confidence = getattr(result, 'confidence', 0.0)
            
            # Extract text content
            extracted_text = self._extract_text_content(result)
            
            # Extract key-value pairs
            key_value_pairs = self._extract_key_value_pairs(result)
            
            # Extract form fields
            form_fields = self._extract_form_fields(result)
            
            # Extract tables
            tables = self._extract_tables(result)
            
            # Extract images
            images = self._extract_images(result)
            
            # Extract languages
            languages = self._extract_languages(result)
            
            # Extract styles
            styles = self._extract_styles(result)
            
            # Extract paragraphs
            paragraphs = self._extract_paragraphs(result)
            
            # Extract lines
            lines = self._extract_lines(result)
            
            # Extract words
            words = self._extract_words(result)
            
            return DocumentAnalysisResult(
                model_used=model_used,
                confidence=confidence,
                pages=pages,
                extracted_text=extracted_text,
                key_value_pairs=key_value_pairs,
                form_fields=form_fields,
                tables=tables,
                images=images,
                languages=languages,
                styles=styles,
                paragraphs=paragraphs,
                lines=lines,
                words=words,
                processing_time=processing_time,
                raw_result=result
            )
            
        except Exception as e:
            logger.error(f"Error extracting analysis result: {e}")
            raise
    
    def _extract_text_content(self, result: Any) -> str:
        """Extract text content from analysis result."""
        try:
            # Try to get content directly
            if hasattr(result, 'content'):
                return result.content
            
            # Extract from pages
            text_content = ""
            if hasattr(result, 'pages'):
                for page in result.pages:
                    if hasattr(page, 'lines'):
                        page_text = "\n".join([line.content for line in page.lines])
                        text_content += page_text + "\n"
                    elif hasattr(page, 'content'):
                        text_content += page.content + "\n"
            
            return text_content.strip()
            
        except Exception as e:
            logger.error(f"Error extracting text content: {e}")
            return ""
    
    def _extract_key_value_pairs(self, result: Any) -> Dict[str, str]:
        """Extract key-value pairs from analysis result."""
        try:
            key_value_pairs = {}
            if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
                for kv_pair in result.key_value_pairs:
                    if kv_pair.key and kv_pair.value:
                        key_text = kv_pair.key.content.strip()
                        value_text = kv_pair.value.content.strip()
                        key_value_pairs[key_text] = value_text
            return key_value_pairs
            
        except Exception as e:
            logger.error(f"Error extracting key-value pairs: {e}")
            return {}
    
    def _extract_form_fields(self, result: Any) -> Dict[str, str]:
        """Extract form fields from analysis result."""
        try:
            form_fields = {}
            if hasattr(result, 'form_fields') and result.form_fields:
                for field_name, field in result.form_fields.items():
                    if field.value:
                        form_fields[field_name] = field.value.content.strip()
            return form_fields
            
        except Exception as e:
            logger.error(f"Error extracting form fields: {e}")
            return {}
    
    def _extract_tables(self, result: Any) -> List[Dict[str, Any]]:
        """Extract tables from analysis result."""
        try:
            tables = []
            if hasattr(result, 'tables') and result.tables:
                for table in result.tables:
                    table_data = {
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "cells": []
                    }
                    
                    if hasattr(table, 'cells') and table.cells:
                        for cell in table.cells:
                            cell_data = {
                                "row_index": cell.row_index,
                                "column_index": cell.column_index,
                                "content": cell.content.strip() if cell.content else "",
                                "row_span": cell.row_span,
                                "column_span": cell.column_span
                            }
                            table_data["cells"].append(cell_data)
                    
                    tables.append(table_data)
            return tables
            
        except Exception as e:
            logger.error(f"Error extracting tables: {e}")
            return []
    
    def _extract_images(self, result: Any) -> List[Dict[str, Any]]:
        """Extract images from analysis result."""
        try:
            images = []
            if hasattr(result, 'images') and result.images:
                for image in result.images:
                    image_data = {
                        "page_number": image.page_number,
                        "confidence": image.confidence,
                        "bounding_polygon": [point for point in image.bounding_polygon] if hasattr(image, 'bounding_polygon') else []
                    }
                    images.append(image_data)
            return images
            
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            return []
    
    def _extract_languages(self, result: Any) -> List[str]:
        """Extract detected languages from analysis result."""
        try:
            languages = []
            if hasattr(result, 'languages') and result.languages:
                for lang in result.languages:
                    if hasattr(lang, 'locale'):
                        languages.append(lang.locale)
            return languages
            
        except Exception as e:
            logger.error(f"Error extracting languages: {e}")
            return []
    
    def _extract_styles(self, result: Any) -> List[Dict[str, Any]]:
        """Extract text styles from analysis result."""
        try:
            styles = []
            if hasattr(result, 'styles') and result.styles:
                for style in result.styles:
                    style_data = {
                        "confidence": style.confidence,
                        "is_handwritten": style.is_handwritten if hasattr(style, 'is_handwritten') else False
                    }
                    styles.append(style_data)
            return styles
            
        except Exception as e:
            logger.error(f"Error extracting styles: {e}")
            return []
    
    def _extract_paragraphs(self, result: Any) -> List[Dict[str, Any]]:
        """Extract paragraphs from analysis result."""
        try:
            paragraphs = []
            if hasattr(result, 'paragraphs') and result.paragraphs:
                for paragraph in result.paragraphs:
                    paragraph_data = {
                        "content": paragraph.content,
                        "confidence": paragraph.confidence,
                        "bounding_regions": []
                    }
                    
                    if hasattr(paragraph, 'bounding_regions') and paragraph.bounding_regions:
                        for region in paragraph.bounding_regions:
                            region_data = {
                                "page_number": region.page_number,
                                "bounding_polygon": [point for point in region.bounding_polygon]
                            }
                            paragraph_data["bounding_regions"].append(region_data)
                    
                    paragraphs.append(paragraph_data)
            return paragraphs
            
        except Exception as e:
            logger.error(f"Error extracting paragraphs: {e}")
            return []
    
    def _extract_lines(self, result: Any) -> List[Dict[str, Any]]:
        """Extract lines from analysis result."""
        try:
            lines = []
            if hasattr(result, 'pages') and result.pages:
                for page in result.pages:
                    if hasattr(page, 'lines') and page.lines:
                        for line in page.lines:
                            line_data = {
                                "content": line.content,
                                "confidence": line.confidence,
                                "page_number": page.page_number,
                                "bounding_polygon": [point for point in line.bounding_polygon] if hasattr(line, 'bounding_polygon') else []
                            }
                            lines.append(line_data)
            return lines
            
        except Exception as e:
            logger.error(f"Error extracting lines: {e}")
            return []
    
    def _extract_words(self, result: Any) -> List[Dict[str, Any]]:
        """Extract words from analysis result."""
        try:
            words = []
            if hasattr(result, 'pages') and result.pages:
                for page in result.pages:
                    if hasattr(page, 'words') and page.words:
                        for word in page.words:
                            word_data = {
                                "content": word.content,
                                "confidence": word.confidence,
                                "page_number": page.page_number,
                                "bounding_polygon": [point for point in word.bounding_polygon] if hasattr(word, 'bounding_polygon') else []
                            }
                            words.append(word_data)
            return words
            
        except Exception as e:
            logger.error(f"Error extracting words: {e}")
            return []
    
    async def analyze_with_multiple_models(
        self, 
        file_content: bytes, 
        models: List[DocumentModel] = None
    ) -> Dict[str, DocumentAnalysisResult]:
        """
        Analyze a document with multiple models and return results for each.
        
        Args:
            file_content: Raw file content
            models: List of models to use (defaults to common models)
            
        Returns:
            Dictionary mapping model names to analysis results
        """
        if not models:
            models = [
                DocumentModel.DOCUMENT,
                DocumentModel.LAYOUT,
                DocumentModel.READ
            ]
        
        results = {}
        
        for model in models:
            try:
                logger.info(f"Analyzing document with model: {model.value}")
                result = await self.analyze_document(file_content, model)
                results[model.value] = result
                
            except Exception as e:
                logger.error(f"Failed to analyze with model {model.value}: {e}")
                continue
        
        return results
    
    async def extract_legal_document_fields(
        self, 
        file_content: bytes
    ) -> Dict[str, Any]:
        """
        Extract legal document fields using specialized analysis.
        
        Args:
            file_content: Raw file content
            
        Returns:
            Extracted legal document fields
        """
        try:
            # Use document model for general extraction
            doc_result = await self.analyze_document(file_content, DocumentModel.DOCUMENT)
            
            # Use layout model for better structure
            layout_result = await self.analyze_document(file_content, DocumentModel.LAYOUT)
            
            # Combine results
            combined_text = doc_result.extracted_text
            if layout_result.extracted_text and len(layout_result.extracted_text) > len(combined_text):
                combined_text = layout_result.extracted_text
            
            # Extract legal fields
            legal_fields = self._extract_legal_fields_from_text(combined_text)
            
            return {
                "document_type": "legal_document",
                "extracted_fields": legal_fields,
                "confidence": max(doc_result.confidence, layout_result.confidence),
                "pages": max(doc_result.pages, layout_result.pages),
                "processing_time": doc_result.processing_time + layout_result.processing_time,
                "raw_text": combined_text,
                "key_value_pairs": {**doc_result.key_value_pairs, **layout_result.key_value_pairs},
                "form_fields": {**doc_result.form_fields, **layout_result.form_fields}
            }
            
        except Exception as e:
            logger.error(f"Error extracting legal document fields: {e}")
            raise
    
    def _extract_legal_fields_from_text(self, text: str) -> Dict[str, Any]:
        """Extract legal document fields from text using patterns."""
        try:
            legal_fields = {}
            
            # Define patterns for legal document fields
            patterns = {
                "case_number": [
                    r"رقم\s*قيد\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                    r"رقم\s*القضية\s*[:\-]?\s*([^\n\r]+)",
                    r"رقم\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                    r"رقم\s*الطلب\s*[:\-]?\s*([^\n\r]+)"
                ],
                "plaintiff": [
                    r"اسم\s*المدعي\s*[:\-]?\s*([^\n\r]+)",
                    r"المدعي\s*[:\-]?\s*([^\n\r]+)",
                    r"مقدم\s*الدعوى\s*[:\-]?\s*([^\n\r]+)"
                ],
                "defendant": [
                    r"اسم\s*المدعى\s*عليه\s*[:\-]?\s*([^\n\r]+)",
                    r"المدعى\s*عليه\s*[:\-]?\s*([^\n\r]+)",
                    r"الخصم\s*[:\-]?\s*([^\n\r]+)"
                ],
                "court": [
                    r"المحكمة\s*[:\-]?\s*([^\n\r]+)",
                    r"المحكمة\s*المختصة\s*[:\-]?\s*([^\n\r]+)",
                    r"قسم\s*[:\-]?\s*([^\n\r]+)"
                ],
                "case_type": [
                    r"نوع\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                    r"صنف\s*الدعوى\s*[:\-]?\s*([^\n\r]+)"
                ],
                "filing_date": [
                    r"تاريخ\s*رفع\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                    r"تاريخ\s*التقديم\s*[:\-]?\s*([^\n\r]+)",
                    r"التاريخ\s*[:\-]?\s*([^\n\r]+)"
                ],
                "case_subject": [
                    r"موضوع\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                    r"الموضوع\s*[:\-]?\s*([^\n\r]+)",
                    r"سبب\s*الدعوى\s*[:\-]?\s*([^\n\r]+)"
                ],
                "request": [
                    r"الطلب\s*[:\-]?\s*([^\n\r]+)",
                    r"طلبات\s*[:\-]?\s*([^\n\r]+)",
                    r"ما\s*يطلب\s*[:\-]?\s*([^\n\r]+)"
                ],
                "mobile": [
                    r"رقم\s*الجوال\s*[:\-]?\s*([^\n\r]+)",
                    r"الجوال\s*[:\-]?\s*([^\n\r]+)",
                    r"الهاتف\s*[:\-]?\s*([^\n\r]+)"
                ],
                "email": [
                    r"البريد\s*الإلكتروني\s*[:\-]?\s*([^\n\r]+)",
                    r"الإيميل\s*[:\-]?\s*([^\n\r]+)",
                    r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
                ]
            }
            
            # Extract fields using patterns
            for field_name, field_patterns in patterns.items():
                for pattern in field_patterns:
                    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        value = match.group(1).strip()
                        if value and len(value) > 2:
                            legal_fields[field_name] = value
                            break
                else:
                    legal_fields[field_name] = "غير مذكور"
            
            return legal_fields
            
        except Exception as e:
            logger.error(f"Error extracting legal fields from text: {e}")
            return {}
    
    async def get_document_summary(
        self, 
        file_content: bytes
    ) -> Dict[str, Any]:
        """
        Get a comprehensive summary of document analysis.
        
        Args:
            file_content: Raw file content
            
        Returns:
            Document summary with key information
        """
        try:
            # Analyze with document model
            result = await self.analyze_document(file_content, DocumentModel.DOCUMENT)
            
            # Create summary
            summary = {
                "document_type": "unknown",
                "confidence": result.confidence,
                "pages": result.pages,
                "languages": result.languages,
                "has_tables": len(result.tables) > 0,
                "has_images": len(result.images) > 0,
                "key_value_pairs_count": len(result.key_value_pairs),
                "form_fields_count": len(result.form_fields),
                "text_length": len(result.extracted_text),
                "processing_time": result.processing_time,
                "extracted_text_preview": result.extracted_text[:500] + "..." if len(result.extracted_text) > 500 else result.extracted_text
            }
            
            # Determine document type
            if len(result.key_value_pairs) > 5 or len(result.form_fields) > 5:
                summary["document_type"] = "form_document"
            elif len(result.tables) > 0:
                summary["document_type"] = "tabular_document"
            elif len(result.images) > 0:
                summary["document_type"] = "image_rich_document"
            else:
                summary["document_type"] = "text_document"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting document summary: {e}")
            raise 