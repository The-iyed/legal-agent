from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.database import get_database
from app.modules.agent.service import AgentService
from app.modules.conversation.service import ConversationService
from app.modules.message.service import MessageService
from app.schemas.agent import QueryRequest, QueryResponse, FileUploadRequest, FileUploadResponse, FileInfoResponse
from bson import ObjectId
import logging
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.routes.message import get_message_service
from app.schemas.conversation import ConversationStatus

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        404: {"description": "Agent or conversation not found"},
        500: {"description": "Internal server error"}
    }
)

def get_agent_service(db: AsyncIOMotorDatabase = Depends(get_database), 
                      message_service: MessageService = Depends(get_message_service)) -> AgentService:
    """Get agent service instance."""
    return AgentService(db, message_service)

def get_conversation_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> ConversationService:
    """Get conversation service instance."""
    return ConversationService(db)

def get_message_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> MessageService:
    """Get message service instance."""
    return MessageService(db)

@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Query the semantic kernel supervisor and store conversation messages",
    description="""
    Send a query to the semantic kernel supervisor and store the conversation history.
    
    This endpoint:
    1. Validates that the conversation exists
    2. Processes the query through the agent service (which handles all message storage)
    3. Returns the agent's response
    
    The conversation history can be retrieved using the `/messages/conversation/{conversation_id}` endpoint.
    
    Required fields:
    - conversation_id: ID of the conversation to store messages in (must be a valid MongoDB ObjectId)
    - user_id: ID of the user making the query
    - query: The actual query text
    
    Returns:
    - response: The agent's response text
    - metadata: Additional information about the response (e.g., confidence, search method, original query)
    """
)
async def query_agent(
    request: QueryRequest = Body(
        ...,
        example={
            "conversation_id": "507f1f77bcf86cd799439011",
            "user_id": "user123",
            "query": "What is the weather like?"
        }
    ),
    agent_service: AgentService = Depends(get_agent_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Process a query through the semantic kernel supervisor and store the conversation.
    
    Args:
        request: The query request containing conversation_id, user_id, and query
        agent_service: Service for processing queries and storing messages
        conversation_service: Service for managing conversations
        
    Returns:
        QueryResponse: The agent's response and metadata
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid
            - 404: If the conversation doesn't exist
            - 500: If there's an error processing the query
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(request.conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )

        # Verify conversation exists
        conversation = await conversation_service.get_conversation(request.conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Agent service handles all message storage and processing
        response = await agent_service.query_agent(
            query=request.query, 
            conversation_id=request.conversation_id,
            user_id=request.user_id
        )

        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying agent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}"
        )

@router.post(
    "/upload-file",
    response_model=FileUploadResponse,
    summary="Upload and process legal document files",
    description="""
    Upload a legal document file (e.g., statement of claim) for processing and validation.
    
    This endpoint:
    1. Validates that the conversation exists
    2. Uploads the file to Azure Blob Storage
    3. Extracts and validates document data against statement of claim format
    4. Stores the processed data in the database if valid
    5. Returns processing results with Arabic response
    
    Required fields:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    - user_id: ID of the user uploading the file
    - file: The document file to upload (PDF, image, etc.)
    
    Returns:
    - response: Arabic response message about processing results
    - file_url: URL of the uploaded file in blob storage
    - case_number: Extracted case number if valid
    - is_valid: Whether the document is valid
    - metadata: Additional processing information
    """
)
async def upload_file(
    conversation_id: str = Form(..., description="Conversation ID"),
    user_id: str = Form(..., description="User ID"),
    file: UploadFile = File(..., description="Document file to upload"),
    agent_service: AgentService = Depends(get_agent_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Upload and process a legal document file.
    
    Args:
        conversation_id: The conversation ID to associate the file with
        user_id: The user ID uploading the file
        file: The document file to upload and process
        agent_service: Service for processing files and storing messages
        conversation_service: Service for managing conversations
        
    Returns:
        FileUploadResponse: Processing results and metadata
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid or file is invalid
            - 404: If the conversation doesn't exist
            - 500: If there's an error processing the file
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )

        # Verify conversation exists
        conversation = await conversation_service.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )

        # Check file size (limit to 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size too large. Maximum size is 10MB."
            )

        # Process file upload
        response = await agent_service.process_file_upload(
            file_content=file_content,
            filename=file.filename,
            conversation_id=conversation_id,
            user_id=user_id
        )

        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}"
        )

