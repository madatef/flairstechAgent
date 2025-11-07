from langchain_core.tools import tool
from db.db import supabase
from typing import Any, Optional


@tool
def create_ticket(email: str, category: str, text: str) -> str:
    """
    Create a new ticket for the user.

    Args:
        email (str): The email of the user creating the ticket.
        category (str): The category of the ticket. Allowed values are:
            - billing
            - technical
            - other
        text (str): The text explaining the issue or question.

    Returns:
        str: A message indicating the result and the created ticket ID if successful.
    """
    try:
        userId = supabase.table("users").select("id").eq("email", email).execute().data[0]["id"]
        if not userId:
            return f"This email is not associated with any users."

        ticketId = supabase.table("tickets").insert({
            "user_id": userId,
            "category": category,
            "text": text,
            "status": "open"
        }).execute()
        return f"Ticket created successfully. Ticket ID: {ticketId}"
    except Exception as e:
        return f"Failed to create ticket: {e}"
    
tools = [
    create_ticket
]


