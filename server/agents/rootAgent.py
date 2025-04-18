from typing import Dict, Any, List, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

import agents.prompt as prompt
from subagents.explore.agent import agent as explore_agent
from subagents.pre_travel.agent import PreTripAgent
from subagents.planning.agent import PlanningAgent
from tools.memory import _load_precreated_itinerary
from tools.weather_tool import weather_tool
import logging

logger = logging.getLogger("root_agent")

class TravelAgentState(TypedDict):
    messages: List[Dict[str, Any]]
    user_input: str
    agent_scratchpad: List[Dict[str, Any]]
    current_agent: str
    itinerary: Dict[str, Any]
    weather_data: Dict[str, Any]
    is_weather_response: bool  # New flag to indicate if weather data was directly returned

llm = ChatOpenAI(model="gpt-4o")

planning_agent_instance = PlanningAgent()


def explore_agent_node(state: TravelAgentState) -> TravelAgentState:
    # If we already handled the weather response directly, skip processing
    if state.get("is_weather_response", False):
        logger.info("Skipping explore agent - weather already handled")
        return state
        
    result = explore_agent.invoke({"input": state["user_input"]})
    output = result.get("output", str(result))
    state["messages"].append({"role": "assistant", "content": output})
    state["agent_scratchpad"].append({"agent": "explore", "output": output})
    return state


def pre_travel_agent_node(state: TravelAgentState) -> TravelAgentState:
    # If we already handled the weather response directly, skip processing
    if state.get("is_weather_response", False):
        logger.info("Skipping pre-travel agent - weather already handled")
        return state
        
    # Pass weather data to pre-travel agent if available
    inputs = {
        "input": state["user_input"],
        "weather_data": state.get("weather_data", {})
    }
    
    result = PreTripAgent().invoke(inputs)
    output = result.get("output", str(result))
    state["messages"].append({"role": "assistant", "content": output})
    state["agent_scratchpad"].append({"agent": "pre_travel", "output": output})
    return state


def planning_agent_node(state: TravelAgentState) -> TravelAgentState:
    # If we already handled the weather response directly, skip processing
    if state.get("is_weather_response", False):
        logger.info("Skipping planning agent - weather already handled")
        return state
        
    sub_state = {
        "messages": [HumanMessage(content=state["user_input"])],
        "tools": [],
        "tool_names": [],
        "last_tool_call_ids": [],
        "weather_data": state.get("weather_data", {})
    }
    
    # Get the weather data if available
    weather_data = state.get("weather_data", {})
    
    # Call planning agent with weather data
    sub_result = planning_agent_instance.graph.invoke(sub_state)

    for msg in reversed(sub_result["messages"]):
        if isinstance(msg, AIMessage):
            state["messages"].append({"role": "assistant", "content": msg.content})
            state["agent_scratchpad"].append({"agent": "planning", "output": msg.content})
            break

    return state