@router.post(
    "/upload-attachments",
    response_model=FileUploadResponse,
    summary="Upload supporting attachments for a validated claim",
    description="""
    Upload supporting documents and attachments for a validated statement of claim.
    
    This endpoint:
    1. Validates that the conversation exists and is in WAITING_FOR_ATTACHMENTS status
    2. Uploads multiple attachment files to Azure Blob Storage
    3. Extracts content from each attachment using Azure Document Intelligence
    4. Stores the processed attachments in the database
    5. Returns a comprehensive overview of the claim with all attachments
    
    Required fields:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    - user_id: ID of the user uploading the attachments
    - files: List of attachment files to upload (PDF, image, etc.)
    
    Returns:
    - response: Arabic response with full claim overview including attachments
    - file_url: URLs of uploaded attachment files
    - case_number: Extracted case number from the original claim
    - is_valid: Whether the attachments were processed successfully
    - metadata: Additional processing information including attachment summaries
    """
)
async def upload_attachments(
    conversation_id: str = Form(..., description="Conversation ID"),
    user_id: str = Form(..., description="User ID"),
    files: list[UploadFile] = File(..., description="Attachment files to upload"),
    agent_service: AgentService = Depends(get_agent_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Upload and process supporting attachments for a validated claim.
    
    Args:
        conversation_id: The conversation ID to associate the attachments with
        user_id: The user ID uploading the attachments
        files: List of attachment files to upload and process
        agent_service: Service for processing files and generating responses
        conversation_service: Service for managing conversations
        
    Returns:
        FileUploadResponse: Processing results and comprehensive claim overview
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid or conversation is in wrong status
            - 404: If the conversation doesn't exist
            - 500: If there's an error processing the attachments
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )

        # Verify conversation exists and is in correct status
        conversation = await conversation_service.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        if conversation.status != "waiting_for_attachments":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Conversation must be in 'waiting_for_attachments' status. Current status: {conversation.status}"
            )

        # Validate files
        if not files or len(files) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )

        # Check total file size (limit to 50MB for multiple files)
        total_size = 0
        for file in files:
            file_content = await file.read()
            total_size += len(file_content)
            # Reset file position for later processing
            await file.seek(0)
            
        if total_size > 50 * 1024 * 1024:  # 50MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Total file size too large. Maximum size is 50MB for all attachments."
            )

        # Process attachments
        attachment_results = await agent_service.process_attachments(
            files=files,
            conversation_id=conversation_id,
            user_id=user_id
        )

        # Update conversation status to claim_docs_discussion
        await conversation_service.update_conversation_status(
            conversation_id, 
            ConversationStatus.CLAIM_DOCS_DISCUSSION
        )

        return attachment_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading attachments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process attachments: {str(e)}"
        )

@router.get(
    "/statement-of-claim/{conversation_id}",
    summary="Get statement of claim data for a conversation",
    description="""
    Retrieve the statement of claim data associated with a conversation.
    
    This endpoint returns the processed document data including extracted fields,
    validation results, and file metadata.
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Returns:
    - Statement of claim data if exists, null otherwise
    """
)
async def get_statement_of_claim(
    conversation_id: str,
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Get statement of claim data for a conversation.
    
    Args:
        conversation_id: The conversation ID to retrieve data for
        agent_service: Service for retrieving statement of claim data
        
    Returns:
        Statement of claim data or null if not found
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid
            - 500: If there's an error retrieving the data
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )

        # Retrieve statement of claim data
        statement_data = await agent_service.get_statement_of_claim(conversation_id)
        
        return statement_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving statement of claim: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statement of claim: {str(e)}"
        )

