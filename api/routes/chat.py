"""WebSocket chat with a being via Claude API."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.services.chat_service import ChatService

router = APIRouter()


@router.websocket("/ws/chat/{slug}")
async def chat_websocket(websocket: WebSocket, slug: str):
    """Chat with a being in its persona via WebSocket."""
    await websocket.accept()
    chat_service = ChatService(slug)

    try:
        await chat_service.initialize()
        await websocket.send_json({
            "type": "system",
            "message": f"Connected to {slug}. Start chatting!",
        })

        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")

            if not user_message:
                continue

            # Stream response from Claude API in being's persona
            response = await chat_service.respond(user_message)
            await websocket.send_json({
                "type": "message",
                "role": "assistant",
                "message": response,
            })

    except WebSocketDisconnect:
        await chat_service.end_session()
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e),
        })
        await websocket.close()
