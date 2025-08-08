"""
PDF Splitter Service

This service handles splitting PDF documents into individual pages and processing
each page with Azure Document Intelligence to ensure comprehensive text extraction.
"""

import logging
import io
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import uuid

import PyPDF2
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from app.core.config.settings import get_settings

logger = logging.getLogger(__name__)


class PDFSplitterService:
    """Service for splitting PDFs into pages and processing with Document Intelligence."""
    
    def __init__(self):
        self.settings = get_settings()
        self._document_intelligence_client = None
        self._initialize_document_intelligence_client()
    
    def _initialize_document_intelligence_client(self):
        """Initialize Azure Document Intelligence client."""
        try:
            if (self.settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and 
                self.settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY):
                self._document_intelligence_client = DocumentAnalysisClient(
                    endpoint=self.settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
                    credential=AzureKeyCredential(self.settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY)
                )
                logger.info("Document Intelligence client initialized for PDF splitting")
            else:
                logger.warning("Document Intelligence credentials not configured for PDF splitting")
        except Exception as e:
            logger.error(f"Failed to initialize Document Intelligence client: {e}")
    
    async def split_and_extract_pdf(
        self, 
        file_content: bytes, 
        filename: str,
        extract_per_page: bool = True,
        combine_results: bool = True
    ) -> Dict[str, Any]:
        """
        Split PDF into pages and extract text from each page using Document Intelligence.
        
        Args:
            file_content: Raw PDF file content
            filename: Original filename
            extract_per_page: Whether to extract text from each page individually
            combine_results: Whether to combine results from all pages
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            logger.info(f"Starting PDF splitting and extraction for {filename}")
            
            # Split PDF into pages
            pages = await self._split_pdf_into_pages(file_content, filename)
            
            if not pages:
                logger.warning(f"No pages extracted from {filename}")
                return {
                    "success": False,
                    "error": "No pages could be extracted from PDF",
                    "total_pages": 0,
                    "extracted_text": "",
                    "page_results": []
                }
            
            logger.info(f"Successfully split PDF into {len(pages)} pages")
            
            # Extract text from each page if requested
            page_results = []
            combined_text = ""
            
            if extract_per_page:
                for page_num, page_content in enumerate(pages, 1):
                    logger.info(f"Processing page {page_num}/{len(pages)}")
                    
                    page_result = await self._extract_text_from_page(
                        page_content, 
                        filename, 
                        page_num
                    )
                    page_results.append(page_result)
                    
                    if combine_results and page_result.get("extracted_text"):
                        combined_text += f"\n--- Page {page_num} ---\n"
                        combined_text += page_result["extracted_text"]
                        combined_text += "\n"
            
            # Prepare final result
            result = {
                "success": True,
                "total_pages": len(pages),
                "extracted_text": combined_text.strip() if combine_results else "",
                "page_results": page_results,
                "processing_timestamp": datetime.utcnow().isoformat(),
                "filename": filename,
                "processing_id": str(uuid.uuid4())
            }
            
            logger.info(f"PDF processing completed for {filename}: {len(pages)} pages processed")
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF {filename}: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_pages": 0,
                "extracted_text": "",
                "page_results": []
            }
    
    async def _split_pdf_into_pages(
        self, 
        file_content: bytes, 
        filename: str
    ) -> List[bytes]:
        """
        Split PDF file into individual pages.
        
        Args:
            file_content: Raw PDF file content
            filename: Original filename
            
        Returns:
            List of page contents as bytes
        """
        try:
            pages = []
            
            # Create PDF reader
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            
            # Extract each page
            for page_num in range(len(pdf_reader.pages)):
                try:
                    # Create a new PDF with just this page
                    pdf_writer = PyPDF2.PdfWriter()
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                    
                    # Write to bytes buffer
                    page_buffer = io.BytesIO()
                    pdf_writer.write(page_buffer)
                    page_content = page_buffer.getvalue()
                    
                    pages.append(page_content)
                    logger.debug(f"Extracted page {page_num + 1}")
                    
                except Exception as e:
                    logger.error(f"Error extracting page {page_num + 1}: {e}")
                    # Continue with other pages
                    continue
            
            return pages
            
        except Exception as e:
            logger.error(f"Error splitting PDF {filename}: {e}")
            return []
    
    async def _extract_text_from_page(
        self, 
        page_content: bytes, 
        filename: str, 
        page_num: int
    ) -> Dict[str, Any]:
        """
        Extract text from a single page using Document Intelligence.
        
        Args:
            page_content: Page content as bytes
            filename: Original filename
            page_num: Page number
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            page_result = {
                "page_number": page_num,
                "extracted_text": "",
                "confidence": 0.0,
                "key_value_pairs": {},
                "form_fields": {},
                "processing_time": 0.0,
                "success": False
            }
            
            if not self._document_intelligence_client:
                logger.warning("Document Intelligence not available, using fallback extraction")
                # Fallback to PyPDF2 text extraction
                try:
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(page_content))
                    if pdf_reader.pages:
                        page_result["extracted_text"] = pdf_reader.pages[0].extract_text()
                        page_result["success"] = True
                except Exception as e:
                    logger.error(f"Fallback extraction failed for page {page_num}: {e}")
                return page_result
            
            start_time = datetime.now()
            
            try:
                # Use Document Intelligence to analyze the page
                poller = self._document_intelligence_client.begin_analyze_document(
                    "prebuilt-layout", page_content
                )
                result = poller.result()
                
                # Extract text with better structure
                extracted_text = ""
                
                # Extract paragraphs for better structure
                if hasattr(result, 'paragraphs'):
                    for paragraph in result.paragraphs:
                        extracted_text += paragraph.content + "\n\n"
                
                # Fallback to lines if paragraphs not available
                if not extracted_text and hasattr(result, 'pages') and result.pages:
                    page = result.pages[0]
                    if hasattr(page, 'lines'):
                        current_line_y = None
                        for line in page.lines:
                            # Group lines by vertical position for better paragraph structure
                            if current_line_y is None or abs(line.polygon[1] - current_line_y) > 5:
                                extracted_text += "\n"
                            extracted_text += line.content + " "
                            current_line_y = line.polygon[1]
                        extracted_text += "\n\n"
                    
                    # Final fallback to page content
                    elif hasattr(page, 'content'):
                        extracted_text = page.content + "\n\n"
                
                # Extract key-value pairs
                key_value_pairs = {}
                if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
                    for kv_pair in result.key_value_pairs:
                        if kv_pair.key and kv_pair.value:
                            key_text = kv_pair.key.content.strip()
                            value_text = kv_pair.value.content.strip()
                            key_value_pairs[key_text] = value_text
                
                # Extract form fields
                form_fields = {}
                if hasattr(result, 'form_fields') and result.form_fields:
                    for field in result.form_fields:
                        if field.name and field.value:
                            form_fields[field.name] = field.value.content
                
                # Calculate processing time
                processing_time = (datetime.now() - start_time).total_seconds()
                
                # Update result
                page_result.update({
                    "extracted_text": extracted_text.strip(),
                    "confidence": getattr(result, 'confidence', 0.0),
                    "key_value_pairs": key_value_pairs,
                    "form_fields": form_fields,
                    "processing_time": processing_time,
                    "success": True
                })
                
                logger.debug(f"Page {page_num} processed successfully in {processing_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Document Intelligence extraction failed for page {page_num}: {e}")
                # Fallback to PyPDF2
                try:
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(page_content))
                    if pdf_reader.pages:
                        page_result["extracted_text"] = pdf_reader.pages[0].extract_text()
                        page_result["success"] = True
                except Exception as fallback_error:
                    logger.error(f"Fallback extraction also failed for page {page_num}: {fallback_error}")
            
            return page_result
            
        except Exception as e:
            logger.error(f"Error extracting text from page {page_num}: {e}")
            return {
                "page_number": page_num,
                "extracted_text": "",
                "confidence": 0.0,
                "key_value_pairs": {},
                "form_fields": {},
                "processing_time": 0.0,
                "success": False,
                "error": str(e)
            }
    
    async def extract_with_multiple_models(
        self, 
        file_content: bytes, 
        filename: str
    ) -> Dict[str, Any]:
        """
        Extract text using multiple Document Intelligence models for better coverage.
        
        Args:
            file_content: Raw PDF file content
            filename: Original filename
            
        Returns:
            Dictionary with combined results from multiple models
        """
        try:
            logger.info(f"Starting multi-model extraction for {filename}")
            
            if not self._document_intelligence_client:
                logger.warning("Document Intelligence not available for multi-model extraction")
                return await self.split_and_extract_pdf(file_content, filename, extract_per_page=False)
            
            # Split PDF into pages
            pages = await self._split_pdf_into_pages(file_content, filename)
            
            if not pages:
                return {
                    "success": False,
                    "error": "No pages could be extracted from PDF",
                    "total_pages": 0,
                    "extracted_text": "",
                    "page_results": []
                }
            
            # Process each page with multiple models in parallel
            logger.info(f"Processing {len(pages)} pages in parallel with multiple models")
            
            # Create tasks for processing each page
            page_tasks = []
            for page_num, page_content in enumerate(pages, 1):
                task = self._process_page_with_multiple_models(page_content, page_num, filename)
                page_tasks.append(task)
            
            # Wait for all pages to complete processing
            page_results = await asyncio.gather(*page_tasks, return_exceptions=True)
            
            # Process results and handle any exceptions
            valid_page_results = []
            combined_text = ""
            
            for i, result in enumerate(page_results):
                if isinstance(result, Exception):
                    logger.error(f"Page {i+1} processing failed: {result}")
                    # Add fallback result for failed page
                    fallback_result = {
                        "page_number": i+1,
                        "extracted_text": "",
                        "confidence": 0.0,
                        "model_used": "error_fallback",
                        "success": False,
                        "error_message": str(result)
                    }
                    valid_page_results.append(fallback_result)
                else:
                    valid_page_results.append(result)
                    if result.get("success"):
                        page_num = result["page_number"]
                        model_used = result["model_used"]
                        extracted_text = result["extracted_text"]
                        combined_text += f"\n--- Page {page_num} (Model: {model_used}) ---\n"
                        combined_text += extracted_text
                        combined_text += "\n"
            
            # Sort results by page number
            valid_page_results.sort(key=lambda x: x["page_number"])
            
            page_results = valid_page_results
            
            return {
                "success": True,
                "total_pages": len(pages),
                "extracted_text": combined_text.strip(),
                "page_results": page_results,
                "processing_timestamp": datetime.utcnow().isoformat(),
                "filename": filename,
                "processing_id": str(uuid.uuid4()),
                "extraction_method": "multi_model"
            }
            
        except Exception as e:
            logger.error(f"Error in multi-model extraction for {filename}: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_pages": 0,
                "extracted_text": "",
                "page_results": []
            }

    async def _process_page_with_multiple_models(
        self, 
        page_content: bytes, 
        page_num: int, 
        filename: str
    ) -> Dict[str, Any]:
        """
        Process a single page with multiple Document Intelligence models in parallel.
        
        Args:
            page_content: Raw page content
            page_num: Page number
            filename: Original filename
            
        Returns:
            Dictionary with the best extraction result for the page
        """
        try:
            logger.debug(f"Processing page {page_num} with multiple models")
            
            # Try different models for better coverage
            models_to_try = ["prebuilt-layout", "prebuilt-document", "prebuilt-read"]
            best_result = None
            best_confidence = 0.0
            
            for model in models_to_try:
                try:
                    poller = self._document_intelligence_client.begin_analyze_document(
                        model, page_content
                    )
                    result = poller.result()
                    
                    # Extract text
                    extracted_text = ""
                    if hasattr(result, 'paragraphs'):
                        for paragraph in result.paragraphs:
                            extracted_text += paragraph.content + "\n\n"
                    elif hasattr(result, 'pages') and result.pages:
                        page = result.pages[0]
                        if hasattr(page, 'lines'):
                            for line in page.lines:
                                extracted_text += line.content + " "
                            extracted_text += "\n\n"
                        elif hasattr(page, 'content'):
                            extracted_text = page.content + "\n\n"
                    
                    # Check if this model gave better results
                    confidence = getattr(result, 'confidence', 0.0)
                    if len(extracted_text.strip()) > len(best_result.get("extracted_text", "") if best_result else "") or confidence > best_confidence:
                        best_result = {
                            "page_number": page_num,
                            "extracted_text": extracted_text.strip(),
                            "confidence": confidence,
                            "model_used": model,
                            "success": True
                        }
                        best_confidence = confidence
                    
                except Exception as e:
                    logger.debug(f"Model {model} failed for page {page_num}: {e}")
                    continue
            
            if best_result:
                return best_result
            else:
                # Fallback to PyPDF2
                try:
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(page_content))
                    if pdf_reader.pages:
                        fallback_text = pdf_reader.pages[0].extract_text()
                        return {
                            "page_number": page_num,
                            "extracted_text": fallback_text,
                            "confidence": 0.0,
                            "model_used": "PyPDF2_fallback",
                            "success": True
                        }
                except Exception as e:
                    logger.error(f"All extraction methods failed for page {page_num}: {e}")
                
                # Return error result
                return {
                    "page_number": page_num,
                    "extracted_text": "",
                    "confidence": 0.0,
                    "model_used": "all_failed",
                    "success": False,
                    "error_message": f"All extraction methods failed for page {page_num}"
                }
                
        except Exception as e:
            logger.error(f"Error processing page {page_num} with multiple models: {e}")
            return {
                "page_number": page_num,
                "extracted_text": "",
                "confidence": 0.0,
                "model_used": "error",
                "success": False,
                "error_message": str(e)
            } 

    async def analyze_full_document_layout(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Analyze the entire PDF in a single pass using prebuilt-layout and
        build combined text and per-page contents.
        
        Returns a dict with: success, total_pages, extracted_text, page_results,
        processing_timestamp, filename, processing_id, extraction_method.
        """
        try:
            if not self._document_intelligence_client:
                logger.warning("Document Intelligence not available for single-pass extraction, falling back to split-and-extract")
                return await self.split_and_extract_pdf(file_content, filename, extract_per_page=True, combine_results=True)
            
            start_time = datetime.utcnow()
            poller = self._document_intelligence_client.begin_analyze_document(
                "prebuilt-layout", file_content
            )
            result = poller.result()
            
            combined_text = ""
            page_results: List[Dict[str, Any]] = []
            total_pages = 0
            
            # Prefer pages iteration for page-wise grouping
            if hasattr(result, 'pages') and result.pages:
                total_pages = len(result.pages)
                for idx, page in enumerate(result.pages, start=1):
                    page_text = ""
                    if hasattr(page, 'lines') and page.lines:
                        # Concatenate lines without geometric grouping to avoid SDK type differences
                        for line in page.lines:
                            page_text += line.content + "\n"
                        page_text += "\n"
                    elif hasattr(page, 'content') and page.content:
                        page_text = page.content + "\n\n"
                    
                    page_results.append({
                        "page_number": idx,
                        "extracted_text": page_text.strip(),
                        "confidence": getattr(result, 'confidence', 0.0),
                        "model_used": "prebuilt-layout",
                        "success": True
                    })
                    combined_text += f"\n--- Page {idx} (Model: prebuilt-layout) ---\n"
                    combined_text += page_text.strip() + "\n"
            else:
                # Fallback to paragraphs only
                total_pages = 1
                text = ""
                if hasattr(result, 'paragraphs') and result.paragraphs:
                    for paragraph in result.paragraphs:
                        text += paragraph.content + "\n\n"
                page_results.append({
                    "page_number": 1,
                    "extracted_text": text.strip(),
                    "confidence": getattr(result, 'confidence', 0.0),
                    "model_used": "prebuilt-layout",
                    "success": True
                })
                combined_text = f"--- Page 1 (Model: prebuilt-layout) ---\n{text.strip()}\n"
            
            return {
                "success": True,
                "total_pages": total_pages,
                "extracted_text": combined_text.strip(),
                "page_results": page_results,
                "processing_timestamp": datetime.utcnow().isoformat(),
                "filename": filename,
                "processing_id": str(uuid.uuid4()),
                "extraction_method": "single_pass_layout"
            }
        except Exception as e:
            logger.error(f"Single-pass layout analysis failed for {filename}: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_pages": 0,
                "extracted_text": "",
                "page_results": []
            } 