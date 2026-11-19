from typing import Dict, Any, List, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import json
import re
import logging

import agents.prompt as prompt
from subagents.explore.agent import agent as explore_agent
from subagents.pre_travel.agent import PreTripAgent
from subagents.planning.agent import PlanningAgent
from tools.memory import _load_precreated_itinerary
from tools.weather_tool import weather_tool

logger = logging.getLogger("root_agent")


class TravelAgentState(TypedDict):
    messages: List[Dict[str, Any]]
    user_input: str
    agent_scratchpad: List[Dict[str, Any]]
    current_agent: str
    itinerary: Dict[str, Any]
    weather_data: Dict[str, Any]
    is_weather_response: bool


llm = ChatOpenAI(model="gpt-4o")
planning_agent_instance = PlanningAgent()


def explore_agent_node(state: TravelAgentState) -> TravelAgentState:
    if state.get("is_weather_response", False):
        logger.info("Skipping explore agent - weather already handled")
        return state
    result = explore_agent.invoke({"input": state["user_input"]})
    output = result.get("output", str(result))
    state["messages"].append({"role": "assistant", "content": output})
    state["agent_scratchpad"].append({"agent": "explore", "output": output})
    return state


def pre_travel_agent_node(state: TravelAgentState) -> TravelAgentState:
    if state.get("is_weather_response", False):
        logger.info("Skipping pre_travel agent - weather already handled")
        return state
    result = PreTripAgent().invoke({"input": state["user_input"]})
    output = result.get("output", str(result))
    state["messages"].append({"role": "assistant", "content": output})
    state["agent_scratchpad"].append({"agent": "pre_travel", "output": output})
    return state


def planning_agent_node(state: TravelAgentState) -> TravelAgentState:
    if state.get("is_weather_response", False):
        logger.info("Skipping planning agent - weather already handled")
        return state

    sub_state = {
        "messages": [HumanMessage(content=state["user_input"])],
        "tools": [],
        "tool_names": [],
        "last_tool_call_ids": [],
        "weather_data": state.get("weather_data", {}),
    }

    weather_data = state.get("weather_data", {})
    if weather_data:
        for location, data in weather_data.items():
            if "report" in data:
                weather_info = f"\nCurrent weather information for {location}: {data['report']}"
                sub_state["messages"].append(SystemMessage(content=weather_info))
                logger.info(f"Added weather information for {location} to planning agent input")

    sub_result = planning_agent_instance.graph.invoke(sub_state)

    tool_data = None
    for msg in reversed(sub_result["messages"]):
        if isinstance(msg, ToolMessage):
            try:
                tool_content = json.loads(msg.content)
                tool_data = tool_content
                break
            except (json.JSONDecodeError, TypeError):
                pass

    for msg in reversed(sub_result["messages"]):
        if isinstance(msg, AIMessage):
            state["messages"].append({"role": "assistant", "content": msg.content})

            if tool_data:
                output = {"text_content": msg.content, **tool_data}
                if weather_data and "api_data" in output and "weather" not in output["api_data"]:
                    output["api_data"]["weather"] = weather_data
                state["agent_scratchpad"].append({"agent": "planning", "output": output})
            else:
                state["agent_scratchpad"].append({"agent": "planning", "output": msg.content})
            break

    return state