@router.get(
    "/file/{conversation_id}",
    response_model=FileInfoResponse,
    summary="Get file information and download link for a conversation",
    description="""
    Retrieve file information and generate a secure download link for documents uploaded in a conversation.
    
    This endpoint:
    1. Validates the conversation exists
    2. Retrieves the statement of claim data
    3. Generates a secure download link for the file
    4. Returns file metadata and access information
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Returns:
    - File information including download link, metadata, and access details
    """
)
async def get_file_info(
    conversation_id: str,
    agent_service: AgentService = Depends(get_agent_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Get file information and download link for a conversation.
    
    Args:
        conversation_id: The conversation ID to retrieve file info for
        agent_service: Service for retrieving statement of claim data
        conversation_service: Service for managing conversations
        
    Returns:
        File information with download link and metadata
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid
            - 404: If the conversation or file doesn't exist
            - 500: If there's an error retrieving the file info
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )

        # Verify conversation exists
        conversation = await conversation_service.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Get statement of claim data
        statement_data = await agent_service.get_statement_of_claim(conversation_id)
        if not statement_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file found for this conversation"
            )

        # Generate secure download link
        file_info = await agent_service.generate_file_download_link(statement_data)
        
        return file_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving file info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve file info: {str(e)}"
        )

@router.get(
    "/file/{conversation_id}/download",
    summary="Download file directly",
    description="""
    Download the file directly from Azure Blob Storage.
    
    This endpoint:
    1. Validates the conversation exists
    2. Retrieves the file from Azure Blob Storage
    3. Streams the file content to the client
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Returns:
    - File content as a stream with appropriate headers
    """
)
async def download_file(
    conversation_id: str,
    agent_service: AgentService = Depends(get_agent_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Download file directly from Azure Blob Storage.
    
    Args:
        conversation_id: The conversation ID to download file for
        agent_service: Service for retrieving and streaming files
        conversation_service: Service for managing conversations
        
    Returns:
        File content stream
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid
            - 404: If the conversation or file doesn't exist
            - 500: If there's an error downloading the file
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )

        # Verify conversation exists
        conversation = await conversation_service.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Get statement of claim data
        statement_data = await agent_service.get_statement_of_claim(conversation_id)
        if not statement_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file found for this conversation"
            )

        # Stream file content
        file_stream = await agent_service.stream_file_content(statement_data)
        
        return file_stream
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )

@router.post(
    "/reload-prompts",
    summary="Force reload all prompts",
    description="""
    Force reload all prompts from disk to pick up any changes.
    
    This endpoint is useful for development and testing when prompt files have been modified.
    
    Returns:
    - Success message indicating prompts have been reloaded
    """
)
async def reload_prompts(
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Force reload all prompts.
    
    Args:
        agent_service: Service for managing prompts
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 
            - 500: If there's an error reloading the prompts
    """
    try:
        agent_service.reload_prompts()
        return {"message": "Prompts reloaded successfully"}
        
    except Exception as e:
        logger.error(f"Error reloading prompts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload prompts: {str(e)}"
        ) 

@router.get(
    "/attachments/{conversation_id}/overview",
    summary="Generate human lawyer-style attachments overview",
    description="Build a grounded overview of attachments and their purpose using full claim text and attachments content."
)
async def attachments_overview(
    conversation_id: str,
):
    from bson import ObjectId
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")
    try:
        from app.modules.attachments.service import AttachmentsAnalysisService
        svc = AttachmentsAnalysisService()
        content = await svc.generate_attachments_overview(conversation_id)
        return {"status": "success", "content": content}
    except Exception as e:
        logger.error(f"attachments_overview error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate attachments overview") 