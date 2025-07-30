from typing import Optional, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class MessageBase(BaseModel):
    conversation_id: str
    message_data: dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "507f1f77bcf86cd799439011",
                "message_data": {
                    "type": "user_message",
                    "content": "Hello, how can you help me?"
                }
            }
        }
    )

class MessageCreate(MessageBase):
    user_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "507f1f77bcf86cd799439011",
                "user_id": "user123",
                "message_data": {
                    "type": "user_message",
                    "content": "Hello, how can you help me?"
                }
            }
        }
    )

class MessageResponse(MessageBase):
    id: str = Field(alias="_id")
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "conversation_id": "507f1f77bcf86cd799439011",
                "user_id": "user123",
                "message_data": {
                    "type": "user_message",
                    "content": "Hello, how can you help me?"
                },
                "created_at": "2024-03-20T10:00:00Z"
            }
        }
    )

class MessageList(BaseModel):
    messages: list[MessageResponse]
    total: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "messages": [
                    {
                        "_id": "507f1f77bcf86cd799439011",
                        "conversation_id": "507f1f77bcf86cd799439011",
                        "user_id": "user123",
                        "message_data": {
                            "type": "user_message",
                            "content": "Hello, how can you help me?"
                        },
                        "created_at": "2024-03-20T10:00:00Z"
                    }
                ],
                "total": 1
            }
        }
    )

class PaginatedMessageResponse(BaseModel):
    messages: List[MessageResponse]
    meta_data: "MetaData"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "messages": [
                    {
                        "_id": "507f1f77bcf86cd799439011",
                        "conversation_id": "507f1f77bcf86cd799439011",
                        "user_id": "user123",
                        "message_data": {
                            "type": "user_message",
                            "content": "Hello, how can you help me?"
                        },
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