def root_agent_node(state: TravelAgentState) -> TravelAgentState:
    import re

    # Initialize the new flag
    state["is_weather_response"] = False

    # Get the raw user input without chat history
    full_input = state["user_input"]
    # Extract just the user's current query if chat history is included
    if "current query:" in full_input.lower():
        try:
            user_input = full_input.lower().split("current query:")[-1].strip()
            logger.info(f"Extracted current query from chat history: {user_input}")
        except Exception as e:
            logger.error(f"Error extracting current query: {str(e)}")
            user_input = full_input.lower()
    else:
        user_input = full_input.lower()
        
    logger.info(f"Processing query: {user_input}")
    agent_mapping = {
        "explore": "explore_agent",
        "in_travel": "in_travel_agent",
        "planning": "planning_agent",
        "post_travel": "post_travel_agent",
        "pre_travel": "pre_travel_agent",
        "weather": "weather_agent"
    }
    
    # Extract weather location if present
    location = weather_tool.extract_location(user_input)
    
    # Check for weather queries - include more comprehensive patterns
    weather_patterns = [
        r"(weather|forecast|temperature|rain|sunny|cloudy|hot|cold|humid|wind|storms?)",
        r"(what('s| is) it like in)",
        r"(should I (bring|pack|wear))",
        r"(will it (rain|snow|be (hot|cold|sunny|cloudy)))"
    ]
    
    is_weather_query = any(re.search(pattern, user_input, re.IGNORECASE) for pattern in weather_patterns)
    
    # If no explicit location mentioned but it looks like a weather query, try to extract location
    if not location and is_weather_query:
        # Try to identify common city names in the query
        common_cities = ["New York", "London", "Paris", "Tokyo", "Berlin", "Rome", "Madrid", "Beijing", "Sydney"]
        for city in common_cities:
            if city.lower() in user_input.lower():
                location = city
                break
    
    # Direct handling of weather queries when both location and weather pattern are detected
    if location and is_weather_query:
        # Log that we detected a weather query
        logger.info(f"Detected weather query for location: {location}")
        
        try:
            # Get weather data
            weather_data = weather_tool.get_current_weather(location)
            # Store in state for use by other agents
            state["weather_data"] = weather_data
            
            # If this is ONLY a weather query with no other travel aspects
            # Simplified check that's more robust to variations
            is_pure_weather_query = any([
                re.match(rf".*?(weather|forecast|temperature).*?(?:in|at|for)\s+{re.escape(location)}.*?", user_input, re.IGNORECASE),
                re.match(rf".*?(?:in|at)\s+{re.escape(location)}.*?(weather|forecast).*?", user_input, re.IGNORECASE),
                re.match(rf".*?{re.escape(location)}.*?(weather|forecast|temperature).*?", user_input, re.IGNORECASE)
            ])
            
            # Check if there are travel planning aspects
            has_travel_aspects = re.search(r"(hotel|flight|itinerary|trip|travel plan|book|reserve)", user_input)
            
            logger.info(f"Pure weather query: {is_pure_weather_query}, Has travel aspects: {has_travel_aspects}")
            
            if is_pure_weather_query and not has_travel_aspects:
                # Direct weather query - handle directly
                weather_response = f"Here's the weather information for {location}: {weather_data.get('report', 'Could not retrieve weather data.')}"
                
                logger.info(f"Returning direct weather response: {weather_response[:50]}...")
                
                # Set the flag to indicate we've directly handled the weather response
                state["is_weather_response"] = True
                
                # Clear any existing messages to ensure our weather response is the only one
                state["messages"] = []
                
                # Add the response to messages
                state["messages"].append({
                    "role": "assistant", 
                    "content": weather_response
                })
                
                # Set the current agent to a valid next node
                state["current_agent"] = "explore_agent"
                return state
                
        except Exception as e:
            # Log the error but continue with normal routing
            logger.error(f"Weather data retrieval error: {e}")
            
            # For direct weather queries, provide a helpful response instead of silent failure
            # Use the same improved pattern matching as above
            is_pure_weather_query = any([
                re.match(rf".*?(weather|forecast|temperature).*?(?:in|at|for)\s+{re.escape(location)}.*?", user_input, re.IGNORECASE),
                re.match(rf".*?(?:in|at)\s+{re.escape(location)}.*?(weather|forecast).*?", user_input, re.IGNORECASE),
                re.match(rf".*?{re.escape(location)}.*?(weather|forecast|temperature).*?", user_input, re.IGNORECASE)
            ])
            
            # Check if there are travel planning aspects
            has_travel_aspects = re.search(r"(hotel|flight|itinerary|trip|travel plan|book|reserve)", user_input)
            
            logger.info(f"Error handler - Pure weather query: {is_pure_weather_query}, Has travel aspects: {has_travel_aspects}")
            
            if is_pure_weather_query and not has_travel_aspects:
                
                error_response = f"I'd like to provide weather information for {location}, but I'm having trouble accessing the weather service at the moment. You can check a reliable weather website for current conditions. If you have any other travel-related questions, I'm happy to help!"
                
                logger.info(f"Returning weather error response: {error_response[:50]}...")
                
                # Set the flag to indicate we've directly handled the weather response
                state["is_weather_response"] = True
                
                # Clear any existing messages to ensure our error response is the only one
                state["messages"] = []
                
                # Add the response to messages
                state["messages"].append({
                    "role": "assistant", 
                    "content": error_response
                })
                
                # Set the current agent to a valid next node
                state["current_agent"] = "explore_agent"
                return state
    
    # If we get here, this is not a pure weather query or we couldn't handle it directly
    # Continue with regular agent routing
    
    # Expanded keyword routing
    if re.search(r"(flight|flights?|airfare|plane|book.*(ticket|flight)|show.*flights?|find.*flight)", user_input):
        response_text = "planning"
    elif re.search(r"(hotel|stay|room|accommodation|book.*hotel|lodge)", user_input):
        response_text = "planning"
    elif re.search(r"(restaurant|food|eat|dining|cuisine|attraction|visit|tour|sightseeing|landmark|discover|explore)", user_input):
        response_text = "planning"
    elif re.search(r"(itinerary|schedule|plan|trip|travel)", user_input):
        response_text = "planning"
    elif re.search(r"(pack|luggage|essentials|carry|prepare|things to bring)", user_input):
        response_text = "pre_travel"
    else:
        # Fallback to LLM
        messages = [SystemMessage(content=prompt.ROOT_AGENT_INSTR), HumanMessage(content=state["user_input"])]
        for msg in state["messages"]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(SystemMessage(content=msg["content"]))
        messages.append(SystemMessage(content="""
        Based on the user's request, determine which specialized agent should handle it.

        Available agents:
        - in_travel: For assistance during travel
        - planning: For planning itineraries and schedules
        - post_travel: For post-trip activities
        - pre_travel: For pre-trip preparations

        Reply with just one word - the name of the agent that should handle this request.
        """))
        response = llm.invoke(messages)
        response_text = response.content.lower().strip()

    state["current_agent"] = agent_mapping.get(response_text, "explore_agent")
    return state


