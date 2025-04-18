from typing import Dict, Any, List, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
# At the top of rootAgent.py, add:
import json
import agents.prompt as prompt
from subagents.explore.agent import agent as explore_agent
from subagents.pre_travel.agent import PreTripAgent
from subagents.planning.agent import PlanningAgent
from tools.memory import _load_precreated_itinerary

class TravelAgentState(TypedDict):
    messages: List[Dict[str, Any]]
    user_input: str
    agent_scratchpad: List[Dict[str, Any]]
    current_agent: str
    itinerary: Dict[str, Any]

llm = ChatOpenAI(model="gpt-4o")

planning_agent_instance = PlanningAgent()


def explore_agent_node(state: TravelAgentState) -> TravelAgentState:
    result = explore_agent.invoke({"input": state["user_input"]})
    output = result.get("output", str(result))
    state["messages"].append({"role": "assistant", "content": output})
    state["agent_scratchpad"].append({"agent": "explore", "output": output})
    return state


def pre_travel_agent_node(state: TravelAgentState) -> TravelAgentState:
    result = PreTripAgent().invoke({"input": state["user_input"]})
    output = result.get("output", str(result))
    state["messages"].append({"role": "assistant", "content": output})
    state["agent_scratchpad"].append({"agent": "pre_travel", "output": output})
    return state


def planning_agent_node(state: TravelAgentState) -> TravelAgentState:
    sub_state = {
        "messages": [HumanMessage(content=state["user_input"])],
        "tools": [],
        "tool_names": [],
        "last_tool_call_ids": []
    }
    sub_result = planning_agent_instance.graph.invoke(sub_state)

    for msg in reversed(sub_result["messages"]):
        if isinstance(msg, AIMessage):
            state["messages"].append({"role": "assistant", "content": msg.content})
            state["agent_scratchpad"].append({"agent": "planning", "output": msg.content})
            break

    return state


def root_agent_node(state: TravelAgentState) -> TravelAgentState:
    import re

    user_input = state["user_input"].lower()
    agent_mapping = {
        "explore": "explore_agent",
        "in_travel": "in_travel_agent",
        "planning": "planning_agent",
        "post_travel": "post_travel_agent",
        "pre_travel": "pre_travel_agent"
    }

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

    graph.add_edge("explore_agent", END)
    graph.add_edge("pre_travel_agent", END)
    graph.add_edge("planning_agent", END)

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
            "itinerary": {}
        }
        final_state = self.model.invoke(initial_state, config={"configurable": {"thread_id": conversation_id}})
        if final_state["messages"]:
            return {"output": final_state["messages"][-1]["content"]}
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
            "itinerary": {}
        }
        final_state = await self.model.ainvoke(initial_state, config={"configurable": {"thread_id": conversation_id}})
        
        # Initialize response with default values and status
        response = {
            "output": "No response generated.",
            "status": "success"  # Default to success
        }
        
        if final_state["messages"]:
            # Get the text output for human readability
            response["output"] = final_state["messages"][-1]["content"]
            
            # Look for API data in agent_scratchpad
            for note in final_state.get("agent_scratchpad", []):
                if note.get("agent") == "planning":
                    # Check if the output contains structured API data
                    output = note.get("output", {})
                    
                    # Check for error status first
                    if isinstance(output, dict) and ("status" in output and output["status"] == "error" or "error" in output):
                        # Handle error case
                        response["status"] = "error"
                        response["error_message"] = output.get("error_message", output.get("error", "Unknown error"))
                        
                        # If there's api_data with error info, include it
                        if "api_data" in output and isinstance(output["api_data"], dict):
                            response["api_data"] = output["api_data"]
                        else:
                            # Create api_data with error info
                            response["api_data"] = {
                                "error": response["error_message"],
                                "status": "error"
                            }
                        
                        # Add error to top level
                        response["error"] = response["error_message"]
                        
                        # Return early on error
                        return response
                    
                    # Handle different output formats for success cases
                    if isinstance(output, dict):
                        # If output already contains api_data
                        if "api_data" in output:
                            response["api_data"] = output["api_data"]
                            
                            # Check for nested error
                            if isinstance(response["api_data"], dict) and "error" in response["api_data"]:
                                response["status"] = "error"
                                response["error_message"] = response["api_data"]["error"]
                                response["error"] = response["api_data"]["error"]
                            
                            # Also add individual data types to top level
                            for data_type, data in output["api_data"].items():
                                # Don't copy error or status to top level
                                if data_type not in ["error", "status"]:
                                    response[data_type] = data
                                
                        # Copy status if present
                        if "status" in output:
                            response["status"] = output["status"]
                                
                        # For backwards compatibility, check for direct data types
                        for data_type in ["flights", "hotels", "restaurants", "attractions"]:
                            if data_type in output:
                                if "api_data" not in response:
                                    response["api_data"] = {}
                                response["api_data"][data_type] = output[data_type]
                                response[data_type] = output[data_type]
                    
                    # Try to parse string outputs (might be JSON)
                    elif isinstance(output, str):
                        try:
                            parsed = json.loads(output)
                            if isinstance(parsed, dict):
                                # Check for error in parsed JSON
                                if "error" in parsed or ("status" in parsed and parsed["status"] == "error"):
                                    response["status"] = "error"
                                    response["error_message"] = parsed.get("error_message", parsed.get("error", "Unknown error"))
                                    response["error"] = response["error_message"]
                                    
                                    # Add api_data for error
                                    if "api_data" in parsed:
                                        response["api_data"] = parsed["api_data"]
                                    else:
                                        response["api_data"] = {
                                            "error": response["error_message"],
                                            "status": "error"
                                        }
                                    
                                    # Return early on error
                                    return response
                                
                                # Extract API data if present for success case
                                if "api_data" in parsed:
                                    response["api_data"] = parsed["api_data"]
                                    
                                    # Add individual data types to top level
                                    for data_type, data in parsed["api_data"].items():
                                        if data_type not in ["error", "status"]:
                                            response[data_type] = data
                                
                                # For backwards compatibility
                                for data_type in ["flights", "hotels", "restaurants", "attractions"]:
                                    if data_type in parsed:
                                        if "api_data" not in response:
                                            response["api_data"] = {}
                                        response["api_data"][data_type] = parsed[data_type]
                                        response[data_type] = parsed[data_type]
                                
                                # Copy status if present
                                if "status" in parsed:
                                    response["status"] = parsed["status"]
                        except Exception as e:
                            # Log parsing error but don't change response
                            print(f"Error parsing JSON from string output: {str(e)}")
                            # Not valid JSON, continue
                            pass
        
        # Final check to ensure api_data exists if we have data types
        has_data_types = any(k in response for k in ["flights", "hotels", "restaurants", "attractions"])
        if has_data_types and "api_data" not in response:
            response["api_data"] = {}
            for data_type in ["flights", "hotels", "restaurants", "attractions"]:
                if data_type in response:
                    response["api_data"][data_type] = response[data_type]
        
        return response
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