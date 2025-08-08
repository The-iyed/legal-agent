#!/usr/bin/env python3
"""
Azure Services Test Script

This script tests Azure OpenAI and Document Intelligence services
to ensure they are properly configured and working.
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import json

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.config.settings import get_settings
from azure.storage.blob import BlobServiceClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AzureServicesTester:
    """Test Azure OpenAI and Document Intelligence services."""
    
    def __init__(self):
        self.settings = get_settings()
        self.test_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "azure_openai": {},
            "document_intelligence": {},
            "storage": {},
            "overall_status": "unknown"
        }
    
    def test_environment_variables(self) -> Dict[str, Any]:
        """Test if all required environment variables are set."""
        logger.info("🔍 Testing environment variables...")
        
        required_vars = {
            "AZURE_OPENAI_ENDPOINT": "Azure OpenAI endpoint",
            "AZURE_OPENAI_API_KEY": "Azure OpenAI API key",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "Azure OpenAI deployment name",
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT": "Document Intelligence endpoint",
            "AZURE_DOCUMENT_INTELLIGENCE_API_KEY": "Document Intelligence API key",
            "AZURE_STORAGE_CONNECTION_STRING": "Azure Storage connection string",
            "AZURE_STORAGE_CONTAINER_NAME": "Azure Storage container name"
        }
        
        missing_vars = []
        present_vars = []
        
        for var_name, description in required_vars.items():
            value = os.getenv(var_name)
            if value:
                present_vars.append(f"✅ {var_name}: {description}")
                # Mask sensitive values
                if "KEY" in var_name or "CONNECTION_STRING" in var_name:
                    logger.info(f"✅ {var_name}: {description} (***masked***)")
                else:
                    logger.info(f"✅ {var_name}: {description} ({value})")
            else:
                missing_vars.append(f"❌ {var_name}: {description}")
                logger.warning(f"❌ {var_name}: {description} (NOT SET)")
        
        result = {
            "status": "ok" if not missing_vars else "missing_variables",
            "present_variables": present_vars,
            "missing_variables": missing_vars,
            "total_required": len(required_vars),
            "total_present": len(present_vars)
        }
        
        logger.info(f"Environment variables: {len(present_vars)}/{len(required_vars)} present")
        return result
    
    def test_azure_openai(self) -> Dict[str, Any]:
        """Test Azure OpenAI service."""
        logger.info("🤖 Testing Azure OpenAI...")
        
        try:
            # Check if required variables are set
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
            
            if not endpoint or not api_key:
                return {
                    "status": "error",
                    "message": "Azure OpenAI endpoint or API key not configured",
                    "details": "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables"
                }
            
            # Initialize Azure OpenAI client
            client = AzureOpenAI(
                api_key=api_key,
                api_version="2024-11-20",
                azure_endpoint=endpoint
            )
            
            # Test simple completion
            logger.info(f"Testing Azure OpenAI with deployment: {deployment_name}")
            
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Respond with 'Azure OpenAI is working correctly' in Arabic."},
                    {"role": "user", "content": "Test message"}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            response_text = response.choices[0].message.content
            logger.info(f"✅ Azure OpenAI response: {response_text}")
            
            return {
                "status": "success",
                "message": "Azure OpenAI is working correctly",
                "deployment": deployment_name,
                "response": response_text,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            error_msg = f"Azure OpenAI test failed: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "details": str(e)
            }
    
    def test_document_intelligence(self) -> Dict[str, Any]:
        """Test Document Intelligence service."""
        logger.info("📄 Testing Document Intelligence...")
        
        try:
            # Check if required variables are set
            endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
            api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
            
            if not endpoint or not api_key:
                return {
                    "status": "error",
                    "message": "Document Intelligence endpoint or API key not configured",
                    "details": "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_API_KEY environment variables"
                }
            
            # Initialize Document Intelligence client
            client = DocumentAnalysisClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(api_key)
            )
            
            # Create a simple test document (text content)
            test_content = """
            Test Document
            
            This is a test document for Document Intelligence.
            
            Sample Text:
            رقم الطلب: 123456789
            التاريخ: 2024/01/01
            اسم المدعي: Test User
            """
            
            # Convert to bytes
            test_bytes = test_content.encode('utf-8')
            
            logger.info("Testing Document Intelligence with sample text...")
            
            # Test document analysis
            poller = client.begin_analyze_document(
                "prebuilt-document", test_bytes
            )
            result = poller.result()
            
            # Extract basic information
            extracted_text = ""
            if hasattr(result, 'content'):
                extracted_text = result.content
            elif hasattr(result, 'pages') and result.pages:
                for page in result.pages:
                    if hasattr(page, 'lines'):
                        page_text = "\n".join([line.content for line in page.lines])
                        extracted_text += page_text + "\n"
            
            logger.info(f"✅ Document Intelligence extracted text: {extracted_text[:100]}...")
            
            return {
                "status": "success",
                "message": "Document Intelligence is working correctly",
                "extracted_text_length": len(extracted_text),
                "extracted_text_preview": extracted_text[:200],
                "total_pages": len(result.pages) if hasattr(result, 'pages') else 1
            }
            
        except Exception as e:
            error_msg = f"Document Intelligence test failed: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "details": str(e)
            }
    
    def test_azure_storage(self) -> Dict[str, Any]:
        """Test Azure Storage service."""
        logger.info("💾 Testing Azure Storage...")
        
        try:
            # Check if required variables are set
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
            
            if not connection_string:
                return {
                    "status": "error",
                    "message": "Azure Storage connection string not configured",
                    "details": "Set AZURE_STORAGE_CONNECTION_STRING environment variable"
                }
            
            # Initialize blob service client
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            
            # Test connection by listing containers
            containers = list(blob_service_client.list_containers(max_results=5))
            logger.info(f"✅ Found {len(containers)} containers in storage account")
            
            # Test specific container if provided
            container_status = "not_specified"
            if container_name:
                try:
                    container_client = blob_service_client.get_container_client(container_name)
                    properties = container_client.get_container_properties()
                    container_status = "exists"
                    logger.info(f"✅ Container '{container_name}' exists and is accessible")
                except Exception as e:
                    container_status = "not_found"
                    logger.warning(f"⚠️ Container '{container_name}' not found: {str(e)}")
            
            return {
                "status": "success",
                "message": "Azure Storage is working correctly",
                "total_containers": len(containers),
                "container_names": [c.name for c in containers],
                "target_container": container_name,
                "target_container_status": container_status
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Azure Storage test failed: {error_msg}")
            
            # Handle specific Azure Storage errors
            if "AccountIsDisabled" in error_msg:
                return {
                    "status": "error",
                    "message": "Azure Storage account is disabled",
                    "details": "The storage account has been deactivated. You need to reactivate it in the Azure portal.",
                    "error_code": "AccountIsDisabled",
                    "recommendations": [
                        "Go to Azure Portal > Storage accounts",
                        "Find your storage account",
                        "Click 'Reactivate' or 'Enable'",
                        "Wait for the account to become active (may take a few minutes)",
                        "If reactivation is not available, create a new storage account"
                    ]
                }
            elif "AuthenticationFailed" in error_msg:
                return {
                    "status": "error",
                    "message": "Azure Storage authentication failed",
                    "details": "The connection string or credentials are invalid.",
                    "error_code": "AuthenticationFailed",
                    "recommendations": [
                        "Check your AZURE_STORAGE_CONNECTION_STRING",
                        "Verify the connection string format",
                        "Ensure the account key is correct",
                        "Check if the storage account exists"
                    ]
                }
            elif "ContainerNotFound" in error_msg:
                return {
                    "status": "error",
                    "message": "Azure Storage container not found",
                    "details": "The specified container does not exist.",
                    "error_code": "ContainerNotFound",
                    "recommendations": [
                        "Check AZURE_STORAGE_CONTAINER_NAME",
                        "Create the container in Azure Portal",
                        "Or use an existing container name"
                    ]
                }
            else:
                return {
                    "status": "error",
                    "message": f"Azure Storage test failed: {error_msg}",
                    "details": str(e)
                }
    
    def test_saudi_legal_document_processing(self) -> Dict[str, Any]:
        """Test Saudi legal document processing with sample data."""
        logger.info("📋 Testing Saudi legal document processing...")
        
        try:
            # Create sample Saudi legal document content
            sample_document = """
            صحيفة الدعوى
            
            بيانات صحيفة الدعوى:
            رقم الطلب: ١٣٨٣٩٥١
            التاريخ: ١٤٤٤/٠٣/١٩
            اسم المدعي: عبير احمد سعيد العمودي
            اسم المدعى عليه: أمانة منطقة الرياض
            رقم الجوال: ٠٥٤٨٠٠٦٧٠٠
            البريد الإلكتروني: maabeer@gmail.com
            
            معلومات اضافية:
            رقم القرار: ٠٠٠٠٠٣٦٥٧٨٤٦
            رقم التظلم: ٣٨٠٥٤٨٢
            رقم المخالفة: ١٠٠٠٠٠٠٣٦٥٧٨٤٦
            """
            
            # Test pattern matching extraction
            from app.modules.agent.service import AgentService
            agent_service = AgentService(db=None, message_service=None)
            
            extracted_data = agent_service._extract_basic_info_from_text(sample_document)
            
            # Check if extraction worked
            extracted_fields = 0
            for section in ["court_info", "plaintiff_info", "plaintiff_address", "defendant_info", "additional_info", "case_details"]:
                if extracted_data.get(section):
                    extracted_fields += len([v for v in extracted_data[section].values() if v and v != "غير مذكور"])
            
            logger.info(f"✅ Extracted {extracted_fields} fields from sample document")
            
            return {
                "status": "success",
                "message": "Saudi legal document processing is working correctly",
                "extracted_fields_count": extracted_fields,
                "sample_extractions": {
                    "request_number": extracted_data.get("court_info", {}).get("request_number"),
                    "plaintiff_name": extracted_data.get("plaintiff_info", {}).get("name"),
                    "defendant_name": extracted_data.get("defendant_info", {}).get("name"),
                    "mobile": extracted_data.get("plaintiff_address", {}).get("mobile"),
                    "email": extracted_data.get("plaintiff_address", {}).get("email"),
                    "decision_number": extracted_data.get("additional_info", {}).get("decision_number")
                }
            }
            
        except Exception as e:
            error_msg = f"Saudi legal document processing test failed: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "details": str(e)
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results."""
        logger.info("🚀 Starting Azure Services Test Suite...")
        logger.info("=" * 60)
        
        # Test environment variables
        env_test = self.test_environment_variables()
        self.test_results["environment"] = env_test
        
        # Test Azure OpenAI
        openai_test = self.test_azure_openai()
        self.test_results["azure_openai"] = openai_test
        
        # Test Document Intelligence
        di_test = self.test_document_intelligence()
        self.test_results["document_intelligence"] = di_test
        
        # Test Azure Storage
        storage_test = self.test_azure_storage()
        self.test_results["storage"] = storage_test
        
        # Test Saudi legal document processing
        legal_test = self.test_saudi_legal_document_processing()
        self.test_results["legal_processing"] = legal_test
        
        # Determine overall status
        all_tests = [env_test, openai_test, di_test, storage_test, legal_test]
        success_count = sum(1 for test in all_tests if test.get("status") == "success")
        error_count = sum(1 for test in all_tests if test.get("status") == "error")
        
        if error_count == 0:
            self.test_results["overall_status"] = "all_passed"
        elif success_count > 0:
            self.test_results["overall_status"] = "partial_success"
        else:
            self.test_results["overall_status"] = "all_failed"
        
        self.test_results["summary"] = {
            "total_tests": len(all_tests),
            "passed": success_count,
            "failed": error_count,
            "success_rate": f"{(success_count/len(all_tests)*100):.1f}%"
        }
        
        return self.test_results
    
    def print_results(self, results: Dict[str, Any]):
        """Print test results in a formatted way."""
        logger.info("=" * 60)
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        
        # Overall status
        status_emoji = {
            "all_passed": "✅",
            "partial_success": "⚠️",
            "all_failed": "❌"
        }
        
        overall_status = results.get("overall_status", "unknown")
        emoji = status_emoji.get(overall_status, "❓")
        logger.info(f"{emoji} Overall Status: {overall_status.upper()}")
        
        # Summary
        summary = results.get("summary", {})
        logger.info(f"📈 Success Rate: {summary.get('success_rate', '0%')}")
        logger.info(f"✅ Passed: {summary.get('passed', 0)}/{summary.get('total_tests', 0)}")
        logger.info(f"❌ Failed: {summary.get('failed', 0)}/{summary.get('total_tests', 0)}")
        
        logger.info("\n" + "=" * 60)
        logger.info("🔍 DETAILED RESULTS")
        logger.info("=" * 60)
        
        # Environment variables
        env_test = results.get("environment", {})
        logger.info(f"\n🌍 Environment Variables: {env_test.get('status', 'unknown')}")
        if env_test.get("missing_variables"):
            logger.info("Missing variables:")
            for var in env_test["missing_variables"]:
                logger.info(f"  {var}")
        
        # Azure OpenAI
        openai_test = results.get("azure_openai", {})
        status_emoji = "✅" if openai_test.get("status") == "success" else "❌"
        logger.info(f"\n{status_emoji} Azure OpenAI: {openai_test.get('status', 'unknown')}")
        if openai_test.get("message"):
            logger.info(f"  Message: {openai_test['message']}")
        if openai_test.get("deployment"):
            logger.info(f"  Deployment: {openai_test['deployment']}")
        
        # Document Intelligence
        di_test = results.get("document_intelligence", {})
        status_emoji = "✅" if di_test.get("status") == "success" else "❌"
        logger.info(f"\n{status_emoji} Document Intelligence: {di_test.get('status', 'unknown')}")
        if di_test.get("message"):
            logger.info(f"  Message: {di_test['message']}")
        if di_test.get("extracted_text_length"):
            logger.info(f"  Extracted text length: {di_test['extracted_text_length']} characters")
        
        # Azure Storage
        storage_test = results.get("storage", {})
        status_emoji = "✅" if storage_test.get("status") == "success" else "❌"
        logger.info(f"\n{status_emoji} Azure Storage: {storage_test.get('status', 'unknown')}")
        if storage_test.get("message"):
            logger.info(f"  Message: {storage_test['message']}")
        if storage_test.get("total_containers"):
            logger.info(f"  Total containers: {storage_test['total_containers']}")
        
        # Legal Processing
        legal_test = results.get("legal_processing", {})
        status_emoji = "✅" if legal_test.get("status") == "success" else "❌"
        logger.info(f"\n{status_emoji} Legal Document Processing: {legal_test.get('status', 'unknown')}")
        if legal_test.get("message"):
            logger.info(f"  Message: {legal_test['message']}")
        if legal_test.get("extracted_fields_count"):
            logger.info(f"  Extracted fields: {legal_test['extracted_fields_count']}")
        
        logger.info("\n" + "=" * 60)
        logger.info("🎯 RECOMMENDATIONS")
        logger.info("=" * 60)
        
        # Provide recommendations based on results
        if results.get("overall_status") == "all_passed":
            logger.info("✅ All services are working correctly!")
            logger.info("🚀 You can now process Saudi legal documents.")
        elif results.get("overall_status") == "partial_success":
            logger.info("⚠️ Some services are working, but there are issues:")
            if env_test.get("status") != "ok":
                logger.info("  - Fix missing environment variables")
            if openai_test.get("status") != "success":
                logger.info("  - Check Azure OpenAI configuration")
            if di_test.get("status") != "success":
                logger.info("  - Check Document Intelligence configuration")
            if storage_test.get("status") != "success":
                logger.info("  - Check Azure Storage configuration")
                # Check for specific storage errors
                if storage_test.get("error_code") == "AccountIsDisabled":
                    logger.info("  🚨 CRITICAL: Azure Storage account is disabled!")
                    logger.info("  📋 To fix this:")
                    for rec in storage_test.get("recommendations", []):
                        logger.info(f"    • {rec}")
        else:
            logger.info("❌ Multiple services are not working:")
            logger.info("  - Check all environment variables")
            logger.info("  - Verify Azure service configurations")
            logger.info("  - Check network connectivity")
            
            # Check for specific storage errors
            storage_test = results.get("storage", {})
            if storage_test.get("error_code") == "AccountIsDisabled":
                logger.info("\n🚨 CRITICAL ISSUE: Azure Storage account is disabled!")
                logger.info("This is preventing file uploads and storage operations.")
                logger.info("📋 Immediate action required:")
                for rec in storage_test.get("recommendations", []):
                    logger.info(f"  • {rec}")
        
        logger.info("=" * 60)

def main():
    """Main function to run the test suite."""
    try:
        tester = AzureServicesTester()
        results = tester.run_all_tests()
        tester.print_results(results)
        
        # Save results to file
        output_file = f"azure_services_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n📄 Detailed results saved to: {output_file}")
        
        # Exit with appropriate code
        if results.get("overall_status") == "all_passed":
            sys.exit(0)
        elif results.get("overall_status") == "partial_success":
            sys.exit(1)
        else:
            sys.exit(2)
            
    except Exception as e:
        logger.error(f"Test suite failed with error: {str(e)}")
        sys.exit(3)

if __name__ == "__main__":
    main() 