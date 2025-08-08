#!/usr/bin/env python3
"""
Test Different Deployment Names

This script tests common deployment names to find the correct one for your Azure OpenAI resource.
"""

import os
import sys
from pathlib import Path
from openai import AzureOpenAI

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config.settings import get_settings

def test_deployment_name(deployment_name: str, client: AzureOpenAI) -> bool:
    """Test if a deployment name works."""
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "user", "content": "Hello"}
            ],
            max_tokens=10
        )
        print(f"✅ {deployment_name}: SUCCESS")
        print(f"   Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            print(f"❌ {deployment_name}: NOT FOUND")
        elif "401" in error_msg:
            print(f"❌ {deployment_name}: UNAUTHORIZED")
        else:
            print(f"❌ {deployment_name}: ERROR - {error_msg[:100]}...")
        return False

def main():
    """Test common deployment names."""
    print("Testing Common Deployment Names")
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
    print()
    
    # Common deployment names to test
    deployment_names = [
        "gpt-4o",
        "gpt-4o-deployment",
        "chat-gpt-4o",
        "gpt-4o-chat",
        "gpt4o",
        "gpt4o-deployment",
        "gpt-4",
        "gpt-4-deployment",
        "chat-gpt-4",
        "gpt-4-chat",
        "gpt-35-turbo",
        "gpt-35-turbo-deployment",
        "chat-gpt-35-turbo",
        "gpt-35-turbo-chat"
    ]
    
    working_deployments = []
    
    for deployment_name in deployment_names:
        if test_deployment_name(deployment_name, client):
            working_deployments.append(deployment_name)
        print()
    
    # Summary
    print("="*50)
    print("SUMMARY")
    print("="*50)
    
    if working_deployments:
        print("✅ Working deployments found:")
        for deployment in working_deployments:
            print(f"   - {deployment}")
        
        print(f"\n🎉 Use one of these deployment names in your .env file:")
        print(f"   AZURE_OPENAI_DEPLOYMENT_NAME={working_deployments[0]}")
        
    else:
        print("❌ No working deployments found.")
        print("\nPossible issues:")
        print("1. No deployments exist in your Azure OpenAI resource")
        print("2. Your API key doesn't have access to deployments")
        print("3. The resource doesn't support the API version")
        print("\nNext steps:")
        print("1. Go to Azure Portal > Your OpenAI Resource > Deployments")
        print("2. Create a new deployment with GPT-4o or GPT-4")
        print("3. Note the exact deployment name")
        print("4. Update your .env file")

if __name__ == "__main__":
    main() 