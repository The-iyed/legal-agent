#!/usr/bin/env python3
"""
Environment Variables Fix Script

This script helps identify and fix environment variable issues.
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

def check_env_file():
    """Check the .env file and identify issues."""
    logger.info("🔍 Checking .env file...")
    
    env_file = ".env"
    if not os.path.exists(env_file):
        logger.error(f"❌ {env_file} file not found")
        return
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    logger.info(f"✅ Found {env_file} file")
    
    # Check for specific issues
    issues = []
    fixes = []
    
    # Check Document Intelligence API key
    if "AZURE_DOCUMENT_INTELLIGENCE_KEY=" in content and "AZURE_DOCUMENT_INTELLIGENCE_API_KEY=" not in content:
        issues.append("❌ Document Intelligence API key has wrong name")
        fixes.append("Change AZURE_DOCUMENT_INTELLIGENCE_KEY to AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
    
    # Check Azure OpenAI API version
    if "AZURE_OPENAI_API_VERSION=2024-02-15-preview" in content:
        issues.append("❌ Azure OpenAI API version is outdated")
        fixes.append("Change AZURE_OPENAI_API_VERSION to 2024-11-20")
    
    # Check storage connection string format
    if "AZURE_STORAGE_CONNECTION_STRING=" in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith("AZURE_STORAGE_CONNECTION_STRING="):
                if line.count(';') < 3:
                    issues.append("❌ Storage connection string appears to be split across multiple lines")
                    fixes.append("Ensure AZURE_STORAGE_CONNECTION_STRING is on a single line")
                break
    
    # Check for missing variables
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY", 
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
        "AZURE_DOCUMENT_INTELLIGENCE_API_KEY",
        "AZURE_STORAGE_CONNECTION_STRING",
        "AZURE_STORAGE_CONTAINER_NAME"
    ]
    
    for var in required_vars:
        if f"{var}=" not in content:
            issues.append(f"❌ Missing {var}")
            fixes.append(f"Add {var}=<value> to your .env file")
    
    return issues, fixes

def create_fixed_env_content():
    """Create the corrected .env content."""
    return """# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=8HMs7Zq5nmC3Y1r5J8Vxz4Y8lP4JK4RgFUzjZXyQTlpTHlFXGpwdJQQJ99BHACYeBjFXJ3w3AAABACOGrfiA
OPENAI_API_KEY=8HMs7Zq5nmC3Y1r5J8Vxz4Y8lP4JK4RgFUzjZXyQTlpTHlFXGpwdJQQJ99BHACYeBjFXJ3w3AAABACOGrfiA
AZURE_OPENAI_ENDPOINT=https://momah-open-ai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-ada-002
AZURE_OPENAI_API_VERSION=2024-11-20

# Azure AI Search Configuration
AZURE_AI_SEARCH_ENDPOINT=https://momah-ai-search.search.windows.net
AZURE_AI_SEARCH_API_KEY=S2ObM5pTXe9WOxsZdbA8W6lAypIdEG72YqEY9nHSZGAzSeDS4n8r
AZURE_AI_SEARCH_STUDY_INDEX_NAME=ma3refa-pdf-index-v3

# Application Configuration
APP_ENV=development
PORT=8000

# Azure Storage Configuration (FIXED)
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=momahstoage;AccountKey=kC+Bbh0nMRAR5/wfZ8LT8aPtfwxgfsOIObZhF839tkWhaMepqI3nOwVbmPDpckGe3+FpqsMxgCT8+ASt4Ixezg==;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER_NAME=legal-storage

# Azure Vision Configuration
AZURE_VISION_ENDPOINT=https://maarefavision.cognitiveservices.azure.com/
AZURE_VISION_KEY=39uiNuPdnRRP68cnidcCIskVqjd5UmUA6ciAuAWlD1m1B2S9IcORJQQJ99BFACYeBjFXJ3w3AAAFACOG4p0x

# Azure Document Intelligence Configuration (FIXED)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://momah-ai-doc-intelligent.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=BKL5HwPAmo4hkpKbKwDIT05bR65HQUA4pmaGAnWBkCbMc5uLL7PrJQQJ99BHACYeBjFXJ3w3AAALACOGuzW1

# Cache and Embedding Configuration
CACHE_DIR=.cache
EMBEDDING_MODEL=text-embedding-ada-002

# Database Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=maarefa_agent
REDIS_HOST=redis
REDIS_PORT=6379

# PostgreSQL Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=commercial_licenses
DB_USER=postgres
DB_PASSWORD=postgres123
DATABASE_URL=postgresql://postgres:postgres123@postgres:5432/commercial_licenses

# PGAdmin Configuration
PGADMIN_DEFAULT_EMAIL=admin@commercial.local
PGADMIN_DEFAULT_PASSWORD=admin123

# Other Services
GROQ_API_KEY=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
MILVUS_URI=http://milvus:19530
EMBEDDING_BACKEND=azure_openai
ALLOW_SPECIAL_EMAIL_DOMAINS=.local
AZURE_STORAGE_DOCS_CONTAINER_NAME=marefa-docs
"""

def main():
    """Main function."""
    logger.info("🔧 Environment Variables Fix Tool")
    logger.info("=" * 60)
    
    # Check current .env file
    issues, fixes = check_env_file()
    
    if issues:
        logger.info("❌ Issues found in .env file:")
        for issue in issues:
            logger.info(f"  {issue}")
        
        logger.info("\n🔧 Fixes needed:")
        for fix in fixes:
            logger.info(f"  {fix}")
        
        # Create corrected .env content
        fixed_content = create_fixed_env_content()
        
        # Save to new file
        backup_file = f".env.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        fixed_file = f".env.fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Backup current .env
        if os.path.exists(".env"):
            with open(backup_file, 'w') as f:
                with open(".env", 'r') as original:
                    f.write(original.read())
            logger.info(f"📄 Current .env backed up to: {backup_file}")
        
        # Save fixed content
        with open(fixed_file, 'w') as f:
            f.write(fixed_content)
        
        logger.info(f"📄 Fixed .env content saved to: {fixed_file}")
        
        logger.info("\n" + "=" * 60)
        logger.info("🎯 NEXT STEPS")
        logger.info("=" * 60)
        logger.info("1. Review the fixed .env content")
        logger.info("2. Replace your current .env with the fixed version:")
        logger.info(f"   cp {fixed_file} .env")
        logger.info("3. Test the services:")
        logger.info("   python3 scripts/test_azure_services.py")
        logger.info("4. If storage still fails, check Azure Portal for account status")
        
    else:
        logger.info("✅ No issues found in .env file")
        logger.info("The problem might be with Azure service configuration")

if __name__ == "__main__":
    main() 