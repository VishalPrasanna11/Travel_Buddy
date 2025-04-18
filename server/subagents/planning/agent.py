from typing import Dict, Any, List, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
import json
import logging
import traceback

# Import our mini-agents
from miniagents.Flight.agent import flight_search_agent, format_flight_results
from miniagents.Hotels.agent import hotel_search_agent, format_hotel_results
from miniagents.Restaurants.agent import restaurant_search_agent, format_restaurant_results
from miniagents.Attractions.agent import attractions_search_agent, format_attractions_results
# from miniagents.Itinerary.agent import itinerary_agent, format_itinerary_results

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('planning_agent')

# ------------------ LangGraph State ------------------ #
class PlanningAgentState(TypedDict):
    messages: List[Any]
    tools: List[Dict[str, Any]]
    tool_names: List[str]
    last_tool_call_ids: List[str]
    weather_data: Dict[str, Any]

# ------------------ LLM ------------------ #
base_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

# ------------------ Query Preprocessing ------------------ #
def preprocess_flight_query(user_input: str) -> str:
    """Use LLM to convert natural language to structured flight query"""
    system_prompt = """
    You are a flight query parser. Extract flight information from the user input 
    and format it as:
    from=OriginCity&to=DestinationCity&departureDate=YYYY-MM-DD&adults=NumberOfAdults

    If return date is mentioned, include: &returnDate=YYYY-MM-DD
    If number of adults isn't specified, default to 1.
    Use only city names without state/country.
    Format dates as YYYY-MM-DD.
    Only output the formatted string, nothing else.
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ]
    response = base_llm.invoke(messages)
    result = response.content.strip()
    logger.info(f"🧠 Flight Query Preprocessed Output: {result}")
    return result

def preprocess_hotel_query(user_input: str) -> str:
    """Use LLM to convert natural language to structured hotel query"""
    system_prompt = """
    You are a hotel query parser. Extract hotel booking information from the user input 
    and format it as:
    city=CityName&checkInDate=YYYY-MM-DD&checkOutDate=YYYY-MM-DD&adults=NumberOfAdults
    
    If specific amenities are mentioned, include them as: &amenities=AMENITY1,AMENITY2
    Valid amenities are: SWIMMING_POOL, SPA, FITNESS_CENTER, AIR_CONDITIONING, RESTAURANT, PARKING, PETS_ALLOWED, 
    AIRPORT_SHUTTLE, BUSINESS_CENTER, DISABLED_FACILITIES, WIFI, MEETING_ROOMS, KITCHEN
    
    If specific ratings are mentioned, include them as: &ratings=Rating1,Rating2
    Valid ratings are: 1,2,3,4,5
    
    Only output the formatted string, nothing else.
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ]
    response = base_llm.invoke(messages)
    result = response.content.strip()
    logger.info(f"🧠 Hotel Query Preprocessed Output: {result}")
    return result

def preprocess_restaurant_query(user_input: str) -> str:
    """Use LLM to convert natural language to structured restaurant query"""
    system_prompt = """
    You are a restaurant query parser. Extract restaurant search information from the user input 
    and format it as:
    location=City&cuisine=CuisineType
    
    Examples:
    - "Find Italian restaurants in New York" -> "location=New York&cuisine=Italian"
    - "Where can I get Thai food in San Francisco" -> "location=San Francisco&cuisine=Thai"
    
    Only output the formatted string, nothing else.
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ]
    response = base_llm.invoke(messages)
    result = response.content.strip()
    logger.info(f" Restaurant Query Preprocessed Output: {result}")
    return result

def preprocess_attractions_query(user_input: str) -> str:
    """Use LLM to convert natural language to structured attractions query"""
    system_prompt = """
    You are an attractions query parser. Extract attraction search information from the user input 
    and format it as:
    location=City&attraction_type=AttractionType
    
    Examples:
    - "Find museums in Paris" -> "location=Paris&attraction_type=museums"
    - "What are some parks in London" -> "location=London&attraction_type=parks"
    
    Only output the formatted string, nothing else.
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ]
    response = base_llm.invoke(messages)
    result = response.content.strip()
    logger.info(f" Attractions Query Preprocessed Output: {result}")
    return result

# ------------------ Tool Schema ------------------ #
tools = [
    {
        "type": "function",
        "function": {
            "name": "flight_search_agent",
            "description": "Search flights using Amadeus API. Use for queries about flights, air travel, or plane tickets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_str": {"type": "string"}
                },
                "required": ["input_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "hotel_search_agent",
            "description": "Search hotels using Amadeus API. Use for queries about hotels, accommodations, or places to stay.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_str": {"type": "string"}
                },
                "required": ["input_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "restaurant_search_agent",
            "description": "Search restaurants using Google Maps API. Use for queries about food, dining, or restaurants.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_str": {"type": "string"}
                },
                "required": ["input_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "attractions_search_agent",
            "description": "Search attractions using Google Maps API. Use for queries about tourist spots, museums, parks, or things to do.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_str": {"type": "string"}
                },
                "required": ["input_str"]
            }
        }
    }
]

