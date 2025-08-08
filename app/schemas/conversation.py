from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from bson import ObjectId
from datetime import datetime
from enum import Enum

class ConversationStatus(str, Enum):
    """Enumeration of conversation statuses."""
    WAITING_FOR_CLAIM = "waiting_for_claim"
    CLAIM_UPLOADED = "claim_uploaded"
    CLAIM_VALIDATED = "claim_validated"
    CLAIM_REJECTED = "claim_rejected"
    WAITING_FOR_ATTACHMENTS = "waiting_for_attachments"
    CLAIM_DISCUSSION = "claim_discussion"
    CLAIM_DOCS_DISCUSSION = "claim_docs_discussion"
    RESPONSE_DRAFTING = "response_drafting"
    RESPONSE_COMPLETED = "response_completed"
    CLOSED = "closed"

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any, handler: Any) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        if not ObjectId.is_valid(str(v)):
            raise ValueError("Invalid ObjectId")
        return str(v)

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: Any,
        handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {
            "type": "string",
            "description": "MongoDB ObjectId",
            "example": "507f1f77bcf86cd799439011"
        }

    def __str__(self) -> str:
        return str(self)

    def __repr__(self) -> str:
        return f"PyObjectId('{str(self)}')"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ObjectId):
            return str(self) == str(other)
        return super().__eq__(other)

class ConversationBase(BaseModel):
    name: str
    status: ConversationStatus = Field(default=ConversationStatus.WAITING_FOR_CLAIM, description="Current status of the conversation")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "New Conversation",
                "status": "waiting_for_claim"
            }
        }
    )

class ConversationCreate(ConversationBase):
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "New Conversation",
                "user_id": "user123"
            }
        }
    )

class ConversationUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[ConversationStatus] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Conversation Name",
                "status": "claim_uploaded"
            }
        }
    )

class ConversationResponse(ConversationBase):
    id: str = Field(alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "name": "New Conversation",
                "user_id": "user123",
                "status": "waiting_for_claim",
                "created_at": "2024-03-20T10:00:00Z"
            }
        }
    )

class ConversationList(BaseModel):
    conversations: List[ConversationResponse]
    total: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversations": [
                    {
                        "_id": "507f1f77bcf86cd799439011",
                        "name": "New Conversation",
                        "user_id": "user123",
                        "created_at": "2024-03-20T10:00:00Z"
                    }
                ],
                "total": 1
            }
        }
    )

class PaginatedConversationResponse(BaseModel):
    conversations: List[ConversationResponse]
    meta_data: "MetaData"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversations": [
                    {
                        "_id": "507f1f77bcf86cd799439011",
                        "name": "New Conversation",
                        "user_id": "user123",
                        "created_at": "2024-03-20T10:00:00Z"
                    }
                ],
                "meta_data": {
                    "total": 1,
                    "page": 1,
                    "page_size": 10,
                    "total_pages": 1
                }
            }
        }
    )

class MetaData(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 1,
                "page": 1,
                "page_size": 10,
                "total_pages": 1
            }
        }
    ) 