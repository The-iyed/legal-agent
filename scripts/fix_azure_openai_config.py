#!/usr/bin/env python3
"""
Azure OpenAI Configuration Fixer

This script helps diagnose and fix Azure OpenAI configuration issues.
"""

import os
import sys
from pathlib import Path
import logging
from openai import AzureOpenAI
from typing import List, Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_environment_variables():
    """Check if all required environment variables are set."""
    print("="*60)
    print("Checking Environment Variables")
    print("="*60)
    
    required_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "AZURE_OPENAI_API_VERSION"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask the API key for security
            if "API_KEY" in var:
                masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"✓ {var}: {masked_value}")
            else:
                print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: NOT SET")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("\n✅ All required environment variables are set")
        return True


def test_azure_openai_connection():
    """Test the Azure OpenAI connection and list available deployments."""
    print("\n" + "="*60)
    print("Testing Azure OpenAI Connection")
    print("="*60)
    
    try:
        # Get settings
        settings = get_settings()
        
        print(f"Endpoint: {settings.AZURE_OPENAI_ENDPOINT}")
        print(f"API Version: {getattr(settings, 'AZURE_OPENAI_API_VERSION', '2024-11-20')}")
        print(f"Deployment Name: {settings.AZURE_OPENAI_DEPLOYMENT_NAME}")
        
        # Initialize client
        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=getattr(settings, 'AZURE_OPENAI_API_VERSION', '2024-11-20'),
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        
        print("✅ Azure OpenAI client initialized successfully")
        
        # Test a simple completion
        print("\nTesting simple completion...")
        try:
            response = client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "user", "content": "Hello, this is a test message."}
                ],
                max_tokens=10
            )
            print("✅ Simple completion test successful")
            print(f"Response: {response.choices[0].message.content}")
            return True
            
        except Exception as e:
            print(f"❌ Simple completion test failed: {e}")
            
            # Try to get more information about the error
            if "404" in str(e):
                print("\n🔍 404 Error detected - this usually means:")
                print("1. The deployment name is incorrect")
                print("2. The deployment doesn't exist")
                print("3. The deployment is not accessible")
                
                # Try to list available deployments
                print("\nAttempting to list available deployments...")
                try:
                    # Note: This might not work depending on your permissions
                    deployments = client.models.list()
                    print("Available models/deployments:")
                    for deployment in deployments:
                        print(f"  - {deployment.id}")
                except Exception as list_error:
                    print(f"Could not list deployments: {list_error}")
                    print("This might be due to insufficient permissions")
            
            return False
            
    except Exception as e:
        print(f"❌ Failed to initialize Azure OpenAI client: {e}")
        return False


def suggest_fixes():
    """Suggest fixes for common Azure OpenAI configuration issues."""
    print("\n" + "="*60)
    print("Suggested Fixes")
    print("="*60)
    
    print("1. Check Deployment Name:")
    print("   - Go to Azure Portal > Your OpenAI Resource > Deployments")
    print("   - Note the exact deployment name (not the model name)")
    print("   - Update AZURE_OPENAI_DEPLOYMENT_NAME in your .env file")
    
    print("\n2. Common Deployment Names:")
    print("   - If you created a deployment for GPT-4o, it might be named:")
    print("     * 'gpt-4o' (if you used the model name as deployment name)")
    print("     * 'gpt-4o-deployment'")
    print("     * 'chat-gpt-4o'")
    print("     * 'gpt-4o-chat'")
    
    print("\n3. Create a New Deployment:")
    print("   - Go to Azure Portal > Your OpenAI Resource > Deployments")
    print("   - Click 'Create'")
    print("   - Choose 'GPT-4o' as the model")
    print("   - Give it a name like 'gpt-4o-deployment'")
    print("   - Update your .env file with the new deployment name")
    
    print("\n4. Check API Version:")
    print("   - Current API version: 2024-11-20")
    print("   - Make sure your Azure OpenAI resource supports this version")
    
    print("\n5. Check Permissions:")
    print("   - Ensure your API key has access to the deployment")
    print("   - Check if the deployment is in the same region as your resource")


def create_test_script():
    """Create a test script to verify the configuration."""
    print("\n" + "="*60)
    print("Creating Test Script")
    print("="*60)
    
    test_script_content = '''#!/usr/bin/env python3
"""
Test Azure OpenAI Configuration
"""

import os
from openai import AzureOpenAI

# Configuration
AZURE_OPENAI_API_KEY = "YOUR_API_KEY_HERE"
AZURE_OPENAI_ENDPOINT = "YOUR_ENDPOINT_HERE"
AZURE_OPENAI_DEPLOYMENT_NAME = "YOUR_DEPLOYMENT_NAME_HERE"
AZURE_OPENAI_API_VERSION = "2024-11-20"

def test_connection():
    try:
        client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "user", "content": "Hello, this is a test."}
            ],
            max_tokens=50
        )
        
        print("✅ Connection successful!")
        print(f"Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
'''
    
    with open("test_azure_openai.py", "w") as f:
        f.write(test_script_content)
    
    print("✅ Created test_azure_openai.py")
    print("Edit this file with your actual credentials and run it to test")


def main():
    """Main function to run all checks."""
    print("Azure OpenAI Configuration Fixer")
    print("This script helps diagnose and fix Azure OpenAI configuration issues.")
    
    # Check environment variables
    env_ok = check_environment_variables()
    
    if not env_ok:
        print("\n❌ Please set the missing environment variables and try again.")
        return
    
    # Test connection
    connection_ok = test_azure_openai_connection()
    
    if not connection_ok:
        suggest_fixes()
        create_test_script()
    else:
        print("\n✅ Azure OpenAI configuration is working correctly!")
        print("You can now use the enhanced PDF processing features.")


if __name__ == "__main__":
    main() 