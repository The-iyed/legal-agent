"""
Claim Extractor API Routes

This module provides dedicated API endpoints for testing and using the claim extractor
module functionality.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging
import asyncio
from datetime import datetime

from app.modules.claim_extractor import (
    ClaimExtractorService,
    ClaimInfo,
    ExtractionResult,
    ProcessingStatus
)
from app.modules.claim_extractor.text_processor import TextProcessor
from app.modules.claim_extractor.openai_refiner import OpenAIRefiner
from app.modules.claim_extractor.storage_manager import StorageManager
from app.modules.claim_extractor.validator import ClaimValidator, ValidationResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/claim-extractor", tags=["Claim Extractor"])


def get_claim_extractor_service() -> ClaimExtractorService:
    """Dependency to get claim extractor service."""
    return ClaimExtractorService()


def get_text_processor() -> TextProcessor:
    """Dependency to get text processor."""
    return TextProcessor()


def get_openai_refiner() -> OpenAIRefiner:
    """Dependency to get OpenAI refiner."""
    return OpenAIRefiner()


def get_storage_manager() -> StorageManager:
    """Dependency to get storage manager."""
    return StorageManager()


def get_validator() -> ClaimValidator:
    """Dependency to get validator."""
    return ClaimValidator()


@router.post("/extract")
async def extract_claim_from_pdf(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = None,
    service: ClaimExtractorService = Depends(get_claim_extractor_service)
) -> Dict[str, Any]:
    """
    Extract claim information from a PDF file.
    
    This endpoint provides the complete claim extraction pipeline:
    1. Upload file to blob storage
    2. Extract raw text using Azure Document Intelligence
    3. Process and structure the text
    4. Refine using OpenAI
    5. Validate the extracted information
    
    Args:
        file: PDF file to process
        conversation_id: Optional conversation ID for organization
        service: Claim extractor service
        
    Returns:
        Complete extraction results with all metadata
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Check file size (limit to 10MB)
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File size too large. Maximum size is 10MB."
            )
        
        logger.info(f"Starting claim extraction for {file.filename}")
        
        # Extract claim information
        result = await service.extract_claim_from_pdf(
            file_content=file_content,
            filename=file.filename,
            conversation_id=conversation_id
        )
        
        # Prepare response
        response = {
            "status": "success",
            "processing_id": result.processing_id,
            "filename": result.filename,
            "extraction_status": result.status.value,
            "processing_time": result.processing_time,
            "file_url": result.file_url,
            "error_message": result.error_message,
            "created_at": result.created_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None
        }
        
        # Add complete raw text (not truncated)
        if result.raw_text:
            response["raw_text"] = result.raw_text
            response["raw_text_length"] = len(result.raw_text)
        
        # Add individual page contents
        if result.page_contents:
            response["page_contents"] = []
            for page_content in result.page_contents:
                page_info = {
                    "page_number": page_content.page_number,
                    "extracted_text": page_content.extracted_text,
                    "text_length": len(page_content.extracted_text),
                    "confidence": page_content.confidence,
                    "model_used": page_content.model_used,
                    "success": page_content.success,
                    "processing_time": page_content.processing_time
                }
                if page_content.error_message:
                    page_info["error_message"] = page_content.error_message
                response["page_contents"].append(page_info)
         
        if result.extracted_claim:
            essential_fields = {
                "case_number": result.extracted_claim.case_number,
                "plaintiff_name": result.extracted_claim.plaintiff_name,
                "defendant_name": result.extracted_claim.defendant_name,
                "case_type": result.extracted_claim.case_type,
                "claim_overview": result.extracted_claim.claim_overview,
                "claim_amount": result.extracted_claim.claim_amount,
                "currency": result.extracted_claim.currency
            }
            response["extracted_claim"] = {k: v for k, v in essential_fields.items() if v}
            response["is_valid"] = result.extracted_claim.is_valid
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting claim: {e}")
        raise HTTPException(status_code=500, detail=f"Claim extraction failed: {str(e)}")


