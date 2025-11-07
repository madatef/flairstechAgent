from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from db.db import supabase
from agent.agent import graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import uvicorn
from dotenv import load_dotenv
import asyncio

load_dotenv()






@asynccontextmanager # This helps free resources (GPU/CPU, memory, etc) when the app starts recieving requests
async def lifespan(app: FastAPI):
    # Run schema setup once on app startup
    with open("./db/schema.sql", "r") as f:
        sql = f.read()

    supabase.postgrest.rpc("exec_sql", {"sql": sql}).execute()

    yield  # Application runs here and resources are freed

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    user_id: str

class ChatResponse(BaseModel):
    response: str
    ticket_created: bool = False


async def get_conversation_history(user_id: str): 
    messages = supabase.table("chat_messages").select("sender, message").eq("user_id", user_id).execute().data
    history = [HumanMessage(item.get("message")) if item.get("sender", "") == "user" else AIMessage(item.get("message")) for item in messages]
    return history

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint that processes user messages and returns agent responses.
    """
    try:
        print("=== Chat endpoint called ===")
        print(f"Message: {request.message}")
        
        # Retrieve conversation history from database
        history = await get_conversation_history(request.user_id)
        print(f"History retrieved: {len(history)} messages")
        
        # Create the input with user message and store it in db
        supabase.table("chat_messages").insert({"sender": "user", "message": request.message, "user_id": request.user_id}).execute()
        user_message = HumanMessage(content=request.message)
        
        # Combine history with new message
        all_messages = history + [user_message]
        print(f"Total messages to process: {len(all_messages)}")
        
        # Invoke the graph with full message history
        # Run the SYNC graph.invoke in a thread pool to avoid blocking
        print("=== Starting graph invocation ===")
        result = await asyncio.to_thread(graph.invoke, {"messages": all_messages})
        print("=== Graph invocation completed ===")
        
        # Extract the response and check if ticket was created
        ticket_created = False
        response_text = ""
        
        # Check if any message in the result contains tool calls
        for msg in result["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                ticket_created = True
                break
        
        # Get the last message as the response
        last_message = result["messages"][-1]
        response_text = last_message.content
        
        # Store updated conversation history
        supabase.table("chat_messages").insert({"sender": "agent", "message": response_text, "user_id": request.user_id}).execute()
        
        
        print(f"=== Response ready: {response_text[:50]}... ===")
        
        return ChatResponse(
            response=response_text,
            ticket_created=ticket_created
        )
        
    except Exception as e:
        print(f"=== ERROR in chat endpoint: {e} ===")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user")
def get_user(email: str):
    # Query Supabase by email
    result = supabase.table("users") \
        .select("id") \
        .eq("email", email) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": result.data["id"]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)