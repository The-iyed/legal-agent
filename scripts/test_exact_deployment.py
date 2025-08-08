#!/usr/bin/env python3
"""
Test Exact Deployment Name

This script tests the exact deployment name that exists in the Azure OpenAI resource.
"""

import os
import sys
from pathlib import Path
from openai import AzureOpenAI

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config.settings import get_settings

def test_exact_deployment():
    """Test the exact deployment name from the image."""
    print("Testing Exact Deployment Name")
    print("="*50)
    
    # Get settings
    settings = get_settings()
    
    # Initialize client
    client = AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=getattr(settings, 'AZURE_OPENAI_API_VERSION', '2024-11-20'),
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
    )
    
    print(f"Endpoint: {settings.AZURE_OPENAI_ENDPOINT}")
    print(f"API Version: {getattr(settings, 'AZURE_OPENAI_API_VERSION', '2024-11-20')}")
    print(f"Current Deployment Name: {settings.AZURE_OPENAI_DEPLOYMENT_NAME}")
    print()
    
    # Test the exact deployment name from the image
    deployment_name = "gpt-4o"
    
    try:
        print(f"Testing deployment: {deployment_name}")
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "user", "content": "Hello, this is a test message."}
            ],
            max_tokens=20
        )
        print("✅ SUCCESS!")
        print(f"Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ ERROR: {error_msg}")
        
        # Check for specific error types
        if "404" in error_msg:
            print("\n🔍 404 Error Analysis:")
            print("The deployment exists but might have access issues:")
            print("1. API key permissions")
            print("2. Regional access")
            print("3. Deployment status")
            
        elif "401" in error_msg:
            print("\n🔍 401 Error Analysis:")
            print("Authentication issue - check API key")
            
        elif "403" in error_msg:
            print("\n🔍 403 Error Analysis:")
            print("Permission issue - check API key permissions")
            
        return False

def test_with_different_api_versions():
    """Test with different API versions."""
    print("\n" + "="*50)
    print("Testing Different API Versions")
    print("="*50)
    
    settings = get_settings()
    deployment_name = "gpt-4o"
    
    api_versions = [
        "2024-11-20",
        "2024-02-15-preview",
        "2024-01-01",
        "2023-12-01-preview"
    ]
    
    for api_version in api_versions:
        try:
            print(f"\nTesting API version: {api_version}")
            client = AzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=api_version,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
            
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=10
            )
            print(f"✅ SUCCESS with API version {api_version}!")
            print(f"Response: {response.choices[0].message.content}")
            return api_version
            
        except Exception as e:
            print(f"❌ Failed with API version {api_version}: {str(e)[:100]}...")
    
    return None

def main():
    """Main function."""
    print("Testing Exact Deployment Configuration")
    print("Based on the deployment details from your Azure portal")
    print()
    
    # Test the exact deployment
    success = test_exact_deployment()
    
    if not success:
        print("\n" + "="*50)
        print("Trying Different API Versions")
        print("="*50)
        
        working_api_version = test_with_different_api_versions()
        
        if working_api_version:
            print(f"\n🎉 SUCCESS! Use API version: {working_api_version}")
            print(f"Update your .env file:")
            print(f"AZURE_OPENAI_API_VERSION={working_api_version}")
        else:
            print("\n❌ No working configuration found.")
            print("\nPossible solutions:")
            print("1. Check if the deployment is in a different region")
            print("2. Verify API key has access to this deployment")
            print("3. Check if the deployment is paused or has issues")
            print("4. Try creating a new deployment with a different name")
    else:
        print("\n🎉 SUCCESS! The deployment is working correctly.")
        print("The enhanced PDF processing should now work properly.")

if __name__ == "__main__":
    main() 