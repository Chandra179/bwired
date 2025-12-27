"""
Chat API - Unified agentic endpoint for document interactions
"""
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from internal.server.server import ServerState

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: Request,
    chat_request: ChatRequest
):
    """
    Unified chat endpoint - Agent handles routing to appropriate tools.
    
    The agent automatically determines whether to:
    - Search documents
    - Index new content
    - Ask for clarification
    
    Args:
        req: FastAPI request object
        chat_request: User's chat message
        
    Returns:
        Agent's response
        
    Raises:
        HTTPException: If agent execution fails
    """
    state: ServerState = req.app.state.server_state
    
    logger.info(f"[CHAT] Received message: '{chat_request.message}'")
    
    if not state.agent:
        raise HTTPException(
            status_code=500,
            detail="Agent not initialized. Check server logs."
        )
    
    try:
        result = await state.agent.run(
            chat_request.message,
            deps=state
        )
        
        response_text = result.output
        logger.info(f"[CHAT] Agent response generated successfully")
        
        return ChatResponse(response=response_text)
        
    except Exception as e:
        logger.error(f"[CHAT] Agent execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Chat request failed: {str(e)}"
        )