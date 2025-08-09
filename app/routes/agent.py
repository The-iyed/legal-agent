from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.database import get_database
from app.modules.agent.service import AgentService
from app.modules.conversation.service import ConversationService
from app.modules.message.service import MessageService
from app.schemas.agent import QueryRequest, QueryResponse, FileUploadRequest, FileUploadResponse, FileInfoResponse
from app.schemas.message import MessageCreate
from bson import ObjectId
import logging
import re
from typing import Optional, Any, List, Union
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
    files: List[UploadFile] = File(..., description="Attachment files to upload"),
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

        # Verify conversation exists
        conversation = await conversation_service.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
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

class LegalBasisRequest(BaseModel):
    conversation_id: str
    user_id: Optional[str] = None

@router.post(
    "/legal-basis/analyze",
    response_model=QueryResponse,
    summary="Advance to legal basis phase and generate analysis",
    description="Analyzes the claim and current attachments without Azure Search; then invites user to proceed or add more attachments."
)
async def analyze_legal_basis(
    request: LegalBasisRequest,
    agent_service: AgentService = Depends(get_agent_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        if not ObjectId.is_valid(request.conversation_id):
            raise HTTPException(status_code=400, detail="Invalid conversation ID format")
        conversation = await conversation_service.get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Fetch full claim text
        claim_doc = await agent_service.get_statement_of_claim(request.conversation_id)
        claim_text = (claim_doc or {}).get("raw_text", "")

        # Fetch attachments text and merge
        db = agent_service.db
        attachments_texts = []
        cursor = db.attachments.find({"conversation_id": request.conversation_id}).sort("created_at", 1)
        async for att in cursor:
            t = ((att.get("extracted_content", {}) or {}).get("raw_text", "") or "").strip()
            if t:
                attachments_texts.append(t)
        attachments_merged = "\n\n---\n".join(attachments_texts)

        # Build context for agent
        context = [
            {"_key": "claim_text", "_value": claim_text},
            {"_key": "attachments_text", "_value": attachments_merged}
        ]

        # Run LegalBasisAgent WITHOUT Azure Search
        from app.modules.semantic_kernel.registry.agent_registry import AgentRegistry
        registry = AgentRegistry()
        agent_class = registry.get_agent_class("legal_basis")
        if not agent_class:
            raise HTTPException(status_code=500, detail="LegalBasis agent not registered")
        agent = agent_class(settings=agent_service.settings)
        result = await agent.execute_without_search("__LEGAL_BASIS__", "", context=context)
        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        # Update status to LEGAL_BASIS
        await conversation_service.update_conversation_status(request.conversation_id, ConversationStatus.LEGAL_BASIS)

        content = result.get("response", {}).get("content", "")

        # Normalize markdown: convert H3/H2/H1 to bold headings, remove leading hashes
        def normalize_md(text: str) -> str:
            text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
            text = re.sub(r"^([\p{L}0-9].*):\s*$", r"**\\1**", text, flags=re.MULTILINE)
            return text

        try:
            import regex as _re  # better unicode categories
            def _norm_unicode(t: str) -> str:
                t = _re.sub(r"^#{1,6}\s*", "", t, flags=_re.MULTILINE)
                # Keep markdown lists/code blocks but make section headers bold if they are on their own line
                t = _re.sub(r"^(?:\*\*|__)?([\p{L}\p{N}].{0,80}?)(?:\:)?\s*$", r"**\1**", t, flags=_re.MULTILINE)
                return t
            content = _norm_unicode(content)
        except Exception:
            content = normalize_md(content)

        # Parse attachments_status block to decide next step
        has_all = None
        missing = []
        try:
            m = re.search(r"\[attachments_status\](.*?)\[/attachments_status\]", content, flags=re.DOTALL|re.IGNORECASE)
            if m:
                block = m.group(1)
                has_line = re.search(r"HAS_ALL:\s*(yes|no)", block, flags=re.IGNORECASE)
                if has_line:
                    has_all = has_line.group(1).lower() == "yes"
                miss_line = re.search(r"MISSING:\s*(.*)", block)
                if miss_line:
                    miss_val = miss_line.group(1).strip()
                    if miss_val and miss_val.lower() != "<names>" and miss_val != "":
                        missing = [x.strip() for x in miss_val.split(',') if x.strip()]
                # Remove the block from the user-facing content
                content = re.sub(r"\[attachments_status\].*?\[/attachments_status\]", "", content, flags=re.DOTALL|re.IGNORECASE).strip()
        except Exception:
            has_all = None

        # Store agent message in conversation history
        try:
            await agent_service._store_agent_message(
                content,
                {"query_type": "legal_basis", "retrieval": "none", "attachments_status": ("all" if has_all else ("missing" if has_all is False else "unknown")), "missing": missing},
                request.conversation_id,
                {"agent_type": "legal_basis", "prompt_type": "analysis", "confidence": 1.0, "reasoning": "legal basis analysis without search"}
            )
        except Exception as e:
            logger.warning(f"Failed to store legal basis message: {e}")

        # Always ask for attachments explicitly; do not auto‑finalize here
        req_text = "نحتاج إلى استكمال المرفقات الداعمة قبل الانتقال للمرحلة التالية."
        if missing:
            req_text += "\nالمرفقات المطلوبة: " + ", ".join(missing)
        req_text += "\nالرجاء رفعها عبر مسار: POST /agents/legal-basis/attachments-or-proceed، أو أبلغني أنك لا تملكها لنكمل بما لدينا." 
        await agent_service._store_agent_message(
            req_text,
            {"query_type": "attachments_requirements", "missing": missing},
            request.conversation_id,
            {"agent_type": "chat", "prompt_type": "waiting_for_attachments", "confidence": 1.0}
        )
        combined = content + "\n\n" + req_text
        return {"response": combined, "metadata": {"agent_type": "legal_basis", "prompt_type": "analysis", "confidence": 1.0}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing legal basis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze legal basis: {e}") 

@router.post(
    "/legal-basis/update-with-attachments",
    response_model=QueryResponse,
    summary="Update legal basis analysis using newly uploaded attachments",
    description="Generates a concise addendum to the prior legal-basis analysis based on new attachments; stores the update as a message."
)
async def update_legal_basis_with_attachments(
    conversation_id: str = Body(..., embed=True),
    agent_service: AgentService = Depends(get_agent_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(status_code=400, detail="Invalid conversation ID format")
        conversation = await conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Fetch prior legal-basis message content (latest)
        messages = await agent_service.message_service.get_conversation_messages(conversation_id, page=1, page_size=200)
        previous_analysis = ""
        if messages and hasattr(messages, 'messages'):
            # iterate reversed to find last legal_basis
            for m in reversed(messages.messages):
                md = m.message_data.get("metadata", {}) if isinstance(m.message_data, dict) else {}
                if md.get("agent_type") == "legal_basis" or md.get("query_type") == "legal_basis":
                    previous_analysis = m.message_data.get("content", "")
                    break

        # Fetch full claim text
        claim_doc = await agent_service.get_statement_of_claim(conversation_id)
        claim_text = (claim_doc or {}).get("raw_text", "")

        # Collect only newly added attachments since last update: for simplicity take latest 10
        db = agent_service.db
        attachments_texts = []
        cursor = db.attachments.find({"conversation_id": conversation_id}).sort("created_at", -1).limit(10)
        async for att in cursor:
            t = ((att.get("extracted_content", {}) or {}).get("raw_text", "") or "").strip()
            if t:
                attachments_texts.append(t)
        new_attachments_text = "\n\n---\n".join(attachments_texts)

        # Run update addendum through LegalBasisAgent
        from app.modules.semantic_kernel.registry.agent_registry import AgentRegistry
        registry = AgentRegistry()
        agent_class = registry.get_agent_class("legal_basis")
        if not agent_class:
            raise HTTPException(status_code=500, detail="LegalBasis agent not registered")
        agent = agent_class(settings=agent_service.settings)
        addendum = await agent.update_with_new_attachments(previous_analysis, claim_text, new_attachments_text)

        # Keep/ensure status at LEGAL_BASIS
        try:
            await conversation_service.update_conversation_status(conversation_id, ConversationStatus.LEGAL_BASIS)
        except Exception:
            pass

        # Store the addendum as an agent message
        await agent_service._store_agent_message(
            addendum,
            {"query_type": "legal_basis_update", "attachments_count_considered": len(attachments_texts)},
            conversation_id,
            {"agent_type": "legal_basis", "prompt_type": "update", "confidence": 1.0}
        )

        return {"response": addendum, "metadata": {"agent_type": "legal_basis", "prompt_type": "update", "confidence": 1.0}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating legal basis with attachments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update legal basis: {e}")

@router.post(
    "/attachments/request",
    response_model=QueryResponse,
    summary="Ask user for specific attachments or confirm proceeding to next phase",
    description="In WAITING_FOR_ATTACHMENTS state, generate a focused message asking for concrete attachments that strengthen the municipality's position; if user confirms no attachments, advance to legal basis phase."
)
async def request_attachments_or_proceed(
    conversation_id: str = Body(...),
    confirm_proceed: bool = Body(False, description="If true, proceed to legal basis phase immediately"),
    agent_service: AgentService = Depends(get_agent_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(status_code=400, detail="Invalid conversation ID format")
        conversation = await conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Only operate in WAITING_FOR_ATTACHMENTS, CLAIM_DISCUSSION, or CLAIM_DOCS_DISCUSSION
        if conversation.status not in [ConversationStatus.WAITING_FOR_ATTACHMENTS, ConversationStatus.CLAIM_DISCUSSION, ConversationStatus.CLAIM_DOCS_DISCUSSION]:
            raise HTTPException(status_code=400, detail=f"Invalid status for attachment request: {conversation.status}")

        if confirm_proceed:
            # Move to legal basis phase
            await conversation_service.update_conversation_status(conversation_id, ConversationStatus.LEGAL_BASIS)
            content = (
                "تم استلام تأكيدك. سننتقل الآن إلى مرحلة: تحليل القضايا القانونية وإعداد الاعتراضات، ثم مناقشة صياغة الوثائق القانونية."
            )
            await agent_service._store_agent_message(
                content,
                {"query_type": "attachments_request", "action": "proceed_to_legal_basis"},
                conversation_id,
                {"agent_type": "chat", "prompt_type": "waiting_for_attachments", "confidence": 1.0}
            )
            return {"response": content, "metadata": {"status": "legal_basis"}}

        # Ensure we are in WAITING_FOR_ATTACHMENTS to enforce strict prompt behavior
        if conversation.status != ConversationStatus.WAITING_FOR_ATTACHMENTS:
            try:
                await conversation_service.update_conversation_status(conversation_id, ConversationStatus.WAITING_FOR_ATTACHMENTS)
            except Exception:
                pass

        # Generate focused request using the updated waiting_for_attachments prompt via supervisor
        convo_data = await agent_service._get_conversation_with_status(conversation_id)
        prompt = convo_data.get("prompt") if convo_data else None
        history = await agent_service._get_conversation_history(conversation_id)
        supervisor_result = await agent_service.supervisor.route_query(
            query="ما هي المرفقات المطلوبة لدعم موقف الأمانة؟",
            context=history,
            system_prompt=prompt,
            conversation_status=ConversationStatus.WAITING_FOR_ATTACHMENTS
        )
        content, agent_metadata = agent_service._extract_response_data(supervisor_result)
        await agent_service._store_agent_message(
            content,
            {"query_type": "attachments_request"},
            conversation_id,
            supervisor_result
        )
        return {"response": content, "metadata": {"agent_type": supervisor_result.get("agent_type"), "prompt_type": supervisor_result.get("prompt_type"), "confidence": supervisor_result.get("confidence")}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in attachments request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to request attachments: {e}") 

@router.post(
    "/legal-basis/orient",
    response_model=QueryResponse,
    summary="Confirm and announce next-phase actions",
    description="Returns a confirmation message that the system will now start تحليل القضايا القانونية وإعداد الاعتراضات باستخدام Azure AI Search, followed by مناقشة صياغة الوثائق القانونية."
)
async def orient_to_legal_basis(
    conversation_id: str = Body(..., embed=True),
    agent_service: AgentService = Depends(get_agent_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(status_code=400, detail="Invalid conversation ID format")
        conversation = await conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        content = (
            "تم تأكيد الانتقال إلى المرحلة التالية.\n\n"
            "سنبدأ الآن بـ: \n"
            "1) تحليل القضايا القانونية وإعداد الاعتراضات باستخدام Azure AI Search استناداً إلى صحيفة الدعوى والمرفقات.\n"
            "2) مناقشة صياغة الوثائق القانونية (المذكرات/اللائحة) والبنود المقترحة للصياغة.\n\n"
            "سأبقيك على اطلاع بالخطوات والنتائج تباعاً."
        )

        await agent_service._store_agent_message(
            content,
            {"query_type": "orientation", "next": "response_drafting"},
            conversation_id,
            {"agent_type": "chat", "prompt_type": "default", "confidence": 1.0}
        )
        return {"response": content, "metadata": {"agent_type": "chat", "prompt_type": "default", "confidence": 1.0}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending orientation message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send orientation message: {e}") 

# Note: multipart form is defined via function signature; no Pydantic body model needed here.

@router.post(
    "/legal-basis/attachments-or-proceed",
    response_model=QueryResponse,
    summary="Upload attachments to refresh legal analysis or proceed to drafting",
    description="If files are provided, they are processed and legal basis is rerun. If proceed=true (and no files), user is oriented to proceed to drafting; status may update to response_drafting.",
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "conversation_id": {"type": "string"},
                            "proceed": {"type": "boolean"},
                            "files": {
                                "type": "array",
                                "items": {"type": "string", "format": "binary"}
                            }
                        },
                        "required": ["conversation_id"]
                    }
                }
            }
        }
    }
)
async def legal_basis_attachments_or_proceed(
    conversation_id: str = Form(..., description="Conversation ID"),
    proceed: bool = Form(False, description="Set true to proceed without uploading files"),
    files: Optional[Union[UploadFile, List[UploadFile]]] = File(None, description="Attachment files to upload (single or multiple)"),
    agent_service: AgentService = Depends(get_agent_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(status_code=400, detail="Invalid conversation ID format")
        conversation = await conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Normalize files: accept single or list, drop empty
        if files:
            if isinstance(files, UploadFile):
                files = [files]
            else:
                files = [f for f in files if getattr(f, "filename", None)]

        # Case 1: user uploaded attachments → process and rerun legal basis
        if files and len(files) > 0:
            # Disallow adding attachments after proceeding to drafting or later
            if conversation.status in [ConversationStatus.RESPONSE_DRAFTING, ConversationStatus.RESPONSE_COMPLETED, ConversationStatus.CLOSED]:
                raise HTTPException(status_code=400, detail=f"Attachments are not allowed after proceeding to drafting. Current status: {conversation.status}")

            # Process attachments
            attach_result = await agent_service.process_attachments(files, conversation_id, user_id="system")

            # Re-run legal basis analysis with full claim + new attachments
            class _LBReq(BaseModel):
                conversation_id: str
                user_id: Optional[str] = None
            lb_req = _LBReq(conversation_id=conversation_id)
            result = await analyze_legal_basis(lb_req, agent_service, conversation_service)  # reuse route logic
            return result

        # Case 2: no attachments. If proceed flag set → update status and orient/proceed
        if proceed:
            # Update status to RESPONSE_DRAFTING as next phase for document drafting
            await conversation_service.update_conversation_status(conversation_id, ConversationStatus.RESPONSE_DRAFTING)

            # Confirm proceeding without asking again
            content = (
                "تم تأكيد انتقالك إلى المرحلة التالية.\n\n"
                "سنبدأ الآن في تحليل القضايا القانونية وإعداد الاعتراضات ثم مناقشة صياغة الوثائق القانونية بناءً على النتائج الحالية."
            )

            await agent_service._store_agent_message(
                content,
                {"query_type": "proceed_to_drafting"},
                conversation_id,
                {"agent_type": "chat", "prompt_type": "default", "confidence": 1.0}
            )

            return {"response": content, "metadata": {"agent_type": "chat", "prompt_type": "default", "confidence": 1.0}}

        # Case 3: neither files nor proceed → Ask the question via advisor
        from app.modules.semantic_kernel.registry.agent_registry import AgentRegistry
        registry = AgentRegistry()
        advisor_class = registry.get_agent_class("phase_advisor")
        if not advisor_class:
            raise HTTPException(status_code=500, detail="Phase advisor agent not registered")
        advisor = advisor_class(settings=agent_service.settings)
        advisor_res = await advisor.execute("__ADVISE__", "", context=None)
        content = (advisor_res or {}).get("response", {}).get("content", "")
        await agent_service._store_agent_message(
            content,
            {"query_type": "advisor_prompt"},
            conversation_id,
            {"agent_type": "phase_advisor", "prompt_type": "legal_basis_next_steps", "confidence": 1.0}
        )
        return {"response": content, "metadata": {"agent_type": "phase_advisor", "prompt_type": "legal_basis_next_steps", "confidence": 1.0}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in legal_basis/attachments-or-proceed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to handle attachments or proceed: {e}") 

@router.post(
    "/legal-basis/finalize",
    response_model=QueryResponse,
    summary="Run final legal-basis with Azure Search and move to drafting discussion",
    description="Requires the conversation to have proceeded to drafting. Runs the full pipeline (issues → plan → Azure AI Search → analysis → defense) and stores the result."
)
async def finalize_legal_basis(
    conversation_id: str = Body(..., embed=True),
    agent_service: AgentService = Depends(get_agent_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(status_code=400, detail="Invalid conversation ID format")
        conversation = await conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Must have proceeded to drafting
        if conversation.status != ConversationStatus.RESPONSE_DRAFTING:
            raise HTTPException(status_code=400, detail=f"Conversation must be in 'response_drafting' after proceed. Current: {conversation.status}")

        # Build context
        claim_doc = await agent_service.get_statement_of_claim(conversation_id)
        claim_text = (claim_doc or {}).get("raw_text", "")
        db = agent_service.db
        attachments_texts = []
        cursor = db.attachments.find({"conversation_id": conversation_id}).sort("created_at", 1)
        async for att in cursor:
            t = ((att.get("extracted_content", {}) or {}).get("raw_text", "") or "").strip()
            if t:
                attachments_texts.append(t)
        attachments_merged = "\n\n---\n".join(attachments_texts)
        context = [
            {"_key": "claim_text", "_value": claim_text},
            {"_key": "attachments_text", "_value": attachments_merged}
        ]

        # Run LegalBasisAgent with Azure Search (full pipeline)
        from app.modules.semantic_kernel.registry.agent_registry import AgentRegistry
        registry = AgentRegistry()
        agent_class = registry.get_agent_class("legal_basis")
        if not agent_class:
            raise HTTPException(status_code=500, detail="LegalBasis agent not registered")
        agent = agent_class(settings=agent_service.settings)
        result = await agent.execute("__LEGAL_BASIS_FINAL__", "", context=context)
        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        content = result.get("response", {}).get("content", "")

        # Keep status at RESPONSE_DRAFTING for continued discussion
        try:
            await conversation_service.update_conversation_status(conversation_id, ConversationStatus.RESPONSE_DRAFTING)
        except Exception:
            pass

        # Store final message
        await agent_service._store_agent_message(
            content,
            {"query_type": "legal_basis_final", "search": "azure_ai_search", "attachments_count_considered": len(attachments_texts)},
            conversation_id,
            {"agent_type": "legal_basis", "prompt_type": "analysis", "confidence": 1.0}
        )

        return {"response": content, "metadata": {"agent_type": "legal_basis", "prompt_type": "analysis", "confidence": 1.0}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finalizing legal basis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to finalize legal basis: {e}") 

@router.post(
    "/legal-basis/generate-pleading",
    response_model=QueryResponse,
    summary="Generate formal legal pleading memo",
    description="Generates a structured legal pleading (لائحة الرد) using claim, attachments, and the latest final analysis. Sections: الوقائع، الدفع الشكلي، الدفع الموضوعي، الخلاصة، الطلبات."
)
async def generate_legal_pleading(
    conversation_id: str = Body(..., embed=True),
    agent_service: AgentService = Depends(get_agent_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(status_code=400, detail="Invalid conversation ID format")
        conversation = await conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Gather context
        claim_doc = await agent_service.get_statement_of_claim(conversation_id)
        claim_text = (claim_doc or {}).get("raw_text", "")
        case_number = (claim_doc or {}).get("case_number", "—")
        plaintiff_name = (claim_doc or {}).get("plaintiff_name", "—")
        claim_meta = ""
        try:
            cd = claim_doc or {}
            fields = []
            for k in ("court", "filing_date", "case_type", "case_subject"):
                v = cd.get(k)
                if v:
                    fields.append(f"{k}: {v}")
            if fields:
                claim_meta = "; ".join(fields)
        except Exception:
            claim_meta = ""

        # attachments
        db = agent_service.db
        attachments_texts = []
        cursor = db.attachments.find({"conversation_id": conversation_id}).sort("created_at", 1)
        async for att in cursor:
            t = ((att.get("extracted_content", {}) or {}).get("raw_text", "") or "").strip()
            if t:
                attachments_texts.append(t)
        attachments_merged = "\n\n---\n".join(attachments_texts)
        attachments_meta = ""
        try:
            cursor2 = db.attachments.find({"conversation_id": conversation_id}).sort("created_at", 1)
            metas = []
            async for att in cursor2:
                fn = att.get("filename")
                pages = ((att.get("extracted_content", {}) or {}).get("total_pages"))
                metas.append(f"{fn or 'مرفق'}{('، صفحات: ' + str(pages)) if pages else ''}")
            attachments_meta = "; ".join(metas[:6])
        except Exception:
            attachments_meta = ""

        # latest final analysis (if any)
        final_analysis = ""
        try:
            messages = await agent_service.message_service.get_conversation_messages(conversation_id, page=1, page_size=200)
            if messages and hasattr(messages, 'messages'):
                for m in reversed(messages.messages):
                    md = m.message_data.get("metadata", {}) if isinstance(m.message_data, dict) else {}
                    if md.get("query_type") == "legal_basis_final":
                        final_analysis = m.message_data.get("content", "")
                        break
        except Exception:
            pass

        # Build a brief conversation context (last few agent lines that support the ministry)
        conv_context = ""
        try:
            history = await agent_service.message_service.get_conversation_messages(conversation_id, page=1, page_size=200, sort_desc=True)
            lines = []
            if history and hasattr(history, 'messages'):
                for m in history.messages:
                    md = m.message_data.get("metadata", {}) if isinstance(m.message_data, dict) else {}
                    if m.message_data.get("type") == "agent_response":
                        txt = m.message_data.get("content", "")
                        if txt:
                            lines.append(txt[:500])
                    if len(lines) >= 3:
                        break
            conv_context = "\n\n---\n".join(lines)
        except Exception:
            conv_context = ""

        # Generate via LegalBasisAgent
        from app.modules.semantic_kernel.registry.agent_registry import AgentRegistry
        registry = AgentRegistry()
        agent_class = registry.get_agent_class("legal_basis")
        if not agent_class:
            raise HTTPException(status_code=500, detail="LegalBasis agent not registered")
        agent = agent_class(settings=agent_service.settings)
        # Inject conversation context into the pleading prompt
        pleading_prompt = agent.prompt_manager.get_prompt("legal_basis", "pleading") or ""
        pleading_prompt = pleading_prompt.replace("{{CONV_CONTEXT}}", conv_context)
        pleading_prompt = pleading_prompt.replace("{{CLAIM_TEXT}}", claim_text or "").replace("{{ATTACHMENTS_TEXT}}", attachments_merged or "").replace("{{FINAL_ANALYSIS}}", final_analysis or "").replace("{{CASE_NUMBER}}", case_number or "—").replace("{{PLAINTIFF_NAME}}", plaintiff_name or "—").replace("{{CLAIM_META}}", claim_meta or "").replace("{{ATTACHMENTS_META}}", attachments_meta or "")
        pleading = await agent._process_query([{"role": "system", "content": pleading_prompt}])

        # Store once (idempotent): skip if the same pleading already exists for this conversation
        stored_ok = False
        try:
            existing = await agent_service.message_service.collection.find_one({
                "conversation_id": conversation_id,
                "message_data.metadata.query_type": "pleading",
                "message_data.content": pleading
            })
            if not existing:
                await agent_service._store_agent_message(
                    pleading,
                    {"query_type": "pleading", "case_number": case_number},
                    conversation_id,
                    {"agent_type": "legal_basis", "prompt_type": "pleading", "confidence": 1.0}
                )
            stored_ok = True
        except Exception:
            stored_ok = False

        # Verify stored
        stored_ok = False
        try:
            msgs = await agent_service.message_service.get_conversation_messages(conversation_id, page=1, page_size=50)
            if msgs and hasattr(msgs, 'messages'):
                for m in reversed(msgs.messages):
                    md = m.message_data.get("metadata", {}) if isinstance(m.message_data, dict) else {}
                    if md.get("query_type") == "pleading":
                        stored_ok = True
                        break
        except Exception:
            pass

        # Provide follow-up notice
        followup = "تم توليد لائحة الرد القانونية. أنا جاهز الآن للإجابة عن أي أسئلة تفصيلية تتعلق بالقضية ومرفقاتها وتحليلها النهائي."
        await agent_service._store_agent_message(
            followup,
            {"query_type": "pleading_followup"},
            conversation_id,
            {"agent_type": "chat", "prompt_type": "default", "confidence": 1.0}
        )

        combined = pleading + "\n\n---\n" + followup
        return {"response": combined, "metadata": {"agent_type": "legal_basis", "prompt_type": "pleading", "confidence": 1.0, "stored_ok": stored_ok}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating pleading: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate pleading: {e}") 