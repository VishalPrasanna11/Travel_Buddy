from fastapi import HTTPException, Depends
from typing import Dict, Any, List, Optional
import os
import re
from middlewares.conn_llm import get_openai_client
from middlewares.conn_database import get_db
from sqlalchemy.orm import Session
from openai import OpenAI
from pydantic import BaseModel, EmailStr
from controllers.llm_chat_historyController import LLMChatHistoryController
import logging
import traceback

# Set up more detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Message(BaseModel):
    role: str
    content: str

class LLMController:
    def __init__(self, openai_client: OpenAI = Depends(get_openai_client)):
        self.openai_client = openai_client
        self.travel_keywords = self._load_keywords()
        self.travel_system_prompt = self._load_system_prompt()
        # Common greetings and conversation starters to allow
        self.allowed_greetings = [
            "hi", "hello", "hey", "greetings", "good morning", 
            "good afternoon", "good evening", "howdy", "what's up",
            "how are you", "nice to meet you", "help", "start"
        ]
    
    def _load_keywords(self) -> List[str]:
        """Load travel keywords from file"""
        keywords_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'travel_keywords.txt')
        try:
            with open(keywords_path, 'r') as file:
                return [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            # Default keywords if file not found
            return ["travel", "vacation", "trip", "hotel", "flight", "destination"]
    
    def _load_system_prompt(self) -> str:
        """Load travel system prompt from file"""
        prompt_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'travel_instructions.txt')
        try:
            with open(prompt_path, 'r') as file:
                return file.read()
        except FileNotFoundError:
            # Default system prompt if file not found
            return "You are a Travel AI Assistant. Only answer travel-related questions."
    
    def is_greeting(self, query: str) -> bool:
        """Check if the query is a common greeting"""
        query_lower = query.lower().strip()
        
        # Check for exact matches first
        if query_lower in self.allowed_greetings:
            return True
            
        # Check if query starts with any greeting
        for greeting in self.allowed_greetings:
            if query_lower.startswith(greeting):
                return True
                
        return False
    
    def is_travel_related(self, query: str) -> bool:
        # Allow greetings and short conversation starters
        if self.is_greeting(query) or len(query.strip().split()) <= 3:
            return True
            
        query_lower = query.lower()
        
        # Check if any travel keyword is in the query
        for keyword in self.travel_keywords:
            if keyword.lower() in query_lower:
                return True
                
        return False
    
    def _check_chat_history_context(self, chat_history: List[Message]) -> bool:
        # If no history, can't determine context
        if not chat_history:
            return False
            
        # Check the last few messages for travel keywords
        recent_messages = chat_history[-3:] if len(chat_history) > 3 else chat_history
        
        for message in recent_messages:
            content = message.content.lower()
            for keyword in self.travel_keywords:
                if keyword.lower() in content:
                    return True
                    
        return False
    
    async def ask_question(
        self, 
        query: str, 
        chat_history: List[Message] = [], 
        chat_id: str = None, 
        user_email: str = None,
        db: Session = None
    ) -> Dict[str, Any]:
        try:
            logger.info(f"ask_question called with query: {query[:30]}..., chat_id: {chat_id}, user_email: {user_email}")
            
            # Debug DB connection
            if db:
                logger.info("Database connection provided")
            else:
                logger.warning("No database connection provided")
            
            # Initialize chat history controller if db is provided
            chat_history_controller = None
            if db:
                logger.info("Initializing chat history controller")
                chat_history_controller = LLMChatHistoryController(db)
            
            # Create a new chat session if none exists
            if not chat_id and chat_history_controller and user_email:
                logger.info(f"Creating new chat session for user: {user_email}")
                try:
                    session_result = await chat_history_controller.create_session(user_email)
                    chat_id = session_result["session"]["id"]
                    logger.info(f"New session created with ID: {chat_id}")
                except Exception as e:
                    logger.error(f"Error creating session: {str(e)}")
                    logger.error(traceback.format_exc())
                    raise
            
            # Load history from DB if needed
            if chat_id and chat_history_controller and not chat_history:
                logger.info(f"Loading chat history for session ID: {chat_id}")
                try:
                    history_result = await chat_history_controller.get_chat_history(chat_id)
                    chat_history = [
                        Message(role=msg["role"], content=msg["content"]) 
                        for msg in history_result["messages"]
                    ]
                    logger.info(f"Loaded {len(chat_history)} messages from history")
                except HTTPException as e:
                    logger.warning(f"HTTP Exception loading history: {str(e)}")
                    # If session not found or other error, create a new session
                    if e.status_code == 404 and user_email:
                        logger.info(f"Session not found, creating new one for: {user_email}")
                        session_result = await chat_history_controller.create_session(user_email)
                        chat_id = session_result["session"]["id"]
                        chat_history = []
                        logger.info(f"New session created with ID: {chat_id}")
                    else:
                        raise
                except Exception as e:
                    logger.error(f"Unexpected error loading history: {str(e)}")
                    logger.error(traceback.format_exc())
                    raise

            # Check if query is travel-related or if conversation context is travel-related
            context_is_travel = self._check_chat_history_context(chat_history)
            
            if not self.is_travel_related(query) and not context_is_travel:
                logger.info("Query is not travel-related, redirecting")
                
                # Save the user query even if we're going to redirect
                if chat_id and chat_history_controller:
                    logger.info(f"Saving user message to DB, session ID: {chat_id}")
                    try:
                        user_msg_result = await chat_history_controller.save_message(chat_id, "user", query)
                        logger.info(f"User message saved with ID: {user_msg_result.get('message', {}).get('id')}")
                    except Exception as e:
                        logger.error(f"Error saving user message: {str(e)}")
                        logger.error(traceback.format_exc())
                        # Continue anyway to provide response to user
                
                # Save the assistant's response to the database
                response_text = "I'm your Travel AI Assistant and can only help with travel-related questions. Feel free to ask me about destinations, trip planning, accommodations, or any other travel topics!"
                if chat_id and chat_history_controller:
                    logger.info(f"Saving assistant redirect message to DB, session ID: {chat_id}")
                    try:
                        asst_msg_result = await chat_history_controller.save_message(chat_id, "assistant", response_text)
                        logger.info(f"Assistant message saved with ID: {asst_msg_result.get('message', {}).get('id')}")
                    except Exception as e:
                        logger.error(f"Error saving assistant message: {str(e)}")
                        logger.error(traceback.format_exc())
                        # Continue anyway to provide response to user
                    
                return {
                    "status": "redirect",
                    "answer": response_text,
                    "model": "filter",
                    "chat_id": chat_id
                }
            
            # Save the user query to the database
            if chat_id and chat_history_controller:
                logger.info(f"Saving user message to DB, session ID: {chat_id}")
                try:
                    user_msg_result = await chat_history_controller.save_message(chat_id, "user", query)
                    logger.info(f"User message saved with ID: {user_msg_result.get('message', {}).get('id')}")
                except Exception as e:
                    logger.error(f"Error saving user message: {str(e)}")
                    logger.error(traceback.format_exc())
                    # Continue anyway to get AI response
                    
            # If it's a greeting, add a travel-focused context to the prompt
            if self.is_greeting(query) and not chat_history:
                actual_query = f"{query}. Please provide a brief introduction about yourself as a travel assistant."
            else:
                actual_query = query
                
            logger.info("Preparing messages for AI model")
            # Prepare messages for the API
            messages = [{"role": "system", "content": self.travel_system_prompt}]
            
            # Add chat history - ensure it's properly formatted for OpenAI
            if chat_history:
                for message in chat_history:
                    # Only include messages with valid roles
                    if message.role in ["user", "assistant", "system"]:
                        messages.append({"role": message.role, "content": message.content})
            
            # Add the current query
            messages.append({"role": "user", "content": actual_query})
            
            logger.info("Calling OpenAI API")
            # Create API request - remove metadata as it appears to be causing issues
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract the response text
            answer = response.choices[0].message.content
            logger.info(f"Received answer from OpenAI: {answer[:30]}...")
            
            # Save the assistant's response to the database
            if chat_id and chat_history_controller:
                logger.info(f"Saving assistant response to DB, session ID: {chat_id}")
                try:
                    asst_msg_result = await chat_history_controller.save_message(chat_id, "assistant", answer)
                    logger.info(f"Assistant message saved with ID: {asst_msg_result.get('message', {}).get('id')}")
                except Exception as e:
                    logger.error(f"Error saving assistant message: {str(e)}")
                    logger.error(traceback.format_exc())
            
            logger.info("Returning successful response to user")
            return {
                "status": "success",
                "answer": answer,
                "model": "gpt-4o",
                "chat_id": chat_id
            }
            
        except Exception as e:
            logger.error(f"Error in ask_question: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Error when calling OpenAI API: {str(e)}")