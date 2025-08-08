#!/usr/bin/env python3
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
