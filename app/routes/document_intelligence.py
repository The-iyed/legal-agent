"""
Document Intelligence API Routes

This module provides API endpoints for document analysis using Azure Document Intelligence.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.modules.document_processor.enhanced_document_intelligence import (
    EnhancedDocumentIntelligenceService,
    DocumentModel
)
from app.modules.document_processor.pdf_splitter import PDFSplitterService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/document-intelligence", tags=["Document Intelligence"])


def get_document_intelligence_service() -> EnhancedDocumentIntelligenceService:
    """Get Document Intelligence service instance."""
    return EnhancedDocumentIntelligenceService()


def get_pdf_splitter_service() -> PDFSplitterService:
    """Get PDF Splitter service instance."""
    return PDFSplitterService()


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    model: str = "prebuilt-document",
    features: Optional[List[str]] = None,
    service: EnhancedDocumentIntelligenceService = Depends(get_document_intelligence_service)
) -> Dict[str, Any]:
    """
    Analyze a document using Azure Document Intelligence.
    
    Args:
        file: Document file to analyze
        model: Document analysis model to use
        features: Optional features to enable
        
    Returns:
        Analysis results
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Validate model
        try:
            document_model = DocumentModel(model)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid model. Available models: {[m.value for m in DocumentModel]}"
            )
        
        logger.info(f"Analyzing document {file.filename} with model {model}")
        
        # Analyze document
        result = await service.analyze_document(
            file_content=file_content,
            model=document_model,
            features=features
        )
        
        return {
            "success": True,
            "filename": file.filename,
            "model_used": model,
            "extracted_text": result.extracted_text,
            "confidence": result.confidence,
            "pages": result.pages,
            "key_value_pairs": result.key_value_pairs,
            "form_fields": result.form_fields,
            "processing_time": result.processing_time,
            "document_type": result.document_type
        }
        
    except Exception as e:
        logger.error(f"Document analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Document analysis failed: {str(e)}")


@router.post("/analyze-pdf-enhanced")
async def analyze_pdf_enhanced(
    file: UploadFile = File(...),
    extract_per_page: bool = True,
    combine_results: bool = True,
    service: PDFSplitterService = Depends(get_pdf_splitter_service)
) -> Dict[str, Any]:
    """
    Analyze PDF with enhanced page-by-page processing using Document Intelligence.
    
    Args:
        file: PDF file to analyze
        extract_per_page: Whether to extract text from each page individually
        combine_results: Whether to combine results from all pages
        
    Returns:
        Enhanced analysis results with page-by-page breakdown
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Read file content
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        logger.info(f"Starting enhanced PDF analysis for {file.filename}")
        
        # Process PDF with page splitting
        result = await service.split_and_extract_pdf(
            file_content=file_content,
            filename=file.filename,
            extract_per_page=extract_per_page,
            combine_results=combine_results
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500, 
                detail=f"PDF processing failed: {result.get('error', 'Unknown error')}"
            )
        
        return {
            "success": True,
            "filename": file.filename,
            "total_pages": result.get("total_pages", 0),
            "extracted_text": result.get("extracted_text", ""),
            "page_results": result.get("page_results", []),
            "processing_timestamp": result.get("processing_timestamp"),
            "processing_id": result.get("processing_id"),
            "extraction_method": "page_by_page"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced PDF analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Enhanced PDF analysis failed: {str(e)}")


@router.post("/analyze-pdf-multi-model")
async def analyze_pdf_multi_model(
    file: UploadFile = File(...),
    service: PDFSplitterService = Depends(get_pdf_splitter_service)
) -> Dict[str, Any]:
    """
    Analyze PDF using multiple Document Intelligence models for maximum coverage.
    
    Args:
        file: PDF file to analyze
        
    Returns:
        Analysis results using the best model for each page
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Read file content
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        logger.info(f"Starting multi-model PDF analysis for {file.filename}")
        
        # Process PDF with multiple models
        result = await service.extract_with_multiple_models(
            file_content=file_content,
            filename=file.filename
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500, 
                detail=f"Multi-model PDF processing failed: {result.get('error', 'Unknown error')}"
            )
        
        return {
            "success": True,
            "filename": file.filename,
            "total_pages": result.get("total_pages", 0),
            "extracted_text": result.get("extracted_text", ""),
            "page_results": result.get("page_results", []),
            "processing_timestamp": result.get("processing_timestamp"),
            "processing_id": result.get("processing_id"),
            "extraction_method": "multi_model"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multi-model PDF analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Multi-model PDF analysis failed: {str(e)}")


@router.get("/models")
async def get_available_models() -> Dict[str, Any]:
    """
    Get list of available Document Intelligence models.
    
    Returns:
        List of available models with descriptions
    """
    models = [
        {
            "value": model.value,
            "name": model.name,
            "description": f"Azure Document Intelligence {model.name} model"
        }
        for model in DocumentModel
    ]
    
    return {
        "success": True,
        "models": models,
        "count": len(models)
    }


@router.post("/extract-text-only")
async def extract_text_only(
    file: UploadFile = File(...),
    service: EnhancedDocumentIntelligenceService = Depends(get_document_intelligence_service)
) -> Dict[str, Any]:
    """
    Extract only text content from document.
    
    Args:
        file: Document file to process
        
    Returns:
        Extracted text content
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        logger.info(f"Extracting text from {file.filename}")
        
        # Use layout model for better text extraction
        result = await service.analyze_document(
            file_content=file_content,
            model=DocumentModel.LAYOUT
        )
        
        return {
            "success": True,
            "filename": file.filename,
            "extracted_text": result.extracted_text,
            "confidence": result.confidence,
            "pages": result.pages,
            "processing_time": result.processing_time
        }
        
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}") 