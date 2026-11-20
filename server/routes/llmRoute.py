from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, EmailStr
from controllers.llmController import LLMController, Message
from middlewares.conn_llm import get_openai_client
from middlewares.conn_database import get_db
from sqlalchemy.orm import Session
from openai import OpenAI
import asyncio
import json
import logging

router = APIRouter()

class QuestionRequest(BaseModel):
    query: str
    chat_id: Optional[str] = None
    user_email: Optional[EmailStr] = None
    chat_history: Optional[List[Message]] = []

    class Config:
        schema_extra = {
            "example": {
                "query": "What are popular tourist destinations in Japan?",
                "chat_id": None,
                "user_email": "user@example.com",
                "chat_history": []
            }
        }

@router.post("/ask-question")
async def ask_question(
    request: QuestionRequest,
    openai_client: OpenAI = Depends(get_openai_client),
    db: Session = Depends(get_db)
):
    logging.info(f"Database connection available: {db is not None}")

    controller = LLMController(openai_client)

    async def generate():
        task = asyncio.create_task(controller.ask_question(
            query=request.query,
            chat_history=request.chat_history,
            chat_id=request.chat_id,
            user_email=request.user_email,
            db=db
        ))
        # Send a space every 10s to keep Heroku's connection alive (30s first-byte timeout)
        while not task.done():
            yield b" "
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=10)
                break
            except asyncio.TimeoutError:
                continue
        result = await task
        yield json.dumps(result).encode()

    return StreamingResponse(generate(), media_type="application/json")
