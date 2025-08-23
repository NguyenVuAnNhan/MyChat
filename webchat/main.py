import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, Cookie
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import json
from collections import defaultdict

from pydantic import BaseModel
from models.Message import Message
from db.session import engine, Base, get_db, SessionLocal
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv
from api import auth

load_dotenv()  

SECRET = os.getenv("SECRET")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key=SECRET)
app.include_router(auth.router, prefix="/auth", tags=["auth"])

class ConnectionManager:
    def __init__(self):
        # Keep track of the pool of connections to this room
        self.rooms: dict[str, list[WebSocket]] = defaultdict(list)
        self.usernames: dict[WebSocket, str] = {}
        self.delete_queue: set[str] = set()

    def check_existing(self, room: str) -> bool:
        return room in self.rooms
    
    def clear_empty(self):
        empty = [room for room, conns in self.rooms.items() if not conns]
        for room in empty:
            print(f"Clearing empty room: {room}")
            del self.rooms[room]
    
    def create_room(self, room: str):
        self.rooms[room] = []

    async def connect(self, room: str, websocket: WebSocket, username: str):
        # Add to connection pool
        self.rooms[room].append(websocket)
        self.usernames[websocket] = username

    def disconnect(self, room:str,  websocket: WebSocket):
        # Remove from connection pool
        if websocket in self.rooms[room]:
            self.rooms[room].remove(websocket)
        if websocket in self.usernames:
            del self.usernames[websocket]
        # Clean up empty room
        if not self.rooms[room]:
            del self.rooms[room]

    async def broadcast(self, room: str, username: str, message: str, db: Session):
        # broadcase the message to all connections in this pool
        db_msg = Message(room=room, username=username, message=message)
        db.add(db_msg)
        db.commit()

        for connection in self.rooms.get(room, []):
            await connection.send_text(message)

Base.metadata.create_all(bind=engine)

manager = ConnectionManager()

@app.on_event("startup")
async def cleanup_task():
    async def loop():
        while True:
            manager.clear_empty()
            await asyncio.sleep(60)  # wait 60s
    asyncio.create_task(loop())

# Home endpoint
@app.get("/")
async def index():
    return HTMLResponse(open("static/rooms.html").read())

@app.get("/login")
async def login():
    return HTMLResponse(open("static/login.html").read())

@app.get("/register")
async def register():
    return HTMLResponse(open("static/register.html").read())

@app.get("/api/{room_name}/history")
async def get_history(room_name: str, db: Session = Depends(get_db)):
    messages = (
        db.query(Message)
        .filter(Message.room == room_name)
        .order_by(Message.timestamp.asc())
        .limit(50)
        .all()
    )
    return [
        {"username": m.username, "message": m.message, "timestamp": m.timestamp.isoformat()}
        for m in messages
    ]

@app.get("/rooms_data")
async def retrieve_rooms():
    res = []

    for room, users in manager.rooms.items():
        res.append({"name": room, "users": len(users)})

    return {
        "rooms": res
    }

class NewRoomRequest(BaseModel):
    room_id: str

class NewRoomResponse(BaseModel):
    room_id: str

@app.post("/api/new_room")
async def make_room(room_request : NewRoomRequest):
    if manager.check_existing(room_request.room_id):
        return {}
    else:
        manager.create_room(room_request.room_id)
        return NewRoomResponse(room_id=room_request.room_id)


@app.get("/t/{room_name}")
async def chatroom():
    return HTMLResponse(open("static/chatroom.html").read())

# Websocket endpoint
@app.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str, session: Optional[str] = Cookie(None)):
    # Connect the client to the pool
    await websocket.accept()
    username = None
    # Event loop
    try:
        join_data = await websocket.receive_text()
        payload = json.loads(join_data)
        if payload.get("type") != "join":
            await websocket.close(code=4000)
            return
        
        username = payload.get("username", "Anonymous")
        await manager.connect(room_name, websocket, username)
        with SessionLocal() as db:
            await manager.broadcast(room_name, username, f"{username} joined the room.", db)
            db.close()

        while True:
            # Receive input
            data = await websocket.receive_text()
            payload = json.loads(data)
            if payload.get("type") == "chat":
                message = payload.get("message", "")
                if message:
                    with SessionLocal() as db:
                        await manager.broadcast(room_name, username, f"{username}: {message}", db)
                        db.close()

    # Handle disconnection
    except WebSocketDisconnect:
        # Disconnect this connection
        manager.disconnect(room_name, websocket)
        # Announce disconnection
        await manager.broadcast(room_name, "A user disconnected")