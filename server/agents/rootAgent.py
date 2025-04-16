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
        - explore: For exploring travel destinations, activities, and attractions
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
        if final_state["messages"]:
            return {"output": final_state["messages"][-1]["content"]}
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