def build_travel_agent_graph():
    memory = MemorySaver()
    graph = StateGraph(TravelAgentState)
    graph.add_node("root_agent", root_agent_node)
    graph.add_node("explore_agent", explore_agent_node)
    graph.add_node("pre_travel_agent", pre_travel_agent_node)
    graph.add_node("planning_agent", planning_agent_node)

    graph.set_entry_point("root_agent")
    graph.add_conditional_edges("root_agent", lambda state: state["current_agent"], {
        "explore_agent": "explore_agent",
        "pre_travel_agent": "pre_travel_agent",
        "planning_agent": "planning_agent"
    })

    # Define the condition to check if this is already a weather response
    def skip_agent_processing(state):
        if state.get("is_weather_response", False):
            logger.info("Skipping further processing - direct weather response")
            return "end"
        return "continue"

    # Add conditional edges from each agent to check if we should skip processing
    graph.add_conditional_edges("explore_agent", skip_agent_processing, {
        "end": END,
        "continue": END  # Default is still END for this agent
    })
    graph.add_conditional_edges("pre_travel_agent", skip_agent_processing, {
        "end": END,
        "continue": END  # Default is still END for this agent
    })
    graph.add_conditional_edges("planning_agent", skip_agent_processing, {
        "end": END,
        "continue": END  # Default is still END for this agent
    })

    return graph.compile(checkpointer=memory)


class Agent:
    def __init__(self, model, name: str, description: str, instruction: str, sub_agents: List = None, before_agent_callback=None):
        self.model = model
        self.name = name
        self.description = description
        self.instruction = instruction
        self.sub_agents = sub_agents or []
        self.before_agent_callback = before_agent_callback
        self.conversation_ids = {}

    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        conversation_id = inputs.get("conversation_id", "default")
        if self.before_agent_callback:
            inputs = self.before_agent_callback(inputs)
        initial_state = {
            "messages": [],
            "user_input": inputs.get("input", ""),
            "agent_scratchpad": [],
            "current_agent": "root_agent",
            "itinerary": {},
            "weather_data": {},
            "is_weather_response": False  # Initialize the new flag
        }
        final_state = self.model.invoke(initial_state, config={"configurable": {"thread_id": conversation_id}})
        
        # Return the last message from the state
        if final_state["messages"]:
            # Extract and log the response for debugging
            output = final_state["messages"][-1]["content"]
            logger.info(f"Final response: {output[:100]}...")
            return {"output": output}
        return {"output": "No response generated."}

    async def ainvoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        conversation_id = inputs.get("conversation_id", "default")
        if self.before_agent_callback:
            inputs = self.before_agent_callback(inputs)
        initial_state = {
            "messages": [],
            "user_input": inputs.get("input", ""),
            "agent_scratchpad": [],
            "current_agent": "root_agent",
            "itinerary": {},
            "weather_data": {},
            "is_weather_response": False  # Initialize the new flag
        }
        final_state = await self.model.ainvoke(initial_state, config={"configurable": {"thread_id": conversation_id}})
        
        # Return the last message from the state
        if final_state["messages"]:
            # Extract and log the response for debugging
            output = final_state["messages"][-1]["content"]
            logger.info(f"Final async response: {output[:100]}...")
            return {"output": output}
        return {"output": "No response generated."}


travel_agent_graph = build_travel_agent_graph()

root_agent = Agent(
    model=travel_agent_graph,
    name="root_agent",
    description="A Travel Concierge using LangGraph and sub-agents",
    instruction=prompt.ROOT_AGENT_INSTR,
    sub_agents=[explore_agent, planning_agent_instance, PreTripAgent()],
    before_agent_callback=_load_precreated_itinerary
)

if __name__ == "__main__":
    result = root_agent.invoke({"input": "Find me flights from NYC to Paris on May 15"})
    print(result["output"])
