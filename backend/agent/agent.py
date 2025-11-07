from typing import Literal
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
from .tools import tools





# Initialize LLM and tools - USE SYNC VERSION with optimizations
llm = ChatOllama(
    model="qwen2.5:latest",
    temperature=0,
    base_url="http://localhost:11434",
    num_ctx=2048,
    num_predict=128,  # Limit response length for faster generation
    repeat_penalty=1.1,
    top_k=40,
    top_p=0.9,
)
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """
    You are a helpful and friendly ticketing support agent assistant. Your job is to talk to users, understand their issue, and create a support ticket for them using the `create_ticket` tool.

    Ticket Categories:
    - Technical → Includes:
    - Password Reset
    - Change Billing Address
    - Billing → Includes:
    - Duplicate Charge / Payment
    - Invoice Not Received
    - Other → Anything outside the above cases

    Goal:
    Carry a natural conversation. Ask the user clarifying questions if the necessary details are missing. Do not rush. Collect:
    - User name (if not already known)
    - Email (optional, ask politely only if needed)
    - Category (Technical, Billing, or Other)
    - Sub-category (password reset, duplicate payment, etc.)
    - Short summary of the issue
    - Any relevant details to help solve the problem

    Once you have enough information, call the `create_ticket` tool.

    After the tool returns a ticket_id:
    - Tell the user the ticket has been created.
    - Provide the ticket ID.
    - End with a polite closing.

    Tone:
    - Warm, friendly, conversational.
    - Be patient and guide the user clearly.
"""

# Define the graph state
class AgentState(MessagesState):
    pass

# Define agent node - SYNC with timing
def agent(state: AgentState):
    import time
    start = time.time()
    print("=== Agent node called ===")
    messages = state["messages"]

    if len(messages) == 1 or not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    print(f"=== Calling LLM with {len(messages)} messages ===")
    try:
        # USE SYNC invoke instead of ainvoke
        response = llm_with_tools.invoke(messages)
        elapsed = time.time() - start
        print(f"=== LLM response received in {elapsed:.2f}s ===")
        return {"messages": [response]}
    except Exception as e:
        print(f"=== LLM Error: {e} ===")
        raise

# Define conditional edge logic
def should_continue(state: AgentState) -> Literal["tools", END]:
    messages = state["messages"]
    last_message = messages[-1]
    
    # If there are tool calls, continue to tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print("=== Tool calls detected, routing to tools ===")
        return "tools"
    
    # Otherwise end
    print("=== No tool calls, ending ===")
    return END

# Build the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("agent", agent)
tools_node = ToolNode(tools)
workflow.add_node("tools", tools_node)

# Add edges
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

# Compile the graph
graph = workflow.compile()