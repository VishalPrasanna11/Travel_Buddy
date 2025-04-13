from fastapi import HTTPException, Depends
from typing import Dict, Any, List, Optional
import os
import re
from middlewares.conn_llm import get_openai_client
from openai import OpenAI
from pydantic import BaseModel, EmailStr

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
        """
        Check if the query is related to travel using keyword matching
        
        Args:
            query (str): The user's question or prompt
            
        Returns:
            bool: True if travel-related, False otherwise
        """
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
        """
        Check if the conversation context is travel-related based on chat history
        
        Args:
            chat_history (List[Message]): The conversation history
            
        Returns:
            bool: True if the context is travel-related, False otherwise
        """
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
        user_email: str = None
    ) -> Dict[str, Any]:
        """
        Send a query to OpenAI's GPT-4o model and get the response
        
        Args:
            query (str): The user's question or prompt
            chat_history (List[Message]): Previous conversation messages
            chat_id (str): Unique identifier for the conversation
            user_email (str): Email of the user making the request
            
        Returns:
            Dict[str, Any]: The response from the model
        """
        # Always check if query is travel-related or if the conversation context is travel-related
        context_is_travel = self._check_chat_history_context(chat_history)
        
        if not self.is_travel_related(query) and not context_is_travel:
            return {
                "status": "redirect",
                "answer": "I'm your Travel AI Assistant and can only help with travel-related questions. Feel free to ask me about destinations, trip planning, accommodations, or any other travel topics!",
                "model": "filter"
            }
        
        try:
            # If it's a greeting, add a travel-focused context to the prompt
            if self.is_greeting(query) and not chat_history:
                actual_query = f"{query}. Please provide a brief introduction about yourself as a travel assistant."
            else:
                actual_query = query
                
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
            
            # Create API request - remove metadata as it appears to be causing issues
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract the response text
            answer = response.choices[0].message.content
            
            return {
                "status": "success",
                "answer": answer,
                "model": "gpt-4o"
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error when calling OpenAI API: {str(e)}")