tool_funcs = {
    "flight_search_agent": flight_search_agent,
    "hotel_search_agent": hotel_search_agent,
    "restaurant_search_agent": restaurant_search_agent,
    "attractions_search_agent": attractions_search_agent,
    # "itinerary_agent": itinerary_agent
    
}

# ------------------ Agent Node ------------------ #
def planning_agent_node(state: PlanningAgentState) -> PlanningAgentState:
    """Process the user input and determine what tools to call"""
    system_message = """You are a comprehensive travel assistant who can help with flights, hotels, restaurants, and attractions.
    
    If weather data is provided, incorporate it into your recommendations and advice.

Use `flight_search_agent` to search for flights. Examples:
- "Find flights from Boston to Tokyo on May 15" 
- "from=Boston&to=Tokyo&departureDate=2025-05-15&adults=2"

Use `hotel_search_agent` to search for hotels. Examples:
- "Find hotels in Tokyo from May 15 to May 20 for 2 adults"
- "city=Tokyo&checkInDate=2025-05-15&checkOutDate=2025-05-20&adults=2"

Use `restaurant_search_agent` to find restaurants. Examples:
- "Find Italian restaurants in Tokyo"
- "location=Tokyo&cuisine=Italian"

Use `attractions_search_agent` to find tourist attractions. Examples:
- "What are some museums in Paris?"
- "location=Paris&attraction_type=museums"

Based on the query, determine which tool(s) to use and respond appropriately.
Return results cleanly and clearly.
"""

    formatted_messages = [SystemMessage(content=system_message)] + state["messages"]

    response = base_llm.invoke(
        formatted_messages,
        tools=tools,
        tool_choice="auto"
    )

    state["messages"].append(response)
    logger.info(f"🛠️ LLM Tool Calls: {getattr(response, 'tool_calls', None)}")
    
    tool_calls, tool_ids = [], []

    if hasattr(response, "tool_calls") and response.tool_calls:
        for call in response.tool_calls:
            # Extract the correct arguments from the tool call
            tool_args = {}
            
            # Option 1: Check if arguments are in 'args' (as seen in the logs)
            if "args" in call and call["args"]:
                tool_args = call["args"]
                logger.info(f"📦 Found arguments in 'args' key: {tool_args}")
            
            # Option 2: Check if arguments are in 'arguments' (original expectation)
            elif "arguments" in call:
                try:
                    raw_args = call["arguments"]
                    if isinstance(raw_args, str):
                        tool_args = json.loads(raw_args)
                    elif isinstance(raw_args, dict):
                        tool_args = raw_args
                    logger.info(f"📦 Found arguments in 'arguments' key: {tool_args}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse tool arguments: {e}")
            
            # Store both 'args' and 'arguments' in the tool call for flexibility
            tool_call = {
                "id": call["id"],
                "name": call["name"],
                "arguments": tool_args,  # Original expected key
                "args": tool_args        # Key seen in logs
            }
            
            tool_calls.append(tool_call)
            tool_ids.append(call["id"])

    state["tools"] = tool_calls
    state["tool_names"] = [t["name"] for t in tool_calls]
    state["last_tool_call_ids"] = tool_ids

    return state

# ------------------ Handling Natural Language Input ------------------ #
def natural_language_flight_search_agent(input_str: str) -> Dict[str, Any]:
    """Handle natural language input for flight search by preprocessing with LLM"""
    try:
        # Use LLM to convert natural language to structured format
        structured_query = preprocess_flight_query(input_str)
        # Pass the structured query to the flight search agent
        return flight_search_agent(input_str=structured_query)
    except Exception as e:
        logger.error(f"❌ Flight Natural Language Processing Error: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Error processing flight query: {str(e)}"}

def natural_language_hotel_search_agent(input_str: str) -> Dict[str, Any]:
    """Handle natural language input for hotel search by preprocessing with LLM"""
    try:
        # Use LLM to convert natural language to structured format
        structured_query = preprocess_hotel_query(input_str)
        # Pass the structured query to the hotel search agent
        return hotel_search_agent(input_str=structured_query)
    except Exception as e:
        logger.error(f"❌ Hotel Natural Language Processing Error: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Error processing hotel query: {str(e)}"}

