#!/usr/bin/env python3
"""
Comprehensive test flow for the Legal Agent System.
Tests the complete flow from start to finish with various scenarios.
Organized into clear stages for better structure and readability.
Includes dynamic Azure OpenAI chatting and comprehensive logging.
"""

import asyncio
import aiohttp
import json
import time
import os
import sys
import traceback
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.config import config
from tests.logger import TestLogger
from tests.azure_client import azure_client

@dataclass
class TestResult:
    """Test result data class."""
    test_name: str
    success: bool
    duration: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    azure_interaction: Optional[Dict[str, Any]] = None

@dataclass
class StageResult:
    """Stage result data class."""
    stage_name: str
    stage_description: str
    tests: List[TestResult]
    total_tests: int
    passed_tests: int
    failed_tests: int
    stage_duration: float
    success_rate: float

class TestFlowRunner:
    """Comprehensive test flow runner for the Legal Agent System."""
    
    def __init__(self):
        """Initialize the test runner."""
        self.session: Optional[aiohttp.ClientSession] = None
        self.results: List[TestResult] = []
        self.stage_results: List[StageResult] = []
        self.conversation_id: Optional[str] = None
        self.test_start_time = time.time()
        
        # Initialize logger
        self.logger = TestLogger()
        
        # Initialize Azure OpenAI client
        self.azure_client = azure_client
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def log_test(self, test_name: str, message: str, level: str = "INFO"):
        """Log test message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {level}: {test_name} - {message}")
    
    def log_stage(self, stage_key: str, message: str):
        """Log stage message with emoji."""
        emoji = config.STAGE_COLORS.get(stage_key, "📋")
        stage_name = config.TEST_STAGES[stage_key]["name"]
        print(f"\n{emoji} {stage_name}")
        print("=" * (len(stage_name) + 3))
        print(f"📝 {message}")
        print()
    
    async def run_test(self, test_name: str, test_func) -> TestResult:
        """Run a single test and record results with comprehensive logging."""
        start_time = time.time()
        self.log_test(test_name, "Starting test...")
        
        # Log test start
        self.logger.log_test_start(test_name, "current_stage")
        
        try:
            result = await test_func()
            duration = time.time() - start_time
            
            if result:
                self.log_test(test_name, f"✅ PASSED ({duration:.2f}s)")
                
                # Log successful test result
                self.logger.log_test_result(
                    test_name=test_name,
                    stage_name="current_stage",
                    status="PASSED",
                    duration=duration,
                    details=result,
                    azure_interaction=result.get("azure_interaction")
                )
                
                return TestResult(test_name, True, duration, details=result, azure_interaction=result.get("azure_interaction"))
            else:
                self.log_test(test_name, f"❌ FAILED ({duration:.2f}s)")
                
                # Log failed test result
                self.logger.log_test_result(
                    test_name=test_name,
                    stage_name="current_stage",
                    status="FAILED",
                    duration=duration,
                    details={},
                    error_message="Test returned False"
                )
                
                return TestResult(test_name, False, duration, error="Test returned False")
                
        except Exception as e:
            duration = time.time() - start_time
            error_traceback = traceback.format_exc()
            
            self.log_test(test_name, f"❌ FAILED ({duration:.2f}s) - {str(e)}", "ERROR")
            
            # Log error test result
            self.logger.log_test_result(
                test_name=test_name,
                stage_name="current_stage",
                status="ERROR",
                duration=duration,
                details={},
                error_message=str(e),
                error_traceback=error_traceback
            )
            
            return TestResult(test_name, False, duration, error=str(e))
    
    async def run_stage(self, stage_key: str) -> StageResult:
        """Run a complete test stage with comprehensive logging."""
        stage_config = config.TEST_STAGES[stage_key]
        stage_name = stage_config["name"]
        stage_description = stage_config["description"]
        test_methods = stage_config["tests"]
        
        self.log_stage(stage_key, stage_description)
        
        # Start stage logging
        self.logger.start_stage(stage_name, stage_description)
        
        stage_start_time = time.time()
        stage_results = []
        
        # Run all tests in this stage
        for test_method in test_methods:
            if hasattr(self, f"test_{test_method}"):
                test_func = getattr(self, f"test_{test_method}")
                result = await self.run_test(test_method.replace('_', ' ').title(), test_func)
                stage_results.append(result)
                self.results.append(result)
            else:
                self.log_test(test_method, f"❌ Test method 'test_{test_method}' not found", "ERROR")
        
        stage_duration = time.time() - stage_start_time
        passed_tests = sum(1 for r in stage_results if r.success)
        failed_tests = len(stage_results) - passed_tests
        success_rate = (passed_tests / len(stage_results)) * 100 if stage_results else 0
        
        # End stage logging
        self.logger.end_stage(stage_name, stage_description, len(stage_results), passed_tests, stage_duration)
        
        stage_result = StageResult(
            stage_name=stage_name,
            stage_description=stage_description,
            tests=stage_results,
            total_tests=len(stage_results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            stage_duration=stage_duration,
            success_rate=success_rate
        )
        
        self.stage_results.append(stage_result)
        
        # Print stage summary
        print(f"📊 Stage Summary: {passed_tests}/{len(stage_results)} tests passed ({success_rate:.1f}%)")
        print(f"⏱️  Stage Duration: {stage_duration:.2f}s")
        print()
        
        return stage_result

    # ============================================================================
    # STAGE 1: System Setup & Health Check
    # ============================================================================
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Test API health check."""
        async with self.session.get(f"{config.BASE_URL}/health") as response:
            if response.status != 200:
                raise Exception(f"Health check failed: {response.status}")
            
            data = await response.json()
            return {"status": response.status, "data": data}
    
    async def test_create_conversation(self) -> Dict[str, Any]:
        """Test conversation creation."""
        conversation_data = {
            "name": f"Test Flow - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "user_id": config.TEST_USER_ID
        }
        
        async with self.session.post(f"{config.API_BASE}/conversations", json=conversation_data) as response:
            if response.status != 201:
                raise Exception(f"Failed to create conversation: {response.status}")
            
            data = await response.json()
            self.conversation_id = data.get("_id") or data.get("id")
            
            return {
                "conversation_id": self.conversation_id,
                "status": data.get("status"),
                "name": data.get("name")
            }

    # ============================================================================
    # STAGE 2: Initial User Interaction
    # ============================================================================
    
    async def test_initial_chat(self) -> Dict[str, Any]:
        """Test initial chat in waiting_for_claim status with Azure OpenAI analysis."""
        # Generate dynamic query using Azure OpenAI
        scenario_result = self.azure_client.generate_test_scenario("legal_query", "initial_chat")
        user_query = scenario_result.get("response", "كيف نبدأ") if scenario_result.get("success") else "كيف نبدأ"
        
        query_data = {
            "conversation_id": self.conversation_id,
            "user_id": config.TEST_USER_ID,
            "query": user_query
        }
        
        async with self.session.post(f"{config.API_BASE}/agents/query", json=query_data) as response:
            if response.status != 200:
                raise Exception(f"Failed to query agent: {response.status}")
            
            data = await response.json()
            agent_response = data.get('response', '')
            metadata = data.get('metadata', {})
            
            # Analyze response using Azure OpenAI
            analysis_result = self.azure_client.analyze_test_response(
                test_name="initial_chat",
                user_query=user_query,
                agent_response=agent_response,
                expected_keywords=config.LEGAL_ASSISTANCE_KEYWORDS
            )
            
            # Validate response contains legal assistance keywords
            contains_keywords = any(keyword in agent_response for keyword in config.LEGAL_ASSISTANCE_KEYWORDS)
            if not contains_keywords:
                raise Exception("Response does not contain expected legal assistance keywords")
            
            return {
                "response": agent_response[:100] + "...",
                "agent_type": metadata.get('agent_type'),
                "confidence": metadata.get('confidence'),
                "reasoning": metadata.get('reasoning'),
                "contains_keywords": contains_keywords,
                "user_query": user_query,
                "azure_interaction": analysis_result.get("interaction_data"),
                "azure_analysis": analysis_result.get("analysis")
            }
    
    async def test_non_legal_topic_redirection(self) -> Dict[str, Any]:
        """Test redirection for non-legal topics with Azure OpenAI analysis."""
        # Generate dynamic non-legal query using Azure OpenAI
        scenario_result = self.azure_client.generate_test_scenario("non_legal_query", "non_legal_redirection")
        user_query = scenario_result.get("response", "ما هو الطقس اليوم؟") if scenario_result.get("success") else "ما هو الطقس اليوم؟"
        
        query_data = {
            "conversation_id": self.conversation_id,
            "user_id": config.TEST_USER_ID,
            "query": user_query
        }
        
        async with self.session.post(f"{config.API_BASE}/agents/query", json=query_data) as response:
            if response.status != 200:
                raise Exception(f"Failed to query agent: {response.status}")
            
            data = await response.json()
            agent_response = data.get('response', '')
            
            # Analyze response using Azure OpenAI
            analysis_result = self.azure_client.analyze_test_response(
                test_name="non_legal_redirection",
                user_query=user_query,
                agent_response=agent_response,
                expected_keywords=config.REDIRECT_KEYWORDS
            )
            
            # Validate response redirects to legal assistance
            redirects = any(keyword in agent_response for keyword in config.REDIRECT_KEYWORDS)
            if not redirects:
                raise Exception("Response does not redirect to legal assistance")
            
            return {
                "response": agent_response[:100] + "...",
                "redirects_to_legal": redirects,
                "user_query": user_query,
                "azure_interaction": analysis_result.get("interaction_data"),
                "azure_analysis": analysis_result.get("analysis")
            }

    # ============================================================================
    # STAGE 3: Document Processing & Validation
    # ============================================================================
    
    async def test_valid_claim_upload(self) -> Dict[str, Any]:
        """Test uploading a valid claim using the provided PDF."""
        # Read the valid claim PDF from the data directory
        if not os.path.exists(config.VALID_CLAIM_PDF):
            raise Exception(f"Valid claim PDF not found at: {config.VALID_CLAIM_PDF}")
        
        with open(config.VALID_CLAIM_PDF, 'rb') as f:
            file_content = f.read()
        
        # Create form data for file upload
        data = aiohttp.FormData()
        data.add_field('conversation_id', self.conversation_id)
        data.add_field('user_id', config.TEST_USER_ID)
        data.add_field('file', file_content, filename='valid_claim.pdf', content_type='application/pdf')
        
        async with self.session.post(f"{config.API_BASE}/agents/upload-file", data=data) as response:
            if response.status != 200:
                raise Exception(f"Failed to upload valid claim: {response.status}")
            
            data = await response.json()
            
            # Validate the response
            if not data.get('is_valid'):
                raise Exception("Valid claim was not recognized as valid")
            
            validation_score = data.get('metadata', {}).get('validation_score', 0)
            if validation_score < config.EXPECTED_VALIDATION_SCORE_MIN:
                raise Exception(f"Validation score too low: {validation_score}")
            
            return {
                "is_valid": data.get('is_valid'),
                "validation_score": validation_score,
                "case_number": data.get('case_number'),
                "response": data.get('response', '')[:100] + "...",
                "file_url": data.get('file_url'),
                "file_size": len(file_content)
            }
    
    async def test_invalid_claim_upload(self) -> Dict[str, Any]:
        """Test uploading an invalid claim."""
        # Create a simple text file instead of PDF to ensure it's invalid
        invalid_content = b"This is not a valid legal document at all. Just some random text."
        
        # Create form data for file upload
        data = aiohttp.FormData()
        data.add_field('conversation_id', self.conversation_id)
        data.add_field('user_id', config.TEST_USER_ID)
        data.add_field('file', invalid_content, filename='invalid_claim.txt', content_type='text/plain')
        
        async with self.session.post(f"{config.API_BASE}/agents/upload-file", data=data) as response:
            if response.status != 200:
                raise Exception(f"Failed to upload invalid claim: {response.status}")
            
            data = await response.json()
            
            # Validate the response
            if data.get('is_valid'):
                raise Exception("Invalid claim was incorrectly recognized as valid")
            
            return {
                "is_valid": data.get('is_valid'),
                "validation_score": data.get('metadata', {}).get('validation_score', 0),
                "response": data.get('response', '')[:100] + "...",
                "validation_errors": data.get('metadata', {}).get('validation_errors', [])
            }

    # ============================================================================
    # STAGE 4: Attachment Decision Flow
    # ============================================================================
    
    async def test_attachment_decision_accept(self) -> Dict[str, Any]:
        """Test accepting attachment upload."""
        # Create a new conversation for this test to avoid status conflicts
        conversation_data = {
            "name": f"Test Attachment Accept - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "user_id": config.TEST_USER_ID
        }
        
        async with self.session.post(f"{config.API_BASE}/conversations", json=conversation_data) as response:
            if response.status != 201:
                raise Exception(f"Failed to create conversation: {response.status}")
            
            data = await response.json()
            test_conversation_id = data.get("_id") or data.get("id")
        
        # Set status to claim_validated
        status_update = {"status": "claim_validated"}
        async with self.session.put(f"{config.API_BASE}/conversations/{test_conversation_id}/status", json=status_update) as response:
            if response.status != 200:
                raise Exception(f"Failed to update status: {response.status}")
        
        # Test attachment decision
        decision_data = {
            "decision": "accept",
            "reason": "I have supporting documents to upload"
        }
        
        async with self.session.post(f"{config.API_BASE}/conversations/{test_conversation_id}/attachment-decision", json=decision_data) as response:
            if response.status != 200:
                raise Exception(f"Failed to handle attachment decision: {response.status}")
            
            data = await response.json()
            
            if data.get('status') != 'waiting_for_attachments':
                raise Exception(f"Status not updated correctly: {data.get('status')}")
            
            return {
                "status": data.get('status'),
                "name": data.get('name'),
                "user_id": data.get('user_id'),
                "conversation_id": test_conversation_id
            }
    
    async def test_attachment_decision_reject(self) -> Dict[str, Any]:
        """Test rejecting attachment upload."""
        # Create a new conversation for this test to avoid status conflicts
        conversation_data = {
            "name": f"Test Attachment Reject - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "user_id": config.TEST_USER_ID
        }
        
        async with self.session.post(f"{config.API_BASE}/conversations", json=conversation_data) as response:
            if response.status != 201:
                raise Exception(f"Failed to create conversation: {response.status}")
            
            data = await response.json()
            test_conversation_id = data.get("_id") or data.get("id")
        
        # Set status to claim_validated
        status_update = {"status": "claim_validated"}
        async with self.session.put(f"{config.API_BASE}/conversations/{test_conversation_id}/status", json=status_update) as response:
            if response.status != 200:
                raise Exception(f"Failed to update status: {response.status}")
        
        # Test attachment decision
        decision_data = {
            "decision": "reject",
            "reason": "I don't have additional documents"
        }
        
        async with self.session.post(f"{config.API_BASE}/conversations/{test_conversation_id}/attachment-decision", json=decision_data) as response:
            if response.status != 200:
                raise Exception(f"Failed to handle attachment decision: {response.status}")
            
            data = await response.json()
            
            if data.get('status') != 'response_drafting':
                raise Exception(f"Status not updated correctly: {data.get('status')}")
            
            return {
                "status": data.get('status'),
                "name": data.get('name'),
                "user_id": data.get('user_id'),
                "conversation_id": test_conversation_id
            }

    # ============================================================================
    # STAGE 5: Attachment-Focused Interaction
    # ============================================================================
    
    async def test_attachment_chat(self) -> Dict[str, Any]:
        """Test chat in waiting_for_attachments status with Azure OpenAI analysis."""
        # First, set status to waiting_for_attachments
        status_update = {"status": "waiting_for_attachments"}
        async with self.session.put(f"{config.API_BASE}/conversations/{self.conversation_id}/status", json=status_update) as response:
            if response.status != 200:
                raise Exception(f"Failed to update status: {response.status}")
        
        # Generate dynamic attachment query using Azure OpenAI
        scenario_result = self.azure_client.generate_test_scenario("attachment_query", "attachment_chat")
        user_query = scenario_result.get("response", "ما هي المرفقات التي أحتاجها؟") if scenario_result.get("success") else "ما هي المرفقات التي أحتاجها؟"
        
        # Test attachment-related query
        query_data = {
            "conversation_id": self.conversation_id,
            "user_id": config.TEST_USER_ID,
            "query": user_query
        }
        
        async with self.session.post(f"{config.API_BASE}/agents/query", json=query_data) as response:
            if response.status != 200:
                raise Exception(f"Failed to query agent: {response.status}")
            
            data = await response.json()
            agent_response = data.get('response', '')
            metadata = data.get('metadata', {})
            
            # Analyze response using Azure OpenAI
            analysis_result = self.azure_client.analyze_test_response(
                test_name="attachment_chat",
                user_query=user_query,
                agent_response=agent_response,
                expected_keywords=config.ATTACHMENT_KEYWORDS
            )
            
            # Validate response contains attachment keywords
            contains_keywords = any(keyword in agent_response for keyword in config.ATTACHMENT_KEYWORDS)
            if not contains_keywords:
                raise Exception("Response does not contain expected attachment keywords")
            
            return {
                "response": agent_response[:100] + "...",
                "agent_type": metadata.get('agent_type'),
                "confidence": metadata.get('confidence'),
                "reasoning": metadata.get('reasoning'),
                "contains_keywords": contains_keywords,
                "user_query": user_query,
                "azure_interaction": analysis_result.get("interaction_data"),
                "azure_analysis": analysis_result.get("analysis")
            }

    # ============================================================================
    # STAGE 6: System Validation & Error Handling
    # ============================================================================
    
    async def test_status_transitions(self) -> Dict[str, Any]:
        """Test status transitions and validation."""
        # Test various status transitions
        test_transitions = [
            ("waiting_for_claim", "claim_validated"),
            ("claim_validated", "waiting_for_attachments"),
            ("waiting_for_attachments", "response_drafting"),
        ]
        
        results = []
        for from_status, to_status in test_transitions:
            # Set initial status
            status_update = {"status": from_status}
            async with self.session.put(f"{config.API_BASE}/conversations/{self.conversation_id}/status", json=status_update) as response:
                if response.status != 200:
                    results.append({"from": from_status, "to": to_status, "success": False, "error": f"Failed to set {from_status}"})
                    continue
            
            # Test transition
            status_update = {"status": to_status}
            async with self.session.put(f"{config.API_BASE}/conversations/{self.conversation_id}/status", json=status_update) as response:
                success = response.status == 200
                results.append({
                    "from": from_status,
                    "to": to_status,
                    "success": success,
                    "error": None if success else f"Status {response.status}"
                })
        
        return {"transitions": results}
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling scenarios."""
        errors = []
        
        # Test invalid conversation ID
        query_data = {
            "conversation_id": "invalid_id",
            "user_id": config.TEST_USER_ID,
            "query": "test"
        }
        
        async with self.session.post(f"{config.API_BASE}/agents/query", json=query_data) as response:
            if response.status == 400:
                errors.append({"test": "Invalid conversation ID", "success": True})
            else:
                errors.append({"test": "Invalid conversation ID", "success": False, "error": f"Expected 400, got {response.status}"})
        
        # Test invalid attachment decision
        decision_data = {
            "decision": "invalid_decision",
            "reason": "test"
        }
        
        async with self.session.post(f"{config.API_BASE}/conversations/{self.conversation_id}/attachment-decision", json=decision_data) as response:
            if response.status == 400:
                errors.append({"test": "Invalid attachment decision", "success": True})
            else:
                errors.append({"test": "Invalid attachment decision", "success": False, "error": f"Expected 400, got {response.status}"})
        
        return {"error_tests": errors}

    # ============================================================================
    # Main Test Flow Execution
    # ============================================================================
    
    async def run_complete_flow(self):
        """Run the complete test flow organized by stages."""
        print("🚀 Starting Comprehensive Legal Agent Test Flow")
        print("=" * 60)
        print(f"📍 Testing against: {config.BASE_URL}")
        print(f"👤 Test User ID: {config.TEST_USER_ID}")
        print(f"⏱️  Request Timeout: {config.REQUEST_TIMEOUT}s")
        print(f"📄 Using Valid Claim: {config.VALID_CLAIM_PDF}")
        print(f"🤖 Azure OpenAI: {'✅ Configured' if self.azure_client.is_configured else '❌ Not Configured'}")
        print()
        
        # Run all stages in order
        stages = [
            "STAGE_1_SETUP",
            "STAGE_2_INITIAL_INTERACTION", 
            "STAGE_3_DOCUMENT_PROCESSING",
            "STAGE_4_ATTACHMENT_FLOW",
            "STAGE_5_ATTACHMENT_INTERACTION",
            "STAGE_6_SYSTEM_VALIDATION"
        ]
        
        for stage_key in stages:
            await self.run_stage(stage_key)
        
        # Generate comprehensive summary
        await self.generate_summary()
    
    async def generate_summary(self):
        """Generate comprehensive test summary report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        total_duration = time.time() - self.test_start_time
        
        # End session logging
        self.logger.end_session(total_tests, passed_tests, total_duration)
        
        # Get Azure OpenAI usage summary
        azure_usage = self.azure_client.get_usage_summary()
        
        print("=" * 60)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏱️  Total Duration: {total_duration:.2f}s")
        print(f"📈 Overall Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print()
        
        # Azure OpenAI Usage Summary
        if azure_usage["is_configured"]:
            print("🤖 AZURE OPENAI USAGE:")
            print("-" * 30)
            print(f"Total Interactions: {azure_usage['total_interactions']}")
            print(f"Total Tokens Used: {azure_usage['total_tokens_used']}")
            print(f"Average Tokens/Interaction: {azure_usage['average_tokens_per_interaction']:.1f}")
            print()
        
        # Stage-by-stage breakdown
        print("📋 STAGE-BY-STAGE BREAKDOWN:")
        print("-" * 40)
        for stage_result in self.stage_results:
            status_emoji = "✅" if stage_result.success_rate == 100 else "⚠️" if stage_result.success_rate > 80 else "❌"
            print(f"{status_emoji} {stage_result.stage_name}")
            print(f"   📊 {stage_result.passed_tests}/{stage_result.total_tests} tests passed ({stage_result.success_rate:.1f}%)")
            print(f"   ⏱️  Duration: {stage_result.stage_duration:.2f}s")
            print()
        
        if failed_tests > 0:
            print("❌ FAILED TESTS:")
            print("-" * 30)
            for result in self.results:
                if not result.success:
                    print(f"• {result.test_name}: {result.error}")
            print()
        
        print("✅ PASSED TESTS:")
        print("-" * 30)
        for result in self.results:
            if result.success:
                print(f"• {result.test_name} ({result.duration:.2f}s)")
        
        # Log files information
        log_files = self.logger.get_log_files()
        print(f"\n📁 LOG FILES GENERATED:")
        print("-" * 30)
        for log_type, log_path in log_files.items():
            print(f"• {log_type}: {log_path}")
        
        print()
        if failed_tests == 0:
            print("🎉 ALL TESTS PASSED! The Legal Agent System is working perfectly!")
        elif passed_tests / total_tests >= 0.8:
            print(f"🎯 EXCELLENT PERFORMANCE! {passed_tests}/{total_tests} tests passed ({(passed_tests/total_tests)*100:.1f}%)")
        else:
            print(f"⚠️  {failed_tests} test(s) failed. Please review the errors above.")

async def main():
    """Main test function."""
    async with TestFlowRunner() as runner:
        await runner.run_complete_flow()

if __name__ == "__main__":
    asyncio.run(main()) 