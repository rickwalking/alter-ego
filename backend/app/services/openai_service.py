"""OpenAI integration service for chat functionality"""
import os
from pathlib import Path
from openai import AsyncOpenAI
from app.config import settings


# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Load knowledge base at startup
knowledge_base_path = Path(settings.KNOWLEDGE_BASE_PATH)
try:
    with open(knowledge_base_path, "r", encoding="utf-8") as f:
        KNOWLEDGE_BASE = f.read()
    print(f"✓ Knowledge base loaded from {knowledge_base_path}")
except FileNotFoundError:
    print(f"⚠ Warning: Knowledge base file not found at {knowledge_base_path}")
    KNOWLEDGE_BASE = ""


async def get_chat_response(message: str) -> str:
    """
    Get chat response from OpenAI based on user message and knowledge base.

    Args:
        message: User's input message

    Returns:
        AI-generated response string

    Raises:
        Exception: If OpenAI API call fails
    """
    try:
        # Build system prompt with PERSON_NAME and knowledge base
        system_prompt = f"""You are {settings.PERSON_NAME}. Answer questions about your career and personal background based on the provided knowledge base. Be conversational and helpful.

Knowledge Base:
{KNOWLEDGE_BASE}"""

        # Call OpenAI API
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"✗ OpenAI API error: {str(e)}")
        raise Exception(f"Failed to get chat response: {str(e)}")