def natural_language_restaurant_search_agent(input_str: str) -> Dict[str, Any]:
    """Handle natural language input for restaurant search by preprocessing with LLM"""
    try:
        # Use LLM to convert natural language to structured format
        structured_query = preprocess_restaurant_query(input_str)
        # Pass the structured query to the restaurant search agent
        return restaurant_search_agent(input_str=structured_query)
    except Exception as e:
        logger.error(f"❌ Restaurant Natural Language Processing Error: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Error processing restaurant query: {str(e)}"}

def natural_language_attractions_search_agent(input_str: str) -> Dict[str, Any]:
    """Handle natural language input for attractions search by preprocessing with LLM"""
    try:
        # Use LLM to convert natural language to structured format
        structured_query = preprocess_attractions_query(input_str)
        # Pass the structured query to the attractions search agent
        return attractions_search_agent(input_str=structured_query)
    except Exception as e:
        logger.error(f"❌ Attractions Natural Language Processing Error: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Error processing attractions query: {str(e)}"}

# ------------------ Execute Tool Function ------------------ #
def execute_tool(tool_func, state: PlanningAgentState, tool_key: str) -> PlanningAgentState:
    """Execute the tool with extracted arguments"""
    for call in state["tools"]:
        if call["name"] == tool_key and call["id"] in state.get("last_tool_call_ids", []):
            try:
                # Try multiple possible locations for arguments
                args = {}
                
                # Option 1: Check for "args" key (as seen in logs)
                if "args" in call and call["args"]:
                    args = call["args"]
                    logger.info(f"📦 Using arguments from 'args' key: {args}")
                
                # Option 2: Check for "arguments" key (as in original code)
                elif "arguments" in call and call["arguments"]:
                    args = call["arguments"]
                    logger.info(f"📦 Using arguments from 'arguments' key: {args}")
                
                # If still empty, try one more approach - maybe it's nested?
                if not args and isinstance(call.get("arguments", {}), dict):
                    nested_args = call["arguments"].get("input_str")
                    if nested_args:
                        args = {"input_str": nested_args}
                        logger.info(f"📦 Found arguments in nested structure: {args}")
                
                logger.info(f"🧪 Executing tool: {tool_key} with args: {args}")
                
                # Last resort - if we still don't have valid args, raise an error
                if not args or "input_str" not in args:
                    raise ValueError(f"Could not find required 'input_str' in args: {call}")
                
                # Check what kind of search we're doing and how to handle the input
                input_str = args["input_str"]
                
                if tool_key == "flight_search_agent":
                    # For flight searches
                    if not input_str.startswith("from="):
                        # Handle natural language input
                        result = natural_language_flight_search_agent(input_str)
                    else:
                        # Handle structured input directly
                        result = tool_func(**args)
                
                elif tool_key == "hotel_search_agent":
                    # For hotel searches
                    if not input_str.startswith("city="):
                        # Handle natural language input
                        result = natural_language_hotel_search_agent(input_str)
                    else:
                        # Handle structured input directly
                        result = tool_func(**args)
                
                elif tool_key == "restaurant_search_agent":
                    # For restaurant searches
                    if not input_str.startswith("location="):
                        # Handle natural language input
                        result = natural_language_restaurant_search_agent(input_str)
                    else:
                        # Handle structured input directly
                        result = tool_func(**args)
                
                elif tool_key == "attractions_search_agent":
                    # For attractions searches
                    if not input_str.startswith("location="):
                        # Handle natural language input
                        result = natural_language_attractions_search_agent(input_str)
                    else:
                        # Handle structured input directly
                        result = tool_func(**args)
                
                else:
                    # Unknown tool
                    result = {"error": f"Unknown tool: {tool_key}"}
                
                logger.info(f"✅ Tool returned: {result}")
                state["messages"].append(
                    ToolMessage(tool_call_id=call["id"], content=json.dumps(result))
                )
            except Exception as e:
                logger.error(f"❌ Tool execution error: {str(e)}")
                state["messages"].append(
                    ToolMessage(tool_call_id=call["id"], content=json.dumps({"error": str(e)}))
                )
    return state

# ------------------ Graph Flow Control ------------------ #
def should_continue(state: PlanningAgentState) -> str:
    """Determine the next step based on tool calls"""
    if not state["tool_names"]:
        return "end"
    
    tool_name = state["tool_names"][0]
    if tool_name == "flight_search_agent":
        return "execute_flight"
    elif tool_name == "hotel_search_agent":
        return "execute_hotel"
    elif tool_name == "restaurant_search_agent":
        return "execute_restaurant"
    elif tool_name == "attractions_search_agent":
        return "execute_attractions"
    else:
        return "end"

