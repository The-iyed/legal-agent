"""
Claim Extractor Module

This module provides specialized functionality for extracting and processing
legal claim information from PDF documents using Azure Document Intelligence
and Azure OpenAI for refinement.
"""

from .service import ClaimExtractorService
from .models import ClaimInfo, ExtractionResult, ProcessingStatus

__all__ = [
    "ClaimExtractorService",
    "ClaimInfo", 
    "ExtractionResult",
    "ProcessingStatus"
] 