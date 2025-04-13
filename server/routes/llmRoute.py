from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from pydantic import BaseModel
from controllers.llmController import LLMController

# Create the router
router = APIRouter()

# Define request model
class QuestionRequest(BaseModel):
    query: str
    
    class Config:
        schema_extra = {
            "example": {
                "query": "What is the capital of France?"
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
    
    # Get the response from the LLM
    response = await llm_controller.ask_question(request.query)
    
    return response