# ------------------ LangGraph Setup ------------------ #
def build_planning_agent_graph():
    """Build the LangGraph workflow"""
    workflow = StateGraph(PlanningAgentState)
    
    # Add nodes
    workflow.add_node("agent", planning_agent_node)
    workflow.add_node("execute_flight", lambda s: execute_tool(flight_search_agent, s, "flight_search_agent"))
    workflow.add_node("execute_hotel", lambda s: execute_tool(hotel_search_agent, s, "hotel_search_agent"))
    workflow.add_node("execute_restaurant", lambda s: execute_tool(restaurant_search_agent, s, "restaurant_search_agent"))
    workflow.add_node("execute_attractions", lambda s: execute_tool(attractions_search_agent, s, "attractions_search_agent"))
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add conditional edges from agent node
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "execute_flight": "execute_flight",
            "execute_hotel": "execute_hotel",
            "execute_restaurant": "execute_restaurant",
            "execute_attractions": "execute_attractions",
            "end": END
        }
    )
    
    # Add edges back to agent node
    workflow.add_edge("execute_flight", "agent")
    workflow.add_edge("execute_hotel", "agent")
    workflow.add_edge("execute_restaurant", "agent")
    workflow.add_edge("execute_attractions", "agent")
    
    return workflow.compile()

# ------------------ Agent Wrapper ------------------ #
class PlanningAgent:
    def __init__(self):
        self.graph = build_planning_agent_graph()
        self.name = "planning_agent"

    def invoke(self, inputs: Dict[str, str]) -> Dict[str, str]:
        """Synchronous invocation of the agent"""
        user_input = inputs.get("input", "")
        weather_data = inputs.get("weather_data", {})
        
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "tools": [],
            "tool_names": [],
            "last_tool_call_ids": [],
            "weather_data": weather_data
        }
        
        # Add weather data to the prompt if available
        if weather_data and weather_data.get("report"):
            weather_info = f"\n\nCurrent weather information: {weather_data.get('report')}"
            initial_state["messages"].append(SystemMessage(content=weather_info))
        final_state = self.graph.invoke(initial_state, config={"recursion_limit": 10})

        # Process the final state to extract the response
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, ToolMessage):
                try:
                    parsed = json.loads(msg.content)
                    if "error" in parsed:
                        return {"output": f"❌ {parsed['error']}"}
                    
                    # Format based on which tool was called
                    if "hotels" in parsed:
                        return {"output": format_hotel_results(parsed)}
                    elif "flight" in parsed:
                        return {"output": format_flight_results(parsed)}
                    elif "restaurants" in parsed:
                        return {"output": format_restaurant_results(parsed)}
                    elif "attractions" in parsed:
                        return {"output": format_attractions_results(parsed)}
                    else:
                        return {"output": f"✅ Results: {parsed}"}
                except Exception as e:
                    return {"output": f"⚠️ Failed to parse tool response: {str(e)}"}

        for msg in reversed(final_state["messages"]):
            if isinstance(msg, AIMessage):
                return {"output": msg.content}

        return {"output": "⚠️ No valid response. Something went wrong internally."}

    async def ainvoke(self, inputs: Dict[str, str]) -> Dict[str, str]:
        """Asynchronous invocation of the agent"""
        user_input = inputs.get("input", "")
        weather_data = inputs.get("weather_data", {})
        
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "tools": [],
            "tool_names": [],
            "last_tool_call_ids": [],
            "weather_data": weather_data
        }
        
        # Add weather data to the prompt if available
        if weather_data and weather_data.get("report"):
            weather_info = f"\n\nCurrent weather information: {weather_data.get('report')}"
            initial_state["messages"].append(SystemMessage(content=weather_info))
        final_state = await self.graph.ainvoke(initial_state, config={"recursion_limit": 10})
        
        # Process the final state to extract the response
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, ToolMessage):
                try:
                    parsed = json.loads(msg.content)
                    # Format based on which tool was called
                    if "hotels" in parsed:
                        return {"output": format_hotel_results(parsed)}
                    elif "flight" in parsed:
                        return {"output": format_flight_results(parsed)}
                    elif "restaurants" in parsed:
                        return {"output": format_restaurant_results(parsed)}
                    elif "attractions" in parsed:
                        return {"output": format_attractions_results(parsed)}
                    else:
                        return {"output": f"✅ Results: {parsed}"}
                except:
                    return {"output": "⚠️ Received unparseable response data."}
            if isinstance(msg, AIMessage):
                return {"output": msg.content}
        return {"output": "Let me help you plan your trip."}

# ✅ Instantiate
agent = PlanningAgent()