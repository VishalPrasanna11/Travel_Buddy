from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, EmailStr
from controllers.llmController import LLMController

# Create the router
router = APIRouter()

# Define message model
class Message(BaseModel):
    role: str
    content: str

# Define request model
class QuestionRequest(BaseModel):
    query: str
    chat_history: List[Message] = []
    chat_id: str
    user_email: EmailStr
    
    class Config:
        schema_extra = {
            "example": {
                "query": "What is the capital of France?",
                "chat_history": [
                    {"role": "user", "content": "Plan a vacation to Paris?"},
                    {"role": "assistant", "content": "Planning a vacation to Paris is an exciting endeavor! Here's a suggested itinerary..."}
                ],
                "chat_id": "chat_123456",
                "user_email": "user@example.com"
            }
        }

# Define response model
class QuestionResponse(BaseModel):
    status: str
    answer: str
    model: str

# Endpoint to ask a question to the LLM
@router.post("/ask-question", response_model=QuestionResponse)
async def ask_question(
    request: QuestionRequest,
    llm_controller: LLMController = Depends()
) -> Dict[str, Any]:
 
    if not request.query or request.query.strip() == "":
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    

    response = await llm_controller.ask_question(
        query=request.query, 
        chat_history=request.chat_history,
        chat_id=request.chat_id,
        user_email=request.user_email
    )
    
    return response