@router.post("/process-text")
async def process_text_only(
    text: str,
    processor: TextProcessor = Depends(get_text_processor)
) -> Dict[str, Any]:
    """
    Process raw text to extract structured claim information.
    
    This endpoint tests only the text processing component without
    requiring a PDF file or Azure services.
    
    Args:
        text: Raw text to process
        processor: Text processor service
        
    Returns:
        Structured data extracted from text
    """
    try:
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="No text provided")
        
        logger.info("Processing text for structured data extraction")
        
        # Extract structured data
        structured_data = await processor.extract_structured_data(text)
        
        # Extract text sections
        sections = processor.extract_text_sections(text)
        
        response = {
            "status": "success",
            "extracted_fields": len(structured_data),
            "field_names": list(structured_data.keys()),
            "structured_data": structured_data,
            "sections": {
                name: content[:500] + "..." if len(content) > 500 else content
                for name, content in sections.items()
            },
            "sections_count": len(sections)
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        raise HTTPException(status_code=500, detail=f"Text processing failed: {str(e)}")


@router.post("/refine")
async def refine_with_openai(
    raw_text: str,
    extracted_claim: Optional[Dict[str, Any]] = None,
    refiner: OpenAIRefiner = Depends(get_openai_refiner)
) -> Dict[str, Any]:
    """
    Refine extracted information using Azure OpenAI.
    
    This endpoint tests the OpenAI refinement component.
    
    Args:
        raw_text: Raw text extracted from document
        extracted_claim: Optional structured claim data
        refiner: OpenAI refiner service
        
    Returns:
        Refined response and analysis
    """
    try:
        if not raw_text or not raw_text.strip():
            raise HTTPException(status_code=400, detail="No text provided")
        
        logger.info("Refining information with OpenAI")
        
        # Convert dict to ClaimInfo if provided
        claim_info = None
        if extracted_claim:
            try:
                claim_info = ClaimInfo(**extracted_claim)
            except Exception as e:
                logger.warning(f"Invalid claim data provided: {e}")
        
        # Refine with OpenAI
        refined_response = await refiner.refine_claim_extraction(raw_text, claim_info)
        
        # Generate claim overview
        claim_overview = await refiner.generate_claim_overview(raw_text, claim_info)
        
        # Generate legal summary if claim info is available
        legal_summary = ""
        if claim_info:
            legal_summary = await refiner.generate_legal_summary(claim_info)
        
        # Enhanced analysis
        enhanced_analysis = await refiner.enhance_claim_analysis(claim_info) if claim_info else {"enhancement": "No claim data provided"}
        
        response = {
            "status": "success",
            "claim_overview": claim_overview,
            "openai_available": refiner.client is not None
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error refining with OpenAI: {e}")
        raise HTTPException(status_code=500, detail=f"OpenAI refinement failed: {str(e)}")


@router.post("/generate-overview")
async def generate_claim_overview(
    raw_text: str,
    extracted_claim: Optional[Dict[str, Any]] = None,
    refiner: OpenAIRefiner = Depends(get_openai_refiner)
) -> Dict[str, Any]:
    """
    Generate a user-friendly claim overview.
    
    This endpoint specifically generates a clear explanation of the claim
    for users to understand the case better.
    
    Args:
        raw_text: Raw text extracted from document
        extracted_claim: Optional structured claim data
        refiner: OpenAI refiner service
        
    Returns:
        Claim overview and metadata
    """
    try:
        if not raw_text or not raw_text.strip():
            raise HTTPException(status_code=400, detail="No text provided")
        
        logger.info("Generating claim overview")
        
        # Convert dict to ClaimInfo if provided
        claim_info = None
        if extracted_claim:
            try:
                claim_info = ClaimInfo(**extracted_claim)
            except Exception as e:
                logger.warning(f"Invalid claim data provided: {e}")
        
        # Generate claim overview
        claim_overview = await refiner.generate_claim_overview(raw_text, claim_info)
        
        response = {
            "status": "success",
            "claim_overview": claim_overview,
            "openai_available": refiner.client is not None
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating claim overview: {e}")
        raise HTTPException(status_code=500, detail=f"Claim overview generation failed: {str(e)}")


@router.post("/validate")
async def validate_claim_data(
    claim_data: Dict[str, Any],
    validator: ClaimValidator = Depends(get_validator)
) -> Dict[str, Any]:
    """
    Validate extracted claim information.
    
    This endpoint tests the validation component.
    
    Args:
        claim_data: Claim information to validate
        validator: Claim validator service
        
    Returns:
        Validation results and scores
    """
    try:
        logger.info("Validating claim data")
        
        # Convert dict to ClaimInfo
        try:
            claim_info = ClaimInfo(**claim_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid claim data: {str(e)}")
        
        # Validate claim
        validation_result = await validator.validate_claim(claim_info)
        
        # Get validation summary
        summary = validator.get_validation_summary(validation_result)
        
        response = {
            "status": "success",
            "validation_result": {
                "is_valid": validation_result.is_valid,
                "confidence": validation_result.confidence,
                "score": validation_result.score,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings
            },
            "summary": summary,
            "claim_info": claim_info.dict()
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating claim: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/upload-test")
async def test_file_upload(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = None,
    storage: StorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    Test file upload to Azure Blob Storage.
    
    This endpoint tests only the storage component.
    
    Args:
        file: File to upload
        conversation_id: Optional conversation ID
        storage: Storage manager service
        
    Returns:
        Upload results and file information
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        logger.info(f"Testing file upload for {file.filename}")
        
        # Upload file
        file_url = await storage.upload_file(
            file_content=file_content,
            filename=file.filename,
            conversation_id=conversation_id
        )
        
        # Get file metadata
        metadata = await storage.get_file_metadata(file_url)
        
        # List files
        files = await storage.list_files(conversation_id=conversation_id)
        
        response = {
            "status": "success",
            "filename": file.filename,
            "file_url": file_url,
            "file_size": len(file_content),
            "metadata": metadata,
            "files_count": len(files),
            "storage_available": storage.is_storage_available(),
            "storage_info": storage.get_storage_info()
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error testing file upload: {e}")
        raise HTTPException(status_code=500, detail=f"File upload test failed: {str(e)}")


@router.get("/health")
async def health_check(
    service: ClaimExtractorService = Depends(get_claim_extractor_service),
    storage: StorageManager = Depends(get_storage_manager),
    refiner: OpenAIRefiner = Depends(get_openai_refiner)
) -> Dict[str, Any]:
    """
    Health check for all claim extractor components.
    
    Returns:
        Health status of all components
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "claim_extractor_service": "healthy",
                "text_processor": "healthy",
                "openai_refiner": "healthy" if refiner.client else "unavailable",
                "storage_manager": "healthy" if storage.is_storage_available() else "unavailable",
                "validator": "healthy"
            },
            "services": {
                "azure_document_intelligence": "available" if service.document_intelligence.client else "unavailable",
                "azure_openai": "available" if refiner.client else "unavailable",
                "azure_storage": "available" if storage.is_storage_available() else "unavailable"
            }
        }
        
        # Check if any critical component is unavailable
        unavailable_components = [
            name for name, status in health_status["components"].items()
            if status == "unavailable"
        ]
        
        if unavailable_components:
            health_status["status"] = "degraded"
            health_status["unavailable_components"] = unavailable_components
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/sample-data")
async def get_sample_data() -> Dict[str, Any]:
    """
    Get sample claim data for testing.
    
    Returns:
        Sample claim data in various formats
    """
    sample_claim = {
        "case_number": "1383951",
        "claim_number": "1383951",
        "filing_date": "2024/03/19",
        "plaintiff_name": "عبير احمد سعيد العمودي",
        "plaintiff_id": "1234567890",
        "plaintiff_mobile": "0548006700",
        "plaintiff_email": "maabeer@gmail.com",
        "plaintiff_address": "الرياض، المملكة العربية السعودية",
        "defendant_name": "أمانة منطقة الرياض",
        "defendant_type": "جهة حكومية",
        "defendant_id": "9876543210",
        "court_name": "المحكمة الإدارية بالرياض",
        "court_type": "إدارية",
        "court_location": "الرياض",
        "case_type": "دعوى إدارية",
        "case_subject": "طلب إلغاء قرار إداري",
        "case_facts": "تتعلق القضية بقرار إداري صادر من الجهة المختصة",
        "case_requests": "إلغاء القرار الإداري والتعويض عن الأضرار",
        "claim_overview": "دعوى إدارية مقدمة من عبير احمد سعيد العمودي ضد أمانة منطقة الرياض، تطلب إلغاء قرار إداري والتعويض عن الأضرار بمبلغ 50000 ريال سعودي",
        "decision_number": "000003657846",
        "appeal_number": "3805482",
        "violation_number": "10000003657846",
        "claim_amount": "50000",
        "currency": "ريال سعودي"
    }
    
    sample_text = """
    صحيفة الدعوى
    
    بيانات صحيفة الدعوى:
    رقم الطلب: ١٣٨٣٩٥١
    التاريخ: ١٤٤٤/٠٣/١٩
    اسم المدعي: عبير احمد سعيد العمودي
    اسم المدعى عليه: أمانة منطقة الرياض
    رقم الجوال: ٠٥٤٨٠٠٦٧٠٠
    البريد الإلكتروني: maabeer@gmail.com
    
    معلومات المحكمة:
    المحكمة: المحكمة الإدارية بالرياض
    نوع الدعوى: دعوى إدارية
    موضوع الدعوى: طلب إلغاء قرار إداري
    
    معلومات اضافية:
    رقم القرار: ٠٠٠٠٠٣٦٥٧٨٤٦
    رقم التظلم: ٣٨٠٥٤٨٢
    رقم المخالفة: ١٠٠٠٠٠٠٣٦٥٧٨٤٦
    
    وقائع الدعوى:
    تتعلق القضية بقرار إداري صادر من الجهة المختصة
    
    الطلب:
    إلغاء القرار الإداري والتعويض عن الأضرار
    """
    
    sample_overview = "دعوى إدارية مقدمة من عبير احمد سعيد العمودي ضد أمانة منطقة الرياض، تطلب إلغاء قرار إداري والتعويض عن الأضرار بمبلغ 50000 ريال سعودي."

    return {
        "sample_claim": sample_claim,
        "sample_text": sample_text,
        "sample_overview": sample_overview,
        "usage_examples": {
            "process_text": "POST /api/v1/claim-extractor/process-text with sample_text",
            "validate": "POST /api/v1/claim-extractor/validate with sample_claim",
            "refine": "POST /api/v1/claim-extractor/refine with sample_text and sample_claim",
            "generate_overview": "POST /api/v1/claim-extractor/generate-overview with sample_text and sample_claim",
            "extract": "POST /api/v1/claim-extractor/extract with a PDF file"
        }
    } 