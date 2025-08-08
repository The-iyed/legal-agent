"""
Claim Extractor Service

This service provides specialized functionality for extracting claim information
from PDF documents using Azure Document Intelligence and Azure OpenAI.
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

from app.core.config.settings import get_settings
from app.modules.document_processor.enhanced_document_intelligence import (
    EnhancedDocumentIntelligenceService,
    DocumentModel
)
from .models import ClaimInfo, ExtractionResult, ProcessingStatus, PageContent
from .text_processor import TextProcessor
from .openai_refiner import OpenAIRefiner
from .storage_manager import StorageManager
from .validator import ClaimValidator

logger = logging.getLogger(__name__)


class ClaimExtractorService:
    """
    Service for extracting and processing claim information from PDF documents.
    
    This service orchestrates the entire claim extraction process:
    1. Upload file to blob storage
    2. Extract raw text using Azure Document Intelligence
    3. Process and structure the extracted text
    4. Refine results using Azure OpenAI
    5. Validate the extracted information
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.document_intelligence = EnhancedDocumentIntelligenceService()
        self.text_processor = TextProcessor()
        self.openai_refiner = OpenAIRefiner()
        self.storage_manager = StorageManager()
        self.validator = ClaimValidator()
        
        logger.info("ClaimExtractorService initialized successfully")
    
    async def extract_claim_from_pdf(
        self, 
        file_content: bytes, 
        filename: str,
        conversation_id: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract claim information from a PDF file with concurrent processing.
        
        Args:
            file_content: Raw PDF file content
            filename: Original filename
            conversation_id: Optional conversation ID for tracking
            
        Returns:
            ExtractionResult with processed claim information
        """
        # Initialize result
        processing_id = str(uuid.uuid4())
        result = ExtractionResult(
            processing_id=processing_id,
            filename=filename,
            status=ProcessingStatus.PROCESSING
        )
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting concurrent claim extraction for {filename} (ID: {processing_id})")
             
            # Step 1: Upload file (required before other operations)
            result = await self._upload_file(result, file_content, conversation_id)
             
            # Step 2: Extract raw text and process text concurrently
            logger.info(f"Starting concurrent OCR and text processing for {filename}")
            
            # Run OCR extraction and text processing in parallel
            ocr_task = self._extract_raw_text(result, file_content)
            text_processing_task = self._process_text_after_ocr(result)
            
            # Wait for both tasks to complete
            ocr_result, text_processing_result = await asyncio.gather(
                ocr_task, 
                text_processing_task,
                return_exceptions=True
            )
            
            # Handle any exceptions from parallel tasks
            if isinstance(ocr_result, Exception):
                logger.error(f"OCR extraction failed: {ocr_result}")
                raise ocr_result
            if isinstance(text_processing_result, Exception):
                logger.error(f"Text processing failed: {text_processing_result}")
                raise text_processing_result
            
            # Update result with OCR and text processing results
            result = ocr_result
            if text_processing_result.extracted_claim:
                result.extracted_claim = text_processing_result.extracted_claim
            
            # Step 3: Run OpenAI refinement and validation concurrently
            logger.info(f"Starting concurrent OpenAI refinement and validation for {filename}")
            
            refinement_task = self._refine_with_openai(result)
            validation_task = self._validate_claim(result)
            
            # Wait for both tasks to complete
            refinement_result, validation_result = await asyncio.gather(
                refinement_task,
                validation_task,
                return_exceptions=True
            )
            
            # Handle any exceptions from parallel tasks
            if isinstance(refinement_result, Exception):
                logger.error(f"OpenAI refinement failed: {refinement_result}")
                # Continue with validation result if refinement fails
                result = validation_result
            elif isinstance(validation_result, Exception):
                logger.error(f"Validation failed: {validation_result}")
                # Continue with refinement result if validation fails
                result = refinement_result
            else:
                # Both succeeded, merge results
                result = refinement_result
                if validation_result.extracted_claim:
                    result.extracted_claim.is_valid = validation_result.extracted_claim.is_valid
                    result.extracted_claim.validation_errors = validation_result.extracted_claim.validation_errors
            
            processing_time = (datetime.now() - start_time).total_seconds()
            result.processing_time = processing_time
             
            if result.extracted_claim and result.extracted_claim.is_valid:
                result.update_status(ProcessingStatus.VALIDATED)
            else:
                result.update_status(ProcessingStatus.COMPLETED)
            
            logger.info(f"Concurrent claim extraction completed for {filename} in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error extracting claim from {filename}: {e}")
            result.add_error(str(e))
        
        return result
    
    async def _upload_file(
        self, 
        result: ExtractionResult, 
        file_content: bytes,
        conversation_id: Optional[str]
    ) -> ExtractionResult:
        """Upload file to blob storage."""
        try:
            logger.info(f"Uploading file {result.filename} to blob storage")
            
            file_url = await self.storage_manager.upload_file(
                file_content=file_content,
                filename=result.filename,
                conversation_id=conversation_id
            )
            
            result.file_url = file_url
            logger.info(f"File uploaded successfully: {file_url}")
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise Exception(f"File upload failed: {str(e)}")
        
        return result
    
    async def _extract_raw_text(
        self, 
        result: ExtractionResult, 
        file_content: bytes
    ) -> ExtractionResult:
        """Extract raw text using Azure Document Intelligence with enhanced PDF processing."""
        try:
            logger.info(f"Extracting raw text from {result.filename}")
            
            # Check if this is a PDF file for enhanced processing
            if result.filename.lower().endswith('.pdf'):
                logger.info(f"Using enhanced PDF processing for {result.filename}")
                
                # Import the PDF splitter service for enhanced PDF extraction with page details
                from app.modules.document_processor.pdf_splitter import PDFSplitterService
                pdf_splitter = PDFSplitterService()
                
                # Use multi-model extraction to get detailed page information
                # Use a single-pass prebuilt-layout extraction for performance
                extraction_result = await pdf_splitter.analyze_full_document_layout(
                    file_content,
                    result.filename
                )
                
                if extraction_result.get("success"):
                    # Store the combined text
                    result.raw_text = extraction_result.get("extracted_text", "")
                    result.raw_text_length = len(result.raw_text)
                    result.document_intelligence_confidence = 0.95  # High confidence for enhanced extraction
                    
                    # Store individual page contents
                    page_results = extraction_result.get("page_results", [])
                    for page_data in page_results:
                        page_content = PageContent(
                            page_number=page_data.get("page_number", 0),
                            extracted_text=page_data.get("extracted_text", ""),
                            confidence=page_data.get("confidence", 0.0),
                            model_used=page_data.get("model_used", "unknown"),
                            processing_time=page_data.get("processing_time"),
                            key_value_pairs=page_data.get("key_value_pairs", {}),
                            form_fields=page_data.get("form_fields", {}),
                            success=page_data.get("success", True),
                            error_message=page_data.get("error_message")
                        )
                        result.page_contents.append(page_content)
                    
                    # Update claim info with document metadata
                    if result.extracted_claim is None:
                        result.extracted_claim = ClaimInfo()
                    
                    result.extracted_claim.total_pages = extraction_result.get("total_pages", len(page_results))
                    result.extracted_claim.document_type = "صحيفة دعوى"
                    
                    logger.info(f"Enhanced PDF text extracted: {len(result.raw_text)} characters from {len(page_results)} pages")
                    
                else:
                    # Fallback to document processor service
                    from app.modules.document_processor.service import DocumentProcessorService
                    doc_processor = DocumentProcessorService()
                    
                    extracted_text = await doc_processor._extract_pdf_with_page_splitting(
                        file_content, 
                        result.filename
                    )
                    
                    result.raw_text = extracted_text
                    result.raw_text_length = len(extracted_text)
                    result.document_intelligence_confidence = 0.85  # Lower confidence for fallback
                    
                    # Update claim info with document metadata
                    if result.extracted_claim is None:
                        result.extracted_claim = ClaimInfo()
                    
                    # Estimate pages based on text length (rough approximation)
                    estimated_pages = max(1, len(extracted_text) // 2000)  # ~2000 chars per page
                    result.extracted_claim.total_pages = estimated_pages
                    result.extracted_claim.document_type = "صحيفة دعوى"
                    
                    logger.info(f"Fallback PDF text extracted: {len(extracted_text)} characters")
                
            else:
                # Use original method for non-PDF files
                # Use layout model as primary for structured forms
                layout_result = await self.document_intelligence.analyze_document(
                    file_content=file_content,
                    model=DocumentModel.LAYOUT
                )
                
                # Use document model as backup for comprehensive text extraction
                doc_result = await self.document_intelligence.analyze_document(
                    file_content=file_content,
                    model=DocumentModel.DOCUMENT
                )
                
                # Prioritize layout results for structured forms, fallback to document
                combined_text = layout_result.extracted_text
                if not combined_text or len(combined_text) < 100:
                    combined_text = doc_result.extracted_text
                
                result.raw_text = combined_text
                result.raw_text_length = len(combined_text)
                result.document_intelligence_confidence = max(
                    doc_result.confidence, 
                    layout_result.confidence
                )
                
                # Create a single page content for non-PDF files
                page_content = PageContent(
                    page_number=1,
                    extracted_text=combined_text,
                    confidence=result.document_intelligence_confidence,
                    model_used="layout_document_combined",
                    success=True
                )
                result.page_contents.append(page_content)
                
                # Update claim info with document metadata
                if result.extracted_claim is None:
                    result.extracted_claim = ClaimInfo()
                
                result.extracted_claim.total_pages = max(doc_result.pages, layout_result.pages)
                result.extracted_claim.document_type = "صحيفة دعوى"
                
                logger.info(f"Raw text extracted: {len(combined_text)} characters")
            
        except Exception as e:
            logger.error(f"Failed to extract raw text: {e}")
            raise Exception(f"Text extraction failed: {str(e)}")
        
        return result
    
    async def _process_text(self, result: ExtractionResult) -> ExtractionResult:
        """Process and structure the extracted text."""
        try:
            logger.info(f"Processing text for {result.filename}")
            
            if not result.raw_text:
                raise Exception("No raw text available for processing")
            
            # Process the text to extract structured information
            structured_data = await self.text_processor.extract_structured_data(
                result.raw_text
            )
            
            # Update claim info with structured data
            if result.extracted_claim is None:
                result.extracted_claim = ClaimInfo()
            
            # Map structured data to claim fields
            for field, value in structured_data.items():
                if hasattr(result.extracted_claim, field) and value:
                    setattr(result.extracted_claim, field, value)
            
            # Ensure case type is properly set
            if not result.extracted_claim.case_type:
                if "اداريه" in result.raw_text or "إدارية" in result.raw_text:
                    result.extracted_claim.case_type = "دعوى إدارية"
                elif "تجاريه" in result.raw_text or "تجارية" in result.raw_text:
                    result.extracted_claim.case_type = "دعوى تجارية"
                elif "جنائيه" in result.raw_text or "جنائية" in result.raw_text:
                    result.extracted_claim.case_type = "دعوى جنائية"
                else:
                    result.extracted_claim.case_type = "دعوى مدنية"
            
            # Set case subject if not available
            if not result.extracted_claim.case_subject:
                if "مخالفة" in result.raw_text or "مخالف" in result.raw_text:
                    result.extracted_claim.case_subject = "طلب إلغاء قرار إداري"
                elif "تعويض" in result.raw_text:
                    result.extracted_claim.case_subject = "طلب تعويض"
                else:
                    result.extracted_claim.case_subject = "طلب قانوني"
            
            logger.info(f"Text processing completed for {result.filename}")
            
        except Exception as e:
            logger.error(f"Failed to process text: {e}")
            raise Exception(f"Text processing failed: {str(e)}")
        
        return result

    async def _process_text_after_ocr(self, result: ExtractionResult) -> ExtractionResult:
        """
        Process text concurrently with OCR extraction.
        This method waits for OCR to complete and then processes the text.
        """
        try:
            logger.info(f"Starting concurrent text processing for {result.filename}")
            
            # Wait for OCR to complete by checking for raw_text
            max_wait_time = 60  # Maximum wait time in seconds
            wait_interval = 0.5  # Check every 0.5 seconds
            waited_time = 0
            
            while not result.raw_text and waited_time < max_wait_time:
                await asyncio.sleep(wait_interval)
                waited_time += wait_interval
            
            if not result.raw_text:
                logger.warning(f"OCR extraction timeout for {result.filename}, proceeding with empty text")
                # Create empty claim info
                if result.extracted_claim is None:
                    result.extracted_claim = ClaimInfo()
                return result
            
            # Process the text to extract structured information
            structured_data = await self.text_processor.extract_structured_data(
                result.raw_text
            )
            
            # Update claim info with structured data
            if result.extracted_claim is None:
                result.extracted_claim = ClaimInfo()
            
            # Map structured data to claim fields
            for field, value in structured_data.items():
                if hasattr(result.extracted_claim, field) and value:
                    setattr(result.extracted_claim, field, value)
            
            # Ensure case type is properly set
            if not result.extracted_claim.case_type:
                if "اداريه" in result.raw_text or "إدارية" in result.raw_text:
                    result.extracted_claim.case_type = "دعوى إدارية"
                elif "تجاريه" in result.raw_text or "تجارية" in result.raw_text:
                    result.extracted_claim.case_type = "دعوى تجارية"
                elif "جنائيه" in result.raw_text or "جنائية" in result.raw_text:
                    result.extracted_claim.case_type = "دعوى جنائية"
                else:
                    result.extracted_claim.case_type = "دعوى مدنية"
            
            # Set case subject if not available
            if not result.extracted_claim.case_subject:
                if "مخالفة" in result.raw_text or "مخالف" in result.raw_text:
                    result.extracted_claim.case_subject = "طلب إلغاء قرار إداري"
                elif "تعويض" in result.raw_text:
                    result.extracted_claim.case_subject = "طلب تعويض"
                else:
                    result.extracted_claim.case_subject = "طلب قانوني"
            
            logger.info(f"Concurrent text processing completed for {result.filename}")
            
        except Exception as e:
            logger.error(f"Failed to process text concurrently: {e}")
            # Create empty claim info on error
            if result.extracted_claim is None:
                result.extracted_claim = ClaimInfo()
        
        return result
    
    async def _refine_with_openai(self, result: ExtractionResult) -> ExtractionResult:
        """Refine extracted information using Azure OpenAI."""
        try:
            logger.info(f"Refining results with OpenAI for {result.filename}")
            
            if not result.raw_text:
                raise Exception("No raw text available for refinement")
            
            # Generate claim overview for user-friendly explanation only (skip separate refinement to save time)
            if result.extracted_claim:
                claim_overview = await self.openai_refiner.generate_claim_overview(
                    raw_text=result.raw_text,
                    extracted_claim=result.extracted_claim
                )
                result.extracted_claim.claim_overview = claim_overview
                logger.info(f"Claim overview generated for {result.filename}")
            
            logger.info(f"OpenAI claim overview completed for {result.filename}")
            
        except Exception as e:
            logger.error(f"Failed to refine with OpenAI: {e}")
            # Don't fail the entire process if OpenAI refinement fails
            # Skip refined_response path for speed; still try to generate basic overview
            if result.extracted_claim:
                try:
                    claim_overview = await self.openai_refiner.generate_claim_overview(
                        raw_text=result.raw_text,
                        extracted_claim=result.extracted_claim
                    )
                    result.extracted_claim.claim_overview = claim_overview
                except Exception as overview_error:
                    logger.error(f"Failed to generate claim overview: {overview_error}")
        
        return result
    
    async def _validate_claim(self, result: ExtractionResult) -> ExtractionResult:
        """Validate the extracted claim information."""
        try:
            logger.info(f"Validating claim for {result.filename}")
            
            if not result.extracted_claim:
                raise Exception("No claim information to validate")
            
            # Validate the claim
            validation_result = await self.validator.validate_claim(
                result.extracted_claim
            )
            
            # Update claim with validation results
            result.extracted_claim.is_valid = validation_result.is_valid
            result.extracted_claim.validation_errors = validation_result.errors
            result.extracted_claim.processing_confidence = validation_result.confidence
            
            logger.info(f"Claim validation completed for {result.filename}")
            
        except Exception as e:
            logger.error(f"Failed to validate claim: {e}")
            # Don't fail the entire process if validation fails
            if result.extracted_claim:
                result.extracted_claim.is_valid = False
                result.extracted_claim.validation_errors = [str(e)]
        
        return result
    
    async def get_extraction_status(self, processing_id: str) -> Optional[ExtractionResult]:
        """Get the status of a claim extraction process."""
        try:
            # This would typically query a database or cache
            # For now, we'll return None as we don't have persistent storage
            logger.info(f"Getting extraction status for {processing_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get extraction status: {e}")
            return None
    
    async def get_extraction_history(
        self, 
        conversation_id: Optional[str] = None,
        limit: int = 10
    ) -> list[ExtractionResult]:
        """Get extraction history for a conversation."""
        try:
            # This would typically query a database
            # For now, we'll return an empty list
            logger.info(f"Getting extraction history for conversation {conversation_id}")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get extraction history: {e}")
            return [] 