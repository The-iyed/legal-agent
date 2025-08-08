#!/usr/bin/env python3
"""
Azure Storage Account Fix Script

This script helps diagnose and fix Azure Storage account issues.
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_storage_connection():
    """Check if storage connection string is valid."""
    try:
        from azure.storage.blob import BlobServiceClient
        
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            logger.error("❌ AZURE_STORAGE_CONNECTION_STRING not set")
            return False
        
        # Try to create client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Try to list containers (this will fail if account is disabled)
        containers = list(blob_service_client.list_containers(max_results=1))
        logger.info("✅ Storage connection string is valid")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "AccountIsDisabled" in error_msg:
            logger.error("❌ Storage account is disabled")
            return False
        else:
            logger.error(f"❌ Storage connection failed: {error_msg}")
            return False

def provide_fix_instructions():
    """Provide step-by-step instructions to fix storage account issues."""
    logger.info("=" * 60)
    logger.info("🔧 AZURE STORAGE ACCOUNT FIX INSTRUCTIONS")
    logger.info("=" * 60)
    
    logger.info("\n📋 Option 1: Reactivate Existing Account")
    logger.info("1. Go to Azure Portal: https://portal.azure.com")
    logger.info("2. Navigate to 'Storage accounts'")
    logger.info("3. Find your storage account")
    logger.info("4. Click on the account name")
    logger.info("5. Look for 'Reactivate' or 'Enable' button")
    logger.info("6. Click to reactivate the account")
    logger.info("7. Wait 2-5 minutes for activation")
    
    logger.info("\n📋 Option 2: Create New Storage Account")
    logger.info("1. Go to Azure Portal: https://portal.azure.com")
    logger.info("2. Click 'Create a resource'")
    logger.info("3. Search for 'Storage account'")
    logger.info("4. Click 'Create'")
    logger.info("5. Fill in the details:")
    logger.info("   - Subscription: Your subscription")
    logger.info("   - Resource group: Create new or use existing")
    logger.info("   - Storage account name: leg-agent-storage (or similar)")
    logger.info("   - Region: Same as your other Azure resources")
    logger.info("   - Performance: Standard")
    logger.info("   - Redundancy: LRS (Locally redundant storage)")
    logger.info("6. Click 'Review + create' then 'Create'")
    logger.info("7. Wait for deployment to complete")
    
    logger.info("\n📋 Option 3: Get Connection String")
    logger.info("1. Go to your storage account in Azure Portal")
    logger.info("2. Click 'Access keys' in the left menu")
    logger.info("3. Click 'Show' next to 'Connection string'")
    logger.info("4. Copy the connection string")
    logger.info("5. Update your .env file:")
    logger.info("   AZURE_STORAGE_CONNECTION_STRING=<paste_connection_string>")
    
    logger.info("\n📋 Option 4: Create Container")
    logger.info("1. Go to your storage account in Azure Portal")
    logger.info("2. Click 'Containers' in the left menu")
    logger.info("3. Click '+ Container'")
    logger.info("4. Name: leg-agent-files")
    logger.info("5. Public access level: Private")
    logger.info("6. Click 'Create'")
    logger.info("7. Update your .env file:")
    logger.info("   AZURE_STORAGE_CONTAINER_NAME=leg-agent-files")

def create_sample_env_file():
    """Create a sample .env file with storage configuration."""
    sample_env = """# Azure Storage Configuration
# Replace these values with your actual storage account details

# Storage Account Connection String
# Format: DefaultEndpointsProtocol=https;AccountName=<account_name>;AccountKey=<account_key>;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=your-storage-account;AccountKey=your-account-key;EndpointSuffix=core.windows.net

# Storage Container Name (create this container in your storage account)
AZURE_STORAGE_CONTAINER_NAME=leg-agent-files

# Storage Account Name (for reference)
AZURE_STORAGE_ACCOUNT_NAME=your-storage-account

# Other Azure Services (keep existing values)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-openai-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=your-document-intelligence-api-key
"""
    
    filename = f"sample_storage_env_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, 'w') as f:
        f.write(sample_env)
    
    logger.info(f"\n📄 Sample .env configuration saved to: {filename}")
    logger.info("Copy the storage-related variables to your .env file")

def main():
    """Main function."""
    logger.info("🔍 Azure Storage Account Diagnostic Tool")
    logger.info("=" * 60)
    
    # Check current connection
    logger.info("Checking current storage connection...")
    is_working = check_storage_connection()
    
    if is_working:
        logger.info("✅ Storage account is working correctly!")
        logger.info("No action needed.")
    else:
        logger.info("❌ Storage account has issues.")
        provide_fix_instructions()
        create_sample_env_file()
        
        logger.info("\n" + "=" * 60)
        logger.info("🎯 NEXT STEPS")
        logger.info("=" * 60)
        logger.info("1. Follow the instructions above to fix your storage account")
        logger.info("2. Update your .env file with the new connection string")
        logger.info("3. Run the test script again: python scripts/test_azure_services.py")
        logger.info("4. If you need help, check Azure documentation or contact support")

if __name__ == "__main__":
    main() 