"""WebSocket handler for real-time chat - re-exports from routes."""

# WebSocket handling is in api/routes/chat.py
# This module exists for organizational clarity
from api.routes.chat import chat_websocket

__all__ = ["chat_websocket"]