def root_agent_node(state: TravelAgentState) -> TravelAgentState:
    user_input = state["user_input"].lower()
    agent_mapping = {
        "explore": "explore_agent",
        "in_travel": "in_travel_agent",
        "planning": "planning_agent",
        "post_travel": "post_travel_agent",
        "pre_travel": "pre_travel_agent",
    }

    weather_patterns = [
        r"(weather|forecast|temperature|rain|sunny|cloudy|hot|cold|humid|wind|storms?)",
        r"(what('s| is) it like in)",
        r"(should I (bring|pack|wear))",
        r"(will it (rain|snow|be (hot|cold|sunny|cloudy)))",
    ]

    is_weather_query = any(re.search(pattern, user_input, re.IGNORECASE) for pattern in weather_patterns)

    if is_weather_query:
        locations = weather_tool.extract_multiple_locations(user_input)

        if locations:
            logger.info(f"Detected weather query for locations: {locations}")

            try:
                weather_results = weather_tool.get_weather_for_multiple_locations(locations)
                state["weather_data"] = weather_results
                has_travel_aspects = re.search(r"(hotel|flight|itinerary|trip|travel plan|book|reserve)", user_input)

                if not has_travel_aspects:
                    weather_response = weather_tool.format_weather_response(weather_results)
                    logger.info("Returning direct weather response for multiple locations")
                    state["is_weather_response"] = True
                    state["messages"] = [{"role": "assistant", "content": weather_response}]
                    state["current_agent"] = "explore_agent"
                    return state
            except Exception as e:
                logger.error(f"Multiple weather data retrieval error: {e}")

                if not re.search(r"(hotel|flight|itinerary|trip|travel plan|book|reserve)", user_input):
                    location_names = ", ".join(locations)
                    error_response = (
                        f"I'd like to provide weather information for {location_names}, "
                        "but I'm having trouble accessing the weather service at the moment. "
                        "You can check a reliable weather website for current conditions. "
                        "If you have any other travel-related questions, I'm happy to help!"
                    )
                    logger.info("Returning weather error response for multiple locations")
                    state["is_weather_response"] = True
                    state["messages"] = [{"role": "assistant", "content": error_response}]
                    state["current_agent"] = "explore_agent"
                    return state

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
        messages = [SystemMessage(content=prompt.ROOT_AGENT_INSTR), HumanMessage(content=state["user_input"])]
        for msg in state["messages"]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(SystemMessage(content=msg["content"]))
        messages.append(
            SystemMessage(
                content=(
                    "Based on the user's request, determine which specialized agent should handle it.\n\n"
                    "Available agents:\n"
                    "- in_travel: For assistance during travel\n"
                    "- planning: For planning itineraries and schedules\n"
                    "- post_travel: For post-trip activities\n"
                    "- pre_travel: For pre-trip preparations\n\n"
                    "Reply with just one word - the name of the agent that should handle this request."
                )
            )
        )
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
    graph.add_conditional_edges(
        "root_agent",
        lambda state: state["current_agent"],
        {
            "explore_agent": "explore_agent",
            "pre_travel_agent": "pre_travel_agent",
            "planning_agent": "planning_agent",
        },
    )

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
            "itinerary": {},
            "weather_data": {},
            "is_weather_response": False,
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
            "itinerary": {},
            "weather_data": {},
            "is_weather_response": False,
        }

        final_state = await self.model.ainvoke(initial_state, config={"configurable": {"thread_id": conversation_id}})

        response = {
            "output": "No response generated.",
            "status": "success",
            "api_data": {},
        }

        if final_state["messages"]:
            response["output"] = final_state["messages"][-1]["content"]

        for note in final_state.get("agent_scratchpad", []):
            if note.get("agent") != "planning":
                continue

            output = note.get("output", "")

            if isinstance(output, str):
                try:
                    if output.strip().startswith("{") and output.strip().endswith("}"):
                        parsed = json.loads(output)
                        if "api_data" in parsed:
                            response["api_data"] = parsed["api_data"]
                        for key in ["restaurants", "flights", "flight", "hotels", "attractions", "weather"]:
                            if key in parsed:
                                data_key = "flights" if key == "flight" else key
                                response[data_key] = parsed[key]
                                if data_key not in response["api_data"]:
                                    response["api_data"][data_key] = parsed[key]
                except json.JSONDecodeError:
                    pass

                _extract_embedded_data(output, response)

            elif isinstance(output, dict):
                if "api_data" in output:
                    response["api_data"] = output["api_data"]
                for key in ["restaurants", "flights", "flight", "hotels", "attractions", "weather"]:
                    if key in output:
                        data_key = "flights" if key == "flight" else key
                        response[data_key] = output[key]
                        if data_key not in response["api_data"]:
                            response["api_data"][data_key] = output[key]

        for msg in reversed(final_state.get("messages", [])):
            if isinstance(msg, dict) and "content" in msg:
                content = msg["content"]
                if isinstance(content, str) and any(
                    key in content for key in ["restaurants", "flights", "hotels", "attractions", "weather"]
                ):
                    _extract_embedded_data(content, response)

        if final_state.get("weather_data") and "weather" not in response["api_data"]:
            response["api_data"]["weather"] = final_state["weather_data"]

        for key in ["restaurants", "flights", "hotels", "attractions", "weather"]:
            if key in response and key not in response["api_data"]:
                response["api_data"][key] = response[key]

        return response


def _extract_embedded_data(text: str, response: dict) -> None:
    for key in ["restaurants", "flights", "flight", "hotels", "attractions", "weather"]:
        if key not in text:
            continue
        try:
            data_pattern = rf'"{key}"\s*:\s*\[(.*?)\]'
            data_matches = re.findall(data_pattern, text, re.DOTALL)
            if not data_matches:
                continue

            data_key = "flights" if key == "flight" else key
            data_json = '{"' + data_key + '": [' + data_matches[0] + "]}"
            data_json = re.sub(r",\s*\]", "]", data_json)

            parsed_data = json.loads(data_json)
            if data_key in parsed_data:
                if data_key not in response or not response[data_key]:
                    response[data_key] = parsed_data[data_key]
                if data_key not in response.get("api_data", {}) or not response["api_data"].get(data_key):
                    response.setdefault("api_data", {})[data_key] = parsed_data[data_key]
        except (json.JSONDecodeError, Exception):
            pass


travel_agent_graph = build_travel_agent_graph()

root_agent = Agent(
    model=travel_agent_graph,
    name="root_agent",
    description="A Travel Concierge using LangGraph and sub-agents",
    instruction=prompt.ROOT_AGENT_INSTR,
    sub_agents=[explore_agent, planning_agent_instance, PreTripAgent()],
    before_agent_callback=_load_precreated_itinerary,
)
