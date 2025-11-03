"""API routes for chat functionality"""
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services import get_chat_response

# Request/Response Models
class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., min_length=1, description="User message")

class ChatResponse(BaseModel):
    """Chat response model"""
    response: str = Field(..., description="AI-generated response")
    timestamp: str = Field(..., description="Response timestamp in ISO8601 format")

# Create router
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process chat message and return AI response.

    Args:
        request: ChatRequest with user message

    Returns:
        ChatResponse with AI-generated response and timestamp

    Raises:
        HTTPException: If OpenAI API call fails
    """
    try:
        # Get response from OpenAI service
        ai_response = await get_chat_response(request.message)

        # Return response with timestamp
        return ChatResponse(
            response=ai_response,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )
