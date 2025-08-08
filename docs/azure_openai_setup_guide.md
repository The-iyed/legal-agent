# Azure OpenAI Setup Guide

This guide helps you fix the Azure OpenAI configuration issues that are preventing the enhanced PDF processing from working correctly.

## Current Issue

The system is getting a 404 "Resource Not Found" error when trying to access the Azure OpenAI deployment. This typically means:

1. The deployment name is incorrect
2. The deployment doesn't exist
3. The deployment is not accessible with current permissions

## Step-by-Step Fix

### 1. Check Your Azure OpenAI Resource

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your Azure OpenAI resource (named `momah-open-ai`)
3. In the left sidebar, click on **"Deployments"**

### 2. Verify Existing Deployments

Look at the list of deployments. You should see something like:

- **Deployment Name**: The actual name of your deployment
- **Model**: The model being used (e.g., GPT-4o)
- **Status**: Should be "Succeeded"

### 3. Common Deployment Names

If you don't see any deployments, or if the deployment name doesn't match `gpt-4o`, here are common naming patterns:

- `gpt-4o` (if you used the model name as deployment name)
- `gpt-4o-deployment`
- `chat-gpt-4o`
- `gpt-4o-chat`
- `gpt4o`
- `gpt4o-deployment`

### 4. Create a New Deployment (If Needed)

If no deployment exists, create one:

1. Click **"Create"** in the Deployments page
2. Fill in the details:
   - **Deployment name**: Choose a name like `gpt-4o-deployment`
   - **Model**: Select `GPT-4o`
   - **Model version**: Choose the latest version
   - **Content filtering**: Default settings
3. Click **"Create"**
4. Wait for the deployment to complete (Status should show "Succeeded")

### 5. Update Environment Variables

Once you have the correct deployment name, update your `.env` file:

```bash
# Current (incorrect)
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Update to the actual deployment name (example)
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-deployment
```

### 6. Test the Configuration

Run the diagnostic script to verify the fix:

```bash
python3 scripts/fix_azure_openai_config.py
```

## Alternative Solutions

### Option 1: Use a Different API Version

If the 2024-11-20 API version is not supported, try:

```bash
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### Option 2: Check Resource Region

Ensure your Azure OpenAI resource is in a region that supports GPT-4o:

- East US
- West US 2
- West Europe
- North Europe
- Australia East
- Canada East

### Option 3: Use a Different Model

If GPT-4o is not available, you can use GPT-4:

1. Create a deployment with GPT-4 model
2. Update the deployment name in your `.env` file

## Verification Steps

### 1. Test Basic Connection

Create a simple test script:

```python
from openai import AzureOpenAI
import os

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-11-20"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

try:
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=10
    )
    print("✅ Success!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ Error: {e}")
```

### 2. Test Enhanced PDF Processing

Once the Azure OpenAI is working, test the enhanced PDF processing:

```bash
python3 scripts/test_enhanced_pdf_processing.py
```

## Troubleshooting

### Error: "Resource not found"

**Cause**: Deployment name is incorrect or doesn't exist
**Solution**: 
1. Check the exact deployment name in Azure Portal
2. Update your `.env` file with the correct name

### Error: "API version not supported"

**Cause**: Your Azure OpenAI resource doesn't support the API version
**Solution**:
1. Try a different API version (e.g., `2024-02-15-preview`)
2. Update your Azure OpenAI resource to a newer version

### Error: "Insufficient permissions"

**Cause**: API key doesn't have access to the deployment
**Solution**:
1. Generate a new API key in Azure Portal
2. Ensure the key has the necessary permissions

### Error: "Model not available"

**Cause**: GPT-4o is not available in your region
**Solution**:
1. Use GPT-4 instead
2. Move your resource to a supported region

## Environment Variables Reference

Here's the complete set of environment variables you need:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name_here
AZURE_OPENAI_API_VERSION=2024-11-20
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-ada-002

# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your_document_intelligence_key

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=your_storage_connection_string
```

## Next Steps

Once you've fixed the Azure OpenAI configuration:

1. **Test the enhanced PDF processing**:
   ```bash
   python3 scripts/test_enhanced_pdf_processing.py
   ```

2. **Start the server**:
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Test the API endpoints**:
   - Upload a PDF to `/api/v1/document-intelligence/analyze-pdf-enhanced`
   - Check the enhanced text extraction results

4. **Monitor the logs** for successful processing

## Support

If you continue to have issues:

1. Check the Azure OpenAI service status
2. Verify your subscription has access to GPT-4o
3. Contact Azure support if needed
4. Check the application logs for detailed error messages

## Success Indicators

You'll know the configuration is working when:

- ✅ The diagnostic script shows "Connection successful"
- ✅ PDF processing completes without OpenAI errors
- ✅ Claim extraction includes refined responses
- ✅ API endpoints return successful responses

The enhanced PDF processing will then work correctly, providing comprehensive text extraction from multi-page documents using Document Intelligence and refined analysis with Azure OpenAI. 