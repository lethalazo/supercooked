"""FastAPI app entry point for Super Cooked dashboard."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import activity, analytics, beings, chat, content, feed

app = FastAPI(
    title="Super Cooked API",
    description="Manage digital beings on the human internet",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:4444"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(beings.router, prefix="/beings", tags=["beings"])
app.include_router(content.router, tags=["content"])
app.include_router(chat.router, tags=["chat"])
app.include_router(feed.router, prefix="/feed", tags=["feed"])
app.include_router(activity.router, tags=["activity"])
app.include_router(analytics.router, tags=["analytics"])


@app.get("/")
async def root():
    return {"name": "Super Cooked API", "version": "0.1.0", "status": "running"}
