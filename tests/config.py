"""
Test configuration for the Legal Agent System.
"""

import os
from typing import Dict, Any

class TestConfig:
    """Configuration for test environment."""
    
    # API Configuration
    BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8017")
    API_BASE = f"{BASE_URL}/api"
    
    # Test User Configuration
    TEST_USER_ID = os.getenv("TEST_USER_ID", "757848baa61")
    
    # Test Data Paths
    TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
    VALID_CLAIM_PDF = os.path.join(TEST_DATA_DIR, "valid_claim.pdf")
    INVALID_CLAIM_PDF = os.path.join(TEST_DATA_DIR, "invalid_claim.pdf")
    SIMPLE_PDF = os.path.join(TEST_DATA_DIR, "simple.pdf")
    
    # Test Timeouts
    REQUEST_TIMEOUT = 30  # seconds
    WAIT_TIMEOUT = 5  # seconds
    
    # Test Validation
    EXPECTED_VALIDATION_SCORE_MIN = 0.7
    EXPECTED_VALIDATION_SCORE_MAX = 1.0
    
    # Test Response Keywords
    LEGAL_ASSISTANCE_KEYWORDS = [
        "صحيفة الدعوى", "رد قانوني", "لائحة الرد", "مساعدتك", "قضية"
    ]
    
    ATTACHMENT_KEYWORDS = [
        "مرفقات", "مستندات", "داعمة", "صحيفة دعواك", "مرحلة جمع"
    ]
    
    REDIRECT_KEYWORDS = [
        "عذراً", "مساعد قانوني", "قضيتك القانونية", "صحيفة دعوى"
    ]
    
    # Test Status Flow
    EXPECTED_STATUS_FLOW = [
        "waiting_for_claim",
        "claim_validated", 
        "waiting_for_attachments",
        "response_drafting"
    ]
    
    # Test Stages Configuration
    TEST_STAGES = {
        "STAGE_1_SETUP": {
            "name": "System Setup & Health Check",
            "description": "Verify system is running and healthy",
            "tests": ["health_check", "create_conversation"]
        },
        "STAGE_2_INITIAL_INTERACTION": {
            "name": "Initial User Interaction",
            "description": "Test initial chat and security features",
            "tests": ["initial_chat", "non_legal_topic_redirection"]
        },
        "STAGE_3_DOCUMENT_PROCESSING": {
            "name": "Document Processing & Validation",
            "description": "Test claim upload and validation",
            "tests": ["valid_claim_upload", "invalid_claim_upload"]
        },
        "STAGE_4_ATTACHMENT_FLOW": {
            "name": "Attachment Decision Flow",
            "description": "Test attachment decision handling",
            "tests": ["attachment_decision_accept", "attachment_decision_reject"]
        },
        "STAGE_5_ATTACHMENT_INTERACTION": {
            "name": "Attachment-Focused Interaction",
            "description": "Test chat in attachment collection mode",
            "tests": ["attachment_chat"]
        },
        "STAGE_6_SYSTEM_VALIDATION": {
            "name": "System Validation & Error Handling",
            "description": "Test status transitions and error scenarios",
            "tests": ["status_transitions", "error_handling"]
        }
    }
    
    # Stage Colors for Output
    STAGE_COLORS = {
        "STAGE_1_SETUP": "🔧",
        "STAGE_2_INITIAL_INTERACTION": "💬",
        "STAGE_3_DOCUMENT_PROCESSING": "📄",
        "STAGE_4_ATTACHMENT_FLOW": "📎",
        "STAGE_5_ATTACHMENT_INTERACTION": "🔍",
        "STAGE_6_SYSTEM_VALIDATION": "✅"
    }

# Global test configuration instance
config = TestConfig() 